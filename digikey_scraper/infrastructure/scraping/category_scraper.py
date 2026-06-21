"""Selenium-backed scraper that fetches a DigiKey category listing page."""

from __future__ import annotations

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ...domain.models import ProductResult
from ...driver import create_driver, get_page_soup
from ...scraper import DETAIL_LINK_SELECTOR, parse_category_listing


class CategoryScraper:
    """Fetches a DigiKey category filter page and returns up to `limit` ProductResults.

    One connection only — no per-product detail page visits.
    """

    def __init__(self, show_browser: bool = False) -> None:
        self.show_browser = show_browser
        self._driver: webdriver.Chrome | None = None

    @property
    def driver(self) -> webdriver.Chrome | None:
        return self._driver

    def open(self) -> None:
        if self._driver is None:
            self._driver = create_driver(headless=not self.show_browser)

    def fetch(
        self,
        url: str,
        category_label: str,
        limit: int = 25,
        timeout: int = 30,
    ) -> list[ProductResult]:
        if self._driver is None:
            self.open()
        assert self._driver is not None

        self._driver.get(url)
        try:
            WebDriverWait(self._driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, DETAIL_LINK_SELECTOR))
            )
        except TimeoutException:
            pass  # parse whatever loaded

        soup = get_page_soup(self._driver)
        return parse_category_listing(soup, category_label=category_label, limit=limit)

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
