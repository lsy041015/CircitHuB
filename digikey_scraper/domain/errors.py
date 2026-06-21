"""Domain-level errors. Keep framework exceptions out of application/domain layers."""

from __future__ import annotations


class ScrapeError(Exception):
    """Base class for scraping failures surfaced to the application layer."""


class ScrapeTimeout(ScrapeError):
    """Raised when a supplier page fails to load within the timeout."""


class ScrapeBlocked(ScrapeError):
    """Raised when the supplier blocks automated access."""
