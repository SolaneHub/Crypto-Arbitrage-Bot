import time
from scanner.price_scanner import MultiPairArbitrageScanner

t0 = time.perf_counter()
scanner = MultiPairArbitrageScanner()
cycle = scanner.scan_cycle()
t1 = time.perf_counter()

elapsed_ms = (t1 - t0) * 1000.0

print(f"=== TEST SCAN SU 25 COPPIE NO-MEME ===")
print(f"Blocco monitorato: #{cycle['block']}")
print(f"Tempo di esecuzione totale: {elapsed_ms:.1f} ms")
print(f"Gas Price: {cycle['gas_price_gwei']:.4f} Gwei (Gas/Tx: ${cycle['gas_cost_usd']:.4f})")
print(f"Coppie analizzate con successo: {len(cycle['pairs'])} su 25\n")

print(f"{'Coppia':<16} | {'Buy DEX':<16} | {'Prezzo Buy':>12} | {'Sell DEX':<16} | {'Prezzo Sell':>12} | {'Spread %':>10} | {'Netto %':>9} | {'Stato':<10}")
print("-" * 115)

for p in cycle["pairs"]:
    p_fmt = ".2f" if "USDC" in p["pair"] and "cbBTC" in p["pair"] else (".4f" if "USDC" in p["pair"] else ".8f")
    net_s = "+" if p["net_pct"] > 0 else ""
    gross_s = "+" if p["gross_pct"] > 0 else ""
    tag = "[PROFITTO!]" if p["is_profitable"] else "[attesa]"
    print(
        f"{p['pair']:<16} | {p['buy_dex']:<16} | {p['buy_price']:>12{p_fmt}} | "
        f"{p['sell_dex']:<16} | {p['sell_price']:>12{p_fmt}} | {gross_s}{p['gross_pct']:>9.3f}% | {net_s}{p['net_pct']:>8.3f}% | {tag:<10}"
    )
