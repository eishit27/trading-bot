"""
Centralized Configuration for Phoenix Quanta MEV Arbitrage Engine.
All system-wide tunables, endpoints, protocol parameters, and token maps.
"""

import os
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass(frozen=True)
class ChainConfig:
    chain_id: int
    name: str
    rpc_urls: List[str]
    default_gas_gwei: float
    typical_block_time_s: float
    is_l2: bool
    sequencer_fee_usd: float = 0.01


# Global Supported Networks
CHAINS: Dict[str, ChainConfig] = {
    "BASE_L2": ChainConfig(
        chain_id=8453,
        name="Coinbase Base L2 (FCFS Sequencer)",
        rpc_urls=[
            "https://mainnet.base.org",
            "https://base.llamarpc.com",
            "https://base-rpc.publicnode.com"
        ],
        default_gas_gwei=0.005,
        typical_block_time_s=2.0,
        is_l2=True,
        sequencer_fee_usd=0.01
    ),
    "ETH_MAINNET": ChainConfig(
        chain_id=1,
        name="Ethereum Mainnet (MEV-Boost / Flashbots)",
        rpc_urls=[
            "https://eth.llamarpc.com",
            "https://ethereum-rpc.publicnode.com",
            "https://cloudflare-eth.com"
        ],
        default_gas_gwei=16.0,
        typical_block_time_s=12.0,
        is_l2=False,
        sequencer_fee_usd=0.00
    )
}

# Active Block Builder Relays (Flashbots MEV-Boost)
BUILDER_RELAYS: List[Dict[str, str]] = [
    {"name": "Flashbots",   "url": "https://relay.flashbots.net"},
    {"name": "Titan",       "url": "https://rpc.titanbuilder.xyz"},
    {"name": "BeaverBuild", "url": "https://rpc.beaverbuild.com"},
    {"name": "Builder0x69", "url": "https://builder0x69.io"}
]

# AMM Protocol Parameters
AMM_CONFIG = {
    "UNISWAP_V2_FEE_BPS": 30,         # 0.30%
    "UNISWAP_V2_GAMMA": 0.997,
    "UNISWAP_V3_DEFAULT_FEE_BPS": 5,  # 0.05%
    "CURVE_DEFAULT_FEE_BPS": 4,       # 0.04%
    "CURVE_DEFAULT_A": 100.0,
    "AERODROME_SLIPSTREAM_FEE_BPS": 5
}

# Gas Benchmarks (Asymmetry advantage)
GAS_PROFILE = {
    "YUL_ASSEMBLY_GAS": 81_200,       # OptimizedArbitrageYul.sol
    "STANDARD_SOLIDITY_GAS": 148_500, # Typical competing searcher contract
    "GAS_REDUCTION_PCT": 45.3
}

# Safety & Execution Guardian Defaults
SAFETY_CONFIG = {
    "MIN_PROFIT_THRESHOLD_USD": 0.50,
    "MAX_SLIPPAGE_BPS": 50,           # 0.5% max allowable slippage
    "SIMULATION_TIMEOUT_MS": 15.0,
    "ZERO_DEBT_ENFORCED": True,
    "ZERO_LOSS_ENFORCED": True
}

# Common Verified Token Addresses (Ethereum Mainnet)
ETH_TOKENS = {
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    "DAI":  "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
    "UNI":  "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984"
}

# Common Verified Token Addresses (Base L2)
BASE_TOKENS = {
    "USDC":    "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "WETH":    "0x4200000000000000000000000000000000000006",
    "AERO":    "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
    "cbBTC":   "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
    "VIRTUAL": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b"
}
