<p align="center">
  <img src="assets/circithub-banner.png" alt="CircitHuB — parts search, datasheets, local AI and LAN teamwork in one app" width="100%">
</p>

<p align="center"><a href="README.md">한국어</a> · <b>English</b></p>

# CircitHuB

The app's own window title and sidebar say **CircuitKit**, older docs say **CircuitHUB**, and the Python package is `digikey-scraper`.

> **Type a part number and get DigiKey prices, specs and the datasheet in one window; drag over a table in an English datasheet and get it translated or summarized in Korean.**

A PySide6 (Qt6) desktop app for Korean electronics students and engineers, with a local Ollama AI chat, LAN result sharing and a team chat.

> **Status: personal project, prototype.** Search, datasheet region translate/summarize, LAN sharing and team chat are implemented; 274 of 276 tests pass
> (Windows, Python 3.10). The AI chat context modes are not wired into the UI yet, and live DigiKey search was not re-checked while writing this.

## Why

Three frictions repeat every day in circuit work: switching between KiCad/Altium and the browser once per BOM line (30 parts, 30 round trips),
English-only datasheets where misreading Absolute Maximum Ratings can damage a part, and teammates looking up the same parts separately and
passing results around by chat or email. CircitHuB keeps search, datasheets, AI questions and sharing inside one app.

## What it does

| Feature | Details |
|---|---|
| DigiKey search | One or many part numbers; drives Chrome to collect price breaks, key specs and datasheet links as cards. Several matches come back as a candidate list. |
| BOM | Reads part numbers from `.txt`/`.csv`/`.tsv` (UTF-8, falling back to CP949); repeats count as quantity; the BOM total uses the unit price for each part's quantity. |
| Sort and filter | By price, stock or fetch time; by component type; spec ranges that understand SI prefixes such as `4.7k` or `100n`; hide errors. |
| Categories | 12 tiles (resistor, capacitor, MOSFET, MCU, ...) load the first page of a DigiKey category, up to 25 items. |
| Datasheet viewer | Downloads the PDF (up to 100 MB), renders at 150 DPI, and sends a dragged region to Gemini for Korean translation or summary; Tesseract OCR covers pages without a text layer. |
| AI chat | Streams answers from local Ollama `gemma4:e4b` and saves sessions. Modes that inject part results, datasheet RAG chunks or the datasheet title exist in the service (see Limits). |
| LAN | Sends result text to another instance over TCP; a team chat server with channels, mentions, reactions and threads. |
| Storage and packaging | Text export and auto-save; search history as JSON, or PostgreSQL when `DATABASE_URL` is set; Korean/English UI; PyInstaller spec for a Windows `.exe`. |

## How it works

Business logic must not depend on the UI or infrastructure, so the code follows a four-layer ports-and-adapters design. Boundaries are Python
`Protocol`s: `SupplierScraper`, for example, only needs `open()`, `fetch_one()`, `cancel()` and `close()`, so a future Mouser adapter only has to meet that contract.

```text
 [UI]  MainWindow (PySide6, 9 mixins) · AiChatPanel · DatasheetViewer · team chat window
   │     SearchWorker thread → Qt signals for progress and results
   ▼
 [Application]  SearchService · AiChatService · RagService · FileSettingsStore
   │     depends only on domain Protocol ports
   ▼
 [Domain]  ProductResult · SupplierScraper · TextGenerator · VectorStore · pricing
   ▲
   │     container.py build_container() wires the adapters
 [Infrastructure]
   scraping/     ResilientSupplier → SeleniumDigiKeyScraper → Chrome → DigiKey
   llm/          OllamaTextGenerator → localhost:11434 (gemma4:e4b)
   persistence/  JSON files · PostgreSQL (DATABASE_URL)
   rag/          HashingEmbedder · InMemoryVectorStore · chunker
   cv/           OpenCV image ops

 DatasheetViewer ─(region text + PNG)─▶ gemma_client.py ─▶ Gemini API (gemini-2.5-flash)
```

The AI work is split on purpose:

| Task | Model | Where | Code |
|---|---|---|---|
| Chat (part Q&A, general, RAG) | `gemma4:e4b` | local Ollama | `ollama_text_generator.py`, `ai_chat_service.py` |
| Datasheet region translate/summarize (text + image) | `gemini-2.5-flash` | Google Gemini API | `gemma_client.py` |

Despite its name, `gemma_client.py` (`class GemmaDatasheetAnalyzer`) calls Gemini: `GEMMA_MODEL = "gemini-2.5-flash"`, and it reads keys under both `GEMINI_*` and `GEMMA_*` names.
`AiChatService` has `general` plus three context modes: `parts` (search results as JSON in the system prompt), `rag` (top 3 datasheet chunks from `RagService`)
and `datasheet` (the open datasheet's title). It sends the last 10 messages as history.

Why local `gemma4:e4b` for chat, as the project records it: (1) part choices and BOMs are design secrets, and a local model never sends questions off the machine; (2) no per-token cost;
(3) works offline in labs and factories; (4) no requests-per-minute or daily token limits; (5) the Gemma 4 generation was judged better at Korean
technical terms, focused instruction following and long prompts; (6) the small `e4b` variant targets an ordinary dev PC (8 GB VRAM GPU or 32 GB RAM);
(7) Ollama keeps the adapter small: `OllamaTextGenerator` is 60 lines and the model is one string in `container.py` (its `is_available()` health check exists but the app does not call it yet).
Datasheet regions stay on Gemini because OCR failures (schematics, package drawings, dense tables) need the pixels (the Ollama path sends text only),
because ratings tables must be accurate, and because a SHA-256 cache avoids paying twice for the same region.

## Screens

The repository only has screenshots from the datasheet-viewer audit of 2026-05-31
([`docs/pdf_viewer_full_manual_audit.md`](docs/pdf_viewer_full_manual_audit.md)), taken with synthetic PDFs.
**There are no screenshots of the main search window or the AI chat panel yet.**

<table>
  <tr>
    <td><img src="docs/pdf_viewer_audit/01_initial_loaded.png" alt="Datasheet viewer with a synthetic ABSOLUTE MAXIMUM RATINGS table"></td>
    <td><img src="docs/pdf_viewer_audit/05_shown_table_detection.png" alt="Table detection boxes with the detection-candidates panel"></td>
  </tr>
  <tr>
    <td align="center"><sub>Viewer at load: filter, zoom, preset and search controls, OCR and Gemma badges</sub></td>
    <td align="center"><sub>Table detection: boxes on the table and title, candidate rows, analyze / false-positive / restore</sub></td>
  </tr>
</table>

That audited viewer passed 39 of 39 of the project's own checks ([`audit_results.json`](docs/pdf_viewer_audit/audit_results.json)). The current
`datasheet_viewer.py` is a minimal viewer with region translate/summarize only; the filters, presets, search and table/pin-map detection shown above are
not in today's code. The image filters remain in `infrastructure/cv/image_ops.py` and are covered by tests only.

## Run

Needs Python 3.10+ and Google Chrome. Optional: Tesseract (OCR), Ollama with `gemma4:e4b` (chat), a Gemini API key (datasheet AI), Docker (PostgreSQL).
Chrome, Tesseract and Gemini keys are not bundled in the `.exe`. Pinned stack: PySide6 6.6.3, Selenium 4.21.0, undetected-chromedriver >= 3.5.5, beautifulsoup4 4.12.3,
google-genai >= 1.0.0, httpx >= 0.27, numpy < 2, opencv-python 4.11.0.86, PyMuPDF 1.27.2, pytesseract 0.3.13; dev tools are pytest, pytest-cov, ruff, mypy and pip-audit.

```bash
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
curl -fsSL https://ollama.com/install.sh | sh && ollama pull gemma4:e4b   # optional, AI chat
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"                              # optional, datasheet AI
bash setup_chrome_profile.sh                                             # once, see below
python digikey_price_scraper.py                                          # or: python -m digikey_scraper.qt_gui

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen python -m pytest -q   # tests
```

- **Cloudflare step.** DigiKey may show a Cloudflare check. `setup_chrome_profile.sh` opens DigiKey in a dedicated Chrome profile
  (`~/.local/share/digikey-scraper/chrome-profile`); you watch the check finish once, press Enter and close Chrome, and the `cf_clearance` cookie stays in the profile.
  The app reuses that profile and starts Chrome with `undetected-chromedriver` (plain Selenium as a fallback). The script says the cookie lasts about 24-48 hours.
  It assumes bash and Linux Chrome paths; on Windows, point `DIGIKEY_CHROME_USER_DATA_DIR` at a profile. **Follow DigiKey's terms of use;** the app looks up parts one by one and is not meant for bulk scraping.
- **API keys.** `GEMINI_API_KEY` or `GEMINI_API_KEYS` (comma or newline separated; `GEMMA_*` names also work), then `config/settings.env`, then a key file in
  `config/api_keys/` (`gemini_api_keys.txt`, `gemma_api_keys.txt`, or the singular forms), then `GEMMA_CONFIG_ROOT`. The repo has no `.gitignore`, so a key file there is **not** ignored by git.
- **Other variables.** `DIGIKEY_CHROME_PROFILE_DIRECTORY` (profile folder name), `DIGIKEY_SCRAPER_DATA_DIR` (defaults to `%LOCALAPPDATA%\DigiKeyPriceScraper` or
  `~/.local/share/digikey_price_scraper`), `TESSERACT_CMD`, `DIGIKEY_SHARE_BIND_HOST` (share receiver address, default `127.0.0.1`), `DATABASE_URL`.
- **Data folder.** `app_settings.json`, `auto_saved_results/` (exports and team chat history), `search_history/`, `shared_specs/`, `.gemma_cache/`, `ai_chat_sessions.json`.
- **PostgreSQL.** `pip install -r requirements-dev.txt`, `docker compose up -d db`, then
  `export DATABASE_URL=postgresql+psycopg2://digikey:digikey@localhost:5432/digikey`. Without it, or if DB setup fails, history falls back to JSON.
- **Windows build.** `powershell -ExecutionPolicy Bypass -File scripts\build_windows_exe.ps1` produces `dist\DigiKeyPriceScraper\DigiKeyPriceScraper.exe`;
  install PyInstaller yourself, it is not in the requirements files. See [`docs/windows_release_checklist.md`](docs/windows_release_checklist.md).

## Usage

1. Run `setup_chrome_profile.sh` once. Then enter part numbers (`LM358P, NE555P, TL072CP`) or use **BOM 가져오기** (Import BOM); adjust quantities on the chips.
2. Press **조회 시작** (Start). Cards show price breaks, specs and links; the status strip shows success/error/blocked/candidate counts, average response time and the BOM total.
   Turn on **브라우저 창 표시** (show browser) if DigiKey keeps asking for a security check.
3. Open **데이터시트** on a card, pick **영역 번역** (translate) or **영역 요약** (summarize), and drag over a table (at least 20×20 px). Each viewer window asks
   once for consent before uploading the region to Gemini ("be careful with confidential/NDA documents").
4. **AI 채팅** opens the local chat dock; answers stream token by token while Ollama is running.
5. To send results, enter the peer IP and port (default 5000) and press **전송** (Send). To receive from another PC, the receiver must set `DIGIKEY_SHARE_BIND_HOST` (for example `0.0.0.0`) before launching the app.
   For team chat, one person presses **서버 시작** (start server, default port 5100) and the others connect; an optional token and allowed-hosts list filter peers.

The original README's scenarios still describe the intent: (A) quoting a three-part BOM with side-by-side price cards and a total, which the code implements;
(B) summarizing an STM32F4 "Power Supply Characteristics" table and then asking the local model about GPIO current, where the summary works but the chat
does not receive datasheet context yet; (C) a team meeting where one engineer shares candidates over LAN and mentions a colleague in the group chat, both implemented.
Step-by-step instructions and troubleshooting are in [USAGE_MANUAL.md](USAGE_MANUAL.md) (Korean).

## Design notes

- `SearchService` runs and is tested without Qt; `SearchWorker` only adds signals. Strict mypy and the 85% coverage gate cover the new layers only, fencing off legacy GUI/CV code.
- Round-robin API keys: a key that hits a retryable error (429, 503, ...) rests for 62 s; the next free key is tried after 1.5 s, and if all are resting the wait grows to at most 30 s.
  Responses are cached under a SHA-256 of model, output length, task, prompt and image bytes.
- `PRICE_PATTERN` accepts `$`, `₩`, `€` and `£`, and `MAIN_SPEC_ALIASES` maps 10 spec fields to both Korean and English DigiKey labels (`constants.py`).
- `ResilientSupplier` retries ordinary errors twice (0.5 s, 1 s) but never retries `ScrapeBlocked`; on a block, `SearchService` waits 8 s and checks once more, then marks the part blocked.
- RAG runs fully offline: a 256-dimension hashing embedder, an in-memory cosine store and 500-character chunks with 50 characters of overlap. `CitationEnforcingAnswerer`
  checks that an answer's words actually appear in the chunks it cites and refuses when support is weak (tested, not yet wired into the app).
- Safe defaults for LAN: the share receiver listens on `127.0.0.1` unless told otherwise; shares are capped at 5 MB, metadata at 64 KB and chat frames at 64 KB.

<details>
<summary>Composition root and streaming chat code</summary>

```python
def build_container() -> Container:
    llm = OllamaTextGenerator(model="gemma4:e4b")
    repo = JsonAiChatRepository()
    return Container(
        results=_build_result_repository(),   # PostgreSQL if DATABASE_URL is set, else JSON
        settings=FileSettingsStore(),
        ai_chat=AiChatService(llm=llm, repo=repo),
    )

# OllamaTextGenerator.stream_chat(), core loop
with httpx.stream("POST", url, json=payload, timeout=120.0) as resp:
    resp.raise_for_status()
    for line in resp.iter_lines():
        if not line:
            continue
        data = json.loads(line)
        chunk = data.get("message", {}).get("content", "")
        if chunk:
            on_chunk(chunk)
            full.append(chunk)
        if data.get("done"):
            break
```

</details>

## Limits

- The chat context modes are not connected in the running app: nothing calls `set_parts_context()` on the main chat panel, `container.py` passes no `RagService`,
  and `open_datasheet()` passes no chat service to the viewer. Every mode currently behaves like plain chat. The RAG tokenizer is `[a-z0-9]+`, so Korean-only questions find nothing.
- The screenshots show an older viewer, and `benchmarks/datasheet_table_detection/` is a stub with one synthetic annotation and no results.
- Two hygiene tests in `tests/test_repo_hygiene.py` fail because the repo has no `.gitignore` (with `build/` and `dist/`) and no `.github/workflows/windows.yml`.
- [`code-review`](code-review) (2026-06-22) still lists open items: `_GemmaRegionWorker` ignores `isInterruptionRequested()`, no viewer guards when `cv2`/`fitz`/`numpy`
  are missing, no return type on `create_driver`, `google-genai` import errors caught as `Exception`, plus a fixed 30 s PDF timeout, Otsu-only OCR thresholding,
  a one-page render cache and a few refactors. Its "put the model name in the cache key" item is already done in the code.
- Chrome setup is Linux-first; the app depends on DigiKey's page structure; `CachingSupplier` and `AggregatingSupplier` (best price across suppliers) exist but are unused.

## Credits

No license file (and no `license` field in `pyproject.toml`). The bundled Pretendard and JetBrains Mono fonts are not original work, and the repo ships no font
license files. Part data and datasheets belong to DigiKey and the manufacturers; use DigiKey under its terms of use and Gemini under Google's terms.
DigiKey, Google, Gemini, Gemma, Ollama and Cloudflare are trademarks of their owners; naming them implies no affiliation or endorsement.

---

<p align="center"><sub>LSY.KOR · <a href="https://github.com/lsy041015">More projects</a></sub></p>
