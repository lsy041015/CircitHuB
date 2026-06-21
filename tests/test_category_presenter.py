import unittest

from digikey_scraper._translations import TRANSLATIONS
from digikey_scraper.category_presenter import (
    category_badge_text,
    category_result_payload,
    category_strip_payload,
)


def _tr(lang: str):
    table = TRANSLATIONS[lang]

    def translate(key: str, **kw) -> str:
        text = table[key]
        return text.format(**kw) if kw else text

    return translate


class CategoryPresenterTests(unittest.TestCase):
    def test_idle_result_payload_guides_tile_click(self) -> None:
        title, detail = category_result_payload(_tr("ko"), "idle")
        self.assertIn("카테고리", title)
        self.assertIn("타일", detail)

    def test_searching_strip_payload_mentions_category_label(self) -> None:
        state, main, detail, progress = category_strip_payload(
            _tr("ko"), "searching", label="저항"
        )
        self.assertEqual(state, "searching")
        self.assertIn("저항", main)
        self.assertIn("목록", detail)
        self.assertEqual(progress, 15)

    def test_empty_payload_distinguishes_no_results_from_error(self) -> None:
        state, main, detail, progress = category_strip_payload(
            _tr("ko"), "empty", label="센서"
        )
        self.assertEqual(state, "cancelled")
        self.assertIn("없", main)
        self.assertIn("센서", detail)
        self.assertEqual(progress, 100)

    def test_error_payload_includes_retry_guidance(self) -> None:
        title, detail = category_result_payload(
            _tr("en"), "error", label="Resistor", error="403 forbidden"
        )
        self.assertIn("Resistor", title)
        self.assertIn("403 forbidden", detail)
        self.assertIn("retry", detail.lower())

    def test_badge_text_uses_idle_copy_without_label(self) -> None:
        text = category_badge_text(_tr("ko"), "")
        self.assertIn("실행 전", text)

    def test_badge_text_includes_last_category_label(self) -> None:
        text = category_badge_text(_tr("en"), "MCU")
        self.assertIn("MCU", text)
        self.assertIn("Last", text)


if __name__ == "__main__":
    unittest.main()
