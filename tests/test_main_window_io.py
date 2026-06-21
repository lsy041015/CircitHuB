import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from digikey_scraper._main_window import MainWindow
from digikey_scraper._main_window_io import MainWindowIoMixin


class _IoHarness(MainWindowIoMixin):
    def __init__(self) -> None:
        self.parts = [{"name": "OLD", "qty": 1}]
        self.results = ["old-result"]
        self._query_times = [1.0]
        self.latest_share_text = "old share"
        self.status_message = None
        self.saved = False
        self.render_chips_calls = 0
        self.render_results_calls = 0
        self.update_run_button_calls = 0
        self.update_statusbar_calls = 0

    def _tr(self, key: str, **values) -> str:
        if values:
            return f"{key}:{values}"
        return key

    def render_chips(self) -> None:
        self.render_chips_calls += 1

    def render_results(self) -> None:
        self.render_results_calls += 1

    def _update_run_button(self) -> None:
        self.update_run_button_calls += 1

    def _update_statusbar(self) -> None:
        self.update_statusbar_calls += 1

    def set_status(self, message: str, _progress=None) -> None:
        self.status_message = message

    def save_settings(self) -> None:
        self.saved = True


class TestMainWindowIo(unittest.TestCase):
    def test_main_window_uses_io_mixin(self) -> None:
        self.assertTrue(issubclass(MainWindow, MainWindowIoMixin))

    def test_get_result_text_strips_whitespace(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.latest_share_text = "  abc  \n"
        self.assertEqual(window.get_result_text(), "abc")

    def test_auto_save_results_writes_expected_file(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.latest_share_text = "hello"
        with TemporaryDirectory() as tmp:
            window.auto_save_dir = Path(tmp) / "nested" / "autosave"
            saved = window._auto_save_results()
            self.assertIsNotNone(saved)
            assert saved is not None
            self.assertTrue(saved.exists())
            self.assertTrue(saved.name.startswith("digikey_results_"))
            self.assertEqual(saved.read_text(encoding="utf-8"), "hello")

    def test_import_bom_clears_view_state_for_empty_bom(self) -> None:
        window = _IoHarness()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.csv"
            path.write_text(",;\n\t", encoding="utf-8")
            with patch(
                "digikey_scraper._main_window_io.QFileDialog.getOpenFileName",
                return_value=(str(path), ""),
            ):
                window.import_bom()

        self.assertEqual(window.parts, [])
        self.assertEqual(window.results, [])
        self.assertEqual(window._query_times, [])
        self.assertEqual(window.latest_share_text, "")
        self.assertEqual(window.render_chips_calls, 1)
        self.assertEqual(window.render_results_calls, 1)
        self.assertEqual(window.update_run_button_calls, 1)
        self.assertEqual(window.update_statusbar_calls, 1)
        self.assertTrue(window.saved)
        self.assertIn("bom_loaded_status", window.status_message)


if __name__ == "__main__":
    unittest.main()
