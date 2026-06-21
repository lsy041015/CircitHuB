# 로컬 LLM 채팅 기능 설계

**날짜:** 2026-06-20  
**상태:** 승인됨  
**모델:** Ollama + Gemma4:e4b

---

## 1. 목표

DigiKey 스크래퍼 앱에 Ollama 기반 로컬 LLM 채팅 기능 추가.

- 일반 대화 (general)
- 현재 부품 검색 결과를 컨텍스트로 활용한 대화 (parts)
- 데이터시트 RAG 기반 Q&A (rag)
- 대화 기록 로컬 JSON 저장 및 복원

---

## 2. 아키텍처

기존 헥사고날(포트-어댑터) 아키텍처를 그대로 따름.

```
domain/
  ports.py          — AiChatRepository 포트 추가
  chat_models.py    — AiChatMessage, AiChatSession 데이터 클래스 (신규)

application/
  ai_chat_service.py  — AiChatService 오케스트레이션 (신규)

infrastructure/
  llm/
    __init__.py
    ollama_text_generator.py  — OllamaTextGenerator, TextGenerator 포트 구현 (신규)
  persistence/
    json_ai_chat_repository.py  — AiChatRepository JSON 구현 (신규)

digikey_scraper/
  _ai_chat_panel.py      — 메인 윈도우 사이드 패널 위젯 (신규)
  _main_window.py        — AI 채팅 도크 위젯 토글 슬롯 추가 (수정)
  _main_window_chat.py   — AI 채팅 패널 초기화 연결 (수정)
  datasheet_viewer.py    — 하단 splitter에 AI Q&A 패널 삽입 (수정)
  container.py           — OllamaTextGenerator, JsonAiChatRepository 바인딩 (수정)

requirements.txt  — httpx 추가 (수정)
```

### 데이터 흐름

```
UI 입력
  → AiChatService.send_message(session_id, text, context_mode)
      context_mode="general"  → 메시지 그대로 전달
      context_mode="parts"    → 부품 목록 JSON을 system 메시지에 주입
      context_mode="rag"      → RagService.retrieve() 청크를 system 메시지에 주입
  → OllamaTextGenerator.stream_chat(messages, on_chunk)
      → POST http://localhost:11434/api/chat (stream=True)
      → 청크마다 Qt 시그널 emit → UI 실시간 업데이트
  → 완료 시 JsonAiChatRepository.save_session()
```

---

## 3. 데이터 모델

### `domain/chat_models.py`

```python
@dataclass
class AiChatMessage:
    role: str          # "user" | "assistant"
    content: str
    timestamp: float

@dataclass
class AiChatSession:
    id: str
    title: str         # 첫 메시지 앞 30자 자동 생성
    context_mode: str  # "general" | "parts" | "rag"
    messages: list[AiChatMessage]
    created_at: float
    updated_at: float
```

### 저장 형식

파일: `auto_saved_results/ai_chat_sessions.json`

```json
{
  "sessions": [
    {
      "id": "uuid4",
      "title": "부품 추천 문의",
      "context_mode": "parts",
      "messages": [
        {"role": "user", "content": "...", "timestamp": 1718800000.0},
        {"role": "assistant", "content": "...", "timestamp": 1718800005.0}
      ],
      "created_at": 1718800000.0,
      "updated_at": 1718800005.0
    }
  ]
}
```

---

## 4. 포트 추가

### `domain/ports.py` 에 추가

```python
@runtime_checkable
class AiChatRepository(Protocol):
    def save_session(self, session: AiChatSession) -> None: ...
    def load_sessions(self) -> list[AiChatSession]: ...
    def delete_session(self, session_id: str) -> None: ...
```

---

## 5. Ollama 어댑터

### `infrastructure/llm/ollama_text_generator.py`

```python
class OllamaTextGenerator:
    def __init__(self, model: str = "gemma4:e4b", base_url: str = "http://localhost:11434")

    def generate(self, prompt: str) -> str:
        # 단발성 생성 — RAG Answerer 포트 구현용
        # POST /api/generate

    def stream_chat(
        self,
        messages: list[dict],
        on_chunk: Callable[[str], None],
    ) -> str:
        # 스트리밍 채팅 — POST /api/chat stream=True
        # 청크마다 on_chunk(chunk_text) 호출

    def is_available(self) -> bool:
        # GET /api/tags — 서버 실행 여부 + 모델 존재 확인
```

**Ollama 미실행 시:** 예외 캐치 후 오류 메시지를 채팅 버블로 표시. 앱 크래시 없음.

---

## 6. AiChatService

### `application/ai_chat_service.py`

```python
class AiChatService:
    def __init__(
        self,
        llm: OllamaTextGenerator,
        repo: AiChatRepository,
        rag_service: RagService | None = None,
    )

    def new_session(self, context_mode: str = "general") -> AiChatSession

    def send_message(
        self,
        session: AiChatSession,
        text: str,
        on_chunk: Callable[[str], None],
        parts_context: list[dict] | None = None,   # context_mode="parts" 시
        rag_query: str | None = None,              # context_mode="rag" 시 — None이면 text를 그대로 사용
    ) -> str

    def load_sessions(self) -> list[AiChatSession]
    def save_session(self, session: AiChatSession) -> None
    def delete_session(self, session_id: str) -> None
```

---

## 7. UI

### 메인 윈도우 사이드 패널 (`_ai_chat_panel.py`)

- `QDockWidget` — 우측 도크, 토글 가능
- 상단: 세션 선택 드롭다운 + [새 대화] 버튼
- 컨텍스트 콤보박스: 일반 / 현재 부품 결과 / 데이터시트 RAG
- 채팅 버블 영역: `QScrollArea` + 동적 레이블
- 하단: 텍스트 입력창 + [전송] 버튼 (Enter 키 전송)
- 스트리밍 중 [전송] 버튼 비활성화

```
┌─────────────────────────────────┐
│ AI 채팅        [새 대화] [세션▼]│
├─────────────────────────────────┤
│ 컨텍스트: [일반            ▼]   │
├─────────────────────────────────┤
│                                 │
│  [AI] 안녕하세요. 무엇을...     │
│                                 │
│            [사용자] 이 부품...  │
│                                 │
│  [AI] (스트리밍 중...)          │
│                                 │
├─────────────────────────────────┤
│ [입력창              ] [전송]   │
└─────────────────────────────────┘
```

### 데이터시트 뷰어 패널 (`datasheet_viewer.py` 수정)

- 기존 PDF 뷰어 영역 + 하단 `QSplitter`로 AI Q&A 패널 추가
- 기존 Gemini 분석 탭 옆에 "Ollama Q&A" 탭 추가
- 자동으로 context_mode="rag", 현재 열린 데이터시트 대상

```
┌──────────────────────────────────────────────┐
│ [PDF 뷰어 영역]                              │
├──────────────────────────────────────────────┤
│ [Gemini 분석] [Ollama Q&A]                  │
│ ─────────────────────────────────────────── │
│ Q: 최대 전압은?                              │
│ A: 40V (p.3 Table 1 참조)                   │
│ ─────────────────────────────────────────── │
│ [데이터시트에 대해 질문하세요...  ] [전송]  │
└──────────────────────────────────────────────┘
```

---

## 8. 수정/신규 파일 요약

| 구분 | 파일 | 내용 |
|------|------|------|
| 신규 | `domain/chat_models.py` | 데이터 클래스 |
| 신규 | `application/ai_chat_service.py` | 채팅 서비스 |
| 신규 | `infrastructure/llm/__init__.py` | 패키지 |
| 신규 | `infrastructure/llm/ollama_text_generator.py` | Ollama 어댑터 |
| 신규 | `infrastructure/persistence/json_ai_chat_repository.py` | JSON 저장소 |
| 신규 | `digikey_scraper/_ai_chat_panel.py` | 사이드 패널 위젯 |
| 수정 | `domain/ports.py` | AiChatRepository 포트 추가 |
| 수정 | `digikey_scraper/container.py` | 새 어댑터 바인딩 |
| 수정 | `digikey_scraper/_main_window.py` | 도크 토글 슬롯 |
| 수정 | `digikey_scraper/_main_window_chat.py` | AI 패널 초기화 |
| 수정 | `digikey_scraper/datasheet_viewer.py` | Ollama Q&A 탭 |
| 수정 | `requirements.txt` | httpx 추가 |

---

## 9. 의존성

```
httpx>=0.27   # Ollama HTTP 클라이언트 (스트리밍 지원)
```

Ollama는 별도 설치 및 실행 필요 (`ollama serve`, 모델: `gemma4:e4b`).

---

## 10. 테스트 고려사항

- `OllamaTextGenerator` — `is_available()` 단위 테스트 (mock HTTP)
- `AiChatService` — mock LLM + mock repo로 컨텍스트 주입 로직 검증
- `JsonAiChatRepository` — 저장/로드/삭제 round-trip 테스트
- UI 테스트: `QT_QPA_PLATFORM=offscreen` 환경에서 패널 초기화 확인
