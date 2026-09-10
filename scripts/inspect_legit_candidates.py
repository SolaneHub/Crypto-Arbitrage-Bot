import requests

TOKENS = {
    "cbBTC": "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
    "wstETH": "0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452",
    "cbETH": "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22",
    "LINK": "0x88Rb94F5a7aB03C3503a6C4d3209B1f3b3cDcb90", # let us check LINK on Base
    "AERO": "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
    "VIRTUAL": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b"
}

# Real Base LINK address: 0x88Fb150BDc53A65fe94EdA0c9BA91307861AA564
TOKENS["LINK"] = "0x88Fb150BDc53A65fe94EdA0c9BA91307861AA564"

for name, addr in TOKENS.items():
    url = f"https://api.dexscreener.com/latest/dex/tokens/{addr}"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        pairs = r.json().get("pairs", [])
        base_pairs = [p for p in pairs if p.get("chainId") == "base"]
        print(f"\n[+] {name} ({addr[:10]}...) - {len(base_pairs)} coppie su Base:")
        sorted_pairs = sorted(base_pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0) or 0), reverse=True)[:3]
        for p in sorted_pairs:
            dex = p.get("dexId")
            b_sym = p.get("baseToken", {}).get("symbol")
            q_sym = p.get("quoteToken", {}).get("symbol")
            p_addr = p.get("pairAddress")
            liq = float(p.get("liquidity", {}).get("usd", 0) or 0)
            vol = float(p.get("volume", {}).get("h24", 0) or 0)
            price = p.get("priceUsd", "N/A")
            print(f"    - {dex:<12} | {b_sym}/{q_sym:<6} | Prezzo: ${price} | Liq: ${liq:>11,.0f} | Vol24h: ${vol:>11,.0f} | {p_addr}")
