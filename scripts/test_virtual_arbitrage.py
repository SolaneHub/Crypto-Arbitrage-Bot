from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://base-rpc.publicnode.com"))

POOL_UNI = Web3.to_checksum_address("0xE31c372a7Af875b3B5E0F3713B17ef51556da667")
POOL_AERO = Web3.to_checksum_address("0x21594b992F68495dD28d605834b58889d0a727c7")

v2_abi = [{"inputs": [], "name": "getReserves", "outputs": [{"name": "r0", "type": "uint112"}, {"name": "r1", "type": "uint112"}, {"name": "t", "type": "uint32"}], "stateMutability": "view", "type": "function"}]

c_uni = w3.eth.contract(address=POOL_UNI, abi=v2_abi)
c_aero = w3.eth.contract(address=POOL_AERO, abi=v2_abi)

r0_u, r1_u, _ = c_uni.functions.getReserves().call()
r0_a, r1_a, _ = c_aero.functions.getReserves().call()

# Uniswap V2: fee = 0.3% (997/1000)
# Aerodrome: fee = 0.3% o 0.05% (controlliamo fee)
# Prezzo Uni: r1_u / r0_u (WETH per VIRTUAL)
p_uni = r1_u / r0_u
p_aero = r1_a / r0_a

print(f"Prezzo Uniswap:   {p_uni:.8f} WETH ({p_uni * 2465:.4f} USD)")
print(f"Prezzo Aerodrome: {p_aero:.8f} WETH ({p_aero * 2465:.4f} USD)")
spread_pct = ((p_aero - p_uni) / p_uni) * 100
print(f"Spread Spot Lordo: {spread_pct:+.3f}%\n")

# Funzione V2 getAmountOut
def get_amount_out(amount_in, reserve_in, reserve_out, fee_bps=30):
    amount_in_with_fee = amount_in * (10000 - fee_bps)
    numerator = amount_in_with_fee * reserve_out
    denominator = (reserve_in * 10000) + amount_in_with_fee
    return numerator // denominator

# Simuliamo l'arbitraggio per vari importi in WETH
print(f"{'Capitale In (WETH)':<20} | {'Capitale In ($)':<16} | {'WETH Uscita':<16} | {'Netto (WETH)':<14} | {'Netto ($)':<10} | {'ROI %':<8}")
print("-" * 95)

eth_price = 2465.0
for weth_in_float in [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]:
    weth_in = int(weth_in_float * 10**18)
    
    # Leg 1: Compra VIRTUAL su Uniswap con WETH (in=r1_u, out=r0_u)
    virtual_bought = get_amount_out(weth_in, r1_u, r0_u, fee_bps=30)
    
    # Leg 2: Vendi VIRTUAL su Aerodrome per WETH (in=r0_a, out=r1_a)
    # Su Aerodrome la pool volatile ha fee_bps = 30 o 5? Proviamo 30 (conservativo)
    weth_received = get_amount_out(virtual_bought, r0_a, r1_a, fee_bps=30)
    
    diff_weth = (weth_received - weth_in) / 10**18
    diff_usd = diff_weth * eth_price
    roi = (diff_weth / weth_in_float) * 100
    
    sign = "+" if diff_weth > 0 else ""
    tag = " [PROFITTO!]" if diff_weth > 0 else ""
    print(f"{weth_in_float:<20.2f} | ${weth_in_float * eth_price:<15.2f} | {weth_received / 10**18:<16.4f} | {sign}{diff_weth:<13.5f} | {sign}${diff_usd:<9.2f} | {sign}{roi:<7.3f}%{tag}")
