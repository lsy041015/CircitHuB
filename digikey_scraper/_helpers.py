import os
import re
from pathlib import Path

from .domain.pricing import (
    BOM_SAMPLE_QTY,
    extract_unit_price,
    price_rows,
)
from .domain.pricing import (
    calc_bom_total as _calc_bom_total,
)

SETTINGS_FILE = "app_settings.json"
AUTO_SAVE_DIR = "auto_saved_results"

__all__ = [
    "SETTINGS_FILE",
    "AUTO_SAVE_DIR",
    "BOM_SAMPLE_QTY",
    "app_data_dir",
    "runtime_path",
    "split_part_tokens",
    "price_rows",
    "extract_unit_price",
    "_calc_bom_total",
]


def app_data_dir() -> Path:
    override = os.environ.get("DIGIKEY_SCRAPER_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "").strip()
        if local:
            return Path(local).expanduser() / "DigiKeyPriceScraper"
        roaming = os.environ.get("APPDATA", "").strip()
        if roaming:
            return Path(roaming).expanduser() / "DigiKeyPriceScraper"
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    if xdg:
        return Path(xdg).expanduser() / "digikey_price_scraper"
    return Path.home() / ".local" / "share" / "digikey_price_scraper"


def runtime_path(*parts: str) -> Path:
    return app_data_dir().joinpath(*parts)


def split_part_tokens(text: str) -> list[str]:
    return [t.strip().upper() for t in re.split(r"[,;\s\n\r\t]+", text) if t.strip()]


_NOISY_PART_QUERY_TOKENS = {
    "DETAILS",
    "IC",
    "OPAMP",
    "CIRCUIT",
    "RELAY",
    "AUDIO",
}


def normalize_part_query(text: str) -> str:
    clean = " ".join(str(text).strip().split())
    if not clean:
        return ""

    upper = clean.upper()
    if upper in _NOISY_PART_QUERY_TOKENS:
        return ""
    if upper.startswith("$"):
        return ""

    noisy_card = ("DETAILS" in upper) or ("$" in clean)
    if noisy_card and len(clean.split()) >= 4:
        first = clean.split()[0].strip().upper()
        return first if first and first not in _NOISY_PART_QUERY_TOKENS else ""

    return upper
