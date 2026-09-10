from web3 import Web3

# Base RPC Endpoints (con fallback in caso di rate-limit)
RPC_ENDPOINTS = [
    "https://base-rpc.publicnode.com",
    "https://1rpc.io/base",
    "https://base.meowrpc.com",
    "https://mainnet.base.org"
]

CHAIN_ID = 8453
POLL_INTERVAL_SECONDS = 2.0  # Base ha blocchi di ~2 secondi

# Multicall3 universale EVM
MULTICALL3_ADDRESS = Web3.to_checksum_address("0xcA11bde05977b3631167028862bE2a173976CA11")

# Token Principali su Base
TOKENS = {
    "WETH": {
        "address": Web3.to_checksum_address("0x4200000000000000000000000000000000000006"),
        "decimals": 18,
        "symbol": "WETH"
    },
    "USDC": {
        "address": Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),
        "decimals": 6,
        "symbol": "USDC"
    }
}

# Pool monitorate su Base (WETH / USDC)
POOLS = [
    {
        "name": "Uniswap V3 (0.05%)",
        "dex": "Uniswap V3",
        "type": "univ3",
        "address": Web3.to_checksum_address("0xd0b53D9277642d899DF5C87A3966A349A798F224"),
        "base_token": "WETH",
        "quote_token": "USDC",
        "fee_pct": 0.05
    },
    {
        "name": "Aerodrome Volatile",
        "dex": "Aerodrome",
        "type": "univ2",
        "address": Web3.to_checksum_address("0xcDAC0d6c6C59727a65F871236188350531885C43"),
        "base_token": "WETH",
        "quote_token": "USDC",
        "fee_pct": 0.05
    },
    {
        "name": "BaseSwap V2",
        "dex": "BaseSwap",
        "type": "univ2",
        "address": Web3.to_checksum_address("0xab067c01C7F5734da168C699Ae9d23a4512c9FdB"),
        "base_token": "WETH",
        "quote_token": "USDC",
        "fee_pct": 0.30
    }
]

# Configurazione Log / Opportunità
MIN_SPREAD_ALERT_PCT = 0.05  # Notifica/Registra se lo spread lordo supera lo 0.05%
LOG_FILE = "data/opportunities.csv"
