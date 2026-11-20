<p align="center">
  <img src="assets/circithub-banner.png" alt="CircitHuB — parts search, datasheets, local AI and LAN teamwork in one app" width="100%">
</p>

<p align="center"><a href="README.md">한국어</a> · <b>English</b></p>

# CircitHuB

A PySide6 desktop app: type a part number and it pulls DigiKey prices, specs and the datasheet into one window, and if you drag over a table in an English datasheet it translates or summarizes it into Korean.

In circuit labs I kept opening a DigiKey tab for every part, copying prices, and squinting at English electrical-characteristics tables. With 30 parts in a BOM, that's 30 round trips. People in the same lab look up the same parts separately and pass results around in messengers. I got tired of that and put it all in one app.

The naming is a bit messy: the app window says **CircuitKit**, older docs say **CircuitHUB**, and the Python package is `digikey-scraper`. It changed a few times along the way.

## What it does

- **DigiKey search.** Enter one or more part numbers (`LM358P, NE555P, TL072CP`) and it drives Chrome to fetch price breaks, key specs and datasheet links as cards. If several parts match, you get a candidate list, and one failing part doesn't stop the rest.
- **BOM.** Reads part numbers from `.txt`, `.csv` or `.tsv`, counts repeats as quantity, and totals the BOM using the right price break for each quantity.
- **Datasheet viewer.** Open a PDF, drag over a table, and only that region goes to Gemini (`gemini-2.5-flash`) for a Korean translation or summary. PDFs without a text layer go through Tesseract OCR, and asking about the same region again comes straight from the cache.
- **AI chat.** Streaming chat with `gemma4:e4b` on a local Ollama, with saved sessions.
- **LAN sharing and team chat.** Send search results to another PC on the same network, and host or join a team chat with channels, mentions, reactions and threads.
- Also: category search (12 tiles like resistors and MCUs), a spec filter that understands SI prefixes like `4.7k` and `100n`, a Korean/English UI, and a Windows `.exe` build.

<p align="center">
  <img src="docs/pdf_viewer_audit/05_shown_table_detection.png" alt="Table detection boxes in the datasheet viewer with the detection-candidates panel" width="100%">
</p>
<p align="center"><sub>The datasheet viewer during a May 2026 audit, on a synthetic PDF. Today's viewer is a slimmer version with only region translate/summarize, so the filters and table detection are gone. I haven't captured the main search window yet.</sub></p>

## How you use it

1. Type part numbers into the input box or use **BOM 가져오기** (Import BOM). While you type, it suggests similarly spelled parts from favorites and recent searches.
2. Press **조회 시작** (Start). You get progress and time left, then each card shows price breaks, specs and the datasheet link. The status strip shows success/error/blocked counts and the BOM total. If DigiKey keeps asking for a security check, turn on **브라우저 창 표시** (show browser) and pass it yourself.
3. Press **데이터시트** on a card to open the viewer, pick **영역 번역** (translate) or **영역 요약** (summarize), and drag over a table to get the result window.
4. **AI 채팅** in the sidebar opens the chat panel on the right (Ollama has to be running).
5. To send results to another PC, enter its IP and port (default 5000) and press **전송** (Send). For team chat, one person presses **서버 시작** (start server, default 5100) and the others join with the IP and a nickname. The share receiver only listens on `127.0.0.1` by default, so to receive from another PC, set `DIGIKEY_SHARE_BIND_HOST` to something like `0.0.0.0` on the receiving side.

## Things I cared about

**The AI is split in two.** Which parts you combine is design-confidential, so the everyday chat runs on local `gemma4:e4b` and never leaves the machine. No API bills, no rate limits, and it works on a flaky connection. Only datasheet analysis, which has to read images like schematics or dense tables and can't afford mistakes, goes to Gemini, and the app asks for consent first ("be careful with confidential/NDA documents"). Heads-up: despite its name, `gemma_client.py` calls Gemini. It's a leftover from switching models midway.

**It doesn't hammer DigiKey when blocked.** DigiKey sometimes shows a Cloudflare check to automated visits. Ordinary errors get retried twice, but on a block it waits 8 seconds, checks once more, and if it's still blocked it marks that part "blocked". On the Gemini side, multiple API keys are rotated, and a key that hits 429 or 503 rests for a bit.

**Hexagonal (Ports & Adapters) layout.** The search loop (`SearchService`) runs and is tested without Qt; the UI's `SearchWorker` only adds signals. So another supplier like Mouser could plug in by implementing the `SupplierScraper` port. The RAG is hand-rolled too, with a hashing embedder and an in-memory vector store, and it refuses to answer when the words in an answer don't actually appear in the chunks it cites.

If you want to read the code, this is most of what you need.

```text
digikey_scraper/
├── _main_window*.py      # main window (9 feature mixins)
├── datasheet_viewer.py   # PDF viewer, region translate/summarize
├── gemma_client.py       # Gemini calls, key rotation, SHA-256 response cache
├── scraper.py, driver.py # DigiKey parsing, Chrome driver
├── chat.py, sharing.py   # LAN team chat, result sharing (TCP)
├── container.py          # build_container() wires the implementations
├── application/  domain/  infrastructure/
tests/                    # 276 tests
```

## Install and run

You need Python 3.10+ and Google Chrome. Tesseract (OCR), Ollama (AI chat), a Gemini API key (datasheet translation) and Docker (PostgreSQL) are optional, depending on what you want to use.

```bash
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
curl -fsSL https://ollama.com/install.sh | sh && ollama pull gemma4:e4b   # optional, AI chat
export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"                              # optional, datasheet AI
bash setup_chrome_profile.sh                                             # once, see below
python digikey_price_scraper.py                                          # or: python -m digikey_scraper.qt_gui

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen python -m pytest -q   # tests
```

`setup_chrome_profile.sh` opens DigiKey in a dedicated Chrome profile. Watch the check finish and the results appear, press Enter and close Chrome, and the app reuses that session. The cookie expires after roughly 24-48 hours, so just run it again then. The script assumes Linux, so on Windows point `DIGIKEY_CHROME_USER_DATA_DIR` at a profile instead.

This is for looking up parts one at a time. Please follow DigiKey's terms of use and don't use it for bulk scraping.

Settings, saved results, search history, team chat history and the Gemini cache all live in a data folder: `%LOCALAPPDATA%\DigiKeyPriceScraper` on Windows, `~/.local/share/digikey_price_scraper` on Linux, or wherever `DIGIKEY_SCRAPER_DATA_DIR` points. Gemini keys are looked up in environment variables, then `config/settings.env`, then key files in `config/api_keys/`.

Step-by-step screens and troubleshooting are in [USAGE_MANUAL.md](USAGE_MANUAL.md) (Korean).

Search history goes to JSON files by default. If you'd rather use PostgreSQL, do this; everything works without it.

```bash
pip install -r requirements-dev.txt
docker compose up -d db
export DATABASE_URL=postgresql+psycopg2://digikey:digikey@localhost:5432/digikey
```

The Windows `.exe` builds with the line below. PyInstaller isn't in the requirements, so install it yourself.

```powershell
python scripts\check_windows_runtime.py
powershell -ExecutionPolicy Bypass -File scripts\build_windows_exe.ps1
```

## Rough edges

It's a personal project and a prototype. 274 of 276 tests pass (Windows, Python 3.10). The 2 failures are hygiene tests that expect a `.gitignore` and a CI workflow, which the repo doesn't have yet. Without a `.gitignore`, be careful not to commit a key file you put in `config/api_keys/`.

The chat modes that feed part results or a datasheet into the conversation exist in the service and tests but aren't wired into the UI yet, so every mode currently behaves like plain chat. The RAG tokenizer also only looks at letters and digits, so Korean-only questions don't find much.

I didn't re-check live DigiKey search while writing this, and if DigiKey changes its page structure the parsing rules will need fixing. Next I'd like to hook the chat context into the UI and add more suppliers like Mouser and LCSC.

---

<p align="center"><sub>LSY.KOR · <a href="https://github.com/lsy041015">More projects</a></sub></p>
