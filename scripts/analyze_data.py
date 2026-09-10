import sqlite3
import os

DB_PATH = "data/market_history.db"

def analyze():
    if not os.path.exists(DB_PATH):
        print(f"[!] Database non trovato in {DB_PATH}. Avvia prima lo scanner per raccogliere dati.")
        return

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Statistiche generali
        cursor.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp), MIN(block_number), MAX(block_number) FROM price_ticks")
        total_ticks, min_time, max_time, min_block, max_block = cursor.fetchone()

        if not total_ticks:
            print("[!] Il database e ancora vuoto.")
            return

        print("=" * 85)
        print("          REPORT ANALISI DATI RACCOLTI DALLO SCANNER")
        print(f"  Periodo: {min_time} -> {max_time} UTC")
        print(f"  Blocchi monitorati: #{min_block} -> #{max_block} (Totale campionamenti: {total_ticks})")
        print("=" * 85)

        # Statistiche per coppia
        cursor.execute("""
            SELECT 
                pair,
                COUNT(*),
                AVG(gross_spread_pct),
                MAX(gross_spread_pct),
                AVG(net_spread_pct),
                MAX(net_spread_pct),
                SUM(is_profitable)
            FROM price_ticks
            GROUP BY pair
            ORDER BY MAX(net_spread_pct) DESC
        """)
        rows = cursor.fetchall()

        print(f"\n{'Coppia':<18} | {'Campioni':>8} | {'Spread Medio':>12} | {'Spread Max':>11} | {'Netto Medio':>11} | {'Netto Max':>10} | {'Opportunita':>11}")
        print("-" * 92)
        for r in rows:
            pair, count, avg_g, max_g, avg_n, max_n, prof_count = r
            print(f"{pair:<18} | {count:>8} | {avg_g:>11.3f}% | {max_g:>10.3f}% | {avg_n:>10.3f}% | {max_n:>9.3f}% | {prof_count:>11}")

        # Top opportunità profittevoli
        cursor.execute("""
            SELECT timestamp, block_number, pair, buy_dex, sell_dex, gross_spread_pct, net_spread_pct, sim_profit_usd
            FROM price_ticks
            WHERE is_profitable = 1
            ORDER BY sim_profit_usd DESC
            LIMIT 10
        """)
        profitable_rows = cursor.fetchall()

        print("\n" + "=" * 85)
        if profitable_rows:
            print(f"  TOP OPPORTUNITA' PROFITTEVOLI RILEVATE ({len(profitable_rows)} mostrate):")
            print(f"{'Timestamp':<20} | {'Blocco':<8} | {'Coppia':<15} | {'Direzione':<25} | {'Spread':>8} | {'Profitto Netto':>14}")
            print("-" * 95)
            for p in profitable_rows:
                t, blk, pair, b_dex, s_dex, gross, net, profit = p
                direz = f"{b_dex[:10]} -> {s_dex[:10]}"
                print(f"{t:<20} | {blk:<8} | {pair:<15} | {direz:<25} | {gross:>+7.3f}% | +${profit:>11.4f} USD")
        else:
            print("  Nessuna opportunita a profitto netto positivo (> 0 $) registrata finora.")
            print("  (Lascia girare lo scanner per raccogliere dati in diversi orari del giorno/notte).")
        print("=" * 85)

if __name__ == "__main__":
    analyze()
