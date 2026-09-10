import sqlite3

conn = sqlite3.connect("data/market_history.db")
c = conn.cursor()

print("--- TOP 10 SPREAD PER VIRTUAL / WETH ---")
c.execute("""
    SELECT timestamp, block_number, buy_dex, sell_dex, gross_spread_pct, net_spread_pct, sim_profit_usd 
    FROM price_ticks 
    WHERE pair = 'VIRTUAL / WETH' 
    ORDER BY net_spread_pct DESC 
    LIMIT 10
""")
for r in c.fetchall():
    print(f"  [{r[0]}] Blk #{r[1]} | {r[2]} -> {r[3]} | Gross: {r[4]:+.3f}% | Net: {r[5]:+.3f}% | Sim Profit: ${r[6]:.4f}")

print("\n--- TOP 10 SPREAD PER WETH / USDC ---")
c.execute("""
    SELECT timestamp, block_number, buy_dex, sell_dex, gross_spread_pct, net_spread_pct 
    FROM price_ticks 
    WHERE pair = 'WETH / USDC' 
    ORDER BY net_spread_pct DESC 
    LIMIT 10
""")
for r in c.fetchall():
    print(f"  [{r[0]}] Blk #{r[1]} | {r[2]} -> {r[3]} | Gross: {r[4]:+.3f}% | Net: {r[5]:+.3f}%")
