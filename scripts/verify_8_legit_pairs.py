from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://base-rpc.publicnode.com"))

# 8 Coppie Legittime No-Meme
CANDIDATES = [
    {
        "pair": "cbBTC / WETH",
        "pool_a": ("Uniswap V3", "0x8c7080564B5A792A33Ef2FD473fbA6364d5495e5", "v3"),
        "pool_b": ("Aerodrome V2", "0x2578365B3dfA7FfE60108e181EFb79FeDdec2319", "v2"),
    },
    {
        "pair": "cbBTC / USDC",
        "pool_a": ("Uniswap V3", "0xeC558e484cC9f2210714E345298fdc53B253c27D", "v3"),
        "pool_b": ("Aerodrome V2", "0x9c38b55f9A9Aba91BbCEDEb12bf4428f47A6a0B8", "v2"),
    },
    {
        "pair": "wstETH / WETH",
        "pool_a": ("Uniswap V3", "0x6f4482cBF7b43599078fcb012732e20480015644", "v3"),
        "pool_b": ("Aerodrome V2", "0xA6385c73961dd9C58db2EF0c4EB98cE4B60651e8", "v2"),
    },
    {
        "pair": "AERO / WETH",
        "pool_a": ("Uniswap V3", "0x3d5D143381916280ff91407FeBEB52f2b60f33Cf", "v3"),
        "pool_b": ("Aerodrome V2", "0x7f670f78B17dEC44d5Ef68a48740b6f8849cc2e6", "v2"),
    },
    {
        "pair": "AERO / USDC",
        "pool_a": ("Uniswap V3", "0x2426DC0A657BD481ab48f86C1616431905901238", "v3"),
        "pool_b": ("Aerodrome V2", "0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d", "v2"),
    },
    {
        "pair": "VIRTUAL / WETH",
        "pool_a": ("Uniswap V2", "0xE31c372a7Af875b3B5E0F3713B17ef51556da667", "v2"),
        "pool_b": ("Aerodrome V2", "0x21594b992F68495dD28d605834b58889d0a727c7", "v2"),
    },
    {
        "pair": "VIRTUAL / USDC",
        "pool_a": ("Uniswap V3", "0x529d2863a1521d0b57db028168fdE2E97120017C", "v3"),
        "pool_b": ("Aerodrome V2", "0xDb79CecFd1897D2F60B0Ea7Af072CA9A9e71047c", "v2"),
    },
    {
        "pair": "WETH / USDC",
        "pool_a": ("Uniswap V3", "0xd0b53D9277642d899DF5C87A3966A349A798F224", "v3"),
        "pool_b": ("Aerodrome Volatile", "0xcDAC0d6c6C59727a65F871236188350531885C43", "v2"),
    }
]

t_abi = [
    {"inputs": [], "name": "token0", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "token1", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}
]
erc_abi = [{"inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "stateMutability": "view", "type": "function"}, {"inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"}]

print("VERIFICA TOKEN0 E TOKEN1 PER LE 8 COPPIE NO-MEME:")
for item in CANDIDATES:
    p_name = item["pair"]
    for dex_name, addr, p_type in [item["pool_a"], item["pool_b"]]:
        c = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=t_abi)
        t0 = c.functions.token0().call()
        t1 = c.functions.token1().call()
        s0 = w3.eth.contract(address=t0, abi=erc_abi).functions.symbol().call()
        s1 = w3.eth.contract(address=t1, abi=erc_abi).functions.symbol().call()
        d0 = w3.eth.contract(address=t0, abi=erc_abi).functions.decimals().call()
        d1 = w3.eth.contract(address=t1, abi=erc_abi).functions.decimals().call()
        print(f"[{p_name:<14}] {dex_name:<18} ({addr[:10]}...): token0={s0} ({d0} dec), token1={s1} ({d1} dec)")
