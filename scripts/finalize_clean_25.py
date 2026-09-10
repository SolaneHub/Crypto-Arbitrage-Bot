import json
from web3 import Web3

with open("data/25_pairs_config.json", "r") as f:
    pairs = json.load(f)

# Rimuoviamo SNX_WETH
pairs = [p for p in pairs if p["id"] != "SNX_WETH"]

# Aggiungiamo cbBTC / USDbC
w3 = Web3(Web3.HTTPProvider("https://base-rpc.publicnode.com"))
cbBTC = Web3.to_checksum_address("0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf")
USDbC = Web3.to_checksum_address("0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA")

u_addr = Web3.to_checksum_address("0x72D0c3728EF9AF20EF0a1736cf6C21962d9b9873")
a_addr = Web3.to_checksum_address("0x2A88aD25aF542F6485b54709991D758c4F411d8f")

pool_abi = [{"inputs":[],"name":"token0","outputs":[{"name":"","type":"address"}],"stateMutability":"view","type":"function"}]
cu = w3.eth.contract(address=u_addr, abi=pool_abi)
ca = w3.eth.contract(address=a_addr, abi=pool_abi)

pairs.append({
    "id": "cbBTC_USDbC",
    "name": "cbBTC / USDbC",
    "base_symbol": "cbBTC",
    "quote_symbol": "USDbC",
    "base_decimals": 8,
    "quote_decimals": 6,
    "is_quote_eth": False,
    "pool_a": {
        "name": "Uniswap V3",
        "address": u_addr,
        "type": "v3",
        "fee_bps": 30,
        "token0_is_base": (cu.functions.token0().call().lower() == cbBTC.lower())
    },
    "pool_b": {
        "name": "Aerodrome V2",
        "address": a_addr,
        "type": "v2",
        "fee_bps": 30,
        "token0_is_base": (ca.functions.token0().call().lower() == cbBTC.lower())
    }
})

print("Coppie esatte:", len(pairs))
with open("data/25_pairs_config.json", "w") as f:
    json.dump(pairs, f, indent=4)
