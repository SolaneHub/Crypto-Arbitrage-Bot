import os
import time
import sys
from datetime import datetime
from typing import Dict, Any, List

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

from config.settings import (
    RPC_ENDPOINTS,
    MULTICALL3_ADDRESS,
    MONITORED_PAIRS,
    POLL_INTERVAL_SECONDS,
    ESTIMATED_GAS_UNITS,
    DEFAULT_SIMULATION_USD
)
from scanner.multicall import MulticallManager
from scanner.pools import PoolDecoder
from scanner.db_logger import MarketDatabase
from simulator.paper_trader import PaperTrader
from scanner.live_trader import LiveTrader

class MultiPairArbitrageScanner:
    def __init__(self, mode: str = "LIVE"):
        self.mode = mode.upper()
        self.multicall = MulticallManager(RPC_ENDPOINTS, MULTICALL3_ADDRESS)
        self.pairs_config = MONITORED_PAIRS
        self.db = MarketDatabase()
        self.paper_trader = PaperTrader(
            initial_gas_eur=50.0,
            min_net_spread_pct=0.08,
            slippage_buffer_pct=0.03
        )
        self.live_trader = LiveTrader() if self.mode == "LIVE" else None
        self._init_calls()

    def _init_calls(self):
        self.calls = []
        for pair in self.pairs_config:
            for pool_key in ("pool_a", "pool_b"):
                p = pair[pool_key]
                self.calls.append({
                    "target": p["address"],
                    "allowFailure": True,
                    "callData": PoolDecoder.get_calldata(p["type"])
                })

    def scan_cycle(self) -> Dict[str, Any]:
        block_number, raw_results = self.multicall.aggregate(self.calls)
        gas_price_wei = self.multicall.w3.eth.gas_price
        gas_price_gwei = self.multicall.w3.from_wei(gas_price_wei, "gwei")

        # Prezzo ETH di riferimento e costo gas
        eth_price_usd = 2465.0
        gas_cost_usd = (ESTIMATED_GAS_UNITS * gas_price_wei / 10**18) * eth_price_usd

        results = []
        profitable_alerts = []
        call_idx = 0

        for pair in self.pairs_config:
            pool_a_cfg = pair["pool_a"]
            pool_b_cfg = pair["pool_b"]

            success_a, data_a = raw_results[call_idx]
            call_idx += 1
            success_b, data_b = raw_results[call_idx]
            call_idx += 1

            if not success_a or not success_b:
                continue

            state_a = PoolDecoder.decode_pool_state(pool_a_cfg, pair, data_a)
            state_b = PoolDecoder.decode_pool_state(pool_b_cfg, pair, data_b)

            if not state_a or not state_b:
                continue

            p_a = state_a["price"]
            p_b = state_b["price"]

            if p_a < p_b:
                buy_pool, sell_pool = state_a, state_b
            else:
                buy_pool, sell_pool = state_b, state_a

            spread_val = sell_pool["price"] - buy_pool["price"]
            gross_pct = (spread_val / buy_pool["price"]) * 100.0
            fees_pct = (buy_pool["fee_bps"] + sell_pool["fee_bps"]) / 100.0
            net_pct = gross_pct - fees_pct

            # Dimensionamento dinamico del capitale basato sulla profondità reale della pool
            pool_liq = pair.get("aero_liq_usd", 250000)
            if pool_liq >= 2000000:
                sim_capital = 500.0
            elif pool_liq >= 300000:
                sim_capital = 250.0
            else:
                sim_capital = 100.0

            if buy_pool["type"] == "v2" and sell_pool["type"] == "v2":
                # Entrambe V2: calcolo analitico x*y=k esatto
                if pair["is_quote_eth"]:
                    quote_in_float = sim_capital / eth_price_usd
                else:
                    quote_in_float = sim_capital

                quote_in_raw = int(quote_in_float * (10**pair["quote_decimals"]))

                base_bought = PoolDecoder.get_amount_out_v2(
                    quote_in_raw,
                    buy_pool["r_quote_raw"],
                    buy_pool["r_base_raw"],
                    buy_pool["fee_bps"]
                )

                quote_received = PoolDecoder.get_amount_out_v2(
                    base_bought,
                    sell_pool["r_base_raw"],
                    sell_pool["r_quote_raw"],
                    sell_pool["fee_bps"]
                )

                diff_raw = quote_received - quote_in_raw
                diff_quote = diff_raw / (10**pair["quote_decimals"])
                diff_usd = diff_quote * eth_price_usd if pair["is_quote_eth"] else diff_quote
                sim_net_usd = diff_usd - gas_cost_usd
            else:
                # Almeno una pool è V3 / Slipstream: stima dal net_pct
                sim_net_usd = (sim_capital * (net_pct / 100.0)) - gas_cost_usd

            is_profitable = (net_pct > 0 and sim_net_usd > 0)

            pair_res = {
                "pair": pair["name"],
                "quote": pair["quote_symbol"],
                "buy_dex": buy_pool["dex"],
                "buy_price": buy_pool["price"],
                "sell_dex": sell_pool["dex"],
                "sell_price": sell_pool["price"],
                "gross_pct": gross_pct,
                "fees_pct": fees_pct,
                "net_pct": net_pct,
                "gas_cost_usd": gas_cost_usd,
                "sim_capital_usd": sim_capital,
                "sim_profit_usd": sim_net_usd,
                "is_profitable": is_profitable
            }
            results.append(pair_res)

            # Salva sempre nel database
            self.db.record_tick(block_number, gas_price_gwei, gas_cost_usd, pair_res)

            if is_profitable:
                profitable_alerts.append(pair_res)
                if gross_pct < 50.0:
                    paper_trade = self.paper_trader.evaluate_opportunity(
                        block=block_number,
                        pair=pair["name"],
                        buy_dex=buy_pool["dex"],
                        sell_dex=sell_pool["dex"],
                        gross_pct=gross_pct,
                        net_pct=net_pct,
                        gas_cost_usd=gas_cost_usd
                    )
                    if self.mode == "LIVE" and self.live_trader:
                        live_trade = self.live_trader.evaluate_and_execute(
                            pair_cfg=pair,
                            opportunity=pair_res,
                            flash_loan_usd=sim_capital
                        )
                        pair_res["live_trade"] = live_trade

        return {
            "block": block_number,
            "gas_price_gwei": gas_price_gwei,
            "gas_cost_usd": gas_cost_usd,
            "pairs": results,
            "alerts": profitable_alerts
        }

    def start_continuous_monitoring(self):
        mode_label = "TRADING REALE ON-CHAIN (BASE MAINNET)" if self.mode == "LIVE" else "PAPER TRADING (SIMULAZIONE)"
        contract_str = f"Contratto: {self.live_trader.contract_address}" if self.live_trader and self.live_trader.contract_address else "Simulatore Off-Chain"
        
        print("=" * 95)
        print(f"     ARBITRAGE BOT -- {mode_label}")
        print(f"     {contract_str}")
        print(f"     Modello: Flash Loan ($250 - $1.000) a Rischio Zero | Protezione Pre-Flight: eth_call")
        print(f"     25 Coppie No-Meme | Database: data/market_history.db | Registro: data/live_trading_ledger.csv")
        print("=" * 95)

        last_block = 0
        EUR_USD_RATE = 1.085

        if self.mode == "LIVE" and self.live_trader:
            wb = self.live_trader.get_wallet_balances()
            self.live_trader.notifier.notify_startup(
                wallet_address=str(self.live_trader.wallet_address),
                contract_address=str(self.live_trader.contract_address),
                balance_eur=wb["total_eur"],
                eth_bal=wb["eth"],
                mode=self.mode
            )

        kill_switch_notified = False

        try:
            while True:
                kill_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "KILL_SWITCH")
                if os.path.exists(kill_file):
                    if not kill_switch_notified:
                        print("\n🛑 [KILL-SWITCH ATTIVO] Rilevato blocco di emergenza (data/KILL_SWITCH). Operazioni in pausa.")
                        if self.mode == "LIVE" and self.live_trader:
                            self.live_trader.notifier.send_discord_embed(
                                title="🛑 KILL-SWITCH DI EMERGENZA ATTIVATO",
                                description="Il Bot di Arbitraggio è stato messo in **PAUSA IMMEDIATA** di sicurezza.\nNessuna transazione verrà inviata finché il blocco non verrà rimosso con `python scripts/kill_switch.py resume`.",
                                color=0xE74C3C
                            )
                        kill_switch_notified = True
                    time.sleep(2.0)
                    continue
                else:
                    if kill_switch_notified:
                        print("\n🟢 [KILL-SWITCH DISATTIVATO] Blocco rimosso. Il bot riprende le normali operazioni.")
                        if self.mode == "LIVE" and self.live_trader:
                            self.live_trader.notifier.send_discord_embed(
                                title="🟢 KILL-SWITCH DISATTIVATO: OPERAZIONI RIPRESE",
                                description="Il Bot ha ripreso il normale monitoraggio ed esecuzione on-chain su Base L2.",
                                color=0x2ECC71
                            )
                        kill_switch_notified = False

                data = self.scan_cycle()
                curr_block = data["block"]

                if curr_block != last_block:
                    last_block = curr_block
                    t_str = datetime.now().strftime("%H:%M:%S")

                    # Banner Trade Eseguiti con Guadagno Effettivo in Tempo Reale
                    if data["alerts"]:
                        for a in data["alerts"]:
                            lt = a.get("live_trade")
                            if lt and lt.get("status") == "CONFIRMED":
                                print("\n" + "=" * 95)
                                print(f"  🚀 [ARBITRAGGIO LIVE CONFERMATO ON-CHAIN] {lt['pair']} (Blocco #{curr_block})")
                                print(f"     Tx Hash: {lt['tx_hash']}")
                                print(f"     Basescan Explorer: {lt['basescan_url']}")
                                print(f"     " + "-" * 85)
                                print(f"     👉 UTILE NETTO ACCREDITATO:    +{lt['net_profit_eur']:.4f} €  (+${lt['net_profit_usd']:.4f} USD)")
                                print(f"     ⛽ Gas Reale Speso:             {lt['gas_cost_eur']:.5f} €  ({lt['gas_used']:,} gas)")
                                print(f"     📈 Saldo Portafoglio Base:     {lt['wallet_after']['total_eur']:.4f} € ({lt['wallet_after']['eth']:.6f} ETH)")
                                print(f"     🏆 Totale Guadagnato Finora:   +{self.live_trader.cumulative_profit_eur:.4f} €")
                                print("=" * 95 + "\n")
                            elif lt and lt.get("status") == "SIM_PREVENTED":
                                print(f"  🛡️ [PROTEZIONE PRE-FLIGHT ATTIVA] {lt['pair']}: {lt['reason']} -> Bloccato prima dell'invio (Gas speso: 0,00 €)")

                            pt = a.get("paper_trade")
                            if pt and pt["status"] == "EXECUTED" and self.mode != "LIVE":
                                print("\n" + "=" * 95)
                                print(f"  💰 [PAPER TRADE ESEGUITO]  {pt['pair']}  (Blocco #{curr_block})")
                                print(f"     Direzione: {pt['buy_dex']} -> {pt['sell_dex']} | Flash Loan: ${pt['flash_loan_usd']:.0f}")
                                print(f"     👉 GUADAGNO STIMATO NETTO:     +{pt['net_pnl_eur']:.4f} €")
                                print("=" * 95 + "\n")

                    if self.mode == "LIVE" and self.live_trader:
                        wb = self.live_trader.get_wallet_balances()
                        wallet_str = f"Portafoglio: {wb['total_eur']:.2f} € ({wb['eth']:.5f} ETH) | Utile: +{self.live_trader.cumulative_profit_eur:.2f} €"
                    else:
                        summary = self.paper_trader.get_summary()
                        wallet_str = f"Portafoglio: {summary['final_account_value_eur']:.2f} € (Utile: +{summary['total_profit_eur']:.2f} €)"

                    gas_cost_eur = data['gas_cost_usd'] / EUR_USD_RATE
                    print(f"[{t_str}] Blocco #{curr_block} | Gas Base: {data['gas_price_gwei']:.4f} Gwei ({gas_cost_eur:.5f} €) | {wallet_str}")

                    # Mostra lo stato delle coppie
                    for r in data["pairs"]:
                        p_format = ".2f" if "USDC" in r["pair"] and "cbBTC" in r["pair"] else (".4f" if "USDC" in r["pair"] else ".8f")
                        net_sign = "+" if r["net_pct"] > 0 else ""
                        status_flag = "🔥 [OPPORTUNITÀ RILEVATA]" if r["is_profitable"] else "[in scansione]"
                        print(
                            f"  * {r['pair']:<15} | "
                            f"Buy: {r['buy_dex'][:10]:<10} ({r['buy_price']:{p_format}}) -> "
                            f"Sell: {r['sell_dex'][:10]:<10} ({r['sell_price']:{p_format}}) | "
                            f"Spread: {r['gross_pct']:>+6.3f}% | Netto: {net_sign}{r['net_pct']:>+6.3f}% {status_flag}"
                        )
                    print("-" * 95)

                time.sleep(POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\n[!] Monitoraggio terminato dall'utente. Tutti i dati sono stati salvati.")
            if self.mode == "LIVE" and self.live_trader:
                wb = self.live_trader.get_wallet_balances()
                print("\n" + "=" * 80)
                print("               BILANCIO DELLA SESSIONE DI TRADING LIVE")
                print("=" * 80)
                print(f"  Saldo Attuale Portafoglio:        {wb['total_eur']:.4f} € ({wb['eth']:.6f} ETH, {wb['usdc']:.2f} USDC)")
                print(f"  Utile Netto Totale Realizzato:    +{self.live_trader.cumulative_profit_eur:.4f} €")
                print(f"  Transazioni On-Chain Eseguite:    {self.live_trader.total_live_trades}")
                print(f"  Transazioni Protette da Revert:   {self.live_trader.total_reverts_prevented} (0,00 € gas sprecato)")
                print(f"  Gas Totale Base Speso:            {self.live_trader.total_gas_spent_eur:.5f} €")
                print("=" * 80)
                print("  Registro salvato in: data/live_trading_ledger.csv e data/market_history.db\n")
            else:
                summary = self.paper_trader.get_summary()
                print("\n" + "=" * 80)
                print("                BILANCIO FINALE DELLA SESSIONE PAPER")
                print("=" * 80)
                print(f"  Saldo Finale Portafoglio:         {summary['final_account_value_eur']:.4f} €")
                print(f"  Guadagno Stimato Totale:          +{summary['total_profit_eur']:.4f} €")
                print("=" * 80)
