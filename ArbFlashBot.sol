// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IBalancerVault {
    function flashLoan(address recipient, address[] memory tokens, uint256[] memory amounts, bytes memory userData) external;
}

interface ISwapRouter {
    struct ExactInputSingleParams {
        address tokenIn; address tokenOut; uint24 fee;
        address recipient; uint256 deadline;
        uint256 amountIn; uint256 amountOutMinimum; uint160 sqrtPriceLimitX96;
    }
    function exactInputSingle(ExactInputSingleParams calldata params) external payable returns (uint256 amountOut);
}

interface IERC20 {
    function transfer(address recipient, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract ArbFlashBot {
    address public owner;
    address constant VAULT = 0xBA12222222228d8Ba445958a75a0704d566BF2C8; // Balancer 
    address constant ROUTER = 0x2626664c2603336E57B271c5C0b26F421741e481; // Base Uniswap V3

    struct TriangleParams {
        address tokenA; address tokenB; address tokenC;
        uint24 fee1; uint24 fee2; uint24 fee3;
        uint256 loanAmount; uint256 minProfit;
    }

    constructor() { owner = msg.sender; }

    function checkAndShoot(
        address poolAddress, 
        address tokenA, address tokenB, address tokenC,
        uint24 fee1, uint24 fee2, uint24 fee3,
        uint256 loanAmount, uint256 minProfit
    ) external {
        require(msg.sender == owner, "Unauthorized");
        
        address[] memory tokens = new address[](1);
        tokens[0] = tokenA;
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = loanAmount;

        bytes memory userData = abi.encode(TriangleParams({
            tokenA: tokenA, tokenB: tokenB, tokenC: tokenC,
            fee1: fee1, fee2: fee2, fee3: fee3,
            loanAmount: loanAmount, minProfit: minProfit
        }));

        IBalancerVault(VAULT).flashLoan(address(this), tokens, amounts, userData);
    }

    function receiveFlashLoan(
        address[] memory tokens, uint256[] memory amounts,
        uint256[] memory feeAmounts, bytes memory userData
    ) external {
        require(msg.sender == VAULT, "Only Vault");
        TriangleParams memory p = abi.decode(userData, (TriangleParams));

        IERC20(p.tokenA).approve(ROUTER, p.loanAmount);
        uint256 outB = ISwapRouter(ROUTER).exactInputSingle(ISwapRouter.ExactInputSingleParams({
            tokenIn: p.tokenA, tokenOut: p.tokenB, fee: p.fee1,
            recipient: address(this), deadline: block.timestamp,
            amountIn: p.loanAmount, amountOutMinimum: 0, sqrtPriceLimitX96: 0
        }));

        IERC20(p.tokenB).approve(ROUTER, outB);
        uint256 outC = ISwapRouter(ROUTER).exactInputSingle(ISwapRouter.ExactInputSingleParams({
            tokenIn: p.tokenB, tokenOut: p.tokenC, fee: p.fee2,
            recipient: address(this), deadline: block.timestamp,
            amountIn: outB, amountOutMinimum: 0, sqrtPriceLimitX96: 0
        }));

        IERC20(p.tokenC).approve(ROUTER, outC);
        uint256 finalA = ISwapRouter(ROUTER).exactInputSingle(ISwapRouter.ExactInputSingleParams({
            tokenIn: p.tokenC, tokenOut: p.tokenA, fee: p.fee3,
            recipient: address(this), deadline: block.timestamp,
            amountIn: outC, amountOutMinimum: 0, sqrtPriceLimitX96: 0
        }));

        IERC20(p.tokenA).transfer(VAULT, p.loanAmount);
        uint256 profit = IERC20(p.tokenA).balanceOf(address(this));
        require(profit >= p.minProfit, "Insufficient Profit");

        IERC20(p.tokenA).transfer(owner, profit);
    }
}