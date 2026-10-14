#!/usr/bin/env bash
# ==============================================================================
# Linux Master Menu: Quantitative MEV Engine
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python3"

echo ""
echo "========================================================================"
echo "  🔥 LINUX QUANTITATIVE MEV ENGINE MASTER CONTROL 🔥"
echo "  Mode: 100% Self-Funded Equity | Zero-Debt | Deterministic Atomicity"
echo "========================================================================"
echo "  [1] 🔥 LAUNCH PHOENIX WAR ROOM (Live High-Frequency Animated TUI)"
echo "  [2] 🦁 RUN 'THE BEAST' (5-Pillar Zero-Bribe Integrated System)"
echo "  [3] 📊 Launch Classic Quant Terminal Command Center"
echo "  [4] 🌐 Run 'Holy Grail' Multi-Route Aggregation Suite"
echo "  [5] 🚀 Run Full Production Pipeline (RPC + AMMs + Signer + Relay)"
echo "  [6] 🧮 Run Stanford CFMM Convex Flow & Uniswap V3 CLAMM Math"
echo "  [7] 🛡️ Run Baseline Sizing & Revert Verification Scenarios"
echo "  [8] 🚀 Deploy Contracts to Base Sepolia Testnet"
echo "  [9] 🔑 Check Testnet Wallet Balance & Faucet Links"
echo "  [q] Exit"
echo "========================================================================"
read -p "Select an option [1-9]: " choice

case "$choice" in
    1)
        exec "$PYTHON_BIN" "$SCRIPT_DIR/mev_arbitrage_engine/mev_war_room_fire.py"
        ;;
    2)
        exec "$PYTHON_BIN" "$SCRIPT_DIR/mev_arbitrage_engine/the_beast_engine.py"
        ;;
    3)
        exec "$PYTHON_BIN" "$SCRIPT_DIR/mev_arbitrage_engine/terminal_command_center.py"
        ;;
    4)
        exec "$PYTHON_BIN" "$SCRIPT_DIR/mev_arbitrage_engine/run_multi_route_suite.py"
        ;;
    5)
        exec "$PYTHON_BIN" "$SCRIPT_DIR/mev_arbitrage_engine/live_bot_orchestrator.py"
        ;;
    6)
        exec "$PYTHON_BIN" "$SCRIPT_DIR/mev_arbitrage_engine/master_quant_frontier.py"
        ;;
    7)
        exec "$PYTHON_BIN" "$SCRIPT_DIR/mev_arbitrage_engine/run_simulation.py"
        ;;
    8)
        exec ./deploy_testnet.sh
        ;;
    9)
        exec "$PYTHON_BIN" "$SCRIPT_DIR/mev_arbitrage_engine/testnet_wallet.py"
        ;;
    q|Q)
        echo "Exiting."
        exit 0
        ;;
    *)
        echo "Invalid selection. Exiting."
        exit 1
        ;;
esac
