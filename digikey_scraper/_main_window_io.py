from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFileDialog, QMessageBox

from ._helpers import split_part_tokens
from .sharing import build_share_filename


class MainWindowIoMixin:
    def import_bom(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._tr("import_bom_dialog_title"),
            "",
            "Text/CSV files (*.txt *.csv *.tsv);;All files (*.*)",
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = Path(path).read_text(encoding="cp949", errors="ignore")
        imported_parts: list[dict[str, int | str]] = []
        for token in split_part_tokens(text):
            clean = token.strip().upper()
            if not re.search(r"[A-Z0-9]", clean):
                continue
            for part in imported_parts:
                if part["name"] == clean:
                    part["qty"] = int(part["qty"]) + 1
                    break
            else:
                imported_parts.append({"name": clean, "qty": 1})

        self.parts = imported_parts
        self.results = []
        self._query_times = []
        self.latest_share_text = ""
        self.render_chips()
        self.render_results()
        self._update_run_button()
        self._update_statusbar()
        self.set_status(self._tr("bom_loaded_status", name=Path(path).name))
        self.save_settings()

    def _auto_save_results(self) -> Path | None:
        text = self.latest_share_text.strip()
        if not text:
            return None
        self.auto_save_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.auto_save_dir / f"digikey_results_{timestamp}.txt"
        path.write_text(text, encoding="utf-8")
        return path

    def get_result_text(self) -> str:
        return self.latest_share_text.strip()

    def copy_text(self, text: str):
        if text:
            QGuiApplication.clipboard().setText(text)
            self.set_status(self._tr("copied_status"))

    def save_results_as(self):
        text = self.get_result_text()
        if not text:
            QMessageBox.warning(self, self._tr("no_save_title"), self._tr("no_save_message"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            self._tr("save_dialog_title"),
            build_share_filename(),
            "Text files (*.txt);;All files (*.*)",
        )
        if not path:
            return
        Path(path).write_text(text, encoding="utf-8")
        self.set_status(self._tr("saved_status", path=path))
