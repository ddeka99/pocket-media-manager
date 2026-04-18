#!/usr/bin/env bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_venv_python

port="${1:-8765}"
ip_address="$(active_ipv4)"
[[ -n "${ip_address}" ]] || die "Could not determine an active IPv4 address."

base_url="http://${ip_address}:${port}"
health_json="$(curl -fsS "${base_url}/health")"
token="$(get_token "${base_url}")"

BASE_URL="${base_url}" TOKEN="${token}" HEALTH_JSON="${health_json}" "${VENV_PYTHON}" - <<'PY'
import json
import os

health = json.loads(os.environ["HEALTH_JSON"])
base_url = os.environ["BASE_URL"]
token = os.environ["TOKEN"]

print()
print("Pocket Media Manager LAN Check")
print(f"Wi-Fi URL: {base_url}")
print(f"Token: {token}")
print(f"Media root configured: {health.get('media_root_configured')}")
print(f"Indexed items: {health.get('library_count')}")
print()
print("Next MacBook/iPhone input:")
print(f" - Helper URL: {base_url}")
print(f" - Pairing token: {token}")
print()
print("If the iPhone cannot reach this URL on home Wi-Fi, allow Python/Uvicorn through Windows Firewall.")
PY
