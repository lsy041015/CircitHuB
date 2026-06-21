"""Pluggable supplier registry.

Maps a supplier name to a factory producing a SupplierScraper. The P1 seed for
multi-supplier support (WS-1): adding Mouser/LCSC later means registering a new
factory here, with no change to the application layer.
"""

from __future__ import annotations

from collections.abc import Callable

from ...domain.ports import SupplierScraper

SupplierFactory = Callable[..., SupplierScraper]


class SupplierRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, SupplierFactory] = {}

    def register(self, name: str, factory: SupplierFactory) -> None:
        self._factories[name] = factory

    def create(self, name: str, **kwargs) -> SupplierScraper:
        if name not in self._factories:
            raise KeyError(f"unknown supplier: {name!r} (known: {self.names()})")
        return self._factories[name](**kwargs)

    def names(self) -> list[str]:
        return sorted(self._factories)


def default_registry() -> SupplierRegistry:
    """Registry preloaded with the built-in DigiKey supplier."""
    from .selenium_supplier import SeleniumDigiKeyScraper

    reg = SupplierRegistry()
    reg.register(
        "digikey",
        lambda show_browser=False: SeleniumDigiKeyScraper(show_browser=show_browser),
    )

    def _make_local(catalog_path, source="local"):
        from .local_catalog import LocalCatalogSupplier

        return LocalCatalogSupplier(catalog_path, source=source)

    reg.register("local", _make_local)
    return reg
