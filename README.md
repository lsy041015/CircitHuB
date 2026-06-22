# CircuitHUB — 전자 부품 탐색 데스크탑 애플리케이션

> DigiKey 실시간 스크래핑 · AI 채팅 · 데이터시트 분석 · LAN 협업을 통합한 엔지니어링 워크스테이션

---

## 1. 프로젝트 시나리오

### 1.1 배경과 문제 정의

전자 회로 설계 현장에서 엔지니어와 학생들은 매일 반복되는 병목 작업에 시달린다.

**DigiKey 수작업 조회의 한계**

DigiKey는 세계 최대 규모의 전자 부품 유통사 중 하나로, 한국 엔지니어링 현장에서도 표준 데이터 소스로 활용된다. 그러나 기존 사용 패턴에는 세 가지 근본적 마찰이 존재했다.

첫째, **검색 단절 문제**다. 설계자가 회로 설계 도구(KiCad, Altium)를 사용하면서 브라우저로 전환해 DigiKey를 검색하고, 가격을 복사-붙여넣기한 뒤 다시 설계 도구로 돌아오는 컨텍스트 스위칭이 부품 수만큼 반복된다. BOM(Bill of Materials)에 30개 부품이 있으면 이 과정이 30회 반복된다.

둘째, **데이터시트 언어 장벽**이다. 거의 모든 데이터시트는 영어로 작성되며, 한국 엔지니어링 교육 현장에서 학생들이 핵심 전기 특성 표나 핀 맵을 빠르게 이해하는 데 상당한 시간이 소요된다. 특히 Absolute Maximum Ratings 섹션을 잘못 해석하면 부품 파손이나 회로 오설계로 이어진다.

셋째, **팀 협업 단절**이다. 같은 실험실이나 사무실에서 여러 엔지니어가 각자 브라우저를 열고 동일한 부품을 조회하며, 결과를 메신저나 이메일로 공유하는 비효율이 발생한다.

### 1.2 해결 목표

CircuitKit은 이 세 가지 문제를 하나의 데스크탑 애플리케이션으로 해결하는 것을 목표로 설계되었다.

- **단일 인터페이스**: 부품 번호 입력 → 실시간 가격·스펙 표시 → AI 질의 → 데이터시트 열기까지 앱을 벗어나지 않는다
- **한국어 AI 분석**: 데이터시트 특정 영역을 드래그하면 즉시 한국어 번역·요약이 제공된다
- **LAN 공유**: 같은 네트워크의 다른 인스턴스로 검색 결과를 원클릭 전송하거나 그룹 채팅으로 소통한다

### 1.3 주요 사용 시나리오

**시나리오 A — 산업용 BOM 견적**
견적 담당자가 `LM358P, NE555P, TL072CP` 세 부품을 동시에 입력하면, CircuitKit이 Selenium으로 DigiKey를 순차 스크래핑해 각 부품의 가격 구간(Price Break)과 패키지·사양을 카드 형태로 나란히 표시한다. BOM 합계 금액이 자동 계산된다.

**시나리오 B — 실험실 데이터시트 학습**
학생이 STM32F4 마이크로컨트롤러 데이터시트를 열고 'Power Supply Characteristics' 표를 마우스로 드래그 선택한다. Gemini 2.5 Flash가 표 구조를 인식해 핵심 전압·전류 한계를 한국어로 요약해 준다. 이어서 "이 MCU의 최대 GPIO 전류는 몇 mA야?"라고 AI 채팅에 입력하면, 로컬 Gemma4:e4b가 데이터시트 컨텍스트를 참고해 답변한다.

**시나리오 C — 팀 부품 선정 회의**
설계팀 3명이 각자 CircuitKit을 실행한 상태에서 한 명이 후보 부품 결과를 LAN 공유로 나머지 두 명에게 전송한다. 그룹 채팅에서 "@홍길동 이거 정격 전압 확인해봐"처럼 멘션 기반 소통이 가능하다.

---

## 2. 설계 과정

### 2.1 아키텍처 결정 원칙

프로젝트 설계의 핵심 원칙은 **비즈니스 로직이 UI·인프라에 의존하지 않아야 한다**는 것이다. 이를 위해 헥사고날(Ports & Adapters) 아키텍처를 채택했다.

```
┌─────────────────────────────────────────┐
│              UI Layer (Qt/PySide6)       │
│  MainWindow + Mixin 조합                │
├─────────────────────────────────────────┤
│           Application Layer              │
│  SearchService · AiChatService           │
│  RagService · SettingsService            │
├─────────────────────────────────────────┤
│             Domain Layer                 │
│  ProductResult · Ports(Protocol)         │
│  ChatModels · RagModels                  │
├─────────────────────────────────────────┤
│          Infrastructure Layer            │
│  Selenium · Ollama · PyMuPDF             │
│  OpenCV · JSON/PG · InMemoryVectorStore  │
└─────────────────────────────────────────┘
```

각 계층 경계는 Python의 `Protocol`(구조적 타이핑)로 정의된다. 예를 들어 `SupplierScraper` 포트는 `open()`, `fetch_one()`, `cancel()`, `close()` 네 메서드만 요구하며, Selenium 구현체나 미래의 Mouser API 구현체는 이 계약만 준수하면 된다.

### 2.2 GUI 설계: Mixin 기반 분해

`MainWindow`는 기능별 Mixin 클래스를 다중 상속으로 조합한다.

```python
class MainWindow(
    MainWindowChatMixin,        # AI 채팅 패널 연동
    MainWindowCategoryMixin,    # 카테고리 브라우저
    MainWindowPartsMixin,       # 부품 제안 및 자동완성
    MainWindowSearchMixin,      # 검색 실행 및 취소
    MainWindowSidebarMixin,     # 사이드바 제어
    MainWindowIoMixin,          # 파일 저장·불러오기
    UiBuilderMixin,             # 위젯 생성 팩토리
    SharingMixin,               # TCP 공유 수신 서버
    PartSuggestionsMixin,       # 철자 교정 제안
    QMainWindow,
):
```

이 패턴은 단일 클래스의 비대화를 방지하고, 각 Mixin이 명확한 책임 경계를 가지도록 강제한다.

### 2.3 비동기 처리 전략

Qt GUI는 메인 스레드를 블록해선 안 된다. Selenium 스크래핑은 부품당 수 초가 걸리므로 `SearchWorker`가 별도 스레드에서 실행되고, `SearchSignals`(Qt Signal)로 UI에 진행 상태를 전달한다.

```python
class SearchSignals(QObject):
    progress = Signal(int, int, str)    # (현재, 전체, 쿼리명)
    finished = Signal(list, bool, bool)
    failed   = Signal(str)
```

Ollama AI 채팅 역시 스트리밍으로 처리되어 첫 토큰부터 UI에 실시간 렌더링된다.

### 2.4 의존성 주입(DI) 설계

`container.py`가 애플리케이션의 합성 루트(Composition Root) 역할을 한다.

```python
def build_container() -> Container:
    llm  = OllamaTextGenerator(model="gemma4:e4b")
    repo = JsonAiChatRepository()
    return Container(
        results  = _build_result_repository(),   # JSON → PG 자동 전환
        settings = FileSettingsStore(),
        ai_chat  = AiChatService(llm=llm, repo=repo),
    )
```

결과 저장소는 PostgreSQL이 가용하면 자동으로 `PgResultRepository`로, 그렇지 않으면 `JsonResultRepository`로 폴백한다. UI나 비즈니스 로직은 이 차이를 알 필요가 없다.

---

## 3. 구체적인 코드 설명

### 3.1 웹 스크래핑 엔진 (`scraper.py`)

DigiKey는 Cloudflare 봇 탐지를 적용하기 때문에 단순 `requests` 기반 접근은 차단된다. CircuitKit은 두 가지 전략을 병행한다.

**전략 1: Chrome 프로파일 재사용**
`setup_chrome_profile.sh`로 전용 Chrome 프로파일 디렉토리를 생성하고, 사용자가 수동으로 Cloudflare 인증(`cf_clearance` 쿠키)을 통과시킨다. 앱 실행 시 이 프로파일을 로드해 인증된 세션을 재사용한다.

**전략 2: 지능적 결과 선택**
`choose_product_url_or_candidates()`는 검색 결과 페이지에서 정확 일치 후보가 1개면 바로 진입하고, 복수면 후보 목록을 반환해 UI에서 사용자가 선택하도록 한다. 카테고리 결과 페이지의 경우 `open_largest_top_results_category_if_needed()`가 가장 많은 결과를 포함한 카테고리로 자동 이동한다.

가격 파싱은 `is_price_break_row()`가 테이블 행에서 첫 셀이 순수 숫자인지, 가격 패턴(`$`, `₩`, `€`)이 있는지를 복합 검증해 노이즈를 필터링한다.

### 3.2 데이터시트 AI 분석 (`gemma_client.py`)

`GemmaDatasheetAnalyzer`는 두 가지 핵심 내구성 패턴을 구현한다.

**다중 API 키 순환(Round-Robin)**
```python
def _next_key(self) -> tuple[str, int]:
    now = time.time()
    for _ in range(len(self._keys)):
        idx = self._rr % len(self._keys)
        self._rr += 1
        if now >= self._blocked_until[idx]:
            return self._keys[idx], idx
    # 모든 키 차단 시 가장 빨리 풀리는 키 선택
    idx = min(range(len(self._keys)), key=lambda i: self._blocked_until[i])
    return self._keys[idx], idx
```

Rate Limit(HTTP 429) 발생 시 해당 키를 62초 차단하고, 대기 시간을 지수 백오프(최대 30초)로 늘린다.

**응답 캐싱(SHA-256)**
동일한 모델·파라미터·프롬프트 조합은 `SHA-256` 해시로 캐시 키를 생성해 `~/.gemma_cache/*.json`에 저장한다. 동일 데이터시트 영역을 반복 분석할 때 API 호출을 완전히 생략한다.

### 3.3 로컬 AI 채팅 (`ai_chat_service.py` + `ollama_text_generator.py`)

`AiChatService`는 세 가지 컨텍스트 모드를 지원한다.

- **`parts` 모드**: 현재 검색된 부품 결과를 JSON으로 시스템 프롬프트에 주입해 "이 부품의 공급 전압 범위는?" 같은 질문에 답한다
- **`rag` 모드**: `RagService`가 데이터시트 청크에서 유사도 검색으로 관련 내용 3개를 가져와 컨텍스트로 제공한다
- **`datasheet` 모드**: 현재 뷰어에서 열린 데이터시트 제목을 컨텍스트로 제공한다

`OllamaTextGenerator.stream_chat()`은 Ollama의 `/api/chat` 엔드포인트에 스트리밍 POST를 보내고, 각 JSON 라인에서 `message.content` 청크를 `on_chunk` 콜백으로 실시간 전달한다.

```python
def stream_chat(self, messages: list[dict], on_chunk: Callable[[str], None]) -> str:
    url = f"{self._base_url}/api/chat"
    payload = {"model": self._model, "messages": messages, "stream": True}
    with httpx.stream("POST", url, json=payload, timeout=120.0) as resp:
        for line in resp.iter_lines():
            data = json.loads(line)
            chunk = data.get("message", {}).get("content", "")
            if chunk:
                on_chunk(chunk)   # Qt 슬롯에서 UI 업데이트
```

### 3.4 RAG 인프라 (`infrastructure/rag/`)

외부 임베딩 서비스 없이 완전 오프라인 벡터 검색을 구현했다.

- **`HashingEmbedder`**: Feature Hashing(해싱 트릭)으로 텍스트를 고정 차원 벡터로 변환. L2 정규화 적용
- **`InMemoryVectorStore`**: 코사인 유사도(L2 정규화된 벡터의 dot product)로 top-k 검색
- **`chunker.py`**: 데이터시트 텍스트를 겹침(overlap) 있는 고정 크기 청크로 분할

이 설계로 Qdrant 같은 외부 벡터 DB 없이도 기본 RAG가 동작하며, 프로덕션에서는 `VectorStore` 포트에 Qdrant 어댑터를 주입해 대체할 수 있다.

### 3.5 LAN 채팅 (`chat.py`)

`ChatMessage` 데이터클래스는 종류(`kind`), 방(`room`), 발신자, 본문, 타임스탬프, 멘션 목록, 반응(이모지), 읽음 목록을 포함한다. TCP 소켓 기반으로 길이-선행(length-prefixed) 프레임을 사용해 메시지 경계를 보장하고, `peer_allowed()` 검증으로 허용된 호스트만 수신한다.

---

## 4. 구현 환경

### 4.1 개발 환경

| 항목 | 버전 / 사양 |
|------|------------|
| 운영체제 | Ubuntu 22.04 LTS / Windows 10·11 |
| 언어 | Python 3.10 이상 |
| GUI 프레임워크 | PySide6 6.6.3 (Qt6 공식 Python 바인딩) |
| 웹 자동화 | Selenium 4.21.0 + undetected-chromedriver 3.5.5+ |
| 브라우저 | Google Chrome (ChromeDriver 자동 매칭) |

### 4.2 AI 및 문서 처리 스택

| 컴포넌트 | 라이브러리 | 역할 |
|----------|-----------|------|
| 클라우드 LLM | google-genai ≥ 1.0.0 | Gemini 2.5 Flash API (데이터시트 멀티모달) |
| 로컬 LLM | httpx ≥ 0.27 + Ollama | Gemma4:e4b 스트리밍 채팅 |
| PDF 렌더링 | PyMuPDF 1.27.2 | 페이지 래스터화, 텍스트 추출 |
| 컴퓨터 비전 | OpenCV 4.11.0.86 | 데이터시트 테이블 영역 자동 탐지 |
| OCR | pytesseract 0.3.13 | 이미지 영역 텍스트 인식 |
| 수치 연산 | numpy < 2 | 이미지 배열 처리, 벡터 연산 |
| HTML 파싱 | beautifulsoup4 4.12.3 | DigiKey 페이지 구조 파싱 |

### 4.3 데이터 저장 구조

```
~/.local/share/digikey-scraper/   (또는 DIGIKEY_SCRAPER_DATA_DIR)
├── app_settings.json              # 사용자 설정
├── auto_saved_results/            # 자동 저장된 검색 결과
├── shared_specs/                  # 수신된 공유 스펙
├── .gemma_cache/                  # Gemini 응답 캐시
└── ai_chat_sessions.json          # AI 채팅 세션 이력
```

### 4.4 선택적 PostgreSQL 연동

`db.py`는 `DATABASE_URL` 환경 변수가 설정되어 있고 `psycopg2`가 설치된 경우 자동으로 PostgreSQL에 검색 결과를 저장한다. 미설정 시 JSON 파일로 폴백하므로 외부 DB 없이도 모든 기능이 동작한다.

### 4.5 타입 안전성 및 코드 품질

- **mypy**: `domain/`, `application/`, `container.py`에 strict 타입 검사 적용
- **ruff**: E, F, W, I, UP, B 규칙셋으로 린팅
- **pytest**: `QT_QPA_PLATFORM=offscreen`으로 헤드리스 Qt 테스트
- **커버리지 게이트**: 신규 계층 패키지 85% 이상 필수

---

## 5. Gemma4:e4b 로컬 모델 선택 이유

### 5.1 이중 AI 전략의 배경

CircuitKit은 단일 AI 모델 대신 **로컬 모델과 클라우드 모델을 용도에 따라 분리**하는 하이브리드 전략을 채택했다.

| 용도 | 모델 | 실행 위치 |
|------|------|----------|
| AI 채팅 (부품 Q&A, 일반 대화, RAG) | Gemma4:e4b | 로컬 (Ollama) |
| 데이터시트 분석 (이미지+텍스트 멀티모달) | Gemini 2.5 Flash | 클라우드 (Google API) |

이 분리는 각 작업의 특성에 맞는 최적의 모델을 배치한 결과다.

### 5.2 Gemma4:e4b를 AI 채팅에 선택한 이유

**이유 1: 데이터 프라이버시**
전자 부품 선정은 설계 기밀과 직결된다. 어떤 부품 조합을 사용하는지, BOM 구성이 무엇인지는 경쟁사에 노출되면 안 된다. 로컬 모델은 사용자의 질의가 외부 서버로 전송되지 않으므로 기업 보안 정책을 준수하면서 AI 기능을 사용할 수 있다.

**이유 2: API 비용 제로**
AI 채팅은 반복적이고 빈번하게 발생한다. 클라우드 API를 사용하면 토큰 수에 따라 비용이 누적된다. Gemma4:e4b는 초기 모델 다운로드 이후 추가 비용 없이 무제한 사용이 가능하다.

**이유 3: 완전 오프라인 동작**
인터넷이 불안정한 제조 현장이나 실험실 환경에서도 AI 채팅 기능이 중단 없이 동작한다. Ollama 서버가 로컬에서 실행되므로 네트워크 의존성이 없다.

**이유 4: Rate Limit 없음**
클라우드 API는 분당 요청 수(RPM)와 일일 토큰 한도 제한이 있다. 여러 엔지니어가 동시에 채팅 기능을 사용하거나 자동화 파이프라인에서 배치 처리할 때 클라우드 API 제한에 걸릴 수 있다. 로컬 모델은 이런 제약이 없다.

**이유 5: Gemma 4 세대의 성능 우위**
Google의 Gemma 4 세대는 이전 세대 대비 다음 분야에서 개선을 이뤘다.

- **한국어 능력**: 멀티링구얼 학습 데이터 확장으로 한국어 기술 용어(저항, 커패시터, 절대 최대 정격 등)를 정확히 이해하고 생성한다
- **지시 수행(Instruction Following)**: "이 부품의 동작 전압 범위를 알려줘"와 같은 명확한 질문에 핵심만 답하는 정확도가 향상되었다
- **장문 컨텍스트**: 데이터시트 청크와 부품 스펙을 시스템 프롬프트에 포함시킨 긴 컨텍스트 처리 성능이 개선되었다

**이유 6: `:e4b` 양자화의 실용성**
`e4b`는 4비트 효율적 양자화(Efficient 4-bit) 변형이다. 원본 풀 정밀도 모델 대비 메모리 사용량을 약 75% 줄이면서 성능 손실을 최소화한다.

| 구분 | 원본 모델 | gemma4:e4b |
|------|----------|-----------|
| 메모리 요구량 | ~27GB | ~6-8GB |
| GPU 등급 | A100급 필요 | 소비자용 8GB VRAM 또는 CPU 동작 |
| 응답 속도 | 기준 | 비슷하거나 빠름 (캐시 효율) |

일반 개발용 PC(8GB GPU 또는 32GB RAM)에서 설치 즉시 사용 가능하다.

**이유 7: Ollama 생태계 통합**
Ollama는 로컬 LLM을 REST API로 감싸 단순화한다. `OllamaTextGenerator`는 60줄의 코드로 `generate()`와 `stream_chat()`을 구현하며, 모델 교체는 `model` 파라미터 변경 한 줄로 완료된다. `is_available()` 헬스체크로 Ollama 서버 상태를 런타임에 확인해 그레이스풀 디그레이드를 구현한다.

### 5.3 데이터시트 분석에 Gemini 2.5 Flash를 유지한 이유

로컬 Gemma4:e4b가 AI 채팅을 담당하지만, 데이터시트 PDF 분석은 클라우드 Gemini 2.5 Flash가 담당한다.

- **멀티모달 필요성**: Tesseract OCR이 실패한 이미지 영역(회로도, 패키지 도면, 복잡한 테이블)은 픽셀 데이터를 직접 분석해야 한다. 텍스트 전용 로컬 모델과 달리 Gemini는 이미지를 네이티브로 처리한다
- **정밀도**: 절대 최대 정격(Absolute Maximum Ratings), 핀 기능 테이블 같은 기술 데이터는 오류가 허용되지 않는다. 현시점에서 클라우드 모델의 정밀도가 4비트 양자화 로컬 모델보다 높다
- **응답 캐싱으로 비용 절감**: 동일 데이터시트 영역 분석은 SHA-256 캐시가 API 호출을 차단하므로, 반복 사용 시 비용이 급감한다

### 5.4 미래 확장성

포트-어댑터 설계 덕분에 AI 백엔드 교체가 용이하다. `TextGenerator` 포트를 구현하는 새 어댑터를 작성하면 `container.py` 한 줄만 수정해 Claude, LLaMA, Mistral 등 어떤 모델로도 전환할 수 있다. 로컬 모델의 멀티모달 지원이 충분히 성숙하면 데이터시트 분석도 완전 로컬로 전환하는 로드맵이 열려 있다.

---

## 빠른 시작

```bash
# 1. 환경 설정
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Ollama + Gemma4:e4b 설치 (AI 채팅 기능)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma4:e4b

# 3. Gemini API 키 설정 (데이터시트 AI 기능)
mkdir -p config/api_keys
echo "YOUR_GEMINI_API_KEY" > config/api_keys/gemini_api_keys.txt

# 4. Chrome 프로파일 초기화 (최초 1회)
bash setup_chrome_profile.sh

# 5. 실행
python digikey_price_scraper.py
```

---

*CircuitKit은 전자 엔지니어링 교육 및 실무 환경에서의 부품 탐색 워크플로우를 개선하기 위해 설계된 오픈소스 데스크탑 애플리케이션이다.*
