#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$HOME/.venvs/haclaw-ha/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Virtual environment is missing. Run scripts/setup_ha_dev_env.sh first." >&2
  exit 1
fi

cd "$ROOT_DIR"
"$PYTHON_BIN" -m pytest tests -q
"$PYTHON_BIN" -m compileall -q custom_components tests
"$PYTHON_BIN" -m json.tool custom_components/haclaw/manifest.json >/dev/null
"$PYTHON_BIN" -m json.tool custom_components/haclaw/strings.json >/dev/null
"$PYTHON_BIN" -m json.tool custom_components/haclaw/translations/en.json >/dev/null
"$PYTHON_BIN" -m json.tool custom_components/haclaw/translations/zh-Hans.json >/dev/null
