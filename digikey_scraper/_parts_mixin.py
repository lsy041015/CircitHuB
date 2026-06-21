"""Part-number suggestion + autocompletion for MainWindow, as a mixin.

Extracted from _main_window. The pure ranking helpers and suggestion
corpus live here too; methods rely on MainWindow attributes
(_chip_input, parts, favorites, history, result_repository) and the
helper ``_default_parts``.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QCoreApplication, QTimer, QStringListModel, Qt
from PySide6.QtWidgets import QCompleter

from ._helpers import normalize_part_query

COMMON_PART_SUGGESTIONS = (
    "LM358P", "LM358N", "LM324N", "LM393N", "LM741CN", "NE5532P", "TL072CP",
    "TL082CP", "OPA2134PA", "MCP6002-I/P", "LM386N-1",
    "LM7805", "LM7812", "LM7905", "AMS1117-3.3", "AMS1117-5.0", "LM1117T-3.3",
    "LD1117V33", "TPS5430", "MP1584EN", "XL4015E1",
    "1N4148", "1N4001", "1N4007", "SS14", "SS34", "BAT54", "BAV99", "MB6S",
    "2N2222A", "2N3904", "2N3906", "BC547B", "BC557B", "S8050", "S8550",
    "IRFZ44N", "IRLZ44N", "IRF540N", "AO3400A", "AO3401A", "BSS138",
    "2N7000", "FQP30N06L",
    "ATMEGA328P-PU", "STM32F103C8T6", "ESP32-WROOM-32E", "CH340G", "CP2102N",
    "ULN2003A", "ULN2803A", "L293D", "DRV8833", "MAX232CPE", "SN74HC595N",
    "74HC00N", "74HC04N", "74HC14N", "74HC138N", "74HC245N", "PC817",
    "HC-SR04", "DS18B20", "DHT22", "MPU6050", "SSD1306",
)

SUGGESTION_ALIASES = {
    "OPAMP": ("LM358P", "LM324N", "TL072CP", "NE5532P", "OPA2134PA", "MCP6002-I/P"),
    "AMP": ("LM358P", "LM386N-1", "NE5532P", "TL072CP"),
    "REG": ("LM7805", "AMS1117-3.3", "LM1117T-3.3", "TPS5430", "MP1584EN"),
    "LDO": ("AMS1117-3.3", "AMS1117-5.0", "LM1117T-3.3", "LD1117V33"),
    "DIODE": ("1N4148", "1N4007", "SS14", "BAT54", "BAV99"),
    "LED": ("1N4148", "SS14", "PC817"),
    "NPN": ("2N2222A", "2N3904", "BC547B", "S8050"),
    "PNP": ("2N3906", "BC557B", "S8550"),
    "BJT": ("2N2222A", "2N3904", "2N3906", "BC547B"),
    "MOSFET": ("IRFZ44N", "IRLZ44N", "AO3400A", "BSS138", "2N7000"),
    "MCU": ("ATMEGA328P-PU", "STM32F103C8T6", "ESP32-WROOM-32E"),
    "USB": ("CH340G", "CP2102N", "MAX232CPE"),
    "LOGIC": ("SN74HC595N", "74HC00N", "74HC04N", "74HC14N", "74HC245N"),
    "DRIVER": ("ULN2003A", "ULN2803A", "L293D", "DRV8833"),
    "SENSOR": ("HC-SR04", "DS18B20", "DHT22", "MPU6050"),
}


def _suggestion_key(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _edit_distance_limited(left: str, right: str, limit: int = 4) -> int:
    if abs(len(left) - len(right)) > limit:
        return limit + 1
    previous = list(range(len(right) + 1))
    for i, ca in enumerate(left, start=1):
        current = [i]
        row_min = current[0]
        for j, cb in enumerate(right, start=1):
            cost = 0 if ca == cb else 1
            value = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            current.append(value)
            row_min = min(row_min, value)
        if row_min > limit:
            return limit + 1
        previous = current
    return previous[-1]


def _subsequence_gap(needle: str, key: str) -> int | None:
    pos = -1
    gap = 0
    for char in needle:
        next_pos = key.find(char, pos + 1)
        if next_pos < 0:
            return None
        if pos >= 0:
            gap += next_pos - pos - 1
        pos = next_pos
    return gap


def _spell_match_score(needle: str, key: str) -> tuple[int, int] | None:
    if not needle or not key:
        return None

    limit = 1 if len(needle) <= 4 else 2 if len(needle) <= 7 else 3
    lengths = {len(needle)}
    if len(needle) > 2:
        lengths.update({len(needle) - 1, len(needle) + 1})

    best: tuple[int, int] | None = None
    for length in sorted(lengths):
        if length <= 0:
            continue
        max_start = max(len(key) - length, 0)
        for start in range(max_start + 1):
            segment = key[start:start + length]
            if not segment:
                continue
            distance = _edit_distance_limited(needle, segment, limit)
            if distance <= limit:
                candidate = (distance, start)
                if best is None or candidate < best:
                    best = candidate
    return best


class PartSuggestionsMixin:
    def _setup_part_completer(self):
        self._part_suggestion_model = QStringListModel(self)
        self._part_completer = QCompleter(self._part_suggestion_model, self)
        self._part_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._part_completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self._part_completer.setMaxVisibleItems(8)
        self._part_completer.activated.connect(self._accept_part_suggestion)
        self._chip_input.setCompleter(self._part_completer)
        self._refresh_part_suggestions()

    def _part_suggestion_pool(self) -> list[str]:
        suggestions = list(COMMON_PART_SUGGESTIONS)
        for part in self._default_parts() + self.parts:
            name = normalize_part_query(part.get("name", ""))
            if name:
                suggestions.append(name)
        suggestions.extend(
            name for item in self.favorites if (name := normalize_part_query(item))
        )
        for _label, queries, _meta, _status in self.history:
            suggestions.extend(
                name for query in queries if (name := normalize_part_query(query))
            )
        try:
            for record in self.result_repository.recent_searches(limit=30):
                for query in record.get("queries", []):
                    clean = normalize_part_query(query)
                    if clean:
                        suggestions.append(clean)
        except Exception:
            pass
        seen: set[str] = set()
        out: list[str] = []
        for item in suggestions:
            if item and item not in seen:
                seen.add(item)
                out.append(item)
        return out

    def _part_suggestions(self, text: str = "") -> list[str]:
        needle = _suggestion_key(text)
        pool = self._part_suggestion_pool()
        if not needle:
            # text has content but no alphanumeric (e.g. Korean "저항") → no useful matches
            return [] if text.strip() else pool[:8]

        alias_hits: set[str] = set()
        for alias, parts in SUGGESTION_ALIASES.items():
            if alias.startswith(needle) or needle in alias:
                alias_hits.update(parts)

        def score(item: str) -> tuple[int, int, int, str]:
            key = _suggestion_key(item)
            if key.startswith(needle):
                return (0, len(key) - len(needle), len(key), item)
            if needle in key:
                return (1, key.index(needle), len(key), item)

            spell_score = _spell_match_score(needle, key)
            if spell_score is not None:
                distance, start = spell_score
                return (2, distance, start, item)

            gap = _subsequence_gap(needle, key)
            if gap is not None and gap <= max(2, len(key) // 3):
                return (3, gap, len(key), item)

            if item in alias_hits:
                return (4, len(key), len(key), item)
            return (9, len(key), len(key), item)

        ranked = [item for item in pool if score(item)[0] < 9]
        return sorted(ranked, key=score)

    def _refresh_part_suggestions(self, text: str = ""):
        if self._part_suggestion_model is not None:
            self._part_suggestion_model.setStringList(self._part_suggestions(text))
        if text and self._part_completer is not None and self._chip_input.hasFocus():
            self._part_completer.complete()

    def _accept_part_suggestion(self, text: str):
        clean = str(text).strip().upper()
        if not clean:
            return
        self._skip_next_chip_commit = True
        self._chip_input.clear()
        self.add_part(clean)
        if QCoreApplication.instance() is not None:
            QTimer.singleShot(0, self._chip_input.clear)
