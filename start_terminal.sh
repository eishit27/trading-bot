#!/usr/bin/env bash
# ==============================================================================
# Linux Native Launcher: Phoenix Quanta Live MEV War Room & Command Center
# Operating Mode: 100% Self-Funded Equity | Strict Zero-Debt
# ==============================================================================

set -e

# Resolve script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure venv Python is used
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python3"

if [ ! -f "$PYTHON_BIN" ]; then
    echo "❌ Error: Virtual environment Python not found at $PYTHON_BIN"
    exit 1
fi

# Check for --classic flag
if [[ "$*" == *"--classic"* ]]; then
    echo "📊 Initializing Classic Quantitative Command Center..."
    exec "$PYTHON_BIN" "$SCRIPT_DIR/mev_arbitrage_engine/terminal_command_center.py" "${@/--classic/}"
else
    echo "🔥 Initializing Phoenix Quanta High-Frequency MEV War Room..."
    exec "$PYTHON_BIN" "$SCRIPT_DIR/mev_arbitrage_engine/mev_war_room_fire.py" "$@"
fi
