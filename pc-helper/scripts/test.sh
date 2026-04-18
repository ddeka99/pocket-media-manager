#!/usr/bin/env bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_venv_python

cd "${PROJECT_DIR}"
"${VENV_PYTHON}" -m pytest
