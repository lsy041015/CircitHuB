# 검색 결과 정렬 및 소자 필터 설계

**날짜:** 2026-06-15  
**범위:** 메인 검색 UI — 결과 정렬, 소자 유형 필터, 스펙 범위 필터  
**대상 파일:** `_filter_sort.py` (신규), `_ui_builder.py`, `_main_window.py`, `tests/test_filter_sort.py` (신규)

---

## 1. 목표

현재 `render_results()`는 `self.results`를 삽입 순서 그대로 렌더링함. 정렬/필터 없음.

추가 목표:
- 가격/재고/신선도 기준 정렬
- 회로 소자 유형별 필터 (저항/캐패시터/인덕터/IC/다이오드/트랜지스터/커넥터)
- 유형 선택 시 주요 스펙(저항값, 정전용량 등) 수치 범위 필터
- 에러 결과 숨기기

---

## 2. UI 레이아웃

기존 툴바는 변경하지 않음. 결과 카드 그리드 바로 위에 **필터 바(`QWidget`)** 추가.

```
┌─────────────────────────────────────────────────────────────┐
│  [기존 툴바: 검색 입력 / 언어 / 설정 ...]                     │
├─────────────────────────────────────────────────────────────┤
│  결과: 5 · ERR 1  │  [↕ 정렬▾]  [🔩 유형▾]  [___]~[___] Ω  │  [☑ 에러숨김]  │
├─────────────────────────────────────────────────────────────┤
│  [카드] [카드] [카드]                                         │
└─────────────────────────────────────────────────────────────┘
```

### 위젯 목록

| 역할 | 위젯 | 세부 사항 |
|------|------|-----------|
| 결과 수 | `QLabel` (`self.results_count`) | 위치 이동 (필터 바로) |
| 정렬 | `QComboBox` | 기본순 / 가격↑ / 가격↓ / 재고↓ / 최신순 |
| 소자 유형 | `QComboBox` | 전체 + 현재 결과에 감지된 유형만 동적 표시 |
| 범위 min/max | `QLineEdit` × 2 (width=70) | 유형 미선택 시 disabled |
| 단위 레이블 | `QLabel` | 유형에 따라 Ω / F / H / V |
| 에러 숨기기 | `QCheckBox` | |

**필터 바 표시 조건:** `len(self.results) > 0`

> **범위 필터 지원 유형:** 저항, 캐패시터, 인덕터, 다이오드만 지원. IC/트랜지스터/커넥터는 주요 단일 스펙이 없으므로 유형 선택 시 범위 필터 비활성화 (의도적).

---

## 3. 아키텍처

### 데이터 흐름

```
self.results (raw list[ProductResult])
    │
    ▼
_apply_filter(results, type, spec_min, spec_max, hide_errors)
    │
    ▼
_apply_sort(results, sort_key)
    │
    ▼
render_results() → ResultCard 생성
```

`render_results()` 내부 첫 줄에 전처리 삽입. `self.results` 자체는 변경하지 않음 (뷰 전용 변환).

### 신규 파일: `digikey_scraper/_filter_sort.py`

단일 책임: 필터/정렬/파싱 순수 함수만 포함. Qt 의존 없음.

```python
COMPONENT_TYPES: dict[str, list[str]] = {
    "저항":    ["resistor", "저항", "res "],
    "캐패시터": ["capacitor", "캐패시터", "cap "],
    "인덕터":  ["inductor", "인덕터"],
    "IC":      ["ic ", "mcu", "microcontroller", "module"],
    "다이오드": ["diode", "다이오드", "led", "zener"],
    "트랜지스터": ["transistor", "mosfet", "fet", "bjt"],
    "커넥터":  ["connector", "커넥터", "header", "socket"],
}

# 유형 → (specs 키 후보들, 단위 문자열)
SPEC_KEY_MAP: dict[str, tuple[list[str], str]] = {
    "저항":    (["저항", "Resistance", "저항값"], "Ω"),
    "캐패시터": (["정전용량", "Capacitance", "용량"], "F"),
    "인덕터":  (["인덕턴스", "Inductance"], "H"),
    "다이오드": (["순방향전압", "Forward Voltage", "Voltage"], "V"),
}

def detect_component_type(result: ProductResult) -> str | None: ...
def parse_spec_value(text: str) -> float | None: ...  # "10 kΩ" → 10000.0
def apply_filter(results, type_str, spec_min, spec_max, hide_errors) -> list[ProductResult]: ...
def apply_sort(results, sort_key: str) -> list[ProductResult]: ...
```

### `parse_spec_value` 단위 변환표

| 접두어 | 배수 |
|--------|------|
| p (pico) | 1e-12 |
| n (nano) | 1e-9 |
| µ/u (micro) | 1e-6 |
| m (milli) | 1e-3 |
| k (kilo) | 1e3 |
| M (mega) | 1e6 |
| G (giga) | 1e9 |

### `_main_window.py` 상태 추가

```python
self._sort_key: str = "none"
self._filter_type: str | None = None
self._filter_spec_min: float | None = None
self._filter_spec_max: float | None = None
self._filter_hide_errors: bool = False
```

### `_ui_builder.py` 필터 바 빌드

`build_filter_bar(window) -> QWidget` 함수 추가. 반환 위젯을 메인 레이아웃에서 카드 그리드 위에 삽입.

유형 콤보 동적 업데이트 (검색 완료 시 호출):
```python
types_found = {detect_component_type(r) for r in self.results} - {None}
combo_type.clear()
combo_type.addItem("전체", None)
for t in sorted(types_found):
    combo_type.addItem(t, t)
```

유형 변경 시 범위 필터 활성화 + 단위 레이블 갱신:
```python
def _on_type_changed(type_str):
    keys, unit = SPEC_KEY_MAP.get(type_str, ([], ""))
    range_min.setEnabled(bool(keys))
    range_max.setEnabled(bool(keys))
    unit_label.setText(unit)
    self._filter_type = type_str
    self.render_results()
```

---

## 4. 에러 처리

| 상황 | 처리 |
|------|------|
| `parse_spec_value` 파싱 실패 | `None` 반환 → 해당 결과 범위 필터 통과 (숨기지 않음) |
| 범위 입력이 비숫자 | `QLineEdit` 빨간 테두리 + 필터 무시 (크래시 없음) |
| 필터 후 결과 0개 | 기존 빈 상태 UI(`empty_results`) 그대로 표시 |
| 가격 파싱 불가 결과 | 정렬 시 마지막으로 배치 |
| 재고 파싱 불가 결과 | 정렬 시 마지막으로 배치 |

---

## 5. 테스트 (`tests/test_filter_sort.py`)

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_sort_price_asc` | 가격 문자열 파싱 후 오름차순 정렬 |
| `test_sort_stock_desc` | 재고 내림차순 정렬 |
| `test_sort_freshness_desc` | `scraped_at` 내림차순 |
| `test_filter_type_resistor` | 저항 유형 감지 + 비저항 결과 제외 |
| `test_filter_spec_range` | 범위 내 결과만 통과, 범위 외 제외 |
| `test_filter_hide_errors` | `error` 필드 있는 결과 숨김 |
| `test_parse_spec_value` | `"10 kΩ"`→`10000.0`, `"100nF"`→`1e-7`, `"4.7µF"`→`4.7e-6` |
| `test_parse_spec_value_fail` | 파싱 불가 문자열 → `None` |

---

## 6. 변경 파일 요약

| 파일 | 변경 유형 |
|------|-----------|
| `digikey_scraper/_filter_sort.py` | 신규 |
| `digikey_scraper/_ui_builder.py` | 필터 바 빌드 함수 추가 |
| `digikey_scraper/_main_window.py` | 상태 5개 추가, `render_results()` 전처리 삽입 |
| `tests/test_filter_sort.py` | 신규 |

---

## 7. 범위 밖 (이번 스펙 제외)

- BOM CSV import (F2) — 별도 스펙
- 결과 가상화/페이지네이션 (U1) — 별도 스펙
- 에러/빈 상태 친화 메시지 (U2/U3) — 별도 스펙
