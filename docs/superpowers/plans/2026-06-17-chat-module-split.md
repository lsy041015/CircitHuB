# Chat Module Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `_circuitkit_chat_design.py` (2266 lines) into focused modules and remove the orphaned `_chat_dialog.py` legacy file.

**Architecture:** Extract static data, display widgets, and composer into separate files; `CircuitKitChatWindow` stays in `_circuitkit_chat_design.py` (~1200 lines after split). All class imports that tests rely on are updated at their new locations.

**Tech Stack:** Python 3.11+, PySide6, pytest (offscreen)

---

## File Map

| File | Action | Lines after | Responsibility |
|------|--------|-------------|----------------|
| `digikey_scraper/_chat_data.py` | Create | ~75 | Static data: AVATAR_COLORS, CHANNELS, DMS, MESSAGES, SHARE_PARTS, PRESENCE_COLORS |
| `digikey_scraper/_chat_widgets.py` | Create | ~580 | AvatarLabel, PartEmbed, MessageWidget, ChannelsColumn |
| `digikey_scraper/_chat_composer.py` | Create | ~375 | ComposerTextEdit, ComposerWidget |
| `digikey_scraper/_circuitkit_chat_design.py` | Modify | ~1200 | Imports from new modules + CircuitKitChatWindow + GLOBAL_QSS |
| `digikey_scraper/_chat_dialog.py` | Delete | — | Orphaned LAN chat dialog (0 importers) |
| `digikey_scraper/_main_window.py` | Modify | — | Remove ChatMessageInput re-export |
| `tests/test_chat_side_panels.py` | Modify | — | Update ComposerWidget import path |

## Test command (use throughout)

```bash
PYTHONPATH=/home/wego/pj_ws QT_QPA_PLATFORM=offscreen /home/wego/pj_ws/.venv/bin/python \
  -m pytest -p no:cacheprovider --ignore=tests/test_category_presenter.py -q
```

---

### Task 1: Extract `_chat_data.py`

**Files:**
- Create: `digikey_scraper/_chat_data.py`
- Modify: `digikey_scraper/_circuitkit_chat_design.py`

- [ ] **Step 1: Create `digikey_scraper/_chat_data.py`**

Copy the data block verbatim from `_circuitkit_chat_design.py` lines 32–100 into the new file. The new file contains no imports — pure Python literals only.

```python
# digikey_scraper/_chat_data.py
AVATAR_COLORS = {
    'jw':  ('qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #3B68F1,stop:1 #1E3FAF)', '#3B68F1'),
    'sh':  ('qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #E11D48,stop:1 #BE123C)', '#E11D48'),
    'mk':  ('qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #10B981,stop:1 #047857)', '#10B981'),
    'yj':  ('qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #F59E0B,stop:1 #B45309)', '#F59E0B'),
    'bot': ('qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #6366F1,stop:1 #4338CA)', '#6366F1'),
    'hr':  ('qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0EA5E9,stop:1 #0369A1)', '#0EA5E9'),
}

CHANNELS = [
    {'id': 'general',    'name': 'general',        'topic': '팀 전체 공지 · 잡담',           'unread': 0},
    {'id': 'bom-review', 'name': 'bom-review',     'topic': 'BOM 검토 및 승인 요청',          'unread': 3},
    {'id': 'sourcing',   'name': 'parts-sourcing',  'topic': '부품 수급 · 대체품 · 단가 협의', 'unread': 0},
    {'id': 'design',     'name': 'design-review',   'topic': '회로 설계 리뷰',                 'unread': 12},
    {'id': 'random',     'name': 'random',          'topic': '',                               'unread': 0},
]

DMS = [
    {'id': 'dm-sh', 'name': '서현 (PCB)',    'initials': 'SH', 'color': 'sh', 'presence': 'online',  'unread': 1},
    {'id': 'dm-mk', 'name': '민결 (구매)',    'initials': 'MK', 'color': 'mk', 'presence': 'online',  'unread': 0},
    {'id': 'dm-yj', 'name': '윤재 (펌웨어)', 'initials': 'YJ', 'color': 'yj', 'presence': 'away',    'unread': 0},
    {'id': 'dm-hr', 'name': '하린 (QA)',      'initials': 'HR', 'color': 'hr', 'presence': 'offline', 'unread': 0},
]

# Copy MESSAGES list verbatim from _circuitkit_chat_design.py lines 56–83
MESSAGES = [
    # ... (copy exact from source file)
]

# Copy SHARE_PARTS list verbatim from _circuitkit_chat_design.py lines 85–98
SHARE_PARTS = [
    # ... (copy exact from source file)
]

PRESENCE_COLORS = {'online': '#10B981', 'away': '#F59E0B', 'offline': '#CBD5E1'}
```

> **Note:** MESSAGES and SHARE_PARTS are long literal lists. Copy them character-for-character from `_circuitkit_chat_design.py` lines 56–83 and 85–98.

- [ ] **Step 2: Replace the data block in `_circuitkit_chat_design.py`**

Delete lines 32–100 from `_circuitkit_chat_design.py` (everything from `# ─── 데이터` comment through `PRESENCE_COLORS = {...}`) and replace with:

```python
from ._chat_data import (
    AVATAR_COLORS, CHANNELS, DMS, MESSAGES, SHARE_PARTS, PRESENCE_COLORS,
)
```

This one import replaces ~70 lines. The line count of `_circuitkit_chat_design.py` should drop from 2266 to ~2197.

- [ ] **Step 3: Run tests — expect all pass**

```bash
PYTHONPATH=/home/wego/pj_ws QT_QPA_PLATFORM=offscreen /home/wego/pj_ws/.venv/bin/python \
  -m pytest -p no:cacheprovider --ignore=tests/test_category_presenter.py -q
```

- [ ] **Step 4: Commit**

```bash
git add digikey_scraper/_chat_data.py digikey_scraper/_circuitkit_chat_design.py
git commit -m "refactor(chat): extract static data constants to _chat_data.py"
```

---

### Task 2: Extract `_chat_widgets.py`

**Files:**
- Create: `digikey_scraper/_chat_widgets.py`
- Modify: `digikey_scraper/_circuitkit_chat_design.py`

Moves 4 widget classes: `AvatarLabel` (lines ~106–115), `PartEmbed` (~121–260), `MessageWidget` (~265–461), `ChannelsColumn` (~844–1094 in current file; line numbers shift slightly after Task 1).

- [ ] **Step 1: Create `digikey_scraper/_chat_widgets.py` with imports**

```python
from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt, Signal, QPoint, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from ._chat_data import AVATAR_COLORS, PRESENCE_COLORS
```

Then copy the full class bodies of `AvatarLabel`, `PartEmbed`, `MessageWidget`, and `ChannelsColumn` verbatim from `_circuitkit_chat_design.py` into this file, in that order. Do not modify any class internals.

- [ ] **Step 2: Update `_circuitkit_chat_design.py`**

Remove the 4 class definitions from `_circuitkit_chat_design.py` and add this import line after the existing `from ._chat_data import ...` line:

```python
from ._chat_widgets import AvatarLabel, PartEmbed, MessageWidget, ChannelsColumn
```

The file should now lose ~580 lines (4 class definitions removed). Verify the CircuitKitChatWindow body still compiles — it instantiates all 4 classes, which are now imported.

- [ ] **Step 3: Run tests — expect all pass**

```bash
PYTHONPATH=/home/wego/pj_ws QT_QPA_PLATFORM=offscreen /home/wego/pj_ws/.venv/bin/python \
  -m pytest -p no:cacheprovider --ignore=tests/test_category_presenter.py -q
```

- [ ] **Step 4: Commit**

```bash
git add digikey_scraper/_chat_widgets.py digikey_scraper/_circuitkit_chat_design.py
git commit -m "refactor(chat): extract AvatarLabel/PartEmbed/MessageWidget/ChannelsColumn to _chat_widgets.py"
```

---

### Task 3: Extract `_chat_composer.py`

**Files:**
- Create: `digikey_scraper/_chat_composer.py`
- Modify: `digikey_scraper/_circuitkit_chat_design.py`
- Modify: `tests/test_chat_side_panels.py:139`

Moves `ComposerTextEdit` (~line 830, 9 lines) and `ComposerWidget` (~lines 467–827, 361 lines).

`ComposerWidget` uses `SHARE_PARTS` (from `_chat_data`) and `QInputDialog`, `QFileDialog`, `Path`.

- [ ] **Step 1: Create `digikey_scraper/_chat_composer.py` with imports**

```python
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QPoint, QUrl
from PySide6.QtGui import QDesktopServices, QKeyEvent
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel,
    QMenu, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from ._chat_data import SHARE_PARTS
```

Then copy `ComposerWidget` and `ComposerTextEdit` class bodies verbatim from `_circuitkit_chat_design.py` into this file. `ComposerTextEdit` must appear before `ComposerWidget` (it's referenced in `ComposerWidget._build`).

Order in new file:
1. `ComposerTextEdit` class
2. `ComposerWidget` class

- [ ] **Step 2: Update `_circuitkit_chat_design.py`**

Remove `ComposerWidget` and `ComposerTextEdit` class definitions and add:

```python
from ._chat_composer import ComposerWidget, ComposerTextEdit
```

- [ ] **Step 3: Update test import in `tests/test_chat_side_panels.py` line 139**

```python
# Before:
from digikey_scraper._circuitkit_chat_design import ComposerWidget

# After:
from digikey_scraper._chat_composer import ComposerWidget
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
PYTHONPATH=/home/wego/pj_ws QT_QPA_PLATFORM=offscreen /home/wego/pj_ws/.venv/bin/python \
  -m pytest -p no:cacheprovider --ignore=tests/test_category_presenter.py -q
```

- [ ] **Step 5: Commit**

```bash
git add digikey_scraper/_chat_composer.py digikey_scraper/_circuitkit_chat_design.py \
        tests/test_chat_side_panels.py
git commit -m "refactor(chat): extract ComposerWidget/ComposerTextEdit to _chat_composer.py"
```

---

### Task 4: Remove legacy `_chat_dialog.py`

**Files:**
- Delete: `digikey_scraper/_chat_dialog.py`
- Modify: `digikey_scraper/_main_window.py`

`_chat_dialog.py` has 0 importers outside `_main_window.py`. `_main_window.py` only re-exports `ChatMessageInput` from it for backward compatibility. Verify nothing uses it, then delete.

- [ ] **Step 1: Confirm `ChatMessageInput` has no external users**

```bash
grep -r "ChatMessageInput" /home/wego/pj_ws --include="*.py" \
  | grep -v "_chat_dialog.py" | grep -v "_main_window.py"
```

Expected: **no output**. If any output appears, stop and report — do not proceed.

- [ ] **Step 2: Remove re-export from `_main_window.py`**

Remove this line (line 17):
```python
from ._chat_dialog import ChatMessageInput  # re-exported for compatibility
```

Remove `ChatMessageInput` from `__all__` (line 45):
```python
# Before:
__all__ = ["MainWindow", "ChatDialog", "ChatMessageInput", "main"]

# After:
__all__ = ["MainWindow", "ChatDialog", "main"]
```

- [ ] **Step 3: Delete `_chat_dialog.py`**

```bash
rm /home/wego/pj_ws/digikey_scraper/_chat_dialog.py
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
PYTHONPATH=/home/wego/pj_ws QT_QPA_PLATFORM=offscreen /home/wego/pj_ws/.venv/bin/python \
  -m pytest -p no:cacheprovider --ignore=tests/test_category_presenter.py -q
```

- [ ] **Step 5: Commit**

```bash
git add digikey_scraper/_main_window.py
git rm digikey_scraper/_chat_dialog.py
git commit -m "refactor(chat): remove orphaned legacy _chat_dialog.py"
```

---

## Final verification

After all 4 tasks, confirm:

```bash
wc -l /home/wego/pj_ws/digikey_scraper/_circuitkit_chat_design.py
# Expected: ~1200 (down from 2266)

wc -l /home/wego/pj_ws/digikey_scraper/_chat_widgets.py
# Expected: ~580

wc -l /home/wego/pj_ws/digikey_scraper/_chat_composer.py
# Expected: ~375

ls /home/wego/pj_ws/digikey_scraper/_chat_dialog.py
# Expected: No such file

PYTHONPATH=/home/wego/pj_ws QT_QPA_PLATFORM=offscreen /home/wego/pj_ws/.venv/bin/python \
  -m pytest -p no:cacheprovider --ignore=tests/test_category_presenter.py -q
# Expected: all tests pass
```
