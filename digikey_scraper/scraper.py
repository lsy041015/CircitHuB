import re
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Spec-extraction helpers live in _scraper_specs; re-exported here so the public
# ``digikey_scraper.scraper`` API (and existing imports) stay unchanged.
from ._scraper_specs import (
    add_spec_value,
    apply_spec_fallbacks,
    extract_spec_map,
    extract_specs,
    find_inline_spec_value,
    find_spec_value,
    get_inline_value_pattern,
    inline_value_matches_alias,
    normalize_mounting_type,
    sanitize_specs,
    spec_value_matches_label,
    split_voltage_range,
    trim_inline_spec_value,
)
from .constants import (
    BASE_URL,
    CANDIDATE_SPEC_ALIASES,
    MAIN_SPEC_ALIASES,
    NO_INFO,
    PRICE_PATTERN,
    SEARCH_URL,
)
from .driver import get_page_soup
from .models import CategoryLink, ProductLink, ProductResult
from .text_utils import clean_text, normalize_part

__all__ = [
    "add_spec_value",
    "apply_spec_fallbacks",
    "extract_spec_map",
    "extract_specs",
    "find_inline_spec_value",
    "find_spec_value",
    "get_inline_value_pattern",
    "inline_value_matches_alias",
    "normalize_mounting_type",
    "sanitize_specs",
    "spec_value_matches_label",
    "split_voltage_range",
    "trim_inline_spec_value",
]

DETAIL_LINK_SELECTORS = (
    "a[href*='/products/detail/']",
    "a[href*='/product-detail/']",
    "a[data-testid*='product'][href]",
    "a[data-testid*='part'][href]",
    "[data-testid*='product'] a[href]",
    "[class*='product'] a[href]",
    "[class*='Product'] a[href]",
)
DETAIL_LINK_SELECTOR = ", ".join(DETAIL_LINK_SELECTORS)
SEARCH_BLOCKED_PATTERNS = (
    "access denied",
    "captcha",
    "verify you are human",
    "unusual traffic",
    "request blocked",
    "403 forbidden",
    "cloudflare",
    "보안 확인",
    "잠시만 기다리",
    "enable javascript and cookies",
    "ray id",
)
NO_RESULTS_PATTERNS = (
    "no results",
    "0 results",
    "did not match",
    "no products found",
    "검색 결과가 없습니다",
)


def is_blocked_search_page(soup: BeautifulSoup) -> bool:
    text = clean_text(soup.get_text(" ", strip=True)).lower()
    title = clean_text(soup.title.get_text(" ", strip=True)).lower() if soup.title else ""
    return title == "just a moment..." or any(pattern in text for pattern in SEARCH_BLOCKED_PATTERNS)


def extract_name_from_url(url: str) -> str:
    parts = [part for part in url.split("/") if part]
    if len(parts) >= 2:
        return parts[-2]
    return url


def choose_product_link_name(link_text: str, url: str) -> str:
    raw = clean_text(link_text)
    fallback = clean_text(extract_name_from_url(url))
    if not raw:
        return fallback
    if not fallback:
        return raw

    raw_key = normalize_part(raw)
    fallback_key = normalize_part(fallback)
    noisy_markers = ("DETAILS" in raw.upper()) or ("$" in raw) or (" " in raw)
    if fallback_key and raw_key != fallback_key and (fallback_key in raw_key or noisy_markers):
        return fallback
    return raw


def is_detail_url(url: str) -> bool:
    return "/products/detail/" in url or "/product-detail/" in url


def is_category_url(url: str) -> bool:
    return "/products/filter/" in url or "/products/category/" in url


def candidate_matches_query(candidate: ProductLink, query: str) -> bool:
    normalized_query = normalize_part(query)
    searchable = f"{candidate.name} {candidate.description}"
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-./]*", searchable)
    return any(normalize_part(token) == normalized_query for token in tokens)


def extract_largest_number(text: str) -> int:
    numbers = [int(value.replace(",", "")) for value in re.findall(r"\b\d[\d,]*\b", text)]
    return max(numbers) if numbers else 0


def classify_search_page_issue(soup: BeautifulSoup) -> str:
    text = clean_text(soup.get_text(" ", strip=True)).lower()
    if is_blocked_search_page(soup):
        return "DigiKey가 자동화 접근을 차단했거나 확인 페이지를 표시했습니다."
    if any(pattern in text for pattern in NO_RESULTS_PATTERNS):
        return "검색어와 일치하는 제품이 없습니다."
    if soup.find_all("table") or soup.find_all("a", href=True):
        return "검색 결과 페이지 구조가 변경되어 제품 링크를 찾지 못했습니다."
    return "검색 결과 페이지를 불러왔지만 제품 링크를 찾지 못했습니다."


def extract_product_links_from_soup(soup: BeautifulSoup, limit: int = 10) -> list[ProductLink]:
    products: list[ProductLink] = []
    seen_urls = set()

    for link in soup.select(DETAIL_LINK_SELECTOR):
        href = link.get("href")
        if not href:
            continue

        url = urljoin(BASE_URL, href)
        if url in seen_urls or not is_detail_url(url):
            continue

        row = link.find_parent("tr")
        container = row or link.find_parent(["article", "section", "li", "div"])
        description = clean_text(container.get_text(" ", strip=True)) if container else clean_text(link.get_text(" ", strip=True))
        products.append(
            ProductLink(
                name=choose_product_link_name(link.get_text(" ", strip=True), url),
                url=url,
                description=description,
            )
        )
        seen_urls.add(url)

        if len(products) >= limit:
            break

    return products


def find_top_results_container(soup: BeautifulSoup):
    heading_pattern = re.compile(r"\btop\s+results\b", re.IGNORECASE)

    for node in soup.find_all(string=heading_pattern):
        parent = node.parent
        for _ in range(5):
            if parent is None:
                break

            links = parent.find_all("a", href=True)
            category_links = [link for link in links if is_category_url(link["href"])]
            if category_links:
                return parent
            parent = parent.parent

    return None


def get_top_results_category_links(driver: webdriver.Chrome) -> list[CategoryLink]:
    soup = get_page_soup(driver)
    container = find_top_results_container(soup)
    if container is None:
        return []

    categories: list[CategoryLink] = []
    seen_urls = set()

    for anchor in container.find_all("a", href=True):
        href = anchor["href"]
        if not is_category_url(href):
            continue

        url = urljoin(BASE_URL, href)
        if url in seen_urls:
            continue

        parent_text = clean_text(anchor.find_parent().get_text(" ", strip=True)) if anchor.find_parent() else ""
        name = clean_text(anchor.get_text(" ", strip=True)) or extract_name_from_url(url)
        count = extract_largest_number(parent_text)
        categories.append(CategoryLink(name=name, url=url, count=count))
        seen_urls.add(url)

    categories.sort(key=lambda item: item.count, reverse=True)
    return categories


def open_largest_top_results_category_if_needed(driver: webdriver.Chrome, timeout: int) -> None:
    if driver.find_elements(By.CSS_SELECTOR, DETAIL_LINK_SELECTOR):
        return

    categories = get_top_results_category_links(driver)
    if not categories:
        return

    driver.get(categories[0].url)
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, "body")))


def get_product_links(driver: webdriver.Chrome, timeout: int, limit: int = 10) -> list[ProductLink]:
    open_largest_top_results_category_if_needed(driver, timeout)

    soup = get_page_soup(driver)
    if is_blocked_search_page(soup):
        raise ValueError(classify_search_page_issue(soup))

    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, DETAIL_LINK_SELECTOR))
        )
    except TimeoutException as exc:
        soup = get_page_soup(driver)
        raise ValueError(classify_search_page_issue(soup)) from exc

    soup = get_page_soup(driver)
    products = extract_product_links_from_soup(soup, limit=limit)
    if not products:
        raise ValueError(classify_search_page_issue(soup))
    return products


def choose_product_url_or_candidates(
    driver: webdriver.Chrome,
    query: str,
    timeout: int,
) -> tuple[str | None, list[ProductLink]]:
    if is_detail_url(driver.current_url):
        return driver.current_url, []

    products = get_product_links(driver, timeout, limit=10)
    exact_matches = [product for product in products if candidate_matches_query(product, query)]

    if len(exact_matches) == 1:
        return exact_matches[0].url, []

    if len(products) == 1:
        return products[0].url, []

    return None, products


def wait_for_detail_page(driver: webdriver.Chrome, timeout: int) -> None:
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    try:
        WebDriverWait(driver, min(timeout, 8)).until(
            lambda item: (
                item.execute_script("return document.readyState") in {"interactive", "complete"}
                and (
                    item.find_elements(By.CSS_SELECTOR, "table")
                    or item.find_elements(By.CSS_SELECTOR, "[data-testid*='attribute']")
                    or item.find_elements(
                        By.XPATH,
                        "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'digi-key part number')]",
                    )
                )
            )
        )
    except TimeoutException:
        pass


def extract_product_title(soup: BeautifulSoup) -> str:
    selectors = ["h1", "[data-testid='product-title']", "title"]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = clean_text(node.get_text(" ", strip=True))
            if text:
                return text
    return "제품명 확인 실패"


def extract_part_number(soup: BeautifulSoup) -> str | None:
    text = soup.get_text(" ", strip=True)
    match = re.search(r"Digi-?Key Part Number\s*([A-Z0-9\-./]+)", text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def extract_price_rows(soup: BeautifulSoup) -> list[str]:
    rows: list[str] = []

    for table in soup.find_all("table"):
        headers = [clean_text(th.get_text(" ", strip=True)).lower() for th in table.find_all("th")]
        header_text = " ".join(headers)
        if "price" not in header_text and "quantity" not in header_text and "pricing" not in header_text:
            continue

        for row in table.find_all("tr"):
            cells = [clean_text(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
            joined = " | ".join(cells)
            if is_price_break_row(cells) and PRICE_PATTERN.search(joined):
                rows.append(joined)

    if rows:
        return list(dict.fromkeys(rows))

    fallback_rows: list[str] = []
    for line in soup.get_text("\n", strip=True).splitlines():
        normalized = clean_text(line)
        if is_price_break_text(normalized):
            fallback_rows.append(normalized)

    return list(dict.fromkeys(fallback_rows[:10]))


def is_price_break_row(cells: list[str]) -> bool:
    if len(cells) < 2:
        return False

    first_cell = cells[0].replace(",", "").strip()
    joined = " | ".join(cells)

    if not re.fullmatch(r"\d+", first_cell):
        return False
    if "similar" in joined.lower():
        return False
    if re.search(r"[A-Za-z]{2,}\d+[A-Za-z0-9\-]*", cells[0]):
        return False

    return bool(PRICE_PATTERN.search(joined))


def is_price_break_text(text: str) -> bool:
    if "similar" in text.lower():
        return False
    return bool(re.match(r"^\d[\d,]*\s*\|\s*[$\u20a9\u20ac\u00a3]", text))


def extract_datasheet_url(soup: BeautifulSoup) -> str:
    candidates: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True).lower()
        if "datasheet" in text or "datasheet" in href.lower():
            if href.startswith("http"):
                candidates.append(href)
            elif href.startswith("/"):
                candidates.append(urljoin(BASE_URL, href))
    for a in soup.select("[data-testid*='datasheet'], [class*='datasheet'], [class*='Datasheet']"):
        href = a.get("href", "")
        if href.startswith("http"):
            candidates.append(href)
        elif href.startswith("/"):
            candidates.append(urljoin(BASE_URL, href))

    unique_candidates = list(dict.fromkeys(normalize_datasheet_url(url) for url in candidates))
    for url in unique_candidates:
        path = url.split("?", 1)[0].lower()
        if path.endswith(".pdf") or "/pdf/" in path or "/lit/ds/" in path:
            return url

    return unique_candidates[0] if unique_candidates else ""


def normalize_datasheet_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    goto_values = query.get("gotoUrl")
    if parsed.netloc.endswith("ti.com") and goto_values:
        return unquote(goto_values[0])
    return url


def fetch_product_detail(driver: webdriver.Chrome, query: str, product_url: str, timeout: int) -> ProductResult:
    driver.get(product_url)
    wait_for_detail_page(driver, timeout)

    soup = get_page_soup(driver)
    if is_blocked_search_page(soup):
        raise ValueError(classify_search_page_issue(soup))

    title = extract_product_title(soup)
    part_number = extract_part_number(soup)
    price_rows = extract_price_rows(soup)
    specs = extract_specs(soup, {**MAIN_SPEC_ALIASES, **CANDIDATE_SPEC_ALIASES})
    if not part_number and not price_rows and not any(value not in {"N/A", NO_INFO} for value in specs.values()):
        raise ValueError(classify_search_page_issue(soup))

    return ProductResult(
        query=query,
        title=title,
        product_url=product_url,
        datasheet_url=extract_datasheet_url(soup),
        part_number=part_number,
        price_rows=price_rows,
        specs=specs,
    )


def fetch_candidate_details(
    driver: webdriver.Chrome,
    query: str,
    product_links: list[ProductLink],
    timeout: int,
) -> list[ProductResult]:
    results: list[ProductResult] = []
    for product in product_links[:10]:
        try:
            result = fetch_product_detail(driver, product.name or query, product.url, timeout)
        except TimeoutException:
            result = ProductResult(query=product.name or query, error="페이지 로딩 시간이 초과되었습니다.")
        except Exception as exc:
            result = ProductResult(query=product.name or query, error=f"후보 상세 정보를 가져오지 못했습니다: {exc}")
        results.append(result)
    return results


def fetch_one_product(driver: webdriver.Chrome, query: str, timeout: int) -> ProductResult:
    driver.get(SEARCH_URL.format(query=quote(query)))

    product_url, candidate_links = choose_product_url_or_candidates(driver, query, timeout)
    if candidate_links:
        candidates = fetch_candidate_details(driver, query, candidate_links, timeout)
        return ProductResult(query=query, candidate_results=candidates)

    if not product_url:
        return ProductResult(query=query, error="제품 상세 페이지를 찾지 못했습니다.")

    return fetch_product_detail(driver, query, product_url, timeout)


def parse_category_listing(
    soup: BeautifulSoup,
    category_label: str,
    limit: int = 25,
) -> list[ProductResult]:
    """Parse a DigiKey category listing page into ProductResults (no per-product requests)."""
    product_links = extract_product_links_from_soup(soup, limit=limit)
    return [
        ProductResult(
            query=category_label,
            title=link.name or extract_name_from_url(link.url),
            product_url=link.url,
            part_number=extract_name_from_url(link.url),
        )
        for link in product_links
    ]
