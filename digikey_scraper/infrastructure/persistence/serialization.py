"""Shared (de)serialization between ProductResult and plain dicts."""

from __future__ import annotations

from ...domain.models import ProductResult


def result_to_dict(r: ProductResult) -> dict:
    return {
        "query": r.query,
        "title": r.title,
        "product_url": r.product_url,
        "datasheet_url": r.datasheet_url,
        "part_number": r.part_number,
        "price_rows": list(r.price_rows),
        "specs": dict(r.specs),
        "error": r.error,
        "candidate_results": [result_to_dict(c) for c in r.candidate_results],
    }


def result_from_dict(d: dict) -> ProductResult:
    return ProductResult(
        query=d.get("query", ""),
        title=d.get("title", ""),
        product_url=d.get("product_url", ""),
        datasheet_url=d.get("datasheet_url", ""),
        part_number=d.get("part_number"),
        price_rows=list(d.get("price_rows", [])),
        specs=dict(d.get("specs", {})),
        error=d.get("error"),
        candidate_results=[result_from_dict(c) for c in d.get("candidate_results", [])],
    )
