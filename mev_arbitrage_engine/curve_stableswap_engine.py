"""
Curve StableSwap Invariant & Quantitative Pricing Engine.

Mathematical Framework:
Curve Finance uses an invariant combining the Constant Sum invariant (zero slippage)
and Constant Product invariant (infinite liquidity):

    A * n^n * sum(x_i) + D = A * D * n^n + D^(n+1) / (n^n * prod(x_i))

Where:
- n: number of tokens in the pool
- A: amplification coefficient (higher A means closer to constant sum)
- D: total invariant (total pool value at equilibrium when all x_i = D/n)
- x_i: balances of each token in the pool

This engine computes:
1. Exact invariant D via Newton-Raphson iteration.
2. Output y_j when inputting Delta x_i.
3. Exact marginal exchange rates and StableSwap slippage.
"""

import math
from typing import List, Tuple


class CurveStableSwapPool:
    def __init__(self, pool_id: str, tokens: List[str], balances: List[float], A: float = 100.0, fee: float = 0.0004):
        """
        fee: 0.04% (standard Curve 4 bps)
        """
        self.pool_id = pool_id
        self.tokens = tokens
        self.balances = [float(b) for b in balances]
        self.n = len(tokens)
        self.A = float(A)
        self.fee = float(fee)
        self.gamma = 1.0 - fee

    def get_D(self, balances: List[float]) -> float:
        """
        Calculates the invariant D given token balances using Newton's method.
        Solves:
            f(D) = D^(n+1)/(n^n * prod(x)) + (A * n^n - 1) * D - A * n^n * sum(x) = 0
        """
        S = sum(balances)
        if S == 0:
            return 0.0

        n = self.n
        Ann = self.A * (n ** n)

        D = S
        for _ in range(32):
            D_P = D
            for x in balances:
                if x <= 0:
                    return 0.0
                D_P = (D_P * D) / (x * n)

            D_prev = D
            num = (Ann * S + n * D_P) * D
            den = (Ann - 1.0) * D + (n + 1.0) * D_P
            if den == 0:
                break
            D = num / den

            if abs(D - D_prev) <= 1e-4:
                return D

        return D

    def get_y(self, i: int, j: int, x_i_new: float) -> float:
        """
        Calculates the new balance of token j when balance of token i becomes x_i_new.
        Solves for y = x_j in the Curve invariant.
        """
        n = self.n
        balances = list(self.balances)
        D = self.get_D(balances)

        balances[i] = x_i_new
        Ann = self.A * (n ** n)

        # Sum of all balances except token j
        c = D
        S_prime = 0.0

        for k in range(n):
            if k != j:
                S_prime += balances[k]
                c = (c * D) / (balances[k] * n)

        c = (c * D) / (Ann * n)
        b = S_prime + (D / Ann)

        # Newton's method to solve y^2 + (b - D) * y - c = 0
        y = D
        for _ in range(32):
            y_prev = y
            den = 2.0 * y + b - D
            if den == 0:
                break
            y = (y * y + c) / den
            if abs(y - y_prev) <= 1e-4:
                return y

        return y

    def swap(self, token_in: str, token_out: str, dx: float) -> Tuple[float, float]:
        """
        Executes a swap on Curve pool:
        Returns: (dy_received, fee_paid)
        """
        i = self.tokens.index(token_in)
        j = self.tokens.index(token_out)

        x_i_new = self.balances[i] + dx
        y_j_new = self.get_y(i, j, x_i_new)

        dy = self.balances[j] - y_j_new
        fee_amount = dy * self.fee
        dy_net = dy - fee_amount

        # Update balances
        self.balances[i] = x_i_new
        self.balances[j] -= dy_net
        return dy_net, fee_amount

    def get_dy(self, token_in: str, token_out: str, dx: float) -> float:
        """Dry-run returns dy_net without state update."""
        i = self.tokens.index(token_in)
        j = self.tokens.index(token_out)
        x_i_new = self.balances[i] + dx
        y_j_new = self.get_y(i, j, x_i_new)
        dy = self.balances[j] - y_j_new
        return dy * (1.0 - self.fee)
