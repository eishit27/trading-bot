#!/usr/bin/env bash
# ==============================================================================
# Linux Native Launcher: "THE BEAST" Integrated System
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python3"

echo "🦁 Launching 'THE BEAST' Arbitrage Engine..."
exec "$PYTHON_BIN" "$SCRIPT_DIR/mev_arbitrage_engine/the_beast_engine.py" "$@"
