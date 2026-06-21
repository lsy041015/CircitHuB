from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIntValidator, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)


class FlowLayout(QLayout):
    def __init__(self, h_spacing: int = 7, v_spacing: int = 7):
        super().__init__()
        self._items: list = []
        self._h = h_spacing
        self._v = v_spacing

    def addItem(self, item):
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, w: int) -> int:
        return self._do_layout(QRect(0, 0, w, 0), dry=True)

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self._do_layout(rect, dry=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        s = QSize()
        for item in self._items:
            s = s.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return s + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do_layout(self, rect: QRect, dry: bool) -> int:
        m = self.contentsMargins()
        x0 = rect.x() + m.left()
        xmax = rect.right() - m.right()
        x, y, lh = x0, rect.y() + m.top(), 0
        for item in self._items:
            hint = item.sizeHint()
            iw, ih = hint.width(), hint.height()
            if x + iw > xmax and lh > 0:
                x, y, lh = x0, y + lh + self._v, 0
            if not dry:
                item.setGeometry(QRect(x, y, iw, ih))
            x += iw + self._h
            lh = max(lh, ih)
        return y + lh - rect.y() + m.bottom()


class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._on = checked
        self.setFixedSize(32, 20)
        self.setCursor(Qt.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._on

    def setChecked(self, v: bool):
        self._on = bool(v)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#3B68F1" if self._on else "#D0D5DD"))
        p.drawRoundedRect(0, 2, 32, 16, 8, 8)
        p.setBrush(QColor("#FFFFFF"))
        thumb_x = 16 if self._on else 2
        p.drawEllipse(thumb_x, 3, 14, 14)
        p.end()

    def mousePressEvent(self, _e):
        self._on = not self._on
        self.update()
        self.toggled.emit(self._on)


class NewSearchButton(QFrame):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_Hover)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("NewSearchBtn")
        self.setFixedHeight(36)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 10, 0)
        row.setSpacing(8)

        plus = QLabel("+")
        plus.setObjectName("BtnPlus")
        self.text_lbl = QLabel("")
        self.text_lbl.setObjectName("BtnText")
        row.addWidget(plus)
        row.addWidget(self.text_lbl)
        row.addStretch()

        kbd_w = QWidget()
        kbd_l = QHBoxLayout(kbd_w)
        kbd_l.setContentsMargins(0, 0, 0, 0)
        kbd_l.setSpacing(2)
        for k in ["⌘", "N"]:
            kl = QLabel(k)
            kl.setObjectName("KbdKey")
            kl.setAlignment(Qt.AlignCenter)
            kbd_l.addWidget(kl)
        row.addWidget(kbd_w)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class SideHistoryItem(QFrame):
    item_clicked = Signal(object)

    _DOT_COLORS = {
        "success": "#10B981",
        "warning": "#F59E0B",
        "error":   "#EF4444",
    }

    def __init__(
        self,
        label: str,
        meta: str,
        status: str = "success",
        active: bool = False,
        payload=None,
    ):
        super().__init__()
        self.setAttribute(Qt.WA_Hover)
        self.setCursor(Qt.PointingHandCursor)
        self._label = label
        self._payload = payload if payload is not None else label
        self.setObjectName("SideItemActive" if active else "SideItem")

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 7, 10, 7)
        row.setSpacing(8)

        dot = QLabel()
        dot.setFixedSize(7, 7)
        c = self._DOT_COLORS.get(status, "#94A3B8")
        dot.setStyleSheet(f"background:{c};border-radius:3px;min-width:7px;max-width:7px;min-height:7px;max-height:7px;")
        row.addWidget(dot)

        lbl = QLabel(label)
        lbl.setObjectName("SideLabelActive" if active else "SideLabel")
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row.addWidget(lbl, 1)

        meta_l = QLabel(meta)
        meta_l.setObjectName("SideMeta")
        row.addWidget(meta_l)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.item_clicked.emit(self._payload)
        super().mousePressEvent(event)


class SideFavoriteItem(QFrame):
    item_clicked = Signal(str)

    def __init__(self, name: str, price: str = ""):
        super().__init__()
        self.setAttribute(Qt.WA_Hover)
        self.setCursor(Qt.PointingHandCursor)
        self._name = name
        self.setObjectName("SideItem")

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 7, 10, 7)
        row.setSpacing(8)

        icon = QLabel("⊛")
        icon.setObjectName("SideMeta")
        icon.setFixedWidth(14)
        row.addWidget(icon)

        lbl = QLabel(name)
        lbl.setObjectName("SideFavLabel")
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row.addWidget(lbl, 1)

        if price:
            p = QLabel(price)
            p.setObjectName("SideMeta")
            row.addWidget(p)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.item_clicked.emit(self._name)
        super().mousePressEvent(event)


class PartChip(QFrame):
    remove_requested = Signal(str)
    quantity_changed = Signal(str, int)

    def __init__(self, name: str, qty: int):
        super().__init__()
        self.name = name
        self.setObjectName("Chip")
        self.setFixedHeight(28)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 0, 5, 0)
        row.setSpacing(6)

        lbl = QLabel(name)
        lbl.setObjectName("ChipText")
        row.addWidget(lbl)

        qty_input = QLineEdit(str(max(1, int(qty))))
        qty_input.setObjectName("ChipQtyInput")
        qty_input.setValidator(QIntValidator(1, 999999, qty_input))
        qty_input.setAlignment(Qt.AlignCenter)
        qty_input.setFixedSize(52, 22)
        qty_input.setToolTip("Quantity")
        qty_input.editingFinished.connect(
            lambda: self.quantity_changed.emit(name, max(1, int(qty_input.text() or "1")))
        )
        row.addWidget(qty_input)

        close = QPushButton("×")
        close.setFixedSize(20, 20)
        close.clicked.connect(lambda: self.remove_requested.emit(name))
        row.addWidget(close)

        fm = lbl.fontMetrics()
        self.setFixedWidth(fm.horizontalAdvance(name) + 106)

    def sizeHint(self) -> QSize:
        return QSize(self.width(), 28)
