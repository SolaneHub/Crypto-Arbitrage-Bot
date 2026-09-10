import requests
import json

def fetch_top_base_pairs():
    headers = {"Accept": "application/json;version=20230302"}
    
    # 1. GeckoTerminal Trending & Top Pools on Base
    url = "https://api.geckoterminal.com/api/v2/networks/base/trending_pools?page=1"
    res = requests.get(url, headers=headers, timeout=10)
    
    if res.status_code != 200:
        url = "https://api.geckoterminal.com/api/v2/networks/base/pools?page=1"
        res = requests.get(url, headers=headers, timeout=10)
        
    pools = []
    if res.status_code == 200:
        data = res.json()
        for item in data.get("data", []):
            attr = item.get("attributes", {})
            name = attr.get("name")
            address = attr.get("address")
            dex = item.get("relationships", {}).get("dex", {}).get("data", {}).get("id")
            vol_24h = float(attr.get("volume_usd", {}).get("h24") or 0)
            reserve_usd = float(attr.get("reserve_in_usd") or 0)
            change_24h = float(attr.get("price_change_percentage", {}).get("h24") or 0)
            tx_count = attr.get("transactions", {}).get("h24", {}).get("buys", 0) + attr.get("transactions", {}).get("h24", {}).get("sells", 0)
            
            pools.append({
                "name": name,
                "dex": dex,
                "address": address,
                "vol_24h": vol_24h,
                "liquidity_usd": reserve_usd,
                "change_24h": change_24h,
                "tx_count": tx_count
            })
            
    return pools

if __name__ == "__main__":
    pools = fetch_top_base_pairs()
    print(f"=== TOP POOL PIU ATTIVE E VOLATILI SU BASE (GECKOTERMINAL) ===")
    print(f"{'Coppia':<20} | {'DEX':<24} | {'Vol 24h ($)':>12} | {'Liquidita ($)':>14} | {'Var 24h %':>10} | {'Tx 24h':>8}")
    print("-" * 100)
    for p in pools[:15]:
        print(f"{p['name']:<20} | {p['dex']:<24} | {p['vol_24h']:>12,.0f} | {p['liquidity_usd']:>14,.0f} | {p['change_24h']:>+9.2f}% | {p['tx_count']:>8}")
