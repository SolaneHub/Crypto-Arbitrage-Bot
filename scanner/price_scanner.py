import os
import csv
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from config.settings import (
    RPC_ENDPOINTS,
    MULTICALL3_ADDRESS,
    MONITORED_PAIRS,
    POLL_INTERVAL_SECONDS,
    ESTIMATED_GAS_UNITS,
    DEFAULT_SIMULATION_USD,
    LOG_FILE_PROFIT,
    LOG_FILE_ALL
)
from scanner.multicall import MulticallManager
from scanner.pools import PoolDecoder

class MultiPairArbitrageScanner:
    def __init__(self):
        self.multicall = MulticallManager(RPC_ENDPOINTS, MULTICALL3_ADDRESS)
        self.pairs_config = MONITORED_PAIRS
        self._init_calls()
        self._init_csv()

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

    def _init_csv(self):
        os.makedirs(os.path.dirname(LOG_FILE_PROFIT), exist_ok=True)
        if not os.path.exists(LOG_FILE_PROFIT):
            with open(LOG_FILE_PROFIT, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp",
                    "block_number",
                    "pair",
                    "buy_dex",
                    "buy_price",
                    "sell_dex",
                    "sell_price",
                    "gross_spread_pct",
                    "fees_pct",
                    "est_gas_usd",
                    "net_spread_pct",
                    "simulated_capital_usd",
                    "simulated_net_profit_usd"
                ])

    def _log_profit(self, opp: Dict[str, Any]):
        with open(LOG_FILE_PROFIT, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                opp["timestamp"],
                opp["block"],
                opp["pair"],
                opp["buy_dex"],
                f"{opp['buy_price']:.8f}",
                opp["sell_dex"],
                f"{opp['sell_price']:.8f}",
                f"{opp['gross_pct']:.4f}",
                f"{opp['fees_pct']:.4f}",
                f"{opp['gas_cost_usd']:.4f}",
                f"{opp['net_pct']:.4f}",
                f"{opp['sim_capital_usd']:.2f}",
                f"{opp['sim_profit_usd']:.4f}"
            ])

    def scan_cycle(self) -> Dict[str, Any]:
        block_number, raw_results = self.multicall.aggregate(self.calls)
        gas_price_wei = self.multicall.w3.eth.gas_price
        gas_price_gwei = self.multicall.w3.from_wei(gas_price_wei, "gwei")

        # Trova prima il prezzo di ETH per calcolare il gas in USD
        eth_price_usd = 2465.0
        # Calcolo costo gas per flash loan + 2 swap in USD
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

            # Simulazione analitica se entrambe sono V2
            sim_net_usd = 0.0
            sim_capital = DEFAULT_SIMULATION_USD

            if buy_pool["type"] == "v2" and sell_pool["type"] == "v2":
                # Calcola trade reale su V2
                # Converti capitale simulato in quote asset
                if pair["is_quote_eth"]:
                    quote_in_float = sim_capital / eth_price_usd
                else:
                    quote_in_float = sim_capital

                quote_in_raw = int(quote_in_float * (10**pair["quote_decimals"]))

                # Leg 1: swap quote -> base su buy_pool
                base_bought = PoolDecoder.get_amount_out_v2(
                    quote_in_raw,
                    buy_pool["r_quote_raw"],
                    buy_pool["r_base_raw"],
                    buy_pool["fee_bps"]
                )

                # Leg 2: swap base -> quote su sell_pool
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
                "is_profitable": (net_pct > 0 and (sim_net_usd > 0 or buy_pool["type"] != "v2"))
            }
            results.append(pair_res)

            if pair_res["is_profitable"] or net_pct > 0.05:
                opp_log = {
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "block": block_number,
                    **pair_res
                }
                if pair_res["is_profitable"]:
                    self._log_profit(opp_log)
                    profitable_alerts.append(pair_res)

        return {
            "block": block_number,
            "gas_price_gwei": gas_price_gwei,
            "gas_cost_usd": gas_cost_usd,
            "pairs": results,
            "alerts": profitable_alerts
        }

    def start_continuous_monitoring(self):
        print("=" * 88)
        print("     ARBITRAGE BOT -- SCANNER MULTI-COPPIA AD ALTA FREQUENZA (BASE L2)")
        print(f"     4 Coppie Volatili in Ascolto Attivo | Polling ogni {POLL_INTERVAL_SECONDS}s")
        print("=" * 88)

        last_block = 0
        try:
            while True:
                data = self.scan_cycle()
                curr_block = data["block"]

                if curr_block != last_block:
                    last_block = curr_block
                    t_str = datetime.now().strftime("%H:%M:%S")

                    # Banner in caso di profitto netto reale
                    if data["alerts"]:
                        print("\n" + "#" * 88)
                        for a in data["alerts"]:
                            print(f"  >>> [PROFITTO REALE RILEVATO!] <<<")
                            print(f"  Coppia: {a['pair']} | Compra su {a['buy_dex']} -> Vendi su {a['sell_dex']}")
                            print(f"  Spread Lordo: {a['gross_pct']:+.3f}% | Netto Teorico: {a['net_pct']:+.3f}%")
                            if a["sim_profit_usd"] > 0:
                                print(f"  Simulazione con ${a['sim_capital_usd']:.0f}: Guadagno Netto Effettivo: +${a['sim_profit_usd']:.4f} USD (Gas già detratto)")
                        print("#" * 88 + "\n")

                    # Tabella di monitoraggio compatta
                    print(f"[{t_str}] Blocco #{curr_block} | Gas: {data['gas_price_gwei']:.4f} Gwei (Gas/Tx: ${data['gas_cost_usd']:.4f})")
                    for r in data["pairs"]:
                        p_format = ".4f" if r["quote"] == "USDC" else ".8f"
                        net_sign = "+" if r["net_pct"] > 0 else ""
                        status_flag = "[PROFITTO!]" if r["is_profitable"] else "[attesa]"
                        print(
                            f"  * {r['pair']:<15} | "
                            f"Buy: {r['buy_dex'][:10]:<10} ({r['buy_price']:{p_format}}) -> "
                            f"Sell: {r['sell_dex'][:10]:<10} ({r['sell_price']:{p_format}}) | "
                            f"Spread: {r['gross_pct']:>+6.3f}% | Netto: {net_sign}{r['net_pct']:>+6.3f}% {status_flag}"
                        )
                    print("-" * 88)

                time.sleep(POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\n[!] Scanner interrotto dall'utente.")
