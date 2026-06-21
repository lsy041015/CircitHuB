LANGUAGE_OPTIONS = [("ko", "한국어"), ("en", "English")]

RESULT_TEXT = {
    "ko": {
        "search_term": "검색어",
        "requested_quantity": "요청 수량",
        "candidate_notice": "아래 후보 중 정확한 부품명을 찾아 다시 입력해 주세요.",
        "candidate": "후보 {index}",
        "error": "오류",
        "product_name": "제품명",
        "detail_page": "상세 페이지",
        "price_info": "가격 정보",
        "price_missing": "가격 정보를 찾지 못했습니다.",
        "main_info": "주요 정보",
        "no_info": "정보 없음",
    },
    "en": {
        "search_term": "Search term",
        "requested_quantity": "Requested quantity",
        "candidate_notice": "Select the exact part name from the candidates and search again.",
        "candidate": "Candidate {index}",
        "error": "Error",
        "product_name": "Product name",
        "detail_page": "Detail page",
        "price_info": "Price information",
        "price_missing": "No price information found.",
        "main_info": "Key information",
        "no_info": "N/A",
    },
}


def normalize_language(language: str) -> str:
    return language if language in RESULT_TEXT else "ko"


def result_text(language: str, key: str, **kwargs) -> str:
    text = RESULT_TEXT[normalize_language(language)].get(key, key)
    return text.format(**kwargs) if kwargs else text
