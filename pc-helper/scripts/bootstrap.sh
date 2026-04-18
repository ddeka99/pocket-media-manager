#!/usr/bin/env bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

python_path="$(find_real_python || true)"
[[ -n "${python_path}" ]] || die "Could not find a real Python interpreter for Git Bash."

echo "Using Python at $(cygpath -w "${python_path}")"

"${python_path}" -m venv "${VENV_DIR_WIN}"
"${VENV_PYTHON}" -m pip install --upgrade pip
"${VENV_PYTHON}" -m pip install -r "$(cygpath -w "${PROJECT_DIR}/requirements.txt")"

echo
echo "Bootstrap complete."
echo "Run bash ./scripts/run-dev.sh from pc-helper to start the API."
