// SPDX-License-Identifier: MIT
pragma solidity ^0.8.21;

interface IERC20Minimal {
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
}

interface IUniswapV2Pair {
    function swap(
        uint256 amount0Out,
        uint256 amount1Out,
        address to,
        bytes calldata data
    ) external;
}

interface IAaveSimplePool {
    function flashLoanSimple(
        address receiver,
        address asset,
        uint256 amount,
        bytes calldata params,
        uint16 referralCode
    ) external;
}

contract OptimizedArbitrage {
    address public immutable owner;
    address public immutable pool;

    error Unauthorized();
    error InsufficientProfit(uint256 actualProfit, uint256 minRequired);

    // Parametri pre-calcolati dal bot off-chain per massimizzare la velocità on-chain
    struct SwapPlan {
        address pair1;
        address pair2;
        uint256 amount0Out1; // Output atteso dal primo swap (uno dei due sarà 0)
        uint256 amount1Out1;
        uint256 amount0Out2; // Output atteso dal secondo swap (ritorno all'asset di debito)
        uint256 amount1Out2;
        uint256 minProfit;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    constructor(address pool_) {
        owner = msg.sender;
        pool = pool_;
    }

    // Innesco del Flash Loan
    function startArbitrage(
        address asset,
        uint256 amount,
        SwapPlan calldata plan
    ) external onlyOwner {
        IAaveSimplePool(pool).flashLoanSimple(
            address(this),
            asset,
            amount,
            abi.encode(plan),
            0
        );
    }

    // Callback eseguita da Aave: totalmente stateless, zero scritture di storage
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external returns (bool) {
        // Aave garantisce che initiator corrisponda a chi ha invocato il prestito
        if (msg.sender != pool || initiator != address(this)) revert Unauthorized();

        SwapPlan memory plan = abi.decode(params, (SwapPlan));

        // 1. Invia il collaterale preso in prestito direttamente a Pair 1
        IERC20Minimal(asset).transfer(plan.pair1, amount);

        // 2. Swap 1: il token bridge viene inviato direttamente a Pair 2 (zero commissioni gas di rientro)
        IUniswapV2Pair(plan.pair1).swap(
            plan.amount0Out1,
            plan.amount1Out1,
            plan.pair2,
            ""
        );

        // 3. Swap 2: Pair 2 riconverte l'asset e lo invia a questo contratto
        IUniswapV2Pair(plan.pair2).swap(
            plan.amount0Out2,
            plan.amount1Out2,
            address(this),
            ""
        );

        // 4. Calcolo del debito e approvazione ad Aave
        uint256 debt;
        unchecked {
            debt = amount + premium;
        }
        IERC20Minimal(asset).approve(pool, debt);

        // 5. Verifica profitto e incasso immediato all'owner
        uint256 currentBalance = IERC20Minimal(asset).balanceOf(address(this));
        if (currentBalance < debt + plan.minProfit) {
            revert InsufficientProfit(
                currentBalance >= debt ? currentBalance - debt : 0,
                plan.minProfit
            );
        }

        unchecked {
            uint256 profit = currentBalance - debt;
            if (profit > 0) {
                IERC20Minimal(asset).transfer(owner, profit);
            }
        }

        return true;
    }

    // Prelievo di sicurezza nel caso token rimangano accidentalmente nel contratto
    function sweep(address token) external onlyOwner {
        uint256 bal = IERC20Minimal(token).balanceOf(address(this));
        if (bal > 0) {
            IERC20Minimal(token).transfer(owner, bal);
        }
    }
}