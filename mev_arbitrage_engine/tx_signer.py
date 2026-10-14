"""
Cryptographic Transaction Signer & EIP-1559 RLP Encoder.

Handles:
1. Secp256k1 ECDSA private key transaction signing via eth_account.
2. Dynamic EIP-1559 gas fee estimation (maxFeePerGas, maxPriorityFeePerGas).
3. Calldata packing for OptimizedArbitrageYul.sol.
4. Nonce tracking and raw transaction serialization.
"""

from typing import Dict, Any, List
from eth_account import Account
from eth_account.signers.local import LocalAccount
from hexbytes import HexBytes
from web3 import Web3
import eth_abi


class TransactionSigner:
    def __init__(self, private_key_hex: str, chain_id: int = 1):
        """
        chain_id: 1 for Ethereum Mainnet, 8453 for Base, 42161 for Arbitrum.
        """
        self.account: LocalAccount = Account.from_key(private_key_hex)
        self.address = self.account.address
        self.chain_id = chain_id
        self.nonce = 0

    def sync_nonce(self, w3: Web3):
        """Fetches pending transaction count from RPC node."""
        self.nonce = w3.eth.get_transaction_count(self.address, "pending")

    def encode_yul_arbitrage_calldata(
        self,
        base_token: str,
        amount_in_wei: int,
        min_profit_wei: int,
        hops: List[Dict[str, str]]
    ) -> bytes:
        """
        Packs calldata for OptimizedArbitrageYul.executeCyclicArbitrage:
        Function selector: executeCyclicArbitrage(address,uint256,uint256,bytes) -> 0x8b5be682
        Hops: packed binary sequence of [poolAddress (32 bytes)][tokenIn (32 bytes)]
        """
        # Selector for executeCyclicArbitrage(address,uint256,uint256,bytes)
        selector = Web3.keccak(text="executeCyclicArbitrage(address,uint256,uint256,bytes)")[:4]

        # Pack hops bytes
        hops_bytes = bytearray()
        for h in hops:
            pool_addr = bytes.fromhex(h["pool"].replace("0x", "")).rjust(32, b'\x00')
            token_in = bytes.fromhex(h["token_in"].replace("0x", "")).rjust(32, b'\x00')
            hops_bytes.extend(pool_addr)
            hops_bytes.extend(token_in)

        # ABI encode arguments directly via eth_abi (high performance)
        encoded_args = eth_abi.encode(
            ["address", "uint256", "uint256", "bytes"],
            [Web3.to_checksum_address(base_token), amount_in_wei, min_profit_wei, bytes(hops_bytes)]
        )

        return selector + encoded_args

    def sign_eip1559_transaction(
        self,
        to_address: str,
        data: bytes,
        max_fee_per_gas_gwei: float,
        max_priority_fee_per_gas_gwei: float,
        gas_limit: int = 150_000,
        value_wei: int = 0
    ) -> Dict[str, Any]:
        """
        Constructs and signs a Type-2 (EIP-1559) Ethereum transaction.
        Returns: { 'raw_tx_hex': str, 'tx_hash': str }
        """
        max_fee_wei = Web3.to_wei(max_fee_per_gas_gwei, 'gwei')
        priority_fee_wei = Web3.to_wei(max_priority_fee_per_gas_gwei, 'gwei')

        tx_dict = {
            "type": 2,  # EIP-1559
            "chainId": self.chain_id,
            "nonce": self.nonce,
            "to": Web3.to_checksum_address(to_address),
            "value": value_wei,
            "gas": gas_limit,
            "maxFeePerGas": max_fee_wei,
            "maxPriorityFeePerGas": priority_fee_wei,
            "data": HexBytes(data)
        }

        signed_tx = self.account.sign_transaction(tx_dict)
        self.nonce += 1

        return {
            "raw_tx_hex": signed_tx.raw_transaction.hex(),
            "tx_hash": signed_tx.hash.hex(),
            "tx_dict": tx_dict
        }
