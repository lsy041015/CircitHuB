"""Canonical domain models.

The dataclasses physically live in ``digikey_scraper.models`` for backward
compatibility (existing imports and tests use that path). This module is the
layered/canonical import surface; both refer to the same objects.
"""

from __future__ import annotations

from ..models import CategoryLink, ProductLink, ProductResult

__all__ = ["CategoryLink", "ProductLink", "ProductResult"]
