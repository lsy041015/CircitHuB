# CircuitKit — Electronic Component Discovery Desktop Application

> An engineering workstation integrating DigiKey real-time scraping, AI chat, datasheet analysis, and LAN collaboration

---

## 1. Project Scenario

### 1.1 Background and Problem Definition

Engineers and students in electronic circuit design face repetitive bottleneck tasks every day.

**The Limits of Manual DigiKey Lookup**

DigiKey is one of the world's largest electronic component distributors and serves as a standard data source in Korean engineering environments. However, three fundamental friction points existed in the traditional workflow:

The first is the **search context-switch problem**. A designer using EDA tools like KiCad or Altium must switch to a browser, search DigiKey, copy-paste prices, then return to the design tool. This loop repeats once per component. A BOM with 30 parts means 30 repetitions of this cycle.

The second is the **datasheet language barrier**. Nearly all datasheets are written in English, and Korean engineering students spend considerable time parsing critical electrical characteristic tables or pin maps. Misinterpreting the Absolute Maximum Ratings section in particular can lead to component failure or circuit mis-design.

The third is **team collaboration fragmentation**. Multiple engineers in the same lab or office each open their own browsers, look up the same parts independently, and share results via messaging apps or email — an inherently inefficient workflow.

### 1.2 Solution Goals

CircuitKit was designed to solve all three problems within a single desktop application.

- **Single interface**: Part number entry → live price and spec display → AI query → datasheet viewing, all without leaving the app
- **Korean-language AI analysis**: Drag-select any datasheet region for instant Korean translation and summary
- **LAN sharing**: Send search results to another running instance on the same network with one click, or communicate via group chat

### 1.3 Primary Use Scenarios

**Scenario A — Industrial BOM Quotation**
A purchasing engineer enters `LM358P, NE555P, TL072CP` simultaneously. CircuitKit sequentially scrapes DigiKey via Selenium, displaying each component's price breaks and package specifications as side-by-side cards. A BOM subtotal is calculated automatically.

**Scenario B — Lab Datasheet Study**
A student opens an STM32F4 microcontroller datasheet and drag-selects the "Power Supply Characteristics" table. Gemini 2.5 Flash recognizes the table structure and summarizes the key voltage and current limits in Korean. The student then types "What is the maximum GPIO current for this MCU?" into the AI chat, and the local Gemma4:e4b model answers using the datasheet context.

**Scenario C — Team Component Selection Meeting**
Three members of a design team each run CircuitKit on their own machines. One engineer sends candidate component results to the other two via LAN share. In the group chat, mention-based communication like "@john check the voltage rating on this one" is supported.

---

## 2. Design Process

### 2.1 Architectural Principles

The core architectural principle is that **business logic must not depend on UI or infrastructure**. Hexagonal (Ports & Adapters) architecture was adopted to enforce this.

```
┌──────────────────────────────────────────┐
│           UI Layer (Qt/PySide6)           │
│  MainWindow composed from Mixins          │
├──────────────────────────────────────────┤
│          Application Layer                │
│  SearchService · AiChatService            │
│  RagService · SettingsService             │
├──────────────────────────────────────────┤
│            Domain Layer                   │
│  ProductResult · Ports (Protocol)         │
│  ChatModels · RagModels                   │
├──────────────────────────────────────────┤
│         Infrastructure Layer              │
│  Selenium · Ollama · PyMuPDF              │
│  OpenCV · JSON/PG · InMemoryVectorStore   │
└──────────────────────────────────────────┘
```

Layer boundaries are defined with Python `Protocol` (structural typing). For example, the `SupplierScraper` port requires only four methods — `open()`, `fetch_one()`, `cancel()`, and `close()`. A Selenium implementation or a future Mouser API implementation needs only to satisfy this contract.

### 2.2 GUI Design: Mixin-Based Decomposition

`MainWindow` combines feature-specific Mixin classes through multiple inheritance.

```python
class MainWindow(
    MainWindowChatMixin,        # AI chat panel integration
    MainWindowCategoryMixin,    # Category browser
    MainWindowPartsMixin,       # Part suggestions and autocomplete
    MainWindowSearchMixin,      # Search execution and cancellation
    MainWindowSidebarMixin,     # Sidebar control
    MainWindowIoMixin,          # File save/load
    UiBuilderMixin,             # Widget factory
    SharingMixin,               # TCP share receive server
    PartSuggestionsMixin,       # Spell-correction suggestions
    QMainWindow,
):
```

This pattern prevents a single class from becoming bloated and enforces clear responsibility boundaries for each Mixin.

### 2.3 Asynchronous Processing Strategy

A Qt GUI must never block the main thread. Selenium scraping takes several seconds per component, so `SearchWorker` runs in a dedicated thread and reports progress to the UI via `SearchSignals` (Qt Signals).

```python
class SearchSignals(QObject):
    progress = Signal(int, int, str)    # (current, total, query)
    finished = Signal(list, bool, bool)
    failed   = Signal(str)
```

Ollama AI chat is also handled via streaming, rendering from the first token onward in the UI in real time.

### 2.4 Dependency Injection Design

`container.py` serves as the application's Composition Root.

```python
def build_container() -> Container:
    llm  = OllamaTextGenerator(model="gemma4:e4b")
    repo = JsonAiChatRepository()
    return Container(
        results  = _build_result_repository(),   # JSON → PG auto-fallback
        settings = FileSettingsStore(),
        ai_chat  = AiChatService(llm=llm, repo=repo),
    )
```

The result repository automatically switches to `PgResultRepository` when PostgreSQL is available, or falls back to `JsonResultRepository`. Neither the UI nor business logic needs to know about this difference.

---

## 3. Code Walkthrough

### 3.1 Web Scraping Engine (`scraper.py`)

DigiKey applies Cloudflare bot detection, so a naive `requests`-based approach is blocked. CircuitKit uses two parallel strategies.

**Strategy 1: Chrome Profile Reuse**
`setup_chrome_profile.sh` creates a dedicated Chrome profile directory. The user manually passes the Cloudflare challenge once (`cf_clearance` cookie), and the app reuses this authenticated session on subsequent launches.

**Strategy 2: Intelligent Result Selection**
`choose_product_url_or_candidates()` navigates directly to a product detail page if exactly one exact-match candidate exists, or returns a candidate list for the user to pick from if there are multiple. When a category results page is encountered, `open_largest_top_results_category_if_needed()` automatically navigates to the category containing the most results.

Price parsing in `is_price_break_row()` performs composite validation: the first cell must be a pure integer, and a currency pattern (`$`, `₩`, `€`) must appear in the joined row text, filtering out noise effectively.

### 3.2 Datasheet AI Analysis (`gemma_client.py`)

`GemmaDatasheetAnalyzer` implements two key resilience patterns.

**Multi-Key Round-Robin**
```python
def _next_key(self) -> tuple[str, int]:
    now = time.time()
    for _ in range(len(self._keys)):
        idx = self._rr % len(self._keys)
        self._rr += 1
        if now >= self._blocked_until[idx]:
            return self._keys[idx], idx
    # When all keys are blocked, pick the one that unblocks soonest
    idx = min(range(len(self._keys)), key=lambda i: self._blocked_until[i])
    return self._keys[idx], idx
```

On Rate Limit (HTTP 429), the affected key is blocked for 62 seconds and the retry wait grows via exponential backoff (up to 30 seconds).

**SHA-256 Response Caching**
Identical model + parameters + prompt combinations produce a SHA-256 cache key stored in `~/.gemma_cache/*.json`. Repeated analysis of the same datasheet region completely skips the API call.

### 3.3 Local AI Chat (`ai_chat_service.py` + `ollama_text_generator.py`)

`AiChatService` supports three context modes.

- **`parts` mode**: Injects the current search results as JSON into the system prompt, enabling answers to questions like "What is the supply voltage range of this component?"
- **`rag` mode**: `RagService` retrieves the top 3 most relevant datasheet chunks via similarity search and provides them as context
- **`datasheet` mode**: Provides the title of the currently open datasheet as context

`OllamaTextGenerator.stream_chat()` sends a streaming POST to Ollama's `/api/chat` endpoint and delivers each `message.content` chunk from each JSON line to the `on_chunk` callback in real time.

```python
def stream_chat(self, messages: list[dict], on_chunk: Callable[[str], None]) -> str:
    url = f"{self._base_url}/api/chat"
    payload = {"model": self._model, "messages": messages, "stream": True}
    with httpx.stream("POST", url, json=payload, timeout=120.0) as resp:
        for line in resp.iter_lines():
            data = json.loads(line)
            chunk = data.get("message", {}).get("content", "")
            if chunk:
                on_chunk(chunk)   # Updates UI from Qt slot
```

### 3.4 RAG Infrastructure (`infrastructure/rag/`)

A fully offline vector search was implemented without any external embedding service.

- **`HashingEmbedder`**: Converts text to fixed-dimension vectors via Feature Hashing (the hashing trick). L2 normalization is applied.
- **`InMemoryVectorStore`**: Top-k search via cosine similarity (dot product of L2-normalized vectors).
- **`chunker.py`**: Splits datasheet text into fixed-size chunks with overlapping windows.

This design makes basic RAG functional without an external vector database like Qdrant. In production, a Qdrant adapter can be injected into the `VectorStore` port as a drop-in replacement.

### 3.5 LAN Chat (`chat.py`)

The `ChatMessage` dataclass carries kind, room, sender, body, timestamp, mentions list, emoji reactions, and read-by list. The TCP socket layer uses length-prefixed framing to guarantee message boundaries, and `peer_allowed()` validation ensures only permitted hosts can send messages.

---

## 4. Implementation Environment

### 4.1 Development Environment

| Item | Version / Specification |
|------|------------------------|
| Operating system | Ubuntu 22.04 LTS / Windows 10·11 |
| Language | Python 3.10 or newer |
| GUI framework | PySide6 6.6.3 (official Qt6 Python bindings) |
| Web automation | Selenium 4.21.0 + undetected-chromedriver 3.5.5+ |
| Browser | Google Chrome (ChromeDriver auto-matched) |

### 4.2 AI and Document Processing Stack

| Component | Library | Role |
|-----------|---------|------|
| Cloud LLM | google-genai ≥ 1.0.0 | Gemini 2.5 Flash API (datasheet multimodal) |
| Local LLM | httpx ≥ 0.27 + Ollama | Gemma4:e4b streaming chat |
| PDF rendering | PyMuPDF 1.27.2 | Page rasterization, text extraction |
| Computer vision | OpenCV 4.11.0.86 | Datasheet table region auto-detection |
| OCR | pytesseract 0.3.13 | Text recognition from image regions |
| Numerical ops | numpy < 2 | Image array processing, vector math |
| HTML parsing | beautifulsoup4 4.12.3 | DigiKey page structure parsing |

### 4.3 Data Storage Structure

```
~/.local/share/digikey-scraper/   (or DIGIKEY_SCRAPER_DATA_DIR)
├── app_settings.json              # User preferences
├── auto_saved_results/            # Auto-saved search results
├── shared_specs/                  # Received shared specs
├── .gemma_cache/                  # Gemini response cache
└── ai_chat_sessions.json          # AI chat session history
```

### 4.4 Optional PostgreSQL Integration

`db.py` automatically saves search results to PostgreSQL when `DATABASE_URL` is set and `psycopg2` is installed. Without these, it falls back to JSON files — all features work without any external database.

### 4.5 Type Safety and Code Quality

- **mypy**: Strict type checking applied to `domain/`, `application/`, and `container.py`
- **ruff**: Linting with rulesets E, F, W, I, UP, B
- **pytest**: Headless Qt testing via `QT_QPA_PLATFORM=offscreen`
- **Coverage gate**: 85% minimum required for new layered packages

---

## 5. Why Gemma4:e4b as the Local Model

### 5.1 Background: The Dual-AI Strategy

Rather than a single AI model, CircuitKit adopts a **hybrid strategy that separates local and cloud models by task type**.

| Task | Model | Runtime |
|------|-------|---------|
| AI chat (part Q&A, general conversation, RAG) | Gemma4:e4b | Local (Ollama) |
| Datasheet analysis (image + text multimodal) | Gemini 2.5 Flash | Cloud (Google API) |

This separation assigns the optimal model to each task based on its characteristics.

### 5.2 Why Gemma4:e4b for AI Chat

**Reason 1: Data Privacy**
Electronic component selection is directly tied to design confidentiality. Which components are used, and what the BOM contains, must not be exposed to competitors. A local model ensures that user queries never leave the machine, enabling AI features to be used in full compliance with corporate security policies.

**Reason 2: Zero API Cost**
AI chat occurs repeatedly and frequently. Cloud API usage accumulates costs proportional to token count. Gemma4:e4b requires no recurring fees after the initial model download — unlimited usage at zero marginal cost.

**Reason 3: Fully Offline Operation**
In manufacturing environments or laboratories with unstable internet, the AI chat feature runs uninterrupted. The Ollama server runs locally with no network dependency.

**Reason 4: No Rate Limits**
Cloud APIs impose requests-per-minute (RPM) and daily token quota limits. Multiple engineers using the chat feature simultaneously, or batch-processing in an automation pipeline, can exhaust these limits. Local models have no such constraints.

**Reason 5: Gemma 4 Generation Performance**
Google's Gemma 4 generation delivered improvements over previous generations in several areas relevant to this project:

- **Korean language capability**: Expanded multilingual training data enables accurate understanding and generation of Korean technical terms (저항/resistor, 커패시터/capacitor, 절대 최대 정격/absolute maximum ratings, etc.)
- **Instruction following**: Improved accuracy in answering focused questions like "Tell me the operating voltage range of this component" with only the essential information
- **Long context handling**: Better performance processing long system prompts containing datasheet chunks and component specifications side by side

**Reason 6: Practical Value of `:e4b` Quantization**
`e4b` is the Efficient 4-bit quantization variant. It reduces memory usage by approximately 75% compared to the full-precision model while minimizing quality degradation.

| Metric | Base Model | gemma4:e4b |
|--------|-----------|-----------|
| Memory required | ~27 GB | ~6–8 GB |
| GPU requirement | A100-class | Consumer 8 GB VRAM or CPU |
| Response speed | Baseline | Similar or faster (cache efficiency) |

This makes the model usable on a typical development machine (8 GB GPU or 32 GB RAM) with no special hardware requirements.

**Reason 7: Ollama Ecosystem Integration**
Ollama wraps local LLMs behind a simple REST API. `OllamaTextGenerator` implements `generate()` and `stream_chat()` in around 60 lines of code, and switching models requires changing only the `model` parameter — one line in `container.py`. The `is_available()` health check verifies Ollama server status at runtime, enabling graceful degradation when the server is not running.

### 5.3 Why Gemini 2.5 Flash Remains for Datasheet Analysis

While Gemma4:e4b handles AI chat, cloud-based Gemini 2.5 Flash handles datasheet PDF analysis. The reasons are clear:

- **Multimodal requirement**: Image regions where Tesseract OCR fails — schematics, package drawings, complex tables — require direct pixel analysis. Unlike a text-only local model, Gemini natively processes images in the same request as text
- **Accuracy**: Technical data such as Absolute Maximum Ratings and pin function tables cannot tolerate errors. At present, cloud model precision is higher than that of a 4-bit quantized local model for this task
- **Cache-driven cost reduction**: Repeated analysis of the same datasheet region is intercepted by SHA-256 caching, so costs drop sharply with regular use

### 5.4 Future Extensibility

The ports-and-adapters design makes AI backend replacement straightforward. Writing a new adapter that implements the `TextGenerator` port and changing one line in `container.py` is sufficient to switch to Claude, LLaMA, Mistral, or any other model. As local model multimodal capability matures, a roadmap exists to migrate datasheet analysis to fully local inference as well.

---

## Quick Start

```bash
# 1. Set up environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Install Ollama + Gemma4:e4b (for AI chat)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma4:e4b

# 3. Configure Gemini API key (for datasheet AI features)
mkdir -p config/api_keys
echo "YOUR_GEMINI_API_KEY" > config/api_keys/gemini_api_keys.txt

# 4. Initialize Chrome profile (once only)
bash setup_chrome_profile.sh

# 5. Run
python digikey_price_scraper.py
```

---

*CircuitKit is an open-source desktop application designed to streamline the component discovery workflow in electronic engineering education and professional practice.*
