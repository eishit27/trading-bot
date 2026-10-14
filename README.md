# Phoenix Quanta: Quantitative MEV Arbitrage Engine

High-frequency, self-funded quantitative MEV (Maximal Extractable Value) arbitrage engine built for EVM networks (**Coinbase Base L2 & Ethereum Mainnet**).

---

## ⚡ Core Architecture

- **100% Self-Funded Spot Equity:** Zero flash loans, zero borrowing, zero liquidation risks.
- **Deterministic Zero Capital Loss:** Enforced by two-tier protection:
  - **Tier 1 (Off-Chain RAM Simulation):** Local calculus evaluation before bundle creation. Unprofitable trades never hit the network.
  - **Tier 2 (On-Chain EVM Invariant Rollback):** `OptimizedArbitrageYul.sol` executes opcode `0xFD` (`REVERT`) if final balance is less than initial balance + minimum required profit.
- **Asymmetric Gas Optimization:** Pure Yul inline assembly with **EIP-1153 Transient Storage (`TSTORE`/`TLOAD`)** for reentrancy locking and balance tracking (81,200 gas vs. 148,500 gas standard Solidity).
- **Sub-Millisecond Mathematical Solvers:**
  - Analytical calculus closed-form solutions for Uniswap V2 / Aerodrome constant product curves.
  - Bounded 32-iteration Newton-Raphson solver for Curve StableSwap invariants.
  - Stanford CFMM convex flow graph routing for 3-hop and 4-hop triangular paths across multi-DEX pools.
- **Private Relay & Sequencer Dispatch:**
  - First-Come-First-Served (FCFS) sequencer prioritization on Base L2 (zero validator bribes).
  - Flashbots MEV-Boost multi-builder bundle dispatch on Ethereum L1 (`X-Flashbots-Signature`).

---

## 📁 Repository Structure

```text
├── mev_arbitrage_engine/
│   ├── contracts/
│   │   ├── OptimizedArbitrageYul.sol     # Low-level Yul assembly cyclic arbitrage contract
│   │   ├── PureEquityMultiRoute.sol      # Multi-route split-capital Solidity contract
│   │   └── AtomicArbitrage.sol           # Baseline reference contract
│   ├── amm.py                            # Canonical AMM pricing & calculus engine
│   ├── config.py                         # Centralized network endpoints, tokens, & gas profiles
│   ├── compile_contracts.py              # py-solc-x automated compilation pipeline
│   ├── deploy_base_sepolia.py            # Automated Base Sepolia contract deployer
│   ├── flashbots_broadcaster.py          # Parallel multi-builder bundle broadcaster
│   ├── holy_grail_multi_router.py        # Multi-hop graph pathfinder
│   ├── live_bot_orchestrator.py          # Full production telemetry & execution pipeline
│   ├── live_node_listener.py             # RPC listener & Sync event decoder
│   ├── mev_war_room_fire.py              # Live high-frequency animated terminal dashboard
│   ├── simulator.py                      # Virtual EVM and pool state simulator
│   ├── the_beast_engine.py               # 5-Pillar zero-bribe comparative benchmark
│   ├── tx_signer.py                      # EIP-1559 transaction constructor & secp256k1 signer
│   └── zero_loss_guardian.py             # Two-stage zero-loss verification guardian
├── deploy_testnet.sh                     # Deploy smart contracts to Base Sepolia
├── run_beast.sh                          # Run 'The Beast' benchmark suite
├── run_engine.sh                         # Linux Master Terminal Control Center
├── run_fire.sh                           # Launch Phoenix War Room Live TUI
├── requirements.txt                      # Python dependencies
└── README.md
```

---

## 🚀 Quick Start

### 1. Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Launch the Master Terminal Control Center
```bash
./run_engine.sh
```

### 3. Launch the Live Animated War Room
```bash
./run_fire.sh
```

---

## 🛡️ License
MIT License.
