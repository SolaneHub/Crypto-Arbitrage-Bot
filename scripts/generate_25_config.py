import json
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://base-rpc.publicnode.com"))

UNI_FACTORY = Web3.to_checksum_address("0x33128a8fC17869897dcE68Ed026d694621f6FDfD")
AERO_FACTORY = Web3.to_checksum_address("0x420DD381b31aEf6683db6B902084cB0FFECe40Da")

uni_fac = w3.eth.contract(address=UNI_FACTORY, abi=[{"inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}, {"name": "fee", "type": "uint24"}], "name": "getPool", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}])
aero_fac = w3.eth.contract(address=AERO_FACTORY, abi=[{"inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}, {"name": "stable", "type": "bool"}], "name": "getPool", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}])

erc_abi = [{"inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "stateMutability": "view", "type": "function"}, {"inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"}]
pool_abi = [{"inputs": [], "name": "token0", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}, {"inputs": [], "name": "fee", "outputs": [{"name": "", "type": "uint24"}], "stateMutability": "view", "type": "function"}]

TOKENS = {
    "WETH": "0x4200000000000000000000000000000000000006",
    "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
    "EURC": "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42",
    "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
    "USDbC": "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA",
    "cbBTC": "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
    "tBTC": "0x236aa50979D5f3De3Bd1Eeb40E81137F22ab794b",
    "wstETH": "0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452",
    "cbETH": "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22",
    "rETH": "0xB6fe221Fe9EeF5aBa221c348bA20A1Bf5e73624c",
    "weETH": "0x04C0599Ae5A44757c0af6F9eC3b93da8976c150A",
    "ezETH": "0x2416092f143378750bb29b79eD961ab195CcEea5",
    "AERO": "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
    "VIRTUAL": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",
    "SEAM": "0x1C7a460413dD4e964f96D8dFC56E7223cE88CD85",
    "SNX": "0x22e6966B799c4D5B13BE962E1D117b56327FDa66"
}

TOKEN_DECIMALS = {}
for sym, addr in TOKENS.items():
    c = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=erc_abi)
    TOKEN_DECIMALS[sym] = c.functions.decimals().call()

PAIRS_25 = [
    ("cbBTC", "WETH"),
    ("cbBTC", "USDC"),
    ("tBTC", "cbBTC"),
    ("tBTC", "WETH"),
    ("wstETH", "WETH"),
    ("cbETH", "WETH"),
    ("rETH", "WETH"),
    ("weETH", "WETH"),
    ("ezETH", "WETH"),
    ("cbETH", "cbBTC"),
    ("USDC", "EURC"),
    ("USDT", "USDC"),
    ("DAI", "USDC"),
    ("USDbC", "USDC"),
    ("USDT", "WETH"),
    ("DAI", "WETH"),
    ("WETH", "USDC"),
    ("AERO", "WETH"),
    ("AERO", "USDC"),
    ("VIRTUAL", "WETH"),
    ("VIRTUAL", "USDC"),
    ("SEAM", "WETH"),
    ("SNX", "WETH"),
    ("wstETH", "USDC"),
    ("cbETH", "USDC")
]

config_list = []
for base_sym, quote_sym in PAIRS_25:
    tA = Web3.to_checksum_address(TOKENS[base_sym])
    tB = Web3.to_checksum_address(TOKENS[quote_sym])
    
    # 1. Trova pool Uniswap V3 (500, 3000, 100)
    uni_addr = None
    uni_fee_bps = 30
    for f in [500, 3000, 100]:
        p = uni_fac.functions.getPool(tA, tB, f).call()
        if p != "0x0000000000000000000000000000000000000000":
            uni_addr = p
            uni_fee_bps = f // 100 # 5, 30, 1
            break
            
    # 2. Trova pool Aerodrome (volatile o stable)
    aero_addr = None
    aero_is_stable = False
    for stb in [False, True]:
        p = aero_fac.functions.getPool(tA, tB, stb).call()
        if p != "0x0000000000000000000000000000000000000000":
            aero_addr = p
            aero_is_stable = stb
            break
            
    if not uni_addr or not aero_addr:
        print(f"Skipping {base_sym}/{quote_sym}: uni={uni_addr}, aero={aero_addr}")
        continue
        
    # Check token0
    c_u = w3.eth.contract(address=uni_addr, abi=pool_abi)
    u_t0 = c_u.functions.token0().call()
    u_t0_is_base = (u_t0.lower() == tA.lower())
    
    c_a = w3.eth.contract(address=aero_addr, abi=pool_abi)
    a_t0 = c_a.functions.token0().call()
    a_t0_is_base = (a_t0.lower() == tA.lower())
    
    aero_fee_bps = 5 if aero_is_stable else 30
    
    pair_id = f"{base_sym}_{quote_sym}"
    pair_name = f"{base_sym} / {quote_sym}"
    
    config_list.append({
        "id": pair_id,
        "name": pair_name,
        "base_symbol": base_sym,
        "quote_symbol": quote_sym,
        "base_decimals": TOKEN_DECIMALS[base_sym],
        "quote_decimals": TOKEN_DECIMALS[quote_sym],
        "is_quote_eth": (quote_sym == "WETH"),
        "pool_a": {
            "name": "Uniswap V3",
            "address": uni_addr,
            "type": "v3",
            "fee_bps": uni_fee_bps,
            "token0_is_base": u_t0_is_base
        },
        "pool_b": {
            "name": f"Aerodrome {'Stable' if aero_is_stable else 'V2'}",
            "address": aero_addr,
            "type": "v2",
            "fee_bps": aero_fee_bps,
            "token0_is_base": a_t0_is_base
        }
    })

print(f"Generata con successo configurazione per {len(config_list)} coppie!")
with open("data/25_pairs_config.json", "w") as f:
    json.dump(config_list, f, indent=4)
