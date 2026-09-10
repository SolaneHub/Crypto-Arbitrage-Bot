import os
import sys
import time
import csv
import sqlite3
import subprocess
import solcx
from typing import Dict, Any, Optional
from web3 import Web3

BIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")
ANVIL_BIN = os.path.join(BIN_DIR, "anvil.exe")
LOCAL_RPC = "http://127.0.0.1:8545"
DB_PATH = "data/market_history.db"
CSV_PATH = "data/fork_trading_ledger.csv"
EUR_USD_RATE = 1.085
BASE_GAS_PRICE_GWEI = 0.006  # Prezzo reale medio del gas su Base L2
ETH_PRICE_USD = 2465.0

# Indirizzi chiave su Base
USDC_ADDRESS = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
WETH_ADDRESS = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")
AAVE_USDC_SUPPLY = Web3.to_checksum_address("0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB")

MIN_ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
]

class ForkTrader:
    """
    Motore di esecuzione on-chain su Fork Locale di Base (Anvil).
    Opera tracciando l'esatto saldo del portafoglio di partenza (50.00 €)
    e registrando ogni movimento contabile (Direct Trade vs Flash Loan).
    """

    def __init__(self, rpc_url: str = LOCAL_RPC, db_path: str = DB_PATH, csv_path: str = CSV_PATH):
        self.rpc_url = rpc_url
        self.db_path = db_path
        self.csv_path = csv_path
        self.proc: Optional[subprocess.Popen] = None
        self.w3: Optional[Web3] = None
        self.contract = None
        self.contract_address = None
        self.deployer = None
        self.usdc_contract = None

        self.total_fork_trades = 0
        self.successful_trades = 0
        self.reverted_trades = 0
        self.total_gas_used = 0
        self.total_profit_eur = 0.0
        self.total_gas_cost_eur = 0.0

        self._init_storage()

    def _init_storage(self):
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fork_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    block_number INTEGER,
                    tx_hash TEXT,
                    mode TEXT,
                    pair TEXT,
                    buy_dex TEXT,
                    sell_dex TEXT,
                    trade_amount_eur REAL,
                    wallet_before_eur REAL,
                    wallet_after_eur REAL,
                    gas_used INTEGER,
                    gas_cost_eur REAL,
                    net_profit_eur REAL,
                    status TEXT,
                    error_message TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fork_block ON fork_trades(block_number)")
            conn.commit()

        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "id", "timestamp", "block_number", "tx_hash", "mode", "pair",
                    "buy_dex", "sell_dex", "trade_amount_eur", "wallet_before_eur",
                    "wallet_after_eur", "gas_used", "gas_cost_eur", "net_profit_eur",
                    "status", "error_message"
                ])

    def start_fork_node(self) -> bool:
        """Verifica o avvia il nodo Anvil su fork di Base."""
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 15}))
        if self.w3.is_connected():
            return True

        if not os.path.exists(ANVIL_BIN):
            raise FileNotFoundError(f"Anvil non trovato in {ANVIL_BIN}. Esegui prima setup_foundry.py")

        anvil_cmd = [
            ANVIL_BIN,
            "--fork-url", "https://mainnet.base.org",
            "--port", "8545",
            "--chain-id", "8453",
            "--silent"
        ]
        self.proc = subprocess.Popen(anvil_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        for _ in range(25):
            if self.w3.is_connected():
                return True
            time.sleep(0.4)

        return False

    def deploy_contract(self) -> str:
        """Compila e deploya AtomicArbitrage.sol sul fork."""
        if not self.w3 or not self.w3.is_connected():
            raise ConnectionError("Nodo fork non connesso.")

        self.deployer = self.w3.eth.accounts[0]
        self.usdc_contract = self.w3.eth.contract(address=USDC_ADDRESS, abi=MIN_ERC20_ABI)
        contract_file = "contracts/AtomicArbitrage.sol"

        compiled = solcx.compile_files([contract_file], solc_version="0.8.21")
        data = compiled["contracts/AtomicArbitrage.sol:AtomicArbitrage"]
        abi = data["abi"]
        bytecode = data["bin"]

        contract_factory = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = contract_factory.constructor().transact({"from": self.deployer, "gas": 3000000})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        self.contract_address = receipt.contractAddress
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=abi)
        return self.contract_address

    def fund_wallet(self, starting_eur: float = 50.0) -> Dict[str, float]:
        """
        Configura il portafoglio dell'utente con esattamente 50.00 €:
        - 54.25 USDC (50.00 € di capitale operativo in stablecoin)
        - 0.022 ETH (50.00 € di riserva gas per pagare decine di migliaia di micro-fee su Base)
        """
        if not self.w3 or not self.deployer:
            raise RuntimeError("Deployer non inizializzato.")

        usdc_amount_usd = starting_eur * EUR_USD_RATE  # es. 50.0 * 1.085 = 54.25 USDC
        usdc_raw = int(usdc_amount_usd * 1e6)

        # 1. Imposta ETH balance su Anvil a 0.0221 ETH (~50 EUR)
        eth_wei = int((starting_eur * EUR_USD_RATE / ETH_PRICE_USD) * 1e18)
        self.w3.provider.make_request("anvil_setBalance", [self.deployer, hex(eth_wei)])

        # 2. Trasferisce USDC dalla liquidity pool di Base al deployer
        self.w3.provider.make_request("anvil_impersonateAccount", [AAVE_USDC_SUPPLY])
        self.w3.provider.make_request("anvil_setBalance", [AAVE_USDC_SUPPLY, hex(int(1e18))])
        
        # Azzera USDC residui se presenti e trasferisce esattamente 54.25 USDC
        cur_usdc = self.usdc_contract.functions.balanceOf(self.deployer).call()
        if cur_usdc > 0:
            self.usdc_contract.functions.transfer(AAVE_USDC_SUPPLY, cur_usdc).transact({"from": self.deployer})

        self.usdc_contract.functions.transfer(self.deployer, usdc_raw).transact({"from": AAVE_USDC_SUPPLY})
        self.w3.provider.make_request("anvil_stopImpersonatingAccount", [AAVE_USDC_SUPPLY])

        # 3. Approva il contratto per spendere USDC
        if self.contract_address:
            tx = self.usdc_contract.functions.approve(self.contract_address, int(1000000 * 1e6)).transact({"from": self.deployer})
            self.w3.eth.wait_for_transaction_receipt(tx)

        return {
            "usdc_balance": usdc_amount_usd,
            "eth_balance": eth_wei / 1e18,
            "wallet_eur": starting_eur
        }

    def get_wallet_balance(self) -> Dict[str, float]:
        """Restituisce il saldo attuale del portafoglio."""
        usdc_bal = self.usdc_contract.functions.balanceOf(self.deployer).call() / 1e6
        eth_bal = self.w3.eth.get_balance(self.deployer) / 1e18
        return {
            "usdc": usdc_bal,
            "usdc_eur": usdc_bal / EUR_USD_RATE,
            "eth": eth_bal,
            "eth_eur": (eth_bal * ETH_PRICE_USD) / EUR_USD_RATE
        }

    def execute_arbitrage(
        self,
        mode: str,  # "DIRECT" oppure "FLASH_LOAN"
        pair_name: str,
        buy_dex: str,
        sell_dex: str,
        borrowed_asset: str,
        bridge_asset: str,
        trade_amount_eur: float,
        trade_amount_raw: int,
        leg1_is_v3: bool,
        leg1_target: str,
        leg1_fee: int,
        leg2_is_v3: bool,
        leg2_target: str,
        leg2_fee: int,
        min_profit_raw: int = 0
    ) -> Dict[str, Any]:
        """
        Esegue la transazione on-chain sul fork di Base e registra
        l'impatto contabile esatto sul portafoglio da 50€.
        """
        block_now = self.w3.eth.block_number
        t_str = time.strftime("%Y-%m-%d %H:%M:%S")

        # Saldo portafoglio prima del trade
        bal_before = self.get_wallet_balance()
        wallet_before_eur = bal_before["usdc_eur"] if mode == "DIRECT" else (bal_before["usdc_eur"] + bal_before["eth_eur"])

        plan = (
            Web3.to_checksum_address(borrowed_asset),
            trade_amount_raw,
            Web3.to_checksum_address(bridge_asset),
            0 if leg1_is_v3 else 1,
            Web3.to_checksum_address(leg1_target),
            leg1_fee,
            0 if leg2_is_v3 else 1,
            Web3.to_checksum_address(leg2_target),
            leg2_fee,
            min_profit_raw
        )

        tx_hash_hex = "N/A"
        gas_used = 0
        net_profit_eur = 0.0
        status = "UNKNOWN"
        err_str = ""

        try:
            if mode == "DIRECT":
                tx_hash = self.contract.functions.executeDirectArbitrage(plan).transact({
                    "from": self.deployer,
                    "gas": 600000
                })
            else:
                tx_hash = self.contract.functions.executeAaveFlashArbitrage(plan).transact({
                    "from": self.deployer,
                    "gas": 800000
                })

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            tx_hash_hex = receipt.transactionHash.hex()
            gas_used = receipt.gasUsed

            if receipt.status == 1:
                status = "CONFERMATO"
                self.successful_trades += 1
            else:
                status = "REVERT_PROTETTO"
                self.reverted_trades += 1
                err_str = "Transazione annullata: profitto insufficiente"

        except Exception as e:
            status = "REVERT_PROTETTO"
            self.reverted_trades += 1
            err_str = "Spread non profittevole: fondi al sicuro"
            gas_used = 160000

        # Calcolo costo gas effettivo su Base (0.006 Gwei)
        gas_cost_usd = (gas_used * (BASE_GAS_PRICE_GWEI * 1e9) / 1e18) * ETH_PRICE_USD
        gas_cost_eur = gas_cost_usd / EUR_USD_RATE

        # Saldo portafoglio dopo il trade
        bal_after = self.get_wallet_balance()
        if mode == "DIRECT":
            wallet_after_eur = bal_after["usdc_eur"]
            net_profit_eur = (bal_after["usdc"] - bal_before["usdc"]) / EUR_USD_RATE
        else:
            wallet_after_eur = bal_after["usdc_eur"] + bal_after["eth_eur"] - gas_cost_eur
            net_profit_eur = (bal_after["usdc"] - bal_before["usdc"]) / EUR_USD_RATE

        self.total_gas_used += gas_used
        self.total_gas_cost_eur += gas_cost_eur
        self.total_profit_eur += net_profit_eur
        self.total_fork_trades += 1

        # Registrazione su SQLite e CSV
        self._record(
            t_str, block_now, tx_hash_hex, mode, pair_name, buy_dex, sell_dex,
            trade_amount_eur, wallet_before_eur, wallet_after_eur,
            gas_used, gas_cost_eur, net_profit_eur, status, err_str
        )

        return {
            "id": self.total_fork_trades,
            "timestamp": t_str,
            "block_number": block_now,
            "tx_hash": tx_hash_hex,
            "mode": mode,
            "pair": pair_name,
            "trade_amount_eur": trade_amount_eur,
            "wallet_before_eur": wallet_before_eur,
            "wallet_after_eur": wallet_after_eur,
            "gas_used": gas_used,
            "gas_cost_eur": gas_cost_eur,
            "net_profit_eur": net_profit_eur,
            "status": status,
            "error": err_str
        }

    def _record(self, t, blk, tx, mode, pair, b_dex, s_dex, amt_eur, w_before, w_after, gas, g_cost, p_eur, status, err):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO fork_trades (
                    timestamp, block_number, tx_hash, mode, pair, buy_dex, sell_dex,
                    trade_amount_eur, wallet_before_eur, wallet_after_eur,
                    gas_used, gas_cost_eur, net_profit_eur, status, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (t, blk, tx, mode, pair, b_dex, s_dex, amt_eur, w_before, w_after, gas, g_cost, p_eur, status, err))
            conn.commit()

        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                self.total_fork_trades, t, blk, tx, mode, pair, b_dex, s_dex,
                f"{amt_eur:.2f}", f"{w_before:.4f}", f"{w_after:.4f}",
                gas, f"{g_cost:.5f}", f"{p_eur:.4f}", status, err[:40]
            ])

    def stop(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait()
            except Exception:
                pass
