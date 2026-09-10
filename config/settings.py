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

# File di log delle opportunità
LOG_FILE_ALL = "data/all_spreads.csv"
LOG_FILE_PROFIT = "data/profitable_opportunities.csv"

# Capitale di simulazione predefinito per il calcolo del profitto netto ($)
DEFAULT_SIMULATION_USD = 250.0

# 4 Coppie Volatili + WETH/USDC come ancora
MONITORED_PAIRS = [
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
            "fee_bps": 30, # 0.30%
            "token0_is_base": True
        },
        "pool_b": {
            "name": "Aerodrome V2",
            "address": Web3.to_checksum_address("0x21594b992F68495dD28d605834b58889d0a727c7"),
            "type": "v2",
            "fee_bps": 30, # 0.30%
            "token0_is_base": True
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
            "name": "Aerodrome V2",
            "address": Web3.to_checksum_address("0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d"),
            "type": "v2",
            "fee_bps": 30,
            "token0_is_base": False # token0=USDC, token1=AERO
        },
        "pool_b": {
            "name": "Uniswap V3",
            "address": Web3.to_checksum_address("0x2426DC0A657BD481ab48f86C1616431905901238"),
            "type": "v3",
            "fee_bps": 30,
            "token0_is_base": False
        }
    },
    {
        "id": "BRETT_WETH",
        "name": "BRETT / WETH",
        "base_symbol": "BRETT",
        "quote_symbol": "WETH",
        "base_decimals": 18,
        "quote_decimals": 18,
        "is_quote_eth": True,
        "pool_a": {
            "name": "Uniswap V3",
            "address": Web3.to_checksum_address("0xBA3F945812a83471d709BCe9C3CA699A19FB46f7"),
            "type": "v3",
            "fee_bps": 100, # 1.00%
            "token0_is_base": False # token0=WETH, token1=BRETT
        },
        "pool_b": {
            "name": "Aerodrome Slipstream",
            "address": Web3.to_checksum_address("0x4e829F8A5213c42535AB84AA40BD4aDCCE9cBa02"),
            "type": "slipstream",
            "fee_bps": 100,
            "token0_is_base": False
        }
    },
    {
        "id": "DEGEN_WETH",
        "name": "DEGEN / WETH",
        "base_symbol": "DEGEN",
        "quote_symbol": "WETH",
        "base_decimals": 18,
        "quote_decimals": 18,
        "is_quote_eth": True,
        "pool_a": {
            "name": "Aerodrome V2",
            "address": Web3.to_checksum_address("0x2C4909355b0C036840819484c3A882A95659aBf3"),
            "type": "v2",
            "fee_bps": 30,
            "token0_is_base": False # token0=WETH, token1=DEGEN
        },
        "pool_b": {
            "name": "Uniswap V3",
            "address": Web3.to_checksum_address("0x0cA6485b7e9cF814A3Fd09d81672B07323535b64"),
            "type": "v3",
            "fee_bps": 100,
            "token0_is_base": False
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
            "token0_is_base": True # token0=WETH, token1=USDC
        },
        "pool_b": {
            "name": "Aerodrome Volatile",
            "address": Web3.to_checksum_address("0xcDAC0d6c6C59727a65F871236188350531885C43"),
            "type": "v2",
            "fee_bps": 5,
            "token0_is_base": True
        }
    }
]
