#!/bin/bash
# Login OAuth pour le Claude Code isolé de Jarvis.
# Utilise ton abonnement Claude existant, sans toucher à ~/.claude/.

cd "$(dirname "$0")"
export CLAUDE_CONFIG_DIR="$(pwd)/.claude_home"
echo "→ CLAUDE_CONFIG_DIR=$CLAUDE_CONFIG_DIR"
echo "→ Lancement de claude /login..."
claude /login
