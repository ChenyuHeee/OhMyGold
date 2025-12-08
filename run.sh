#!/usr/bin/env bash
set -euo pipefail

# One-click launcher for the GUI.
# - Auto-loads .env if present
# - Prefers local virtualenv (.venv) if available
# - Falls back to system python3

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/.env"

# Default to system python (更稳定的 macOS + PySide6 组合)。如需强制用虚拟环境，设置 USE_VENV=1。
if [[ "${USE_VENV:-}" == "1" ]]; then
  if [[ -x "$ROOT_DIR/.venv312/bin/python3" ]]; then
    PYTHON_BIN="$ROOT_DIR/.venv312/bin/python3"
  elif [[ -x "$ROOT_DIR/.venv/bin/python3" ]]; then
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python3"
  else
    PYTHON_BIN=python3
  fi
else
  PYTHON_BIN=python3
fi

if [[ -f "$ENV_FILE" ]]; then
  echo "Loading environment from .env"
  set -a
  source "$ENV_FILE"
  set +a
else
  echo "No .env found; continuing without extra environment variables"
fi

# Select Qt platform dynamically:
# - macOS + 本机（无 SSH）默认使用 cocoa 以弹窗
# - SSH 或无显示则退回 offscreen
# - 手动设置 QT_QPA_PLATFORM 时不覆盖
if [[ -z "${QT_QPA_PLATFORM:-}" ]]; then
  if [[ "$(uname)" == "Darwin" ]]; then
    if [[ -n "${SSH_TTY:-}" || -n "${SSH_CONNECTION:-}" ]]; then
      export QT_QPA_PLATFORM=offscreen
    else
      export QT_QPA_PLATFORM=cocoa
    fi
  else
    if [[ -z "${DISPLAY:-}" ]]; then
      export QT_QPA_PLATFORM=offscreen
    fi
  fi
fi
# Hint Qt on macOS to avoid certain compositor crashes
export QT_MAC_WANTS_LAYER=1
# Prefer software rendering to avoid GPU driver issues that can cause SIGBUS on macOS
if [[ -z "${QT_OPENGL:-}" ]]; then
  export QT_OPENGL=software
fi

cd "$ROOT_DIR"
exec "$PYTHON_BIN" -m ohmygold.ui.gui
