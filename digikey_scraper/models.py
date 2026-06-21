from dataclasses import dataclass, field


@dataclass
class ProductLink:
    name: str
    url: str
    description: str = ""


@dataclass
class CategoryLink:
    name: str
    url: str
    count: int


@dataclass
class ProductResult:
    query: str
    title: str = ""
    product_url: str = ""
    datasheet_url: str = ""
    part_number: str | None = None
    price_rows: list[str] = field(default_factory=list)
    specs: dict[str, str] = field(default_factory=dict)
    candidate_results: list["ProductResult"] = field(default_factory=list)
    error: str | None = None
    scraped_at: float | None = None  # epoch seconds when this result was fetched (price freshness)

    def to_text(self, language: str = "ko") -> str:
        from .formatters import format_result_text

        return format_result_text(self, language)

    def to_candidate_lines(self, language: str = "ko") -> list[str]:
        from .formatters import format_candidate_lines

        return format_candidate_lines(self, language)
