"""Spec extraction helpers split out from scraper.py.

Holds the DigiKey attribute/spec parsing cluster: inline-pattern regexes, the
spec-map builders, alias matching, sanitisation and supply-voltage fallbacks.
scraper.py re-exports these names so the public ``digikey_scraper.scraper`` API
is unchanged.
"""

import re
from functools import lru_cache

from bs4 import BeautifulSoup

from .constants import (
    ATTRIBUTE_LABELS,
    NO_INFO,
    SPEC_GAIN_BANDWIDTH_PRODUCT,
    SPEC_INPUT_BIAS_CURRENT,
    SPEC_INPUT_OFFSET_VOLTAGE,
    SPEC_MANUFACTURER,
    SPEC_MOUNTING_TYPE,
    SPEC_OPERATING_TEMPERATURE,
    SPEC_OUTPUT_CURRENT_PER_CHANNEL,
    SPEC_SUPPLY_CURRENT,
    SPEC_SUPPLY_VOLTAGE_MAX,
    SPEC_SUPPLY_VOLTAGE_MIN,
)
from .text_utils import clean_text, flexible_label_pattern, normalize_key

ATTRIBUTE_STOP_PATTERN = "|".join(
    flexible_label_pattern(label)
    for label in sorted(set(ATTRIBUTE_LABELS), key=len, reverse=True)
)
HZ_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:hz|khz|mhz|ghz)\b", re.IGNORECASE)
CURRENT_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:pa|na|u?a|μa|µa|ma|a)\b", re.IGNORECASE)
VOLTAGE_PATTERN = re.compile(r"\b[±+\-]?\d+(?:\.\d+)?\s*(?:uv|μv|µv|mv|v)\b", re.IGNORECASE)
TEMPERATURE_PATTERN = re.compile(r"(?:-?\d+(?:\.\d+)?\s*(?:°c|c)|-?\d+\s*(?:to|~|-)\s*\d+)", re.IGNORECASE)
VALUE_TRAILING_PIPE_PATTERN = re.compile(r"\s*\|\s*$")


@lru_cache(maxsize=256)
def get_inline_value_pattern(alias: str) -> re.Pattern[str]:
    alias_pattern = flexible_label_pattern(alias)
    return re.compile(
        rf"{alias_pattern}\s*(?P<value>.+?)(?=\s+(?:{ATTRIBUTE_STOP_PATTERN})\s*|$)",
        re.IGNORECASE,
    )


def add_spec_value(spec_map: dict[str, str], key: str, value: str) -> None:
    key = clean_text(key).strip(":")
    value = clean_text(value)
    if key and value and key not in spec_map and key.lower() != value.lower():
        spec_map[key] = value


def extract_spec_map(soup: BeautifulSoup) -> dict[str, str]:
    spec_map: dict[str, str] = {}

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [clean_text(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
            if len(cells) >= 2:
                add_spec_value(spec_map, cells[0], " | ".join(cells[1:]))

    for item in soup.select("dl"):
        terms = item.find_all("dt")
        defs = item.find_all("dd")
        for term, definition in zip(terms, defs, strict=False):
            add_spec_value(
                spec_map,
                term.get_text(" ", strip=True),
                definition.get_text(" ", strip=True),
            )

    # DigiKey sometimes renders attributes as adjacent div/span text instead of simple table rows.
    for row in soup.select("[class*='attribute'], [class*='Attribute'], [data-testid*='attribute']"):
        pieces = [clean_text(text) for text in row.stripped_strings]
        pieces = [piece for piece in pieces if piece]
        if len(pieces) >= 2:
            if len(pieces) > 5:
                continue
            add_spec_value(spec_map, pieces[0], " | ".join(pieces[1:]))

    return spec_map


def find_spec_value(
    spec_map: dict[str, str],
    aliases: list[str],
    normalized_map: dict[str, str] | None = None,
) -> str:
    normalized_map = normalized_map or {normalize_key(key): value for key, value in spec_map.items()}

    for alias in aliases:
        normalized_alias = normalize_key(alias)
        if normalized_alias and normalized_alias in normalized_map:
            return normalized_map[normalized_alias]

    for alias in aliases:
        normalized_alias = normalize_key(alias)
        if not normalized_alias:
            continue
        for key, value in normalized_map.items():
            if key and (normalized_alias in key or key in normalized_alias):
                return value

    return NO_INFO


def find_inline_spec_value(page_text: str, aliases: list[str], *, text_is_clean: bool = False) -> str:
    text = page_text if text_is_clean else clean_text(page_text)

    for alias in aliases:
        pattern = get_inline_value_pattern(alias)
        match = pattern.search(text)
        if not match:
            continue

        value = clean_text(match.group("value"))
        value = VALUE_TRAILING_PIPE_PATTERN.sub("", value).strip()
        value = trim_inline_spec_value(value)
        if not inline_value_matches_alias(alias, value):
            continue
        if value and normalize_key(value) != normalize_key(alias):
            return value

    return NO_INFO


def inline_value_matches_alias(alias: str, value: str) -> bool:
    alias_key = normalize_key(alias)
    value_key = normalize_key(value)
    if not value or value == NO_INFO:
        return False

    if "gain bandwidth" in alias_key or "bandwidth" in alias_key or normalize_key(SPEC_GAIN_BANDWIDTH_PRODUCT) in alias_key:
        return bool(HZ_PATTERN.search(value))

    if "input bias" in alias_key or normalize_key(SPEC_INPUT_BIAS_CURRENT) in alias_key:
        return bool(CURRENT_PATTERN.search(value))

    if "input offset" in alias_key:
        return bool(VOLTAGE_PATTERN.search(value))

    if "current" in alias_key or "전류" in alias_key:
        return bool(CURRENT_PATTERN.search(value))

    if "voltage" in alias_key or "전압" in alias_key:
        return bool(VOLTAGE_PATTERN.search(value))

    if "temperature" in alias_key or "온도" in alias_key:
        return bool(TEMPERATURE_PATTERN.search(value))

    if "manufacturer" in alias_key:
        bad_values = [
            "supplier device package",
            "base product number",
            "package",
            "mounting type",
        ]
        return not any(bad_value in value_key for bad_value in bad_values)

    return True


def spec_value_matches_label(label: str, value: str) -> bool:
    if not value or value == NO_INFO:
        return False

    label_key = normalize_key(label)
    value_key = normalize_key(value)

    if label == SPEC_GAIN_BANDWIDTH_PRODUCT:
        return bool(HZ_PATTERN.search(value))

    if label == SPEC_INPUT_BIAS_CURRENT:
        return bool(CURRENT_PATTERN.search(value))

    if label == SPEC_INPUT_OFFSET_VOLTAGE or "input offset" in label_key:
        return bool(VOLTAGE_PATTERN.search(value))

    if label in {SPEC_SUPPLY_CURRENT, SPEC_OUTPUT_CURRENT_PER_CHANNEL}:
        return bool(CURRENT_PATTERN.search(value))

    if label in {SPEC_SUPPLY_VOLTAGE_MIN, SPEC_SUPPLY_VOLTAGE_MAX}:
        return bool(VOLTAGE_PATTERN.search(value))

    if label == SPEC_OPERATING_TEMPERATURE:
        return bool(TEMPERATURE_PATTERN.search(value))

    if label == SPEC_MANUFACTURER or "manufacturer" in label_key:
        bad_values = [
            "supplier device package",
            "base product number",
            "package",
            "mounting type",
            "14-soic",
            "tlc274",
        ]
        return not any(bad_value in value_key for bad_value in bad_values)

    if label == SPEC_MOUNTING_TYPE:
        return any(
            mounting_value in value_key
            for mounting_value in [
                "surface mount",
                "smd",
                "smt",
                "through hole",
                "through - hole",
                "through-hole",
                "스루홀",
                "표면실장",
            ]
        )

    return True


def normalize_mounting_type(value: str) -> str:
    value_key = normalize_key(value)
    if any(token in value_key for token in ["surface mount", "smd", "smt", "표면실장"]):
        return "SMD"
    if any(token in value_key for token in ["through hole", "through - hole", "through-hole", "스루홀"]):
        return "Through hole"
    return value


def sanitize_specs(specs: dict[str, str]) -> dict[str, str]:
    sanitized = dict(specs)
    for label, value in list(sanitized.items()):
        if not spec_value_matches_label(label, value):
            sanitized[label] = NO_INFO
        elif label == SPEC_MOUNTING_TYPE:
            sanitized[label] = normalize_mounting_type(value)
    return sanitized


def trim_inline_spec_value(value: str) -> str:
    value = clean_text(value)
    stop_words = [
        "Report Product Information Error",
        "Documents & Media",
        "Datasheets",
        "PCN ",
        "Featured Product",
        "EDA Models",
        "Environmental & Export Classifications",
        "Product Questions and Answers",
        "Additional Resources",
    ]
    for stop_word in stop_words:
        index = value.lower().find(stop_word.lower())
        if index > 0:
            value = value[:index].strip()

    value_pattern = re.compile(
        r"^[±+-]?\d+(?:\.\d+)?\s*(?:pA|nA|μA|µA|uA|mA|A|μV|µV|uV|mV|V|Hz|kHz|MHz|GHz|°C|C|V/μs|V/µs|V/us)"
        r"(?:\s*(?:to|~|-|/|,|±)\s*[±+-]?\d+(?:\.\d+)?\s*(?:pA|nA|μA|µA|uA|mA|A|μV|µV|uV|mV|V|Hz|kHz|MHz|GHz|°C|C|V/μs|V/µs|V/us))*",
        re.IGNORECASE,
    )
    match = value_pattern.match(value)
    if match:
        return clean_text(match.group(0))

    short_text = re.match(r"^[A-Za-z0-9+±°μµ/().,\- ]{1,80}", value)
    if short_text:
        return clean_text(short_text.group(0))

    return value


def split_voltage_range(value: str) -> tuple[str, str]:
    voltages = re.findall(r"[±+-]?\d+(?:\.\d+)?\s*(?:mV|V)", value, flags=re.IGNORECASE)
    single_supply_values = [voltage for voltage in voltages if not voltage.strip().startswith(("±", "-"))]
    if len(single_supply_values) >= 2:
        return single_supply_values[0], single_supply_values[1]
    if len(voltages) >= 2:
        return voltages[0], voltages[1]
    return NO_INFO, NO_INFO


def apply_spec_fallbacks(
    specs: dict[str, str],
    spec_map: dict[str, str],
    normalized_map: dict[str, str] | None = None,
) -> None:
    combined_supply = find_spec_value(
        spec_map,
        [
            "전압 - 공급, 단일/이중(±)",
            "전압 - 전원, 단일/이중(±)",
            "voltage - supply, single/dual (±)",
            "voltage - supply, single/dual (+/-)",
            "voltage - supply span",
            "voltage - supply",
        ],
        normalized_map=normalized_map,
    )

    if combined_supply != NO_INFO:
        min_voltage, max_voltage = split_voltage_range(combined_supply)
        if specs.get(SPEC_SUPPLY_VOLTAGE_MIN) in {NO_INFO, combined_supply}:
            specs[SPEC_SUPPLY_VOLTAGE_MIN] = min_voltage
        if specs.get(SPEC_SUPPLY_VOLTAGE_MAX) in {NO_INFO, combined_supply}:
            specs[SPEC_SUPPLY_VOLTAGE_MAX] = max_voltage


def extract_specs(soup: BeautifulSoup, aliases: dict[str, list[str]]) -> dict[str, str]:
    spec_map = extract_spec_map(soup)
    normalized_map = {normalize_key(key): value for key, value in spec_map.items()}
    specs = {
        label: find_spec_value(spec_map, alias_list, normalized_map=normalized_map)
        for label, alias_list in aliases.items()
    }
    page_text = clean_text(soup.get_text(" ", strip=True))

    for label, alias_list in aliases.items():
        current_value = specs.get(label, NO_INFO)
        if current_value != NO_INFO and spec_value_matches_label(label, current_value):
            continue
        specs[label] = NO_INFO
        specs[label] = find_inline_spec_value(page_text, alias_list, text_is_clean=True)

    apply_spec_fallbacks(specs, spec_map, normalized_map=normalized_map)

    combined_supply = find_inline_spec_value(
        page_text,
        [
            "Voltage - Supply Span",
            "Voltage - Supply",
            "전압 - 공급, 단일/이중(±)",
            "전압 - 전원, 단일/이중(±)",
        ],
        text_is_clean=True,
    )
    if combined_supply != NO_INFO:
        min_voltage, max_voltage = split_voltage_range(combined_supply)
        if specs.get(SPEC_SUPPLY_VOLTAGE_MIN) in {NO_INFO, combined_supply}:
            specs[SPEC_SUPPLY_VOLTAGE_MIN] = min_voltage
        if specs.get(SPEC_SUPPLY_VOLTAGE_MAX) in {NO_INFO, combined_supply}:
            specs[SPEC_SUPPLY_VOLTAGE_MAX] = max_voltage

    return sanitize_specs(specs)
