"""
Mathematical Engine for Quantitative DEX Arbitrage.
Implements:
1. Exact Constant Product AMM swap calculus (Uniswap V2 / Sushiswap).
2. Closed-form analytical optimization for two-pool arbitrage.
3. Multi-hop / Triangular arbitrage cycle detector.
"""

import math
from typing import Tuple, Dict, List, Optional

FEE_NUMERATOR = 997
FEE_DENOMINATOR = 1000
GAMMA = FEE_NUMERATOR / FEE_DENOMINATOR  # 0.997 for 0.3% fee


def get_amount_out(amount_in: float, reserve_in: float, reserve_out: float, gamma: float = GAMMA) -> float:
    """
    Computes the exact output token amount given an input amount and pool reserves.
    Formula: amount_out = (gamma * dx * y) / (x + gamma * dx)
    """
    if amount_in <= 0 or reserve_in <= 0 or reserve_out <= 0:
        return 0.0
    amount_in_with_fee = amount_in * (gamma * 1000)
    numerator = amount_in_with_fee * reserve_out
    denominator = (reserve_in * 1000) + amount_in_with_fee
    return numerator / denominator


def get_amount_in(amount_out: float, reserve_in: float, reserve_out: float, gamma: float = GAMMA) -> float:
    """
    Computes required input amount to receive an exact output amount.
    """
    if amount_out <= 0 or amount_out >= reserve_out:
        return float('inf')
    numerator = reserve_in * amount_out * 1000
    denominator = (reserve_out - amount_out) * (gamma * 1000)
    return (numerator / denominator) + 1.0


def calculate_optimal_arbitrage_input(
    reserve_in_a: float,
    reserve_out_a: float,
    reserve_in_b: float,
    reserve_out_b: float,
    gamma: float = GAMMA
) -> Tuple[float, float]:
    """
    Analytical closed-form solution to maximize net arbitrage profit across two AMM pools.
    
    Path:
    Pool A: Swap Token X -> Token Y (Reserves: x_a, y_a)
    Pool B: Swap Token Y -> Token X (Reserves: y_b, x_b)
    
    Let P(dx) = dx_out(Pool B) - dx
    Setting dP/d(dx) = 0 yields the optimal input dx*.
    
    Returns:
        (optimal_input_dx, expected_net_profit)
    """
    x_a = reserve_in_a
    y_a = reserve_out_a
    y_b = reserve_in_b
    x_b = reserve_out_b

    # Coefficients derived from the combined swap equation
    # P(dx) = [a * dx] / [b + c * dx] - dx
    a = (gamma ** 2) * y_a * x_b
    b = x_a * y_b
    c = gamma * (y_b + gamma * y_a)

    # An arbitrage opportunity exists only if sqrt(a * b) > b
    if a <= b:
        return 0.0, 0.0

    sqrt_ab = math.sqrt(a * b)
    optimal_dx = (sqrt_ab - b) / c

    if optimal_dx <= 0:
        return 0.0, 0.0

    # Calculate actual output and net profit with optimal input
    dy_received = get_amount_out(optimal_dx, x_a, y_a, gamma)
    dx_returned = get_amount_out(dy_received, y_b, x_b, gamma)
    net_profit = dx_returned - optimal_dx

    return optimal_dx, net_profit


class Pool:
    """Represents a live or simulated AMM Liquidity Pool."""
    def __init__(self, name: str, token0: str, token1: str, reserve0: float, reserve1: float):
        self.name = name
        self.token0 = token0
        self.token1 = token1
        self.reserve0 = reserve0
        self.reserve1 = reserve1

    @property
    def price_0_in_1(self) -> float:
        """Spot price of token0 denominated in token1 (before fee/slippage)."""
        return self.reserve1 / self.reserve0 if self.reserve0 > 0 else 0.0

    @property
    def price_1_in_0(self) -> float:
        """Spot price of token1 denominated in token0 (before fee/slippage)."""
        return self.reserve0 / self.reserve1 if self.reserve1 > 0 else 0.0

    def swap(self, token_in: str, amount_in: float) -> Tuple[str, float]:
        """Simulates an on-chain swap and updates pool state."""
        if token_in == self.token0:
            token_out = self.token1
            amount_out = get_amount_out(amount_in, self.reserve0, self.reserve1)
            self.reserve0 += amount_in
            self.reserve1 -= amount_out
        elif token_in == self.token1:
            token_out = self.token0
            amount_out = get_amount_out(amount_in, self.reserve1, self.reserve0)
            self.reserve1 += amount_in
            self.reserve0 -= amount_out
        else:
            raise ValueError(f"Token {token_in} not in pool {self.name}")

        return token_out, amount_out

    def clone(self) -> 'Pool':
        """Creates an isolated replica for zero-risk local simulation."""
        return Pool(self.name, self.token0, self.token1, self.reserve0, self.reserve1)
