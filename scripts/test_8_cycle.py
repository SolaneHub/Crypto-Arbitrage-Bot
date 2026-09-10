from scanner.price_scanner import MultiPairArbitrageScanner

s = MultiPairArbitrageScanner()
cycle = s.scan_cycle()

print(f"Blocco monitorato: #{cycle['block']}")
print(f"Gas Price: {cycle['gas_price_gwei']:.4f} Gwei (Gas/Tx: ${cycle['gas_cost_usd']:.4f})")
print(f"Coppie scansionate con successo: {len(cycle['pairs'])} su 8\n")

print(f"{'Coppia':<16} | {'Buy DEX':<14} | {'Prezzo Buy':>12} | {'Sell DEX':<14} | {'Prezzo Sell':>12} | {'Spread %':>10} | {'Netto %':>9}")
print("-" * 100)
for p in cycle["pairs"]:
    p_fmt = ".2f" if "USDC" in p["pair"] and "cbBTC" in p["pair"] else (".4f" if "USDC" in p["pair"] else ".8f")
    net_s = "+" if p["net_pct"] > 0 else ""
    gross_s = "+" if p["gross_pct"] > 0 else ""
    print(
        f"{p['pair']:<16} | {p['buy_dex']:<14} | {p['buy_price']:>12{p_fmt}} | "
        f"{p['sell_dex']:<14} | {p['sell_price']:>12{p_fmt}} | {gross_s}{p['gross_pct']:>9.3f}% | {net_s}{p['net_pct']:>8.3f}%"
    )
