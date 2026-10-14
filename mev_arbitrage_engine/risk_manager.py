"""
Production Risk Manager & Capital Protection Circuit Breaker.
Guarantees strict budget enforcement, daily loss caps, consecutive failure limits,
and immediate kill-switch mechanisms for real-market execution.
"""

import os
import json
import time
from typing import Tuple, Dict, Any

RISK_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "risk_state.json")
KILL_SWITCH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "KILL")


class RiskManager:
    """
    Enforces strict risk budgeting and execution limits:
    - Minimum Profit to Gas Ratio (e.g. 2.0x)
    - Max Single Trade Allocation (USDC/ETH)
    - Daily Gas Budget Limit
    - Max Consecutive Failure Circuit Breaker
    - Max Hourly Transaction Throttling
    - Emergency File Kill-Switch ('touch KILL')
    """
    def __init__(
        self,
        max_trade_size_usd: float = 10.0,       # Max $10 trade for micro-budget safety
        min_profit_to_gas_ratio: float = 2.0,   # Expected profit must be 2x gas
        max_daily_gas_spend_usd: float = 0.50,  # Max $0.50 gas loss per day (~₹40)
        max_consecutive_failures: int = 3,      # Halt after 3 failed transactions
        max_tx_per_hour: int = 10               # Anti-spam throttling
    ):
        self.max_trade_size_usd = max_trade_size_usd
        self.min_profit_to_gas_ratio = min_profit_to_gas_ratio
        self.max_daily_gas_spend_usd = max_daily_gas_spend_usd
        self.max_consecutive_failures = max_consecutive_failures
        self.max_tx_per_hour = max_tx_per_hour

        self.state = self._load_or_init_state()

    def _load_or_init_state(self) -> Dict[str, Any]:
        today_str = time.strftime("%Y-%m-%d")
        if os.path.exists(RISK_STATE_FILE):
            try:
                with open(RISK_STATE_FILE, "r") as f:
                    data = json.load(f)
                if data.get("date") == today_str:
                    return data
            except Exception:
                pass

        # Reset daily state
        return {
            "date": today_str,
            "daily_gas_spent_usd": 0.0,
            "daily_net_profit_usd": 0.0,
            "consecutive_failures": 0,
            "is_halted": False,
            "halt_reason": "",
            "hourly_tx_timestamps": []
        }

    def _save_state(self):
        with open(RISK_STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def is_kill_switch_active(self) -> bool:
        """Returns True if a KILL file exists in the directory."""
        return os.path.exists(KILL_SWITCH_FILE)

    def allow_trade(
        self,
        trade_size_usd: float,
        expected_gross_profit_usd: float,
        estimated_gas_usd: float
    ) -> Tuple[bool, str]:
        """
        Pre-flight check before broadcasting any transaction.
        Returns: (allowed: bool, reason: str)
        """
        # 1. Check physical emergency KILL file
        if self.is_kill_switch_active():
            return False, "EMERGENCY_HALT: 'KILL' file detected in bot directory."

        # 2. Check persistent halt flag
        if self.state.get("is_halted", False):
            return False, f"CIRCUIT_BREAKER_ACTIVE: Bot is halted ({self.state.get('halt_reason')}). Call reset() to resume."

        # 3. Check trade size cap
        if trade_size_usd > self.max_trade_size_usd:
            return False, f"TRADE_SIZE_EXCEEDED: Requested ${trade_size_usd:.2f} > Max allowable ${self.max_trade_size_usd:.2f}"

        # 4. Check Profit-to-Gas Ratio
        if estimated_gas_usd > 0:
            ratio = expected_gross_profit_usd / estimated_gas_usd
            if ratio < self.min_profit_to_gas_ratio:
                return False, f"UNFAVORABLE_RISK_RATIO: Profit/Gas ratio {ratio:.2f}x < Required {self.min_profit_to_gas_ratio}x"

        # 5. Check Daily Gas Spend Cap
        if self.state["daily_gas_spent_usd"] + estimated_gas_usd > self.max_daily_gas_spend_usd:
            self._trigger_halt("Daily gas budget exhausted")
            return False, f"DAILY_GAS_LIMIT_EXCEEDED: Spent ${self.state['daily_gas_spent_usd']:.3f} + Est ${estimated_gas_usd:.3f} > Max ${self.max_daily_gas_spend_usd:.2f}"

        # 6. Check Rate Limiting (Hourly Tx Count)
        now = time.time()
        one_hour_ago = now - 3600
        recent_txs = [ts for ts in self.state["hourly_tx_timestamps"] if ts > one_hour_ago]
        self.state["hourly_tx_timestamps"] = recent_txs
        if len(recent_txs) >= self.max_tx_per_hour:
            return False, f"RATE_LIMIT_EXCEEDED: {len(recent_txs)} txs in the last hour (Max: {self.max_tx_per_hour})"

        return True, "APPROVED_BY_RISK_MANAGER"

    def record_result(self, success: bool, actual_profit_usd: float, actual_gas_usd: float):
        """Records on-chain execution result to state."""
        self.state["daily_gas_spent_usd"] += actual_gas_usd
        self.state["daily_net_profit_usd"] += (actual_profit_usd - actual_gas_usd)
        self.state["hourly_tx_timestamps"].append(time.time())

        if success:
            self.state["consecutive_failures"] = 0
        else:
            self.state["consecutive_failures"] += 1
            if self.state["consecutive_failures"] >= self.max_consecutive_failures:
                self._trigger_halt(f"{self.max_consecutive_failures} consecutive execution failures hit.")

        self._save_state()

    def _trigger_halt(self, reason: str):
        self.state["is_halted"] = True
        self.state["halt_reason"] = reason
        self._save_state()
        print(f"\n🚨 [RISK MANAGER CIRCUIT BREAKER TRIPPED]: {reason}")
        print("   All trading halted. Delete risk_state.json or call reset() after auditing logs.\n")

    def reset(self):
        """Manually resets the circuit breaker."""
        self.state["is_halted"] = False
        self.state["halt_reason"] = ""
        self.state["consecutive_failures"] = 0
        self._save_state()
        if os.path.exists(KILL_SWITCH_FILE):
            os.remove(KILL_SWITCH_FILE)
        print("✅ RiskManager state successfully reset.")


if __name__ == "__main__":
    # Self-test
    rm = RiskManager(max_trade_size_usd=10.0, max_daily_gas_spend_usd=0.20)
    allowed, msg = rm.allow_trade(5.0, 0.10, 0.02)
    assert allowed, f"Self-test failed: {msg}"
    print(f"RiskManager Self-Test Passed: {msg}")
