from web3 import Web3
from eth_abi import decode

w3 = Web3(Web3.HTTPProvider("https://base-rpc.publicnode.com"))
MULTICALL3_ADDRESS = Web3.to_checksum_address("0xcA11bde05977b3631167028862bE2a173976CA11")

MULTICALL3_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "target", "type": "address"},
                    {"name": "allowFailure", "type": "bool"},
                    {"name": "callData", "type": "bytes"}
                ],
                "name": "calls",
                "type": "tuple[]"
            }
        ],
        "name": "aggregate3",
        "outputs": [
            {
                "components": [
                    {"name": "success", "type": "bool"},
                    {"name": "returnData", "type": "bytes"}
                ],
                "name": "returnData",
                "type": "tuple[]"
            }
        ],
        "stateMutability": "payable",
        "type": "function"
    }
]

multicall = w3.eth.contract(address=MULTICALL3_ADDRESS, abi=MULTICALL3_ABI)

SIG_RESERVES = bytes.fromhex("0902f1ac")
SIG_SLOT0 = bytes.fromhex("3850c7bd")

PAIRS_CONFIG = [
    {
        "pair_name": "VIRTUAL/WETH",
        "pool_a": {"name": "Uniswap V2", "address": "0xE31c372a7Af875b3B5E0F3713B17ef51556da667", "type": "v2", "fee": 0.30},
        "pool_b": {"name": "Aerodrome V2", "address": "0x21594b992F68495dD28d605834b58889d0a727c7", "type": "v2", "fee": 0.30},
        "base_symbol": "VIRTUAL",
        "quote_symbol": "WETH",
        "base_decimals": 18,
        "quote_decimals": 18
    },
    {
        "pair_name": "AERO/USDC",
        "pool_a": {"name": "Aerodrome V2", "address": "0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d", "type": "v2", "fee": 0.30},
        "pool_b": {"name": "Uniswap V3", "address": "0x2426DC0A657BD481ab48f86C1616431905901238", "type": "v3", "fee": 0.30},
        "base_symbol": "AERO",
        "quote_symbol": "USDC",
        "base_decimals": 18,
        "quote_decimals": 6
    },
    {
        "pair_name": "DEGEN/WETH",
        "pool_a": {"name": "Aerodrome V2", "address": "0x2C4909355b0C036840819484c3A882A95659aBf3", "type": "v2", "fee": 0.30},
        "pool_b": {"name": "Uniswap V3", "address": "0x0cA6485b7e9cF814A3Fd09d81672B07323535b64", "type": "v3", "fee": 1.00},
        "base_symbol": "DEGEN",
        "quote_symbol": "WETH",
        "base_decimals": 18,
        "quote_decimals": 18
    },
    {
        "pair_name": "WETH/USDC",
        "pool_a": {"name": "Uniswap V3", "address": "0xd0b53D9277642d899DF5C87A3966A349A798F224", "type": "v3", "fee": 0.05},
        "pool_b": {"name": "Aerodrome Volatile", "address": "0xcDAC0d6c6C59727a65F871236188350531885C43", "type": "v2", "fee": 0.05},
        "base_symbol": "WETH",
        "quote_symbol": "USDC",
        "base_decimals": 18,
        "quote_decimals": 6
    }
]

calls = []
for p in PAIRS_CONFIG:
    for pool_key in ["pool_a", "pool_b"]:
        pool = p[pool_key]
        sig = SIG_RESERVES if pool["type"] == "v2" else SIG_SLOT0
        calls.append({
            "target": Web3.to_checksum_address(pool["address"]),
            "allowFailure": True,
            "callData": sig
        })

results = multicall.functions.aggregate3(calls).call()
print(f"Batch Multicall3 eseguito con successo: {len(results)} pool interrogate in una sola chiamata!\n")

idx = 0
for p in PAIRS_CONFIG:
    print(f"=== {p['pair_name']} ===")
    prices = {}
    for pool_key in ["pool_a", "pool_b"]:
        pool = p[pool_key]
        success, ret = results[idx]
        idx += 1
        if not success or not ret:
            print(f"  {pool['name']}: Chiamata fallita")
            continue
            
        if pool["type"] == "v2":
            r0, r1, _ = decode(["uint112", "uint112", "uint32"], ret)
            # Decodifica prezzo per convenzione quote/base
            # token0 = base, token1 = quote
            p_val = (r1 / 10**p["quote_decimals"]) / (r0 / 10**p["base_decimals"])
            prices[pool["name"]] = {"price": p_val, "r_base": r0 / 10**p["base_decimals"], "r_quote": r1 / 10**p["quote_decimals"], "fee": pool["fee"]}
            print(f"  {pool['name']:<18}: {p_val:.8f} {p['quote_symbol']} (Liq: {r0/10**p['base_decimals']:,.0f} {p['base_symbol']})")
            
        elif pool["type"] == "v3":
            sqrtPriceX96 = decode(["uint160", "int24", "uint16", "uint16", "uint16", "uint8", "bool"], ret)[0]
            raw_ratio = (sqrtPriceX96 / (2**96)) ** 2
            # Per Uniswap V3: se token0 è base e token1 è quote:
            # p_val = raw_ratio * 10^(base_dec - quote_dec)
            p_val = raw_ratio * (10**(p["base_decimals"] - p["quote_decimals"]))
            prices[pool["name"]] = {"price": p_val, "fee": pool["fee"]}
            print(f"  {pool['name']:<18}: {p_val:.8f} {p['quote_symbol']}")

    # Calcolo spread tra i due
    if len(prices) == 2:
        names = list(prices.keys())
        p1, p2 = prices[names[0]]["price"], prices[names[1]]["price"]
        cheaper = names[0] if p1 < p2 else names[1]
        expensive = names[1] if p1 < p2 else names[0]
        min_p = min(p1, p2)
        max_p = max(p1, p2)
        spread_pct = ((max_p - min_p) / min_p) * 100
        combined_fee = prices[names[0]]["fee"] + prices[names[1]]["fee"]
        net_spread = spread_pct - combined_fee
        print(f"  --> Spread: {spread_pct:.3f}% | Fee DEX combinate: {combined_fee:.2f}% | Spread Netto Stimato: {net_spread:+.3f}%")
        if net_spread > 0:
            print("  *** [ATTENZIONE: SPREAD NETTO POSITIVO RILEVATO!] ***")
    print()
