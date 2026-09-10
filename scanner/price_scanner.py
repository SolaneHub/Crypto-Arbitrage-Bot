import os
import csv
import time
from datetime import datetime
from itertools import combinations
from typing import List, Dict, Any

from config.settings import (
    RPC_ENDPOINTS,
    MULTICALL3_ADDRESS,
    POOLS,
    POLL_INTERVAL_SECONDS,
    MIN_SPREAD_ALERT_PCT,
    LOG_FILE
)
from scanner.multicall import MulticallManager
from scanner.pools import PoolDecoder

class ArbitrageScanner:
    def __init__(self):
        self.multicall = MulticallManager(RPC_ENDPOINTS, MULTICALL3_ADDRESS)
        self.calls = [
            {
                "target": pool["address"],
                "allowFailure": True,
                "callData": PoolDecoder.get_calldata(pool["type"])
            }
            for pool in POOLS
        ]
        self._init_csv()

    def _init_csv(self):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp",
                    "block_number",
                    "pair",
                    "buy_dex",
                    "buy_price",
                    "sell_dex",
                    "sell_price",
                    "spread_usd",
                    "gross_spread_pct",
                    "fees_pct",
                    "est_net_spread_pct"
                ])

    def _log_opportunity(self, opp: Dict[str, Any]):
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                opp["timestamp"],
                opp["block"],
                "WETH/USDC",
                opp["buy_dex"],
                f"{opp['buy_price']:.2f}",
                opp["sell_dex"],
                f"{opp['sell_price']:.2f}",
                f"{opp['spread_usd']:.2f}",
                f"{opp['gross_pct']:.4f}",
                f"{opp['fees_pct']:.4f}",
                f"{opp['net_pct']:.4f}"
            ])

    def scan_once(self) -> Dict[str, Any]:
        block_number, raw_results = self.multicall.aggregate(self.calls)
        pool_results = []

        for i, (success, return_data) in enumerate(raw_results):
            if success:
                decoded = PoolDecoder.decode_price(POOLS[i], return_data)
                if decoded:
                    pool_results.append(decoded)

        opportunities = []
        for p1, p2 in combinations(pool_results, 2):
            if p1["price"] < p2["price"]:
                buy_pool, sell_pool = p1, p2
            else:
                buy_pool, sell_pool = p2, p1

            spread_usd = sell_pool["price"] - buy_pool["price"]
            gross_pct = (spread_usd / buy_pool["price"]) * 100.0
            fees_pct = buy_pool["fee_pct"] + sell_pool["fee_pct"]
            net_pct = gross_pct - fees_pct

            opp = {
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "block": block_number,
                "buy_dex": buy_pool["name"],
                "buy_price": buy_pool["price"],
                "sell_dex": sell_pool["name"],
                "sell_price": sell_pool["price"],
                "spread_usd": spread_usd,
                "gross_pct": gross_pct,
                "fees_pct": fees_pct,
                "net_pct": net_pct
            }
            opportunities.append(opp)

            if gross_pct >= MIN_SPREAD_ALERT_PCT:
                self._log_opportunity(opp)

        return {
            "block": block_number,
            "prices": pool_results,
            "opportunities": opportunities
        }

    def start_monitoring(self):
        print("=" * 65)
        print("  DEX ARBITRAGE SCANNER -- BASE NETWORK (Chain ID: 8453)")
        print(f"  Target: WETH / USDC | Intervallo: {POLL_INTERVAL_SECONDS}s")
        print("=" * 65)

        last_block = 0
        try:
            while True:
                data = self.scan_once()
                curr_block = data["block"]

                if curr_block != last_block:
                    last_block = curr_block
                    now_str = datetime.now().strftime("%H:%M:%S")
                    print(f"\n[{now_str}] Blocco #{curr_block}")

                    # Mostra prezzi DEX
                    for p in data["prices"]:
                        res_str = ""
                        if "base_reserve" in p:
                            res_str = f"(Liq: {p['base_reserve']:.1f} WETH)"
                        print(f"  > {p['name']:<22}: {p['price']:>9.2f} USDC {res_str}")

                    # Mostra gli spread
                    for opp in data["opportunities"]:
                        net_sign = "+" if opp["net_pct"] > 0 else ""
                        flag = "[PROFITTO NETTO!]" if opp["net_pct"] > 0 else "[Lordo]"
                        print(
                            f"    * {opp['buy_dex']} -> {opp['sell_dex']}: "
                            f"Spread: ${opp['spread_usd']:>5.2f} ({opp['gross_pct']:>+.3f}%) | "
                            f"Netto teorico: {net_sign}{opp['net_pct']:>.3f}% {flag if opp['gross_pct'] > 0.05 else ''}"
                        )

                time.sleep(POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\n[!] Scanner interrotto dall'utente.")
