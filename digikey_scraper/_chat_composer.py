"""Message composer widgets extracted from _circuitkit_chat_design.py.

Holds ComposerTextEdit (Enter-to-send text area) and ComposerWidget (the full
composer with formatting toolbar, part-share popup, file/emoji/mention menus).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ._chat_data import SHARE_PARTS


class ComposerTextEdit(QTextEdit):
    message_submitted = Signal()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if not (event.modifiers() & Qt.ShiftModifier):
                self.message_submitted.emit()
                return
        super().keyPressEvent(event)


class ComposerWidget(QFrame):
    message_sent = Signal(str, object)   # text, {"parts": [...], "files": [...]}

    def __init__(self, channel_name='', parent=None):
        super().__init__(parent)
        self.channel_name = channel_name
        self.attached = []
        self.attached_files = []
        self.mention_names = []
        self.share_open = False
        self._build()

    def _build(self):
        self.setObjectName('composer')
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 서식 툴바
        toolbar = QFrame()
        toolbar.setObjectName('composer_toolbar')
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(8, 6, 8, 6)
        tl.setSpacing(1)
        for sym, tip, width in [('B','굵게',28), ('I','기울임',28), ('{}','코드',34), ('목록','목록',40), ('링크','링크',40)]:
            b = QPushButton(sym)
            b.setFixedSize(width, 28)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("QPushButton{border:none;background:transparent;color:#475569;"
                            "border-radius:6px;font-size:12px;font-weight:600;padding:0 6px;}"
                            "QPushButton:hover{background:#F4F5F7;color:#0F172A;}")
            b.clicked.connect(lambda _checked=False, kind=sym: self._apply_format(kind))
            tl.addWidget(b)
            if sym == '{}':
                sep = QFrame(); sep.setFrameShape(QFrame.VLine)
                sep.setFixedSize(1, 18)
                sep.setStyleSheet("background:#EDF0F3;")
                tl.addWidget(sep)
        tl.addStretch()
        root.addWidget(toolbar)

        # 첨부 부품 영역
        self.attach_area = QWidget()
        self.attach_area.setVisible(False)
        self.attach_layout = QHBoxLayout(self.attach_area)
        self.attach_layout.setContentsMargins(12, 8, 12, 0)
        self.attach_layout.setSpacing(8)
        self.attach_layout.setAlignment(Qt.AlignLeft)
        root.addWidget(self.attach_area)

        # 부품 공유 팝업 (숨김 상태)
        self.share_popup = QFrame(self)
        self.share_popup.setObjectName('share_popup')
        self.share_popup.setVisible(False)
        self.share_popup.setMinimumWidth(420)
        self.share_popup.setMaximumWidth(560)
        self.share_popup.setStyleSheet("""
            QFrame#share_popup{background:white;border:1px solid #E4E7EC;
                border-radius:10px;}
        """)
        sp_layout = QVBoxLayout(self.share_popup)
        sp_layout.setContentsMargins(10, 10, 10, 10)
        sp_layout.setSpacing(6)
        title = QLabel('검색 결과에서 부품 공유')
        title.setStyleSheet("font-size:11px;font-weight:600;color:#94A3B8;"
                            "padding:6px 8px 4px;")
        sp_layout.addWidget(title)
        for p in SHARE_PARTS:
            row = QFrame()
            row.setCursor(Qt.PointingHandCursor)
            row.setStyleSheet("QFrame{border-radius:7px;background:transparent;}"
                              "QFrame:hover{background:#F4F5F7;}")
            row.setMinimumHeight(54)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(10, 9, 10, 9)
            rl.setSpacing(12)
            icon = QLabel('IC')
            icon.setFixedSize(36, 36)
            icon.setAlignment(Qt.AlignCenter)
            icon.setStyleSheet("background:#EEF4FF;color:#2952D6;border-radius:8px;font-size:16px;")
            rl.addWidget(icon)
            info = QVBoxLayout(); info.setSpacing(1)
            info.addWidget(QLabel(p['name'], styleSheet="font-size:13px;font-weight:600;"
                                  "font-family:'Consolas',monospace;color:#0F172A;"))
            info.addWidget(QLabel(p['sub'], styleSheet="font-size:11px;color:#94A3B8;"))
            rl.addLayout(info, 1)
            rl.addWidget(QLabel(p['price'], styleSheet="font-family:'Consolas',monospace;"
                                "font-size:12px;font-weight:600;color:#475569;"))
            part_copy = dict(p)
            row.mousePressEvent = lambda e, pc=part_copy: self._attach_part(pc)
            sp_layout.addWidget(row)

        # 텍스트 입력
        self.text_edit = ComposerTextEdit()
        self.text_edit.setObjectName('composer_textarea')
        self.text_edit.setPlaceholderText(f'#{self.channel_name} 에 메시지 보내기')
        self.text_edit.setFixedHeight(48)
        self.text_edit.message_submitted.connect(self._send)
        self.text_edit.textChanged.connect(self._auto_grow)
        root.addWidget(self.text_edit)

        # 하단 툴바
        foot = QWidget()
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(8, 6, 8, 8)
        fl.setSpacing(6)

        attach_btn = QPushButton('첨부')
        attach_btn.setFixedSize(40, 30)
        attach_btn.setToolTip('파일 첨부')
        attach_btn.setStyleSheet("QPushButton{border:none;background:transparent;color:#475569;"
                                 "border-radius:7px;font-size:11px;font-weight:600;padding:0 6px;}"
                                 "QPushButton:hover{background:#F4F5F7;}")
        attach_btn.setCursor(Qt.PointingHandCursor)
        attach_btn.clicked.connect(self._pick_files)
        fl.addWidget(attach_btn)

        self.chip_btn = QPushButton('부품')
        self.chip_btn.setFixedSize(40, 30)
        self.chip_btn.setToolTip('부품 공유')
        self.chip_btn.setStyleSheet("QPushButton{border:none;background:transparent;color:#475569;"
                                    "border-radius:7px;font-size:11px;font-weight:600;padding:0 6px;}"
                                    "QPushButton:hover{background:#F4F5F7;}")
        self.chip_btn.setCursor(Qt.PointingHandCursor)
        self.chip_btn.clicked.connect(self._toggle_share)
        fl.addWidget(self.chip_btn)

        emoji_btn = QPushButton('이모')
        emoji_btn.setFixedSize(40, 30)
        emoji_btn.setStyleSheet("QPushButton{border:none;background:transparent;border-radius:7px;"
                                "font-size:11px;font-weight:600;padding:0 6px;}"
                                "QPushButton:hover{background:#F4F5F7;}")
        emoji_btn.setCursor(Qt.PointingHandCursor)
        emoji_btn.clicked.connect(self._show_emoji_menu)
        fl.addWidget(emoji_btn)

        at_btn = QPushButton('@')
        at_btn.setFixedSize(34, 30)
        at_btn.setStyleSheet("QPushButton{border:none;background:transparent;color:#475569;"
                             "border-radius:7px;font-size:15px;font-weight:700;padding:0 4px;}"
                             "QPushButton:hover{background:#F4F5F7;}")
        at_btn.setCursor(Qt.PointingHandCursor)
        at_btn.clicked.connect(self._show_mention_menu)
        fl.addWidget(at_btn)

        hint = QLabel('  Enter 전송 · Shift+Enter 줄바꿈')
        hint.setStyleSheet("color:#94A3B8;font-size:11px;")
        fl.addWidget(hint)
        fl.addStretch()

        self.send_btn = QPushButton('보내기')
        self.send_btn.setFixedHeight(30)
        self.send_btn.setFixedWidth(86)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self._send)
        fl.addWidget(self.send_btn)

        root.addWidget(foot)
        self._auto_grow()

    def _auto_grow(self):
        doc_height = self.text_edit.document().size().height()
        new_h = min(max(int(doc_height) + 20, 48), 160)
        self.text_edit.setFixedHeight(new_h)
        has_content = (
            bool(self.text_edit.toPlainText().strip())
            or bool(self.attached)
            or bool(self.attached_files)
        )
        self.send_btn.setEnabled(has_content)
        self.send_btn.setStyleSheet(
            "QPushButton{background:#3B68F1;border:1px solid #2952D6;border-radius:8px;"
            "color:white;font-size:13px;font-weight:600;padding:0 12px;}"
            "QPushButton:hover{background:#2952D6;}"
            if has_content else
            "QPushButton{background:#EEF0F3;border:1px solid #E4E7EC;border-radius:8px;"
            "color:#94A3B8;font-size:13px;padding:0 12px;}"
        )

    def _toggle_share(self):
        self.share_open = not self.share_open
        if self.share_open:
            self.share_popup.setParent(self.window())
            hint = self.share_popup.sizeHint()
            width = max(420, min(560, hint.width()))
            height = max(260, hint.height())
            self.share_popup.resize(width, height)
            anchor = self.chip_btn.mapTo(self.window(), QPoint(0, 0))
            x = max(12, min(anchor.x(), self.window().width() - width - 12))
            y = max(12, anchor.y() - height - 10)
            self.share_popup.move(x, y)
            self.share_popup.raise_()
            self.share_popup.setVisible(True)
            self.chip_btn.setStyleSheet("QPushButton{border:none;background:#EEF4FF;color:#2952D6;"
                                        "border-radius:7px;font-size:11px;font-weight:700;padding:0 6px;}")
        else:
            self.share_popup.setVisible(False)
            self.chip_btn.setStyleSheet("QPushButton{border:none;background:transparent;color:#475569;"
                                        "border-radius:7px;font-size:11px;font-weight:600;padding:0 6px;}"
                                        "QPushButton:hover{background:#F4F5F7;}")

    def _attach_part(self, part):
        if any(a['name'] == part['name'] for a in self.attached):
            self.share_popup.setVisible(False)
            self.share_open = False
            return
        self.attached.append(part)
        self._rebuild_attachments()
        self.share_popup.setVisible(False)
        self.share_open = False
        self.chip_btn.setStyleSheet("QPushButton{border:none;background:transparent;color:#475569;"
                                    "border-radius:7px;font-size:11px;font-weight:600;padding:0 6px;}"
                                    "QPushButton:hover{background:#F4F5F7;}")
        self._auto_grow()

    def _apply_format(self, kind):
        cursor = self.text_edit.textCursor()
        selected = cursor.selectedText().replace("\u2029", "\n")
        text = selected or "텍스트"
        if kind == 'B':
            value = f"**{text}**"
        elif kind == 'I':
            value = f"*{text}*"
        elif kind == '{}':
            value = f"`{text}`"
        elif kind == '목록':
            value = "\n".join(f"- {line}" for line in text.splitlines() or ["텍스트"])
        elif kind == '링크':
            from PySide6.QtWidgets import QInputDialog
            url, ok = QInputDialog.getText(self, "링크 삽입", "URL:", text="https://")
            if not ok:
                return
            value = f"[{text}]({url})"
        else:
            value = text
        cursor.insertText(value)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.setFocus()
        self._auto_grow()

    def _pick_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "파일 첨부")
        for path in paths:
            p = Path(path)
            if not p.exists() or any(item["path"] == str(p) for item in self.attached_files):
                continue
            size = p.stat().st_size
            self.attached_files.append({
                "name": p.name,
                "path": str(p),
                "size": size,
                "meta": self._format_size(size),
            })
        self._rebuild_attachments()
        self._auto_grow()

    def _show_emoji_menu(self):
        menu = QMenu(self)
        for emoji in ["👍", "✅", "👀", "🔧", "📌", "⚠"]:
            menu.addAction(emoji, lambda e=emoji: self._insert_text(e))
        menu.exec(self.mapToGlobal(QPoint(8, self.height() - 38)))

    def _show_mention_menu(self):
        menu = QMenu(self)
        names = self.mention_names or ["서현", "민결", "윤재", "하린"]
        for name in names:
            menu.addAction(name, lambda n=name: self._insert_text(f"@{n} "))
        menu.exec(self.mapToGlobal(QPoint(8, self.height() - 38)))

    def _insert_text(self, text):
        cursor = self.text_edit.textCursor()
        cursor.insertText(text)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.setFocus()
        self._auto_grow()

    def _format_size(self, size):
        if size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        if size >= 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size} B"

    def _rebuild_attachments(self):
        while self.attach_layout.count():
            item = self.attach_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for p in self.attached:
            chip = QFrame()
            chip.setStyleSheet("QFrame{background:#F4F5F7;border:1px solid #E4E7EC;border-radius:8px;}")
            cl = QHBoxLayout(chip)
            cl.setContentsMargins(10, 6, 6, 6)
            cl.setSpacing(8)
            cl.addWidget(QLabel('IC', styleSheet="color:#2952D6;font-size:12px;font-weight:700;"))
            cl.addWidget(QLabel(p['name'], styleSheet="font-family:'Consolas',monospace;"
                                "font-weight:600;font-size:12px;color:#0F172A;"))
            cl.addWidget(QLabel(p['price'], styleSheet="color:#94A3B8;font-size:12px;"))
            x_btn = QPushButton('✕')
            x_btn.setFixedSize(18, 18)
            x_btn.setCursor(Qt.PointingHandCursor)
            x_btn.setStyleSheet("QPushButton{border:none;background:transparent;color:#94A3B8;"
                                "border-radius:9px;font-size:10px;}"
                                "QPushButton:hover{background:#E4E7EC;color:#0F172A;}")
            part_name = p['name']
            x_btn.clicked.connect(lambda _, n=part_name: self._remove_attach(n))
            cl.addWidget(x_btn)
            self.attach_layout.addWidget(chip)
        for f in self.attached_files:
            chip = QFrame()
            chip.setStyleSheet("QFrame{background:#FFF7ED;border:1px solid #FED7AA;border-radius:8px;}")
            cl = QHBoxLayout(chip)
            cl.setContentsMargins(10, 6, 6, 6)
            cl.setSpacing(8)
            cl.addWidget(QLabel('FILE', styleSheet="color:#C2410C;font-size:11px;font-weight:800;"))
            cl.addWidget(QLabel(f['name'], styleSheet="font-weight:600;font-size:12px;color:#0F172A;"))
            cl.addWidget(QLabel(f['meta'], styleSheet="color:#94A3B8;font-size:12px;"))
            x_btn = QPushButton('✕')
            x_btn.setFixedSize(18, 18)
            x_btn.setCursor(Qt.PointingHandCursor)
            x_btn.setStyleSheet("QPushButton{border:none;background:transparent;color:#94A3B8;"
                                "border-radius:9px;font-size:10px;}"
                                "QPushButton:hover{background:#FED7AA;color:#0F172A;}")
            file_path = f['path']
            x_btn.clicked.connect(lambda _, p=file_path: self._remove_file_attach(p))
            cl.addWidget(x_btn)
            self.attach_layout.addWidget(chip)
        self.attach_area.setVisible(bool(self.attached or self.attached_files))

    def _remove_attach(self, name):
        self.attached = [a for a in self.attached if a['name'] != name]
        self._rebuild_attachments()
        self._auto_grow()

    def _remove_file_attach(self, path):
        self.attached_files = [a for a in self.attached_files if a['path'] != path]
        self._rebuild_attachments()
        self._auto_grow()

    def attach_part_by_name(self, name):
        clean = str(name or "").strip().upper()
        if not clean:
            return
        part = next((dict(p) for p in SHARE_PARTS if p["name"].upper() == clean), None)
        if part is None:
            part = {"name": clean, "sub": "DigiKey search result", "price": "조회 결과"}
        self._attach_part(part)

    def _send(self):
        text = self.text_edit.toPlainText().strip()
        if not text and not self.attached and not self.attached_files:
            return
        self.message_sent.emit(text, {"parts": self.attached[:], "files": self.attached_files[:]})
        self.text_edit.clear()
        self.attached.clear()
        self.attached_files.clear()
        self._rebuild_attachments()
        self.text_edit.setFixedHeight(48)
        self._auto_grow()
