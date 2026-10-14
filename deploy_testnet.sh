#!/usr/bin/env bash
# ==============================================================================
# Linux Launcher: Base Sepolia Testnet Contract Deployment
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python3"

echo "🔨 Checking / Compiling Contracts with Solc 0.8.25 (Cancun EVM)..."
"$PYTHON_BIN" "$SCRIPT_DIR/mev_arbitrage_engine/compile_contracts.py"

echo ""
echo "🚀 Initiating Base Sepolia Deployment..."
exec "$PYTHON_BIN" "$SCRIPT_DIR/mev_arbitrage_engine/deploy_base_sepolia.py" "$@"
