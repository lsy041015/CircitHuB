"""Tests for the P1 resilient pluggable supplier (registry + retry/backoff)."""

import unittest

from digikey_scraper.domain.errors import ScrapeTimeout
from digikey_scraper.domain.models import ProductResult
from digikey_scraper.infrastructure.scraping.registry import SupplierRegistry, default_registry
from digikey_scraper.infrastructure.scraping.resilient import ResilientSupplier


class FlakyScraper:
    """Fails `fail_times` then succeeds; records lifecycle calls."""

    def __init__(self, fail_times=0, exc=RuntimeError("boom")):
        self.fail_times = fail_times
        self.exc = exc
        self.calls = 0
        self.opened = self.closed = self.cancelled = False
        self.driver = "drv"

    def open(self):
        self.opened = True

    def fetch_one(self, query, timeout):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise self.exc
        return ProductResult(query=query, title="ok")

    def cancel(self):
        self.cancelled = True

    def close(self):
        self.closed = True


class ResilientRetryTests(unittest.TestCase):
    def _no_sleep(self):
        delays = []
        return delays, (lambda d: delays.append(d))

    def test_succeeds_first_try_no_retry(self):
        inner = FlakyScraper(fail_times=0)
        delays, sleep = self._no_sleep()
        r = ResilientSupplier(inner, retries=2, sleep=sleep)
        res = r.fetch_one("Q", 15)
        self.assertEqual(res.title, "ok")
        self.assertEqual(inner.calls, 1)
        self.assertEqual(r.last_attempts, 1)
        self.assertEqual(delays, [])

    def test_retries_then_succeeds(self):
        inner = FlakyScraper(fail_times=2)
        delays, sleep = self._no_sleep()
        r = ResilientSupplier(inner, retries=3, base_delay=0.5, sleep=sleep)
        res = r.fetch_one("Q", 15)
        self.assertEqual(res.title, "ok")
        self.assertEqual(inner.calls, 3)
        self.assertEqual(r.last_attempts, 3)
        # exponential backoff: 0.5 * 2^0, 0.5 * 2^1
        self.assertEqual(delays, [0.5, 1.0])

    def test_exhausts_retries_then_raises(self):
        inner = FlakyScraper(fail_times=5, exc=ScrapeTimeout("slow"))
        delays, sleep = self._no_sleep()
        r = ResilientSupplier(inner, retries=2, sleep=sleep)
        with self.assertRaises(ScrapeTimeout):
            r.fetch_one("Q", 15)
        self.assertEqual(inner.calls, 3)  # 1 + 2 retries
        self.assertEqual(r.last_attempts, 3)

    def test_backoff_capped_at_max_delay(self):
        inner = FlakyScraper(fail_times=10)
        delays, sleep = self._no_sleep()
        r = ResilientSupplier(inner, retries=5, base_delay=1.0, max_delay=4.0, sleep=sleep)
        with self.assertRaises(RuntimeError):
            r.fetch_one("Q", 15)
        self.assertEqual(delays, [1.0, 2.0, 4.0, 4.0, 4.0])

    def test_should_cancel_stops_retrying(self):
        inner = FlakyScraper(fail_times=5)
        delays, sleep = self._no_sleep()
        r = ResilientSupplier(inner, retries=5, sleep=sleep, should_cancel=lambda: True)
        with self.assertRaises(RuntimeError):
            r.fetch_one("Q", 15)
        self.assertEqual(inner.calls, 1)  # no retry after cancel
        self.assertEqual(delays, [])

    def test_lifecycle_and_driver_delegate(self):
        inner = FlakyScraper()
        r = ResilientSupplier(inner)
        r.open()
        r.cancel()
        r.close()
        self.assertTrue(inner.opened and inner.cancelled and inner.closed)
        self.assertEqual(r.driver, "drv")

    def test_negative_retries_rejected(self):
        with self.assertRaises(ValueError):
            ResilientSupplier(FlakyScraper(), retries=-1)


class RegistryTests(unittest.TestCase):
    def test_register_create_names(self):
        reg = SupplierRegistry()
        reg.register("fake", lambda show_browser=False: FlakyScraper())
        self.assertEqual(reg.names(), ["fake"])
        self.assertIsInstance(reg.create("fake"), FlakyScraper)

    def test_unknown_supplier_raises(self):
        reg = SupplierRegistry()
        with self.assertRaises(KeyError):
            reg.create("nope")

    def test_default_registry_has_digikey(self):
        reg = default_registry()
        self.assertIn("digikey", reg.names())
        scraper = reg.create("digikey", show_browser=False)
        # Built without opening a real browser; just verify the port shape.
        self.assertTrue(hasattr(scraper, "fetch_one"))
        self.assertIsNone(scraper.driver)


if __name__ == "__main__":
    unittest.main()
