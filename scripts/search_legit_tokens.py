import requests

# Query top volume pools on Base from GeckoTerminal
url = "https://api.geckoterminal.com/api/v2/networks/base/pools?page=1"
headers = {"Accept": "application/json;version=20230302"}

MEME_KEYWORDS = ["inu", "cat", "dog", "pepe", "shib", "trump", "elon", "pump", "moon", "brett", "toshi", "wif", "laptop", "frog"]

res = requests.get(url, headers=headers, timeout=10)
if res.status_code == 200:
    data = res.json().get("data", [])
    print(f"=== ANALISI POOL LEGITTIME SU BASE (SENZA MEMECOIN) ===")
    print(f"{'Coppia':<20} | {'DEX':<24} | {'Volume 24h ($)':>14} | {'Liquidita ($)':>14} | {'Indirizzo Pool':<44}")
    print("-" * 125)
    
    found = []
    for item in data:
        attr = item.get("attributes", {})
        name = attr.get("name", "")
        pool_addr = attr.get("address")
        dex = item.get("relationships", {}).get("dex", {}).get("data", {}).get("id", "")
        vol = float(attr.get("volume_usd", {}).get("h24") or 0)
        liq = float(attr.get("reserve_in_usd") or 0)
        
        # Filtra via memecoin evidenti
        is_meme = any(k in name.lower() for k in MEME_KEYWORDS)
        if is_meme or liq < 50000 or vol < 10000:
            continue
            
        print(f"{name:<20} | {dex:<24} | ${vol:>13,.0f} | ${liq:>13,.0f} | {pool_addr:<44}")
