from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://base-rpc.publicnode.com"))

# Lista pool da verificare
test_pools = [
    {"pair": "VIRTUAL/WETH", "dex": "Uniswap V2", "addr": "0xE31c372a7Af875b3B5E0F3713B17ef51556da667"},
    {"pair": "VIRTUAL/WETH", "dex": "Aerodrome", "addr": "0x21594b992F68495dD28d605834b58889d0a727c7"},
    {"pair": "AERO/USDC", "dex": "Aerodrome", "addr": "0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d"},
    {"pair": "AERO/WETH", "dex": "Aerodrome", "addr": "0x7f670f78B17dEC44d5Ef68a48740b6f8849cc2e6"},
    {"pair": "BRETT/WETH", "dex": "Uniswap V3", "addr": "0xBA3F945812a83471d709BCe9C3CA699A19FB46f7"},
    {"pair": "BRETT/WETH", "dex": "Aerodrome", "addr": "0x4e829F8A5213c42535AB84AA40BD4aDCCE9cBa02"},
    {"pair": "DEGEN/WETH", "dex": "Uniswap V3", "addr": "0x0cA6485b7e9cF814A3Fd09d81672B07323535b64"},
    {"pair": "DEGEN/WETH", "dex": "Aerodrome", "addr": "0x2C4909355b0C036840819484c3A882A95659aBf3"}
]

abi = [
    {"inputs": [], "name": "token0", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "token1", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getReserves", "outputs": [{"name": "r0", "type": "uint112"}, {"name": "r1", "type": "uint112"}, {"name": "t", "type": "uint32"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "slot0", "outputs": [{"name": "sqrtPriceX96", "type": "uint160"}, {"name": "tick", "type": "int24"}, {"name": "oi", "type": "uint16"}, {"name": "oc", "type": "uint16"}, {"name": "ocn", "type": "uint16"}, {"name": "feeProtocol", "type": "uint8"}, {"name": "unlocked", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "fee", "outputs": [{"name": "", "type": "uint24"}], "stateMutability": "view", "type": "function"}
]

print("VERIFICA POOL ON-CHAIN:")
for p in test_pools:
    c = w3.eth.contract(address=Web3.to_checksum_address(p["addr"]), abi=abi)
    try:
        t0 = c.functions.token0().call()
        t1 = c.functions.token1().call()
        pool_type = "unknown"
        fee = "N/A"
        try:
            r0, r1, _ = c.functions.getReserves().call()
            pool_type = "V2 (getReserves)"
        except Exception:
            try:
                s0 = c.functions.slot0().call()
                fee_raw = c.functions.fee().call()
                pool_type = f"V3 (slot0) Fee: {fee_raw/10000}%"
            except Exception:
                pass
        print(f"[{p['pair']}] {p['dex']:<14} | Type: {pool_type:<24} | Addr: {p['addr']}")
    except Exception as e:
        print(f"[{p['pair']}] {p['dex']:<14} | ERRORE: {e}")
