"""
The Multi-Route "Holy Grail" Flow Aggregator & Sizing Engine.

Mathematical Framework:
Instead of sending 100% of capital through a single route (which incurs severe slippage),
this engine discovers M independent or disjoint arbitrage routes simultaneously, and solves
the constrained multi-route capital allocation problem:

    maximize   sum_{j=1}^M Pi_j(x_j)
    subject to sum_{j=1}^M x_j <= X_total
               x_j >= 0  for all j in {1, ..., M}

Where each Pi_j(x_j) is the strictly concave profit function of route j.

By Karush-Kuhn-Tucker (KKT) optimality conditions:
At the optimum, the marginal return across all actively deployed routes must be EQUAL:
    d(Pi_1)/dx_1 = d(Pi_2)/dx_2 = ... = d(Pi_M)/dx_M = lambda*

This ensures no single route suffers from excessive price impact, multiplying net profits
while maintaining 100% atomic revert protection.
"""

import math
from typing import List, Dict, Tuple
try:
    from .advanced_math_engine import MultiHopCycleOptimizer, AdvancedAMMMath
except (ImportError, ValueError):
    from advanced_math_engine import MultiHopCycleOptimizer, AdvancedAMMMath


class ArbitrageRoute:
    def __init__(self, route_id: str, name: str, hops: List[Tuple[float, float, float]]):
        """
        hops: List of (reserve_in, reserve_out, gamma)
        """
        self.route_id = route_id
        self.name = name
        self.hops = hops
        self.optimizer = MultiHopCycleOptimizer(hops)

    def update_hops(self, new_hops: List[Tuple[float, float, float]]):
        """In-place reserve update avoiding reallocation."""
        self.hops = new_hops
        self.optimizer.hops = new_hops
        self.optimizer.k = len(new_hops)

    def profit_at(self, x: float) -> float:
        """Returns net gross profit Pi(x) = F(x) - x."""
        if x <= 0:
            return 0.0
        out, _, _ = self.optimizer.evaluate_composition(x)
        return out - x

    def marginal_profit_at(self, x: float) -> float:
        """Returns d(Pi)/dx = F'(x) - 1.0."""
        if x <= 0:
            _, f_prime, _ = self.optimizer.evaluate_composition(1e-6)
            return f_prime - 1.0
        _, f_prime, _ = self.optimizer.evaluate_composition(x)
        return f_prime - 1.0


class HolyGrailMultiRouter:
    """
    Multi-Route Flow Aggregator.
    Optimally balances capital across M simultaneous arbitrage routes.
    """
    def __init__(self, routes: List[ArbitrageRoute]):
        self.routes = routes
        self.m = len(routes)

    def optimize_multi_route_split(
        self,
        total_capital: float,
        step_size: float = 100.0,
        max_iterations: int = 500
    ) -> Tuple[List[float], float]:
        """
        Solves multi-route capital allocation via Marginal Return Gradient Balancing.
        Allocates incremental capital packets to whichever route currently offers
        the highest marginal profit d(Pi_j)/dx_j.
        
        Returns: (allocations, total_net_profit)
        """
        if total_capital <= 0 or self.m == 0:
            return [0.0] * self.m, 0.0

        allocations = [0.0] * self.m
        remaining_capital = total_capital
        packet_size = min(step_size, total_capital / 50.0)

        while remaining_capital > 1e-4:
            current_packet = min(packet_size, remaining_capital)

            # Evaluate marginal profit across all routes at their current allocation
            marginal_profits = [
                self.routes[j].marginal_profit_at(allocations[j])
                for j in range(self.m)
            ]

            # Find route with the highest marginal return
            best_idx = max(range(self.m), key=lambda j: marginal_profits[j])

            # If even the best route has negative marginal return, stop allocating
            if marginal_profits[best_idx] <= 0:
                break

            allocations[best_idx] += current_packet
            remaining_capital -= current_packet

        # Compute aggregate profit across all routes
        total_profit = sum(
            self.routes[j].profit_at(allocations[j])
            for j in range(self.m)
        )

        return allocations, total_profit
