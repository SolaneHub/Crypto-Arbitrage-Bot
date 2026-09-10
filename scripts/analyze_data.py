import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

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

        print("=" * 95)
        print("                 REPORT ANALISI DATI RACCOLTI DALLO SCANNER")
        print(f"  Periodo: {min_time} -> {max_time} UTC")
        print(f"  Blocchi monitorati: #{min_block} -> #{max_block} (Totale campionamenti: {total_ticks})")
        print("=" * 95)

        # Statistiche per coppia (filtrando spread anomali transitori > 50%)
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
            WHERE gross_spread_pct < 50.0
            GROUP BY pair
            ORDER BY MAX(net_spread_pct) DESC
        """)
        rows = cursor.fetchall()

        print(f"\n{'Coppia':<20} | {'Campioni':>8} | {'Spread Medio':>12} | {'Spread Max':>11} | {'Netto Medio':>11} | {'Netto Max':>10} | {'Occasioni':>10}")
        print("-" * 96)
        for r in rows:
            pair, count, avg_g, max_g, avg_n, max_n, prof_count = r
            print(f"{pair:<20} | {count:>8} | {avg_g:>11.3f}% | {max_g:>10.3f}% | {avg_n:>10.3f}% | {max_n:>9.3f}% | {prof_count:>10}")

        # Top 10 opportunità storiche reali
        cursor.execute("""
            SELECT timestamp, block_number, pair, buy_dex, sell_dex, gross_spread_pct, net_spread_pct, sim_profit_usd
            FROM price_ticks
            WHERE is_profitable = 1
              AND gross_spread_pct < 50.0
            ORDER BY net_spread_pct DESC
            LIMIT 10
        """)
        profitable_rows = cursor.fetchall()

        print("\n" + "=" * 95)
        if profitable_rows:
            print(f"  TOP OPPORTUNITA' PROFITTEVOLI RILEVATE ({len(profitable_rows)} mostrate):")
            print(f"{'Timestamp':<20} | {'Blocco':<8} | {'Coppia':<16} | {'Direzione':<27} | {'Netto %':>8} | {'Profitto ($250)':>15}")
            print("-" * 105)
            for p in profitable_rows:
                t, blk, pair, b_dex, s_dex, gross, net, profit = p
                direz = f"{b_dex[:11]} -> {s_dex[:11]}"
                print(f"{t:<20} | {blk:<8} | {pair:<16} | {direz:<27} | {net:>+7.3f}% | +${profit:>12.4f} USD")
        else:
            print("  Nessuna opportunita a profitto netto positivo (> 0 $) registrata finora.")
        print("=" * 95)

        # Statistiche Paper Trading se disponibili
        try:
            cursor.execute("""
                SELECT COUNT(*), SUM(net_pnl_usd), SUM(net_pnl_eur), SUM(gas_cost_usd), MAX(cumulative_profit_eur)
                FROM paper_trades
                WHERE status = 'EXECUTED'
            """)
            p_count, p_usd, p_eur, p_gas, p_cum = cursor.fetchone()
            if p_count and p_count > 0:
                print(f"\n[i] PAPER TRADING REGISTRATO NEL DATABASE:")
                print(f"    Operazioni Eseguite: {p_count}")
                print(f"    Profitto Netto Cumulato: +${p_usd:.2f} USD (+{p_eur:.2f} €)")
                print(f"    Gas Totale Consumato: ${p_gas:.4f} USD")
                print("=" * 95)
        except Exception:
            pass

        # Statistiche On-Chain Fork Trading (50€ Capital & Flash Loans)
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*),
                    SUM(CASE WHEN status = 'CONFERMATO' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN status LIKE 'REVERT%' THEN 1 ELSE 0 END),
                    SUM(net_profit_eur),
                    SUM(gas_cost_eur),
                    MAX(wallet_after_eur)
                FROM fork_trades
            """)
            f_tot, f_succ, f_rev, f_prof, f_gas, f_max_w = cursor.fetchone()
            if f_tot and f_tot > 0:
                print(f"\n[i] TRADING ON-CHAIN FORK (CAPITALE REALE DI PARTENZA 50 €):")
                print(f"    Transazioni Totali Inviate: {f_tot}")
                print(f"    Transazioni Eseguite con Successo: {f_succ}")
                print(f"    Transazioni Protette da Revert (0 perdite): {f_rev}")
                print(f"    Utile Netto Accreditato: +{f_prof:.4f} €")
                print(f"    Spesa Gas Totale su Base L2: {f_gas:.5f} €")
                print(f"    Picco Saldo Portafoglio: {f_max_w:.4f} €")
                print("=" * 95)
        except Exception:
            pass

if __name__ == "__main__":
    analyze()

