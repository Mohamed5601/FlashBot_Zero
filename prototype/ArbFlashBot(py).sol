// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ISwapRouter {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }
    function exactInputSingle(ExactInputSingleParams calldata params) external payable returns (uint256 amountOut);
}

interface IUniswapV3Pool {
    function flash(address recipient, uint256 amount0, uint256 amount1, bytes calldata data) external;
}

interface IERC20 {
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
}

contract ArbFlashBot {
    address public owner;
    
    // ✅ تم التحديث: عنوان الراوتر الرسمي لـ Uniswap V3 على شبكة Base
    address constant ROUTER = 0x2626664c2603336E57B271c5C0b26F421741e481;

    constructor() {
        owner = msg.sender;
    }

    struct TriangleParams {
        address tokenA; address tokenB; address tokenC;
        uint24 fee1; uint24 fee2; uint24 fee3;
        uint256 loanAmount;
        uint256 minProfit;
    }

    function checkAndShoot(
        address poolAddress, 
        address tokenA, address tokenB, address tokenC, 
        uint24 fee1, uint24 fee2, uint24 fee3, 
        uint256 loanAmount,
        uint256 minProfit
    ) external {
        require(msg.sender == owner, "Owner only");

        TriangleParams memory params = TriangleParams({
            tokenA: tokenA, tokenB: tokenB, tokenC: tokenC,
            fee1: fee1, fee2: fee2, fee3: fee3,
            loanAmount: loanAmount,
            minProfit: minProfit
        });

        bytes memory data = abi.encode(params);
        IUniswapV3Pool(poolAddress).flash(address(this), loanAmount, 0, data);
    }

    function uniswapV3FlashCallback(uint256 fee0, uint256 fee1, bytes calldata data) external {
        TriangleParams memory params = abi.decode(data, (TriangleParams));
        uint256 amountOwed = params.loanAmount + fee0 + fee1;

        IERC20(params.tokenA).approve(ROUTER, params.loanAmount);

        // 1. Swap A -> B
        uint256 amountOutB = ISwapRouter(ROUTER).exactInputSingle(ISwapRouter.ExactInputSingleParams({
            tokenIn: params.tokenA, tokenOut: params.tokenB, fee: params.fee1,
            recipient: address(this), deadline: block.timestamp,
            amountIn: params.loanAmount, amountOutMinimum: 0, sqrtPriceLimitX96: 0
        }));

        // 2. Swap B -> C
        IERC20(params.tokenB).approve(ROUTER, amountOutB);
        uint256 amountOutC = ISwapRouter(ROUTER).exactInputSingle(ISwapRouter.ExactInputSingleParams({
            tokenIn: params.tokenB, tokenOut: params.tokenC, fee: params.fee2,
            recipient: address(this), deadline: block.timestamp,
            amountIn: amountOutB, amountOutMinimum: 0, sqrtPriceLimitX96: 0
        }));

        // 3. Swap C -> A
        IERC20(params.tokenC).approve(ROUTER, amountOutC);
        uint256 amountFinalA = ISwapRouter(ROUTER).exactInputSingle(ISwapRouter.ExactInputSingleParams({
            tokenIn: params.tokenC, tokenOut: params.tokenA, fee: params.fee3,
            recipient: address(this), deadline: block.timestamp,
            amountIn: amountOutC, amountOutMinimum: 0, sqrtPriceLimitX96: 0
        }));

        // الحماية
        require(amountFinalA >= amountOwed + params.minProfit, "Not enough profit on-chain!");

        // السداد
        IERC20(params.tokenA).transfer(msg.sender, amountOwed);

        // الربح
        uint256 profit = IERC20(params.tokenA).balanceOf(address(this));
        if (profit > 0) IERC20(params.tokenA).transfer(owner, profit);
    }
}