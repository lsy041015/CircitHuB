"""
Qt GUI – split into submodules for maintainability.

Public API is preserved: `from digikey_scraper.qt_gui import main, MainWindow`
"""
from ._main_window import MainWindow, main
from ._result_card import ResultCard
from ._stylesheet import APP_QSS
from ._translations import TRANSLATIONS
from ._widgets import (
    FlowLayout,
    NewSearchButton,
    PartChip,
    SideFavoriteItem,
    SideHistoryItem,
    ToggleSwitch,
)

__all__ = [
    "main",
    "MainWindow",
    "ResultCard",
    "APP_QSS",
    "TRANSLATIONS",
    "FlowLayout",
    "NewSearchButton",
    "PartChip",
    "SideFavoriteItem",
    "SideHistoryItem",
    "ToggleSwitch",
]


if __name__ == "__main__":
    main()
