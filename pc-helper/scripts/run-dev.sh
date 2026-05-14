#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -x ./.venv/Scripts/python.exe ]]; then
  echo "Virtual environment not found. Run ./scripts/bootstrap.sh first." >&2
  exit 1
fi

./.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8787 --reload
