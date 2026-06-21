"""SVG circuit schematic symbols keyed by category key.

Each string is a self-contained SVG with viewBox="0 0 60 36".
Rendered at 60x32 logical pixels (2x for HiDPI) by _ui_builder.
Color #1E3FAF matches the app's category-blue theme.
"""
from __future__ import annotations

_C = "#1E3FAF"  # category blue
_W = 'stroke-width="1.8" stroke-linecap="round"'
_WB = 'stroke-width="2.2" stroke-linecap="round"'


def _svg(body: str) -> str:
    return f'<svg viewBox="0 0 60 36" xmlns="http://www.w3.org/2000/svg">{body}</svg>'


def _ln(x1: int, y1: int, x2: int, y2: int, bold: bool = False) -> str:
    w = _WB if bold else _W
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{_C}" {w}/>'


def _poly(pts: str) -> str:
    return f'<polygon points="{pts}" fill="{_C}"/>'


CIRCUIT_SVGS: dict[str, str] = {
    # ── Resistor: IEC rectangle ──────────────────────────────────────────────
    "resistor": _svg(
        _ln(2, 18, 12, 18)
        + f'<rect x="12" y="11" width="36" height="14" fill="none" stroke="{_C}" stroke-width="1.8" rx="1.5"/>'
        + _ln(48, 18, 58, 18)
    ),

    # ── Capacitor: two parallel plates ───────────────────────────────────────
    "capacitor": _svg(
        _ln(2, 18, 26, 18)
        + f'<line x1="26" y1="6" x2="26" y2="30" stroke="{_C}" stroke-width="2.5" stroke-linecap="round"/>'
        + f'<line x1="34" y1="6" x2="34" y2="30" stroke="{_C}" stroke-width="2.5" stroke-linecap="round"/>'
        + _ln(34, 18, 58, 18)
    ),

    # ── Inductor: 3 semicircular bumps above the line ────────────────────────
    "inductor": _svg(
        _ln(2, 22, 10, 22)
        + f'<path d="M10,22 A6,6 0 0,0 22,22 A6,6 0 0,0 34,22 A6,6 0 0,0 46,22"'
        + f' fill="none" stroke="{_C}" stroke-width="1.8" stroke-linecap="round"/>'
        + _ln(46, 22, 58, 22)
    ),

    # ── Diode: filled triangle + cathode bar ─────────────────────────────────
    "diode": _svg(
        _ln(2, 18, 16, 18)
        + _poly("16,8 16,28 38,18")
        + f'<line x1="38" y1="8" x2="38" y2="28" stroke="{_C}" stroke-width="2.2" stroke-linecap="round"/>'
        + _ln(38, 18, 58, 18)
    ),

    # ── MOSFET: gate / insulator / channel segments / D+S terminals ──────────
    "mosfet": _svg(
        # Gate terminal
        _ln(2, 18, 18, 18)
        # Gate plate
        + f'<line x1="18" y1="8" x2="18" y2="28" stroke="{_C}" {_WB}/>'
        # Channel segments (enhancement mode gap in middle)
        + f'<line x1="23" y1="8" x2="23" y2="16" stroke="{_C}" {_WB}/>'
        + f'<line x1="23" y1="20" x2="23" y2="28" stroke="{_C}" {_WB}/>'
        # Drain (top)
        + _ln(23, 12, 44, 12)
        + _ln(44, 4, 44, 12)
        + _ln(44, 4, 58, 4)
        # Source (bottom)
        + _ln(23, 24, 44, 24)
        + _ln(44, 24, 44, 32)
        + _ln(44, 32, 58, 32)
        # Arrow toward channel (N-channel body diode direction)
        + _poly("23,18 33,14 33,22")
    ),

    # ── BJT (NPN): circle + base bar + collector/emitter with arrow ──────────
    "bjt": _svg(
        f'<circle cx="34" cy="18" r="14" fill="none" stroke="{_C}" stroke-width="1.5"/>'
        # Base terminal
        + _ln(2, 18, 20, 18)
        + f'<line x1="20" y1="8" x2="20" y2="28" stroke="{_C}" {_WB}/>'
        # Collector (angled up)
        + _ln(20, 13, 36, 7)
        + _ln(36, 7, 36, 2)
        # Emitter (angled down)
        + _ln(20, 23, 36, 29)
        + _ln(36, 29, 36, 34)
        # NPN arrow (outward on emitter)
        + _poly("28,26 36,29 30,20")
    ),

    # ── Op-Amp: triangle with +/– inputs ─────────────────────────────────────
    "opamp": _svg(
        f'<polygon points="10,4 10,32 52,18" fill="none" stroke="{_C}" stroke-width="1.8" stroke-linejoin="round"/>'
        + _ln(2, 12, 10, 12)
        + _ln(2, 24, 10, 24)
        + _ln(52, 18, 58, 18)
        # + sign on non-inverting input
        + f'<line x1="16" y1="12" x2="22" y2="12" stroke="{_C}" stroke-width="1.5"/>'
        + f'<line x1="19" y1="9" x2="19" y2="15" stroke="{_C}" stroke-width="1.5"/>'
        # – sign on inverting input
        + f'<line x1="16" y1="24" x2="22" y2="24" stroke="{_C}" stroke-width="1.5"/>'
    ),

    # ── MCU: rectangle with 3 pins each side ─────────────────────────────────
    "mcu": _svg(
        f'<rect x="18" y="4" width="24" height="28" fill="none" stroke="{_C}" stroke-width="1.8" rx="2"/>'
        + _ln(2, 10, 18, 10) + _ln(2, 18, 18, 18) + _ln(2, 26, 18, 26)
        + _ln(42, 10, 58, 10) + _ln(42, 18, 58, 18) + _ln(42, 26, 58, 26)
    ),

    # ── LED: diode + two emission arrows ─────────────────────────────────────
    "led": _svg(
        _ln(2, 22, 14, 22)
        + _poly("14,12 14,32 34,22")
        + f'<line x1="34" y1="12" x2="34" y2="32" stroke="{_C}" stroke-width="2.2" stroke-linecap="round"/>'
        + _ln(34, 22, 50, 22)
        # Arrow 1
        + f'<line x1="37" y1="17" x2="44" y2="9" stroke="{_C}" stroke-width="1.4" stroke-linecap="round"/>'
        + _poly("40,8 45,8 43,13")
        # Arrow 2
        + f'<line x1="43" y1="17" x2="50" y2="9" stroke="{_C}" stroke-width="1.4" stroke-linecap="round"/>'
        + _poly("46,8 51,8 49,13")
    ),

    # ── Crystal: box between two vertical bars ────────────────────────────────
    "crystal": _svg(
        _ln(2, 18, 14, 18)
        + f'<line x1="14" y1="8" x2="14" y2="28" stroke="{_C}" stroke-width="2" stroke-linecap="round"/>'
        + f'<rect x="18" y="10" width="24" height="16" fill="none" stroke="{_C}" stroke-width="1.8" rx="1"/>'
        + f'<line x1="42" y1="8" x2="42" y2="28" stroke="{_C}" stroke-width="2" stroke-linecap="round"/>'
        + _ln(42, 18, 58, 18)
    ),

    # ── Relay: coil (rect+bumps) + NO switch contact ─────────────────────────
    "relay": _svg(
        # Coil left terminal
        _ln(2, 30, 8, 30)
        + f'<rect x="8" y="22" width="24" height="10" fill="none" stroke="{_C}" stroke-width="1.8" rx="2"/>'
        + (
            f'<path d="M10,30 Q12,24 14,30 Q16,24 18,30 Q20,24 22,30 Q24,24 26,30 Q28,24 30,30"'
            f' fill="none" stroke="{_C}" stroke-width="1.3" stroke-linecap="round"/>'
        )
        # Coil right terminal
        + _ln(32, 30, 38, 30)
        # Switch pivot → arm
        + _ln(38, 8, 38, 30)
        + _ln(38, 8, 54, 4)
        # NO fixed contact (open circle)
        + f'<circle cx="54" cy="10" r="2.5" fill="none" stroke="{_C}" stroke-width="1.5"/>'
        # External circuit lines
        + _ln(2, 8, 38, 8)
        + _ln(54, 10, 58, 10)
    ),

    # ── Sensor: concentric circles (generic sensing element) ─────────────────
    "sensor": _svg(
        f'<circle cx="30" cy="18" r="14" fill="none" stroke="{_C}" stroke-width="1.8"/>'
        + f'<circle cx="30" cy="18" r="7" fill="none" stroke="{_C}" stroke-width="1.5"/>'
        + f'<circle cx="30" cy="18" r="3" fill="{_C}"/>'
        + _ln(2, 18, 16, 18)
        + _ln(44, 18, 58, 18)
    ),
}
