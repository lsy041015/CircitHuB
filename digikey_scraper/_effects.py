"""Drop-shadow helpers.

Qt QSS has no ``box-shadow``; the reference web design relies on it heavily.
``QGraphicsDropShadowEffect`` approximates a single shadow layer (Qt cannot
stack multiple layers, so the dominant layer of each CSS token is used).
"""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

# Reference ink color used by every shadow token: rgba(15, 23, 42, a)
_INK = (15, 23, 42)


def _shadow(widget: QWidget, blur: int, dy: int, alpha: int) -> None:
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(0, dy)
    eff.setColor(QColor(_INK[0], _INK[1], _INK[2], alpha))
    widget.setGraphicsEffect(eff)


def shadow_sm(widget: QWidget) -> None:
    """--shadow-sm: subtle resting elevation (input panel)."""
    _shadow(widget, blur=4, dy=1, alpha=18)


def shadow_md(widget: QWidget) -> None:
    """--shadow-md: card elevation."""
    _shadow(widget, blur=14, dy=4, alpha=24)
