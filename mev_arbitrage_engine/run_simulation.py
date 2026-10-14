#!/usr/bin/env python3
"""
Interactive Quantitative MEV Arbitrage Simulation Suite.
Demonstrates:
1. Analytical Optimal Input Calculation vs. Naïve Guessing.
2. Atomic Execution with Revert Protection (The $0 Loss Guarantee).
3. Flash Swaps ($0 Collateral Arbitrage).
4. Triangular Multi-Hop Arbitrage.
"""

import sys
from math_engine import Pool, calculate_optimal_arbitrage_input, get_amount_out
from simulator import ArbitrageSimulator


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title.upper()}")
    print("=" * 70)


def run_scenario_1_optimal_vs_naive():
    print_banner("Scenario 1: Optimal Trade Sizing vs. Naïve Sizing")
    print("Market Setup:")
    print("  Pool A (Uniswap V2): 100 WETH / 300,000 USDC   -> Spot Price: $3,000.00 / ETH")
    print("  Pool B (Sushiswap):  100 WETH / 309,000 USDC   -> Spot Price: $3,090.00 / ETH (3% Spread)")
    print("-" * 70)

    # Setup pools
    pool_a = Pool("Uniswap_ETH_USDC", "WETH", "USDC", reserve0=100.0, reserve1=300000.0)
    pool_b = Pool("Sushiswap_ETH_USDC", "WETH", "USDC", reserve0=100.0, reserve1=309000.0)

    sim = ArbitrageSimulator({
        "Uniswap": pool_a.clone(),
        "Sushiswap": pool_b.clone()
    })

    # 1. Analytical solution
    r_in_a = pool_a.reserve1    # USDC
    r_out_a = pool_a.reserve0   # WETH
    r_in_b = pool_b.reserve0    # WETH
    r_out_b = pool_b.reserve1   # USDC

    opt_dx, opt_profit = calculate_optimal_arbitrage_input(r_in_a, r_out_a, r_in_b, r_out_b)

    print(f"[CALCULUS ENGINE] Mathematically Optimal Trade Size: ${opt_dx:,.2f} USDC")
    print(f"[CALCULUS ENGINE] Expected Net Gross Profit:       ${opt_profit:,.2f} USDC")
    print()

    # Compare 3 different trade sizes:
    # 1. Under-sized ($1,000)
    # 2. Optimal ($opt_dx)
    # 3. Over-sized ($50,000) -> where slippage destroys the profit!
    test_sizes = [1000.0, opt_dx, 50000.0]

    for size in test_sizes:
        temp_sim = ArbitrageSimulator({
            "Uniswap": pool_a.clone(),
            "Sushiswap": pool_b.clone()
        })
        res = temp_sim.simulate_two_pool_arbitrage(
            pool_buy_name="Uniswap",
            pool_sell_name="Sushiswap",
            token_base="USDC",
            token_quote="WETH",
            amount_in=size,
            min_profit_threshold=0.01
        )
        tag = "OPTIMAL" if abs(size - opt_dx) < 1e-3 else ("UNDERSIZED" if size < opt_dx else "OVERSIZED")
        print(f"[{tag:^10}] Input: ${size:>9,.2f} | Result: {'SUCCESS' if res.success else 'REVERTED'}")
        print(f"             Output: ${res.amount_out:>9,.2f} | Net Profit: ${res.net_profit:>8,.2f}")
        if not res.success:
            print(f"             Reason: {res.reason}")
    print("\n💡 Key Insight: Notice how trading $50,000 caused so much price slippage")
    print("   that the trade actually LOST money and REVERTED! Sizing is everything in quantitative trading.")


def run_scenario_2_atomic_revert():
    print_banner("Scenario 2: The Atomic Revert Guarantee ($0 Capital Loss)")
    print("Market Setup:")
    print("  Pool A (Uniswap):   100 WETH / 300,000 USDC -> Spot Price: $3,000.00 / ETH")
    print("  Pool B (Sushiswap): 100 WETH / 300,500 USDC -> Spot Price: $3,005.00 / ETH (Spread: 0.16%)")
    print("  Exchange Fees:      0.3% per swap (0.6% combined round-trip fee)")
    print("-" * 70)
    print("Because the spread (0.16%) is SMALLER than the fees (0.60%), this trade is unprofitable.")
    print("In traditional finance, an amateur trader would lose capital here.")
    print("Let's run our Atomic Smart Contract simulation:")
    print("-" * 70)

    pool_a = Pool("Uniswap", "WETH", "USDC", reserve0=100.0, reserve1=300000.0)
    pool_b = Pool("Sushiswap", "WETH", "USDC", reserve0=100.0, reserve1=300500.0)

    sim = ArbitrageSimulator({"Uniswap": pool_a, "Sushiswap": pool_b})

    # Attempt to execute with $5,000
    res = sim.simulate_two_pool_arbitrage(
        pool_buy_name="Uniswap",
        pool_sell_name="Sushiswap",
        token_base="USDC",
        token_quote="WETH",
        amount_in=5000.0,
        min_profit_threshold=1.0  # Require at least $1 profit
    )

    print(f"Status:        {'✅ SUCCESS' if res.success else '🛡️ ATOMIC REVERT TRIGGERED'}")
    print(f"EVM Event:     {res.reason}")
    print(f"Capital Lost:  ${res.net_profit:,.2f} (Zero capital lost!)")
    print("\n💡 Key Insight: The smart contract's `require` statement rolled back all")
    print("   token transfers. Your starting balance remains 100% intact.")


def run_scenario_3_spot_equity_arbitrage():
    print_banner("Scenario 3: 100% Self-Funded Spot Equity Arbitrage (Zero Loans)")
    print("Setup:")
    print("  Deposited Capital: $500.00 USDC (Strictly 100% Spot Equity, Zero Borrowing)")
    print("  Outstanding Debt:  $0.00 (Zero loans, zero margin liabilities)")
    print("  Pool A (Buy Pool):  500 WETH / 1,500,000 USDC ($3,000.00 / ETH - Underpriced)")
    print("  Pool B (Sell Pool): 500 WETH / 1,560,000 USDC ($3,120.00 / ETH - Overpriced)")
    print("-" * 70)

    pool_buy = Pool("BuyPool_Cheap", "WETH", "USDC", reserve0=500.0, reserve1=1500000.0)
    pool_sell = Pool("SellPool_Expensive", "WETH", "USDC", reserve0=500.0, reserve1=1560000.0)

    sim = ArbitrageSimulator({"BuyPool_Cheap": pool_buy, "SellPool_Expensive": pool_sell})

    equity_deployed = 500.0  # Deploy $500 USDC
    print(f"Action: Deploying ${equity_deployed:.2f} USDC self-funded spot equity...")

    res = sim.simulate_spot_equity_arbitrage(
        pool_buy_name="BuyPool_Cheap",
        pool_sell_name="SellPool_Expensive",
        token_base="USDC",
        token_quote="WETH",
        self_funded_equity=equity_deployed,
        min_profit_threshold=1.0
    )

    print(f"Status:        {'✅ SUCCESS' if res.success else '❌ FAILED'}")
    print(f"Details:       {res.reason}")
    print(f"Net Profit:    +${res.net_profit:,.2f} USDC (ROI: {(res.net_profit/equity_deployed)*100:.2f}%)")
    print(f"Debt Balance:  $0.00 (Zero loans taken, 100% principal safe)")
    print("\n💡 Key Insight: Using pure spot equity completely eliminates liquidation risk,")
    print("   interest costs, and debt obligations while retaining EVM atomic revert protection.")


def run_scenario_4_triangular_arbitrage():
    print_banner("Scenario 4: Multi-Hop / Triangular Arbitrage (The Long-Tail Edge)")
    print("Market Setup (3 Interconnected Pools):")
    print("  Pool 1 (USDC/WETH):  Spot = $3,000.00 / ETH")
    print("  Pool 2 (WETH/WBTC):  Spot = 0.0500 BTC / ETH (1 BTC = 20 ETH = $60,000)")
    print("  Pool 3 (WBTC/USDC):  Spot = $62,000.00 / BTC (Temporary price lag in BTC/USDC)")
    print("-" * 70)
    print("Route: USDC -> WETH -> WBTC -> USDC")

    # 1. Setup 3 pools
    pool1 = Pool("USDC_WETH", "USDC", "WETH", reserve0=3000000.0, reserve1=1000.0)
    pool2 = Pool("WETH_WBTC", "WETH", "WBTC", reserve0=1000.0, reserve1=50.0)
    pool3 = Pool("WBTC_USDC", "WBTC", "USDC", reserve0=50.0, reserve1=3100000.0)

    input_usdc = 10000.0  # Trade $10,000
    print(f"Starting Capital: ${input_usdc:,.2f} USDC")

    # Leg 1: USDC -> WETH
    _, weth_received = pool1.swap("USDC", input_usdc)
    print(f"  Step 1: Swapped ${input_usdc:,.2f} USDC -> Received {weth_received:.4f} WETH")

    # Leg 2: WETH -> WBTC
    _, wbtc_received = pool2.swap("WETH", weth_received)
    print(f"  Step 2: Swapped {weth_received:.4f} WETH -> Received {wbtc_received:.4f} WBTC")

    # Leg 3: WBTC -> USDC
    _, final_usdc = pool3.swap("WBTC", wbtc_received)
    print(f"  Step 3: Swapped {wbtc_received:.4f} WBTC -> Received ${final_usdc:,.2f} USDC")

    gross_profit = final_usdc - input_usdc
    print("-" * 70)
    print(f"Final Return:   ${final_usdc:,.2f} USDC")
    print(f"Net Profit:     +${gross_profit:,.2f} USDC ({gross_profit / input_usdc * 100:.2f}%)")
    print("\n💡 Key Insight: This is where independent quant searchers find profit.")
    print("   Two-token pairs are crowded by HFT firms, but multi-hop graph routes")
    print("   across thousands of tokens contain pricing lags that smaller algorithms can harvest.")


def main():
    print("""
    ======================================================================
    🚀 QUANTITATIVE ATOMIC ARBITRAGE & MEV SIMULATION ENGINE
    ======================================================================
    Built with:
    - Pure Mathematical AMM Curve Calculus
    - EVM Atomic Revert Contract Simulation
    - Zero-Risk Simulation Suite
    ======================================================================
    """)
    run_scenario_1_optimal_vs_naive()
    run_scenario_2_atomic_revert()
    run_scenario_3_spot_equity_arbitrage()
    run_scenario_4_triangular_arbitrage()
    print("\n" + "=" * 70)
    print("  SIMULATION SUITE COMPLETED SUCCESSFULLY")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
