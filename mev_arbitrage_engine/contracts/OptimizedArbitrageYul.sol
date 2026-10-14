// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

/**
 * @title OptimizedArbitrageYul
 * @author Quantitative MEV Engineering
 * @notice Ultra-low latency, gas-optimized Arbitrage Execution Engine.
 * 
 * ADVANCED OPTIMIZATIONS IMPLEMENTED:
 * 1. EIP-1153 Transient Storage (TSTORE / TLOAD):
 *    Replaces cold storage SSTORE (2,100 - 20,000 gas) with EVM Cancun transient storage (100 gas)
 *    for reentrancy locking and balance snapshotting.
 * 2. Yul Inline Assembly Execution:
 *    Bypasses Solidity ABI decoding overhead and memory expansion penalties.
 * 3. Atomic Invariant Check:
 *    Guaranteed zero-loss rollback if profit does not meet or exceed minProfit.
 */

contract OptimizedArbitrageYul {
    address public immutable owner;

    // Transient storage slots (EIP-1153)
    bytes32 private constant REENTRANCY_SLOT = 0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103;
    bytes32 private constant INITIAL_BAL_SLOT = 0x8a9bf461d33190df09b552d8e48b8941fc32da1e2d8b5eb659e984fa57f5c504;

    // Custom 4-byte error selector: bytes4(keccak256("UnprofitableArbitrage(uint256,uint256)"))
    // Value: 0xce7a50ef
    error UnprofitableArbitrage(uint256 actualReturn, uint256 expectedMinimum);
    error Unauthorized();
    error Reentrancy();

    event ArbitrageExecuted(address indexed baseToken, uint256 amountIn, uint256 netProfit);

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    modifier nonReentrant() {
        assembly {
            // TLOAD from transient storage slot
            if tload(REENTRANCY_SLOT) {
                // Revert with Reentrancy()
                mstore(0x00, 0xab143c06)
                revert(0x1c, 0x04)
            }
            // TSTORE 1 (locked)
            tstore(REENTRANCY_SLOT, 1)
        }
        _;
        assembly {
            // TSTORE 0 (unlocked)
            tstore(REENTRANCY_SLOT, 0)
        }
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Executes multi-hop cyclic arbitrage using pure Yul assembly.
     * @param baseToken The token we start and finish with (e.g., USDC / WETH).
     * @param amountIn Exact input capital to deploy.
     * @param minProfit Minimum profit threshold required to avoid atomic revert.
     * @param hops Encoded route: array of (pool, tokenIn, tokenOut).
     */
    function executeCyclicArbitrage(
        address baseToken,
        uint256 amountIn,
        uint256 minProfit,
        bytes calldata hops
    ) external onlyOwner nonReentrant {
        uint256 balanceBefore;
        uint256 balanceAfter;

        assembly {
            // 1. Snapshot initial balance using staticcall to IERC20.balanceOf(address(this))
            // Function selector for balanceOf(address): 0x70a08231
            mstore(0x00, 0x70a08231)
            mstore(0x20, address())
            let success := staticcall(gas(), baseToken, 0x1c, 0x24, 0x00, 0x20)
            if iszero(success) { revert(0, 0) }
            balanceBefore := mload(0x00)

            // Ensure contract holds sufficient initial balance
            if lt(balanceBefore, amountIn) { revert(0, 0) }

            // Store in transient storage
            tstore(INITIAL_BAL_SLOT, balanceBefore)

            // 2. Decode hops and execute consecutive swaps
            // hops format: sequence of 64-byte chunks:
            // [0..32: pool address] [32..64: tokenIn address]
            let offset := hops.offset
            let end := add(offset, hops.length)
            let currentAmount := amountIn

            for {} lt(offset, end) { offset := add(offset, 64) } {
                let pool := calldataload(offset)
                let tokenIn := calldataload(add(offset, 32))

                // Transfer currentAmount to pool: IERC20(tokenIn).transfer(pool, currentAmount)
                // selector: 0xa9059cbb
                mstore(0x00, 0xa9059cbb)
                mstore(0x20, pool)
                mstore(0x40, currentAmount)
                let transferSuccess := call(gas(), tokenIn, 0, 0x1c, 0x44, 0x00, 0x20)
                if iszero(transferSuccess) { revert(0, 0) }

                // Query pool reserves to calculate exact output
                // IUniswapV2Pair.getReserves(): selector 0x0902f1ac
                mstore(0x00, 0x0902f1ac)
                let resSuccess := staticcall(gas(), pool, 0x1c, 0x04, 0x00, 0x60)
                if iszero(resSuccess) { revert(0, 0) }
                let r0 := mload(0x00)
                let r1 := mload(0x20)

                // Query token0 to know swap direction
                // token0(): selector 0x0dfe1681
                mstore(0x00, 0x0dfe1681)
                let t0Success := staticcall(gas(), pool, 0x1c, 0x04, 0x00, 0x20)
                if iszero(t0Success) { revert(0, 0) }
                let t0 := mload(0x00)

                let reserveIn := r0
                let reserveOut := r1
                let amount0Out := 0
                let amount1Out := 0

                // If tokenIn == token0, swap token0 -> token1
                if eq(tokenIn, t0) {
                    reserveIn := r0
                    reserveOut := r1
                    // Uniswap AMM formula with 0.3% fee: (dx * 997 * rOut) / (rIn * 1000 + dx * 997)
                    let amountInWithFee := mul(currentAmount, 997)
                    let num := mul(amountInWithFee, reserveOut)
                    let den := add(mul(reserveIn, 1000), amountInWithFee)
                    amount1Out := div(num, den)
                    currentAmount := amount1Out
                }
                // If tokenIn == token1, swap token1 -> token0
                if iszero(eq(tokenIn, t0)) {
                    reserveIn := r1
                    reserveOut := r0
                    let amountInWithFee := mul(currentAmount, 997)
                    let num := mul(amountInWithFee, reserveOut)
                    let den := add(mul(reserveIn, 1000), amountInWithFee)
                    amount0Out := div(num, den)
                    currentAmount := amount0Out
                }

                // Call pool.swap(amount0Out, amount1Out, address(this), "")
                // selector: 0x022c0d9f
                mstore(0x00, 0x022c0d9f)
                mstore(0x20, amount0Out)
                mstore(0x40, amount1Out)
                mstore(0x60, address())
                mstore(0x80, 0x80) // offset to empty bytes
                mstore(0xa0, 0)    // length of empty bytes
                let swapSuccess := call(gas(), pool, 0, 0x1c, 0xa4, 0x00, 0x00)
                if iszero(swapSuccess) { revert(0, 0) }
            }

            // 3. Query final balance
            mstore(0x00, 0x70a08231)
            mstore(0x20, address())
            let balFinalSuccess := staticcall(gas(), baseToken, 0x1c, 0x24, 0x00, 0x20)
            if iszero(balFinalSuccess) { revert(0, 0) }
            balanceAfter := mload(0x00)

            // --- THE ATOMIC REVERT CHECK IN YUL ---
            let requiredMinimum := add(balanceBefore, minProfit)
            if lt(balanceAfter, requiredMinimum) {
                // Revert with UnprofitableArbitrage(balanceAfter, requiredMinimum)
                mstore(0x00, 0xce7a50ef)
                mstore(0x20, balanceAfter)
                mstore(0x40, requiredMinimum)
                revert(0x1c, 0x44)
            }
        }

        uint256 netProfit = balanceAfter - balanceBefore;
        emit ArbitrageExecuted(baseToken, amountIn, netProfit);
    }

    /**
     * @notice Withdraw profits to owner.
     */
    function withdraw(address token) external onlyOwner {
        assembly {
            mstore(0x00, 0x70a08231)
            mstore(0x20, address())
            let success := staticcall(gas(), token, 0x1c, 0x24, 0x00, 0x20)
            if iszero(success) { revert(0, 0) }
            let bal := mload(0x00)

            if gt(bal, 0) {
                // IERC20.transfer(owner, bal)
                mstore(0x00, 0xa9059cbb)
                mstore(0x20, caller())
                mstore(0x40, bal)
                let transferSuccess := call(gas(), token, 0, 0x1c, 0x44, 0x00, 0x20)
                if iszero(transferSuccess) { revert(0, 0) }
            }
        }
    }
}
