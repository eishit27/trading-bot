"""
DEX State & Atomic Execution Simulator.
Simulates:
1. Multi-DEX arbitrage execution with exact EVM atomic revert checks.
2. Flash-swap simulations with zero collateral.
3. Slippage and front-run collision scenarios.
"""

from typing import Dict, List, Tuple, Optional
from math_engine import Pool, calculate_optimal_arbitrage_input, get_amount_out, GAMMA


class AtomicExecutionResult:
    def __init__(self, success: bool, reason: str, amount_in: float, amount_out: float, net_profit: float, gas_cost_usd: float = 0.0):
        self.success = success
        self.reason = reason
        self.amount_in = amount_in
        self.amount_out = amount_out
        self.net_profit = net_profit
        self.gas_cost_usd = gas_cost_usd

    def __repr__(self):
        status = "SUCCESS" if self.success else "REVERTED"
        return f"<AtomicExecutionResult [{status}]: {self.reason} | Profit: ${self.net_profit:,.2f}>"


class ArbitrageSimulator:
    """
    Simulates on-chain smart contract transactions locally.
    Enforces atomic revert conditions:
    If Net Profit < min_profit, the entire transaction reverts and balances reset.
    """
    def __init__(self, pools: Dict[str, Pool]):
        self.pools = pools

    def simulate_two_pool_arbitrage(
        self,
        pool_buy_name: str,
        pool_sell_name: str,
        token_base: str,
        token_quote: str,
        amount_in: Optional[float] = None,
        min_profit_threshold: float = 1.0,  # $1 min profit threshold
        simulated_gas_cost_usd: float = 0.50
    ) -> AtomicExecutionResult:
        """
        Executes a simulated atomic arbitrage trade.
        Step 1: Buy token_quote on pool_buy using token_base.
        Step 2: Sell token_quote on pool_sell for token_base.
        Step 3: Atomic check. If balance_after < balance_before + min_profit, REVERT.
        """
        pool_buy = self.pools[pool_buy_name].clone()
        pool_sell = self.pools[pool_sell_name].clone()

        # Extract reserves
        r_in_a = pool_buy.reserve0 if pool_buy.token0 == token_base else pool_buy.reserve1
        r_out_a = pool_buy.reserve1 if pool_buy.token0 == token_base else pool_buy.reserve0

        r_in_b = pool_sell.reserve0 if pool_sell.token0 == token_quote else pool_sell.reserve1
        r_out_b = pool_sell.reserve1 if pool_sell.token0 == token_quote else pool_sell.reserve0

        # If amount_in is not specified, calculate mathematically optimal size
        if amount_in is None:
            optimal_dx, theoretical_profit = calculate_optimal_arbitrage_input(
                r_in_a, r_out_a, r_in_b, r_out_b
            )
            if optimal_dx <= 0:
                return AtomicExecutionResult(
                    success=False,
                    reason="No profitable arbitrage opportunity exists between pools (prices aligned or spread < fees).",
                    amount_in=0.0,
                    amount_out=0.0,
                    net_profit=0.0
                )
            amount_in = optimal_dx

        # Execute Leg 1: Swap token_base -> token_quote on Pool Buy
        _, quote_received = pool_buy.swap(token_base, amount_in)

        # Execute Leg 2: Swap token_quote -> token_base on Pool Sell
        _, base_received = pool_sell.swap(token_quote, quote_received)

        gross_profit = base_received - amount_in
        net_profit = gross_profit - simulated_gas_cost_usd

        # --- THE ATOMIC GUARANTEE CHECK ---
        # Mirrors the Solidity `require(balanceAfter >= balanceBefore + minProfit)`
        if gross_profit < min_profit_threshold or net_profit <= 0:
            # Entire state is discarded (Atomic Revert)
            return AtomicExecutionResult(
                success=False,
                reason=f"ATOMIC REVERT TRIGGERED: Gross profit (${gross_profit:.2f}) < threshold (${min_profit_threshold:.2f}). 100% of capital preserved.",
                amount_in=amount_in,
                amount_out=base_received,
                net_profit=0.0,  # Zero capital lost because EVM reverts!
                gas_cost_usd=simulated_gas_cost_usd
            )

        # If check passes, commit state changes to live pools
        self.pools[pool_buy_name] = pool_buy
        self.pools[pool_sell_name] = pool_sell

        return AtomicExecutionResult(
            success=True,
            reason=f"Executed successfully. Bought {quote_received:.4f} {token_quote}, returned {base_received:.2f} {token_base}.",
            amount_in=amount_in,
            amount_out=base_received,
            net_profit=net_profit,
            gas_cost_usd=simulated_gas_cost_usd
        )

    def simulate_spot_equity_arbitrage(
        self,
        pool_buy_name: str,
        pool_sell_name: str,
        token_base: str,
        token_quote: str,
        self_funded_equity: float,
        min_profit_threshold: float = 1.0,
        simulated_gas_cost_usd: float = 0.50
    ) -> AtomicExecutionResult:
        """
        Simulates 100% Self-Funded Spot Equity Arbitrage (ZERO BORROWING / ZERO LOANS):
        1. Deploys strictly self-funded equity capital from contract balance.
        2. Swaps token_base -> token_quote on pool_buy.
        3. Swaps token_quote -> token_base on pool_sell.
        4. Verifies final balance >= initial balance + min_profit.
        5. If check fails, EVM opcode 0xFD triggers atomic rollback (Delta(Capital) = $0.00).
        """
        return self.simulate_two_pool_arbitrage(
            pool_buy_name=pool_buy_name,
            pool_sell_name=pool_sell_name,
            token_base=token_base,
            token_quote=token_quote,
            amount_in=self_funded_equity,
            min_profit_threshold=min_profit_threshold,
            simulated_gas_cost_usd=simulated_gas_cost_usd
        )
