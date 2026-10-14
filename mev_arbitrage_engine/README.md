# Quantitative Atomic Arbitrage & MEV Simulation Engine

An educational, quantitative framework demonstrating how atomic arbitrage, trade sizing calculus, and $0-collateral flash swaps work under the hood.

---

## 📁 Repository Structure

```
mev_arbitrage_engine/
├── contracts/
│   ├── PureEquityMultiRoute.sol   # 100% Self-Funded, ZERO-DEBT multi-route aggregator (no loans, pure spot equity)
│   ├── MultiRouteArbitrage.sol    # Multi-path batch aggregator contract (bundles multiple cycles in 1 tx)
│   ├── AtomicArbitrage.sol        # Production Solidity contract with atomic revert & flash swap callee
│   └── OptimizedArbitrageYul.sol  # Pure Yul assembly contract with EIP-1153 transient storage (45.3% gas savings)
├── terminal_command_center.py     # Live Bloomberg-style Quant Terminal Command Center (Zero-Debt TUI)
├── holy_grail_multi_router.py     # Multi-route KKT flow balancing aggregator (splits capital across 4+ paths)
├── run_multi_route_suite.py       # Performance showdown: Single-route vs. Multi-route aggregation
├── live_node_listener.py          # Real-time RPC node event listener & Uniswap Sync log decoder
├── curve_stableswap_engine.py     # Curve StableSwap invariant & Newton-Raphson D/y solver
├── uniswap_v3_clamm_engine.py     # Uniswap V3 concentrated liquidity piecewise tick crossing
├── stanford_cfmm_router.py        # Stanford global convex flow splitter (Boyd & Chitra KKT solver)
├── zero_loss_guardian.py          # Pre-flight RAM simulation & zero-loss execution shield
├── tx_signer.py                   # Cryptographic ECDSA signer & EIP-1559 Type-2 transaction encoder
├── flashbots_broadcaster.py       # Multi-builder private relay broadcaster (X-Flashbots-Signature)
├── live_bot_orchestrator.py       # Full end-to-end live production pipeline daemon
├── run_advanced_suite.py          # Graph theory & multi-hop Newton-Raphson optimizer
├── master_quant_frontier.py       # Frontier master runner (Stanford + V3 + Zero-Loss Proof)
└── run_simulation.py              # Baseline interactive scenarios
```

---

## 🧮 The Advanced Quantitative Architecture

### 1. Multi-Route "Holy Grail" Aggregation (KKT Balancing)
Instead of forcing all capital through a single route (which incurs severe price slippage), the aggregator discovers multiple non-colliding cycles simultaneously and balances capital across all active routes such that marginal profit is equalized:

$$\frac{d\Pi_1}{dx_1}(x_1^*) = \frac{d\Pi_2}{dx_2}(x_2^*) = \dots = \frac{d\Pi_M}{dx_M}(x_M^*) = \lambda^*$$

Bundled into a single atomic transaction via [MultiRouteArbitrage.sol](file:///home/eishit/Documents/antigravity/busy-newton/mev_arbitrage_engine/contracts/MultiRouteArbitrage.sol).

### 2. Multi-Protocol Pricing (Uniswap V2, V3, and Curve)
* **Uniswap V2:** Constant-product analytical closed-form optimal trade sizing $\Delta x^*$.
* **Uniswap V3 CLAMM:** Square root price ($\sqrt{P}$) and discrete tick boundary crossing ($\pm \Delta L$).
* **Curve Finance:** StableSwap invariant ($A \cdot n^n \sum x_i + D = A \cdot D \cdot n^n + \frac{D^{n+1}}{n^n \prod x_i}$) solved via Newton-Raphson iteration.

### 3. Stanford CFMM Global Convex Flow Splitting (Boyd & Chitra)
Splits capital across fragmented liquidity pools simultaneously via Projected Gradient Descent on a simplex, equalizing marginal prices across all routes to extract maximum alpha with minimum slippage.

### 4. Cryptographic EIP-1559 Signer & Multi-Builder Private Relay
* **Type-2 Transaction Encoding:** Packs custom calldata for `OptimizedArbitrageYul.sol` and signs raw RLP bytes with secp256k1 ECDSA.
* **Flashbots `X-Flashbots-Signature`:** Generates cryptographic header authentication over payload hashes.
* **Multi-Casting:** Broadcasts simultaneously to **Flashbots, Titan, BeaverBuild, and Builder0x69**.

### 5. Deterministic Zero-Loss Execution Shield
* **Off-chain:** `ZeroLossGuardian` aborts non-profitable trades in local RAM ($0 bytes sent, $0 gas spent).
* **On-chain:** EVM `REVERT` opcode resets state to transaction origin if net return is below minimum profit ($0 capital lost).
* **Private Relay:** Block builders drop reverting bundles, preventing any failed transactions from ever landing on-chain.

---

## 🚀 How to Run

### Run the Live Quant Terminal Command Center (Zero-Debt TUI Dashboard):
```bash
./.venv/bin/python3 mev_arbitrage_engine/terminal_command_center.py
```

### Run the "Holy Grail" Multi-Route Showdown Suite:
```bash
./.venv/bin/python3 mev_arbitrage_engine/run_multi_route_suite.py
```

### Run the Full Live Production Pipeline:
```bash
./.venv/bin/python3 mev_arbitrage_engine/live_bot_orchestrator.py
```

### Run the Frontier Suite (Stanford CFMM + V3 CLAMM + Zero-Loss):
```bash
./.venv/bin/python3 mev_arbitrage_engine/master_quant_frontier.py
```

### Run the Graph Optimization Suite (Bellman-Ford + Newton-Raphson):
```bash
./.venv/bin/python3 mev_arbitrage_engine/run_advanced_suite.py
```

---

## 🛡️ The Smart Contract Atomic Guarantee

In [AtomicArbitrage.sol](file:///home/eishit/Documents/antigravity/busy-newton/mev_arbitrage_engine/contracts/AtomicArbitrage.sol):
```solidity
uint256 balanceAfter = IERC20(tokenA).balanceOf(address(this));
require(
    balanceAfter >= balanceBefore + minProfit,
    "ATOMIC_REVERT: Arbitrage did not meet minimum profit threshold"
);
```
If the execution fails to deliver at least `minProfit`:
* All token transfers within the block are **rolled back** by the EVM.
* **$0.00 of trading capital is lost.**

---

## 🚀 How to Run the Simulation

Run the simulation suite using Python:

```bash
./.venv/bin/python3 mev_arbitrage_engine/run_simulation.py
```

### Included Scenarios:
1. **Optimal Sizing vs. Naïve Sizing:** Demonstrates why oversized trades cause slippage that triggers atomic reverts.
2. **Atomic Revert Protection:** Proves how the smart contract prevents capital loss when spreads are smaller than fees.
3. **$0-Collateral Flash Swaps:** Borrows WETH with $0 upfront, sells on an overpriced pool, repays the loan, and retains profit.
4. **Triangular Arbitrage:** Demonstrates multi-hop routing (USDC $\rightarrow$ WETH $\rightarrow$ WBTC $\rightarrow$ USDC) across liquidity pools.
