"""Tests for P1 multi-supplier aggregation + local catalog supplier."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from digikey_scraper.application.search_service import NullProgressSink, SearchService
from digikey_scraper.domain.models import ProductResult
from digikey_scraper.infrastructure.scraping.aggregating import AggregatingSupplier
from digikey_scraper.infrastructure.scraping.local_catalog import LocalCatalogSupplier
from digikey_scraper.infrastructure.scraping.registry import default_registry


class FakeSupplier:
    def __init__(self, results=None, raises=None):
        self.results = results or {}
        self.raises = raises or {}
        self.opened = self.closed = self.cancelled = False
        self.driver = None

    def open(self):
        self.opened = True

    def fetch_one(self, query, timeout):
        if query in self.raises:
            raise self.raises[query]
        return self.results.get(query, ProductResult(query=query, error="missing"))

    def cancel(self):
        self.cancelled = True

    def close(self):
        self.closed = True


class AggregatingTests(unittest.TestCase):
    def test_picks_lowest_unit_price(self):
        cheap = ProductResult(query="Q", title="cheap", price_rows=["100|$0.20|$20"])
        pricey = ProductResult(query="Q", title="pricey", price_rows=["100|$0.50|$50"])
        agg = AggregatingSupplier([FakeSupplier({"Q": pricey}), FakeSupplier({"Q": cheap})])
        agg.open()
        best = agg.fetch_one("Q", 15)
        self.assertEqual(best.title, "cheap")

    def test_skips_error_results(self):
        good = ProductResult(query="Q", title="good", price_rows=["1|$1|$1"])
        agg = AggregatingSupplier(
            [FakeSupplier({"Q": ProductResult(query="Q", error="x")}), FakeSupplier({"Q": good})]
        )
        self.assertEqual(agg.fetch_one("Q", 15).title, "good")

    def test_supplier_exception_does_not_abort_others(self):
        good = ProductResult(query="Q", title="good", price_rows=["1|$1|$1"])
        agg = AggregatingSupplier(
            [FakeSupplier(raises={"Q": RuntimeError("down")}), FakeSupplier({"Q": good})]
        )
        self.assertEqual(agg.fetch_one("Q", 15).title, "good")

    def test_all_fail_returns_error(self):
        agg = AggregatingSupplier(
            [
                FakeSupplier(raises={"Q": RuntimeError("a")}),
                FakeSupplier({"Q": ProductResult(query="Q", error="b")}),
            ]
        )
        self.assertIsNotNone(agg.fetch_one("Q", 15).error)

    def test_lifecycle_fans_out(self):
        a, b = FakeSupplier(), FakeSupplier()
        agg = AggregatingSupplier([a, b])
        agg.open()
        agg.cancel()
        agg.close()
        self.assertTrue(
            a.opened and b.opened and a.cancelled and b.cancelled and a.closed and b.closed
        )

    def test_empty_suppliers_rejected(self):
        with self.assertRaises(ValueError):
            AggregatingSupplier([])

    def test_first_strategy_returns_first_success(self):
        r1 = ProductResult(query="Q", title="first", price_rows=["1|$9|$9"])
        r2 = ProductResult(query="Q", title="second", price_rows=["1|$1|$1"])
        agg = AggregatingSupplier(
            [FakeSupplier({"Q": r1}), FakeSupplier({"Q": r2})], strategy="first"
        )
        self.assertEqual(agg.fetch_one("Q", 15).title, "first")


class LocalCatalogTests(unittest.TestCase):
    def _catalog(self, d):
        path = Path(d) / "catalog.json"
        path.write_text(
            json.dumps(
                {
                    "LM358P": {
                        "title": "LM358",
                        "part_number": "296-1-ND",
                        "price_rows": ["1|$0.40|$0.40"],
                    }
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_hit_and_miss(self):
        with TemporaryDirectory() as d:
            s = LocalCatalogSupplier(self._catalog(d))
            s.open()
            hit = s.fetch_one("lm358p", 15)  # case-insensitive
            self.assertEqual(hit.title, "LM358")
            self.assertIsNone(hit.error)
            miss = s.fetch_one("UNKNOWN", 15)
            self.assertIn("not in", miss.error)

    def test_missing_catalog_file_is_graceful(self):
        s = LocalCatalogSupplier("/nonexistent/catalog.json")
        s.open()
        self.assertIsNotNone(s.fetch_one("LM358P", 15).error)


class MultiSupplierIntegrationTests(unittest.TestCase):
    def test_search_service_over_aggregating_supplier(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "c.json"
            path.write_text(
                json.dumps({"LM358P": {"title": "local-LM358", "price_rows": ["100|$0.15|$15"]}}),
                encoding="utf-8",
            )
            local = default_registry().create("local", catalog_path=path)
            web_like = FakeSupplier(
                {"LM358P": ProductResult(query="LM358P", title="web", price_rows=["100|$0.30|$30"])}
            )
            agg = AggregatingSupplier([web_like, local])
            sink = NullProgressSink()
            SearchService(agg).run(["LM358P"], 15, False, sink)
            self.assertEqual(len(sink.results), 1)
            self.assertEqual(sink.results[0].title, "local-LM358")  # cheaper wins


if __name__ == "__main__":
    unittest.main()
