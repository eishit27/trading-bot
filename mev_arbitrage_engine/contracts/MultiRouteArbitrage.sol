// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

/**
 * @title MultiRouteArbitrage
 * @notice Multi-Path Batch Arbitrage Aggregator.
 * 
 * ARCHITECTURE:
 * Instead of funneling capital through a single route (which incurs severe slippage),
 * this contract executes MULTIPLE INDEPENDENT ARBITRAGE ROUTES simultaneously
 * within a single atomic Ethereum transaction.
 * 
 * ZERO-LOSS GUARANTEE:
 * Aggregates proceeds from all routes. If total recovered capital < initial capital + minProfit,
 * the entire multi-route bundle REVERTS atomically.
 */

interface IERC20 {
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
}

interface IUniswapV2Pair {
    function token0() external view returns (address);
    function token1() external view returns (address);
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
    function swap(uint256 amount0Out, uint256 amount1Out, address to, bytes calldata data) external;
}

contract MultiRouteArbitrage {
    address public immutable owner;

    struct Hop {
        address pool;
        address tokenIn;
        address tokenOut;
    }

    struct Route {
        uint256 capitalAllocated;
        Hop[] hops;
    }

    event MultiRouteExecuted(
        address indexed baseToken,
        uint256 totalInput,
        uint256 totalOutput,
        uint256 netProfit,
        uint256 routesCount
    );

    error Unauthorized();
    error UnprofitableMultiRoute(uint256 actual, uint256 expected);

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Executes a multi-route batch arbitrage.
     * @param baseToken The token to deploy and retrieve (e.g., USDC).
     * @param totalCapital Total capital required across all routes.
     * @param minTotalProfit Minimum aggregate profit threshold required to prevent revert.
     * @param routes Array of Route structs, each containing allocated capital and hop sequence.
     */
    function executeMultiRouteArbitrage(
        address baseToken,
        uint256 totalCapital,
        uint256 minTotalProfit,
        Route[] calldata routes
    ) external onlyOwner {
        uint256 balanceBefore = IERC20(baseToken).balanceOf(address(this));
        require(balanceBefore >= totalCapital, "Insufficient contract balance");

        // Execute each route independently using its allocated capital slice
        for (uint256 r = 0; r < routes.length; r++) {
            uint256 currentAmount = routes[r].capitalAllocated;

            for (uint256 h = 0; h < routes[r].hops.length; h++) {
                Hop calldata hop = routes[r].hops[h];
                currentAmount = _executeSwap(hop.pool, hop.tokenIn, hop.tokenOut, currentAmount);
            }
        }

        // --- GLOBAL ATOMIC CHECK ---
        uint256 balanceAfter = IERC20(baseToken).balanceOf(address(this));
        uint256 requiredMinimum = balanceBefore + minTotalProfit;

        if (balanceAfter < requiredMinimum) {
            revert UnprofitableMultiRoute(balanceAfter, requiredMinimum);
        }

        uint256 netProfit = balanceAfter - balanceBefore;
        emit MultiRouteExecuted(baseToken, totalCapital, balanceAfter, netProfit, routes.length);
    }

    /**
     * @dev Internal swap helper.
     */
    function _executeSwap(
        address pool,
        address tokenIn,
        address tokenOut,
        uint256 amountIn
    ) internal returns (uint256 amountOut) {
        (uint112 r0, uint112 r1, ) = IUniswapV2Pair(pool).getReserves();
        address t0 = IUniswapV2Pair(pool).token0();

        (uint256 reserveIn, uint256 reserveOut) = tokenIn == t0 ? (uint256(r0), uint256(r1)) : (uint256(r1), uint256(r0));

        // Transfer tokenIn to pool
        IERC20(tokenIn).transfer(pool, amountIn);

        // Constant product formula with 0.3% fee
        uint256 amountInWithFee = amountIn * 997;
        amountOut = (amountInWithFee * reserveOut) / ((reserveIn * 1000) + amountInWithFee);

        uint256 amount0Out = tokenOut == t0 ? amountOut : 0;
        uint256 amount1Out = tokenOut == t0 ? 0 : amountOut;

        IUniswapV2Pair(pool).swap(amount0Out, amount1Out, address(this), new bytes(0));
    }

    /**
     * @notice Withdraw funds to owner.
     */
    function withdraw(address token) external onlyOwner {
        uint256 bal = IERC20(token).balanceOf(address(this));
        if (bal > 0) {
            IERC20(token).transfer(owner, bal);
        }
    }
}
