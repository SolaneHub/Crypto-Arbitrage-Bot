import requests

TOKENS = {
    "AERO": "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
    "BRETT": "0x532f27101965dd16442E59d40670FaF5eBB142E4",
    "DEGEN": "0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed",
    "VIRTUAL": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b"
}

print("=== VERIFICA CROSS-DEX PER I TOKEN PIU ATTIVI SU BASE ===")
for symbol, addr in TOKENS.items():
    url = f"https://api.dexscreener.com/latest/dex/tokens/{addr}"
    res = requests.get(url, timeout=10)
    if res.status_code == 200:
        data = res.json()
        pairs = data.get("pairs", [])
        print(f"\n[+] {symbol} ({addr[:8]}...{addr[-6:]})")
        print(f"    Totale coppie attive: {len(pairs)}")
        
        # Filtra per DEX principali (Uniswap, Aerodrome, Sushi, Pancake)
        top_pairs = sorted(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0), reverse=True)[:4]
        for p in top_pairs:
            dex = p.get("dexId")
            base = p.get("baseToken", {}).get("symbol")
            quote = p.get("quoteToken", {}).get("symbol")
            price = p.get("priceUsd", "N/A")
            liq = float(p.get("liquidity", {}).get("usd", 0) or 0)
            vol24 = float(p.get("volume", {}).get("h24", 0) or 0)
            pair_addr = p.get("pairAddress")
            print(f"    - {dex:<12}: {base}/{quote:<5} | Prezzo: ${price} | Liq: ${liq:>10,.0f} | Vol 24h: ${vol24:>10,.0f} | Pool: {pair_addr}")
