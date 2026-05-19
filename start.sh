#!/usr/bin/env bash
# Lance Jarvis + Vibe Island UI en parallèle. Ctrl+C arrête tout proprement.

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
UI_BIN="$ROOT/ui/.build/release/JarvisUI"
VENV_PY="$ROOT/.venv/bin/python3"

# Build le binaire Swift s'il manque
if [ ! -x "$UI_BIN" ]; then
    echo "[start] build UI Swift…"
    (cd "$ROOT/ui" && swift build -c release)
fi

# Nettoie toute instance UI précédente
pkill -f "/JarvisUI$" 2>/dev/null || true
rm -f /tmp/jarvis-ui.sock /tmp/jarvis-ui-events.sock 2>/dev/null || true
sleep 0.2

# Lance l'UI en background
echo "[start] Vibe Island UI…"
JARVIS_UI=1 "$UI_BIN" &
UI_PID=$!

# Trap : à la sortie (Ctrl+C, exit Python, erreur), tue l'UI une seule fois
_cleaned=0
cleanup() {
    [ "$_cleaned" = "1" ] && return
    _cleaned=1
    echo ""
    echo "[start] arrêt UI (pid=$UI_PID)…"
    kill "$UI_PID" 2>/dev/null || true
    wait "$UI_PID" 2>/dev/null || true
    rm -f /tmp/jarvis-ui.sock /tmp/jarvis-ui-events.sock 2>/dev/null || true
    echo "[start] done."
}
trap cleanup EXIT

# Lance Jarvis Python en foreground (Ctrl+C va directement à lui → shutdown propre)
echo "[start] Jarvis (main.py)…"
cd "$ROOT"
JARVIS_UI=1 "$VENV_PY" main.py
