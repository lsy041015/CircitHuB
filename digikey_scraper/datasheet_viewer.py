"""Minimal datasheet PDF viewer with box translate/summarize only."""
from __future__ import annotations

import urllib.request
import os
import shutil
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

try:
    import cv2
    import fitz  # PyMuPDF
    import numpy as np

    from .infrastructure.cv.image_ops import samples_to_bgr as _samples_to_bgr

    _IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - depends on user environment
    cv2 = fitz = np = None
    _samples_to_bgr = None
    _IMPORT_ERROR = exc

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QImage, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .gemma_client import GemmaDatasheetAnalyzer, load_gemma_api_keys

MAX_PDF_DOWNLOAD_BYTES = 100 * 1024 * 1024


def _find_tesseract_cmd() -> str | None:
    env_cmd = os.environ.get("TESSERACT_CMD", "").strip()
    if env_cmd:
        return env_cmd

    found = shutil.which("tesseract")
    if found:
        return found

    if os.name != "nt":
        return None

    roots = [
        os.environ.get("ProgramFiles", ""),
        os.environ.get("ProgramFiles(x86)", ""),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    for root in roots:
        if not root:
            continue
        candidate = Path(root) / "Tesseract-OCR" / "tesseract.exe"
        if candidate.exists():
            return str(candidate)
    return None


def _configure_tesseract(pytesseract_module) -> bool:
    cmd = _find_tesseract_cmd()
    if not cmd:
        return False
    pytesseract_module.pytesseract.tesseract_cmd = cmd
    return True


def _bgr_to_qpixmap(img_bgr: np.ndarray) -> QPixmap:
    rgb = np.ascontiguousarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    h, w, _ch = rgb.shape
    qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())


class _PdfLoader(QThread):
    pdf_ready = Signal(bytes, int, str)
    progress = Signal(int, int)
    error = Signal(str)

    def __init__(self, url: str, dpi: int = 150):
        super().__init__()
        self._url = url
        self._dpi = dpi
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _request_url(self) -> str:
        parsed = urlparse(self._url)
        goto_values = parse_qs(parsed.query).get("gotoUrl")
        if parsed.netloc.endswith("ti.com") and goto_values:
            return unquote(goto_values[0])
        return self._url

    def run(self):
        try:
            if _IMPORT_ERROR is not None:
                raise RuntimeError(f"missing datasheet dependency: {_IMPORT_ERROR}")
            req = urllib.request.Request(
                self._request_url(),
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/pdf,*/*"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                status = getattr(resp, "status", 200) or 200
                content_type = resp.headers.get("Content-Type", "")
                total = int(resp.headers.get("Content-Length") or 0)
                limit_mb = MAX_PDF_DOWNLOAD_BYTES // (1024 * 1024)
                if total > MAX_PDF_DOWNLOAD_BYTES:
                    raise ValueError(f"datasheet too large ({total / (1024 * 1024):.0f} MB > {limit_mb} MB limit)")
                chunks = []
                received = 0
                while True:
                    if self._cancelled:
                        return
                    chunk = resp.read(128 * 1024)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    received += len(chunk)
                    if received > MAX_PDF_DOWNLOAD_BYTES:
                        raise ValueError(f"datasheet exceeds {limit_mb} MB download limit")
                    self.progress.emit(received, total)
                data = b"".join(chunks)
            if not data:
                raise ValueError("empty PDF response")
            if status >= 400:
                raise ValueError(f"HTTP {status} while downloading datasheet")
            if b"%PDF" not in data[:1024]:
                hint = content_type or "unknown content type"
                raise ValueError(f"datasheet response is not a PDF ({hint}, {len(data)} bytes)")
            doc = fitz.open(stream=data, filetype="pdf")
            page_count = doc.page_count
            metadata = doc.metadata or {}
            doc.close()
            if page_count <= 0:
                raise ValueError("PDF has no renderable pages")
            self.pdf_ready.emit(data, page_count, metadata.get("title") or f"{len(data):,} bytes")
        except Exception as exc:
            self.error.emit(str(exc))


class _GemmaRegionWorker(QThread):
    result_ready = Signal(str)
    result_error = Signal(str)

    def __init__(self, mode: str, title: str, page_number: int, region_text: str, image_png: bytes | None):
        super().__init__()
        self._mode = mode
        self._title = title
        self._page_number = page_number
        self._region_text = region_text
        self._image_png = image_png

    def run(self):
        try:
            analyzer = GemmaDatasheetAnalyzer()
            if self._mode == "summary":
                result = analyzer.summarize_region_to_korean(
                    part_title=self._title,
                    page_number=self._page_number,
                    region_text=self._region_text,
                    image_png=self._image_png,
                )
            else:
                result = analyzer.translate_region_to_korean(
                    part_title=self._title,
                    page_number=self._page_number,
                    region_text=self._region_text,
                    image_png=self._image_png,
                )
            self.result_ready.emit(result)
        except Exception as exc:
            self.result_error.emit(str(exc))


class _GemmaResultDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, text: str, warning: bool = False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 540)
        self.setStyleSheet(
            "QDialog { background:#0F1117; }"
            "QLabel { color:#FFFFFF; font-weight:600; }"
            "QTextEdit { color:#FFFFFF; background:#151926; border:1px solid #2D3149; border-radius:8px; padding:10px; font-size:13px; }"
            "QPushButton { color:#FFFFFF; background:#2D3149; border:1px solid #3B425F; border-radius:6px; padding:6px 12px; }"
            "QPushButton:hover { background:#3B425F; }"
        )
        layout = QVBoxLayout(self)
        label = QLabel(("Warning" if warning else title) if getattr(parent, "_lang", "ko") == "en" else ("경고" if warning else title))
        self.viewer = QTextEdit()
        self.viewer.setReadOnly(True)
        self.viewer.setAcceptRichText(False)
        self.viewer.setPlainText(text)
        copy_btn = QPushButton("Copy" if getattr(parent, "_lang", "ko") == "en" else "복사")
        copy_btn.clicked.connect(self._copy)
        save_btn = QPushButton("Save" if getattr(parent, "_lang", "ko") == "en" else "저장")
        save_btn.clicked.connect(self._save)
        close_btn = QPushButton("Close" if getattr(parent, "_lang", "ko") == "en" else "닫기")
        close_btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(copy_btn)
        row.addWidget(save_btn)
        row.addWidget(close_btn)
        layout.addWidget(label)
        layout.addWidget(self.viewer, 1)
        layout.addLayout(row)

    def _copy(self):
        QApplication.clipboard().setText(self.viewer.toPlainText())

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Gemma Result", "gemma_result.txt", "Text files (*.txt);;All files (*.*)")
        if path:
            Path(path).write_text(self.viewer.toPlainText(), encoding="utf-8")


class DatasheetViewer(QDialog):
    def __init__(self, url: str, title: str = "", language: str = "ko", parent=None, ai_chat_service=None):
        super().__init__(parent)
        self._url = url
        self._title = title or "Datasheet"
        self._lang = language if language in {"ko", "en"} else "ko"
        self._pdf_data: bytes | None = None
        self._page_count = 0
        self._current = 0
        self._dpi = 150
        self._doc = None
        self._last_pixmap: QPixmap | None = None
        self._last_display_scale = 1.0
        self._raw_page: np.ndarray | None = None
        self._raw_page_index = -1
        self._selection_mode: str | None = None
        self._selection_start: tuple[int, int] | None = None
        self._selection_start_disp: tuple[int, int] | None = None
        self._selection_region: tuple[int, int, int, int] | None = None
        self._drag_base_pixmap: QPixmap | None = None
        self._gemma_consent = False
        self._ai_chat_service = ai_chat_service

        self.setWindowTitle(f"{'Datasheet' if self._lang == 'en' else '데이터시트'} - {self._title}")
        self.resize(900, 1100)
        self.setMinimumSize(600, 700)
        self._build_ui()
        self._load_pdf()

    def _build_ui(self):
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        toolbar = QFrame()
        toolbar.setStyleSheet(
            "QFrame { background:#1E2130; border-bottom:1px solid #2D3149; }"
            "QLabel { color:#FFFFFF; }"
            "QPushButton { color:#FFFFFF; background:#2D3149; border:1px solid #3B425F; border-radius:6px; padding:3px 8px; }"
            "QPushButton:hover { background:#3B425F; }"
            "QPushButton:checked { background:#3B68F1; border-color:#6B8CFF; }"
            "QPushButton:disabled { color:#8E96AE; background:#24283A; border-color:#343A54; }"
            "QComboBox { color:#FFFFFF; background:#2D3149; border:1px solid #3B425F; border-radius:6px; padding:3px 8px; }"
            "QComboBox QAbstractItemView { color:#FFFFFF; background:#2D3149; selection-background-color:#3B68F1; }"
        )
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(8)

        self._prev_btn = QPushButton("<")
        self._prev_btn.setFixedSize(32, 28)
        self._prev_btn.clicked.connect(self._prev_page)
        self._prev_btn.setEnabled(False)
        self._page_lbl = QLabel("-")
        self._page_lbl.setAlignment(Qt.AlignCenter)
        self._page_lbl.setMinimumWidth(80)
        self._next_btn = QPushButton(">")
        self._next_btn.setFixedSize(32, 28)
        self._next_btn.clicked.connect(self._next_page)
        self._next_btn.setEnabled(False)

        self._zoom_box = QComboBox()
        for item in ("Fit Width", "Fit Page", "75%", "100%", "125%", "150%", "200%"):
            self._zoom_box.addItem(item)
        self._zoom_box.currentIndexChanged.connect(self._refresh_image)

        self._translate_btn = QPushButton("Translate Box" if self._lang == "en" else "영역 번역")
        self._translate_btn.setCheckable(True)
        self._translate_btn.clicked.connect(lambda: self._set_selection_mode("translate"))
        self._summary_btn = QPushButton("Summarize Box" if self._lang == "en" else "영역 요약")
        self._summary_btn.setCheckable(True)
        self._summary_btn.clicked.connect(lambda: self._set_selection_mode("summary"))
        self._gemma_status_lbl = QLabel()
        self._refresh_gemma_status_badge()

        row.addWidget(self._prev_btn)
        row.addWidget(self._page_lbl)
        row.addWidget(self._next_btn)
        row.addSpacing(8)
        row.addWidget(QLabel("Zoom:" if self._lang == "en" else "확대:"))
        row.addWidget(self._zoom_box)
        row.addSpacing(12)
        row.addWidget(self._translate_btn)
        row.addWidget(self._summary_btn)
        row.addStretch()
        row.addWidget(self._gemma_status_lbl)

        self._status = QProgressBar()
        self._status.setRange(0, 0)
        self._status.setFixedHeight(3)
        self._status.setTextVisible(False)
        self._status.setStyleSheet("QProgressBar { background:#1E2130; border:none; } QProgressBar::chunk { background:#3B68F1; }")

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setAlignment(Qt.AlignCenter)
        self._scroll.setStyleSheet("background:#0F1117;")
        self._img_lbl = QLabel()
        self._img_lbl.setAlignment(Qt.AlignCenter)
        self._img_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._img_lbl.setStyleSheet("color:#FFFFFF; font-size:15px; background:#0F1117;")
        self._img_lbl.mousePressEvent = self._on_image_pressed
        self._img_lbl.mouseMoveEvent = self._on_image_dragged
        self._img_lbl.mouseReleaseEvent = self._on_image_released
        self._img_lbl.setMouseTracking(True)
        self._scroll.setWidget(self._img_lbl)

        self._viewer_status_lbl = QLabel("")
        self._viewer_status_lbl.setStyleSheet("color:#FFFFFF; background:#151926; border-top:1px solid #2D3149; padding:5px 10px; font-size:12px;")

        vl.addWidget(toolbar)
        vl.addWidget(self._status)

        if self._ai_chat_service is not None:
            from ._ai_chat_panel import AiChatPanel

            splitter = QSplitter(Qt.Orientation.Vertical)
            splitter.addWidget(self._scroll)
            ai_panel = AiChatPanel(self._ai_chat_service, parent=self)
            ai_panel.set_parts_context([{"title": self._title}])
            ai_panel._new_session_with_mode("datasheet")
            splitter.addWidget(ai_panel)
            splitter.setSizes([700, 300])
            vl.addWidget(splitter, 1)
            self._ai_chat_panel = ai_panel
        else:
            vl.addWidget(self._scroll, 1)

        vl.addWidget(self._viewer_status_lbl)

        QShortcut(QKeySequence(Qt.Key_Left), self, self._prev_page)
        QShortcut(QKeySequence(Qt.Key_Right), self, self._next_page)
        self._img_lbl.setText("Loading datasheet..." if self._lang == "en" else "데이터시트 로딩 중...")

    def _load_pdf(self):
        self._loader = _PdfLoader(self._url, dpi=self._dpi)
        self._loader.pdf_ready.connect(self._on_pdf_ready)
        self._loader.progress.connect(self._on_load_progress)
        self._loader.error.connect(self._on_load_error)
        self._loader.start()

    def _on_load_progress(self, received: int, total: int):
        if total > 0:
            self._status.setRange(0, total)
            self._status.setValue(received)

    def _on_pdf_ready(self, data: bytes, page_count: int, info: str):
        self._close_document()
        self._pdf_data = data
        self._page_count = page_count
        self._status.hide()
        self._current = 0
        self._prev_btn.setEnabled(False)
        self._next_btn.setEnabled(page_count > 1)
        self._img_lbl.setToolTip(info)
        self._refresh_image()

    def _on_load_error(self, msg: str):
        self._status.hide()
        self._img_lbl.setText(f"{'Load failed' if self._lang == 'en' else '로딩 실패'}\n{self._url}\n{msg}")

    def _document(self):
        if self._doc is None:
            self._doc = fitz.open(stream=self._pdf_data, filetype="pdf")
        return self._doc

    def _close_document(self):
        if self._doc is not None:
            try:
                self._doc.close()
            except Exception:
                pass
            self._doc = None

    def _prev_page(self):
        if self._current > 0:
            self._current -= 1
            self._clear_selection()
            self._refresh_image()

    def _next_page(self):
        if self._current < self._page_count - 1:
            self._current += 1
            self._clear_selection()
            self._refresh_image()

    def _render_page(self, index: int) -> np.ndarray:
        if self._raw_page is not None and self._raw_page_index == index:
            return self._raw_page
        scale = self._dpi / 72.0
        pix = self._document().load_page(index).get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        self._raw_page = _samples_to_bgr(pix.samples, pix.height, pix.width, pix.n)
        self._raw_page_index = index
        return self._raw_page

    def _zoom_scale(self, shape: tuple[int, ...]) -> float:
        img_h, img_w = shape[0], shape[1]
        text = self._zoom_box.currentText()
        if text == "Fit Width":
            return max(self._scroll.viewport().width() - 24, 1) / max(img_w, 1)
        if text == "Fit Page":
            width = max(self._scroll.viewport().width() - 24, 1)
            height = max(self._scroll.viewport().height() - 24, 1)
            return min(width / max(img_w, 1), height / max(img_h, 1))
        return int(text.rstrip("%")) / 100.0

    def _refresh_image(self):
        if not self._pdf_data or self._page_count <= 0:
            return
        self._page_lbl.setText(f"{self._current + 1} / {self._page_count}")
        self._prev_btn.setEnabled(self._current > 0)
        self._next_btn.setEnabled(self._current < self._page_count - 1)
        raw = self._render_page(self._current)
        composed = raw.copy()
        if self._selection_region is not None:
            x, y, w, h = self._selection_region
            cv2.rectangle(composed, (x, y), (x + w, y + h), (255, 180, 0), 5)
        scale = self._zoom_scale(composed.shape)
        self._last_display_scale = scale
        if scale != 1.0:
            interp = cv2.INTER_LANCZOS4 if scale > 1.0 else cv2.INTER_AREA
            composed = cv2.resize(composed, (max(int(composed.shape[1] * scale), 1), max(int(composed.shape[0] * scale), 1)), interpolation=interp)
        px = _bgr_to_qpixmap(composed)
        self._last_pixmap = px
        self._img_lbl.clear()
        self._img_lbl.setPixmap(px)
        self._img_lbl.setMinimumSize(px.size())
        self._img_lbl.resize(px.size())
        self._viewer_status_lbl.setText(
            f"Page {self._current + 1}/{self._page_count}  ·  {self._zoom_box.currentText()}"
            if self._lang == "en"
            else f"{self._current + 1}/{self._page_count} 쪽  ·  {self._zoom_box.currentText()}"
        )

    def _set_selection_mode(self, mode: str):
        if self._selection_mode == mode:
            self._selection_mode = None
        else:
            self._selection_mode = mode
        self._translate_btn.setChecked(self._selection_mode == "translate")
        self._summary_btn.setChecked(self._selection_mode == "summary")
        self._selection_start = None
        self._selection_start_disp = None
        self._drag_base_pixmap = None
        if self._selection_mode:
            text = "Drag a box on the page" if self._lang == "en" else "페이지에서 영역을 드래그하세요"
        else:
            text = "Selection mode off" if self._lang == "en" else "영역 선택 모드 꺼짐"
        self._viewer_status_lbl.setText(text)

    def _clear_selection(self):
        self._selection_region = None
        self._selection_start = None
        self._selection_start_disp = None
        self._drag_base_pixmap = None

    def _on_image_pressed(self, event):
        if event.button() != Qt.LeftButton or self._selection_mode is None or not self._pdf_data:
            return
        self._selection_start = self._image_event_point(event)
        self._selection_start_disp = (int(event.pos().x()), int(event.pos().y()))
        self._selection_region = (*self._selection_start, 1, 1)
        self._drag_base_pixmap = self._last_pixmap.copy() if self._last_pixmap is not None else None
        event.accept()

    def _on_image_dragged(self, event):
        if self._selection_mode is None or self._selection_start is None:
            return
        self._selection_region = self._normalized_region(self._selection_start, self._image_event_point(event))
        base = self._drag_base_pixmap
        if base is None or self._selection_start_disp is None:
            return
        dx0, dy0 = self._selection_start_disp
        dx1, dy1 = int(event.pos().x()), int(event.pos().y())
        preview = base.copy()
        painter = QPainter(preview)
        painter.setPen(QPen(QColor(255, 180, 0), 2))
        painter.drawRect(min(dx0, dx1), min(dy0, dy1), abs(dx1 - dx0), abs(dy1 - dy0))
        painter.end()
        self._img_lbl.setPixmap(preview)
        event.accept()

    def _on_image_released(self, event):
        if event.button() != Qt.LeftButton or self._selection_mode is None or self._selection_start is None:
            return
        mode = self._selection_mode
        region = self._normalized_region(self._selection_start, self._image_event_point(event))
        self._selection_start = None
        self._selection_start_disp = None
        self._drag_base_pixmap = None
        if region[2] < 20 or region[3] < 20:
            self._selection_region = None
            self._refresh_image()
            return
        self._selection_region = region
        self._selection_mode = None
        self._translate_btn.setChecked(False)
        self._summary_btn.setChecked(False)
        self._refresh_image()
        self._run_region_action(mode, region)
        event.accept()

    def _image_event_point(self, event) -> tuple[int, int]:
        scale = self._last_display_scale or 1.0
        raw = self._render_page(self._current)
        x = max(0, min(int(event.pos().x() / scale), raw.shape[1] - 1))
        y = max(0, min(int(event.pos().y() / scale), raw.shape[0] - 1))
        return x, y

    def _normalized_region(self, start: tuple[int, int], end: tuple[int, int]) -> tuple[int, int, int, int]:
        x0, y0 = start
        x1, y1 = end
        x, y = min(x0, x1), min(y0, y1)
        return x, y, abs(x1 - x0), abs(y1 - y0)

    def _run_region_action(self, mode: str, region: tuple[int, int, int, int]):
        if not self._ensure_gemma_consent():
            return
        text = self._extract_region_pdf_text(region)
        if not text.strip():
            text = self._ocr_region_text(region)
        image_png = self._encode_region_png(region)
        self._set_busy(True, mode)
        self._region_worker = _GemmaRegionWorker(mode, self._title, self._current + 1, text, image_png)
        self._region_worker.result_ready.connect(lambda result: self._show_region_result(mode, result))
        self._region_worker.result_error.connect(lambda message: self._show_gemma_message("Gemini", message, warning=True))
        self._region_worker.finished.connect(lambda: self._set_busy(False, mode))
        self._region_worker.start()

    def _extract_region_pdf_text(self, region: tuple[int, int, int, int]) -> str:
        scale = self._dpi / 72.0
        x, y, w, h = region
        rect = fitz.Rect(x / scale, y / scale, (x + w) / scale, (y + h) / scale)
        words = self._document().load_page(self._current).get_text("words")
        rows = []
        for word in words:
            word_rect = fitz.Rect(word[:4])
            if word_rect.intersects(rect):
                rows.append((word_rect.y0, word_rect.x0, str(word[4])))
        if not rows:
            return ""
        rows.sort()
        line_height = max(1.0, float(np.median([abs(rows[idx][0] - rows[idx - 1][0]) for idx in range(1, len(rows))] or [8.0])))
        lines: list[tuple[float, list[tuple[float, str]]]] = []
        for y0, x0, text in rows:
            if lines and abs(y0 - lines[-1][0]) <= line_height * 0.6:
                lines[-1][1].append((x0, text))
            else:
                lines.append((y0, [(x0, text)]))
        return "\n".join(" ".join(text for _x0, text in sorted(line)) for _y0, line in lines)

    def _ocr_region_text(self, region: tuple[int, int, int, int]) -> str:
        try:
            import pytesseract  # type: ignore
        except Exception:
            return ""
        _configure_tesseract(pytesseract)
        crop = self._crop_region_bgr(region)
        if crop is None or crop.size == 0:
            return ""
        try:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
            gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
            return str(pytesseract.image_to_string(gray, lang="eng")).strip()
        except Exception:
            return ""

    def _crop_region_bgr(self, region: tuple[int, int, int, int]) -> np.ndarray | None:
        raw = self._render_page(self._current)
        x, y, w, h = region
        x = max(0, min(x, raw.shape[1] - 1))
        y = max(0, min(y, raw.shape[0] - 1))
        w = max(1, min(w, raw.shape[1] - x))
        h = max(1, min(h, raw.shape[0] - y))
        return raw[y:y + h, x:x + w]

    def _encode_region_png(self, region: tuple[int, int, int, int]) -> bytes | None:
        crop = self._crop_region_bgr(region)
        if crop is None or crop.size == 0:
            return None
        ok, encoded = cv2.imencode(".png", crop)
        return encoded.tobytes() if ok else None

    def _ensure_gemma_consent(self) -> bool:
        if self._gemma_consent:
            return True
        if self._lang == "ko":
            title = "AI 클라우드 전송 동의"
            body = "선택 영역의 텍스트와 이미지가 Google Gemini API로 전송됩니다.\n\n기밀/NDA 문서는 주의하세요. 계속할까요?"
        else:
            title = "AI cloud upload consent"
            body = "The selected region text and image will be uploaded to Google's Gemini API.\n\nBe careful with confidential/NDA documents. Continue?"
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(body)
        box.setIcon(QMessageBox.Warning)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        box.setStyleSheet(
            "QMessageBox { background:#0F1117; }"
            "QMessageBox QLabel { color:#FFFFFF; }"
            "QMessageBox QPushButton { color:#FFFFFF; background:#2D3149; border:1px solid #3B425F; border-radius:6px; padding:6px 14px; min-width:72px; }"
            "QMessageBox QPushButton:hover { background:#3B425F; }"
        )
        reply = box.exec()
        if reply != QMessageBox.Yes:
            return False
        self._gemma_consent = True
        return True

    def _set_busy(self, busy: bool, mode: str):
        self._translate_btn.setEnabled(not busy)
        self._summary_btn.setEnabled(not busy)
        if busy:
            self._viewer_status_lbl.setText(
                "Translating selected region..." if mode == "translate" and self._lang == "en"
                else "선택 영역 번역 중..." if mode == "translate"
                else "Summarizing selected region..." if self._lang == "en"
                else "선택 영역 요약 중..."
            )

    def _show_region_result(self, mode: str, text: str):
        title = (
            "Gemini Translation" if mode == "translate" and self._lang == "en"
            else "Gemini 영역 번역" if mode == "translate"
            else "Gemini Summary" if self._lang == "en"
            else "Gemini 영역 요약"
        )
        self._show_gemma_message(title, text, warning=False)

    def _show_gemma_message(self, title: str, text: str, warning: bool = False):
        dialog = _GemmaResultDialog(self, title, text, warning)
        dialog.exec()

    def _refresh_gemma_status_badge(self):
        ready = bool(load_gemma_api_keys())
        self._gemma_status_lbl.setText("Gemini: ready" if ready and self._lang == "en" else "Gemini: 준비" if ready else "Gemini: key" if self._lang == "en" else "Gemini: 키 없음")
        color = "#22C55E" if ready else "#F59E0B"
        self._gemma_status_lbl.setStyleSheet(f"color:#FFFFFF; border:1px solid {color}; border-radius:5px; padding:2px 6px; font-size:11px;")

    @staticmethod
    def _stop_worker(worker, grace_ms: int = 3000):
        if worker is None or not worker.isRunning():
            return
        try:
            worker.blockSignals(True)
            worker.requestInterruption()
            worker.quit()
            if not worker.wait(grace_ms):
                worker.wait()
        except Exception:
            pass

    def closeEvent(self, event):
        loader = getattr(self, "_loader", None)
        if loader is not None and loader.isRunning():
            loader.cancel()
            if not loader.wait(3000):
                loader.wait()
        self._stop_worker(getattr(self, "_region_worker", None))
        self._close_document()
        event.accept()
        self.deleteLater()


def open_datasheet(url: str, title: str = "", language: str = "ko", parent=None):
    dlg = DatasheetViewer(url, title, language, parent)
    dlg.show()
    return dlg
