"""Bundled application fonts.

Registers Pretendard (sans) and JetBrains Mono (mono) from
``assets/fonts`` so the QSS ``font-family`` rules resolve to the same
typefaces the reference web design uses. Falls back silently to system
fonts (Malgun Gothic / Consolas) if the files are missing.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFontDatabase


def _font_dir() -> Path:
    # PyInstaller extracts bundled data under sys._MEIPASS; the source tree
    # keeps the fonts next to this module.
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "digikey_scraper" / "assets" / "fonts"
    return Path(__file__).resolve().parent / "assets" / "fonts"


_FONT_DIR = _font_dir()


def load_fonts() -> list[str]:
    """Register all bundled font files. Returns loaded family names."""
    families: list[str] = []
    if not _FONT_DIR.is_dir():
        return families
    for path in sorted(_FONT_DIR.glob("*.[ot]tf")):
        fid = QFontDatabase.addApplicationFont(str(path))
        if fid != -1:
            families.extend(QFontDatabase.applicationFontFamilies(fid))
    return families
