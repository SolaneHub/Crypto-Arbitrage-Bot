import os
import sys
import json
import sqlite3
import csv
import time
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

from config.settings import (
    MULTICALL3_ADDRESS,
    ESTIMATED_GAS_UNITS,
    DEFAULT_SIMULATION_USD
)
from scanner.discovery import VERIFIED_TOKENS
from scanner.notifier import MarketNotifier

EUR_USD_RATE = 1.085
BASE_MAINNET_RPC = os.getenv("BASE_MAINNET_RPC", "https://mainnet.base.org")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ATOMIC_ARBITRAGE_ADDRESS = os.getenv("ATOMIC_ARBITRAGE_ADDRESS")
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
UNI_V3_ROUTER = "0x2626664c2603336E57B271c5C0b26F421741e481"

MIN_ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"}
]

class LiveTrader:
    """
    Motore di esecuzione Live On-Chain per Base Mainnet.
    Opera in simbiosi con lo Smart Contract AtomicArbitrage.sol.
    
    Salvaguardia Assoluta:
    Prima di inviare ogni transazione alla blockchain, esegue una simulazione
    preventiva 'eth_call'. Se la transazione non genera profitto o incorre
    in slippage, viene annullata a monte a costo 0,00 € di gas.
    """

    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or BASE_MAINNET_RPC
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 15}))
        if not self.w3.is_connected():
            raise ConnectionError(f"Impossibile connettersi all'RPC di Base: {self.rpc_url}")

        self.wallet_address = Web3.to_checksum_address(WALLET_ADDRESS) if WALLET_ADDRESS else None
        self.private_key = PRIVATE_KEY
        self.contract_address = Web3.to_checksum_address(ATOMIC_ARBITRAGE_ADDRESS) if ATOMIC_ARBITRAGE_ADDRESS else None

        abi_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contracts", "AtomicArbitrage_abi.json")
        with open(abi_path, "r") as f:
            self.contract_abi = json.load(f)

        if self.contract_address:
            self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.contract_abi)
        else:
            self.contract = None

        self.usdc_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS),
            abi=MIN_ERC20_ABI
        )

        self.db_path = "data/market_history.db"
        self.csv_path = "data/live_trading_ledger.csv"
        self.total_live_trades = 0
        self.total_reverts_prevented = 0
        self.cumulative_profit_eur = 0.0
        self.cumulative_profit_usd = 0.0
        self.total_gas_spent_eur = 0.0
        self.notifier = MarketNotifier()

        self._init_storage()

    def _init_storage(self):
        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS live_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    block_number INTEGER,
                    tx_hash TEXT,
                    pair TEXT,
                    buy_dex TEXT,
                    sell_dex TEXT,
                    flash_loan_usd REAL,
                    net_profit_usd REAL,
                    net_profit_eur REAL,
                    gas_cost_usd REAL,
                    gas_cost_eur REAL,
                    gas_used INTEGER,
                    wallet_eth_after REAL,
                    wallet_usdc_after REAL,
                    status TEXT,
                    basescan_url TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_live_block ON live_trades(block_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_live_pair ON live_trades(pair)")
            conn.commit()

        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "block_number", "tx_hash", "pair",
                    "buy_dex", "sell_dex", "flash_loan_usd", "net_profit_eur",
                    "gas_cost_eur", "wallet_eth_after", "status", "basescan_url"
                ])

    def get_wallet_balances(self) -> Dict[str, float]:
        """Restituisce il saldo in tempo reale del portafoglio su Base Mainnet."""
        if not self.wallet_address:
            return {"eth": 0.0, "eth_eur": 0.0, "usdc": 0.0, "usdc_eur": 0.0, "total_eur": 0.0}

        eth_wei = self.w3.eth.get_balance(self.wallet_address)
        eth_bal = float(self.w3.from_wei(eth_wei, "ether"))

        try:
            usdc_raw = self.usdc_contract.functions.balanceOf(self.wallet_address).call()
            usdc_bal = usdc_raw / 1e6
        except Exception:
            usdc_bal = 0.0

        eth_price_usd = 2465.0
        eth_eur = (eth_bal * eth_price_usd) / EUR_USD_RATE
        usdc_eur = usdc_bal / EUR_USD_RATE
        total_eur = eth_eur + usdc_eur

        return {
            "eth": eth_bal,
            "eth_eur": eth_eur,
            "usdc": usdc_bal,
            "usdc_eur": usdc_eur,
            "total_eur": total_eur,
            "eth_wei": eth_wei
        }

    def send_telegram_alert(self, message: str):
        """Invia notifica Telegram se configurata in .env."""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            return
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            requests.post(url, json=payload, timeout=5)
        except Exception:
            pass

    def evaluate_and_execute(
        self,
        pair_cfg: Dict[str, Any],
        opportunity: Dict[str, Any],
        flash_loan_usd: float = DEFAULT_SIMULATION_USD
    ) -> Dict[str, Any]:
        """
        Valuta ed esegue un'opportunità di arbitraggio dal vivo su Base Mainnet.
        1. Ricava la sequenza di pool e token corretti.
        2. Esegue eth_call: se la simulazione fallisce, annulla senza inviare tx.
        3. Se la simulazione ha successo con profitto, invia la transazione reale.
        """
        if not self.contract or not self.wallet_address or not self.private_key:
            return {"status": "NOT_CONFIGURED", "reason": "Credenziali wallet o contratto mancanti."}

        base_sym = pair_cfg["base_symbol"]
        quote_sym = pair_cfg["quote_symbol"]

        if base_sym not in VERIFIED_TOKENS or quote_sym not in VERIFIED_TOKENS:
            return {"status": "SKIPPED", "reason": "Token non censito nel registro verificato."}

        base_addr = Web3.to_checksum_address(VERIFIED_TOKENS[base_sym]["address"])
        quote_addr = Web3.to_checksum_address(VERIFIED_TOKENS[quote_sym]["address"])
        quote_dec = VERIFIED_TOKENS[quote_sym]["decimals"]

        # Determina quale pool compra (DEX più basso) e quale pool vende (DEX più alto)
        pool_a = pair_cfg["pool_a"]
        pool_b = pair_cfg["pool_b"]

        buy_dex = opportunity["buy_dex"]
        if pool_a["name"] == buy_dex:
            buy_pool = pool_a
            sell_pool = pool_b
        else:
            buy_pool = pool_b
            sell_pool = pool_a

        # Configura parametri Leg 1 (Acquisto Base Token con Quote Token)
        leg1_is_v3 = (buy_pool["type"] == "v3")
        leg1_target = Web3.to_checksum_address(UNI_V3_ROUTER if leg1_is_v3 else buy_pool["address"])
        leg1_fee = buy_pool["fee_bps"] * 100 if leg1_is_v3 else 0

        # Configura parametri Leg 2 (Vendita Base Token per riottenere Quote Token)
        leg2_is_v3 = (sell_pool["type"] == "v3")
        leg2_target = Web3.to_checksum_address(UNI_V3_ROUTER if leg2_is_v3 else sell_pool["address"])
        leg2_fee = sell_pool["fee_bps"] * 100 if leg2_is_v3 else 0

        # Calcolo importo prestito flash loan
        eth_price_usd = 2465.0
        if pair_cfg["is_quote_eth"]:
            loan_units = flash_loan_usd / eth_price_usd
        else:
            loan_units = flash_loan_usd

        loan_raw = int(loan_units * (10**quote_dec))
        min_profit_raw = 0

        # Costruzione della struct ExecutionPlan per AtomicArbitrage.sol
        plan = (
            quote_addr,
            loan_raw,
            base_addr,
            0 if leg1_is_v3 else 1,
            leg1_target,
            leg1_fee,
            0 if leg2_is_v3 else 1,
            leg2_target,
            leg2_fee,
            min_profit_raw
        )

        # -------------------------------------------------------------
        # LIVELLO DIFENSIVO 1: SIMULAZIONE PREVENTIVA ON-CHAIN (eth_call)
        # Costo: 0,00 € di gas. Se fallisce, il trade non parte MAI.
        # -------------------------------------------------------------
        try:
            self.contract.functions.executeAaveFlashArbitrage(plan).call({"from": self.wallet_address})
        except Exception as sim_err:
            self.total_reverts_prevented += 1
            err_msg = str(sim_err)
            if "0x4e88422a" in err_msg or "InsufficientProfit" in err_msg:
                reason = "Slippage o profitto netto inferiore alle fee dei DEX"
            else:
                reason = f"Revert protettivo ({type(sim_err).__name__})"

            return {
                "status": "SIM_PREVENTED",
                "pair": pair_cfg["name"],
                "reason": reason,
                "gas_cost_eur": 0.0
            }

        # -------------------------------------------------------------
        # LIVELLO 2: ESECUZIONE REALE ON-CHAIN (Solo se eth_call ha avuto successo!)
        # -------------------------------------------------------------
        bal_before = self.get_wallet_balances()
        curr_block = self.w3.eth.block_number
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        try:
            nonce = self.w3.eth.get_transaction_count(self.wallet_address, "pending")
            gas_price = int(self.w3.eth.gas_price * 1.15)  # +15% per inclusione istantanea al blocco

            tx_data = self.contract.functions.executeAaveFlashArbitrage(plan).build_transaction({
                "from": self.wallet_address,
                "nonce": nonce,
                "gas": 750000,
                "gasPrice": gas_price,
                "chainId": 8453
            })

            signed_tx = self.w3.eth.account.sign_transaction(tx_data, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hex = tx_hash.hex()
            basescan_url = f"https://basescan.org/tx/{tx_hex}"

            # Attendi conferma (~2 secondi su Base L2)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=45)
            gas_used = receipt.gasUsed
            gas_cost_eth = (gas_used * receipt.effectiveGasPrice) / 1e18
            gas_cost_usd = gas_cost_eth * eth_price_usd
            gas_cost_eur = gas_cost_usd / EUR_USD_RATE

            bal_after = self.get_wallet_balances()

            if receipt.status == 1:
                usdc_diff = bal_after["usdc"] - bal_before["usdc"]
                eth_diff = bal_after["eth"] - bal_before["eth"]
                
                net_profit_usd = usdc_diff + (eth_diff * eth_price_usd)
                net_profit_eur = net_profit_usd / EUR_USD_RATE

                self.total_live_trades += 1
                self.cumulative_profit_eur += net_profit_eur
                self.cumulative_profit_usd += net_profit_usd
                self.total_gas_spent_eur += gas_cost_eur

                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO live_trades (
                            timestamp, block_number, tx_hash, pair, buy_dex, sell_dex,
                            flash_loan_usd, net_profit_usd, net_profit_eur, gas_cost_usd,
                            gas_cost_eur, gas_used, wallet_eth_after, wallet_usdc_after,
                            status, basescan_url
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        now_str, curr_block, tx_hex, pair_cfg["name"],
                        buy_dex, sell_pool["name"], flash_loan_usd,
                        net_profit_usd, net_profit_eur, gas_cost_usd,
                        gas_cost_eur, gas_used, bal_after["eth"], bal_after["usdc"],
                        "CONFIRMED", basescan_url
                    ))
                    conn.commit()

                with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        now_str, curr_block, tx_hex, pair_cfg["name"],
                        buy_dex, sell_pool["name"], f"{flash_loan_usd:.0f}",
                        f"{net_profit_eur:.4f}", f"{gas_cost_eur:.5f}",
                        f"{bal_after['eth']:.6f}", "CONFIRMED", basescan_url
                    ])

                self.notifier.notify_trade_executed(
                    pair=pair_cfg["name"],
                    buy_dex=buy_dex,
                    sell_dex=sell_pool["name"],
                    flash_loan_usd=flash_loan_usd,
                    net_profit_eur=net_profit_eur,
                    net_profit_usd=net_profit_usd,
                    gas_cost_eur=gas_cost_eur,
                    wallet_total_eur=bal_after["total_eur"],
                    tx_hash=tx_hex,
                    basescan_url=basescan_url
                )

                return {
                    "status": "CONFIRMED",
                    "pair": pair_cfg["name"],
                    "tx_hash": tx_hex,
                    "basescan_url": basescan_url,
                    "net_profit_eur": net_profit_eur,
                    "net_profit_usd": net_profit_usd,
                    "gas_cost_eur": gas_cost_eur,
                    "gas_used": gas_used,
                    "wallet_after": bal_after
                }
            else:
                return {
                    "status": "REVERTED_ON_CHAIN",
                    "tx_hash": tx_hex,
                    "basescan_url": basescan_url,
                    "gas_cost_eur": gas_cost_eur
                }

        except Exception as tx_err:
            return {
                "status": "ERROR",
                "pair": pair_cfg["name"],
                "reason": str(tx_err)
            }
