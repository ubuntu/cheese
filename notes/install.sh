#!/usr/bin/env bash
# Install Custom CLI (note-taking app) on Kali Linux / Debian-based systems
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[*] Installing Custom CLI..."
pip install "$DIR" --quiet

echo ""
echo "[✔] Custom CLI installed successfully!"
echo ""
echo "Commands available:"
echo "  notes new \"My title\"   — create a note"
echo "  notes list              — list all notes"
echo "  notes view <id>         — view a note"
echo "  notes search <query>    — search notes"
echo "  notes gui               — launch web GUI in browser"
echo "  notes --help            — full help"
