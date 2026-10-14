"""
Uniswap V3 Concentrated Liquidity (CLAMM) Piecewise Tick Engine.

Mathematical Framework:
Unlike constant product AMMs (Uniswap V2) where liquidity is continuous and infinite,
Uniswap V3 concentrates liquidity into discrete intervals called Ticks.

Formulas:
1. Price at tick i:
       P(i) = 1.0001^i  =>  sqrt(P(i)) = 1.0001^(i / 2)
2. In-range swap amounts:
       Delta_x = L * (1 / sqrt(P_lower) - 1 / sqrt(P_upper))
       Delta_y = L * (sqrt(P_upper) - sqrt(P_lower))
3. Discrete Liquidity Step (Tick Crossing):
       When price crosses tick boundary i, active liquidity L transitions:
       L_new = L_current + Delta_L(i)  (when moving left-to-right)

This engine models exact piecewise non-linear price impact across discrete tick steps.
"""

import math
from typing import List, Dict, Tuple, Optional


class Tick:
    def __init__(self, index: int, liquidity_net: float):
        self.index = index
        self.liquidity_net = liquidity_net  # Delta L added/removed when crossing tick
        self.sqrt_price = math.pow(1.0001, index / 2.0)


class UniswapV3CLAMMPool:
    """
    Production-accurate simulation of a Uniswap V3 Concentrated Liquidity Pool.
    """
    def __init__(
        self,
        pool_id: str,
        token0: str,
        token1: str,
        fee_tier: float = 0.0005,  # 0.05% fee (500 bps)
        current_tick: int = 80000,
        current_liquidity: float = 10_000_000.0
    ):
        self.pool_id = pool_id
        self.token0 = token0
        self.token1 = token1
        self.fee = fee_tier
        self.gamma = 1.0 - fee_tier

        self.current_tick = current_tick
        self.sqrt_price = math.pow(1.0001, current_tick / 2.0)
        self.liquidity = current_liquidity
        self.ticks: Dict[int, Tick] = {}

    def add_tick(self, index: int, liquidity_net: float):
        self.ticks[index] = Tick(index, liquidity_net)

    @property
    def price(self) -> float:
        """Spot price P = (sqrt_price)^2"""
        return self.sqrt_price * self.sqrt_price

    def swap_token0_for_token1(self, amount_in: float) -> Tuple[float, float, int]:
        """
        Swaps Token 0 for Token 1 (Price decreases, sqrt_price moves downwards).
        Crosses ticks downward, dynamically updating liquidity L.
        Returns: (amount_out, final_price, ticks_crossed)
        """
        amount_remaining = amount_in
        amount_out = 0.0
        ticks_crossed = 0

        # Sort initialized ticks below current tick in descending order
        sorted_ticks = sorted(
            [t for t in self.ticks.values() if t.index < self.current_tick],
            key=lambda t: t.index,
            reverse=True
        )

        curr_sqrt_p = self.sqrt_price
        curr_l = self.liquidity

        for target_tick in sorted_ticks:
            if amount_remaining <= 0:
                break

            target_sqrt_p = target_tick.sqrt_price

            # Max token0 that can be consumed to move price from curr_sqrt_p down to target_sqrt_p
            # Delta_x = L * (1 / target_sqrt_p - 1 / curr_sqrt_p)
            max_delta_x = curr_l * (1.0 / target_sqrt_p - 1.0 / curr_sqrt_p) / self.gamma

            if amount_remaining >= max_delta_x:
                # Consume max amount, cross the tick!
                amount_in_step = max_delta_x
                # Delta_y = L * (curr_sqrt_p - target_sqrt_p)
                delta_y = curr_l * (curr_sqrt_p - target_sqrt_p)

                amount_out += delta_y
                amount_remaining -= amount_in_step

                # Cross the tick: subtract liquidity_net when moving left
                curr_l -= target_tick.liquidity_net
                curr_sqrt_p = target_sqrt_p
                self.current_tick = target_tick.index
                ticks_crossed += 1
            else:
                # Does not reach the next tick. Compute exact resting price within current tick:
                # 1 / new_sqrt_p = 1 / curr_sqrt_p + (amount_remaining * gamma) / L
                amount_in_eff = amount_remaining * self.gamma
                inv_new_sqrt_p = (1.0 / curr_sqrt_p) + (amount_in_eff / curr_l)
                new_sqrt_p = 1.0 / inv_new_sqrt_p

                delta_y = curr_l * (curr_sqrt_p - new_sqrt_p)
                amount_out += delta_y
                curr_sqrt_p = new_sqrt_p
                amount_remaining = 0.0
                break

        # Fallback if no more ticks exist: consume remaining in current liquidity
        if amount_remaining > 0 and curr_l > 0:
            amount_in_eff = amount_remaining * self.gamma
            inv_new_sqrt_p = (1.0 / curr_sqrt_p) + (amount_in_eff / curr_l)
            new_sqrt_p = 1.0 / inv_new_sqrt_p
            delta_y = curr_l * (curr_sqrt_p - new_sqrt_p)
            amount_out += delta_y
            curr_sqrt_p = new_sqrt_p

        self.sqrt_price = curr_sqrt_p
        self.liquidity = curr_l
        return amount_out, self.price, ticks_crossed
