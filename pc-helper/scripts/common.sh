#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${PROJECT_DIR}/.venv"
VENV_DIR_WIN="$(cygpath -w "${VENV_DIR}")"
VENV_PYTHON="${VENV_DIR}/Scripts/python.exe"

die() {
  echo "$1" >&2
  exit 1
}

find_real_python() {
  local user_name="${USERNAME:-${USER:-}}"
  local candidates=()

  if [[ -n "${user_name}" ]]; then
    candidates+=("/c/Users/${user_name}/AppData/Local/Python/bin/python.exe")
    candidates+=("/c/Users/${user_name}/AppData/Local/Programs/Python/Python"*/python.exe)
  fi

  candidates+=("/c/Program Files/Python"*/python.exe)

  for candidate in "${candidates[@]}"; do
    if [[ -f "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done

  return 1
}

require_venv_python() {
  [[ -f "${VENV_PYTHON}" ]] || die "Virtual environment not found. Run ./scripts/bootstrap.sh first."
}

get_token() {
  local base_url="$1"
  curl -fsS "${base_url}/pairing" | "${VENV_PYTHON}" -c "import json,sys; print(json.load(sys.stdin)['api_token'])"
}

active_ipv4() {
  "${VENV_PYTHON}" - <<'PY'
import re
import subprocess
import sys

output = subprocess.check_output(["ipconfig"], text=True, encoding="utf-8", errors="replace")
blocks = re.split(r"\r?\n\r?\n", output)
for block in blocks:
    if "Media disconnected" in block:
        continue
    if "Default Gateway" not in block:
        continue
    match = re.search(r"IPv4 Address[^\n]*:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", block)
    if match:
        print(match.group(1))
        sys.exit(0)
sys.exit(1)
PY
}
