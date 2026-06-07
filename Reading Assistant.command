#!/bin/bash
# Reading Assistant — double-click launcher for macOS
# If opened from Finder, macOS Terminal will open, run this script, then close.

set -euo pipefail

# Resolve the project root (where this script lives)
cd "$(dirname "$0")"
ROOT="$(pwd)"

# Prefer the bundled virtual environment if it exists
if [ -f "$ROOT/.venv/bin/activate" ]; then
  source "$ROOT/.venv/bin/activate"
elif [ -f "$ROOT/venv/bin/activate" ]; then
  source "$ROOT/venv/bin/activate"
fi

PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" &>/dev/null; then
    PYTHON="$candidate"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  echo "Error: Python 3 is not installed."
  echo "Install it from https://www.python.org/downloads/ and try again."
  read -r -p "Press Return to close this window."
  exit 1
fi

# Verify gui.py exists
if [ ! -f "$ROOT/gui.py" ]; then
  echo "Error: gui.py not found in $ROOT"
  read -r -p "Press Return to close this window."
  exit 1
fi

# Install dependencies if missing (quiet check)
if "$PYTHON" -c "import PySide6" 2>/dev/null; then
  :
else
  echo "Installing dependencies (one-time setup)..."
  if [ -f "$ROOT/requirements.txt" ]; then
    "$PYTHON" -m pip install -q -r "$ROOT/requirements.txt" 2>&1 || {
      echo "Warning: pip install failed. The app may not work correctly."
    }
  fi
fi

# Launch the GUI
exec "$PYTHON" "$ROOT/gui.py"
