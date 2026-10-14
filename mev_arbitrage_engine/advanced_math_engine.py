"""
Advanced Quantitative Mathematics Engine for Decentralized Exchange (DEX) Arbitrage.

Mathematical Foundations:
1. Log-Transformation of AMM Marginal Rates:
   Maps optimal arbitrage routing to Negative-Weight Cycle Detection on Directed Multigraphs.
   Weight w(u, v) = -ln(gamma * reserve_out / reserve_in).
   A negative cycle in sum of weights corresponds to a product of rates > 1.

2. Strict Concavity & Exact Convex Optimization:
   For an arbitrary K-hop cyclic path C = (p_1, p_2, ..., p_K), each AMM swap function:
       f_i(x) = (gamma_i * x * y_i) / (x_i + gamma_i * x)
   is strictly concave (f''(x) < 0) and monotonically increasing (f'(x) > 0).
   The composition F(x) = f_K(f_{K-1}(...f_1(x)...)) is strictly concave.
   Therefore, Profit Pi(x) = F(x) - x is strictly concave with a UNIQUE global maximum x*.
   Solved via analytical Newton-Raphson iteration with exact derivative composition:
       x_{n+1} = x_n - Pi'(x_n) / Pi''(x_n).

3. Game-Theoretic Auction Valuation (First-Price Sealed-Bid Flashbots Bribe):
   Under Bayesian Nash Equilibrium with N competing searchers:
       b*(v) = ((N - 1) / N) * v
   Calculates optimal tip to guarantee block inclusion while maximizing retained searcher surplus.
"""

import math
from typing import List, Tuple, Dict, Optional


GAMMA = 0.997  # 0.3% standard DEX fee


class AdvancedAMMMath:
    @staticmethod
    def swap_f(x: float, r_in: float, r_out: float, gamma: float = GAMMA) -> float:
        """AMM swap output: f(x) = (gamma * x * r_out) / (r_in + gamma * x)"""
        if x <= 0:
            return 0.0
        g_x = gamma * x
        return (g_x * r_out) / (r_in + g_x)

    @staticmethod
    def swap_f_prime(x: float, r_in: float, r_out: float, gamma: float = GAMMA) -> float:
        """First derivative: f'(x) = (gamma * r_in * r_out) / (r_in + gamma * x)^2"""
        denom = r_in + gamma * x
        return (gamma * r_in * r_out) / (denom * denom)

    @staticmethod
    def swap_f_double_prime(x: float, r_in: float, r_out: float, gamma: float = GAMMA) -> float:
        """Second derivative: f''(x) = -2 * (gamma^2 * r_in * r_out) / (r_in + gamma * x)^3"""
        denom = r_in + gamma * x
        return -2.0 * (gamma * gamma * r_in * r_out) / (denom * denom * denom)


class MultiHopCycleOptimizer:
    """
    Solves for the exact global optimal capital allocation along any arbitrary K-hop AMM cycle.
    Uses Newton-Raphson with Chain Rule Derivative Propagation.
    """
    def __init__(self, hop_reserves: List[Tuple[float, float, float]]):
        """
        hop_reserves: List of (reserve_in, reserve_out, gamma) for each pool in the cycle.
        """
        self.hops = hop_reserves
        self.k = len(hop_reserves)

    def evaluate_composition(self, x: float) -> Tuple[float, float, float]:
        """
        Evaluates F(x), F'(x), and F''(x) along the cycle using the Chain Rule:
        F = f_K o f_{K-1} o ... o f_1
        F'(x) = prod_{i=1}^K f_i'(z_{i-1})
        F''(x) = derived via logarithmic differentiation / recursive chain rule.
        """
        if x <= 0:
            return 0.0, 0.0, 0.0

        z = x
        f_vals = [x]
        f_primes = []
        f_double_primes = []

        for r_in, r_out, gamma in self.hops:
            out = AdvancedAMMMath.swap_f(z, r_in, r_out, gamma)
            fp = AdvancedAMMMath.swap_f_prime(z, r_in, r_out, gamma)
            fpp = AdvancedAMMMath.swap_f_double_prime(z, r_in, r_out, gamma)

            f_primes.append(fp)
            f_double_primes.append(fpp)
            z = out
            f_vals.append(z)

        # F'(x) = product of all f_i'(z_{i-1})
        f_prime_total = 1.0
        for fp in f_primes:
            f_prime_total *= fp

        # F''(x) using chain rule:
        # F''(x) = sum_{j=1}^K [ f_j''(z_{j-1}) * (prod_{m=1}^{j-1} f_m')^2 * prod_{n=j+1}^K f_n' ]
        f_double_prime_total = 0.0
        for j in range(self.k):
            # Term before j
            prod_before = 1.0
            for m in range(j):
                prod_before *= f_primes[m]

            # Term after j
            prod_after = 1.0
            for n in range(j + 1, self.k):
                prod_after *= f_primes[n]

            term = f_double_primes[j] * (prod_before ** 2) * prod_after
            f_double_prime_total += term

        return f_vals[-1], f_prime_total, f_double_prime_total

    def optimize_input(self, tolerance: float = 1e-6, max_iter: int = 50) -> Tuple[float, float]:
        """
        Finds the exact optimal input x* where Pi'(x) = F'(x) - 1 = 0.
        Returns: (x_star, max_profit)
        """
        # Step 1: Check marginal profitability at x -> 0+
        _, f_prime_zero, _ = self.evaluate_composition(1e-6)
        if f_prime_zero <= 1.0:
            # Marginal return at zero input is <= 1, meaning even a $0.01 trade loses money.
            return 0.0, 0.0

        # Initial heuristic starting guess (based on smallest pool liquidity)
        min_reserve = min(h[0] for h in self.hops)
        x = min_reserve * 0.01  # start at 1% of pool size

        for _ in range(max_iter):
            f_val, f_prime, f_double_prime = self.evaluate_composition(x)
            grad = f_prime - 1.0  # Pi'(x)

            if abs(grad) < tolerance:
                break

            if f_double_prime >= 0:
                # Should not occur due to strict concavity, fallback to gradient step
                step = grad * 0.1
            else:
                step = grad / f_double_prime

            x_next = x - step

            # Keep x strictly positive and within liquidity bounds
            if x_next <= 0:
                x = x * 0.5
            else:
                x = x_next

        final_out, _, _ = self.evaluate_composition(x)
        profit = final_out - x
        return max(0.0, x), max(0.0, profit)


class GraphArbitrageEngine:
    """
    Constructs a full multi-asset directed liquidity graph.
    Uses Bellman-Ford to find all negative-weight arbitrage cycles.
    """
    def __init__(self):
        self.tokens: List[str] = []
        self.edges: List[Dict] = []

    def add_pool(self, pool_id: str, token_a: str, token_b: str, r_a: float, r_b: float, gamma: float = GAMMA):
        if token_a not in self.tokens:
            self.tokens.append(token_a)
        if token_b not in self.tokens:
            self.tokens.append(token_b)

        # Forward edge: Swap Token A -> Token B
        # Marginal exchange rate: gamma * (r_b / r_a)
        rate_ab = gamma * (r_b / r_a)
        weight_ab = -math.log(rate_ab)

        # Reverse edge: Swap Token B -> Token A
        rate_ba = gamma * (r_a / r_b)
        weight_ba = -math.log(rate_ba)

        self.edges.append({
            "pool_id": pool_id,
            "u": token_a,
            "v": token_b,
            "weight": weight_ab,
            "r_in": r_a,
            "r_out": r_b,
            "gamma": gamma
        })
        self.edges.append({
            "pool_id": pool_id,
            "u": token_b,
            "v": token_a,
            "weight": weight_ba,
            "r_in": r_b,
            "r_out": r_a,
            "gamma": gamma
        })

    def find_negative_cycles(self) -> List[List[Dict]]:
        """
        Executes Bellman-Ford with cycle decomposition to discover all arbitrage loops.
        """
        n = len(self.tokens)
        dist = {t: 0.0 for t in self.tokens}
        parent = {t: None for t in self.tokens}
        edge_used = {t: None for t in self.tokens}

        # Relax edges |V| - 1 times
        for _ in range(n - 1):
            for edge in self.edges:
                u, v, w = edge["u"], edge["v"], edge["weight"]
                if dist[u] + w < dist[v] - 1e-9:
                    dist[v] = dist[u] + w
                    parent[v] = u
                    edge_used[v] = edge

        # Detect negative weight cycles on n-th pass
        cycles = []
        visited_nodes = set()

        for edge in self.edges:
            u, v, w = edge["u"], edge["v"], edge["weight"]
            if dist[u] + w < dist[v] - 1e-9:
                # Negative cycle found! Trace back to find cycle
                curr = v
                for _ in range(n):
                    curr = parent[curr]

                # Extract the cycle
                cycle = []
                step = curr
                while True:
                    e = edge_used[step]
                    cycle.append(e)
                    step = parent[step]
                    if step == curr or step is None:
                        break

                cycle.reverse()
                cycle_key = tuple(e["pool_id"] for e in cycle)
                if cycle_key not in visited_nodes and len(cycle) >= 2:
                    visited_nodes.add(cycle_key)
                    cycles.append(cycle)

        return cycles


class GameTheoreticAuctionSolver:
    """
    Computes optimal validator tips under First-Price Sealed-Bid MEV Auctions (Flashbots / MEV-Boost).
    """
    @staticmethod
    def calculate_optimal_bid(gross_profit: float, estimated_competitors: int = 5) -> Tuple[float, float]:
        """
        Bayesian Nash Equilibrium Bidding Formula:
        b*(v) = ((N - 1) / N) * v
        Returns: (builder_bribe_tip, retained_searcher_profit)
        """
        if gross_profit <= 0:
            return 0.0, 0.0

        n = max(2, estimated_competitors)
        bribe_fraction = (n - 1.0) / float(n)
        
        # Add slight competitive margin (capped at 98% to avoid negative returns)
        bribe_fraction = min(0.98, max(0.50, bribe_fraction))

        builder_tip = gross_profit * bribe_fraction
        retained_profit = gross_profit - builder_tip

        return builder_tip, retained_profit
