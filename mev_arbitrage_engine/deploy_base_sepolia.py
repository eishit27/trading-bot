#!/usr/bin/env python3
"""
Automated Base Sepolia Contract Deployer (Chain ID: 84532).
Deploys PureEquityMultiRoute and OptimizedArbitrageYul to live testnet.
"""

import os
import sys
import json
import time
from eth_account import Account
from web3 import Web3
from hexbytes import HexBytes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(BASE_DIR, "build")
DEPLOYED_FILE = os.path.join(BASE_DIR, "deployed_addresses.json")
RPC_URL = "https://sepolia.base.org"

sys.path.append(BASE_DIR)
from testnet_wallet import get_or_create_wallet
from compile_contracts import compile_all


def deploy_contract(w3: Web3, account: Account, artifact_name: str) -> dict:
    artifact_path = os.path.join(BUILD_DIR, f"{artifact_name}.json")
    if not os.path.exists(artifact_path):
        print(f"Artifact {artifact_name}.json missing, compiling now...")
        compile_all()

    with open(artifact_path, "r") as f:
        artifact = json.load(f)

    bytecode = artifact["bytecode"]
    abi = artifact["abi"]

    print(f"\n🚀 Deploying {artifact_name}...")
    print(f"   Bytecode Size: {len(bytes.fromhex(bytecode[2:])):,} bytes")

    # Estimate gas and prepare EIP-1559 tx
    nonce = w3.eth.get_transaction_count(account.address, "pending")
    base_fee = w3.eth.get_block("latest").get("baseFeePerGas", 1000000)
    priority_fee = w3.to_wei(0.005, "gwei")
    max_fee = int(base_fee * 1.5) + priority_fee

    contract_factory = w3.eth.contract(abi=abi, bytecode=bytecode)
    deploy_tx_data = contract_factory.constructor().build_transaction({
        "from": account.address,
        "nonce": nonce,
        "chainId": 84532,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": priority_fee,
        "value": 0
    })

    # Estimate gas with safety margin
    try:
        gas_est = w3.eth.estimate_gas(deploy_tx_data)
        deploy_tx_data["gas"] = int(gas_est * 1.25)
    except Exception as e:
        deploy_tx_data["gas"] = 2_500_000

    signed_tx = account.sign_transaction(deploy_tx_data)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    tx_hash_hex = tx_hash.hex()
    print(f"   📡 TX Broadcast: https://sepolia.basescan.org/tx/{tx_hash_hex}")
    print(f"   ⏳ Waiting for block confirmation on Base Sepolia...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120, poll_latency=2)
    contract_address = receipt.contractAddress

    status = "SUCCESS" if receipt.status == 1 else "FAILED"
    print(f"   ✅ Contract Deployed [{status}]: {contract_address}")
    print(f"   🔍 BaseScan Link: https://sepolia.basescan.org/address/{contract_address}")
    print(f"   ⛽ Gas Used: {receipt.gasUsed:,} units (Effective Gas Price: {receipt.effectiveGasPrice / 1e9:.4f} Gwei)")

    return {
        "contractName": artifact_name,
        "contractAddress": contract_address,
        "deploymentTxHash": tx_hash_hex,
        "blockNumber": receipt.blockNumber,
        "gasUsed": receipt.gasUsed,
        "deployedAt": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "network": "Base Sepolia Testnet",
        "chainId": 84532
    }


def main():
    w = get_or_create_wallet()
    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"headers": {"User-Agent": "Mozilla/5.0"}}))

    print("=" * 80)
    print("  🚀 BASE SEPOLIA TESTNET CONTRACT DEPLOYMENT ENGINE")
    print("=" * 80)
    print(f"  • Network:        Base Sepolia (Chain ID: 84532)")
    print(f"  • Deployer:       {w['address']}")
    print(f"  • Wallet Balance: {w['balance_eth']:.6f} ETH")

    if not w["is_funded"]:
        print("\n" + "=" * 80)
        print("  ⚠️ WALLET HAS 0 ETH ON BASE SEPOLIA")
        print("=" * 80)
        print("  Gas is required to register contracts on the real blockchain.")
        print("  Claim 100% free testnet ETH (0.001 ETH is plenty):")
        print("  1. Coinbase Faucet: https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet")
        print("  2. Superchain Faucet: https://console.optimism.io/faucet")
        print("  3. Chainlink Faucet:  https://faucets.chain.link/base-sepolia")
        print(f"\n  👉 Paste Address: {w['address']}")
        print("=" * 80 + "\n")
        sys.exit(1)

    account = Account.from_key(w["private_key"])
    deployed_records = {}

    if os.path.exists(DEPLOYED_FILE):
        try:
            with open(DEPLOYED_FILE, "r") as f:
                deployed_records = json.load(f)
        except Exception:
            pass

    # 1. Deploy PureEquityMultiRoute
    res_multi = deploy_contract(w3, account, "PureEquityMultiRoute")
    deployed_records["PureEquityMultiRoute"] = res_multi

    # 2. Deploy OptimizedArbitrageYul
    res_yul = deploy_contract(w3, account, "OptimizedArbitrageYul")
    deployed_records["OptimizedArbitrageYul"] = res_yul

    with open(DEPLOYED_FILE, "w") as f:
        json.dump(deployed_records, f, indent=2)

    print("\n" + "=" * 80)
    print("  🎉 DEPLOYMENT COMPLETED & RECORDED")
    print("=" * 80)
    print(f"  • PureEquityMultiRoute:  {res_multi['contractAddress']}")
    print(f"  • OptimizedArbitrageYul: {res_yul['contractAddress']}")
    print(f"  • Records saved to:      {DEPLOYED_FILE}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
