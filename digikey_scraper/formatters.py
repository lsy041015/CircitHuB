from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from .constants import CANDIDATE_SPEC_ALIASES, MAIN_SPEC_ALIASES, NO_INFO, SEPARATOR
from .i18n import normalize_language, result_text

if TYPE_CHECKING:
    from .models import ProductResult


def display_value(value: str | None, language: str) -> str:
    if not value or value == NO_INFO:
        return result_text(language, "no_info")
    return value


def format_candidate_lines(result: ProductResult, language: str = "ko") -> list[str]:
    language = normalize_language(language)
    lines = [
        f"{result_text(language, 'product_name')}: {display_value(result.title, language)}",
        f"DigiKey Part Number: {display_value(result.part_number, language)}",
    ]
    for label in CANDIDATE_SPEC_ALIASES:
        lines.append(f"{label}: {display_value(result.specs.get(label), language)}")
    return lines


def format_result_text(
    result: ProductResult,
    language: str = "ko",
    requested_quantity: int | None = None,
) -> str:
    language = normalize_language(language)
    if result.candidate_results:
        lines = [
            f"{result_text(language, 'search_term')}: {result.query}",
            "",
            result_text(language, "candidate_notice"),
        ]
        for index, candidate in enumerate(result.candidate_results, start=1):
            lines.append("")
            lines.append(f"[{result_text(language, 'candidate', index=index)}]")
            lines.extend(format_candidate_lines(candidate, language))
        return "\n".join(lines)

    if result.error:
        return f"{result_text(language, 'search_term')}: {result.query}\n\n{result_text(language, 'error')}: {result.error}"

    lines = [
        f"{result_text(language, 'search_term')}: {result.query}",
        f"{result_text(language, 'product_name')}: {result.title}",
        f"{result_text(language, 'detail_page')}: {result.product_url}",
    ]
    if requested_quantity is not None:
        lines.insert(1, f"{result_text(language, 'requested_quantity')}: {requested_quantity}")
    if result.part_number:
        lines.append(f"DigiKey Part Number: {result.part_number}")

    lines.append("")
    lines.append(f"[{result_text(language, 'price_info')}]")
    lines.extend(result.price_rows[:10] or [result_text(language, "price_missing")])

    lines.append("")
    lines.append(f"[{result_text(language, 'main_info')}]")
    for label in MAIN_SPEC_ALIASES:
        lines.append(f"{label}: {display_value(result.specs.get(label), language)}")

    return "\n".join(lines)


def format_results_text(
    results: Iterable[ProductResult],
    language: str = "ko",
    quantities: dict[str, int] | None = None,
) -> str:
    quantities = quantities or {}
    return f"\n{SEPARATOR}\n".join(
        format_result_text(result, language, quantities.get(result.query)) for result in results
    )
