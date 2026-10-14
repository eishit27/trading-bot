#!/usr/bin/env bash
# ==============================================================================
# Linux Direct Launcher: Phoenix Quanta Live MEV War Room
# Operating Mode: 100% Self-Funded Equity | Strict Zero-Debt
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python3"

exec "$PYTHON_BIN" "$SCRIPT_DIR/mev_arbitrage_engine/mev_war_room_fire.py" "$@"
