import os
import sqlite3
import csv
from datetime import datetime
from typing import Dict, Any, Optional, List

DB_PATH = "data/market_history.db"
LEDGER_CSV_PATH = "data/paper_trading_ledger.csv"
EUR_USD_RATE = 1.085

class PaperTrader:
    """
    Simulatore realistico di Paper Trading per Arbitraggio On-Chain su Base.
    Simula l'esecuzione atomica tramite Smart Contract e Flash Loan,
    utilizzando un fondo carburante iniziale (Gas Wallet) di 50.00 EUR.
    """

    def __init__(
        self,
        initial_gas_eur: float = 50.0,
        flash_loan_usd: float = 1000.0,
        min_net_spread_pct: float = 0.08,
        slippage_buffer_pct: float = 0.03,
        db_path: str = DB_PATH,
        csv_path: str = LEDGER_CSV_PATH
    ):
        self.initial_gas_eur = initial_gas_eur
        self.wallet_gas_balance_eur = initial_gas_eur
        self.flash_loan_usd = flash_loan_usd
        self.min_net_spread_pct = min_net_spread_pct
        self.slippage_buffer_pct = slippage_buffer_pct
        self.db_path = db_path
        self.csv_path = csv_path

        self.total_trades_executed = 0
        self.total_trades_reverted = 0
        self.cumulative_profit_usd = 0.0
        self.cumulative_profit_eur = 0.0
        self.total_gas_spent_usd = 0.0
        self.total_gas_spent_eur = 0.0

        self._init_storage()

    def _init_storage(self):
        if self.db_path:
            os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS paper_trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        block_number INTEGER,
                        pair TEXT,
                        buy_dex TEXT,
                        sell_dex TEXT,
                        flash_loan_usd REAL,
                        gross_spread_pct REAL,
                        slippage_pct REAL,
                        net_spread_pct REAL,
                        gross_pnl_usd REAL,
                        gas_cost_usd REAL,
                        net_pnl_usd REAL,
                        net_pnl_eur REAL,
                        cumulative_profit_usd REAL,
                        cumulative_profit_eur REAL,
                        wallet_gas_eur REAL,
                        status TEXT
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_block ON paper_trades(block_number)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_paper_pair ON paper_trades(pair)")
                conn.commit()

        if self.csv_path:
            os.makedirs(os.path.dirname(self.csv_path) or ".", exist_ok=True)
            if not os.path.exists(self.csv_path):
                with open(self.csv_path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "trade_id", "timestamp", "block_number", "pair",
                        "buy_dex", "sell_dex", "flash_loan_usd", "gross_pct",
                        "net_spread_pct", "gross_pnl_usd", "gas_cost_usd",
                        "net_pnl_usd", "net_pnl_eur", "cumulative_profit_eur",
                        "wallet_gas_eur", "status"
                    ])

    def evaluate_opportunity(
        self,
        block: int,
        pair: str,
        buy_dex: str,
        sell_dex: str,
        gross_pct: float,
        net_pct: float,
        gas_cost_usd: float,
        timestamp: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Valuta se un'opportunità soddisfa i criteri minimi di profitto
        ed esegue un paper trade atomico.
        """
        if timestamp is None:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # Verifica saldo gas
        gas_cost_eur = gas_cost_usd / EUR_USD_RATE
        if self.wallet_gas_balance_eur < gas_cost_eur:
            return None  # Portafoglio a secco di gas

        # Taglia del Flash Loan adatta alla liquidità
        loan_size = self._get_optimal_loan_size(pair)

        # Spread effettivo al netto di uno slippage cautelativo aggiuntivo
        effective_net_pct = net_pct - self.slippage_buffer_pct

        if effective_net_pct < self.min_net_spread_pct:
            return None

        # Calcolo economico del trade
        gross_pnl_usd = loan_size * (effective_net_pct / 100.0)
        net_pnl_usd = gross_pnl_usd - gas_cost_usd
        net_pnl_eur = net_pnl_usd / EUR_USD_RATE

        if net_pnl_usd <= 0:
            # Revert di sicurezza (lo smart contract non scambia se non in profitto)
            self.wallet_gas_balance_eur -= gas_cost_eur
            self.total_trades_reverted += 1
            status = "REVERTED_ZERO_PROFIT"
            net_pnl_usd = -gas_cost_usd
            net_pnl_eur = -gas_cost_eur
        else:
            # Esecuzione riuscita con profitto incassato
            self.wallet_gas_balance_eur -= gas_cost_eur
            self.cumulative_profit_usd += net_pnl_usd
            self.cumulative_profit_eur += net_pnl_eur
            self.total_gas_spent_usd += gas_cost_usd
            self.total_gas_spent_eur += gas_cost_eur
            self.total_trades_executed += 1
            status = "EXECUTED"

        trade_record = {
            "timestamp": timestamp,
            "block_number": block,
            "pair": pair,
            "buy_dex": buy_dex,
            "sell_dex": sell_dex,
            "flash_loan_usd": loan_size,
            "gross_spread_pct": gross_pct,
            "slippage_pct": self.slippage_buffer_pct,
            "net_spread_pct": effective_net_pct,
            "gross_pnl_usd": gross_pnl_usd,
            "gas_cost_usd": gas_cost_usd,
            "net_pnl_usd": net_pnl_usd,
            "net_pnl_eur": net_pnl_eur,
            "cumulative_profit_usd": self.cumulative_profit_usd,
            "cumulative_profit_eur": self.cumulative_profit_eur,
            "wallet_gas_eur": self.wallet_gas_balance_eur,
            "current_wallet_total_eur": self.initial_gas_eur + self.cumulative_profit_eur,
            "roi_pct": (self.cumulative_profit_eur / self.initial_gas_eur) * 100.0,
            "status": status
        }

        self._record_trade(trade_record)
        return trade_record

    def _get_optimal_loan_size(self, pair: str) -> float:
        """
        Adatta la dimensione del Flash Loan alla profondità stimata del book
        per evitare eccessivo price impact.
        """
        p_upper = pair.upper()
        if "WETH / USDC" in p_upper or "USDT / USDC" in p_upper:
            return 2500.0   # Pool molto profonde
        elif "wstETH" in p_upper or "cbBTC" in p_upper or "USDbC" in p_upper:
            return 1000.0   # Pool medio-grandi
        elif "VIRTUAL" in p_upper or "AERO" in p_upper:
            return 750.0    # Token volatili con buona liquidità
        else:
            return 500.0    # Coppie più giovani/sottili (SEAM, EURC, ecc.)

    def _record_trade(self, t: Dict[str, Any]):
        if self.db_path:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO paper_trades (
                        timestamp, block_number, pair, buy_dex, sell_dex,
                        flash_loan_usd, gross_spread_pct, slippage_pct, net_spread_pct,
                        gross_pnl_usd, gas_cost_usd, net_pnl_usd, net_pnl_eur,
                        cumulative_profit_usd, cumulative_profit_eur, wallet_gas_eur, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    t["timestamp"], t["block_number"], t["pair"], t["buy_dex"], t["sell_dex"],
                    t["flash_loan_usd"], t["gross_spread_pct"], t["slippage_pct"], t["net_spread_pct"],
                    t["gross_pnl_usd"], t["gas_cost_usd"], t["net_pnl_usd"], t["net_pnl_eur"],
                    t["cumulative_profit_usd"], t["cumulative_profit_eur"], t["wallet_gas_eur"], t["status"]
                ))
                conn.commit()

        if self.csv_path:
            with open(self.csv_path, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    self.total_trades_executed + self.total_trades_reverted,
                    t["timestamp"], t["block_number"], t["pair"],
                    t["buy_dex"], t["sell_dex"], f"{t['flash_loan_usd']:.2f}",
                    f"{t['gross_spread_pct']:.4f}", f"{t['net_spread_pct']:.4f}",
                    f"{t['gross_pnl_usd']:.4f}", f"{t['gas_cost_usd']:.4f}",
                    f"{t['net_pnl_usd']:.4f}", f"{t['net_pnl_eur']:.4f}",
                    f"{t['cumulative_profit_eur']:.4f}", f"{t['wallet_gas_eur']:.4f}",
                    t["status"]
                ])

    def get_summary(self) -> Dict[str, Any]:
        total_pnl_eur = self.cumulative_profit_eur
        net_wallet_eur = self.wallet_gas_balance_eur + total_pnl_eur
        roi_on_capital = ((net_wallet_eur - self.initial_gas_eur) / self.initial_gas_eur) * 100.0

        return {
            "initial_gas_wallet_eur": self.initial_gas_eur,
            "remaining_gas_eur": self.wallet_gas_balance_eur,
            "total_gas_spent_eur": self.total_gas_spent_eur,
            "trades_executed": self.total_trades_executed,
            "trades_reverted": self.total_trades_reverted,
            "total_profit_usd": self.cumulative_profit_usd,
            "total_profit_eur": self.cumulative_profit_eur,
            "final_account_value_eur": net_wallet_eur,
            "roi_pct": roi_on_capital
        }
