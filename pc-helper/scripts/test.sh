#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -x ./.venv/Scripts/python.exe ]]; then
  echo "Virtual environment not found. Run ./scripts/bootstrap.sh first." >&2
  exit 1
fi

mkdir -p .tmp/pytest
TMPDIR="$ROOT/.tmp" TEMP="$ROOT/.tmp" TMP="$ROOT/.tmp" ./.venv/Scripts/python.exe -m pytest --basetemp="$ROOT/.tmp/pytest"
