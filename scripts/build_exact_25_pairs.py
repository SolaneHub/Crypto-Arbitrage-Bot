import json
from web3 import Web3
from scanner.multicall import MulticallManager
from scanner.pools import PoolDecoder
from config.settings import RPC_ENDPOINTS, MULTICALL3_ADDRESS

manager = MulticallManager(RPC_ENDPOINTS, MULTICALL3_ADDRESS)

UNI_FACTORY = Web3.to_checksum_address("0x33128a8fC17869897dcE68Ed026d694621f6FDfD")
AERO_FACTORY = Web3.to_checksum_address("0x420DD381b31aEf6683db6B902084cB0FFECe40Da")
uni_fac = manager.w3.eth.contract(address=UNI_FACTORY, abi=[{"inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}, {"name": "fee", "type": "uint24"}], "name": "getPool", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}])
aero_fac = manager.w3.eth.contract(address=AERO_FACTORY, abi=[{"inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}, {"name": "stable", "type": "bool"}], "name": "getPool", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}])
pool_abi = [{"inputs": [], "name": "token0", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}, {"inputs": [], "name": "liquidity", "outputs": [{"name": "", "type": "uint128"}], "stateMutability": "view", "type": "function"}]
v2_abi = [{"inputs": [], "name": "getReserves", "outputs": [{"name": "r0", "type": "uint112"}, {"name": "r1", "type": "uint112"}, {"name": "t", "type": "uint32"}], "stateMutability": "view", "type": "function"}, {"inputs": [], "name": "token0", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}]

TOKENS = {
    "WETH": ("0x4200000000000000000000000000000000000006", 18),
    "USDC": ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 6),
    "USDT": ("0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2", 6),
    "EURC": ("0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42", 6),
    "DAI": ("0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb", 18),
    "USDbC": ("0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA", 6),
    "cbBTC": ("0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf", 8),
    "wstETH": ("0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452", 18),
    "cbETH": ("0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22", 18),
    "rETH": ("0xB6fe221Fe9EeF5aBa221c348bA20A1Bf5e73624c", 18),
    "weETH": ("0x04C0599Ae5A44757c0af6F9eC3b93da8976c150A", 18),
    "ezETH": ("0x2416092f143378750bb29b79eD961ab195CcEea5", 18),
    "AERO": ("0x940181a94A35A4569E4529A3CDfB74e38FD98631", 18),
    "VIRTUAL": ("0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b", 18),
    "SEAM": ("0x1C7a460413dD4e964f96D8dFC56E7223cE88CD85", 18),
    "SNX": ("0x22e6966B799c4D5B13BE962E1D117b56327FDa66", 18)
}

TARGET_25_PAIRS = [
    # 1. Bitcoin Core (2)
    ("cbBTC", "WETH"),
    ("cbBTC", "USDC"),
    # 2. Liquid Staking & Restaking (5)
    ("wstETH", "WETH"),
    ("cbETH", "WETH"),
    ("rETH", "WETH"),
    ("ezETH", "WETH"),
    ("wstETH", "USDC"),
    # 3. Stablecoin & Foreign Exchange FX (8)
    ("USDC", "EURC"),
    ("USDT", "USDC"),
    ("DAI", "USDC"),
    ("USDbC", "USDC"),
    ("USDT", "WETH"),
    ("DAI", "WETH"),
    ("EURC", "WETH"),
    ("USDbC", "WETH"),
    # 4. Native Base Ecosystem & AI (10)
    ("WETH", "USDC"),
    ("AERO", "WETH"),
    ("AERO", "USDC"),
    ("AERO", "cbBTC"),
    ("VIRTUAL", "WETH"),
    ("VIRTUAL", "USDC"),
    ("SEAM", "WETH"),
    ("SEAM", "USDC"),
    ("SNX", "USDC"),
    ("USDbC", "USDT")
]

final_25 = []
print("COSTRUZIONE E VERIFICA DELLE 25 COPPIE NO-MEME:")
for b_sym, q_sym in TARGET_25_PAIRS:
    tA = Web3.to_checksum_address(TOKENS[b_sym][0])
    tB = Web3.to_checksum_address(TOKENS[q_sym][0])
    
    # Trova pool Uni V3
    u_addr = None
    u_fee = 30
    for f in [500, 3000, 100, 10000]:
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
                
    # Trova pool Aero
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
                
    if not u_addr or not a_addr:
        print(f"[-] Errore su {b_sym}/{q_sym}: u={u_addr}, a={a_addr}")
        continue
        
    c_u = manager.w3.eth.contract(address=u_addr, abi=pool_abi)
    c_a = manager.w3.eth.contract(address=a_addr, abi=pool_abi)
    
    final_25.append({
        "id": f"{b_sym}_{q_sym}",
        "name": f"{b_sym} / {q_sym}",
        "base_symbol": b_sym,
        "quote_symbol": q_sym,
        "base_decimals": TOKENS[b_sym][1],
        "quote_decimals": TOKENS[q_sym][1],
        "is_quote_eth": (q_sym == "WETH"),
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
    print(f"[{len(final_25):>2}/25] OK: {b_sym}/{q_sym:<6} | UniV3: {u_addr[:10]}... | Aero: {a_addr[:10]}...")

print(f"\nTOTALE COMPLETATO: {len(final_25)} coppie certificate!")
with open("data/25_pairs_config.json", "w") as f:
    json.dump(final_25, f, indent=4)
