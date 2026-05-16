// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// واجهة مخففة لا تطلب (bool) لتجنب الأخطاء مع عملات الميم
interface IERC20Relaxed {
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external; // removed returns bool
    function approve(address spender, uint256 amount) external;    // removed returns bool
}

interface IBalancerVault {
    function flashLoan(address recipient, address[] memory tokens, uint256[] memory amounts, bytes memory userData) external;
}

interface IRouter {
    struct ExactInputParams {
        bytes path;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
    }
    function exactInput(ExactInputParams calldata params) external payable returns (uint256 amountOut);
    
    struct Route {
        address from; address to; bool stable; address factory;
    }
    function swapExactTokensForTokens(
        uint256 amountIn, uint256 amountOutMin, Route[] calldata routes, address to, uint256 deadline
    ) external returns (uint256[] memory amounts);
}

contract ArbFlashBot {
    address constant VAULT = 0xBA12222222228d8Ba445958a75a0704d566BF2C8;
    address constant UNI_ROUTER = 0x2626664c2603336E57B271c5C0b26F421741e481;
    address constant AERO_ROUTER = 0xCF77A3ba9a5cA399af7227C093Af81a16a445235;
    address constant AERO_FACTORY = 0x420DD381b31aEf6683db6B902084cB0FFECe40Da;
    
    address public immutable owner;

    constructor() { owner = msg.sender; }

    modifier onlyOwner() { require(msg.sender == owner, "Not Owner"); _; }

    // دالة موافقة "مدرعة" (Safe Approval)
    function approveAll(address token) external onlyOwner {
        // نحاول الموافقة لكل راوتر، ونتجاهل الأخطاء البسيطة
        _safeApprove(token, UNI_ROUTER);
        _safeApprove(token, AERO_ROUTER);
        _safeApprove(token, VAULT);
    }

    // دالة داخلية لتنفيذ الموافقة بأمان
    function _safeApprove(address token, address spender) internal {
        // استخدام low-level call لتجنب التوقف بسبب الـ return values
        (bool success, ) = token.call(abi.encodeWithSelector(0x095ea7b3, spender, type(uint256).max));
        require(success, "Approve Failed");
    }

    function withdraw(address token) external onlyOwner {
        uint256 balance = IERC20Relaxed(token).balanceOf(address(this));
        if (balance > 0) {
            IERC20Relaxed(token).transfer(owner, balance);
        }
    }

    struct TradeParams {
        bool buyOnUni;
        bytes uniPath;
        uint256 loanAmount;
        uint256 minProfit;
        address tokenBorrow;
        address tokenTarget;
        bool isStable;
        uint16 buyTaxBps;
        uint16 sellTaxBps; 
    }

    function executeArb(TradeParams calldata p) external onlyOwner {
        address[] memory tokens = new address[](1);
        tokens[0] = p.tokenBorrow;
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = p.loanAmount;
        IBalancerVault(VAULT).flashLoan(address(this), tokens, amounts, abi.encode(p));
    }

    function receiveFlashLoan(
        address[] memory tokens, uint256[] memory amounts, uint256[] memory feeAmounts, bytes memory userData
    ) external {
        require(msg.sender == VAULT, "Not Vault");
        TradeParams memory p = abi.decode(userData, (TradeParams));
        
        uint256 amountRepay = amounts[0] + feeAmounts[0];
        uint256 amountOut; 

        if (p.buyOnUni) {
            // الشراء من UniSwap
            uint256 bought = IRouter(UNI_ROUTER).exactInput(IRouter.ExactInputParams({
                path: p.uniPath, recipient: address(this), deadline: block.timestamp, amountIn: p.loanAmount, amountOutMinimum: 1
            }));
            require(bought > 0, "Uni Buy Zero"); 

            // الموافقة الداخلية قبل البيع (لضمان الأمان)
            _safeApprove(p.tokenTarget, AERO_ROUTER);

            IRouter.Route[] memory routes = new IRouter.Route[](1);
            routes[0] = IRouter.Route({from: p.tokenTarget, to: p.tokenBorrow, stable: p.isStable, factory: AERO_FACTORY});
            
            try IRouter(AERO_ROUTER).swapExactTokensForTokens(bought, 1, routes, address(this), block.timestamp) returns (uint256[] memory outs) {
                 amountOut = outs[outs.length - 1];
            } catch { revert("Aero Sell Fail"); }

        } else {
            // الشراء من Aerodrome
            IRouter.Route[] memory routes = new IRouter.Route[](1);
            routes[0] = IRouter.Route({from: p.tokenBorrow, to: p.tokenTarget, stable: p.isStable, factory: AERO_FACTORY});
            
            uint256[] memory outs;
            try IRouter(AERO_ROUTER).swapExactTokensForTokens(p.loanAmount, 1, routes, address(this), block.timestamp) returns (uint256[] memory _outs) {
                outs = _outs;
            } catch { revert("Aero Buy Fail"); }
            
            uint256 amountToSell = outs[outs.length - 1];
            require(amountToSell > 0, "Aero Buy Zero");

            // الموافقة الداخلية
             _safeApprove(p.tokenTarget, UNI_ROUTER);

            try IRouter(UNI_ROUTER).exactInput(IRouter.ExactInputParams({
                path: p.uniPath, recipient: address(this), deadline: block.timestamp, amountIn: amountToSell, amountOutMinimum: 1
            })) returns (uint256 _sold) {
                amountOut = _sold;
            } catch { revert("Uni Sell Fail"); }
        }

        uint256 balanceFinal = IERC20Relaxed(p.tokenBorrow).balanceOf(address(this));
        
        if (balanceFinal < amountRepay) {
            revert("Loss: Can't Repay Loan");
        }
        
        if (balanceFinal < amountRepay + p.minProfit) {
            revert("Profit Too Low");
        }

        IERC20Relaxed(p.tokenBorrow).transfer(VAULT, amountRepay);
    }
}
