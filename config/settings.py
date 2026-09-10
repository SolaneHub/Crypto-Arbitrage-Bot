import os
import json
from web3 import Web3

# Endpoints RPC Base con failover
RPC_ENDPOINTS = [
    "https://base-rpc.publicnode.com",
    "https://1rpc.io/base",
    "https://base.meowrpc.com",
    "https://mainnet.base.org"
]

CHAIN_ID = 8453
POLL_INTERVAL_SECONDS = 2.0  # Tempo di blocco su Base

# Multicall3 su Base
MULTICALL3_ADDRESS = Web3.to_checksum_address("0xcA11bde05977b3631167028862bE2a173976CA11")

# Stima costo medio gas per flash loan + 2 swap
ESTIMATED_GAS_UNITS = 180000

# File di log
LOG_FILE_ALL = "data/spread_snapshots.csv"
LOG_FILE_PROFIT = "data/profitable_opportunities.csv"
DB_PATH = "data/market_history.db"

# Capitale di simulazione predefinito per il calcolo del profitto netto ($)
DEFAULT_SIMULATION_USD = 250.0

# Carica le 25 Coppie No-Meme verificate on-chain da JSON
PAIRS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "25_pairs_config.json")

def load_monitored_pairs():
    if not os.path.exists(PAIRS_FILE):
        return []
    with open(PAIRS_FILE, "r") as f:
        pairs = json.load(f)
    for p in pairs:
        p["pool_a"]["address"] = Web3.to_checksum_address(p["pool_a"]["address"])
        p["pool_b"]["address"] = Web3.to_checksum_address(p["pool_b"]["address"])
    return pairs

MONITORED_PAIRS = load_monitored_pairs()
