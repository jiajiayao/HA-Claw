#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$HOME/.venvs/haclaw-ha}"
HA_CONFIG_DIR="${HA_CONFIG_DIR:-$HOME/.ha-dev/haclaw}"

if [[ ! -x "$VENV_DIR/bin/hass" ]]; then
  echo "Home Assistant is missing. Run scripts/setup_ha_dev_env.sh first." >&2
  exit 1
fi

mkdir -p "$HA_CONFIG_DIR"
ln -sfn "$ROOT_DIR/custom_components" "$HA_CONFIG_DIR/custom_components"

exec "$VENV_DIR/bin/hass" -c "$HA_CONFIG_DIR" --debug
