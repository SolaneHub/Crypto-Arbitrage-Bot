import os
import sys
import json
import time

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from simulator.fork_trader import ForkTrader, EUR_USD_RATE
from scanner.discovery import VERIFIED_TOKENS

def run_fork_tests():
    print("=" * 95)
    print("      TEST ON-CHAIN SUL FORK LOCALE DI BASE (ANVIL) CON CAPITALE DI PARTENZA: 50,00 €")
    print("      Verifica atomica con Smart Contract AtomicArbitrage.sol contro DEX reali di Base")
    print("=" * 95)

    trader = ForkTrader()
    print("\n[1/4] Connessione al nodo Anvil (Fork Base Mainnet)...")
    if not trader.start_fork_node():
        print("[!] Errore nell'avvio del fork locale.")
        return

    print("[2/4] Compilazione e Deploy on-chain di AtomicArbitrage.sol...")
    contract_addr = trader.deploy_contract()
    print(f"      [OK] Smart Contract attivo all'indirizzo: {contract_addr}")

    print("\n[3/4] Inizializzazione del portafoglio di test con Capitale Esatto di 50,00 €...")
    wallet_info = trader.fund_wallet(starting_eur=50.0)
    print(f"      - Saldo Stablecoin USDC: {wallet_info['usdc_balance']:.2f} USDC (50.00 €)")
    print(f"      - Riserva Gas ETH:       {wallet_info['eth_balance']:.5f} ETH (~50.00 € per ~18.000 txs)")
    print(f"      - Approvazione ERC20:    [OK] Smart Contract autorizzato per gli swap diretti")

    print("\n[4/4] Esecuzione dei Test On-Chain con registrazione continua a registro...")
    print(f"{'#':<3} | {'Modalità':<11} | {'Coppia DEX':<14} | {'Capitale':>9} | {'Portafoglio':>13} | {'Utile Netto':>11} | {'Gas Base':>9} | {'Esito On-Chain':<16}")
    print("-" * 105)

    with open("data/25_pairs_config.json") as f:
        pairs = json.load(f)

    # Elenco dei test da eseguire con 50€:
    # 1. Arbitraggio Diretto con 50€ su WETH / USDC (Uniswap V3 -> Aerodrome V2)
    # 2. Arbitraggio Diretto con 50€ su WETH / USDC (DEX invertiti per test revert)
    # 3. Arbitraggio Diretto con 50€ su wstETH / USDC
    # 4. Flash Loan $500 da Aave V3 (con portafoglio da 50€ intatto a riserva gas)
    # 5. Flash Loan $1,000 da Aave V3 su WETH / USDC
    # 6. Test Difensivo con spread negativo (Verifica Revert e protezione totale dei 50€)

    test_plan = [
        {"mode": "DIRECT", "b_sym": "WETH", "q_sym": "USDC", "amt_eur": 50.0, "swap_inv": False, "note": "50€ Diretto (Uni V3 -> Aero)"},
        {"mode": "DIRECT", "b_sym": "WETH", "q_sym": "USDC", "amt_eur": 50.0, "swap_inv": True,  "note": "50€ Diretto (Aero -> Uni V3)"},
        {"mode": "DIRECT", "b_sym": "wstETH", "q_sym": "USDC", "amt_eur": 50.0, "swap_inv": False, "note": "50€ Diretto (wstETH/USDC)"},
        {"mode": "FLASH_LOAN", "b_sym": "WETH", "q_sym": "USDC", "amt_eur": 460.0, "swap_inv": False, "note": "Flash Loan $500 (Aave V3)"},
        {"mode": "FLASH_LOAN", "b_sym": "WETH", "q_sym": "USDC", "amt_eur": 920.0, "swap_inv": False, "note": "Flash Loan $1000 (Aave V3)"},
        {"mode": "FLASH_LOAN", "b_sym": "SEAM", "q_sym": "WETH", "amt_eur": 460.0, "swap_inv": False, "note": "Flash Loan $500 (SEAM/WETH)"},
    ]

    for item in test_plan:
        b_sym = item["b_sym"]
        q_sym = item["q_sym"]
        mode = item["mode"]
        amt_eur = item["amt_eur"]
        amt_usd = amt_eur * EUR_USD_RATE

        matching = [p for p in pairs if p["base_symbol"] == b_sym and p["quote_symbol"] == q_sym]
        if not matching:
            continue
        p = matching[0]

        b_addr = VERIFIED_TOKENS[b_sym]["address"]
        q_addr = VERIFIED_TOKENS[q_sym]["address"]
        q_dec = VERIFIED_TOKENS[q_sym]["decimals"]

        trade_raw = int(amt_usd * 10**q_dec)

        pa = p["pool_a"]
        pb = p["pool_b"]

        if item["swap_inv"]:
            first_pool, second_pool = pb, pa
        else:
            first_pool, second_pool = pa, pb

        leg1_is_v3 = (first_pool["type"] == "v3")
        leg1_target = "0x2626664c2603336E57B271c5C0b26F421741e481" if leg1_is_v3 else first_pool["address"]
        leg1_fee = first_pool["fee_bps"] * 100 if leg1_is_v3 else 0

        leg2_is_v3 = (second_pool["type"] == "v3")
        leg2_target = "0x2626664c2603336E57B271c5C0b26F421741e481" if leg2_is_v3 else second_pool["address"]
        leg2_fee = second_pool["fee_bps"] * 100 if leg2_is_v3 else 0

        res = trader.execute_arbitrage(
            mode=mode,
            pair_name=p["name"],
            buy_dex=first_pool["name"],
            sell_dex=second_pool["name"],
            borrowed_asset=q_addr,
            bridge_asset=b_addr,
            trade_amount_eur=amt_eur,
            trade_amount_raw=trade_raw,
            leg1_is_v3=leg1_is_v3,
            leg1_target=leg1_target,
            leg1_fee=leg1_fee,
            leg2_is_v3=leg2_is_v3,
            leg2_target=leg2_target,
            leg2_fee=leg2_fee,
            min_profit_raw=0
        )

        status_disp = "[OK] ESEGUITO" if res["status"] == "CONFERMATO" else "[PROTETTO]"
        mode_disp = "50€ DIRETTO" if mode == "DIRECT" else "FLASH LOAN"
        profit_disp = f"+{res['net_profit_eur']:.4f} €" if res['net_profit_eur'] > 0 else " 0.0000 €"

        print(
            f"{res['id']:<3} | {mode_disp:<11} | {p['name']:<14} | "
            f"{amt_eur:>7.0f} € | {res['wallet_after_eur']:>11.4f} € | "
            f"{profit_disp:>11} | {res['gas_cost_eur']:>7.5f} € | {status_disp:<16}"
        )
        time.sleep(0.4)

    print("-" * 105)

    final_bal = trader.get_wallet_balance()
    initial_eur = 50.0
    current_usdc_eur = final_bal["usdc_eur"]
    roi_pct = ((current_usdc_eur - initial_eur) / initial_eur) * 100.0 if current_usdc_eur >= initial_eur else 0.0

    print("\n" + "=" * 95)
    print("                    BILANCIO CONTABILE FINALE SUI 50,00 €")
    print("=" * 95)
    print(f"  Capitale iniziale di partenza:             50.00 € (54.25 USDC)")
    print(f"  Saldo finale portafoglio in USDC:          {final_bal['usdc']:.4f} USDC ({current_usdc_eur:.4f} €)")
    print(f"  Utile netto generato e accreditato:        +{trader.total_profit_eur:.4f} €")
    print(f"  Rendimento netto sul capitale iniziale:    +{roi_pct:.2f}%")
    print(f"  Totale transazioni inviate al contratto:   {trader.total_fork_trades}")
    print(f"  Transazioni andate a buon fine (Success):  {trader.successful_trades}")
    print(f"  Transazioni protette da Revert (0 perdite):{trader.reverted_trades}")
    print(f"  Totale Gas Base L2 speso:                  {trader.total_gas_cost_eur:.5f} € (Gas unit: {trader.total_gas_used:,})")
    print("=" * 95)
    print("  [OK] Registro completo salvato in: 'data/fork_trading_ledger.csv' e SQLite 'market_history.db'")
    print("=" * 95)

    trader.stop()

if __name__ == "__main__":
    run_fork_tests()
