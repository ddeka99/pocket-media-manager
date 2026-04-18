#!/usr/bin/env bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_venv_python

base_url="${BASE_URL:-http://127.0.0.1:8765}"
rescan=0

if [[ "${1:-}" == "--rescan" ]]; then
  rescan=1
fi

token="$(get_token "${base_url}")"

if [[ "${rescan}" -eq 1 ]]; then
  echo "Rescanning library..."
  curl -fsS -X POST -H "Authorization: Bearer ${token}" "${base_url}/library/rescan" >/dev/null
fi

config_json="$(curl -fsS -H "Authorization: Bearer ${token}" "${base_url}/config")"
summary_json="$(curl -fsS -H "Authorization: Bearer ${token}" "${base_url}/library/summary")"

BASE_URL="${base_url}" CONFIG_JSON="${config_json}" SUMMARY_JSON="${summary_json}" "${VENV_PYTHON}" - <<'PY'
import json
import os

config = json.loads(os.environ["CONFIG_JSON"])
summary = json.loads(os.environ["SUMMARY_JSON"])

print()
print("Pocket Media Manager Helper")
print(f"Base URL: {os.environ.get('BASE_URL', 'http://127.0.0.1:8765')}")
print(f"Media root: {config.get('media_root')}")
print(f"Items indexed: {summary.get('total_items')}")
print(f"Direct-play items: {summary.get('direct_play_items')}")
print(f"Incompatible items: {summary.get('incompatible_items')}")

latest_scan = summary.get("latest_scan")
if latest_scan:
    print(f"Last scan: {latest_scan.get('completed_at')}")

folders = summary.get("top_folders") or []
if folders:
    print()
    print("Top folders:")
    for folder in folders:
        print(f" - {folder.get('folder')}: {folder.get('item_count')}")
PY
