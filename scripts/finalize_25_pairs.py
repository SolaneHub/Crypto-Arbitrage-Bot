import json
from web3 import Web3
from scanner.multicall import MulticallManager
from scanner.pools import PoolDecoder
from config.settings import RPC_ENDPOINTS, MULTICALL3_ADDRESS

with open("data/25_pairs_config.json", "r") as f:
    current_pairs = json.load(f)

# Rimuoviamo le 3 coppie con pool stantie (spread > 5%)
clean_pairs = [p for p in current_pairs if p["id"] not in ("tBTC_cbBTC", "tBTC_WETH", "cbETH_USDC")]

# Candidati per arrivare esattamente a 25 coppie pulite
manager = MulticallManager(RPC_ENDPOINTS, MULTICALL3_ADDRESS)

UNI_FACTORY = Web3.to_checksum_address("0x33128a8fC17869897dcE68Ed026d694621f6FDfD")
AERO_FACTORY = Web3.to_checksum_address("0x420DD381b31aEf6683db6B902084cB0FFECe40Da")
uni_fac = manager.w3.eth.contract(address=UNI_FACTORY, abi=[{"inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}, {"name": "fee", "type": "uint24"}], "name": "getPool", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}])
aero_fac = manager.w3.eth.contract(address=AERO_FACTORY, abi=[{"inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}, {"name": "stable", "type": "bool"}], "name": "getPool", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}])
pool_abi = [{"inputs": [], "name": "token0", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}, {"inputs": [], "name": "liquidity", "outputs": [{"name": "", "type": "uint128"}], "stateMutability": "view", "type": "function"}]
v2_abi = [{"inputs": [], "name": "getReserves", "outputs": [{"name": "r0", "type": "uint112"}, {"name": "r1", "type": "uint112"}, {"name": "t", "type": "uint32"}], "stateMutability": "view", "type": "function"}, {"inputs": [], "name": "token0", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}]

TOKENS_EXTRA = {
    "AERO": ("0x940181a94A35A4569E4529A3CDfB74e38FD98631", 18),
    "cbBTC": ("0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf", 8),
    "USDC": ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 6),
    "WETH": ("0x4200000000000000000000000000000000000006", 18),
    "wstETH": ("0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452", 18),
    "weETH": ("0x04C0599Ae5A44757c0af6F9eC3b93da8976c150A", 18),
    "ezETH": ("0x2416092f143378750bb29b79eD961ab195CcEea5", 18),
    "USDT": ("0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2", 6),
    "EURC": ("0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42", 6)
}

candidate_extra = [
    ("AERO", "cbBTC", False),
    ("weETH", "USDC", False),
    ("ezETH", "USDC", False),
    ("USDT", "EURC", False),
    ("wstETH", "cbBTC", False),
    ("cbBTC", "USDT", False)
]

for b_sym, q_sym, is_q_eth in candidate_extra:
    if len(clean_pairs) >= 25:
        break
    tA = Web3.to_checksum_address(TOKENS_EXTRA[b_sym][0])
    tB = Web3.to_checksum_address(TOKENS_EXTRA[q_sym][0])
    
    # Cerca Uni V3
    u_addr = None
    u_fee = 30
    for f in [500, 3000, 100]:
        p = uni_fac.functions.getPool(tA, tB, f).call()
        if p != "0x0000000000000000000000000000000000000000":
            try:
                cp = manager.w3.eth.contract(address=p, abi=pool_abi)
                if cp.functions.liquidity().call() > 0:
                    u_addr = p
                    u_fee = f // 100
                    break
            except Exception:
                pass
                
    # Cerca Aero V2
    a_addr = None
    a_stb = False
    for stb in [False, True]:
        p = aero_fac.functions.getPool(tA, tB, stb).call()
        if p != "0x0000000000000000000000000000000000000000":
            try:
                cp = manager.w3.eth.contract(address=p, abi=v2_abi)
                r0, r1, _ = cp.functions.getReserves().call()
                if r0 > 0 and r1 > 0:
                    a_addr = p
                    a_stb = stb
                    break
            except Exception:
                pass
                
    if u_addr and a_addr:
        c_u = manager.w3.eth.contract(address=u_addr, abi=pool_abi)
        c_a = manager.w3.eth.contract(address=a_addr, abi=pool_abi)
        clean_pairs.append({
            "id": f"{b_sym}_{q_sym}",
            "name": f"{b_sym} / {q_sym}",
            "base_symbol": b_sym,
            "quote_symbol": q_sym,
            "base_decimals": TOKENS_EXTRA[b_sym][1],
            "quote_decimals": TOKENS_EXTRA[q_sym][1],
            "is_quote_eth": is_q_eth,
            "pool_a": {
                "name": "Uniswap V3",
                "address": u_addr,
                "type": "v3",
                "fee_bps": u_fee,
                "token0_is_base": (c_u.functions.token0().call().lower() == tA.lower())
            },
            "pool_b": {
                "name": f"Aerodrome {'Stable' if a_stb else 'V2'}",
                "address": a_addr,
                "type": "v2",
                "fee_bps": 5 if a_stb else 30,
                "token0_is_base": (c_a.functions.token0().call().lower() == tA.lower())
            }
        })
        print(f"[+] Aggiunta: {b_sym}/{q_sym}")

print(f"\nTOTALE DEFINITIVO: {len(clean_pairs)} coppie attive e certificate!")
with open("data/25_pairs_config.json", "w") as f:
    json.dump(clean_pairs, f, indent=4)
