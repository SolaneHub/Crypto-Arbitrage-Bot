from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://base-rpc.publicnode.com"))

UNI_FACTORY = Web3.to_checksum_address("0x33128a8fC17869897dcE68Ed026d694621f6FDfD")
AERO_FACTORY = Web3.to_checksum_address("0x420DD381b31aEf6683db6B902084cB0FFECe40Da")

WETH = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")
USDC = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
cbBTC = Web3.to_checksum_address("0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf")
wstETH = Web3.to_checksum_address("0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452")
AERO = Web3.to_checksum_address("0x940181a94A35A4569E4529A3CDfB74e38FD98631")
VIRTUAL = Web3.to_checksum_address("0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b")

uni_abi = [{"inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}, {"name": "fee", "type": "uint24"}], "name": "getPool", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}]
aero_abi = [{"inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}, {"name": "stable", "type": "bool"}], "name": "getPool", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}]

uni_fac = w3.eth.contract(address=UNI_FACTORY, abi=uni_abi)
aero_fac = w3.eth.contract(address=AERO_FACTORY, abi=aero_abi)

PAIRS_TO_CHECK = [
    ("cbBTC / WETH", cbBTC, WETH),
    ("cbBTC / USDC", cbBTC, USDC),
    ("wstETH / WETH", wstETH, WETH),
    ("AERO / WETH", AERO, WETH),
    ("AERO / USDC", AERO, USDC),
    ("VIRTUAL / WETH", VIRTUAL, WETH),
    ("VIRTUAL / USDC", VIRTUAL, USDC),
    ("WETH / USDC", WETH, USDC)
]

print("=== VERIFICA COPPIE LEGITTIME CROSS-DEX (UNISWAP V3 vs AERODROME) ===")
for name, tA, tB in PAIRS_TO_CHECK:
    # Check Uni V3 (fee 500, 3000)
    p_uni_500 = uni_fac.functions.getPool(tA, tB, 500).call()
    p_uni_3000 = uni_fac.functions.getPool(tA, tB, 3000).call()
    
    # Check Aero V2 (stable=False, stable=True)
    p_aero_vol = aero_fac.functions.getPool(tA, tB, False).call()
    p_aero_stb = aero_fac.functions.getPool(tA, tB, True).call()
    
    print(f"\n[+] {name}:")
    print(f"    - Uniswap V3 (0.05%): {p_uni_500}")
    print(f"    - Uniswap V3 (0.30%): {p_uni_3000}")
    print(f"    - Aerodrome Volatile: {p_aero_vol}")
    print(f"    - Aerodrome Stable  : {p_aero_stb}")
