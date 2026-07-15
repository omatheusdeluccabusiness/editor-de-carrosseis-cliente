#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi

if [[ -f "secrets/credentials.enc.json" ]]; then
  if [[ -f "${HOME}/.carrossel-editor-recovery-key" ]]; then
    "$PYTHON_BIN" scripts/credenciais.py restore --if-needed --non-interactive
  elif [[ -t 0 ]]; then
    "$PYTHON_BIN" scripts/credenciais.py restore --if-needed
  else
    "$PYTHON_BIN" scripts/credenciais.py restore --if-needed --non-interactive
  fi
fi

"$PYTHON_BIN" scripts/carrossel_service.py start
