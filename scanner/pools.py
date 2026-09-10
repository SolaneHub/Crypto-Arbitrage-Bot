from eth_abi import decode
from typing import Dict, Any, Optional

GET_RESERVES_SIG = bytes.fromhex("0902f1ac")
SLOT0_SIG = bytes.fromhex("3850c7bd")

class PoolDecoder:
    @staticmethod
    def get_calldata(pool_type: str) -> bytes:
        if pool_type in ("univ2", "aerodrome"):
            return GET_RESERVES_SIG
        elif pool_type == "univ3":
            return SLOT0_SIG
        else:
            raise ValueError(f"Tipo pool non supportato: {pool_type}")

    @staticmethod
    def decode_price(pool_config: Dict[str, Any], return_data: bytes) -> Optional[Dict[str, Any]]:
        if not return_data:
            return None

        pool_type = pool_config["type"]
        base_symbol = pool_config["base_token"]
        quote_symbol = pool_config["quote_token"]

        try:
            if pool_type in ("univ2", "aerodrome"):
                r0, r1, _ = decode(["uint112", "uint112", "uint32"], return_data)
                # In BaseSwap e Aerodrome WETH-USDC: token0 = WETH (18 dec), token1 = USDC (6 dec)
                weth_reserve = r0 / 10**18
                usdc_reserve = r1 / 10**6
                
                if weth_reserve <= 0:
                    return None
                
                price = usdc_reserve / weth_reserve
                return {
                    "dex": pool_config["dex"],
                    "name": pool_config["name"],
                    "price": price,
                    "base_reserve": weth_reserve,
                    "quote_reserve": usdc_reserve,
                    "fee_pct": pool_config["fee_pct"]
                }

            elif pool_type == "univ3":
                sqrtPriceX96, tick, _, _, _, _, _ = decode(
                    ["uint160", "int24", "uint16", "uint16", "uint16", "uint8", "bool"],
                    return_data
                )
                raw_ratio = (sqrtPriceX96 / (2**96)) ** 2
                # token0 = WETH (18), token1 = USDC (6) -> raw_ratio * 10^12 = USDC per WETH
                price = raw_ratio * (10**12)
                return {
                    "dex": pool_config["dex"],
                    "name": pool_config["name"],
                    "price": price,
                    "tick": tick,
                    "fee_pct": pool_config["fee_pct"]
                }
        except Exception as e:
            return None
