#!/usr/bin/env python3
"""
Automated Contract Compiler for Phoenix Quanta MEV Engine.
Compiles all Solidity contracts to EVM Cancun bytecode and extracts ABIs.
"""

import os
import sys
import json
import solcx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTRACTS_DIR = os.path.join(BASE_DIR, "contracts")
BUILD_DIR = os.path.join(BASE_DIR, "build")

CONTRACT_FILES = [
    "PureEquityMultiRoute.sol",
    "OptimizedArbitrageYul.sol",
    "AtomicArbitrage.sol"
]


def compile_all():
    os.makedirs(BUILD_DIR, exist_ok=True)
    solcx_version = "0.8.25"

    installed = [str(v) for v in solcx.get_installed_solc_versions()]
    if solcx_version not in installed:
        print(f"📦 Installing solc {solcx_version}...")
        solcx.install_solc(solcx_version)

    print(f"🔨 Compiling contracts with solc {solcx_version} (EVM Cancun / 1,000,000 runs)...")

    results = {}
    for filename in CONTRACT_FILES:
        filepath = os.path.join(CONTRACTS_DIR, filename)
        if not os.path.exists(filepath):
            print(f"⚠️ Warning: File not found: {filepath}")
            continue

        compiled = solcx.compile_files(
            [filepath],
            solc_version=solcx_version,
            evm_version="cancun",
            optimize=True,
            optimize_runs=1000000
        )

        for contract_id, data in compiled.items():
            name = contract_id.split(":")[-1]
            bytecode = data.get("bin", "")
            abi = data.get("abi", [])

            if not bytecode:
                continue

            artifact = {
                "contractName": name,
                "source": filename,
                "evmVersion": "cancun",
                "solcVersion": solcx_version,
                "bytecode": "0x" + bytecode,
                "abi": abi
            }

            out_path = os.path.join(BUILD_DIR, f"{name}.json")
            with open(out_path, "w") as f:
                json.dump(artifact, f, indent=2)

            results[name] = {
                "artifact_path": out_path,
                "bytecode_bytes": len(bytes.fromhex(bytecode))
            }

            print(f"  ✅ {name:<25} -> {len(bytes.fromhex(bytecode)):>5,} bytes ({out_path})")

    print("\n🎉 Compilation complete. Artifacts saved in `mev_arbitrage_engine/build/`.")
    return results


if __name__ == "__main__":
    compile_all()
