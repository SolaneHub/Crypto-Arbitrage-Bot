import json
from web3 import Web3
from scanner.multicall import MulticallManager

with open("data/25_pairs_config.json", "r") as f:
    pairs = json.load(f)

manager = MulticallManager(["https://base-rpc.publicnode.com"], "0xcA11bde05977b3631167028862bE2a173976CA11")
UNI_FACTORY = Web3.to_checksum_address("0x33128a8fC17869897dcE68Ed026d694621f6FDfD")
AERO_FACTORY = Web3.to_checksum_address("0x420DD381b31aEf6683db6B902084cB0FFECe40Da")
uf = manager.w3.eth.contract(address=UNI_FACTORY, abi=[{"inputs":[{"name":"tokenA","type":"address"},{"name":"tokenB","type":"address"},{"name":"fee","type":"uint24"}],"name":"getPool","outputs":[{"name":"","type":"address"}],"stateMutability":"view","type":"function"}])
af = manager.w3.eth.contract(address=AERO_FACTORY, abi=[{"inputs":[{"name":"tokenA","type":"address"},{"name":"tokenB","type":"address"},{"name":"stable","type":"bool"}],"name":"getPool","outputs":[{"name":"","type":"address"}],"stateMutability":"view","type":"function"}])

SNX = Web3.to_checksum_address("0x22e6966B799c4D5B13BE962E1D117b56327FDa66")
WETH = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")

u_addr = uf.functions.getPool(SNX, WETH, 500).call()
if u_addr == "0x0000000000000000000000000000000000000000":
    u_addr = uf.functions.getPool(SNX, WETH, 3000).call()
a_addr = af.functions.getPool(SNX, WETH, False).call()

pool_abi = [{"inputs":[],"name":"token0","outputs":[{"name":"","type":"address"}],"stateMutability":"view","type":"function"}]
cu = manager.w3.eth.contract(address=u_addr, abi=pool_abi)
ca = manager.w3.eth.contract(address=a_addr, abi=pool_abi)

pairs.append({
    "id": "SNX_WETH",
    "name": "SNX / WETH",
    "base_symbol": "SNX",
    "quote_symbol": "WETH",
    "base_decimals": 18,
    "quote_decimals": 18,
    "is_quote_eth": True,
    "pool_a": {
        "name": "Uniswap V3",
        "address": u_addr,
        "type": "v3",
        "fee_bps": 5,
        "token0_is_base": (cu.functions.token0().call().lower() == SNX.lower())
    },
    "pool_b": {
        "name": "Aerodrome V2",
        "address": a_addr,
        "type": "v2",
        "fee_bps": 30,
        "token0_is_base": (ca.functions.token0().call().lower() == SNX.lower())
    }
})

print("Coppie totali:", len(pairs))
with open("data/25_pairs_config.json", "w") as f:
    json.dump(pairs, f, indent=4)
