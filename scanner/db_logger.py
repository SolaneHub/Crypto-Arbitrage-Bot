import os
import sqlite3
import csv
from datetime import datetime
from typing import Dict, Any

DB_PATH = "data/market_history.db"
CSV_PROFIT_PATH = "data/profitable_opportunities.csv"
CSV_ALL_PATH = "data/spread_snapshots.csv"

class MarketDatabase:
    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.db_path = DB_PATH
        self._init_db()
        self._init_csv()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_ticks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    block_number INTEGER,
                    gas_price_gwei REAL,
                    gas_cost_usd REAL,
                    pair TEXT,
                    buy_dex TEXT,
                    buy_price REAL,
                    sell_dex TEXT,
                    sell_price REAL,
                    gross_spread_pct REAL,
                    fees_pct REAL,
                    net_spread_pct REAL,
                    is_profitable INTEGER,
                    sim_capital_usd REAL,
                    sim_profit_usd REAL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pair ON price_ticks(pair)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_profitable ON price_ticks(is_profitable)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_block ON price_ticks(block_number)")
            conn.commit()

    def _init_csv(self):
        if not os.path.exists(CSV_PROFIT_PATH):
            with open(CSV_PROFIT_PATH, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "block_number", "pair", "buy_dex", "buy_price",
                    "sell_dex", "sell_price", "gross_spread_pct", "fees_pct",
                    "gas_cost_usd", "net_spread_pct", "sim_capital_usd", "sim_profit_usd"
                ])
        if not os.path.exists(CSV_ALL_PATH):
            with open(CSV_ALL_PATH, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "block_number", "gas_gwei", "pair",
                    "buy_dex", "buy_price", "sell_dex", "sell_price",
                    "gross_pct", "net_pct", "is_profitable"
                ])

    def record_tick(self, block: int, gas_gwei: Any, gas_cost_usd: Any, pair_data: Dict[str, Any]):
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        is_prof = 1 if pair_data["is_profitable"] else 0
        g_gwei = float(gas_gwei)
        g_cost = float(gas_cost_usd)

        # 1. Salva nel Database SQLite
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO price_ticks (
                    timestamp, block_number, gas_price_gwei, gas_cost_usd,
                    pair, buy_dex, buy_price, sell_dex, sell_price,
                    gross_spread_pct, fees_pct, net_spread_pct,
                    is_profitable, sim_capital_usd, sim_profit_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now_str, int(block), g_gwei, g_cost,
                str(pair_data["pair"]), str(pair_data["buy_dex"]),
                float(pair_data["buy_price"]), str(pair_data["sell_dex"]),
                float(pair_data["sell_price"]), float(pair_data["gross_pct"]),
                float(pair_data["fees_pct"]), float(pair_data["net_pct"]),
                is_prof, float(pair_data["sim_capital_usd"]),
                float(pair_data["sim_profit_usd"])
            ))
            conn.commit()

        # 2. Salva nel CSV di snapshot continuo
        with open(CSV_ALL_PATH, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                now_str, block, f"{g_gwei:.4f}", pair_data["pair"],
                pair_data["buy_dex"], f"{float(pair_data['buy_price']):.8f}",
                pair_data["sell_dex"], f"{float(pair_data['sell_price']):.8f}",
                f"{float(pair_data['gross_pct']):.4f}", f"{float(pair_data['net_pct']):.4f}", is_prof
            ])

        # 3. Se profittevole, aggiungi al file delle sole opportunità d'oro
        if pair_data["is_profitable"]:
            with open(CSV_PROFIT_PATH, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    now_str, block, pair_data["pair"], pair_data["buy_dex"],
                    f"{float(pair_data['buy_price']):.8f}", pair_data["sell_dex"],
                    f"{float(pair_data['sell_price']):.8f}", f"{float(pair_data['gross_pct']):.4f}",
                    f"{float(pair_data['fees_pct']):.4f}", f"{g_cost:.4f}",
                    f"{float(pair_data['net_pct']):.4f}", f"{float(pair_data['sim_capital_usd']):.2f}",
                    f"{float(pair_data['sim_profit_usd']):.4f}"
                ])
