#!/usr/bin/env bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

host="${1:-0.0.0.0}"
port="${2:-8765}"

require_venv_python

cd "${PROJECT_DIR}"
"${VENV_PYTHON}" -m uvicorn app.main:app --reload --host "${host}" --port "${port}"
