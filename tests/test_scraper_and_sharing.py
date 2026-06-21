import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz
from bs4 import BeautifulSoup
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from digikey_scraper._helpers import runtime_path
from digikey_scraper._result_card import ResultCard
from digikey_scraper.constants import MAIN_SPEC_ALIASES, NO_INFO
from digikey_scraper.datasheet_benchmark import (
    evaluate_detections,
    load_annotation_regions,
    region_iou,
)
from digikey_scraper.datasheet_viewer import (
    DatasheetViewer,
    _GemmaResultDialog,
)
from digikey_scraper.formatters import format_result_text, format_results_text
from digikey_scraper.gemma_client import GEMMA_MODEL, GemmaDatasheetAnalyzer, load_gemma_api_keys
from digikey_scraper.models import ProductResult
from digikey_scraper.qt_gui import MainWindow
from digikey_scraper.scraper import (
    DETAIL_LINK_SELECTOR,
    classify_search_page_issue,
    extract_datasheet_url,
    extract_part_number,
    extract_product_links_from_soup,
    extract_specs,
    fetch_product_detail,
    is_blocked_search_page,
    is_category_url,
    is_detail_url,
    normalize_datasheet_url,
)
from digikey_scraper.sharing import (
    MAX_SHARE_BYTES,
    receive_shared_text,
    safe_filename,
    save_shared_text,
)
from digikey_scraper.text_utils import normalize_key, normalize_part


class ScraperExtractionTests(unittest.TestCase):
    def test_url_helpers_accept_locale_independent_digikey_paths(self) -> None:
        self.assertTrue(is_detail_url("https://www.digikey.com/products/detail/vendor/part/123"))
        self.assertTrue(is_detail_url("https://www.digikey.com/en/products/detail/vendor/part/123"))
        self.assertTrue(is_category_url("/products/category/integrated-circuits-ics/32"))
        self.assertTrue(is_category_url("/en/products/filter/amplifiers/687"))

    def test_detail_link_selector_accepts_locale_independent_path(self) -> None:
        soup = BeautifulSoup(
            '<a href="/products/detail/texas-instruments/LM358P/277042">LM358P</a>',
            "html.parser",
        )

        self.assertEqual(soup.select_one(DETAIL_LINK_SELECTOR).get_text(strip=True), "LM358P")

    def test_product_link_extraction_uses_selector_fallbacks_and_dedupes(self) -> None:
        soup = BeautifulSoup(
            """
            <section class="ProductCard">
              <a data-testid="product-card-link" href="/product-detail/analog-devices/AD8606/123">AD8606</a>
              <p>Operational amplifier</p>
            </section>
            <section class="ProductCard">
              <a data-testid="product-card-link" href="/product-detail/analog-devices/AD8606/123">AD8606 duplicate</a>
            </section>
            """,
            "html.parser",
        )

        links = extract_product_links_from_soup(soup)

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].name, "AD8606")
        self.assertEqual(links[0].url, "https://www.digikey.com/product-detail/analog-devices/AD8606/123")
        self.assertIn("Operational amplifier", links[0].description)

    def test_product_link_extraction_prefers_exact_part_name_over_card_text(self) -> None:
        soup = BeautifulSoup(
            """
            <div class="ProductCard">
              <a data-testid="product-card-link" href="/products/detail/intersil/LM324N/123">
                LM324N IC OPAMP GP 4 CIRCUIT 14DIP INTERSIL $0.30000 DETAILS
              </a>
            </div>
            """,
            "html.parser",
        )

        links = extract_product_links_from_soup(soup)

        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].name, "LM324N")

    def test_search_page_issue_classifies_blocked_no_results_and_dom_change(self) -> None:
        blocked = BeautifulSoup("<html><body>Access Denied verify you are human</body></html>", "html.parser")
        empty = BeautifulSoup("<main>No results found for xyz</main>", "html.parser")
        changed = BeautifulSoup("<table><tr><td>Part</td><td>LM358P</td></tr></table>", "html.parser")

        self.assertIn("차단", classify_search_page_issue(blocked))
        self.assertIn("일치하는 제품이 없습니다", classify_search_page_issue(empty))
        self.assertIn("구조가 변경", classify_search_page_issue(changed))

    def test_cloudflare_just_a_moment_is_blocked_page(self) -> None:
        soup = BeautifulSoup("<html><head><title>Just a moment...</title></head><body></body></html>", "html.parser")

        self.assertTrue(is_blocked_search_page(soup))
        self.assertIn("차단", classify_search_page_issue(soup))

    def test_fetch_product_detail_rejects_blocked_detail_page(self) -> None:
        class FakeDriver:
            def get(self, url: str) -> None:
                self.current_url = url

        soup = BeautifulSoup("<html><head><title>Just a moment...</title></head><body></body></html>", "html.parser")
        with (
            patch("digikey_scraper.scraper.wait_for_detail_page", lambda *_args: None),
            patch("digikey_scraper.scraper.get_page_soup", return_value=soup),
        ):
            with self.assertRaises(ValueError):
                fetch_product_detail(FakeDriver(), "LM358P", "https://example.test/product", 15)

    def test_fetch_product_detail_rejects_empty_detail_page(self) -> None:
        class FakeDriver:
            def get(self, url: str) -> None:
                self.current_url = url

        soup = BeautifulSoup("<html><head><title>www.digikey.com</title></head><body></body></html>", "html.parser")
        with (
            patch("digikey_scraper.scraper.wait_for_detail_page", lambda *_args: None),
            patch("digikey_scraper.scraper.get_page_soup", return_value=soup),
        ):
            with self.assertRaises(ValueError):
                fetch_product_detail(FakeDriver(), "LM358P", "https://example.test/product", 15)

    def test_extract_part_number_accepts_digikey_hyphen_variant(self) -> None:
        soup = BeautifulSoup("<main>Digi-Key Part Number 296-1395-5-ND</main>", "html.parser")

        self.assertEqual(extract_part_number(soup), "296-1395-5-ND")

    def test_extract_datasheet_url_prefers_pdf_over_html_datasheet(self) -> None:
        soup = BeautifulSoup(
            """
            <a href="/htmldatasheets/parts/lm358.html">Datasheet</a>
            <a href="https://www.ti.com/lit/ds/symlink/lm358.pdf">Datasheet PDF</a>
            """,
            "html.parser",
        )

        self.assertEqual(extract_datasheet_url(soup), "https://www.ti.com/lit/ds/symlink/lm358.pdf")

    def test_extract_datasheet_url_normalizes_ti_goto_url(self) -> None:
        soup = BeautifulSoup(
            """
            <a href="https://www.ti.com/general/docs/suppproductinfo.tsp?distId=10&gotoUrl=https%3A%2F%2Fwww.ti.com%2Flit%2Fgpn%2Flm358">Datasheet</a>
            """,
            "html.parser",
        )

        self.assertEqual(extract_datasheet_url(soup), "https://www.ti.com/lit/gpn/lm358")

    def test_normalize_datasheet_url_decodes_ti_goto_url(self) -> None:
        self.assertEqual(
            normalize_datasheet_url(
                "https://www.ti.com/general/docs/suppproductinfo.tsp?gotoUrl=https%3A%2F%2Fwww.ti.com%2Flit%2Fgpn%2Fne5532"
            ),
            "https://www.ti.com/lit/gpn/ne5532",
        )

    def test_extract_specs_uses_clean_korean_labels(self) -> None:
        html = """
        <table>
          <tr><th>Manufacturer</th><td>Texas Instruments</td></tr>
          <tr><th>Mounting Type</th><td>Surface Mount</td></tr>
          <tr><th>Voltage - Supply</th><td>3 V to 30 V</td></tr>
        </table>
        """

        specs = extract_specs(BeautifulSoup(html, "html.parser"), MAIN_SPEC_ALIASES)

        self.assertEqual(specs["제조사"], "Texas Instruments")
        self.assertEqual(specs["실장유형"], "SMD")
        self.assertEqual(specs["전압 - 범위(최소)"], "3 V")
        self.assertEqual(specs["전압 - 범위(최대)"], "30 V")
        self.assertEqual(specs["작동 온도"], NO_INFO)


class SharingTests(unittest.TestCase):
    class FakeConnection:
        def __init__(self, data: bytes) -> None:
            self._data = bytearray(data)
            self.sent = bytearray()

        def recv(self, size: int) -> bytes:
            chunk = self._data[:size]
            del self._data[:size]
            return bytes(chunk)

        def sendall(self, data: bytes) -> None:
            self.sent.extend(data)

    def _framed_share_payload(self, metadata: object, payload: bytes = b"") -> bytes:
        encoded_metadata = json.dumps(metadata).encode("utf-8")
        return len(encoded_metadata).to_bytes(4, "big") + encoded_metadata + payload

    def test_runtime_path_uses_data_dir_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"DIGIKEY_SCRAPER_DATA_DIR": tmp}):
                self.assertEqual(runtime_path("shared_specs"), Path(tmp) / "shared_specs")

    def test_safe_filename_removes_windows_reserved_characters(self) -> None:
        self.assertEqual(safe_filename('bad:name<>.txt'), "bad_name__.txt")

    def test_safe_filename_falls_back_when_empty(self) -> None:
        self.assertEqual(safe_filename("<<<"), "digikey_specs.txt")

    def test_save_shared_text_avoids_filename_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("digikey_scraper.sharing.SHARE_DIR", Path(tmp)):
                first = save_shared_text("result.txt", "first")
                second = save_shared_text("result.txt", "second")

            self.assertNotEqual(first, second)
            self.assertEqual(first.read_text(encoding="utf-8"), "first")
            self.assertEqual(second.read_text(encoding="utf-8"), "second")

    def test_receive_shared_text_reads_framed_payload(self) -> None:
        payload = "hello 공유".encode()
        connection = self.FakeConnection(
            self._framed_share_payload({"filename": "result.txt", "size": len(payload)}, payload)
        )

        filename, text = receive_shared_text(connection)

        self.assertEqual(filename, "result.txt")
        self.assertEqual(text, "hello 공유")
        self.assertEqual(bytes(connection.sent), b"OK")

    def test_receive_shared_text_rejects_non_object_metadata(self) -> None:
        connection = self.FakeConnection(self._framed_share_payload(["bad"]))

        with self.assertRaises(ValueError):
            receive_shared_text(connection)

    def test_receive_shared_text_rejects_large_payload(self) -> None:
        connection = self.FakeConnection(
            self._framed_share_payload({"filename": "too-large.txt", "size": MAX_SHARE_BYTES + 1})
        )

        with self.assertRaises(ValueError):
            receive_shared_text(connection)


class FormatterTests(unittest.TestCase):
    def test_product_result_text_helpers_accept_language(self) -> None:
        result = ProductResult(
            query="LM358P",
            title="LM358P Operational Amplifier",
            part_number="296-1395-5-ND",
            specs={"제조사": "Texas Instruments"},
        )

        self.assertIn("Search term: LM358P", result.to_text("en"))
        self.assertIn("Product name: LM358P Operational Amplifier", "\n".join(result.to_candidate_lines("en")))

    def test_result_text_supports_korean_and_english(self) -> None:
        result = ProductResult(
            query="LM358P",
            title="LM358P Operational Amplifier",
            product_url="https://example.test/product",
            part_number="296-1395-5-ND",
            price_rows=["1 | $0.50 | $0.50"],
            specs={"제조사": "Texas Instruments"},
        )

        korean = format_result_text(result, "ko")
        english = format_result_text(result, "en")

        self.assertIn("검색어: LM358P", korean)
        self.assertIn("[가격 정보]", korean)
        self.assertIn("Search term: LM358P", english)
        self.assertIn("[Price information]", english)
        self.assertIn("작동 온도: N/A", english)

    def test_results_text_uses_separator_between_results(self) -> None:
        text = format_results_text([ProductResult(query="A"), ProductResult(query="B")], "en")

        self.assertIn("Search term: A", text)
        self.assertIn("Search term: B", text)
        self.assertIn("=" * 80, text)

    def test_results_text_can_include_requested_quantity(self) -> None:
        text = format_results_text([ProductResult(query="A")], "en", {"A": 12})

        self.assertIn("Requested quantity: 12", text)


class TextNormalizationTests(unittest.TestCase):
    def test_normalize_key_unifies_common_digikey_label_variants(self) -> None:
        self.assertEqual(
            normalize_key("Voltage–Supply, Single/Dual (±)"),
            normalize_key("voltage - supply single / dual (+/-)"),
        )
        self.assertEqual(normalize_key("Current - Supply (µA)"), normalize_key("current_supply (uA)"))

    def test_normalize_part_ignores_separator_and_case_variants(self) -> None:
        self.assertEqual(normalize_part("lm-358p"), normalize_part("LM358P"))
        self.assertEqual(normalize_part(" 296-1395-5-ND "), "29613955ND")


class DatasheetBenchmarkTests(unittest.TestCase):
    def test_region_iou_and_detection_metrics(self) -> None:
        self.assertEqual(region_iou((0, 0, 10, 10), (20, 20, 5, 5)), 0.0)
        self.assertGreater(region_iou((0, 0, 10, 10), (1, 1, 10, 10)), 0.5)

        metrics = evaluate_detections([(0, 0, 10, 10), (50, 50, 10, 10)], [(1, 1, 10, 10)])

        self.assertEqual(metrics.matched, 1)
        self.assertEqual(metrics.predicted, 2)
        self.assertEqual(metrics.truth, 1)
        self.assertEqual(metrics.precision, 0.5)
        self.assertEqual(metrics.recall, 1.0)

    def test_benchmark_sample_annotation_loads(self) -> None:
        path = Path("benchmarks/datasheet_table_detection/sample_annotations.json")

        regions = load_annotation_regions(path, 3)

        self.assertEqual(len(regions), 2)
        self.assertEqual(regions[0], (50, 80, 420, 180))


class GuiThreadBoundaryTests(unittest.TestCase):
    def test_status_key_slot_formats_message_on_main_window(self) -> None:
        app = QApplication.instance() or QApplication([])
        window = MainWindow()
        try:
            window.stop_receiver()
            window.set_status_key("send_done", {"peer": "127.0.0.1", "port": 5000})

            self.assertIn("127.0.0.1:5000", window._status_message)
        finally:
            window.close()
            app.processEvents()

    def test_datasheet_button_uses_card_language(self) -> None:
        app = QApplication.instance() or QApplication([])
        result = ProductResult(
            query="LM358P",
            title="LM358P",
            datasheet_url="https://example.test/lm358p.pdf",
        )
        card = ResultCard(1, result, False, "en")
        try:
            with patch("digikey_scraper.datasheet_viewer.open_datasheet") as mocked_open:
                card._open_datasheet()

            mocked_open.assert_called_once_with(result.datasheet_url, result.title, "en", parent=card)
        finally:
            card.close()
            app.processEvents()

    def test_candidate_button_emits_exact_search_value(self) -> None:
        app = QApplication.instance() or QApplication([])
        candidate = ProductResult(
            query="LM324N IC OPAMP GP 4 CIRCUIT 14DIP INTERSIL $0.30000 DETAILS",
            title="LM324N Quad Op Amp",
            part_number="LM324N",
        )
        result = ProductResult(query="LM324", candidate_results=[candidate])
        card = ResultCard(1, result, False, "en")
        emitted: list[str] = []
        card.candidate_requested.connect(emitted.append)
        try:
            buttons = card.findChildren(QPushButton, "CandidateBtn")
            button = buttons[0] if buttons else None
            self.assertIsNotNone(button)
            button.click()
            self.assertEqual(emitted, ["LM324N"])
        finally:
            card.close()
            app.processEvents()

    def test_error_card_exposes_retry_and_digikey_actions(self) -> None:
        app = QApplication.instance() or QApplication([])
        result = ProductResult(query="NE5532P", error="Supplier blocked automated access")
        card = ResultCard(1, result, False, "en")
        emitted: list[str] = []
        card.candidate_requested.connect(emitted.append)
        try:
            buttons = {button.text(): button for button in card.findChildren(QPushButton)}
            self.assertIn("Retry", buttons)
            self.assertIn("Open DigiKey", buttons)
            buttons["Retry"].click()
            self.assertEqual(emitted, ["NE5532P"])
        finally:
            card.close()
            app.processEvents()

    def test_minimal_datasheet_viewer_renders_and_navigates_pdf(self) -> None:
        app = QApplication.instance() or QApplication([])
        pdf_path = Path(tempfile.gettempdir()) / "digikey_datasheet_viewer_test.pdf"
        doc = fitz.open()
        page1 = doc.new_page(width=300, height=200)
        page1.insert_text((40, 80), "LM358P PAGE 1", fontsize=18)
        page2 = doc.new_page(width=300, height=200)
        page2.insert_text((40, 80), "LM358P PAGE 2", fontsize=18)
        doc.save(str(pdf_path))
        doc.close()

        viewer = DatasheetViewer(pdf_path.as_uri(), "LM358P", "en")
        try:
            self._wait_for_pdf(app, viewer)

            self.assertEqual(viewer._page_count, 2)
            self.assertIsNotNone(viewer._img_lbl.pixmap())
            self.assertFalse(viewer._img_lbl.pixmap().isNull())
            self.assertEqual(viewer._page_lbl.text(), "1 / 2")

            viewer._next_page()
            self.assertEqual(viewer._current, 1)
            self.assertEqual(viewer._page_lbl.text(), "2 / 2")

            viewer._prev_page()
            self.assertEqual(viewer._current, 0)
            self.assertEqual(viewer._page_lbl.text(), "1 / 2")
        finally:
            viewer.close()
            app.processEvents()
            pdf_path.unlink(missing_ok=True)

    def test_minimal_datasheet_viewer_error_message_mentions_url_and_reason(self) -> None:
        app = QApplication.instance() or QApplication([])
        with patch.object(DatasheetViewer, "_load_pdf", lambda self: None):
            viewer = DatasheetViewer("https://example.test/not-a-pdf.html", "LM358P", "en")
        try:
            viewer._on_load_error("datasheet response is not a PDF")

            self.assertIn("Load failed", viewer._img_lbl.text())
            self.assertIn("https://example.test/not-a-pdf.html", viewer._img_lbl.text())
            self.assertIn("not a PDF", viewer._img_lbl.text())
        finally:
            viewer.close()
            app.processEvents()

    def test_minimal_datasheet_viewer_extracts_and_encodes_selected_region(self) -> None:
        app = QApplication.instance() or QApplication([])
        pdf_path = Path(tempfile.gettempdir()) / "digikey_datasheet_region_extract_test.pdf"
        doc = fitz.open()
        page = doc.new_page(width=360, height=220)
        page.insert_text((40, 70), "Supply Voltage 2.7V 5.0V 5.5V", fontsize=12)
        doc.save(str(pdf_path))
        doc.close()

        viewer = DatasheetViewer(pdf_path.as_uri(), "analysis", "en")
        try:
            self._wait_for_pdf(app, viewer)
            scale = viewer._dpi / 72.0
            region = (int(35 * scale), int(55 * scale), int(280 * scale), int(35 * scale))

            text = viewer._extract_region_pdf_text(region)
            self.assertIn("Supply", text)
            self.assertIn("5.5V", text)

            encoded = viewer._encode_region_png(region)
            self.assertIsNotNone(encoded)
            self.assertGreater(len(encoded), 100)

            crop = viewer._crop_region_bgr((9999, 9999, 999, 999))
            self.assertEqual(crop.shape[0], 1)
            self.assertEqual(crop.shape[1], 1)
        finally:
            viewer.close()
            app.processEvents()
            pdf_path.unlink(missing_ok=True)

    def test_minimal_datasheet_viewer_selection_mode_and_status(self) -> None:
        app = QApplication.instance() or QApplication([])
        with patch.object(DatasheetViewer, "_load_pdf", lambda self: None):
            viewer = DatasheetViewer("https://example.test/test.pdf", "LM358P", "ko")
        try:
            viewer._set_selection_mode("translate")

            self.assertEqual(viewer._selection_mode, "translate")
            self.assertTrue(viewer._translate_btn.isChecked())
            self.assertIn("드래그", viewer._viewer_status_lbl.text())
            self.assertEqual(viewer._normalized_region((20, 30), (5, 10)), (5, 10, 15, 20))

            viewer._set_selection_mode("translate")
            self.assertIsNone(viewer._selection_mode)
            self.assertFalse(viewer._translate_btn.isChecked())
        finally:
            viewer.close()
            app.processEvents()

    @staticmethod
    def _wait_for_pdf(app, viewer, timeout: float = 5.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline and viewer._page_count <= 0:
            app.processEvents()
            time.sleep(0.02)
        app.processEvents()
        if viewer._page_count <= 0:
            raise AssertionError(viewer._img_lbl.text() or "PDF did not load")


class GemmaClientTests(unittest.TestCase):
    def test_gemini_flash_is_default_model(self) -> None:
        self.assertEqual(GEMMA_MODEL, "gemini-2.5-flash")
        self.assertEqual(GemmaDatasheetAnalyzer(keys=["test-key"]).model, "gemini-2.5-flash")

    def test_load_gemma_api_keys_reads_project_key_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_dir = root / "config" / "api_keys"
            key_dir.mkdir(parents=True)
            (key_dir / "gemini_api_keys.txt").write_text("# local keys\nfile-key-1\nfile-key-2\n", encoding="utf-8")

            with patch.dict("os.environ", {"GEMINI_API_KEY": "", "GEMINI_API_KEYS": "", "GEMMA_API_KEY": "", "GEMMA_API_KEYS": ""}, clear=False):
                self.assertEqual(load_gemma_api_keys(root), ["file-key-1", "file-key-2"])

    def test_load_gemma_api_keys_prefers_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_dir = root / "config" / "api_keys"
            key_dir.mkdir(parents=True)
            (key_dir / "gemma_api_keys.txt").write_text("file-key", encoding="utf-8")

            with patch.dict("os.environ", {"GEMINI_API_KEYS": "env-key-1,env-key-2", "GEMMA_API_KEYS": ""}):
                self.assertEqual(load_gemma_api_keys(root), ["env-key-1", "env-key-2"])

    def test_load_gemma_api_keys_reads_settings_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg_dir = root / "config"
            cfg_dir.mkdir(parents=True)
            (cfg_dir / "settings.env").write_text('GEMINI_API_KEY="settings-key"\n', encoding="utf-8")

            with patch.dict("os.environ", {"GEMINI_API_KEY": "", "GEMINI_API_KEYS": "", "GEMMA_API_KEY": "", "GEMMA_API_KEYS": ""}, clear=False):
                self.assertEqual(load_gemma_api_keys(root), ["settings-key"])

    def test_load_gemma_api_keys_keeps_legacy_gemma_key_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_dir = root / "config" / "api_keys"
            key_dir.mkdir(parents=True)
            (key_dir / "gemma_api_keys.txt").write_text("legacy-key", encoding="utf-8")

            with patch.dict("os.environ", {"GEMINI_API_KEY": "", "GEMINI_API_KEYS": "", "GEMMA_API_KEY": "", "GEMMA_API_KEYS": ""}, clear=False):
                self.assertEqual(load_gemma_api_keys(root), ["legacy-key"])

    def test_gemma_client_builds_datasheet_prompt_for_fixed_model(self) -> None:
        analyzer = GemmaDatasheetAnalyzer(keys=["test-key"])
        self.assertEqual(analyzer.model, GEMMA_MODEL)

        prompt = analyzer._build_prompt("LM358P", 3, "Parameter Min Typ Max\nSupply Voltage 2.7V 5.0V 5.5V")

        self.assertIn("LM358P", prompt)
        self.assertIn("Supply Voltage", prompt)
        self.assertIn("구조화 데이터", prompt)

    def test_gemma_client_builds_question_prompt(self) -> None:
        analyzer = GemmaDatasheetAnalyzer(keys=["test-key"])
        prompt = {}

        def fake_generate(text: str, max_output_tokens: int = 1200, **_kwargs) -> str:
            prompt["text"] = text
            prompt["tokens"] = max_output_tokens
            return "answer"

        analyzer._generate_text = fake_generate  # type: ignore[method-assign]

        self.assertEqual(
            analyzer.answer_question(
                part_title="LM358P",
                question="최대 전압은?",
                context="[Page 3]\nSupply Voltage max 5.5V",
            ),
            "answer",
        )
        self.assertIn("최대 전압", prompt["text"])
        self.assertIn("Supply Voltage max 5.5V", prompt["text"])
        self.assertEqual(prompt["tokens"], 1400)

    def test_gemma_client_ranks_region_candidates_from_json(self) -> None:
        analyzer = GemmaDatasheetAnalyzer(keys=["test-key"])
        prompt = {}

        def fake_generate(text: str, max_output_tokens: int = 1200, **_kwargs) -> str:
            prompt["text"] = text
            prompt["tokens"] = max_output_tokens
            return '{"candidates":[{"id":2,"is_table":true,"type":"electrical_characteristics","confidence":"high","reason":"전압 표"},{"id":1,"is_table":false,"type":"reject","confidence":"low","reason":"본문"}]}'

        analyzer._generate_text = fake_generate  # type: ignore[method-assign]

        ranked = analyzer.rank_region_candidates(
            part_title="LM358P",
            page_number=3,
            candidates=[
                {"id": 1, "box": [0, 0, 100, 40], "score": 0.1, "text": "paragraph", "context": "body"},
                {
                    "id": 2,
                    "box": [0, 50, 300, 120],
                    "score": 0.9,
                    "text": "Supply Voltage 2.7V 5.0V 5.5V",
                    "context": "Electrical Characteristics\nSupply Voltage 2.7V 5.0V 5.5V",
                },
            ],
        )

        self.assertEqual(ranked[0]["id"], 2)
        self.assertTrue(ranked[0]["is_table"])
        self.assertIn("Supply Voltage", prompt["text"])
        self.assertIn("context", prompt["text"])
        self.assertEqual(prompt["tokens"], 1800)

    def test_gemma_client_builds_summary_card_prompt(self) -> None:
        analyzer = GemmaDatasheetAnalyzer(keys=["test-key"])
        prompt = {}

        def fake_generate(text: str, max_output_tokens: int = 1200, **_kwargs) -> str:
            prompt["text"] = text
            prompt["tokens"] = max_output_tokens
            return "## 부품 검토 요약 카드\n- 핵심 정격: 5.5V"

        analyzer._generate_text = fake_generate  # type: ignore[method-assign]

        result = analyzer.summarize_datasheet_regions(
            part_title="LM358P",
            regions=[
                {
                    "page": 3,
                    "kind": "electrical_characteristics",
                    "box": [10, 20, 300, 120],
                    "score": 1.2,
                    "text": "Supply Voltage Min 2.7V Typ 5.0V Max 5.5V",
                }
            ],
        )

        self.assertIn("요약 카드", result)
        self.assertIn("Supply Voltage", prompt["text"])
        self.assertIn("근거 페이지", prompt["text"])
        self.assertEqual(prompt["tokens"], 1800)

    def test_gemma_client_cache_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            analyzer = GemmaDatasheetAnalyzer(keys=["test-key"], cache_dir=Path(tmp))
            key = analyzer._cache_key(["prompt"], 1200, "unit")

            self.assertIsNone(analyzer._read_cache(key))
            self.assertEqual(analyzer._store_cache(key, "cached answer"), "cached answer")
            self.assertEqual(analyzer._read_cache(key), "cached answer")

    def test_minimal_datasheet_region_result_preserves_math_text(self) -> None:
        app = QApplication.instance() or QApplication([])
        with patch.object(DatasheetViewer, "_load_pdf", lambda self: None):
            viewer = DatasheetViewer("https://example.test/test.pdf", "LM358P", "ko")
        try:
            summary = (
                "## 부품 검토 요약 카드\n"
                "- 전원/전류: P = V × I = 5V × 20mA = 100mW\n"
                "- 온도/열: Tj = Ta + P × θJA = 25°C + 0.1W × 100°C/W\n"
                "- 검토 메모: VOUT ≤ VCC - 1.5V"
            )
            with patch.object(viewer, "_show_gemma_message") as mocked_show:
                viewer._show_region_result("summary", summary)

            shown_text = mocked_show.call_args.args[1]
            self.assertIn("P = V × I", shown_text)
            self.assertIn("θJA", shown_text)
            self.assertIn("100°C/W", shown_text)
            self.assertIn("≤", shown_text)
        finally:
            viewer.close()
            app.processEvents()

    def test_gemma_result_dialog_preserves_plain_math_text(self) -> None:
        app = QApplication.instance() or QApplication([])
        parent = QWidget()
        dialog = _GemmaResultDialog(parent, "Gemma", "P = V × I\nθJA ≤ 100°C/W")
        try:
            self.assertEqual(dialog.viewer.toPlainText(), "P = V × I\nθJA ≤ 100°C/W")
        finally:
            dialog.close()
            parent.close()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
