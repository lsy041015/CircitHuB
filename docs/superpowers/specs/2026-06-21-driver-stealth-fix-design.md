# Driver Stealth Fix — Design Spec

**Date:** 2026-06-21  
**Status:** Approved

## Problem

DigiKey blocks scraping with "해당 페이지에서 자동화를 차단" error.  
Two root causes in `digikey_scraper/driver.py`:

1. Bot-signal Chrome flags leak automation identity to Cloudflare
2. `_apply_profile_options(opts, None, profile_directory)` — passes `None` for `user_data_dir`, so `--profile-directory` added via opts without corresponding `--user-data-dir` may cause profile not loading with uc.

## Scope

Single file: `digikey_scraper/driver.py`

## Changes

### 1. Remove bot-signal flags (uc + selenium fallback both)

| Flag / Pref | Reason to remove |
|---|---|
| `--disable-extensions` | Known bot signal |
| `--disable-background-networking` | Known bot signal |
| `--disable-gpu` | Suspicious in non-headless mode |
| `prefs: images: 2` | Bot signal (sites expect images loaded) |
| `prefs: credentials_enable_service: False` | Bot signal |
| `prefs: password_manager_enabled: False` | Bot signal |

Keep: `--no-sandbox`, `--disable-dev-shm-usage`, `--window-size`, `--lang=en-US`, `--no-first-run`, `--no-default-browser-check`

### 2. Fix uc profile argument (line 154)

**Before:**
```python
_apply_profile_options(opts, None, profile_directory)
```

**After:**
```python
if profile_directory:
    opts.add_argument(f"--profile-directory={profile_directory}")
```

`user_data_dir` is already passed to `uc.Chrome(user_data_dir=...)` constructor — do not duplicate via opts.

## Non-changes

- No changes to scraper.py, selenium_supplier.py, or any other file
- No new dependencies
- Selenium fallback: keep `--disable-blink-features=AutomationControlled`, `excludeSwitches`, `useAutomationExtension`
- Selenium fallback: remove same bot-signal flags/prefs listed above
