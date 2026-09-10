import time
from datetime import datetime
from typing import Dict, Any, List

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

class MultiPairArbitrageScanner:
    def __init__(self):
        self.multicall = MulticallManager(RPC_ENDPOINTS, MULTICALL3_ADDRESS)
        self.pairs_config = MONITORED_PAIRS
        self.db = MarketDatabase()
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

        # Stima prezzo ETH e costo gas operazione
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

            # Simulazione trade reale se entrambe sono V2
            sim_net_usd = 0.0
            sim_capital = DEFAULT_SIMULATION_USD

            if buy_pool["type"] == "v2" and sell_pool["type"] == "v2":
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

            is_profitable = (net_pct > 0 and (sim_net_usd > 0 or buy_pool["type"] != "v2"))

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

            # Salva sempre nel database e nei file CSV per analisi
            self.db.record_tick(block_number, gas_price_gwei, gas_cost_usd, pair_res)

            if is_profitable:
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
        print("     Dati salvati automaticamente in data/market_history.db e CSV")
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

                    if data["alerts"]:
                        print("\n" + "#" * 88)
                        for a in data["alerts"]:
                            print("  >>> [PROFITTO REALE RILEVATO!] <<<")
                            print(f"  Coppia: {a['pair']} | Compra su {a['buy_dex']} -> Vendi su {a['sell_dex']}")
                            print(f"  Spread Lordo: {a['gross_pct']:+.3f}% | Netto Teorico: {a['net_pct']:+.3f}%")
                            if a["sim_profit_usd"] > 0:
                                print(f"  Guadagno Netto Stimato: +${a['sim_profit_usd']:.4f} USD (Trade da ${a['sim_capital_usd']:.0f})")
                        print("#" * 88 + "\n")

                    print(f"[{t_str}] Blocco #{curr_block} | Gas: {data['gas_price_gwei']:.4f} Gwei (${data['gas_cost_usd']:.4f}/tx)")
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
            print("\n[!] Scanner interrotto dall'utente. I dati raccolti sono al sicuro nel database.")
