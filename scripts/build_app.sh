#!/bin/bash
# Build a standalone macOS .app bundle for Reading Assistant using PyInstaller.
#
# Usage:
#   ./scripts/build_app.sh
#
# The finished bundle is written to:
#   build/dist/Reading Assistant.app
#
# A copy is also placed in the project root for convenience.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# --- Colour helpers ---
green() { printf '\033[32m%s\033[0m\n' "$*"; }
bold()  { printf '\033[1m%s\033[0m\n' "$*"; }

echo ""
bold "═══ Reading Assistant — macOS .app Builder ═══"
echo ""

# ---------- 1. Python / venv ----------
if [ -f "$ROOT/.venv/bin/activate" ]; then
  bold "• Activating .venv …"
  source "$ROOT/.venv/bin/activate"
elif [ -f "$ROOT/venv/bin/activate" ]; then
  bold "• Activating venv …"
  source "$ROOT/venv/bin/activate"
fi

PYTHON="$(command -v python3 || command -v python)"
if [ -z "$PYTHON" ]; then
  echo "Error: Python 3 is not installed." >&2
  exit 1
fi

# ---------- 2. Install build deps ----------
bold "• Ensuring PyInstaller is available …"
"$PYTHON" -m pip install -q --upgrade pip
"$PYTHON" -m pip install -q pyinstaller 2>&1 | tail -1

# ---------- 3. Generate app icon ----------
bold "• Generating app icon …"
if [ ! -f "$ROOT/build/AppIcon.icns" ]; then
  "$PYTHON" "$ROOT/scripts/generate_icon.py"
else
  echo "  AppIcon.icns already exists — skipping generation."
fi

# ---------- 4. Clean previous build ----------
bold "• Cleaning previous build artefacts …"
rm -rf "$ROOT/build/pyinstaller-work" "$ROOT/dist"

# ---------- 5. Run PyInstaller ----------
bold "• Running PyInstaller …"
"$PYTHON" -m PyInstaller \
  --clean \
  --noconfirm \
  --distpath "$ROOT/dist" \
  --workpath "$ROOT/build/pyinstaller-work" \
  "$ROOT/Reading Assistant.spec" 2>&1

# ---------- 6. Sign the app (ad-hoc for local use) ----------
APP_BUNDLE="$ROOT/dist/Reading Assistant.app"
if [ -d "$APP_BUNDLE" ]; then
  bold "• Signing bundle (ad-hoc) …"
  codesign --deep --force --sign - "$APP_BUNDLE" 2>&1 || true
fi

# ---------- 7. Copy to project root for convenience ----------
DEST="$ROOT/Reading Assistant.app"
bold "• Copying bundle to project root …"
rm -rf "$DEST"
cp -R "$APP_BUNDLE" "$DEST"

# ---------- 8. Verify ----------
echo ""
green "✔ Done!"
echo ""
echo "  App bundle:      $APP_BUNDLE"
echo "  Project root:    $DEST"
if [ -d "$APP_BUNDLE" ]; then
  SIZE="$(du -sh "$APP_BUNDLE" | cut -f1)"
  echo "  Bundle size:     $SIZE"
fi
echo ""
bold "Double-click Reading Assistant.app in Finder to launch."
echo ""
