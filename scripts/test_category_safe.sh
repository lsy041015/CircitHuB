#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
QT_QPA_PLATFORM=offscreen \
"$ROOT_DIR/.venv/bin/python" -m pytest tests/test_category_search.py -q
