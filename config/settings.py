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

# 8 COPPIE ISTITUZIONALI & NO-MEME SU BASE
MONITORED_PAIRS = [
    {
        "id": "cbBTC_WETH",
        "name": "cbBTC / WETH",
        "base_symbol": "cbBTC",
        "quote_symbol": "WETH",
        "base_decimals": 8,
        "quote_decimals": 18,
        "is_quote_eth": True,
        "pool_a": {
            "name": "Uniswap V3",
            "address": Web3.to_checksum_address("0x8c7080564B5A792A33Ef2FD473fbA6364d5495e5"),
            "type": "v3",
            "fee_bps": 30, # 0.30%
            "token0_is_base": False
        },
        "pool_b": {
            "name": "Aerodrome V2",
            "address": Web3.to_checksum_address("0x2578365B3dfA7FfE60108e181EFb79FeDdec2319"),
            "type": "v2",
            "fee_bps": 30, # 0.30%
            "token0_is_base": False
        }
    },
    {
        "id": "cbBTC_USDC",
        "name": "cbBTC / USDC",
        "base_symbol": "cbBTC",
        "quote_symbol": "USDC",
        "base_decimals": 8,
        "quote_decimals": 6,
        "is_quote_eth": False,
        "pool_a": {
            "name": "Uniswap V3",
            "address": Web3.to_checksum_address("0xeC558e484cC9f2210714E345298fdc53B253c27D"),
            "type": "v3",
            "fee_bps": 30,
            "token0_is_base": False
        },
        "pool_b": {
            "name": "Aerodrome V2",
            "address": Web3.to_checksum_address("0x9c38b55f9A9Aba91BbCEDEb12bf4428f47A6a0B8"),
            "type": "v2",
            "fee_bps": 30,
            "token0_is_base": False
        }
    },
    {
        "id": "wstETH_WETH",
        "name": "wstETH / WETH",
        "base_symbol": "wstETH",
        "quote_symbol": "WETH",
        "base_decimals": 18,
        "quote_decimals": 18,
        "is_quote_eth": True,
        "pool_a": {
            "name": "Uniswap V3",
            "address": Web3.to_checksum_address("0x6f4482cBF7b43599078fcb012732e20480015644"),
            "type": "v3",
            "fee_bps": 5, # 0.05%
            "token0_is_base": False
        },
        "pool_b": {
            "name": "Aerodrome V2",
            "address": Web3.to_checksum_address("0xA6385c73961dd9C58db2EF0c4EB98cE4B60651e8"),
            "type": "v2",
            "fee_bps": 5, # 0.05%
            "token0_is_base": False
        }
    },
    {
        "id": "AERO_WETH",
        "name": "AERO / WETH",
        "base_symbol": "AERO",
        "quote_symbol": "WETH",
        "base_decimals": 18,
        "quote_decimals": 18,
        "is_quote_eth": True,
        "pool_a": {
            "name": "Uniswap V3",
            "address": Web3.to_checksum_address("0x3d5D143381916280ff91407FeBEB52f2b60f33Cf"),
            "type": "v3",
            "fee_bps": 30,
            "token0_is_base": False
        },
        "pool_b": {
            "name": "Aerodrome V2",
            "address": Web3.to_checksum_address("0x7f670f78B17dEC44d5Ef68a48740b6f8849cc2e6"),
            "type": "v2",
            "fee_bps": 30,
            "token0_is_base": False
        }
    },
    {
        "id": "AERO_USDC",
        "name": "AERO / USDC",
        "base_symbol": "AERO",
        "quote_symbol": "USDC",
        "base_decimals": 18,
        "quote_decimals": 6,
        "is_quote_eth": False,
        "pool_a": {
            "name": "Uniswap V3",
            "address": Web3.to_checksum_address("0x2426DC0A657BD481ab48f86C1616431905901238"),
            "type": "v3",
            "fee_bps": 30,
            "token0_is_base": False
        },
        "pool_b": {
            "name": "Aerodrome V2",
            "address": Web3.to_checksum_address("0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d"),
            "type": "v2",
            "fee_bps": 30,
            "token0_is_base": False
        }
    },
    {
        "id": "VIRTUAL_WETH",
        "name": "VIRTUAL / WETH",
        "base_symbol": "VIRTUAL",
        "quote_symbol": "WETH",
        "base_decimals": 18,
        "quote_decimals": 18,
        "is_quote_eth": True,
        "pool_a": {
            "name": "Uniswap V2",
            "address": Web3.to_checksum_address("0xE31c372a7Af875b3B5E0F3713B17ef51556da667"),
            "type": "v2",
            "fee_bps": 30,
            "token0_is_base": True
        },
        "pool_b": {
            "name": "Aerodrome V2",
            "address": Web3.to_checksum_address("0x21594b992F68495dD28d605834b58889d0a727c7"),
            "type": "v2",
            "fee_bps": 30,
            "token0_is_base": True
        }
    },
    {
        "id": "VIRTUAL_USDC",
        "name": "VIRTUAL / USDC",
        "base_symbol": "VIRTUAL",
        "quote_symbol": "USDC",
        "base_decimals": 18,
        "quote_decimals": 6,
        "is_quote_eth": False,
        "pool_a": {
            "name": "Uniswap V3",
            "address": Web3.to_checksum_address("0x529d2863a1521d0b57db028168fdE2E97120017C"),
            "type": "v3",
            "fee_bps": 30,
            "token0_is_base": True
        },
        "pool_b": {
            "name": "Aerodrome V2",
            "address": Web3.to_checksum_address("0xDb79CecFd1897D2F60B0Ea7Af072CA9A9e71047c"),
            "type": "v2",
            "fee_bps": 30,
            "token0_is_base": True
        }
    },
    {
        "id": "WETH_USDC",
        "name": "WETH / USDC",
        "base_symbol": "WETH",
        "quote_symbol": "USDC",
        "base_decimals": 18,
        "quote_decimals": 6,
        "is_quote_eth": False,
        "pool_a": {
            "name": "Uniswap V3",
            "address": Web3.to_checksum_address("0xd0b53D9277642d899DF5C87A3966A349A798F224"),
            "type": "v3",
            "fee_bps": 5, # 0.05%
            "token0_is_base": True
        },
        "pool_b": {
            "name": "Aerodrome Volatile",
            "address": Web3.to_checksum_address("0xcDAC0d6c6C59727a65F871236188350531885C43"),
            "type": "v2",
            "fee_bps": 5, # 0.05%
            "token0_is_base": True
        }
    }
]
