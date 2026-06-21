import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from digikey_scraper._circuitkit_design import CircuitKitWindow
from digikey_scraper._helpers import app_data_dir, runtime_path
from digikey_scraper._main_window import MainWindow as ProductionMainWindow
from digikey_scraper.datasheet_viewer import _configure_tesseract, _find_tesseract_cmd
from digikey_scraper.qt_gui import MainWindow


class WindowsRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    def test_qt_gui_mainwindow_is_production_window(self) -> None:
        self.assertIs(MainWindow, ProductionMainWindow)

    def test_main_window_constructs_offscreen(self) -> None:
        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        try:
            self.assertIn("DigiKey", window.windowTitle())
            self.assertTrue(window.footer_meta.text())
        finally:
            window.close()
            app.processEvents()

    def test_legacy_circuitkit_window_switches_search_and_chat_pages(self) -> None:
        app = QApplication.instance() or QApplication([])
        window = CircuitKitWindow()
        try:
            self.assertEqual(window.page_stack.currentIndex(), 0)
            window._switch_page("chat")
            self.assertEqual(window.page_stack.currentIndex(), 1)
            self.assertEqual(window.active_page, "chat")
            window._open_chat("NE5532P")
            self.assertIn("NE5532P", [p["name"] for p in window.chat_window.composer.attached])
            window._switch_page("search")
            self.assertEqual(window.page_stack.currentIndex(), 0)
        finally:
            window.close()
            app.processEvents()

    def test_runtime_path_override_still_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"DIGIKEY_SCRAPER_DATA_DIR": tmp}):
                self.assertEqual(runtime_path("shared_specs"), Path(tmp) / "shared_specs")

    @unittest.skipUnless(os.name == "nt", "Windows app data path is Windows-only")
    def test_windows_app_data_uses_localappdata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "DIGIKEY_SCRAPER_DATA_DIR": "",
                "LOCALAPPDATA": tmp,
                "APPDATA": str(Path(tmp) / "Roaming"),
                "XDG_DATA_HOME": str(Path(tmp) / "xdg"),
            }
            with patch.dict(os.environ, env):
                self.assertEqual(app_data_dir(), Path(tmp) / "DigiKeyPriceScraper")

    @unittest.skipUnless(os.name == "nt", "Windows Tesseract paths are Windows-only")
    def test_tesseract_discovery_checks_windows_install_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exe = root / "Tesseract-OCR" / "tesseract.exe"
            exe.parent.mkdir()
            exe.write_text("", encoding="utf-8")
            env = {
                "PATH": "",
                "TESSERACT_CMD": "",
                "ProgramFiles": str(root),
                "ProgramFiles(x86)": "",
                "LOCALAPPDATA": "",
            }
            with patch.dict(os.environ, env):
                self.assertEqual(_find_tesseract_cmd(), str(exe))

    def test_configure_tesseract_returns_false_when_missing(self) -> None:
        class FakePytesseract:
            class pytesseract:
                tesseract_cmd = ""

        with patch("digikey_scraper.datasheet_viewer._find_tesseract_cmd", return_value=None):
            self.assertFalse(_configure_tesseract(FakePytesseract))


if __name__ == "__main__":
    unittest.main()
