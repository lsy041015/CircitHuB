import unittest

from digikey_scraper._main_window import MainWindow
from digikey_scraper._main_window_search import MainWindowSearchMixin, result_status_counts
from digikey_scraper.models import ProductResult


class MainWindowSearchTests(unittest.TestCase):
    def test_main_window_uses_search_mixin(self) -> None:
        self.assertTrue(issubclass(MainWindow, MainWindowSearchMixin))

    def test_failure_guide_classifies_common_errors(self) -> None:
        window = MainWindow.__new__(MainWindow)

        self.assertIn("Chrome", window._build_failure_guide("ChromeDriver missing"))
        self.assertIn("network", window._build_failure_guide("request timed out").lower())
        self.assertIn("request rate", window._build_failure_guide("429 too many requests").lower())

    def test_result_status_counts_tracks_blocked_and_candidates(self) -> None:
        counts = result_status_counts(
            [
                ProductResult(query="OK", title="ok"),
                ProductResult(query="BLOCKED", error="공급사가 자동화 접근을 차단했습니다"),
                ProductResult(query="CAND", candidate_results=[ProductResult(query="C1")]),
            ]
        )

        self.assertEqual(counts["completed"], 2)
        self.assertEqual(counts["errors"], 1)
        self.assertEqual(counts["blocked"], 1)
        self.assertEqual(counts["candidates"], 1)


if __name__ == "__main__":
    unittest.main()
