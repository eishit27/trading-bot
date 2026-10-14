#!/usr/bin/env python3
"""
Testnet Wallet Manager for Base Sepolia (Chain ID: 84532).
Generates, stores, and audits testnet deployment credentials.
"""

import os
import sys
import json
from eth_account import Account
from web3 import Web3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WALLET_FILE = os.path.join(BASE_DIR, "testnet_wallet.json")
RPC_URL = "https://sepolia.base.org"


def get_or_create_wallet() -> dict:
    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"headers": {"User-Agent": "Mozilla/5.0"}}))

    if os.path.exists(WALLET_FILE):
        with open(WALLET_FILE, "r") as f:
            wallet_data = json.load(f)
        address = wallet_data["address"]
        private_key = wallet_data["private_key"]
    else:
        # Generate new dedicated testnet account
        acct = Account.create()
        address = acct.address
        private_key = acct.key.hex()
        wallet_data = {
            "network": "Base Sepolia Testnet",
            "chain_id": 84532,
            "address": address,
            "private_key": private_key
        }
        with open(WALLET_FILE, "w") as f:
            json.dump(wallet_data, f, indent=2)
        os.chmod(WALLET_FILE, 0o600)  # Secure read/write only for owner

    # Query on-chain balance
    balance_wei = 0
    try:
        balance_wei = w3.eth.get_balance(address)
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch balance from RPC ({e})")

    balance_eth = Web3.from_wei(balance_wei, "ether")

    return {
        "address": address,
        "private_key": private_key,
        "balance_eth": float(balance_eth),
        "balance_wei": balance_wei,
        "is_funded": balance_wei > 0
    }


def main():
    print("=" * 80)
    print("  🔑 BASE SEPOLIA TESTNET WALLET PROFILE")
    print("=" * 80)

    w = get_or_create_wallet()
    print(f"  • Network:          Base Sepolia (Chain ID: 84532)")
    print(f"  • RPC Endpoint:     {RPC_URL}")
    print(f"  • Wallet Address:   {w['address']}")
    print(f"  • Explorer URL:     https://sepolia.basescan.org/address/{w['address']}")
    print(f"  • On-Chain Balance: {w['balance_eth']:.6f} ETH")

    if not w["is_funded"]:
        print("\n" + "-" * 80)
        print("  ⚠️ WALLET NEEDS TESTNET ETH FOR DEPLOYMENT GAS (~0.001 ETH needed)")
        print("-" * 80)
        print("  Claim free Base Sepolia testnet ETH from any of these faucets:")
        print("  1. Coinbase Developer Faucet: https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet")
        print("  2. Superchain Faucet:         https://console.optimism.io/faucet")
        print("  3. Chainlink Faucet:          https://faucets.chain.link/base-sepolia")
        print(f"\n  👉 Paste your address: {w['address']}")
        print("-" * 80)
    else:
        print(f"\n  ✅ Wallet is funded and ready for contract deployment!")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
