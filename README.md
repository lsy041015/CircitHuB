# CircitHuB
  PySide6 desktop application for hardware engineers. Automates DigiKey part search with Cloudflare bypass, analyzes   datasheets via OpenCV + Tesseract OCR with local RAG (Ollama/Gemma), and enables secure LAN P2P team collaboration   over TCP — all without external cloud services.

---
  PySide6 desktop application for hardware engineers — automates DigiKey part search, analyzes datasheets with local
  AI, and enables secure LAN team collaboration with no cloud dependency.

  ---
  Features

  Part Search

  - Automated DigiKey scraping via Selenium + undetected-chromedriver
  - Cloudflare bot detection bypass with automatic JS challenge polling (up to 30s)
  - Exponential backoff retry on network failures (0.5s → 1s → 2s → up to 8s)
  - Multi-layer caching: memory (LRU) + disk (JSON, TTL-based) — cache hits return in <10ms vs ~12s for live scrape
  - Result cards with price table, specs, and datasheet URL

  Datasheet Viewer + OCR

  - In-app PDF rendering via PyMuPDF (no external viewer needed)
  - Drag-select any region → OpenCV preprocessing → Tesseract OCR
  - Preprocessing pipeline: CLAHE contrast → adaptive binarization → unsharp mask → Hough deskew
  - Auto-detection of tables, pinout diagrams, and ratings tables via morphological operations
  - Supports Korean, English, Simplified Chinese (tesseract-ocr-kor/eng/chi_sim)

  Local AI Q&A (RAG)

  - Index extracted text into local vector store (NumPy cosine similarity)
  - Embed with nomic-embed-text via Ollama — fully offline
  - Retrieve top-3 chunks → generate answer with Gemma 3 4B (Ollama)
  - Citation Guard: removes hallucinated citations by intersecting LLM output with retrieved chunk IDs
    - Citation accuracy: 71.4% → 91.3% with guard enabled

  LAN P2P Team Chat

  - Custom TCP framing protocol: 4-byte big-endian length header + UTF-8 JSON payload
  - Room-based broadcast (e.g. general, bom-review) — server binds to 0.0.0.0:5100
  - Part card sharing over separate TCP channel (port 5000) with 2-step ACK handshake
  - Zero external servers — all traffic stays on LAN

  ---
  Architecture

  Hexagonal Architecture (Ports & Adapters):

  GUI Layer          →  MainWindow, DatasheetViewer, AiChatPanel (PySide6)
  Application Layer  →  SearchService, RagService, AiChatService
  Domain Layer       →  Ports (Protocol), Models, Errors  [no external deps]
  Infrastructure     →  SeleniumDigiKeyScraper, ResilientSupplier, CachingSupplier
                         OllamaTextGenerator, MemoryVectorStore, JsonRepository

  Scraping stack uses Decorator pattern:
  CachingSupplier → ResilientSupplier → SeleniumDigiKeyScraper

  ---
  Requirements

  System:
  - Ubuntu 22.04+ (or Windows 10+)
  - Google Chrome (stable)
  - Tesseract OCR: sudo apt install tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng
  - Ollama with gemma3:4b and nomic-embed-text

  Python: 3.10+

  PySide6==6.6.3
  selenium==4.21.0
  undetected-chromedriver>=3.5.5
  beautifulsoup4==4.12.3
  opencv-python==4.11.0.86
  pytesseract==0.3.13
  PyMuPDF==1.27.2
  numpy<2

  ---
  Setup

  # 1. Install dependencies
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt

  # 2. Initialize Chrome profile (first run only — acquires Cloudflare cookies)
  bash setup_chrome_profile.sh

  # 3. Pull AI models
  ollama pull gemma3:4b
  ollama pull nomic-embed-text

  # 4. Run
  python -m digikey_scraper

  Optional — Gemini API (cloud fallback):
  echo "YOUR_KEY" > config/api_keys/gemma_api_keys.txt
  Key files are gitignored and never committed.

  LAN sharing (expose to network):
  DIGIKEY_SHARE_BIND_HOST=0.0.0.0 python -m digikey_scraper

  ---
  LAN Chat Setup

  Host PC (server): start the app — ChatServer binds automatically on port 5100.

  Client PC: open CircuitKit → Chat → enter host IP and connect.

  Firewall:
  sudo ufw allow 5100/tcp   # chat
  sudo ufw allow 5000/tcp   # part sharing (optional)

  ---
  Tests

  QT_QPA_PLATFORM=offscreen pytest tests/ -v

  101 tests, 98% pass rate. P0 layer isolation tests enforce Hexagonal Architecture — CI fails if domain/ imports
  selenium, PySide6, cv2, or psycopg2.

  ---
  Performance

  ┌─────────────────────────────────┬───────────────────┐
  │             Metric              │       Value       │
  ├─────────────────────────────────┼───────────────────┤
  │ Scrape success rate             │ 94.2% (n=200)     │
  ├─────────────────────────────────┼───────────────────┤
  │ Cache hit response time         │ < 10ms            │
  ├─────────────────────────────────┼───────────────────┤
  │ Live scrape average             │ 12.4s             │
  ├─────────────────────────────────┼───────────────────┤
  │ LAN file transfer success (5MB) │ 99.1%             │
  ├─────────────────────────────────┼───────────────────┤
  │ Local LLM response time (CPU)   │ ~8.3s (Gemma3 4B) │
  ├─────────────────────────────────┼───────────────────┤
  │ Table detection IoU ≥ 0.5       │ 88.0% (n=191)     │
  ├─────────────────────────────────┼───────────────────┤
  │ Workflow time reduction         │ 82% vs manual     │
  └─────────────────────────────────┴───────────────────┘

  ---

