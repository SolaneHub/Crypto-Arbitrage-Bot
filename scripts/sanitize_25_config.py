import json
from web3 import Web3
from scanner.multicall import MulticallManager
from scanner.pools import PoolDecoder
from config.settings import RPC_ENDPOINTS, MULTICALL3_ADDRESS

with open("data/25_pairs_config.json", "r") as f:
    pairs = json.load(f)

# Fix AERO / WETH to the active 0.3% pool
for p in pairs:
    if p["id"] == "AERO_WETH":
        p["pool_a"]["address"] = "0x3d5D143381916280ff91407FeBEB52f2b60f33Cf"
        p["pool_a"]["fee_bps"] = 30
        p["pool_a"]["token0_is_base"] = False

# Eseguiamo un ciclo di MulticallManager per testare i prezzi di tutte e 25
manager = MulticallManager(RPC_ENDPOINTS, MULTICALL3_ADDRESS)

calls = []
for p in pairs:
    for k in ("pool_a", "pool_b"):
        calls.append({
            "target": Web3.to_checksum_address(p[k]["address"]),
            "allowFailure": True,
            "callData": PoolDecoder.get_calldata(p[k]["type"])
        })

blk, raw_results = manager.aggregate(calls)

valid_pairs = []
idx = 0
print(f"VERIFICA PREZZI ON-CHAIN AL BLOCCO #{blk}:")
for p in pairs:
    s_a, d_a = raw_results[idx]
    idx += 1
    s_b, d_b = raw_results[idx]
    idx += 1
    
    if not s_a or not s_b or not d_a or not d_b:
        print(f"[-] Scartata {p['name']}: chiamata fallita")
        continue
        
    state_a = PoolDecoder.decode_pool_state(p["pool_a"], p, d_a)
    state_b = PoolDecoder.decode_pool_state(p["pool_b"], p, d_b)
    
    if not state_a or not state_b:
        print(f"[-] Scartata {p['name']}: decodifica fallita")
        continue
        
    p_a = state_a["price"]
    p_b = state_b["price"]
    
    # Sanity check sui prezzi: non devono essere NaN, zero o astronomici
    if p_a <= 0 or p_b <= 0 or p_a > 1e10 or p_b > 1e10 or p_a < 1e-10 or p_b < 1e-10:
        print(f"[-] Scartata {p['name']}: prezzo fuori scala (p_a={p_a}, p_b={p_b})")
        continue
        
    # Calcolo spread
    min_p = min(p_a, p_b)
    max_p = max(p_a, p_b)
    spread = ((max_p - min_p) / min_p) * 100.0
    
    # Se lo spread è superiore al 50%, significa che uno dei due pool ha liquidità abbandonata/disallineata
    if spread > 50.0:
        print(f"[-] Scartata {p['name']}: spread anomalo {spread:.1f}% (pool disallineata/illiquida)")
        continue
        
    valid_pairs.append(p)
    print(f"[+] OK: {p['name']:<16} | {p['pool_a']['name']}: {p_a:.6f} | {p['pool_b']['name']}: {p_b:.6f} | Spread: {spread:.3f}%")

print(f"\nCoppie finali validate ad altissima qualita e liquidita reale: {len(valid_pairs)}")

# Salva la lista pulita e certificata
with open("data/25_pairs_config.json", "w") as f:
    json.dump(valid_pairs, f, indent=4)
