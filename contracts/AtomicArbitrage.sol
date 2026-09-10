// SPDX-License-Identifier: MIT
pragma solidity ^0.8.21;

/**
 * @title AtomicArbitrage
 * @notice Contratto per l'esecuzione atomica di arbitraggio DEX-to-DEX su Base Network.
 *         Supporta Flash Loan a costo zero tramite Balancer V2 Vault (e fallback su Aave V3).
 *         Fonde la velocità a basso consumo di gas con controlli difensivi di slippage e revert automatico.
 */

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}

interface IAeroV2Pair {
    function swap(uint256 amount0Out, uint256 amount1Out, address to, bytes calldata data) external;
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
    function token0() external view returns (address);
    function token1() external view returns (address);
    function getAmountOut(uint256 amountIn, address tokenIn) external view returns (uint256);
}

/// @dev Interfaccia per SwapRouter02 di Uniswap V3 su Base
interface ISwapRouterV3 {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }
    function exactInputSingle(ExactInputSingleParams calldata params) external payable returns (uint256 amountOut);
}

/// @dev Interfaccia Balancer V2 Flash Loan (0.00% Fee su Base)
interface IBalancerVault {
    function flashLoan(
        address recipient,
        IERC20[] memory tokens,
        uint256[] memory amounts,
        bytes memory userData
    ) external;
}

/// @dev Interfaccia Aave V3 Flash Loan
interface IAaveV3Pool {
    function flashLoanSimple(
        address receiverAddress,
        address asset,
        uint256 amount,
        bytes calldata params,
        uint16 referralCode
    ) external;
}

contract AtomicArbitrage {
    address public immutable owner;
    address public constant BALANCER_VAULT = 0xba12222222228d8Ba53140F039445Ca69944369c;
    address public constant AAVE_V3_POOL  = 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5;
    address public constant UNI_V3_ROUTER = 0x2626664c2603336E57B271c5C0b26F421741e481;

    // Errori Custom gas-efficient
    error Unauthorized();
    error InsufficientProfit(uint256 actualProfit, uint256 requiredProfit);
    error InvalidCaller();
    error TransferFailed();

    event ArbitrageExecuted(
        address indexed borrowedAsset,
        uint256 loanAmount,
        uint256 netProfit,
        uint256 timestamp
    );

    enum DexType { UNISWAP_V3, AERODROME_V2 }

    struct ExecutionPlan {
        address borrowedAsset;
        uint256 loanAmount;
        address bridgeAsset;
        DexType leg1Dex;
        address leg1Target;     // Indirizzo Pool V2 o Router V3
        uint24 leg1V3Fee;       // Se V3
        DexType leg2Dex;
        address leg2Target;     // Indirizzo Pool V2 o Router V3
        uint24 leg2V3Fee;       // Se V3
        uint256 minProfitAmount;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Avvia l'arbitraggio richiedendo un Flash Loan a costo zero a Balancer V2
     */
    function executeBalancerFlashArbitrage(ExecutionPlan calldata plan) external onlyOwner {
        IERC20[] memory tokens = new IERC20[](1);
        tokens[0] = IERC20(plan.borrowedAsset);

        uint256[] memory amounts = new uint256[](1);
        amounts[0] = plan.loanAmount;

        IBalancerVault(BALANCER_VAULT).flashLoan(
            address(this),
            tokens,
            amounts,
            abi.encode(plan)
        );
    }

    /**
     * @notice Callback obbligatoria per Balancer V2 Flash Loan
     */
    function receiveFlashLoan(
        IERC20[] memory tokens,
        uint256[] memory amounts,
        uint256[] memory feeAmounts,
        bytes memory userData
    ) external {
        if (msg.sender != BALANCER_VAULT) revert InvalidCaller();

        ExecutionPlan memory plan = abi.decode(userData, (ExecutionPlan));
        uint256 debt = amounts[0] + feeAmounts[0];

        // Esegui la strategia di arbitraggio a 2 leg
        _executeSwaps(plan);

        // Verifica profitto netto dopo rimborso
        uint256 finalBalance = tokens[0].balanceOf(address(this));
        if (finalBalance < debt + plan.minProfitAmount) {
            revert InsufficientProfit(
                finalBalance >= debt ? finalBalance - debt : 0,
                plan.minProfitAmount
            );
        }

        // Rimborso del Flash Loan a Balancer
        _safeTransfer(address(tokens[0]), BALANCER_VAULT, debt);

        // Accredito immediato dell'utile all'owner
        uint256 profit = finalBalance - debt;
        if (profit > 0) {
            _safeTransfer(address(tokens[0]), owner, profit);
            emit ArbitrageExecuted(address(tokens[0]), plan.loanAmount, profit, block.timestamp);
        }
    }

    /**
     * @notice Avvia l'arbitraggio tramite Aave V3 (Fallback)
     */
    function executeAaveFlashArbitrage(ExecutionPlan calldata plan) external onlyOwner {
        IAaveV3Pool(AAVE_V3_POOL).flashLoanSimple(
            address(this),
            plan.borrowedAsset,
            plan.loanAmount,
            abi.encode(plan),
            0
        );
    }

    /**
     * @notice Callback obbligatoria per Aave V3 Flash Loan
     */
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external returns (bool) {
        if (msg.sender != AAVE_V3_POOL || initiator != address(this)) revert InvalidCaller();

        ExecutionPlan memory plan = abi.decode(params, (ExecutionPlan));
        uint256 debt = amount + premium;

        // Esegui i due swap
        _executeSwaps(plan);

        // Verifica profitto netto
        uint256 finalBalance = IERC20(asset).balanceOf(address(this));
        if (finalBalance < debt + plan.minProfitAmount) {
            revert InsufficientProfit(
                finalBalance >= debt ? finalBalance - debt : 0,
                plan.minProfitAmount
            );
        }

        // Approvazione e rimborso ad Aave
        _safeApprove(asset, AAVE_V3_POOL, debt);

        // Accredito profitto
        uint256 profit = finalBalance - debt;
        if (profit > 0) {
            _safeTransfer(asset, owner, profit);
            emit ArbitrageExecuted(asset, plan.loanAmount, profit, block.timestamp);
        }

        return true;
    }

    /**
     * @notice Esegue un arbitraggio diretto utilizzando il proprio capitale (es. 50 €)
     *         senza ricorrere a Flash Loan. I fondi vengono prelevati dall'owner e restituiti con il profitto.
     */
    function executeDirectArbitrage(ExecutionPlan calldata plan) external onlyOwner {
        _safeTransferFrom(plan.borrowedAsset, owner, address(this), plan.loanAmount);

        _executeSwaps(plan);

        uint256 finalBalance = IERC20(plan.borrowedAsset).balanceOf(address(this));
        if (finalBalance < plan.loanAmount + plan.minProfitAmount) {
            revert InsufficientProfit(
                finalBalance >= plan.loanAmount ? finalBalance - plan.loanAmount : 0,
                plan.minProfitAmount
            );
        }

        _safeTransfer(plan.borrowedAsset, owner, finalBalance);

        uint256 profit = finalBalance - plan.loanAmount;
        if (profit > 0) {
            emit ArbitrageExecuted(plan.borrowedAsset, plan.loanAmount, profit, block.timestamp);
        }
    }

    /**
     * @dev Esecuzione interna dei due swap atomici
     */
    function _executeSwaps(ExecutionPlan memory plan) internal {
        // LEG 1: Scambio BorrowedAsset -> BridgeAsset
        uint256 bridgeReceived = 0;
        if (plan.leg1Dex == DexType.UNISWAP_V3) {
            _safeApprove(plan.borrowedAsset, UNI_V3_ROUTER, plan.loanAmount);
            bridgeReceived = ISwapRouterV3(UNI_V3_ROUTER).exactInputSingle(
                ISwapRouterV3.ExactInputSingleParams({
                    tokenIn: plan.borrowedAsset,
                    tokenOut: plan.bridgeAsset,
                    fee: plan.leg1V3Fee,
                    recipient: address(this),
                    amountIn: plan.loanAmount,
                    amountOutMinimum: 0, // Lo slippage globale è protetto dal minProfit finale
                    sqrtPriceLimitX96: 0
                })
            );
        } else {
            // Aerodrome V2
            IAeroV2Pair pair = IAeroV2Pair(plan.leg1Target);
            uint256 amountOut = pair.getAmountOut(plan.loanAmount, plan.borrowedAsset);
            _safeTransfer(plan.borrowedAsset, plan.leg1Target, plan.loanAmount);
            bool isToken0 = (pair.token0() == plan.borrowedAsset);

            pair.swap(
                isToken0 ? 0 : amountOut,
                isToken0 ? amountOut : 0,
                address(this),
                ""
            );
            bridgeReceived = amountOut;
        }

        // LEG 2: Scambio BridgeAsset -> BorrowedAsset
        if (plan.leg2Dex == DexType.UNISWAP_V3) {
            _safeApprove(plan.bridgeAsset, UNI_V3_ROUTER, bridgeReceived);
            ISwapRouterV3(UNI_V3_ROUTER).exactInputSingle(
                ISwapRouterV3.ExactInputSingleParams({
                    tokenIn: plan.bridgeAsset,
                    tokenOut: plan.borrowedAsset,
                    fee: plan.leg2V3Fee,
                    recipient: address(this),
                    amountIn: bridgeReceived,
                    amountOutMinimum: 0,
                    sqrtPriceLimitX96: 0
                })
            );
        } else {
            // Aerodrome V2
            IAeroV2Pair pair = IAeroV2Pair(plan.leg2Target);
            uint256 amountOut = pair.getAmountOut(bridgeReceived, plan.bridgeAsset);
            _safeTransfer(plan.bridgeAsset, plan.leg2Target, bridgeReceived);
            bool isToken0 = (pair.token0() == plan.bridgeAsset);

            pair.swap(
                isToken0 ? 0 : amountOut,
                isToken0 ? amountOut : 0,
                address(this),
                ""
            );
        }
    }

    // Helper per trasferimento sicuro compatibile con token non standard (USDT)
    function _safeTransfer(address token, address to, uint256 amount) internal {
        (bool success, bytes memory data) = token.call(
            abi.encodeWithSelector(IERC20.transfer.selector, to, amount)
        );
        if (!success || (data.length != 0 && !abi.decode(data, (bool)))) {
            revert TransferFailed();
        }
    }

    function _safeApprove(address token, address spender, uint256 amount) internal {
        (bool success, bytes memory data) = token.call(
            abi.encodeWithSelector(IERC20.approve.selector, spender, amount)
        );
        if (!success || (data.length != 0 && !abi.decode(data, (bool)))) {
            revert TransferFailed();
        }
    }

    function _safeTransferFrom(address token, address from, address to, uint256 amount) internal {
        (bool success, bytes memory data) = token.call(
            abi.encodeWithSelector(IERC20.transferFrom.selector, from, to, amount)
        );
        if (!success || (data.length != 0 && !abi.decode(data, (bool)))) {
            revert TransferFailed();
        }
    }

    // Prelievo di sicurezza fondi
    function rescueToken(address token) external onlyOwner {
        uint256 balance = IERC20(token).balanceOf(address(this));
        if (balance > 0) {
            _safeTransfer(token, owner, balance);
        }
    }

    function rescueETH() external onlyOwner {
        uint256 balance = address(this).balance;
        if (balance > 0) {
            (bool sent, ) = owner.call{value: balance}("");
            if (!sent) revert TransferFailed();
        }
    }

    receive() external payable {}
}
