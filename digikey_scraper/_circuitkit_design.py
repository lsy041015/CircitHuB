"""
CircuitKit — DigiKey 부품 정보 조회기 (PySide6 버전)
실행: python circuitkit.py
요구사항: pip install PySide6
"""

import sys
import webbrowser
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame, QSizePolicy,
    QStackedWidget, QSpinBox, QCheckBox, QGridLayout, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, QTimer, QSize, Signal, QRect, QPoint, QMimeData
from PySide6.QtGui import QColor, QFont, QPainter, QLinearGradient, QBrush, QClipboard

from ._circuitkit_chat_design import CircuitKitChatWindow

# ─────────────────────────────────────────────
#  FlowLayout  (Qt에 없어서 직접 구현)
# ─────────────────────────────────────────────
from PySide6.QtWidgets import QLayout

class FlowLayout(QLayout):
    def __init__(self, parent=None, h_spacing=7, v_spacing=7):
        super().__init__(parent)
        self._items = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test):
        m = self.contentsMargins()
        eff_rect = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y = eff_rect.x(), eff_rect.y()
        line_height = 0
        row_items = []

        for item in self._items:
            wid = item.widget()
            sw = item.sizeHint().width()
            sh = item.sizeHint().height()

            next_x = x + sw + self._h_spacing
            if next_x - self._h_spacing > eff_rect.right() and line_height > 0:
                x = eff_rect.x()
                y = y + line_height + self._v_spacing
                line_height = 0

            if not test:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = x + sw + self._h_spacing
            line_height = max(line_height, sh)

        return y + line_height - rect.y() + m.bottom()


# ─────────────────────────────────────────────
#  데이터
# ─────────────────────────────────────────────
MOCK_PARTS = {
    'LM358P': {
        'name': 'LM358P', 'digikey': '296-1395-5-ND',
        'manufacturer': 'Texas Instruments',
        'description': 'Op Amp, Dual, GP, 8-DIP',
        'detailUrl': 'https://www.digikey.com/en/products/detail/texas-instruments/LM358P/277042',
        'datasheetUrl': 'https://www.ti.com/lit/ds/symlink/lm358.pdf',
        'mountingType': 'Through Hole', 'package': 'PDIP-8', 'status': 'Active',
        'stock': 47892, 'operatingTemp': '0°C ~ 70°C', 'supplyVoltage': '3V ~ 32V',
        'prices': [
            {'qty': 1,    'unit': 0.2700, 'ext': 0.27},
            {'qty': 10,   'unit': 0.1870, 'ext': 1.87},
            {'qty': 50,   'unit': 0.1530, 'ext': 7.65},
            {'qty': 100,  'unit': 0.1423, 'ext': 14.23},
            {'qty': 250,  'unit': 0.1310, 'ext': 32.76},
            {'qty': 500,  'unit': 0.1243, 'ext': 62.13},
            {'qty': 1000, 'unit': 0.1187, 'ext': 118.68},
        ],
    },
    'TL072CP': {
        'name': 'TL072CP', 'digikey': '296-1775-5-ND',
        'manufacturer': 'Texas Instruments',
        'description': 'Op Amp, Dual, JFET, Low Noise, 8-DIP',
        'detailUrl': 'https://www.digikey.com/en/products/detail/texas-instruments/TL072CP/277421',
        'datasheetUrl': 'https://www.ti.com/lit/ds/symlink/tl072.pdf',
        'mountingType': 'Through Hole', 'package': 'PDIP-8', 'status': 'Active',
        'stock': 28547, 'operatingTemp': '0°C ~ 70°C', 'supplyVoltage': '±3.5V ~ ±18V',
        'prices': [
            {'qty': 1,    'unit': 1.0400, 'ext': 1.04},
            {'qty': 10,   'unit': 0.7490, 'ext': 7.49},
            {'qty': 50,   'unit': 0.6324, 'ext': 31.62},
            {'qty': 100,  'unit': 0.5963, 'ext': 59.63},
            {'qty': 250,  'unit': 0.5582, 'ext': 139.55},
            {'qty': 500,  'unit': 0.5352, 'ext': 267.59},
            {'qty': 1000, 'unit': 0.5163, 'ext': 516.25},
        ],
    },
    'NE5532P': {
        'name': 'NE5532P', 'digikey': '497-1639-5-ND',
        'manufacturer': 'STMicroelectronics',
        'description': 'Op Amp, Dual, Low Noise Audio, 8-DIP',
        'detailUrl': 'https://www.digikey.com/en/products/detail/stmicroelectronics/NE5532P/588510',
        'datasheetUrl': 'https://www.st.com/resource/en/datasheet/ne5532.pdf',
        'mountingType': 'Through Hole', 'package': 'PDIP-8', 'status': 'Active',
        'stock': 12340, 'operatingTemp': '0°C ~ 70°C', 'supplyVoltage': '±3V ~ ±20V',
        'prices': [
            {'qty': 1,    'unit': 0.8500, 'ext': 0.85},
            {'qty': 10,   'unit': 0.6120, 'ext': 6.12},
            {'qty': 50,   'unit': 0.5184, 'ext': 25.92},
            {'qty': 100,  'unit': 0.4842, 'ext': 48.42},
            {'qty': 250,  'unit': 0.4478, 'ext': 111.96},
            {'qty': 500,  'unit': 0.4282, 'ext': 214.08},
            {'qty': 1000, 'unit': 0.4052, 'ext': 405.20},
        ],
    },
}

HISTORY_DATA = [
    {'id': 'h1', 'label': 'LM358P, TL072CP, NE5532P', 'time': '방금',    'status': 'success'},
    {'id': 'h2', 'label': 'STM32F103C8T6',             'time': '14분 전', 'status': 'success'},
    {'id': 'h3', 'label': 'ATmega328P-PU',             'time': '1시간 전','status': 'success'},
    {'id': 'h4', 'label': '10kΩ 저항 5종',             'time': '어제',    'status': 'success'},
    {'id': 'h5', 'label': 'ESP32-WROOM-32',            'time': '어제',    'status': 'warning'},
    {'id': 'h6', 'label': 'CD4017BE, 74HC595N',        'time': '11월 6일','status': 'success'},
]

FAVORITES_DATA = [
    {'id': 'f1', 'label': 'LM358P',         'meta': '$0.27'},
    {'id': 'f2', 'label': 'ESP32-WROOM-32', 'meta': '$3.10'},
    {'id': 'f3', 'label': 'ATmega328P-PU',  'meta': '$2.06'},
    {'id': 'f4', 'label': 'STM32F103C8T6',  'meta': '$4.85'},
]

STATUS_DOT_COLORS = {'success': '#10B981', 'warning': '#F59E0B', 'error': '#EF4444'}


def fmt_usd(n):
    return f'${n:.4f}' if n < 1 else f'${n:.2f}'


# ─────────────────────────────────────────────
#  칩 위젯
# ─────────────────────────────────────────────
class ChipWidget(QFrame):
    removed = Signal(str)

    def __init__(self, name, qty=1, parent=None):
        super().__init__(parent)
        self.part_name = name
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 4, 0)
        layout.setSpacing(4)

        lbl = QLabel(name)
        lbl.setStyleSheet("color:#1E3FAF; font-weight:600; font-size:13px; font-family:'Consolas','Courier New',monospace;")
        layout.addWidget(lbl)

        if qty > 1:
            q = QLabel(f'×{qty}')
            q.setStyleSheet("background:rgba(59,104,241,0.15); color:#1E3FAF; border-radius:9px;"
                            " padding:0 5px; font-size:11px; font-weight:600;")
            layout.addWidget(q)

        x_btn = QPushButton('✕')
        x_btn.setFixedSize(20, 20)
        x_btn.setCursor(Qt.PointingHandCursor)
        x_btn.setStyleSheet("QPushButton{border:none;background:transparent;color:#1E3FAF;"
                            "border-radius:10px;font-size:11px;}"
                            "QPushButton:hover{background:rgba(59,104,241,0.18);}")
        x_btn.clicked.connect(lambda: self.removed.emit(name))
        layout.addWidget(x_btn)

        self.setFixedHeight(28)
        self.setStyleSheet("QFrame{background:#EEF4FF;border:1px solid #D5E0FF;border-radius:14px;}")

    def sizeHint(self):
        return super().sizeHint()


# ─────────────────────────────────────────────
#  칩 입력 영역
# ─────────────────────────────────────────────
class ChipInputArea(QWidget):
    partsChanged = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parts = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 8)
        outer.setSpacing(8)

        # 칩들이 들어갈 FlowLayout 컨테이너
        self.flow_container = QWidget()
        self.flow = FlowLayout(self.flow_container, h_spacing=7, v_spacing=7)
        outer.addWidget(self.flow_container)

        # 입력창
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText('예: LM358P, TL072CP, NE5532P')
        self.input_field.setFixedHeight(28)
        self.input_field.setStyleSheet(
            "QLineEdit{border:none;background:transparent;font-size:13px;"
            "font-family:'Consolas','Courier New',monospace;color:#0F172A;}"
        )
        self.input_field.returnPressed.connect(self._commit)
        self.input_field.installEventFilter(self)
        outer.addWidget(self.input_field)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self.input_field and event.type() == QEvent.KeyPress:
            key = event.key()
            txt = self.input_field.text()
            if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                if txt.strip():
                    self._commit()
                return True
            if key == Qt.Key_Backspace and not txt and self.parts:
                self.remove_part(self.parts[-1]['name'])
                return True
        return super().eventFilter(obj, event)

    def _commit(self):
        raw = self.input_field.text()
        tokens = [t.strip().upper() for t in raw.replace(';', ',').replace('\n', ',').split(',') if t.strip()]
        for t in tokens:
            self._add_part_silent(t)
        self.input_field.clear()
        self._update_placeholder()
        self.partsChanged.emit(self.parts[:])

    def _add_part_silent(self, name):
        for p in self.parts:
            if p['name'] == name:
                p['qty'] += 1
                self._rebuild_chips()
                return
        self.parts.append({'name': name, 'qty': 1})
        self._rebuild_chips()

    def add_part(self, name):
        self._add_part_silent(name.strip().upper())
        self._update_placeholder()
        self.partsChanged.emit(self.parts[:])

    def remove_part(self, name):
        self.parts = [p for p in self.parts if p['name'] != name]
        self._rebuild_chips()
        self._update_placeholder()
        self.partsChanged.emit(self.parts[:])

    def clear_all(self):
        self.parts.clear()
        self._rebuild_chips()
        self._update_placeholder()
        self.partsChanged.emit(self.parts[:])

    def set_parts(self, parts):
        self.parts = [dict(p) for p in parts]
        self._rebuild_chips()
        self._update_placeholder()

    def _rebuild_chips(self):
        while self.flow.count():
            item = self.flow.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        for p in self.parts:
            chip = ChipWidget(p['name'], p['qty'])
            chip.removed.connect(self.remove_part)
            self.flow.addWidget(chip)
        self.flow_container.updateGeometry()
        self.updateGeometry()

    def _update_placeholder(self):
        if self.parts:
            self.input_field.setPlaceholderText('부품을 추가하세요…')
        else:
            self.input_field.setPlaceholderText('예: LM358P, TL072CP, NE5532P')


# ─────────────────────────────────────────────
#  결과 카드
# ─────────────────────────────────────────────
class ResultCard(QFrame):
    toggle_fav  = Signal(str)
    copy_part   = Signal(dict)
    share_chat  = Signal(dict)

    def __init__(self, index, part, is_fav=False, parent=None):
        super().__init__(parent)
        self.part = part
        self.setObjectName('result_card')
        self.setStyleSheet("""
            QFrame#result_card{background:#fff;border:1px solid #E4E7EC;border-radius:12px;}
            QFrame#result_card:hover{border-color:#D0D5DD;}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 카드 헤더
        head = QWidget()
        head.setStyleSheet("border-bottom:1px solid #EDF0F3;")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(14, 12, 12, 12)
        hl.setSpacing(12)

        num = QLabel(str(index).zfill(2))
        num.setFixedSize(26, 26)
        num.setAlignment(Qt.AlignCenter)
        num.setStyleSheet("background:#F4F5F7;color:#94A3B8;font-size:11px;font-weight:600;"
                          "border-radius:7px;font-family:'Consolas',monospace;")
        hl.addWidget(num)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_lbl = QLabel(part['name'])
        name_lbl.setStyleSheet("font-size:16px;font-weight:700;font-family:'Consolas','Courier New',monospace;color:#0F172A;")
        ok = QLabel('✓')
        ok.setFixedSize(14, 14)
        ok.setAlignment(Qt.AlignCenter)
        ok.setStyleSheet("background:#10B981;color:white;border-radius:7px;font-size:9px;font-weight:700;")
        name_row.addWidget(name_lbl)
        name_row.addWidget(ok)
        name_row.addStretch()

        maker_row = QHBoxLayout()
        maker_row.setSpacing(6)
        maker_row.addWidget(self._lbl(part['manufacturer'], "font-size:12px;font-weight:500;color:#475569;"))
        maker_row.addWidget(self._lbl('·', "color:#94A3B8;font-size:12px;"))
        maker_row.addWidget(self._lbl(part['digikey'], "font-size:12px;color:#94A3B8;font-family:'Consolas',monospace;"))
        maker_row.addStretch()

        title_col.addLayout(name_row)
        title_col.addLayout(maker_row)
        hl.addLayout(title_col, 1)

        # 아이콘 버튼들
        for icon, tip, slot in [
            ('★' if is_fav else '☆', '즐겨찾기', lambda: self.toggle_fav.emit(part['name'])),
            ('↗', '팀 채팅에 공유', lambda: self.share_chat.emit(part)),
            ('⧉', '클립보드 복사',  lambda: self.copy_part.emit(part)),
        ]:
            b = QPushButton(icon)
            b.setFixedSize(26, 26)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            color = '#F59E0B' if (icon == '★' and is_fav) else '#94A3B8'
            b.setStyleSheet(f"QPushButton{{border:none;background:transparent;color:{color};"
                            f"border-radius:6px;font-size:{'15' if '★' in icon or '☆' in icon else '14'}px;}}"
                            f"QPushButton:hover{{background:#F4F5F7;color:#0F172A;}}")
            b.clicked.connect(slot)
            hl.addWidget(b)

        root.addWidget(head)

        # ── KV 그리드
        kv = QWidget()
        kv_grid = QGridLayout(kv)
        kv_grid.setContentsMargins(16, 10, 16, 10)
        kv_grid.setHorizontalSpacing(14)
        kv_grid.setVerticalSpacing(7)
        kv_grid.setColumnMinimumWidth(0, 90)
        kv_grid.setColumnStretch(1, 1)

        rows = [
            ('설명',       part['description'],                    False),
            ('패키지',     f"{part['package']} · {part['mountingType']}", False),
            ('재고',       f"{part['stock']:,} 개",               False),
            ('전원/온도',  f"{part['supplyVoltage']} · {part['operatingTemp']}", True),
        ]
        for i, (k, v, mono) in enumerate(rows):
            k_lbl = self._lbl(k, "color:#94A3B8;font-size:12px;font-weight:500;")
            v_lbl = self._lbl(v, ("font-family:'Consolas',monospace;" if mono else "") + "color:#0F172A;font-size:12px;")
            v_lbl.setWordWrap(True)
            kv_grid.addWidget(k_lbl, i, 0, Qt.AlignTop)
            kv_grid.addWidget(v_lbl, i, 1)

        root.addWidget(kv)

        # ── 가격표
        pf = QWidget()
        pfl = QVBoxLayout(pf)
        pfl.setContentsMargins(16, 4, 16, 14)
        pfl.setSpacing(6)

        prices = part['prices']
        best   = min(p['unit'] for p in prices)
        top    = prices[0]['unit']
        saving = int(((top - best) / top) * 100) if top > 0 else 0

        ph = QHBoxLayout()
        ph.addWidget(self._lbl('수량별 단가', "color:#94A3B8;font-size:11px;"))
        ph.addStretch()
        best_badge = self._lbl(f'최저 {fmt_usd(best)} · {saving}% ↓',
            "background:#ECFDF5;color:#047857;font-size:11px;font-weight:600;"
            "border-radius:999px;padding:1px 6px;")
        ph.addWidget(best_badge)
        pfl.addLayout(ph)

        tbl = QTableWidget(min(len(prices), 6), 4)
        tbl.setHorizontalHeaderLabels(['수량', '단가', '합계', '절약'])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setSelectionMode(QTableWidget.NoSelection)
        tbl.setFocusPolicy(Qt.NoFocus)
        tbl.setShowGrid(False)
        tbl.setStyleSheet("""
            QTableWidget{border:none;background:transparent;
                font-family:'Consolas','Courier New',monospace;font-size:12px;}
            QTableWidget::item{padding:0 4px;border-bottom:1px dashed #EDF0F3;}
            QHeaderView::section{background:transparent;color:#94A3B8;font-size:10px;
                font-weight:500;border:none;border-bottom:1px solid #EDF0F3;padding:4px 4px;}
        """)

        row_h = 26
        tbl.setFixedHeight(min(len(prices), 6) * row_h + 30)
        for i, p in enumerate(prices[:6]):
            sv = int(((top - p['unit']) / top) * 100) if i > 0 else 0
            is_best = (p['unit'] == best)
            fg = QColor('#047857') if is_best else QColor('#0F172A')
            fg_dim = QColor('#047857') if is_best else QColor('#94A3B8')

            def cell(txt, align=Qt.AlignRight | Qt.AlignVCenter, color=fg):
                it = QTableWidgetItem(txt)
                it.setTextAlignment(align)
                it.setForeground(color)
                return it

            tbl.setItem(i, 0, cell(f"{p['qty']:,}",    Qt.AlignLeft | Qt.AlignVCenter))
            tbl.setItem(i, 1, cell(fmt_usd(p['unit'])))
            tbl.setItem(i, 2, cell(fmt_usd(p['ext'])))
            tbl.setItem(i, 3, cell(f'−{sv}%' if i > 0 else '—', color=fg_dim))
            tbl.setRowHeight(i, row_h)

        pfl.addWidget(tbl)
        root.addWidget(pf)

        # ── 카드 푸터
        foot = QFrame()
        foot.setStyleSheet("background:#FCFCFD;border-top:1px solid #EDF0F3;"
                           "border-bottom-left-radius:12px;border-bottom-right-radius:12px;")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(14, 8, 14, 8)
        fl.setSpacing(8)

        ds_btn = QPushButton('📄 데이터시트')
        ds_btn.setCursor(Qt.PointingHandCursor)
        ds_btn.clicked.connect(lambda: webbrowser.open(part['datasheetUrl']))
        fl.addWidget(ds_btn)

        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#EDF0F3;"); sep.setFixedWidth(1)
        fl.addWidget(sep)

        dk_btn = QPushButton('↗ DigiKey 상세')
        dk_btn.setCursor(Qt.PointingHandCursor)
        dk_btn.clicked.connect(lambda: webbrowser.open(part['detailUrl']))
        fl.addWidget(dk_btn)

        fl.addStretch()
        fl.addWidget(self._lbl('조회 0.8s', "color:#94A3B8;font-size:11px;"))

        for b in (ds_btn, dk_btn):
            b.setStyleSheet("QPushButton{border:none;background:transparent;color:#2952D6;"
                            "font-size:12px;font-weight:500;border-radius:6px;padding:4px 8px;}"
                            "QPushButton:hover{background:#EEF4FF;}")

        root.addWidget(foot)

    @staticmethod
    def _lbl(text, style=''):
        l = QLabel(text)
        if style:
            l.setStyleSheet(style)
        return l


# ─────────────────────────────────────────────
#  메인 윈도우
# ─────────────────────────────────────────────
class CircuitKitWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.chat_window = None
        self.active_page = "search"
        self.parts            = [{'name': 'LM358P', 'qty': 1},
                                 {'name': 'TL072CP', 'qty': 1},
                                 {'name': 'NE5532P', 'qty': 1}]
        self.active_hist_id   = 'h1'
        self.fav_ids          = {'f1'}
        self.fav_part_names   = {'LM358P'}
        self.tab_mode         = 'cards'
        self.history_item_wids = {}

        self.setWindowTitle('CircuitKit — DigiKey 부품 정보 조회기')
        self.resize(1200, 800)
        self.setMinimumSize(960, 640)
        self.setStyleSheet(GLOBAL_QSS)

        self._build_ui()
        self._refresh_results()

    # ── UI 구성 ──────────────────────────────────
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        vbox.addWidget(self._make_titlebar())

        body = QWidget()
        hbox = QHBoxLayout(body)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        hbox.addWidget(self._make_sidebar())
        self.page_stack = QStackedWidget()
        self.page_stack.addWidget(self._make_main())
        self.chat_window = CircuitKitChatWindow()
        self.chat_window.set_embedded_mode(True)
        self.chat_window.search_requested.connect(lambda: self._switch_page("search"))
        self.page_stack.addWidget(self.chat_window)
        hbox.addWidget(self.page_stack, 1)
        vbox.addWidget(body, 1)

    # ── 타이틀바 ──────────────────────────────────
    def _make_titlebar(self):
        bar = QFrame()
        bar.setObjectName('titlebar')
        bar.setFixedHeight(36)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(10)

        lay.addWidget(QLabel('◈', styleSheet='color:#3B68F1;font-size:14px;'))
        title = QLabel('CircuitKit — DigiKey 부품 정보 조회기')
        title.setObjectName('titlebar_title')
        lay.addWidget(title)
        lay.addStretch()

        self.search_nav_btn = QPushButton('🔍  부품 검색')
        self.search_nav_btn.setObjectName('nav_btn_active')
        self.search_nav_btn.setCursor(Qt.PointingHandCursor)
        self.search_nav_btn.clicked.connect(lambda: self._switch_page("search"))
        lay.addWidget(self.search_nav_btn)

        self.chat_nav_btn = QPushButton('↗  팀 채팅  5')
        self.chat_nav_btn.setObjectName('nav_btn')
        self.chat_nav_btn.setCursor(Qt.PointingHandCursor)
        self.chat_nav_btn.clicked.connect(lambda: self._switch_page("chat"))
        lay.addWidget(self.chat_nav_btn)

        for sym, name, slot in [('−', 'win_min', self.showMinimized),
                                 ('□', 'win_max', self._toggle_max),
                                 ('✕', 'win_close', self.close)]:
            b = QPushButton(sym)
            b.setObjectName(name)
            b.setFixedSize(28, 22)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(slot)
            lay.addWidget(b)
        return bar

    def _toggle_max(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def _switch_page(self, page):
        self.active_page = page
        if hasattr(self, "page_stack"):
            self.page_stack.setCurrentIndex(1 if page == "chat" else 0)
        if hasattr(self, "search_nav_btn"):
            self.search_nav_btn.setObjectName("nav_btn_active" if page == "search" else "nav_btn")
            self.chat_nav_btn.setObjectName("nav_btn_active" if page == "chat" else "nav_btn")
            for btn in (self.search_nav_btn, self.chat_nav_btn):
                btn.style().unpolish(btn)
                btn.style().polish(btn)

    # ── 사이드바 ──────────────────────────────────
    def _make_sidebar(self):
        sb = QFrame()
        sb.setObjectName('sidebar')
        sb.setFixedWidth(264)
        vb = QVBoxLayout(sb)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(0)

        # 로고 헤더
        hdr = QWidget()
        hdr.setObjectName('sidebar_header')
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(18, 20, 18, 14)
        hl.setSpacing(10)
        logo = QLabel('CK')
        logo.setObjectName('logo')
        logo.setFixedSize(32, 32)
        logo.setAlignment(Qt.AlignCenter)
        hl.addWidget(logo)
        col = QVBoxLayout()
        col.setSpacing(1)
        col.addWidget(QLabel('CircuitKit', objectName='app_name'))
        col.addWidget(QLabel('부품 가격 · 사양 조회', objectName='app_desc'))
        hl.addLayout(col)
        hl.addStretch()
        vb.addWidget(hdr)

        # 새 검색 버튼
        nsb = QPushButton('＋  새 검색          ⌘N')
        nsb.setObjectName('new_search_btn')
        nsb.setFixedHeight(36)
        nsb.setCursor(Qt.PointingHandCursor)
        nsb.clicked.connect(self._on_new_search)
        vb.addWidget(nsb)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setObjectName('sidebar_scroll')
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(6, 4, 6, 14)
        cl.setSpacing(0)

        # 최근 검색
        cl.addWidget(self._section_header('⏱  최근 검색', len(HISTORY_DATA)))
        for h in HISTORY_DATA:
            w = self._history_item(h)
            self.history_item_wids[h['id']] = w
            cl.addWidget(w)
        cl.addSpacing(10)

        # 즐겨찾기
        cl.addWidget(self._section_header('★  즐겨찾기', len(FAVORITES_DATA)))
        for f in FAVORITES_DATA:
            cl.addWidget(self._favorite_item(f))

        cl.addStretch()
        scroll.setWidget(content)
        vb.addWidget(scroll, 1)

        # 하단 유저 영역
        footer = QFrame()
        footer.setObjectName('sidebar_footer')
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(14, 12, 14, 12)
        fl.setSpacing(10)
        avatar = QLabel('DK')
        avatar.setObjectName('sidebar_avatar')
        avatar.setFixedSize(28, 28)
        avatar.setAlignment(Qt.AlignCenter)
        fl.addWidget(avatar)
        uc = QVBoxLayout(); uc.setSpacing(0)
        uc.addWidget(QLabel('DigiKey', objectName='user_name'))
        uc.addWidget(QLabel('데모 상태 · 실제 연결 아님', objectName='user_meta'))
        fl.addLayout(uc, 1)
        gear = QPushButton('⚙')
        gear.setObjectName('icon_btn')
        gear.setFixedSize(26, 26)
        gear.setCursor(Qt.PointingHandCursor)
        gear.clicked.connect(lambda: self._show_toast('설정은 메인 앱에서 변경하세요'))
        fl.addWidget(gear)
        vb.addWidget(footer)
        return sb

    def _section_header(self, title, count):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 8, 12, 6)
        lay.setSpacing(0)
        lay.addWidget(QLabel(title, objectName='section_header'))
        lay.addStretch()
        lay.addWidget(QLabel(str(count), objectName='section_count'))
        return w

    def _history_item(self, h):
        w = QFrame()
        w.setCursor(Qt.PointingHandCursor)
        w.setProperty('hist_id', h['id'])
        lay = QHBoxLayout(w)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(9)

        dot = QLabel('●')
        color = STATUS_DOT_COLORS.get(h['status'], '#94A3B8')
        dot.setStyleSheet(f'color:{color};font-size:8px;')
        dot.setFixedWidth(10)
        lay.addWidget(dot)

        lbl = QLabel(h['label'])
        lbl.setObjectName('history_label')
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lay.addWidget(lbl, 1)

        time = QLabel(h['time'])
        time.setObjectName('history_time')
        lay.addWidget(time)

        active = h['id'] == self.active_hist_id
        self._set_history_style(w, active)

        # 클릭 이벤트를 mousePressEvent로 처리
        w.mousePressEvent = lambda e, hid=h['id']: self._on_pick_history(hid)
        return w

    def _set_history_style(self, w, active):
        bg    = '#EEF4FF' if active else 'transparent'
        color = '#1E3FAF' if active else '#475569'
        fw    = '600'     if active else 'normal'
        w.setStyleSheet(f"""
            QFrame{{background:{bg};border-radius:6px;}}
            QFrame:hover{{background:#EEF0F3;}}
            QLabel#history_label{{color:{color};font-size:13px;font-weight:{fw};}}
            QLabel#history_time{{color:#94A3B8;font-size:11px;}}
        """)

    def _favorite_item(self, f):
        w = QFrame()
        w.setCursor(Qt.PointingHandCursor)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(10, 7, 10, 7)
        lay.setSpacing(9)
        lay.addWidget(QLabel('⊡', styleSheet='color:#94A3B8;font-size:14px;'))
        lbl = QLabel(f['label'])
        lbl.setStyleSheet("color:#0F172A;font-size:12px;font-family:'Consolas',monospace;")
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lay.addWidget(lbl, 1)
        lay.addWidget(QLabel(f['meta'], styleSheet='color:#94A3B8;font-size:11px;'))
        star = QPushButton('★' if f['id'] in self.fav_ids else '☆')
        star.setFixedSize(22, 22)
        star.setStyleSheet("QPushButton{border:none;background:transparent;color:#F59E0B;"
                           "font-size:14px;border-radius:4px;}"
                           "QPushButton:hover{background:#EEF0F3;}")
        star.setCursor(Qt.PointingHandCursor)
        lay.addWidget(star)
        w.setStyleSheet("QFrame{background:transparent;border-radius:6px;}"
                        "QFrame:hover{background:#EEF0F3;}")
        return w

    # ── 메인 영역 ──────────────────────────────────
    def _make_main(self):
        frame = QFrame()
        frame.setObjectName('main_area')
        vb = QVBoxLayout(frame)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(0)

        # 헤더
        hdr = QFrame()
        hdr.setObjectName('main_header')
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(28, 22, 28, 16)
        hl.setSpacing(18)
        tc = QVBoxLayout(); tc.setSpacing(4)
        tc.addWidget(QLabel('부품 가격 및 세부 정보 조회', objectName='main_h1'))
        tc.addWidget(QLabel('부품명을 입력하면 가격, 주요 스펙, 데이터시트를 한 번에 조회합니다',
                             objectName='main_desc'))
        hl.addLayout(tc, 1)
        for txt in ('📄 BOM 가져오기', '💾 결과 저장'):
            b = QPushButton(txt)
            b.setObjectName('btn')
            b.setEnabled(False)
            b.setToolTip('데모 화면에서는 비활성화됨')
            hl.addWidget(b)
        vb.addWidget(hdr)

        # 바디 스크롤
        scroll = QScrollArea()
        scroll.setObjectName('main_body_scroll')
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body_w = QWidget()
        self.body_vbox = QVBoxLayout(body_w)
        self.body_vbox.setContentsMargins(28, 18, 28, 28)
        self.body_vbox.setSpacing(0)

        self._build_input_panel()
        self._build_status_strip()
        self._build_results_area()

        self.body_vbox.addStretch()
        scroll.setWidget(body_w)
        vb.addWidget(scroll, 1)

        vb.addWidget(self._make_statusbar())
        return frame

    def _build_input_panel(self):
        panel = QFrame()
        panel.setObjectName('input_panel')
        pv = QVBoxLayout(panel)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(0)

        # 패널 상단 행
        row = QFrame()
        row.setObjectName('panel_row')
        rl = QHBoxLayout(row)
        rl.setContentsMargins(14, 10, 14, 10)
        rl.setSpacing(12)
        rl.addWidget(QLabel('부품 입력', objectName='label_tag'))
        helper = QLabel('엔터 · 쉼표 · 줄바꿈으로 구분 — 여러 부품을 한 번에 붙여넣기 가능')
        helper.setObjectName('helper_text')
        helper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        rl.addWidget(helper, 1)
        ex = QPushButton('✦ 예시')
        ex.setObjectName('btn_ghost')
        ex.setCursor(Qt.PointingHandCursor)
        ex.clicked.connect(self._load_example)
        cl = QPushButton('🗑 비우기')
        cl.setObjectName('btn_ghost_danger')
        cl.setCursor(Qt.PointingHandCursor)
        cl.clicked.connect(self._clear_all)
        rl.addWidget(ex); rl.addWidget(cl)
        pv.addWidget(row)

        # 칩 입력
        self.chip_input = ChipInputArea()
        self.chip_input.set_parts(self.parts)
        self.chip_input.partsChanged.connect(self._on_parts_changed)
        pv.addWidget(self.chip_input)

        # 옵션 행
        opts = QFrame()
        opts.setObjectName('options_row')
        ol = QHBoxLayout(opts)
        ol.setContentsMargins(14, 12, 14, 12)
        ol.setSpacing(18)

        # 타임아웃
        tg = QHBoxLayout(); tg.setSpacing(8)
        tg.addWidget(QLabel('⏱', styleSheet='color:#94A3B8;'))
        tg.addWidget(QLabel('타임아웃', objectName='opt_label'))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setObjectName('input_num')
        self.timeout_spin.setRange(1, 120)
        self.timeout_spin.setValue(15)
        self.timeout_spin.setSuffix(' 초')
        self.timeout_spin.setFixedSize(80, 28)
        tg.addWidget(self.timeout_spin)
        ol.addLayout(tg)

        # 브라우저 체크박스
        self.browser_chk = QCheckBox('브라우저 창 표시')
        self.browser_chk.setObjectName('browser_chk')
        ol.addWidget(self.browser_chk)

        # IP / Port 공유
        sg = QHBoxLayout(); sg.setSpacing(8)
        sg.addWidget(QLabel('📡', styleSheet='font-size:13px;'))
        sg.addWidget(QLabel('공유', objectName='opt_label'))
        self.ip_input = QLineEdit()
        self.ip_input.setObjectName('ip_input')
        self.ip_input.setPlaceholderText('192.168.0.10')
        self.ip_input.setFixedSize(124, 28)
        self.port_input = QLineEdit()
        self.port_input.setObjectName('ip_input')
        self.port_input.setText('5000')
        self.port_input.setFixedSize(60, 28)
        self.port_input.setAlignment(Qt.AlignCenter)
        for sym, tip in [('↗', '결과 보내기'), ('↺', '수신 재시작')]:
            b = QPushButton(sym)
            b.setObjectName('btn_ghost')
            b.setFixedSize(32, 28)
            b.setToolTip(f'{tip}: 데모 화면에서는 비활성화됨')
            b.setEnabled(False)
            sg.addWidget(b)
        sg.insertWidget(3, self.ip_input)
        sg.insertWidget(4, QLabel(':', styleSheet='color:#94A3B8;'))
        sg.insertWidget(5, self.port_input)
        ol.addLayout(sg)

        ol.addStretch()

        # 조회 시작 버튼
        self.run_btn = QPushButton(f'▶  조회 시작  {len(self.parts)}')
        self.run_btn.setObjectName('btn_primary')
        self.run_btn.setFixedHeight(32)
        self.run_btn.setMinimumWidth(120)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self._on_run)
        ol.addWidget(self.run_btn)

        pv.addWidget(opts)
        self.body_vbox.addWidget(panel)

    def _build_status_strip(self):
        self.status_strip = QFrame()
        self.status_strip.setObjectName('status_strip')
        sl = QHBoxLayout(self.status_strip)
        sl.setContentsMargins(14, 11, 14, 11)
        sl.setSpacing(12)
        sl.addWidget(QLabel('●', styleSheet='color:#10B981;font-size:8px;'))
        self.status_main_lbl = QLabel('조회 완료')
        self.status_main_lbl.setObjectName('status_lbl')
        sl.addWidget(self.status_main_lbl)
        self.status_bom_lbl  = QLabel()
        self.status_bom_lbl.setObjectName('bom_lbl')
        sl.addWidget(self.status_bom_lbl)
        sl.addStretch()
        self.status_strip.setVisible(False)
        self.body_vbox.addWidget(self.status_strip)

    def _build_results_area(self):
        # 결과 헤더 (제목 + 탭)
        rh = QWidget()
        rl = QHBoxLayout(rh)
        rl.setContentsMargins(0, 22, 0, 10)
        rl.setSpacing(12)
        rl.addWidget(QLabel('조회 결과', objectName='results_title'))
        self.count_pill = QLabel('0 / 0')
        self.count_pill.setObjectName('count_pill')
        rl.addWidget(self.count_pill)
        rl.addStretch()

        tabs = QFrame()
        tabs.setObjectName('tabs_frame')
        tl = QHBoxLayout(tabs)
        tl.setContentsMargins(2, 2, 2, 2)
        tl.setSpacing(0)
        self.tab_cards_btn = QPushButton('▦ 카드 보기')
        self.tab_cards_btn.setObjectName('tab_active')
        self.tab_cards_btn.setCursor(Qt.PointingHandCursor)
        self.tab_cards_btn.clicked.connect(lambda: self._set_tab('cards'))
        self.tab_text_btn  = QPushButton('≡ 텍스트 보기')
        self.tab_text_btn.setObjectName('tab_inactive')
        self.tab_text_btn.setCursor(Qt.PointingHandCursor)
        self.tab_text_btn.clicked.connect(lambda: self._set_tab('text'))
        tl.addWidget(self.tab_cards_btn)
        tl.addWidget(self.tab_text_btn)
        rl.addWidget(tabs)
        self.body_vbox.addWidget(rh)

        # 스택: 카드 그리드 vs 텍스트
        self.results_stack = QStackedWidget()

        cards_w = QWidget()
        self.cards_grid = QGridLayout(cards_w)
        self.cards_grid.setContentsMargins(0, 0, 0, 0)
        self.cards_grid.setSpacing(14)
        self.results_stack.addWidget(cards_w)

        self.text_view = QTextEdit()
        self.text_view.setObjectName('text_view')
        self.text_view.setReadOnly(True)
        self.text_view.setMinimumHeight(300)
        self.results_stack.addWidget(self.text_view)

        self.body_vbox.addWidget(self.results_stack)

    def _make_statusbar(self):
        bar = QFrame()
        bar.setObjectName('statusbar')
        bar.setFixedHeight(28)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(14)
        lay.addWidget(QLabel('● 연결됨', objectName='sb_ok'))
        lay.addWidget(QLabel('데모 데이터', objectName='sb_item'))
        lay.addWidget(QLabel('실제 캐시/동기화 상태 아님', objectName='sb_item'))
        lay.addStretch()
        self.sb_parts_lbl   = QLabel(f'{len(self.parts)}개 부품', objectName='sb_item')
        self.sb_timeout_lbl = QLabel('타임아웃 15s', objectName='sb_item')
        lay.addWidget(self.sb_parts_lbl)
        lay.addWidget(self.sb_timeout_lbl)
        return bar

    # ── 이벤트 핸들러 ─────────────────────────────
    def _on_parts_changed(self, parts):
        self.parts = parts
        self.run_btn.setText(f'▶  조회 시작  {len(parts)}')
        self.run_btn.setEnabled(len(parts) > 0)
        self.sb_parts_lbl.setText(f'{len(parts)}개 부품')

    def _on_new_search(self):
        self.active_hist_id = None
        self._update_history_active()
        self.parts = []
        self.chip_input.clear_all()
        self._refresh_results()

    def _on_pick_history(self, hist_id):
        self.active_hist_id = hist_id
        self._update_history_active()
        if hist_id == 'h1':
            parts = [{'name': 'LM358P', 'qty': 1},
                     {'name': 'TL072CP', 'qty': 1},
                     {'name': 'NE5532P', 'qty': 1}]
        else:
            h = next((x for x in HISTORY_DATA if x['id'] == hist_id), None)
            if h:
                names = [s.strip() for s in h['label'].replace('·', ',').split(',') if s.strip()]
                parts = [{'name': n.upper(), 'qty': 1} for n in names]
            else:
                parts = []
        self.parts = parts
        self.chip_input.set_parts(parts)
        self._refresh_results()

    def _update_history_active(self):
        for hid, w in self.history_item_wids.items():
            self._set_history_style(w, hid == self.active_hist_id)

    def _load_example(self):
        parts = [{'name': 'LM358P', 'qty': 1},
                 {'name': 'TL072CP', 'qty': 1},
                 {'name': 'NE5532P', 'qty': 1}]
        self.parts = parts
        self.chip_input.set_parts(parts)
        self._refresh_results()

    def _clear_all(self):
        self.parts = []
        self.chip_input.clear_all()
        self._refresh_results()

    def _on_run(self):
        self.run_btn.setText('■  중지')
        self.run_btn.setEnabled(False)
        self._refresh_results()
        QTimer.singleShot(1400, self._on_run_done)

    def _on_run_done(self):
        self.run_btn.setText(f'▶  조회 시작  {len(self.parts)}')
        self.run_btn.setEnabled(True)

    def _set_tab(self, mode):
        self.tab_mode = mode
        if mode == 'cards':
            self.tab_cards_btn.setObjectName('tab_active')
            self.tab_text_btn.setObjectName('tab_inactive')
            self.results_stack.setCurrentIndex(0)
        else:
            self.tab_cards_btn.setObjectName('tab_inactive')
            self.tab_text_btn.setObjectName('tab_active')
            self.results_stack.setCurrentIndex(1)
        for b in (self.tab_cards_btn, self.tab_text_btn):
            b.style().unpolish(b); b.style().polish(b)

    def _refresh_results(self):
        results = [MOCK_PARTS[p['name']] for p in self.parts if p['name'] in MOCK_PARTS]

        # 상태 스트립
        if results:
            bom = sum((p['prices'][3]['unit'] if len(p['prices']) > 3
                       else p['prices'][0]['unit']) * 100 for p in results)
            self.status_main_lbl.setText(f'{len(results)}개 부품 조회가 끝났습니다')
            self.status_bom_lbl.setText(f'· 평균 응답 0.8s · BOM 100ea 합계 ${bom:.2f}')
            self.status_strip.setVisible(True)
        else:
            self.status_strip.setVisible(False)

        self.count_pill.setText(f'{len(results)} / {len(self.parts)}')

        # 카드 초기화
        for i in reversed(range(self.cards_grid.count())):
            item = self.cards_grid.takeAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        if results:
            for i, part in enumerate(results):
                card = ResultCard(i + 1, part, part['name'] in self.fav_part_names)
                card.toggle_fav.connect(self._toggle_fav)
                card.copy_part.connect(self._on_copy)
                card.share_chat.connect(self._on_share)
                self.cards_grid.addWidget(card, i // 2, i % 2)
        else:
            empty = QLabel('부품을 입력하고  ▶ 조회 시작  을 누르세요')
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet('color:#94A3B8;font-size:13px;border:1px dashed #E4E7EC;'
                                'border-radius:12px;padding:38px 16px;')
            self.cards_grid.addWidget(empty, 0, 0, 1, 2)

        # 텍스트 뷰
        lines = []
        for i, p in enumerate(results):
            price_str = '  '.join(f"{x['qty']}={fmt_usd(x['unit'])}" for x in p['prices'])
            lines += [
                f"[{i+1}] {p['name']}  ({p['digikey']})",
                f"    제조사 : {p['manufacturer']}",
                f"    설명   : {p['description']}",
                f"    실장   : {p['mountingType']} · {p['package']}",
                f"    재고   : {p['stock']:,} 개",
                f"    단가   : {price_str}",
                f"    링크   : {p['detailUrl']}",
                f"    PDF    : {p['datasheetUrl']}",
                '',
            ]
        self.text_view.setPlainText('\n'.join(lines))

    def _toggle_fav(self, name):
        if name in self.fav_part_names:
            self.fav_part_names.discard(name)
            self._show_toast('즐겨찾기 해제됨')
        else:
            self.fav_part_names.add(name)
            self._show_toast('즐겨찾기에 추가됨')
        self._refresh_results()

    def _on_copy(self, part):
        txt = f"{part['name']}\t{part['digikey']}\t{part['manufacturer']}\t{fmt_usd(part['prices'][0]['unit'])}"
        QApplication.clipboard().setText(txt)
        self._show_toast(f"{part['name']} 정보가 클립보드에 복사되었습니다")

    def _on_share(self, part):
        self._show_toast(f"{part['name']} · 팀 채팅으로 공유됩니다")
        self._open_chat(part.get("name"))

    def _open_chat(self, part_name=None):
        if part_name and hasattr(self.chat_window, "composer"):
            self.chat_window.composer.attach_part_by_name(part_name)
        self._switch_page("chat")

    def _show_toast(self, msg):
        self.statusBar().showMessage(msg, 2200)


# ─────────────────────────────────────────────
#  전역 QSS 스타일
# ─────────────────────────────────────────────
GLOBAL_QSS = """
QMainWindow, QWidget { font-family:'Malgun Gothic','Apple SD Gothic Neo','Nanum Gothic',sans-serif; }

/* ── 타이틀바 ── */
QFrame#titlebar {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #FBFBFC, stop:1 #F4F5F7);
    border-bottom: 1px solid #E4E7EC;
}
QLabel#titlebar_title { font-size:12px; font-weight:500; color:#475569; }
QLabel#search_badge {
    font-size:12px; font-weight:500; color:#1E3FAF;
    background:#EEF4FF; border:1px solid #D5E0FF;
    border-radius:6px; padding:3px 9px;
}
QPushButton#chat_btn {
    font-size:12px; color:#475569;
    border:1px solid #E4E7EC; border-radius:6px;
    background:transparent; padding:3px 9px;
}
QPushButton#chat_btn:hover { background:#F4F5F7; }
QPushButton#nav_btn {
    font-size:12px; color:#475569;
    border:1px solid #E4E7EC; border-radius:6px;
    background:transparent; padding:3px 10px;
}
QPushButton#nav_btn:hover { background:#F4F5F7; }
QPushButton#nav_btn_active {
    font-size:12px; color:#1E3FAF; font-weight:700;
    border:1px solid #D5E0FF; border-radius:6px;
    background:#EEF4FF; padding:3px 10px;
}
QPushButton#win_min, QPushButton#win_max {
    border:none; background:transparent; color:#94A3B8; border-radius:4px; font-size:13px;
}
QPushButton#win_min:hover, QPushButton#win_max:hover { background:#EEF0F3; color:#0F172A; }
QPushButton#win_close { border:none; background:transparent; color:#94A3B8; border-radius:4px; font-size:13px; }
QPushButton#win_close:hover { background:#FEE2E2; color:#BE123C; }

/* ── 사이드바 ── */
QFrame#sidebar { background:#F8F9FB; border-right:1px solid #E4E7EC; }
QLabel#logo {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #3B68F1, stop:1 #1E3FAF);
    color:white; font-weight:700; font-size:13px; border-radius:8px;
}
QLabel#app_name { font-weight:700; font-size:14px; color:#0F172A; }
QLabel#app_desc { font-size:11px; color:#94A3B8; }
QPushButton#new_search_btn {
    background:white; border:1px solid #E4E7EC; border-radius:8px;
    color:#0F172A; font-size:13px; font-weight:500;
    margin:6px 14px 14px 14px; padding:0 12px;
    text-align:left;
}
QPushButton#new_search_btn:hover { border-color:#D0D5DD; }
QLabel#section_header { font-size:11px; font-weight:600; color:#94A3B8; letter-spacing:1px; }
QLabel#section_count {
    font-size:11px; font-weight:600; background:#F4F5F7;
    color:#475569; border-radius:999px; padding:1px 6px;
}
QScrollArea#sidebar_scroll { border:none; background:transparent; }
QFrame#sidebar_footer { border-top:1px solid #E4E7EC; }
QLabel#sidebar_avatar {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #E11D48, stop:1 #F59E0B);
    color:white; font-weight:600; font-size:12px; border-radius:14px;
}
QLabel#user_name { font-size:12px; font-weight:500; color:#0F172A; }
QLabel#user_meta { font-size:11px; color:#94A3B8; }
QPushButton#icon_btn {
    border:none; background:transparent; color:#94A3B8; border-radius:6px; font-size:14px;
}
QPushButton#icon_btn:hover { background:#EEF0F3; color:#0F172A; }

/* ── 메인 영역 ── */
QFrame#main_area { background:white; }
QFrame#main_header { border-bottom:1px solid #EDF0F3; background:white; }
QLabel#main_h1 { font-size:20px; font-weight:700; color:#0F172A; }
QLabel#main_desc { font-size:12px; color:#94A3B8; }
QPushButton#btn {
    border:1px solid #E4E7EC; border-radius:7px; background:white;
    color:#0F172A; font-size:13px; font-weight:500; height:32px; padding:0 12px;
}
QPushButton#btn:hover { background:#F4F5F7; border-color:#D0D5DD; }
QScrollArea#main_body_scroll { border:none; background:white; }

/* ── 입력 패널 ── */
QFrame#input_panel { border:1px solid #E4E7EC; border-radius:12px; background:white; }
QFrame#panel_row {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #FBFBFC, stop:1 #F8F9FB);
    border-bottom:1px solid #EDF0F3;
    border-top-left-radius:12px; border-top-right-radius:12px;
}
QLabel#label_tag { font-size:11px; font-weight:600; color:#475569; }
QLabel#helper_text { color:#94A3B8; font-size:12px; }
QPushButton#btn_ghost {
    border:transparent; background:transparent; color:#475569;
    font-size:12px; font-weight:500; border-radius:6px; height:28px; padding:0 8px;
}
QPushButton#btn_ghost:hover { background:#F4F5F7; border:1px solid #E4E7EC; }
QPushButton#btn_ghost_danger {
    border:transparent; background:transparent; color:#BE123C;
    font-size:12px; font-weight:500; border-radius:6px; height:28px; padding:0 8px;
}
QPushButton#btn_ghost_danger:hover { background:#FEF2F2; }
QFrame#options_row {
    background:#FCFCFD; border-top:1px solid #EDF0F3;
    border-bottom-left-radius:12px; border-bottom-right-radius:12px;
}
QLabel#opt_label { color:#94A3B8; font-size:12px; }
QSpinBox#input_num {
    border:1px solid #E4E7EC; border-radius:6px; padding:0 8px;
    font-size:13px; background:white; font-family:'Consolas',monospace;
}
QSpinBox#input_num:focus { border-color:#3B68F1; }
QLineEdit#ip_input {
    border:1px solid #E4E7EC; border-radius:6px; padding:0 8px;
    font-size:12px; background:white; font-family:'Consolas',monospace;
}
QLineEdit#ip_input:focus { border-color:#3B68F1; }
QCheckBox#browser_chk { color:#475569; font-size:12px; }
QPushButton#btn_primary {
    background:#3B68F1; border:1px solid #2952D6; border-radius:7px;
    color:white; font-size:13px; font-weight:500; padding:0 14px;
}
QPushButton#btn_primary:hover { background:#2952D6; }
QPushButton#btn_primary:disabled { background:#94A3B8; border-color:#94A3B8; }

/* ── 상태 스트립 ── */
QFrame#status_strip {
    background:#ECFDF5; border:1px solid #BBF7D0;
    border-radius:10px; margin-top:14px;
}
QLabel#status_lbl { color:#047857; font-size:13px; font-weight:500; }
QLabel#bom_lbl    { color:#047857; font-size:13px; }

/* ── 결과 헤더 ── */
QLabel#results_title { font-size:14px; font-weight:700; color:#0F172A; }
QLabel#count_pill {
    background:#F4F5F7; color:#475569;
    font-size:11px; font-weight:600; border-radius:999px; padding:2px 7px;
}
QFrame#tabs_frame { background:#F4F5F7; border:1px solid #E4E7EC; border-radius:8px; }
QPushButton#tab_active {
    background:white; border:none; border-radius:6px;
    color:#0F172A; font-size:12px; font-weight:500; padding:5px 11px;
}
QPushButton#tab_inactive {
    background:transparent; border:none; border-radius:6px;
    color:#475569; font-size:12px; font-weight:500; padding:5px 11px;
}
QPushButton#tab_inactive:hover { color:#0F172A; }

/* ── 텍스트 뷰 ── */
QTextEdit#text_view {
    background:#0F172A; color:#E2E8F0; border-radius:12px; border:none;
    font-family:'Consolas','Courier New',monospace; font-size:12px;
    padding:14px 16px; selection-background-color:#3B68F1;
}

/* ── 상태바 ── */
QFrame#statusbar { background:#FAFBFC; border-top:1px solid #E4E7EC; }
QLabel#sb_ok   { color:#047857; font-size:11px; }
QLabel#sb_item { color:#94A3B8; font-size:11px; }

/* ── 스크롤바 ── */
QScrollBar:vertical { width:10px; background:transparent; border:none; }
QScrollBar::handle:vertical {
    background:#D6DAE0; border-radius:5px; min-height:20px; margin:2px 2px;
}
QScrollBar::handle:vertical:hover { background:#B8BFC8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; border:none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
"""


MainWindow = CircuitKitWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    win = CircuitKitWindow()
    win.show()
    sys.exit(app.exec())


# ─────────────────────────────────────────────
#  진입점
# ─────────────────────────────────────────────
if __name__ == '__main__':
    main()
