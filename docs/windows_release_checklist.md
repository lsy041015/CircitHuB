# Windows Release Checklist

Use this checklist on a clean Windows 10/11 machine before shipping a build.

## Development Install

1. Create and activate `.venv`.
2. Install `requirements.txt` and `requirements-dev.txt`.
3. Run `python scripts\check_windows_runtime.py`.
4. Run `python -m unittest discover -s tests`.

## Feature Verification

1. Launch `python digikey_price_scraper.py`.
2. Confirm the main window opens.
3. Search at least one known part, such as `LM358P`.
4. Confirm result cards render price/spec fields.
5. Save results to a text file.
6. Start receiver and verify localhost sharing.
7. Open a datasheet PDF.
8. Select a PDF region and confirm PDF text extraction.
9. If Tesseract is installed, confirm OCR extraction.
10. If a Gemini key is configured, confirm translate/summarize actions.
11. Restart the app and confirm settings persist under `%LOCALAPPDATA%\DigiKeyPriceScraper`.

## EXE Build

1. Run `powershell -ExecutionPolicy Bypass -File scripts\build_windows_exe.ps1`.
2. Confirm `dist\DigiKeyPriceScraper\DigiKeyPriceScraper.exe` exists.
3. Launch the executable.
4. Repeat the feature verification checklist.

## Known External Requirements

- Chrome is required for DigiKey search.
- Tesseract is required for OCR only.
- Gemini API key is required for AI translate/summarize only.
- Chrome, Tesseract, and Gemini keys are not bundled with the executable.
