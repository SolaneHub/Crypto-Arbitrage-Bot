from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://base-rpc.publicnode.com"))

AERO = Web3.to_checksum_address("0x940181a94A35A4569E4529A3CDfB74e38FD98631")
USDC = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
WETH = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")
BRETT = Web3.to_checksum_address("0x532f27101965dd16442E59d40670FaF5eBB142E4")

UNI_V3_FACTORY = Web3.to_checksum_address("0x33128a8fC17869897dcE68Ed026d694621f6FDfD")
factory_abi = [{"inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}, {"name": "fee", "type": "uint24"}], "name": "getPool", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}]

factory = w3.eth.contract(address=UNI_V3_FACTORY, abi=factory_abi)

print("UNISWAP V3 POOLS FOR AERO:")
for fee in [500, 3000, 10000]:
    p_usdc = factory.functions.getPool(AERO, USDC, fee).call()
    p_weth = factory.functions.getPool(AERO, WETH, fee).call()
    print(f"Fee {fee/10000}% -> AERO/USDC: {p_usdc} | AERO/WETH: {p_weth}")

# Inspect BRETT Aerodrome
brett_aero = Web3.to_checksum_address("0x4e829F8A5213c42535AB84AA40BD4aDCCE9cBa02")
print("\nBRETT Aerodrome pool functions:")
# Check if slot0 exists
s_abi = [{"inputs": [], "name": "slot0", "outputs": [{"name": "sqrtPriceX96", "type": "uint160"}, {"name": "tick", "type": "int24"}, {"name": "oi", "type": "uint16"}, {"name": "oc", "type": "uint16"}, {"name": "ocn", "type": "uint16"}, {"name": "feeProtocol", "type": "uint8"}, {"name": "unlocked", "type": "bool"}], "stateMutability": "view", "type": "function"}]
c = w3.eth.contract(address=brett_aero, abi=s_abi)
try:
    res = c.functions.slot0().call()
    print("  HAS slot0()! (Aerodrome Slipstream CL pool), sqrtPriceX96:", res[0])
except Exception as e:
    print("  slot0 err:", e)
