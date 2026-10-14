// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AtomicArbitrage
 * @dev Production-standard Atomic MEV Arbitrage Contract.
 * Operating Principle: 100% SELF-FUNDED SPOT EQUITY (ZERO-DEBT / ZERO-LOAN).
 * 
 * CORE GUARANTEE:
 * Atomicity via the EVM `require` statement. If final proceeds are less than
 * initial capital + minimum expected profit, the entire transaction REVERTS (0xFD).
 * No funds can ever be lost to an unprofitable execution.
 * Zero borrowing, zero flash loans, zero debt liabilities.
 */

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}

interface IUniswapV2Pair {
    function token0() external view returns (address);
    function token1() external view returns (address);
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
    function swap(uint256 amount0Out, uint256 amount1Out, address to, bytes calldata data) external;
}

contract AtomicArbitrage {
    address public immutable owner;

    // Events for off-chain searcher telemetry
    event ArbitrageSuccess(
        address indexed token,
        uint256 amountIn,
        uint256 amountOut,
        uint256 netProfit
    );
    event EmergencyWithdraw(address indexed token, uint256 amount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Unauthorized: Not contract owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Executes atomic direct arbitrage across two UniswapV2-compatible pools using 100% self-funded spot equity.
     * @param tokenA The starting/ending asset (e.g., USDC or WETH).
     * @param tokenB The intermediate asset.
     * @param poolBuy The pool where tokenB is cheaper relative to tokenA.
     * @param poolSell The pool where tokenB is more expensive relative to tokenA.
     * @param amountIn Exact input amount of tokenA from self-funded balance.
     * @param minProfit Minimum net profit required (enforces atomic safety).
     */
    function executeDirectArbitrage(
        address tokenA,
        address tokenB,
        address poolBuy,
        address poolSell,
        uint256 amountIn,
        uint256 minProfit
    ) external onlyOwner {
        uint256 balanceBefore = IERC20(tokenA).balanceOf(address(this));
        require(balanceBefore >= amountIn, "Insufficient tokenA balance: Self-funded equity required");

        // 1. Calculate amountOut for First Swap (Buy tokenB on poolBuy)
        uint256 tokenBReceived = _swapOnPool(tokenA, tokenB, poolBuy, amountIn);

        // 2. Calculate amountOut for Second Swap (Sell tokenB for tokenA on poolSell)
        uint256 tokenAReceived = _swapOnPool(tokenB, tokenA, poolSell, tokenBReceived);

        // 3. THE ATOMIC CONSTRAINT:
        // Final balance must be at least the starting balance + minimum profit.
        // If not, EVM reverts every state change (all token transfers are undone).
        uint256 balanceAfter = IERC20(tokenA).balanceOf(address(this));
        require(
            balanceAfter >= balanceBefore + minProfit,
            "ATOMIC_REVERT: Arbitrage did not meet minimum profit threshold"
        );

        uint256 netProfit = balanceAfter - balanceBefore;
        emit ArbitrageSuccess(tokenA, amountIn, tokenAReceived, netProfit);
    }

    /**
     * @dev Internal helper to perform a Uniswap V2 pair swap with safe transfer handling.
     */
    function _swapOnPool(
        address tokenIn,
        address tokenOut,
        address pool,
        uint256 amountIn
    ) internal returns (uint256 amountOut) {
        (uint112 reserve0, uint112 reserve1, ) = IUniswapV2Pair(pool).getReserves();
        address token0 = IUniswapV2Pair(pool).token0();

        (uint256 reserveIn, uint256 reserveOut) = tokenIn == token0 
            ? (uint256(reserve0), uint256(reserve1)) 
            : (uint256(reserve1), uint256(reserve0));

        // Uniswap V2 constant product formula: (amountIn * 997 * reserveOut) / (reserveIn * 1000 + amountIn * 997)
        uint256 amountInWithFee = amountIn * 997;
        uint256 numerator = amountInWithFee * reserveOut;
        uint256 denominator = (reserveIn * 1000) + amountInWithFee;
        amountOut = numerator / denominator;

        // Safe transfer tokenIn to pool
        _safeTransfer(tokenIn, pool, amountIn);

        // Call swap
        uint256 amount0Out = tokenOut == token0 ? amountOut : 0;
        uint256 amount1Out = tokenOut == token0 ? 0 : amountOut;
        IUniswapV2Pair(pool).swap(amount0Out, amount1Out, address(this), new bytes(0));
    }

    /**
     * @dev Low-level safeTransfer handling tokens that do not return a bool (e.g. USDT).
     */
    function _safeTransfer(address token, address to, uint256 value) internal {
        (bool success, bytes memory data) = token.call(
            abi.encodeWithSelector(IERC20.transfer.selector, to, value)
        );
        require(success && (data.length == 0 || abi.decode(data, (bool))), "SafeTransferFailed");
    }

    /**
     * @notice Emergency withdrawal of tokens to owner.
     */
    function withdraw(address token) external onlyOwner {
        uint256 balance = IERC20(token).balanceOf(address(this));
        require(balance > 0, "Zero balance");
        _safeTransfer(token, owner, balance);
        emit EmergencyWithdraw(token, balance);
    }

    receive() external payable {}
}
