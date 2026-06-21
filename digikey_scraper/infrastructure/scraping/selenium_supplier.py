"""Selenium-backed DigiKey scraper adapter implementing the SupplierScraper port.

Wraps the existing functional scraper (``digikey_scraper.scraper``) and driver
factory (``digikey_scraper.driver``) behind the domain port so the application
layer stays framework-agnostic.
"""

from __future__ import annotations

import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from ...constants import BASE_URL
from ...domain.errors import ScrapeBlocked, ScrapeTimeout
from ...domain.models import ProductResult
from ...driver import create_driver, get_page_soup
from ...scraper import fetch_one_product, is_blocked_search_page

_WARMUP_TIMEOUT = 15
_CHALLENGE_POLL_INTERVAL = 1
_CHALLENGE_MAX_WAIT = 30


def _wait_for_cf_challenge(driver, max_wait: int = _CHALLENGE_MAX_WAIT) -> None:
    """Poll until Cloudflare JS challenge auto-resolves or max_wait seconds pass."""
    if not is_blocked_search_page(get_page_soup(driver)):
        return
    for _ in range(max_wait):
        time.sleep(_CHALLENGE_POLL_INTERVAL)
        try:
            if not is_blocked_search_page(get_page_soup(driver)):
                return
        except Exception:
            pass


class SeleniumDigiKeyScraper:
    """SupplierScraper backed by a single reusable Selenium Chrome driver."""

    def __init__(self, show_browser: bool = False) -> None:
        self.show_browser = show_browser
        self._driver: webdriver.Chrome | None = None

    @property
    def driver(self) -> webdriver.Chrome | None:
        return self._driver

    def open(self) -> None:
        if self._driver is None:
            self._driver = create_driver(headless=not self.show_browser)
            self._warmup()

    def _warmup(self) -> None:
        if self._driver is None:
            return
        try:
            self._driver.get(BASE_URL)
            WebDriverWait(self._driver, _WARMUP_TIMEOUT).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            _wait_for_cf_challenge(self._driver)
        except Exception:
            pass

    def fetch_one(self, query: str, timeout: int) -> ProductResult:
        if self._driver is None:
            self.open()
        try:
            if self._driver is not None and hasattr(self._driver, "set_page_load_timeout"):
                self._driver.set_page_load_timeout(timeout)
            return fetch_one_product(self._driver, query, timeout)
        except TimeoutException as exc:
            raise ScrapeTimeout(str(exc)) from exc
        except ValueError as exc:
            if "차단" in str(exc) or "blocked" in str(exc).lower():
                if self._driver is not None:
                    try:
                        self._driver.get(BASE_URL)
                        _wait_for_cf_challenge(self._driver)
                    except Exception:
                        pass
                raise ScrapeBlocked(str(exc)) from exc
            raise

    def cancel(self) -> None:
        self._quit()

    def close(self) -> None:
        self._quit()

    def _quit(self) -> None:
        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None
