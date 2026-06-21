"""Tests for P0 architecture layers: domain, application services, persistence, DI."""

import os
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from digikey_scraper.application.search_service import NullProgressSink, SearchService
from digikey_scraper.application.settings_service import FileSettingsStore
from digikey_scraper.container import build_container
from digikey_scraper.domain.errors import ScrapeTimeout
from digikey_scraper.domain.models import ProductResult
from digikey_scraper.domain.pricing import calc_bom_total, extract_unit_price
from digikey_scraper.infrastructure.persistence.json_repository import JsonResultRepository
from digikey_scraper.infrastructure.persistence.serialization import (
    result_from_dict,
    result_to_dict,
)


class FakeScraper:
    """In-memory SupplierScraper for headless tests."""

    def __init__(self, behavior=None):
        self.behavior = behavior or {}
        self.opened = False
        self.closed = False

    def open(self):
        self.opened = True

    def fetch_one(self, query, timeout):
        action = self.behavior.get(query, "ok")
        if action == "timeout":
            raise ScrapeTimeout("slow")
        if action == "boom":
            raise RuntimeError("network down")
        return ProductResult(query=query, title=f"{query} title", price_rows=["1|$1.00|$1.00"])

    def cancel(self):
        pass

    def close(self):
        self.closed = True


class SearchServiceTests(unittest.TestCase):
    def test_runs_headless_and_collects_results(self):
        scraper = FakeScraper()
        sink = NullProgressSink()
        SearchService(scraper).run(["LM358P", "TL072CP"], 15, False, sink)
        self.assertEqual(len(sink.results), 2)
        self.assertFalse(sink.cancelled)
        self.assertTrue(scraper.opened)
        self.assertTrue(scraper.closed)
        self.assertIsNone(sink.error)

    def test_timeout_becomes_error_result_not_crash(self):
        scraper = FakeScraper({"BAD": "timeout"})
        sink = NullProgressSink()
        SearchService(scraper, language="en").run(["BAD"], 15, False, sink)
        self.assertEqual(len(sink.results), 1)
        self.assertIn("timed out", sink.results[0].error)

    def test_generic_error_becomes_error_result(self):
        scraper = FakeScraper({"BAD": "boom"})
        sink = NullProgressSink()
        SearchService(scraper, language="en").run(["BAD"], 15, False, sink)
        self.assertIn("network down", sink.results[0].error)

    def test_blocked_error_becomes_clear_error_result(self):
        from digikey_scraper.domain.errors import ScrapeBlocked

        class BlockedScraper(FakeScraper):
            def fetch_one(self, query, timeout):
                raise ScrapeBlocked("Cloudflare challenge")

        sink = NullProgressSink()
        SearchService(BlockedScraper(), language="en").run(["LM358P"], 15, False, sink)
        self.assertIn("blocked automated access", sink.results[0].error)

    def test_precancelled_run_finishes_cancelled(self):
        scraper = FakeScraper()
        sink = NullProgressSink()
        ev = threading.Event()
        ev.set()
        SearchService(scraper).run(["LM358P"], 15, False, sink, ev)
        self.assertTrue(sink.cancelled)
        self.assertEqual(sink.results, [])

    def test_show_browser_keeps_driver_open(self):
        scraper = FakeScraper()
        SearchService(scraper).run(["LM358P"], 15, True, NullProgressSink())
        self.assertFalse(scraper.closed)


class SettingsStoreTests(unittest.TestCase):
    def test_round_trip(self):
        with TemporaryDirectory() as d:
            store = FileSettingsStore(Path(d) / "settings.json")
            self.assertEqual(store.load(), {})
            store.save({"language": "en", "timeout": 20})
            self.assertEqual(store.load()["language"], "en")

    def test_corrupt_file_returns_empty(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "settings.json"
            p.write_text("{not json", encoding="utf-8")
            self.assertEqual(FileSettingsStore(p).load(), {})


class JsonRepositoryTests(unittest.TestCase):
    def test_save_and_recent(self):
        with TemporaryDirectory() as d:
            repo = JsonResultRepository(Path(d))
            sid = repo.save_search(["LM358P"], [ProductResult(query="LM358P", title="x")], "ko")
            self.assertIsNotNone(sid)
            recent = repo.recent_searches()
            self.assertEqual(len(recent), 1)
            self.assertEqual(recent[0]["query_count"], 1)

    def test_recent_empty_when_no_dir(self):
        with TemporaryDirectory() as d:
            repo = JsonResultRepository(Path(d) / "missing")
            self.assertEqual(repo.recent_searches(), [])


class SerializationTests(unittest.TestCase):
    def test_result_round_trip_with_candidates(self):
        r = ProductResult(
            query="Q",
            title="T",
            price_rows=["1|$1|$1"],
            specs={"k": "v"},
            candidate_results=[ProductResult(query="C", title="cand")],
        )
        back = result_from_dict(result_to_dict(r))
        self.assertEqual(back.title, "T")
        self.assertEqual(back.specs, {"k": "v"})
        self.assertEqual(back.candidate_results[0].title, "cand")


class ContainerTests(unittest.TestCase):
    def test_build_container_falls_back_to_json_without_db(self):
        c = build_container()
        self.assertIsInstance(c.results, JsonResultRepository)
        self.assertTrue(hasattr(c.settings, "load"))


class PricingTests(unittest.TestCase):
    def test_extract_unit_price(self):
        self.assertEqual(extract_unit_price("$1,234.50"), 1234.50)
        self.assertEqual(extract_unit_price("no price"), float("inf"))

    def test_calc_bom_total_skips_errors(self):
        ok = ProductResult(query="A", price_rows=["100|$0.50|$50.00"])
        bad = ProductResult(query="B", error="x")
        self.assertEqual(calc_bom_total([ok, bad]), 50.0)

    def test_calc_bom_total_uses_requested_quantities(self):
        result = ProductResult(
            query="A",
            price_rows=["1|$1.00|$1.00", "10|$0.75|$7.50", "100|$0.50|$50.00"],
        )
        self.assertEqual(calc_bom_total([result], {"A": 12}), 9.0)


class PgRepositoryTests(unittest.TestCase):
    """Exercises the Postgres repo against an in-memory SQLite engine.

    The repo uses generic SQLAlchemy Core, so it is backend-agnostic and we can
    verify its logic without a running Postgres.
    """

    def _engine(self):
        from sqlalchemy import create_engine

        # StaticPool keeps one shared in-memory DB across connections.
        from sqlalchemy.pool import StaticPool

        return create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )

    def test_save_and_recent_round_trip(self):
        from digikey_scraper.infrastructure.persistence.pg_repository import PgResultRepository

        repo = PgResultRepository(self._engine())
        sid = repo.save_search(["LM358P", "TL072CP"], [ProductResult(query="LM358P")], "en")
        self.assertIsNotNone(sid)
        recent = repo.recent_searches()
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["query_count"], 2)
        self.assertEqual(recent[0]["language"], "en")
        self.assertEqual(recent[0]["queries"], ["LM358P", "TL072CP"])


class SeleniumAdapterTests(unittest.TestCase):
    def test_open_uses_driver_factory_and_translates_timeout(self):
        from selenium.common.exceptions import TimeoutException

        from digikey_scraper.infrastructure.scraping import selenium_supplier as mod

        fake_driver = object()
        created = {}

        def fake_create_driver(headless):
            created["headless"] = headless
            return fake_driver

        def fake_fetch(driver, query, timeout):
            raise TimeoutException("slow")

        orig_create, orig_fetch = mod.create_driver, mod.fetch_one_product
        mod.create_driver, mod.fetch_one_product = fake_create_driver, fake_fetch
        try:
            scraper = mod.SeleniumDigiKeyScraper(show_browser=False)
            scraper.open()
            self.assertIs(scraper.driver, fake_driver)
            self.assertTrue(created["headless"])
            with self.assertRaises(ScrapeTimeout):
                scraper.fetch_one("LM358P", 15)
        finally:
            mod.create_driver, mod.fetch_one_product = orig_create, orig_fetch
            scraper.close()
            self.assertIsNone(scraper.driver)

    def test_value_error_blocked_translates_to_domain_error(self):
        from digikey_scraper.domain.errors import ScrapeBlocked
        from digikey_scraper.infrastructure.scraping import selenium_supplier as mod

        orig_create, orig_fetch = mod.create_driver, mod.fetch_one_product
        mod.create_driver = lambda headless: object()
        mod.fetch_one_product = lambda d, q, t: (_ for _ in ()).throw(ValueError("자동화 접근을 차단"))
        try:
            scraper = mod.SeleniumDigiKeyScraper(show_browser=False)
            with self.assertRaises(ScrapeBlocked):
                scraper.fetch_one("LM358P", 15)
        finally:
            mod.create_driver, mod.fetch_one_product = orig_create, orig_fetch
            scraper.close()


class ResilientSupplierTests(unittest.TestCase):
    def test_does_not_retry_blocked_errors(self):
        from digikey_scraper.domain.errors import ScrapeBlocked
        from digikey_scraper.infrastructure.scraping.resilient import ResilientSupplier

        class BlockedSupplier(FakeScraper):
            def fetch_one(self, query, timeout):
                self.calls = getattr(self, "calls", 0) + 1
                raise ScrapeBlocked("blocked")

        supplier = BlockedSupplier()
        resilient = ResilientSupplier(supplier, retries=3, sleep=lambda _delay: None)

        with self.assertRaises(ScrapeBlocked):
            resilient.fetch_one("LM358P", 15)

        self.assertEqual(supplier.calls, 1)
        self.assertEqual(resilient.last_attempts, 1)


class DriverFactoryTests(unittest.TestCase):
    def test_undetected_chrome_respects_headless_flag(self):
        import types

        from digikey_scraper import driver as mod

        captured = {}

        class FakeChromeOptions:
            def __init__(self):
                self.arguments = []
                self.experimental_options = {}
                self.binary_location = None

            def add_argument(self, value):
                self.arguments.append(value)

            def add_experimental_option(self, key, value):
                self.experimental_options[key] = value

        class FakeChrome:
            def __init__(
                self,
                options,
                headless,
                user_data_dir,
                version_main,
                driver_executable_path,
            ):
                captured["arguments"] = list(options.arguments)
                captured["headless"] = headless
                captured["user_data_dir"] = user_data_dir
                captured["version_main"] = version_main
                captured["driver_executable_path"] = driver_executable_path

            def quit(self):
                pass

        fake_uc = types.SimpleNamespace(ChromeOptions=FakeChromeOptions, Chrome=FakeChrome)

        with (
            patch.dict("sys.modules", {"undetected_chromedriver": fake_uc, "pyvirtualdisplay": None}),
            patch.object(mod, "_find_chrome_binary", return_value=None),
            patch.object(mod, "_get_chrome_major_version", return_value=124),
            patch.object(mod, "_system_chromedriver_is_snap", return_value=False),
            patch.object(mod, "_chrome_profile_config", return_value=(None, None)),
            patch.object(mod, "_clear_profile_locks"),
        ):
            mod.create_driver(headless=True)

        self.assertIn("--headless=new", captured["arguments"])
        self.assertTrue(captured["headless"])

    def test_undetected_chrome_can_reuse_configured_profile(self):
        import types

        from digikey_scraper import driver as mod

        captured = {}

        class FakeChromeOptions:
            def __init__(self):
                self.arguments = []
                self.experimental_options = {}

            def add_argument(self, value):
                self.arguments.append(value)

            def add_experimental_option(self, key, value):
                self.experimental_options[key] = value

        class FakeChrome:
            def __init__(
                self,
                options,
                headless,
                user_data_dir,
                version_main,
                driver_executable_path,
            ):
                captured["arguments"] = list(options.arguments)
                captured["headless"] = headless
                captured["user_data_dir"] = user_data_dir

            def quit(self):
                pass

        fake_uc = types.SimpleNamespace(ChromeOptions=FakeChromeOptions, Chrome=FakeChrome)

        with (
            patch.dict(
                "os.environ",
                {
                    "DIGIKEY_CHROME_USER_DATA_DIR": "~/chrome-profile",
                    "DIGIKEY_CHROME_PROFILE_DIRECTORY": "Default",
                },
            ),
            patch.dict("sys.modules", {"undetected_chromedriver": fake_uc, "pyvirtualdisplay": None}),
            patch.object(mod, "_find_chrome_binary", return_value=None),
            patch.object(mod, "_get_chrome_major_version", return_value=124),
            patch.object(mod, "_system_chromedriver_is_snap", return_value=False),
            patch.object(mod, "_clear_profile_locks"),
        ):
            mod.create_driver(headless=True)

        self.assertEqual(captured["user_data_dir"], os.path.expanduser("~/chrome-profile"))
        self.assertIn("--profile-directory=Default", captured["arguments"])
        self.assertIn("--start-minimized", captured["arguments"])
        self.assertIn("--window-position=-32000,-32000", captured["arguments"])
        self.assertNotIn("--headless=new", captured["arguments"])
        self.assertFalse(captured["headless"])


class QtSinkTests(unittest.TestCase):
    def test_qt_progress_sink_forwards_to_signals(self):
        from digikey_scraper.workers import _QtProgressSink

        class FakeSignal:
            def __init__(self):
                self.calls = []

            def emit(self, *args):
                self.calls.append(args)

        class FakeSignals:
            progress = FakeSignal()
            finished = FakeSignal()
            failed = FakeSignal()

        sigs = FakeSignals()
        sink = _QtProgressSink(sigs)
        sink.on_progress(1, 3, "Q")
        sink.on_finished([], True, False)
        sink.on_failed("boom")
        self.assertEqual(sigs.progress.calls, [(1, 3, "Q")])
        self.assertEqual(sigs.finished.calls, [([], True, False)])
        self.assertEqual(sigs.failed.calls, [("boom",)])


class DbHelperTests(unittest.TestCase):
    def test_database_url_and_availability(self):
        import os

        from digikey_scraper.infrastructure.persistence import db

        old = os.environ.get("DATABASE_URL")
        try:
            os.environ.pop("DATABASE_URL", None)
            self.assertIsNone(db.database_url())
            self.assertFalse(db.db_available())
            os.environ["DATABASE_URL"] = "postgresql+psycopg2://u:p@localhost/x"
            self.assertEqual(db.database_url(), "postgresql+psycopg2://u:p@localhost/x")
            self.assertTrue(db.db_available())  # SQLAlchemy is installed in dev
        finally:
            if old is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = old

    def test_make_engine_requires_url(self):
        import os

        from digikey_scraper.infrastructure.persistence import db

        old = os.environ.get("DATABASE_URL")
        try:
            os.environ["DATABASE_URL"] = "sqlite://"
            engine = db.make_engine()
            self.assertIsNotNone(engine)
            os.environ.pop("DATABASE_URL", None)
            with self.assertRaises(RuntimeError):
                db.make_engine()
        finally:
            if old is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = old


class SeleniumSuccessTests(unittest.TestCase):
    def test_fetch_one_success_and_cancel(self):
        from digikey_scraper.infrastructure.scraping import selenium_supplier as mod

        result = ProductResult(query="LM358P", title="ok")
        orig_create, orig_fetch = mod.create_driver, mod.fetch_one_product
        mod.create_driver = lambda headless: object()
        mod.fetch_one_product = lambda d, q, t: result
        try:
            scraper = mod.SeleniumDigiKeyScraper(show_browser=True)
            self.assertIs(scraper.fetch_one("LM358P", 15), result)  # auto-opens
            self.assertIsNotNone(scraper.driver)
            scraper.cancel()
            self.assertIsNone(scraper.driver)
        finally:
            mod.create_driver, mod.fetch_one_product = orig_create, orig_fetch


class CandidateFormattingTests(unittest.TestCase):
    def test_candidate_lines_fill_missing_with_no_info(self):
        from digikey_scraper.formatters import display_value, format_candidate_lines

        r = ProductResult(query="Q", title="LM358", part_number="296-1234-5-ND")
        lines = format_candidate_lines(r, "en")
        self.assertTrue(any("LM358" in ln for ln in lines))
        self.assertTrue(any("296-1234-5-ND" in ln for ln in lines))
        # missing title falls back to the localized "no info" string
        self.assertNotEqual(display_value(None, "en"), "")

    def test_product_result_to_candidate_lines_delegates(self):
        from digikey_scraper.formatters import format_candidate_lines

        r = ProductResult(query="Q", title="T")
        self.assertEqual(r.to_candidate_lines("ko"), format_candidate_lines(r, "ko"))


class SearchWorkerWiringTests(unittest.TestCase):
    def test_worker_exposes_driver_and_cancel_without_opening(self):
        from digikey_scraper.workers import SearchWorker

        class FakeSignals:
            pass

        worker = SearchWorker(["LM358P"], 15, False, FakeSignals(), "ko")
        self.assertIsNone(worker.driver)  # no driver until run/open
        worker.cancel()  # must not raise
        self.assertTrue(worker._cancel_event.is_set())


if __name__ == "__main__":
    unittest.main()
