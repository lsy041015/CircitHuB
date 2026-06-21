import unittest

from digikey_scraper._helpers import normalize_part_query
from digikey_scraper._main_window import MainWindow, _spell_match_score
from digikey_scraper._main_window_parts import MainWindowPartsMixin


class _FakeChipInput:
    def __init__(self) -> None:
        self._text = ""

    def setText(self, text: str) -> None:
        self._text = text

    def text(self) -> str:
        return self._text

    def clear(self) -> None:
        self._text = ""


class PartSuggestionTests(unittest.TestCase):
    def test_main_window_uses_part_mixin(self) -> None:
        self.assertTrue(issubclass(MainWindow, MainWindowPartsMixin))

    def test_normalize_part_query_strips_noisy_candidate_card_text(self) -> None:
        self.assertEqual(
            normalize_part_query("LM324N IC OPAMP GP 4 CIRCUIT 14DIP INTERSIL $0.30000 DETAILS"),
            "LM324N",
        )
        self.assertEqual(normalize_part_query("DETAILS"), "")
        self.assertEqual(normalize_part_query("$0.30000"), "")

    def test_part_suggestions_follow_typed_spelling_and_typos(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window._part_suggestion_pool = lambda: ["LM358P", "TL072CP", "NE5532P", "STM32F103C8T6"]

        self.assertEqual(window._part_suggestions("LM358")[0], "LM358P")
        self.assertEqual(window._part_suggestions("LM35BP")[0], "LM358P")
        self.assertEqual(window._part_suggestions("F103C8")[0], "STM32F103C8T6")
        self.assertIsNotNone(_spell_match_score("TL02CP", "TL072CP"))

    def test_accepting_single_suggestion_adds_one_part_even_with_spaces(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.parts = []
        window._chip_input = _FakeChipInput()
        window.render_chips = lambda: None
        window.render_results = lambda: None
        window._update_run_button = lambda: None
        window._update_statusbar = lambda: None
        window.save_settings = lambda: None

        window._accept_part_suggestion("ESP32 WROOM 32E")

        self.assertEqual(window.parts, [{"name": "ESP32 WROOM 32E", "qty": 1}])
        self.assertEqual(window._chip_input.text(), "")

    def test_accepting_suggestion_skips_followup_commit_of_stale_text(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.parts = []
        window._chip_input = _FakeChipInput()
        window.render_chips = lambda: None
        window.render_results = lambda: None
        window._update_run_button = lambda: None
        window._update_statusbar = lambda: None
        window.save_settings = lambda: None

        window._accept_part_suggestion("LM358P")
        window._chip_input.setText("LM358")
        window.commit_input()

        self.assertEqual(window.parts, [{"name": "LM358P", "qty": 1}])
        self.assertEqual(window._chip_input.text(), "")

    def test_loading_history_payload_preserves_parts_with_spaces(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.parts = []
        window.render_chips = lambda: None
        window.render_results = lambda: None
        window._update_run_button = lambda: None
        window._update_statusbar = lambda: None
        window.save_settings = lambda: None

        window._load_history_label(["ESP32 WROOM 32E", "LM358P"])

        self.assertEqual(
            window.parts,
            [
                {"name": "ESP32 WROOM 32E", "qty": 1},
                {"name": "LM358P", "qty": 1},
            ],
        )

    def test_part_suggestion_pool_filters_noisy_saved_queries(self) -> None:
        window = MainWindow.__new__(MainWindow)
        window.parts = [{"name": "LM324N IC OPAMP GP 4 CIRCUIT 14DIP INTERSIL $0.30000 DETAILS", "qty": 1}]
        window.favorites = {"LM358P", "DETAILS"}
        window.history = [
            ("x", ["IC", "LM324N IC OPAMP GP 4 CIRCUIT 14DIP INTERSIL $0.30000 DETAILS"], "now", "warning")
        ]
        window.result_repository = type(
            "_Repo",
            (),
            {
                "recent_searches": staticmethod(
                    lambda limit=30: [
                        {"queries": ["DETAILS", "OPA2134PA IC AUDIO 2 CIRCUIT 8DIP Texas Instruments $7.64000 Details"]}
                    ]
                )
            },
        )()
        window._default_parts = lambda: []

        pool = window._part_suggestion_pool()

        self.assertIn("LM324N", pool)
        self.assertIn("OPA2134PA", pool)
        self.assertNotIn("DETAILS", pool)
        self.assertNotIn("IC", pool)
        self.assertNotIn("LM324N IC OPAMP GP 4 CIRCUIT 14DIP INTERSIL $0.30000 DETAILS", pool)

    def test_sanitize_parts_normalizes_noisy_saved_part_name(self) -> None:
        window = MainWindow.__new__(MainWindow)

        parts = window._sanitize_parts(
            [{"name": "LM324N IC OPAMP GP 4 CIRCUIT 14DIP INTERSIL $0.30000 DETAILS", "qty": 1}]
        )

        self.assertEqual(parts, [{"name": "LM324N", "qty": 1}])


if __name__ == "__main__":
    unittest.main()
