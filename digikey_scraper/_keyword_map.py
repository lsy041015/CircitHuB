"""Maps component-type keywords (Korean/English) to DigiKey category filter URLs."""
from __future__ import annotations

from typing import TypedDict


class Category(TypedDict):
    key: str
    label_ko: str
    label_en: str
    icon: str
    url: str


BASE = "https://www.digikey.com"

CATEGORIES: list[Category] = [
    {
        "key": "resistor",
        "label_ko": "저항",
        "label_en": "Resistor",
        "icon": "Ω",
        "url": f"{BASE}/en/products/filter/chip-resistors/52",
    },
    {
        "key": "capacitor",
        "label_ko": "커패시터",
        "label_en": "Capacitor",
        "icon": "C",
        "url": f"{BASE}/en/products/filter/ceramic-capacitors/60",
    },
    {
        "key": "inductor",
        "label_ko": "인덕터",
        "label_en": "Inductor",
        "icon": "L",
        "url": f"{BASE}/en/products/filter/fixed-inductors/71",
    },
    {
        "key": "diode",
        "label_ko": "다이오드",
        "label_en": "Diode",
        "icon": "▷|",
        "url": f"{BASE}/en/products/filter/rectifier-diodes/288",
    },
    {
        "key": "mosfet",
        "label_ko": "MOSFET",
        "label_en": "MOSFET",
        "icon": "⊣",
        "url": f"{BASE}/en/products/filter/single-mosfets/225",
    },
    {
        "key": "bjt",
        "label_ko": "BJT",
        "label_en": "BJT",
        "icon": "⊿",
        "url": f"{BASE}/en/products/filter/bipolar-transistors-bjt/73",
    },
    {
        "key": "opamp",
        "label_ko": "오퍼앰프",
        "label_en": "Op-Amp",
        "icon": "△",
        "url": f"{BASE}/en/products/filter/instrumentation-op-amps-buffer-amps/687",
    },
    {
        "key": "mcu",
        "label_ko": "MCU",
        "label_en": "MCU",
        "icon": "□",
        "url": f"{BASE}/en/products/filter/microcontrollers/78",
    },
    {
        "key": "led",
        "label_ko": "LED",
        "label_en": "LED",
        "icon": "◉",
        "url": f"{BASE}/en/products/filter/standard-leds-through-hole/94",
    },
    {
        "key": "crystal",
        "label_ko": "크리스탈",
        "label_en": "Crystal",
        "icon": "◇",
        "url": f"{BASE}/en/products/filter/crystals/171",
    },
    {
        "key": "relay",
        "label_ko": "릴레이",
        "label_en": "Relay",
        "icon": "⎍",
        "url": f"{BASE}/en/products/filter/power-relays-over-2-amps/196",
    },
    {
        "key": "sensor",
        "label_ko": "센서",
        "label_en": "Sensor",
        "icon": "◈",
        "url": f"{BASE}/en/products/filter/optical-sensors-photodiodes/543",
    },
]

# Build lookup index: all keys + Korean + English labels → category dict
_INDEX: dict[str, Category] = {}
for _cat in CATEGORIES:
    _INDEX[_cat["key"].lower()] = _cat
    _INDEX[_cat["label_ko"].lower()] = _cat
    _INDEX[_cat["label_en"].lower()] = _cat


def lookup_category(text: str) -> Category | None:
    """Return category dict if text matches a known keyword (case-insensitive), else None."""
    return _INDEX.get(text.strip().lower())
