"""
Gas Asymmetry & Tip Density Bidding Optimizer.

Mathematical Framework:
Block builders (Flashbots, Titan, Beaver) rank bundles by Effective Tip per Gas:
    PriorityScore = Bribe / GasUsed

If Competitor A uses standard Solidity:
    Gas_A = 150,000
    If Gross Profit is V, and Competitor A bids 90% of V:
    Bribe_A = 0.90 * V
    Score_A = (0.90 * V) / 150,000

Our Engine (Optimized Yul Assembly + EIP-1153):
    Gas_Our = 81,200  (45.9% less gas!)

To WIN the block, our Score must satisfy:
    Score_Our > Score_A
    Bribe_Our / Gas_Our > Bribe_A / Gas_A
    Bribe_Our > Bribe_A * (Gas_Our / Gas_A)
    Bribe_Our > (0.90 * V) * (81,200 / 150,000) = 0.487 * V

THE ASYMMETRY ALPHA:
Our bot only needs to bid 49% of V to BEAT the competitor's 90% bid!
Instead of keeping 10% ($0.80), we keep 51% ($5.10) while still WINNING the block!
"""

from typing import Dict, Tuple


class TipDensityOptimizer:
    def __init__(self, our_gas_consumed: int = 81_200, competitor_gas_consumed: int = 150_000):
        self.our_gas = our_gas_consumed
        self.comp_gas = competitor_gas_consumed
        self.gas_advantage_ratio = our_gas_consumed / float(competitor_gas_consumed)

    def calculate_winning_asymmetric_bid(
        self,
        gross_profit_usd: float,
        competitor_bribe_pct: float = 0.90
    ) -> Dict[str, float]:
        """
        Calculates the exact minimal bid needed to out-rank a 90% competitor bid.
        """
        if gross_profit_usd <= 0:
            return {"our_bribe": 0.0, "our_retained": 0.0, "retained_pct": 0.0}

        comp_bribe = gross_profit_usd * competitor_bribe_pct
        comp_priority_score = comp_bribe / self.comp_gas

        # Minimal bribe to beat competitor priority score by 1% margin
        our_winning_bribe = (comp_priority_score * self.our_gas) * 1.01

        # Safety cap: never bid more than 92% of gross profit
        our_winning_bribe = min(our_winning_bribe, gross_profit_usd * 0.92)

        our_retained_profit = gross_profit_usd - our_winning_bribe
        our_retained_pct = (our_retained_profit / gross_profit_usd) * 100.0

        comp_retained = gross_profit_usd - comp_bribe

        return {
            "gross_profit_usd": gross_profit_usd,
            "competitor_bribe": comp_bribe,
            "competitor_retained": comp_retained,
            "our_winning_bribe": our_winning_bribe,
            "our_retained_profit": our_retained_profit,
            "our_retained_pct": our_retained_pct,
            "alpha_multiplier": our_retained_profit / comp_retained if comp_retained > 0 else 1.0
        }
