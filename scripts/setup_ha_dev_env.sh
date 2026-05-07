#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/opt/homebrew/bin/python3.14}"
VENV_DIR="${VENV_DIR:-$HOME/.venvs/haclaw-ha}"
HA_CONFIG_DIR="${HA_CONFIG_DIR:-$HOME/.ha-dev/haclaw}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python not found: $PYTHON_BIN" >&2
  echo "Install Home Assistant supported Python, for example: brew install python@3.14" >&2
  exit 1
fi

mkdir -p "$HA_CONFIG_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/requirements-dev.txt"

if [[ "${RESET_HA_CONFIG:-0}" == "1" || ! -f "$HA_CONFIG_DIR/configuration.yaml" ]]; then
  cp "$ROOT_DIR/dev/ha-config/configuration.yaml" "$HA_CONFIG_DIR/configuration.yaml"
fi

ln -sfn "$ROOT_DIR/custom_components" "$HA_CONFIG_DIR/custom_components"

echo "HAclaw dev environment ready:"
echo "  venv: $VENV_DIR"
echo "  HA config: $HA_CONFIG_DIR"
echo "Run tests:"
echo "  scripts/run_tests.sh"
echo "Run Home Assistant config check:"
echo "  $VENV_DIR/bin/hass --script check_config -c $HA_CONFIG_DIR"
echo "Start Home Assistant:"
echo "  scripts/run_hass_dev.sh"
