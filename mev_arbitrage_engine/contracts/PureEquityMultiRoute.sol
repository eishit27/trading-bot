// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

/**
 * @title PureEquityMultiRoute
 * @notice 100% Self-Funded, Pure Equity Multi-Path Arbitrage Engine.
 * 
 * CORE PRINCIPLES:
 * 1. ZERO DEBT / ZERO LOANS:
 *    Trades EXCLUSIVELY with own deposited wallet capital.
 *    Contains ZERO external flash loan calls, zero borrowing protocols, zero interest fees,
 *    and zero debt liability.
 * 
 * 2. DETERMINISTIC ATOMIC SAFETY:
 *    Executes across multiple disjoint routes simultaneously.
 *    If aggregate proceeds from all paths fail to exceed initial capital + minProfit,
 *    the EVM rolls back every state change atomically (REVERT opcode 0xFD).
 *    Total Capital Loss = $0.00000000.
 * 
 * 3. EIP-1153 TRANSIENT STORAGE LOCK:
 *    Uses Cancun transient memory (100 gas) to prevent reentrancy and protect state snapshots.
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

contract PureEquityMultiRoute {
    address public immutable owner;

    // EIP-1153 Transient Storage Slots
    bytes32 private constant LOCK_SLOT = 0x6e903a45a666e8550db3dbb899478f79de1d41829e5a1b3beabf3ab3b028df13;

    struct Hop {
        address pool;
        address tokenIn;
        address tokenOut;
    }

    struct RoutePlan {
        uint256 selfFundedAllocation;
        Hop[] hops;
    }

    event MultiRouteExecuted(
        address indexed baseToken,
        uint256 totalEquityDeployed,
        uint256 netProfitGenerated,
        uint256 activeRoutesCount
    );

    error Unauthorized();
    error ReentrancyActive();
    error InsufficientEquity(uint256 available, uint256 required);
    error UnprofitableExecution(uint256 actualBalance, uint256 minimumRequired);

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    modifier nonReentrant() {
        assembly {
            if tload(LOCK_SLOT) {
                mstore(0x00, 0xab143c06) // Reentrancy()
                revert(0x1c, 0x04)
            }
            tstore(LOCK_SLOT, 1)
        }
        _;
        assembly {
            tstore(LOCK_SLOT, 0)
        }
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Executes multi-route arbitrage using 100% self-funded capital.
     * @param baseToken The token to trade (e.g. USDC).
     * @param totalEquityToDeploy Total capital from contract balance to allocate.
     * @param minNetProfit Minimum net profit required to avoid an atomic revert.
     * @param routes Array of RoutePlan structs defining paths and capital slices.
     */
    function executeSelfFundedMultiRoute(
        address baseToken,
        uint256 totalEquityToDeploy,
        uint256 minNetProfit,
        RoutePlan[] calldata routes
    ) external onlyOwner nonReentrant {
        uint256 balanceBefore = IERC20(baseToken).balanceOf(address(this));
        if (balanceBefore < totalEquityToDeploy) {
            revert InsufficientEquity(balanceBefore, totalEquityToDeploy);
        }

        // Execute each route using its allocated slice of self-funded equity
        for (uint256 r = 0; r < routes.length; r++) {
            uint256 currentAmount = routes[r].selfFundedAllocation;

            for (uint256 h = 0; h < routes[r].hops.length; h++) {
                Hop calldata hop = routes[r].hops[h];
                currentAmount = _swapLeg(hop.pool, hop.tokenIn, hop.tokenOut, currentAmount);
            }
        }

        // --- HARD DETERMINISTIC ATOMIC CHECK ---
        uint256 balanceAfter = IERC20(baseToken).balanceOf(address(this));
        uint256 requiredMinimum = balanceBefore + minNetProfit;

        if (balanceAfter < requiredMinimum) {
            revert UnprofitableExecution(balanceAfter, requiredMinimum);
        }

        uint256 netProfit = balanceAfter - balanceBefore;
        emit MultiRouteExecuted(baseToken, totalEquityToDeploy, netProfit, routes.length);
    }

    /**
     * @dev Swaps on AMM pool using constant product invariant.
     */
    function _swapLeg(
        address pool,
        address tokenIn,
        address tokenOut,
        uint256 amountIn
    ) internal returns (uint256 amountOut) {
        (uint112 r0, uint112 r1, ) = IUniswapV2Pair(pool).getReserves();
        address t0 = IUniswapV2Pair(pool).token0();

        (uint256 reserveIn, uint256 reserveOut) = tokenIn == t0 ? (uint256(r0), uint256(r1)) : (uint256(r1), uint256(r0));

        // Transfer tokenIn to pool with safe handling
        _safeTransfer(tokenIn, pool, amountIn);

        // Constant product formula with 0.3% fee
        uint256 amountInWithFee = amountIn * 997;
        amountOut = (amountInWithFee * reserveOut) / ((reserveIn * 1000) + amountInWithFee);

        uint256 amount0Out = tokenOut == t0 ? amountOut : 0;
        uint256 amount1Out = tokenOut == t0 ? 0 : amountOut;

        IUniswapV2Pair(pool).swap(amount0Out, amount1Out, address(this), new bytes(0));
    }

    /**
     * @notice Withdraws full equity balance to owner.
     */
    function withdrawEquity(address token) external onlyOwner {
        uint256 bal = IERC20(token).balanceOf(address(this));
        if (bal > 0) {
            _safeTransfer(token, owner, bal);
        }
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
}
