from eth_abi import decode
from typing import Dict, Any, Optional

SIG_RESERVES = bytes.fromhex("0902f1ac")
SIG_SLOT0 = bytes.fromhex("3850c7bd")

class PoolDecoder:
    @staticmethod
    def get_calldata(pool_type: str) -> bytes:
        if pool_type == "v2":
            return SIG_RESERVES
        elif pool_type in ("v3", "slipstream"):
            return SIG_SLOT0
        else:
            raise ValueError(f"Tipo pool non supportato: {pool_type}")

    @staticmethod
    def decode_pool_state(
        pool_cfg: Dict[str, Any],
        pair_cfg: Dict[str, Any],
        return_data: bytes
    ) -> Optional[Dict[str, Any]]:
        if not return_data:
            return None

        p_type = pool_cfg["type"]
        base_dec = pair_cfg["base_decimals"]
        quote_dec = pair_cfg["quote_decimals"]
        t0_is_base = pool_cfg["token0_is_base"]

        try:
            if p_type == "v2":
                r0, r1, _ = decode(["uint112", "uint112", "uint32"], return_data)
                r_base_raw = r0 if t0_is_base else r1
                r_quote_raw = r1 if t0_is_base else r0

                r_base = r_base_raw / (10**base_dec)
                r_quote = r_quote_raw / (10**quote_dec)

                if r_base <= 0 or r_quote <= 0:
                    return None

                price = r_quote / r_base
                if price <= 0 or price > 1e12 or price < 1e-12:
                    return None

                return {
                    "dex": pool_cfg["name"],
                    "type": "v2",
                    "price": price,
                    "r_base_raw": r_base_raw,
                    "r_quote_raw": r_quote_raw,
                    "r_base": r_base,
                    "r_quote": r_quote,
                    "fee_bps": pool_cfg["fee_bps"]
                }

            elif p_type == "v3":
                # Uniswap V3 (uint8) oppure PancakeSwap V3 (uint32)
                try:
                    sqrtPriceX96 = decode(
                        ["uint160", "int24", "uint16", "uint16", "uint16", "uint8", "bool"],
                        return_data
                    )[0]
                except Exception:
                    sqrtPriceX96 = decode(
                        ["uint160", "int24", "uint16", "uint16", "uint16", "uint32", "bool"],
                        return_data
                    )[0]

                raw_ratio = (sqrtPriceX96 / (2**96)) ** 2

                if t0_is_base:
                    price = raw_ratio * (10**(base_dec - quote_dec))
                else:
                    price = (1.0 / raw_ratio) * (10**(base_dec - quote_dec))

                if price <= 0 or price > 1e12 or price < 1e-12:
                    return None

                return {
                    "dex": pool_cfg["name"],
                    "type": "v3",
                    "price": price,
                    "fee_bps": pool_cfg["fee_bps"]
                }

            elif p_type == "slipstream":
                # Aerodrome Slipstream: 6 campi
                sqrtPriceX96 = decode(
                    ["uint160", "int24", "uint16", "uint16", "uint16", "bool"],
                    return_data
                )[0]
                raw_ratio = (sqrtPriceX96 / (2**96)) ** 2

                if t0_is_base:
                    price = raw_ratio * (10**(base_dec - quote_dec))
                else:
                    price = (1.0 / raw_ratio) * (10**(base_dec - quote_dec))

                if price <= 0 or price > 1e12 or price < 1e-12:
                    return None

                return {
                    "dex": pool_cfg["name"],
                    "type": "slipstream",
                    "price": price,
                    "fee_bps": pool_cfg["fee_bps"]
                }

        except Exception:
            return None

    @staticmethod
    def get_amount_out_v2(amount_in: int, reserve_in: int, reserve_out: int, fee_bps: int = 30) -> int:
        if amount_in <= 0 or reserve_in <= 0 or reserve_out <= 0:
            return 0
        amount_in_with_fee = amount_in * (10000 - fee_bps)
        numerator = amount_in_with_fee * reserve_out
        denominator = (reserve_in * 10000) + amount_in_with_fee
        return numerator // denominator
