from __future__ import annotations

from collections.abc import Callable

Translator = Callable[[str], str]


def category_badge_text(tr: Callable[..., str], label: str) -> str:
    if label:
        return tr("category_last_badge", label=label)
    return tr("category_last_badge_idle")


def category_strip_payload(
    tr: Callable[..., str],
    stage: str,
    *,
    label: str = "",
    count: int = 0,
    error: str = "",
) -> tuple[str, str, str, int]:
    if stage == "searching":
        return (
            "searching",
            tr("category_searching_main", label=label),
            tr("category_searching_detail", label=label),
            15,
        )
    if stage == "success":
        return (
            "success",
            tr("category_success_main", count=count),
            tr("category_success_detail", label=label),
            100,
        )
    if stage == "empty":
        return (
            "cancelled",
            tr("category_empty_main"),
            tr("category_empty_detail", label=label),
            100,
        )
    if stage == "error":
        return (
            "error",
            tr("category_error_main", label=label or tr("category_title")),
            tr("category_error_detail", error=error),
            100,
        )
    return ("neutral", tr("category_idle_main"), tr("category_idle_detail"), 0)


def category_result_payload(
    tr: Callable[..., str],
    stage: str,
    *,
    label: str = "",
    error: str = "",
) -> tuple[str, str]:
    if stage == "searching":
        return (
            tr("category_searching_result_title", label=label),
            tr("category_searching_result_detail", label=label),
        )
    if stage == "empty":
        return (
            tr("category_empty_result_title", label=label),
            tr("category_empty_result_detail", label=label),
        )
    if stage == "error":
        return (
            tr("category_error_result_title", label=label or tr("category_title")),
            tr("category_error_result_detail", error=error),
        )
    return (
        tr("category_idle_result_title"),
        tr("category_idle_result_detail"),
    )
