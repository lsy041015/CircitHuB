import re
from functools import lru_cache


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=8192)
def normalize_key(text: str) -> str:
    text = clean_text(text).lower()
    text = text.replace("–", "-").replace("—", "-").replace("_", " ")
    text = text.replace("±", "+/-").replace("μ", "u").replace("µ", "u")
    text = re.sub(r"\s*/\s*", " / ", text)
    text = re.sub(r"\s*-\s*", " - ", text)
    text = re.sub(r"[^a-z0-9가-힣+/() -]", " ", text)
    text = re.sub(r"\s+-\s+", " ", text)
    return clean_text(text)


def normalize_part(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def flexible_label_pattern(label: str) -> str:
    pattern = re.escape(label)
    pattern = pattern.replace(r"\ ", r"\s*")
    pattern = pattern.replace(r"\-", r"\s*-\s*")
    pattern = pattern.replace(r"\/", r"\s*/\s*")
    pattern = pattern.replace(r"\±", r"(?:±|\+/-)")
    return pattern
