import unittest
from unittest.mock import patch

from digikey_scraper._main_window import MainWindow
from digikey_scraper._main_window_sidebar import MainWindowSidebarMixin


class _Label:
    def setText(self, text):
        self.text = text


class _FakeSignal:
    def __init__(self) -> None:
        self.connected = []

    def connect(self, callback) -> None:
        self.connected.append(callback)


class _FakeHistoryWidget:
    def __init__(self, label, meta, status, payload) -> None:
        self.label = label
        self.meta = meta
        self.status = status
        self.payload = payload
        self.item_clicked = _FakeSignal()
        self.deleted = False

    def deleteLater(self) -> None:
        self.deleted = True


class _FakeFavoriteWidget:
    def __init__(self, name, price) -> None:
        self.name = name
        self.price = price
        self.item_clicked = _FakeSignal()
        self.deleted = False

    def deleteLater(self) -> None:
        self.deleted = True


class _FakeItem:
    def __init__(self, widget) -> None:
        self._widget = widget

    def widget(self):
        return self._widget


class _FakeLayout:
    def __init__(self, widgets=None) -> None:
        self.widgets = list(widgets or [])

    def count(self) -> int:
        return len(self.widgets)

    def takeAt(self, index: int):
        return _FakeItem(self.widgets.pop(index))

    def addWidget(self, widget) -> None:
        self.widgets.append(widget)


class MainWindowSidebarTests(unittest.TestCase):
    def test_main_window_uses_sidebar_mixin(self) -> None:
        self.assertTrue(issubclass(MainWindow, MainWindowSidebarMixin))

    def test_api_state_ready_updates_footer_labels(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.footer_name = _Label()
        window.footer_meta = _Label()
        window.sb_connected = _Label()
        window.sb_api = _Label()

        window._set_api_state("ready")

        self.assertEqual(window.footer_name.text, "DigiKey")
        self.assertEqual(window.sb_connected.text, "● 준비됨")

    def test_update_statusbar_falls_back_to_default_timeout(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.parts = [{"name": "LM358P", "qty": 1}, {"name": "NE5532P", "qty": 1}]
        window.timeout_default = "15"
        window.timeout_input = type("TimeoutInput", (), {"text": lambda self: "bad"})()
        window.sb_parts = _Label()
        window.sb_timeout = _Label()
        def _tr(key, **kwargs):
            if key == "statusbar_parts_fmt":
                return f"parts={kwargs['n']}"
            if key == "statusbar_timeout_fmt":
                return f"timeout={kwargs['t']}"
            raise KeyError(key)

        window._tr = _tr

        window._update_statusbar()

        self.assertEqual(window.sb_parts.text, "parts=2")
        self.assertEqual(window.sb_timeout.text, "timeout=15")

    def test_render_sidebar_lists_updates_badges_and_renders_recent_history(self) -> None:
        window = MainWindow.__new__(MainWindow)
        old_history = _FakeHistoryWidget("old", "old-meta", "old-status", ["old"])
        old_favorite = _FakeFavoriteWidget("OLD", "$9.99")
        window.history_container_layout = _FakeLayout([old_history])
        window.fav_container_layout = _FakeLayout([old_favorite])
        window.history = [
            ("Q1", ["Q1"], "meta1", "ok"),
            ("Q2", ["Q2"], "meta2", "warning"),
        ]
        window.favorites = {"LM358P", "NE5532P"}
        window.favorite_prices = {"LM358P": "$0.10"}
        window._hist_count_cnt = _Label()
        window._fav_count_cnt = _Label()
        window._load_history_label = lambda payload: payload
        window._load_fav_item = lambda name: name

        with patch(
            "digikey_scraper._main_window_sidebar.SideHistoryItem",
            _FakeHistoryWidget,
        ), patch(
            "digikey_scraper._main_window_sidebar.SideFavoriteItem",
            _FakeFavoriteWidget,
        ):
            window.render_sidebar_lists()

        self.assertTrue(old_history.deleted)
        self.assertTrue(old_favorite.deleted)
        self.assertEqual(window._hist_count_cnt.text, "2")
        self.assertEqual(window._fav_count_cnt.text, "2")
        self.assertEqual(
            [widget.label for widget in window.history_container_layout.widgets],
            ["Q2", "Q1"],
        )
        self.assertEqual(
            [widget.payload for widget in window.history_container_layout.widgets],
            [["Q2"], ["Q1"]],
        )
        self.assertEqual(
            [widget.name for widget in window.fav_container_layout.widgets],
            ["LM358P", "NE5532P"],
        )
        self.assertEqual(
            [widget.price for widget in window.fav_container_layout.widgets],
            ["$0.10", ""],
        )


if __name__ == "__main__":
    unittest.main()
