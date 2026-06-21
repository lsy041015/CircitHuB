# DigiKey Price Scraper

PySide6 desktop app for searching DigiKey parts, extracting price/spec data, saving results, and sharing result text over a local socket.

## Features

- Search one or more part numbers from a Qt GUI.
- Extract product title, DigiKey part number, price breaks, and key specs.
- Display results as cards or formatted text.
- Save result text automatically when enabled.
- Share formatted specs to another running instance over TCP.
- LAN group chat for quick collaboration.
- Minimal datasheet PDF viewer with manual box selection, text/OCR extraction, and Gemini-assisted translate/summarize.
- Gemini 2.5 Flash is the default AI model for datasheet region actions.
- Supports Korean and English UI text.

## Requirements

- Python 3.10 or newer.
- Google Chrome installed.
- ChromeDriver compatible with the installed Chrome version, or Selenium Manager support available in the local Selenium install.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run

```bash
python digikey_price_scraper.py
```

Alternative module entry:

```bash
python -m digikey_scraper.qt_gui
```

## Test

```bash
source .venv/bin/activate
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 QT_QPA_PLATFORM=offscreen python -m pytest -q
```

Category smoke shortcut:

```bash
./scripts/test_category_safe.sh
```

## Gemini API Keys

Gemini features read keys in this order:

1. `GEMINI_API_KEYS` or `GEMINI_API_KEY`
2. `GEMMA_API_KEYS` or `GEMMA_API_KEY` for legacy compatibility
3. `config/api_keys/gemini_api_keys.txt`
4. `config/api_keys/gemma_api_keys.txt` for legacy compatibility
5. `config/settings.env`

Create `config/api_keys/gemini_api_keys.txt` and place one key per line. Key files are ignored by git.

## Runtime Files

The app writes local runtime data under `DIGIKEY_SCRAPER_DATA_DIR` when set, otherwise under the user's data directory:

- `app_settings.json`: user settings.
- `auto_saved_results/`: auto-saved search results.
- `shared_specs/`: received/shared spec text.
- `.gemma_cache/`: cached Gemini responses.

These files are ignored by git because they are local user data.

## Development Notes

- Core scraping logic lives in `digikey_scraper/scraper.py`.
- GUI composition and state live mostly in `digikey_scraper/_main_window.py`.
- Result formatting lives in `digikey_scraper/formatters.py`.
- Socket sharing lives in `digikey_scraper/sharing.py`.
- LAN group chat lives in `digikey_scraper/chat.py`.
- Minimal datasheet/Gemini workflows live in `digikey_scraper/datasheet_viewer.py`.
- Gemini API key loading, retry, and prompt code lives in `digikey_scraper/gemma_client.py`.
- Existing tests cover parser, formatter, and sharing behavior in `tests/test_scraper_and_sharing.py`.
