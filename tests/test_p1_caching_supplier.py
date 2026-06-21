"""Tests for the P1 CachingSupplier decorator (TTL, mem + disk)."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from digikey_scraper.domain.models import ProductResult
from digikey_scraper.infrastructure.scraping.caching import CachingSupplier


class CountingSupplier:
    def __init__(self, error=False):
        self.error = error
        self.calls = 0
        self.opened = self.closed = self.cancelled = False
        self.driver = "drv"

    def open(self):
        self.opened = True

    def fetch_one(self, query, timeout):
        self.calls += 1
        if self.error:
            return ProductResult(query=query, error="boom")
        return ProductResult(query=query, title=f"{query}-{self.calls}")

    def cancel(self):
        self.cancelled = True

    def close(self):
        self.closed = True


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class CachingTests(unittest.TestCase):
    def test_second_call_hits_cache(self):
        inner = CountingSupplier()
        c = CachingSupplier(inner, ttl_seconds=100, clock=FakeClock())
        r1 = c.fetch_one("LM358P", 15)
        r2 = c.fetch_one("LM358P", 15)
        self.assertEqual(inner.calls, 1)  # only one real fetch
        self.assertEqual(r1.title, r2.title)
        self.assertEqual((c.hits, c.misses), (1, 1))

    def test_case_insensitive_key(self):
        inner = CountingSupplier()
        c = CachingSupplier(inner, ttl_seconds=100)
        c.fetch_one("lm358p", 15)
        c.fetch_one("LM358P", 15)
        self.assertEqual(inner.calls, 1)

    def test_ttl_expiry_refetches(self):
        inner = CountingSupplier()
        clock = FakeClock()
        c = CachingSupplier(inner, ttl_seconds=50, clock=clock)
        c.fetch_one("Q", 15)
        clock.t += 60  # past TTL
        c.fetch_one("Q", 15)
        self.assertEqual(inner.calls, 2)

    def test_errors_not_cached(self):
        inner = CountingSupplier(error=True)
        c = CachingSupplier(inner, ttl_seconds=100)
        c.fetch_one("Q", 15)
        c.fetch_one("Q", 15)
        self.assertEqual(inner.calls, 2)  # error re-fetched each time

    def test_disk_persists_across_instances(self):
        with TemporaryDirectory() as d:
            inner1 = CountingSupplier()
            c1 = CachingSupplier(inner1, ttl_seconds=1000, cache_dir=d)
            c1.fetch_one("Q", 15)
            # new instance, fresh memory, same disk dir
            inner2 = CountingSupplier()
            c2 = CachingSupplier(inner2, ttl_seconds=1000, cache_dir=d)
            r = c2.fetch_one("Q", 15)
            self.assertEqual(inner2.calls, 0)  # served from disk
            self.assertTrue(r.title)
            self.assertTrue(any(Path(d).glob("*.json")))

    def test_lifecycle_and_driver_delegate(self):
        inner = CountingSupplier()
        c = CachingSupplier(inner)
        c.open()
        c.cancel()
        c.close()
        self.assertTrue(inner.opened and inner.cancelled and inner.closed)
        self.assertEqual(c.driver, "drv")


if __name__ == "__main__":
    unittest.main()
