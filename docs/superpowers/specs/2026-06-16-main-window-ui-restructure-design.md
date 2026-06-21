# MainWindow UI Restructure Design

## Goal

Production GUI 경로를 유지한 채 `MainWindow` 를 얇은 조정자(coordinator)로 축소한다.  
기존 실행 경로 `digikey_price_scraper.py -> digikey_scraper.qt_gui -> digikey_scraper._main_window.MainWindow` 는 그대로 둔다.

이번 구조 설계의 우선순위는 다음과 같다.

1. 저위험 점진 분리
2. 기존 동작 보존
3. 테스트 가능한 작은 책임 단위 확보
4. 장기적으로 데모/실험 UI 제거 가능 상태 만들기

## Current Problems

### 1. Active production path responsibilities are still concentrated

현재 production 경로 핵심 파일은 다음이다.

- `digikey_scraper/_main_window.py`
- `digikey_scraper/_ui_builder.py`
- `digikey_scraper/qt_gui.py`

최근 분리 이후에도 `MainWindow` 는 여전히 아래 성격을 함께 가진다.

- 화면 조립 이후의 coordinator
- sidebar/status/footer 갱신 담당
- chat window open/share bridge
- BOM import / save / clipboard I/O
- lifecycle / shutdown 정리

즉 “실행 흐름 조정자” 와 “UI 세부 렌더링/도우미” 가 아직 섞여 있다.

### 2. Parallel UI stack still exists

아래 파일들은 production 엔트리에서 직접 쓰이지 않지만 별도 UI 스택을 유지한다.

- `digikey_scraper/_circuitkit_design.py`
- `digikey_scraper/_circuitkit_chat_design.py`

이 둘은 테스트나 실험 UI로만 남아 있고, production 구조를 이해하는 비용을 키운다.

### 3. Runtime-facing tests still encode old alternative UI

`tests/test_windows_runtime.py` 는 production `MainWindow` 뿐 아니라 `CircuitKitWindow` 도 검증한다.  
이 상태에서는 production 경로 정리가 끝나도 대체 UI를 쉽게 제거할 수 없다.

## Design Principles

### Keep runtime API stable

아래 public/runtime entry surface 는 유지한다.

- `digikey_price_scraper.py`
- `digikey_scraper.qt_gui.main`
- `digikey_scraper.qt_gui.MainWindow`

### Extract by responsibility, not by widget type

분리는 “버튼 모음”, “QFrame 모음” 기준이 아니라 책임 기준으로 한다.

- state mutation
- search orchestration
- category orchestration
- sidebar/status presentation
- chat bridging
- file/clipboard I/O

### Coordinator stays small

최종적으로 `_main_window.py` 는 다음만 남긴다.

- object composition
- default state bootstrap
- dependency wiring
- mixin inheritance assembly
- final shutdown / lifecycle glue

### Remove demo UI only after production coverage is sufficient

`_circuitkit_*` 파일은 즉시 지우지 않는다.  
먼저 production 경로 테스트가 대체 UI 없이 충분히 서는 상태를 만든 뒤 제거한다.

## Target Production Structure

### Runtime entry layer

- `digikey_price_scraper.py`
  - 단일 실행 진입점 유지
- `digikey_scraper/qt_gui.py`
  - public API export 유지

### Main window assembly layer

- `digikey_scraper/_main_window.py`
  - `MainWindow` 생성
  - dependency wiring
  - startup state bootstrap
  - close/shutdown lifecycle

### Extracted responsibility modules

- `digikey_scraper/_ui_builder.py`
  - widget tree 생성만 담당
- `digikey_scraper/_main_window_parts.py`
  - 부품 추가/삭제/수량/히스토리 로드
- `digikey_scraper/_main_window_search.py`
  - 검색 실행, worker 연결, 진행/성공/실패 상태 전이
- `digikey_scraper/_main_window_category.py`
  - 카테고리 검색 흐름과 결과 렌더
- `digikey_scraper/_main_window_sidebar.py`
  - sidebar list 렌더, footer/api state, statusbar, language apply
- `digikey_scraper/_main_window_io.py`
  - BOM import, auto-save, save-as, clipboard copy
- `digikey_scraper/_main_window_chat.py`
  - chat open, text share, part share bridge

### Supporting view modules that remain shared

- `digikey_scraper/_result_card.py`
- `digikey_scraper/_widgets.py`
- `digikey_scraper/_stylesheet.py`
- `digikey_scraper/_translations.py`

## Boundaries

### `_main_window_sidebar.py`

책임:

- `render_sidebar_lists()`
- `_apply_language()`
- `_update_statusbar()`
- `_set_api_state()`
- tab/sidebar active state 반영

비책임:

- search worker 실행
- category worker 실행
- file I/O

이 모듈은 “현재 state 를 받아 화면 텍스트/표시를 갱신하는 presentation helper” 성격으로 둔다.

### `_main_window_io.py`

책임:

- `import_bom()`
- `_auto_save_results()`
- `copy_text()`
- `save_results_as()`
- `get_result_text()`

비책임:

- search state 변경
- favorites 변경
- category status 변경

### `_main_window_chat.py`

책임:

- `open_chat()`
- `share_text_to_chat()`
- `share_part_to_chat()`

비책임:

- chat persistence 내부 구현
- category or search state mutation

이 레이어는 production `MainWindow` 와 chat UI 사이 adapter 역할만 한다.

## Migration Sequence

### Phase 1: Complete low-risk MainWindow decomposition

순서:

1. `_main_window_sidebar.py` 분리
2. `_main_window_io.py` 분리
3. `_main_window_chat.py` 분리

완료 기준:

- `_main_window.py` 에서 대형 흐름 메서드 대부분 제거
- 각 분리마다 mixin 존재 검증 테스트 추가
- runtime smoke tests green

### Phase 2: Stabilize production-only test path

작업:

- `tests/test_windows_runtime.py` 를 production 경로 중심으로 재정렬
- `CircuitKitWindow` 검증을 별도 legacy test 로 분리하거나 제거 후보로 전환
- production `MainWindow` 만으로도 GUI smoke confidence 확보

완료 기준:

- production 실행 검증이 `_circuitkit_design.py` 없이도 충분

### Phase 3: Quarantine and remove demo/legacy UI

대상:

- `digikey_scraper/_circuitkit_design.py`
- `digikey_scraper/_circuitkit_chat_design.py`

조건:

- production chat/share flow 가 별도 bridge/module 로 분리 완료
- runtime tests 가 production 경로만 검증
- 남은 참조가 tests 또는 docs 에만 존재

완료 방식:

1. 참조 제거
2. 테스트 갱신
3. 파일 삭제

## Error Handling Strategy

이번 리팩터의 목표는 동작 변경이 아니다.  
따라서 예외 처리 정책은 기존 수준을 유지한다.

단, 분리 과정에서 아래 원칙을 지킨다.

- state transition 은 기존 시점과 동일해야 한다
- UI status text 는 기존과 동일해야 한다
- file save / auto-save 실패 메시지 동작은 바꾸지 않는다
- search/category cancellation 동작은 바꾸지 않는다

즉 “예외 정책 개선” 은 별도 작업으로 분리하고, 이번 설계에서는 구조 분리에만 집중한다.

## Testing Strategy

### Structure lock tests

각 새 mixin 분리 시 아래 형식 테스트를 추가한다.

- `MainWindow` 가 해당 mixin 을 상속하는지 확인

목적:

- 분리 후 다시 거대한 `_main_window.py` 로 회귀하는 것 방지

### Targeted behavior tests

각 책임별 기존 테스트를 유지하거나 추가한다.

- parts: `tests/test_part_suggestions.py`
- category: `tests/test_category_search.py`
- search/runtime: `tests/test_windows_runtime.py`
- new sidebar/io/chat responsibilities: 각 전용 테스트 파일 추가

### Runtime smoke

계속 유지할 최소 검증:

- `QT_QPA_PLATFORM=offscreen` 에서 `MainWindow()` 생성 가능
- 주요 버튼/페이지 전환 가능
- search/category/share 기본 wiring 정상

## Explicit Non-Goals

이번 구조 설계에서는 아래를 하지 않는다.

- 검색 알고리즘 변경
- category 결과 모델 변경
- chat UI redesign
- `_ui_builder.py` 의 대규모 재작성
- 새로운 state management framework 도입
- `_circuitkit_*` 즉시 삭제

## Recommended Implementation Order

1. `_main_window_sidebar.py`
2. `_main_window_io.py`
3. `_main_window_chat.py`
4. runtime test production-only 정리
5. `_circuitkit_design.py` 제거 준비
6. `_circuitkit_chat_design.py` 제거 준비

이 순서를 추천하는 이유:

- 현재 남은 `_main_window.py` 의 가장 큰 잔여 책임을 먼저 줄일 수 있다
- production 경로의 모양이 먼저 선명해진다
- 그 다음에 legacy/demo UI 제거 판단이 쉬워진다
