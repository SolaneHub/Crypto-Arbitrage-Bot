import sqlite3

conn = sqlite3.connect("data/market_history.db")
c = conn.cursor()

c.execute("SELECT timestamp, block_number, buy_dex, buy_price, sell_dex, sell_price, gross_spread_pct, net_spread_pct FROM price_ticks WHERE pair = 'wstETH / WETH' ORDER BY id DESC LIMIT 5")
print("--- ULTIMI 5 TICK wstETH / WETH ---")
for r in c.fetchall():
    print(f"[{r[0]}] Blk #{r[1]} | Buy: {r[2]} ({r[3]:.6f}) -> Sell: {r[4]} ({r[5]:.6f}) | Gross: {r[6]:+.3f}% | Net: {r[7]:+.3f}%")

c.execute("SELECT timestamp, block_number, buy_dex, buy_price, sell_dex, sell_price, gross_spread_pct, net_spread_pct FROM price_ticks WHERE pair = 'WETH / USDC' ORDER BY id DESC LIMIT 5")
print("\n--- ULTIMI 5 TICK WETH / USDC ---")
for r in c.fetchall():
    print(f"[{r[0]}] Blk #{r[1]} | Buy: {r[2]} (${r[3]:.2f}) -> Sell: {r[4]} (${r[5]:.2f}) | Gross: {r[6]:+.3f}% | Net: {r[7]:+.3f}%")
