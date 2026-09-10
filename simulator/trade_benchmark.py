from web3 import Web3
from typing import List, Dict, Any

# Parametri su Base
RPC_URL = "https://base-rpc.publicnode.com"
WETH = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")
USDC = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")

AERO_POOL = Web3.to_checksum_address("0xcDAC0d6c6C59727a65F871236188350531885C43")
QUOTER_V2 = Web3.to_checksum_address("0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a")

AERO_ABI = [
    {
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "tokenIn", "type": "address"}
        ],
        "name": "getAmountOut",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

QUOTER_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "tokenIn", "type": "address"},
                    {"name": "tokenOut", "type": "address"},
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "fee", "type": "uint24"},
                    {"name": "sqrtPriceLimitX96", "type": "uint160"}
                ],
                "name": "params",
                "type": "tuple"
            }
        ],
        "name": "quoteExactInputSingle",
        "outputs": [
            {"name": "amountOut", "type": "uint256"},
            {"name": "sqrtPriceX96After", "type": "uint160"},
            {"name": "initializedTicksCrossed", "type": "uint32"},
            {"name": "gasEstimate", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

class ArbitrageBenchmark:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 10}))
        self.aero = self.w3.eth.contract(address=AERO_POOL, abi=AERO_ABI)
        self.quoter = self.w3.eth.contract(address=QUOTER_V2, abi=QUOTER_ABI)

    def run_benchmark(self, amounts_usd: List[float] = [10, 50, 100, 250, 500, 1000, 2500, 5000]):
        gas_price_wei = self.w3.eth.gas_price
        gas_price_gwei = self.w3.from_wei(gas_price_wei, "gwei")
        block = self.w3.eth.block_number

        print("=" * 80)
        print("          BENCHMARK MATEMATICO DI ARBITRAGGIO -- BASE NETWORK")
        print(f"  Blocco: #{block} | Gas Price: {gas_price_gwei:.4f} Gwei | Coppia: WETH / USDC")
        print("=" * 80)

        # Stima costo gas in USD (circa 180.000 unità per flash loan + 2 swap)
        # Prezzo stimato ETH ~ 2460 USD
        est_gas_units = 180000
        eth_price_est = 2465.0
        gas_cost_usd = (est_gas_units * gas_price_wei / 10**18) * eth_price_est

        print(f"[i] Stima costo gas per operazione completa (2 swap): ${gas_cost_usd:.4f} USD\n")

        self._benchmark_direction(
            title="DIREZIONE 1: Compra su Aerodrome -> Vendi su Uniswap V3",
            buy_dex="Aerodrome",
            sell_dex="Uniswap V3",
            amounts=amounts_usd,
            gas_cost_usd=gas_cost_usd,
            direction="aero_to_uni"
        )

        print("\n" + "-" * 80 + "\n")

        self._benchmark_direction(
            title="DIREZIONE 2: Compra su Uniswap V3 -> Vendi su Aerodrome",
            buy_dex="Uniswap V3",
            sell_dex="Aerodrome",
            amounts=amounts_usd,
            gas_cost_usd=gas_cost_usd,
            direction="uni_to_aero"
        )

    def _benchmark_direction(
        self,
        title: str,
        buy_dex: str,
        sell_dex: str,
        amounts: List[float],
        gas_cost_usd: float,
        direction: str
    ):
        print(f"=== {title} ===")
        header = f"{'Capitale ($)':>12} | {'Token Ricevuti':>14} | {'USDC Uscita':>12} | {'Lordo ($)':>10} | {'Gas ($)':>8} | {'Netto ($)':>10} | {'ROI Netto %':>11}"
        print(header)
        print("-" * len(header))

        for amt in amounts:
            usdc_in = int(amt * 10**6)

            try:
                if direction == "aero_to_uni":
                    # Leg 1: swap USDC -> WETH su Aerodrome
                    weth_received = self.aero.functions.getAmountOut(usdc_in, USDC).call()
                    # Leg 2: swap WETH -> USDC su Uniswap V3
                    params = (WETH, USDC, weth_received, 500, 0)
                    quote_uni = self.quoter.functions.quoteExactInputSingle(params).call()
                    usdc_out = quote_uni[0]
                    token_display = f"{weth_received / 10**18:.4f} WETH"

                else:
                    # Leg 1: swap USDC -> WETH su Uniswap V3
                    params = (USDC, WETH, usdc_in, 500, 0)
                    quote_uni = self.quoter.functions.quoteExactInputSingle(params).call()
                    weth_received = quote_uni[0]
                    # Leg 2: swap WETH -> USDC su Aerodrome
                    usdc_out = self.aero.functions.getAmountOut(weth_received, WETH).call()
                    token_display = f"{weth_received / 10**18:.4f} WETH"

                out_dollars = usdc_out / 10**6
                gross_pnl = out_dollars - amt
                net_pnl = gross_pnl - gas_cost_usd
                roi_pct = (net_pnl / amt) * 100.0

                net_str = f"{'+' if net_pnl > 0 else ''}{net_pnl:.2f}"
                gross_str = f"{'+' if gross_pnl > 0 else ''}{gross_pnl:.2f}"
                roi_str = f"{'+' if roi_pct > 0 else ''}{roi_pct:.3f}%"

                tag = " [PROFITTO!]" if net_pnl > 0 else ""
                print(
                    f"{amt:>12.2f} | {token_display:>14} | {out_dollars:>12.2f} | "
                    f"{gross_str:>10} | {gas_cost_usd:>8.4f} | {net_str:>10} | {roi_str:>11}{tag}"
                )
            except Exception as e:
                print(f"{amt:>12.2f} | ERRORE: {e}")

if __name__ == "__main__":
    b = ArbitrageBenchmark()
    b.run_benchmark()
