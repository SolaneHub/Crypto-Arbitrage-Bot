import requests
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://base-rpc.publicnode.com"))

# Factories su Base
UNI_V3_FACTORY = Web3.to_checksum_address("0x33128a8fC17869897dcE68Ed026d694621f6FDfD")
AERO_V2_FACTORY = Web3.to_checksum_address("0x420DD381b31aEf6683db6B902084cB0FFECe40Da")
PANCAKE_V3_FACTORY = Web3.to_checksum_address("0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865")
BASESWAP_V2_FACTORY = Web3.to_checksum_address("0xFDa619b6d20975be80A10332cD39b9a4b0FAa8BB")

uni_fac_abi = [{"inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}, {"name": "fee", "type": "uint24"}], "name": "getPool", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}]
aero_fac_abi = [{"inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}, {"name": "stable", "type": "bool"}], "name": "getPool", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}]
v2_fac_abi = [{"inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}], "name": "getPair", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}]

uni_fac = w3.eth.contract(address=UNI_V3_FACTORY, abi=uni_fac_abi)
aero_fac = w3.eth.contract(address=AERO_V2_FACTORY, abi=aero_fac_abi)
baseswap_fac = w3.eth.contract(address=BASESWAP_V2_FACTORY, abi=v2_fac_abi)

# Token Address Ufficiali su Base
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
    "EXTRA": "0x6738011F44F76Da3634125bB7dC50117d9A56930",
    "SEAM": "0x1C7a460413dD4e964f96D8dFC56E7223cE88CD85",
    "SNX": "0x22e6966B799c4D5B13BE962E1D117b56327FDa66",
    "CRV": "0x8ee73c484A261066776a5ce9e4320E6BC0565b44",
    "LINK": "0x88Fb150BDc53A65fe94EdA0c9BA91307861AA564"
}

# Candidati per le 25 coppie
PAIR_COMBINATIONS = [
    # Bitcoin
    ("cbBTC", "WETH"),
    ("cbBTC", "USDC"),
    ("tBTC", "cbBTC"),
    ("tBTC", "WETH"),
    # LST / LRT Liquid Staking Pegs
    ("wstETH", "WETH"),
    ("cbETH", "WETH"),
    ("rETH", "WETH"),
    ("weETH", "WETH"),
    ("ezETH", "WETH"),
    # Stablecoin Arbitrage
    ("USDC", "EURC"),
    ("USDT", "USDC"),
    ("DAI", "USDC"),
    ("USDbC", "USDC"),
    # Core & DeFi Ecosystem
    ("WETH", "USDC"),
    ("AERO", "WETH"),
    ("AERO", "USDC"),
    ("VIRTUAL", "WETH"),
    ("VIRTUAL", "USDC"),
    ("EXTRA", "WETH"),
    ("SEAM", "WETH"),
    ("SNX", "WETH"),
    ("CRV", "WETH"),
    ("LINK", "USDC"),
    ("cbETH", "cbBTC"),
    ("wstETH", "USDC")
]

print(f"VERIFICA DISPONIBILITA' MULTI-DEX PER LE 25 COPPIE:")
verified_count = 0
for tA_sym, tB_sym in PAIR_COMBINATIONS:
    if tA_sym not in TOKENS or tB_sym not in TOKENS:
        continue
    tA = Web3.to_checksum_address(TOKENS[tA_sym])
    tB = Web3.to_checksum_address(TOKENS[tB_sym])
    
    # 1. Cerca Uniswap V3 (500, 3000, 100)
    uni_pool = None
    uni_fee = 0
    for f in [100, 500, 3000]:
        p = uni_fac.functions.getPool(tA, tB, f).call()
        if p != "0x0000000000000000000000000000000000000000":
            uni_pool = p
            uni_fee = f
            break
            
    # 2. Cerca Aerodrome (volatile o stable)
    aero_pool = None
    aero_type = ""
    for stb in [False, True]:
        p = aero_fac.functions.getPool(tA, tB, stb).call()
        if p != "0x0000000000000000000000000000000000000000":
            aero_pool = p
            aero_type = "Stable" if stb else "Volatile"
            break
            
    # 3. Cerca BaseSwap V2
    baseswap_pool = baseswap_fac.functions.getPair(tA, tB).call()
    
    pair_name = f"{tA_sym}/{tB_sym}"
    dex_found = []
    if uni_pool:
        dex_found.append(f"UniV3({uni_fee/10000}%)")
    if aero_pool:
        dex_found.append(f"Aero({aero_type})")
    if baseswap_pool != "0x0000000000000000000000000000000000000000":
        dex_found.append("BaseSwapV2")
        
    status = "[OK MULTI-DEX]" if len(dex_found) >= 2 else "[SOLO 1 DEX]"
    if len(dex_found) >= 2:
        verified_count += 1
    print(f"{pair_name:<16} | {status:<15} | DEX: {', '.join(dex_found)}")

print(f"\nTotale coppie verificate con almeno 2 DEX attivi: {verified_count}")
