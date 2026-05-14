#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

find_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    printf '%s\n' "$PYTHON"
    return 0
  fi

  local candidate
  for name in python python3 py; do
    while IFS= read -r candidate; do
      [[ -z "$candidate" ]] && continue
      [[ "$candidate" == *"/WindowsApps/"* ]] && continue
      if "$candidate" --version >/dev/null 2>&1; then
        printf '%s\n' "$candidate"
        return 0
      fi
    done < <(which -a "$name" 2>/dev/null || true)
  done

  return 1
}

if ! PYTHON_BIN="$(find_python)"; then
  echo "Python was not found. Install Python 3.11+ and make sure a real python is available in Git Bash." >&2
  echo "You can also run: PYTHON=/path/to/python ./scripts/bootstrap.sh" >&2
  exit 1
fi

"$PYTHON_BIN" -m venv .venv
./.venv/Scripts/python.exe -m pip install --upgrade pip
./.venv/Scripts/python.exe -m pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Update PUBLIC_BASE_URL with this PC's LAN IP before phone testing."
fi
