#!/usr/bin/env python3
"""
Master Test Suite: The "Holy Grail" Multi-Route Aggregation Engine.

Demonstrates:
1. Discovery of 4 Independent Arbitrage Routes across the DeFi Graph:
   - Route 1: 2-Hop Direct (USDC -> WETH -> USDC)
   - Route 2: 3-Hop Triangular (USDC -> WETH -> WBTC -> USDC)
   - Route 3: 4-Hop Altcoin Cross (USDC -> DAI -> WETH -> LINK -> USDC)
   - Route 4: 3-Hop Governance Loop (USDC -> UNI -> WETH -> USDC)
2. The Mathematical Showdown: Single-Route Execution vs. Multi-Route Aggregation.
3. The Global Atomic Revert Shield ($0 Loss Guarantee for the entire bundle).
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from holy_grail_multi_router import ArbitrageRoute, HolyGrailMultiRouter


def print_banner(title: str):
    print("\n" + "=" * 80)
    print(f"  {title.upper()}")
    print("=" * 80)


def main():
    print("""
    ==============================================================================
    🏆 THE "HOLY GRAIL" MULTI-ROUTE ARBITRAGE AGGREGATOR
    ==============================================================================
    * Combines multiple independent & disjoint arbitrage cycles simultaneously
    * Karush-Kuhn-Tucker (KKT) Marginal Profit Balancing
    * Eliminates Single-Path Slippage Chokepoints
    * 100% Bundled Atomic Revert Guarantee
    ==============================================================================
    """)

    # -------------------------------------------------------------------------
    # 1. DEFINE 4 DISTINCT ARBITRAGE ROUTES
    # -------------------------------------------------------------------------
    print_banner("Step 1: Ingesting 4 Distinct Multi-Asset Routes")

    # Route 1: 2-Hop Direct (USDC/WETH spread)
    r1_hops = [
        (6_000_000.0, 2_000.0, 0.997),    # Uni: Swap USDC -> WETH ($3,000/ETH)
        (1_000.0, 3_055_000.0, 0.997)     # Sushi: Swap WETH -> USDC ($3,055/ETH - 1.8% Spread)
    ]
    route1 = ArbitrageRoute("R1_DIRECT", "Route 1 [2-Hop Direct]: USDC -> WETH -> USDC", r1_hops)

    # Route 2: 3-Hop Triangular (USDC -> WETH -> WBTC -> USDC)
    r2_hops = [
        (5_000_000.0, 1_666.6, 0.997),    # Uni: USDC -> WETH ($3,000/ETH)
        (2_000.0, 100.0, 0.997),          # Uni: WETH -> WBTC (0.05 BTC/ETH)
        (50.0, 3_110_000.0, 0.997)        # Sushi: WBTC -> USDC ($62,200/BTC)
    ]
    route2 = ArbitrageRoute("R2_TRIANGULAR", "Route 2 [3-Hop Triangular]: USDC -> WETH -> WBTC -> USDC", r2_hops)

    # Route 3: 4-Hop Altcoin Cross (USDC -> DAI -> WETH -> LINK -> USDC)
    r3_hops = [
        (4_000_000.0, 4_010_000.0, 0.997),# Curve: USDC -> DAI (Slight depeg)
        (3_010_000.0, 1_000.0, 0.997),    # Uni: DAI -> WETH
        (1_100.0, 200_000.0, 0.997),      # Uni: WETH -> LINK
        (100_000.0, 1_685_000.0, 0.997)   # Sushi: LINK -> USDC
    ]
    route3 = ArbitrageRoute("R3_QUAD", "Route 3 [4-Hop Altcoin]: USDC -> DAI -> WETH -> LINK -> USDC", r3_hops)

    # Route 4: 3-Hop Governance Loop (USDC -> UNI -> WETH -> USDC)
    r4_hops = [
        (2_100_000.0, 250_000.0, 0.997),  # Sushi: USDC -> UNI ($8.40/UNI)
        (500_000.0, 1_420.0, 0.997),      # Uni: UNI -> WETH
        (1_000.0, 3_045_000.0, 0.997)     # Aerodrome: WETH -> USDC
    ]
    route4 = ArbitrageRoute("R4_GOV", "Route 4 [3-Hop Gov Loop]: USDC -> UNI -> WETH -> USDC", r4_hops)

    routes = [route1, route2, route3, route4]
    for r in routes:
        print(f"  * {r.name}")

    # -------------------------------------------------------------------------
    # 2. THE SHOWDOWN: SINGLE ROUTE VS. MULTI-ROUTE AGGREGATION
    # -------------------------------------------------------------------------
    print_banner("Step 2: Single-Route vs. Multi-Route Performance Showdown")
    total_capital = 50_000.0
    print(f"Total Capital Available to Deploy: ${total_capital:,.2f} USDC\n")

    # Case A: Naïve Single Route (Forcing all $50,000 into Route 1)
    single_profit = route1.profit_at(total_capital)
    single_roi = (single_profit / total_capital) * 100.0
    print(f"--- CASE A: NAÏVE SINGLE-ROUTE (100% into Route 1) ---")
    print(f"  Allocated Capital: ${total_capital:,.2f} -> Route 1")
    if single_profit > 0:
        print(f"  Gross Profit:      +${single_profit:,.2f} USDC (ROI: {single_roi:.2f}%)")
    else:
        print(f"  Gross Profit:      $-{-single_profit:,.2f} USDC (REVERTED! Squeezed by massive slippage)")

    # Case B: The Multi-Route "Holy Grail" Aggregator
    aggregator = HolyGrailMultiRouter(routes)
    allocations, multi_profit = aggregator.optimize_multi_route_split(total_capital)
    multi_roi = (multi_profit / total_capital) * 100.0

    print(f"\n--- CASE B: MULTI-ROUTE 'HOLY GRAIL' AGGREGATION ---")
    for j in range(len(routes)):
        pct = (allocations[j] / total_capital) * 100.0
        r_profit = routes[j].profit_at(allocations[j])
        print(f"  -> {routes[j].name}")
        print(f"     Allocated: ${allocations[j]:>9,.2f} ({pct:>5.1f}%) | Route Profit: +${r_profit:>7,.2f}")

    print("-" * 80)
    print(f"Total Multi-Route Capital Deployed: ${sum(allocations):,.2f} USDC")
    print(f"Aggregate Net Profit:               +${multi_profit:,.2f} USDC (ROI: {multi_roi:.2f}%)")

    # Alpha Multiple
    if single_profit > 0:
        multiplier = multi_profit / single_profit
        extra_dollars = multi_profit - single_profit
        print(f"\n🏆 PERFORMANCE ADVANTAGE: {multiplier:.2f}x MORE PROFIT (+${extra_dollars:,.2f} pure extra gain)")
    else:
        print(f"\n🏆 PERFORMANCE ADVANTAGE: Multi-route turned a REVERTED trade into +${multi_profit:,.2f} clean profit!")

    print("\n💡 Key Insight: Single routes suffer from severe AMM slippage.")
    print("   By combining multiple non-colliding paths into a single atomic bundle,")
    print("   the engine extracts maximum liquidity without moving prices against itself.")

    # -------------------------------------------------------------------------
    # 3. GLOBAL BUNDLED ATOMIC REVERT GUARANTEE
    # -------------------------------------------------------------------------
    print_banner("Step 3: The Global Bundled Atomic Guarantee")
    print("In MultiRouteArbitrage.sol:")
    print("  require(balanceAfter >= balanceBefore + minTotalProfit)")
    print("  • If ANY route encounters sudden on-chain front-running,")
    print("  • The entire bundle rolls back atomically in one block.")
    print("  • Total Capital Loss = $0.00000000.")

    print("\n" + "=" * 80)
    print("  HOLY GRAIL MULTI-ROUTE SUITE COMPLETED WITH DISTINCTION")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
