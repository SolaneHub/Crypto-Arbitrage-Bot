import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from simulator.paper_trader import PaperTrader, EUR_USD_RATE

DB_PATH = "data/market_history.db"

def run_backtest():
    if not os.path.exists(DB_PATH):
        print(f"[!] Database non trovato in {DB_PATH}")
        return

    # Usiamo un'istanza in-memory del PaperTrader (nessun file temporaneo su disco)
    trader = PaperTrader(
        initial_gas_eur=50.0,
        min_net_spread_pct=0.08,
        slippage_buffer_pct=0.03,
        db_path=None,
        csv_path=None
    )

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Selezioniamo le opportunità distinte per blocco e coppia
        # per non eseguire duplicati nello stesso blocco
        cursor.execute("""
            SELECT 
                block_number,
                timestamp,
                pair,
                buy_dex,
                sell_dex,
                gross_spread_pct,
                net_spread_pct,
                gas_cost_usd
            FROM price_ticks
            WHERE is_profitable = 1
              AND gross_spread_pct < 50.0  -- Filtra eventuali anomalie decimali transitorie
            GROUP BY block_number, pair
            ORDER BY block_number ASC
        """)
        rows = cursor.fetchall()

    if not rows:
        print("[!] Nessuna opportunita profittevole trovata da simulare.")
        return

    print("=" * 95)
    print("        SIMULAZIONE DI PAPER TRADING SU DATI ON-CHAIN REALI (BASE L2)")
    print(f"  Capitale Iniziale Gas Wallet: 50.00 EUR (~ ${50.0 * EUR_USD_RATE:.2f} USD in ETH)")
    print(f"  Metodo di esecuzione: Smart Contract Atomico + Flash Loan (0 collaterale)")
    print(f"  Protezione Slippage Cautelativa: 0.03% dedotto dallo spread")
    print(f"  Soglia minima di profitto netto richiesta: +0.08%")
    print("=" * 95)

    print(f"\n{'Blocco':<8} | {'Timestamp':<19} | {'Coppia':<15} | {'Flash Loan':>10} | {'Netto %':>8} | {'Gas':>8} | {'Profitto Netto':>14} | {'Saldo Wallet':>13}")
    print("-" * 110)

    trades_count = 0
    for r in rows:
        blk, t_str, pair, b_dex, s_dex, gross_pct, net_pct, gas_cost = r
        res = trader.evaluate_opportunity(
            block=blk,
            pair=pair,
            buy_dex=b_dex,
            sell_dex=s_dex,
            gross_pct=gross_pct,
            net_pct=net_pct,
            gas_cost_usd=gas_cost,
            timestamp=t_str
        )
        if res and res["status"] == "EXECUTED":
            trades_count += 1
            if trades_count <= 25 or trades_count % 10 == 0:  # Stampa i primi 25 e poi a campioni
                p_usd = res["net_pnl_usd"]
                p_eur = res["net_pnl_eur"]
                print(
                    f"{blk:<8} | {t_str:<19} | {pair:<15} | "
                    f"${res['flash_loan_usd']:>8.0f} | {res['net_spread_pct']:>+7.3f}% | "
                    f"${res['gas_cost_usd']:>6.4f} | +${p_usd:>6.2f} (+{p_eur:.2f}€) | "
                    f"{res['wallet_gas_eur'] + res['cumulative_profit_eur']:>10.2f} €"
                )

    summary = trader.get_summary()

    print("\n" + "=" * 95)
    print("              ESTRATTO CONTO FINALE -- RISULTATI PAPER TRADING")
    print("=" * 95)
    print(f"  Capitale Gas di partenza:          50.00 €")
    print(f"  Operazioni simulate eseguite:      {summary['trades_executed']}")
    print(f"  Spesa totale Gas Blockchain:       {summary['total_gas_spent_eur']:.4f} €  (${summary['total_gas_spent_eur'] * EUR_USD_RATE:.4f} USD)")
    print(f"  Guadagno Netto Totale generato:    +{summary['total_profit_eur']:.2f} €  (+${summary['total_profit_usd']:.2f} USD)")
    print(f"  Patrimonio Finale (Gas + Utili):   {summary['final_account_value_eur']:.2f} €")
    print(f"  Rendimento sul capitale (ROI):     {summary['roi_pct']:+.2f} %")
    print("  I trade eseguiti in tempo reale sono registrati in 'data/paper_trading_ledger.csv'.")
    print("=" * 95)

if __name__ == "__main__":
    run_backtest()
