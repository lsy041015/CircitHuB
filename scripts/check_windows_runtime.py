from __future__ import annotations

import argparse
import importlib
import os
import platform
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REQUIRED_MODULES = [
    "PySide6",
    "selenium",
    "bs4",
    "numpy",
    "cv2",
    "fitz",
    "pytesseract",
    "google.genai",
]


def _print_result(name: str, ok: bool, detail: str = "", *, warning: bool = False) -> None:
    status = "WARN" if warning else "OK" if ok else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"{status}: {name}{suffix}")


def _import_check() -> bool:
    ok = True
    for module_name in REQUIRED_MODULES:
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, "__version__", "")
            _print_result(f"import {module_name}", True, str(version))
        except Exception as exc:
            ok = False
            _print_result(f"import {module_name}", False, f"{type(exc).__name__}: {exc}")
    return ok


def _qt_check() -> bool:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication
        from digikey_scraper.qt_gui import MainWindow

        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        _print_result("Qt MainWindow", True, window.windowTitle())
        window.close()
        app.processEvents()
        return True
    except Exception as exc:
        _print_result("Qt MainWindow", False, f"{type(exc).__name__}: {exc}")
        return False


def _selenium_check(skip_browser: bool) -> bool:
    if skip_browser:
        _print_result("Selenium Chrome driver", True, "skipped")
        return True
    try:
        from digikey_scraper.driver import create_driver

        driver = create_driver(headless=True)
        driver.quit()
        _print_result("Selenium Chrome driver", True)
        return True
    except Exception as exc:
        _print_result("Selenium Chrome driver", False, f"{type(exc).__name__}: {exc}")
        return False


def _external_tools_check() -> bool:
    chrome = shutil.which("chrome") or shutil.which("chrome.exe") or shutil.which("google-chrome")
    chromedriver = shutil.which("chromedriver") or shutil.which("chromedriver.exe")
    tesseract = shutil.which("tesseract") or shutil.which("tesseract.exe")

    _print_result(
        "Chrome on PATH",
        bool(chrome),
        chrome or "Selenium Manager may still find Chrome",
        warning=not bool(chrome),
    )
    _print_result(
        "ChromeDriver on PATH",
        bool(chromedriver),
        chromedriver or "Selenium Manager may download/use driver",
        warning=not bool(chromedriver),
    )
    _print_result(
        "Tesseract on PATH",
        bool(tesseract),
        tesseract or "OCR disabled until installed/configured",
        warning=not bool(tesseract),
    )
    return True


def _path_check() -> bool:
    try:
        from digikey_scraper._helpers import app_data_dir

        data_dir = app_data_dir()
        _print_result("runtime data dir", True, str(data_dir))
        if platform.system() == "Windows":
            expected_roots = [
                os.environ.get("LOCALAPPDATA", ""),
                os.environ.get("APPDATA", ""),
            ]
            if not any(root and Path(data_dir).is_relative_to(Path(root)) for root in expected_roots):
                _print_result("Windows app data root", False, str(data_dir))
                return False
        return True
    except Exception as exc:
        _print_result("runtime data dir", False, f"{type(exc).__name__}: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Windows runtime readiness.")
    parser.add_argument("--skip-browser", action="store_true", help="Skip launching Selenium Chrome.")
    args = parser.parse_args()

    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {platform.platform()}")

    checks = [
        _import_check(),
        _qt_check(),
        _selenium_check(args.skip_browser),
        _external_tools_check(),
        _path_check(),
    ]
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
