import json
import os
import requests
from typing import Dict, Any, List, Optional, Tuple
from web3 import Web3
from config.settings import RPC_ENDPOINTS, MULTICALL3_ADDRESS
from scanner.multicall import MulticallManager

# Indirizzi Factory standard su Base L2
UNI_V3_FACTORY = Web3.to_checksum_address("0x33128a8fC17869897dcE68Ed026d694621f6FDfD")
AERO_FACTORY = Web3.to_checksum_address("0x420DD381b31aEf6683db6B902084cB0FFECe40Da")
PANCAKE_V3_FACTORY = Web3.to_checksum_address("0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865")

# ABI essenziali per Factory e Pool
UNI_FACTORY_ABI = [{
    "inputs": [
        {"name": "tokenA", "type": "address"},
        {"name": "tokenB", "type": "address"},
        {"name": "fee", "type": "uint24"}
    ],
    "name": "getPool",
    "outputs": [{"name": "", "type": "address"}],
    "stateMutability": "view",
    "type": "function"
}]

AERO_FACTORY_ABI = [{
    "inputs": [
        {"name": "tokenA", "type": "address"},
        {"name": "tokenB", "type": "address"},
        {"name": "stable", "type": "bool"}
    ],
    "name": "getPool",
    "outputs": [{"name": "", "type": "address"}],
    "stateMutability": "view",
    "type": "function"
}]

POOL_BASE_ABI = [
    {"inputs": [], "name": "token0", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "token1", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "liquidity", "outputs": [{"name": "", "type": "uint128"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getReserves", "outputs": [{"name": "r0", "type": "uint112"}, {"name": "r1", "type": "uint112"}, {"name": "t", "type": "uint32"}], "stateMutability": "view", "type": "function"}
]

# Registro dei Token Istituzionali verificati su Base (No-Meme)
VERIFIED_TOKENS = {
    "WETH": {"address": "0x4200000000000000000000000000000000000006", "decimals": 18, "category": "Core"},
    "USDC": {"address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "decimals": 6, "category": "Stable"},
    "USDT": {"address": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2", "decimals": 6, "category": "Stable"},
    "EURC": {"address": "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42", "decimals": 6, "category": "FX/Stable"},
    "DAI": {"address": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb", "decimals": 18, "category": "Stable"},
    "USDbC": {"address": "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA", "decimals": 6, "category": "Stable"},
    "cbBTC": {"address": "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf", "decimals": 8, "category": "Bitcoin"},
    "tBTC": {"address": "0x236aa50979D5f3De3Bd1Eeb40E81137F22ab794b", "decimals": 18, "category": "Bitcoin"},
    "wstETH": {"address": "0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452", "decimals": 18, "category": "LST"},
    "cbETH": {"address": "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22", "decimals": 18, "category": "LST"},
    "rETH": {"address": "0xB6fe221Fe9EeF5aBa221c348bA20A1Bf5e73624c", "decimals": 18, "category": "LST"},
    "weETH": {"address": "0x04C0599Ae5A44757c0af6F9eC3b93da8976c150A", "decimals": 18, "category": "LRT"},
    "ezETH": {"address": "0x2416092f143378750bb29b79eD961ab195CcEea5", "decimals": 18, "category": "LRT"},
    "AERO": {"address": "0x940181a94A35A4569E4529A3CDfB74e38FD98631", "decimals": 18, "category": "DEX"},
    "VIRTUAL": {"address": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b", "decimals": 18, "category": "AI Ecosystem"},
    "SEAM": {"address": "0x1C7a460413dD4e964f96D8dFC56E7223cE88CD85", "decimals": 18, "category": "Lending/DeFi"},
    "SNX": {"address": "0x22e6966B799c4D5B13BE962E1D117b56327FDa66", "decimals": 18, "category": "Synthetics/DeFi"}
}

MEME_EXCLUSION_KEYWORDS = [
    "inu", "dog", "cat", "pepe", "shib", "trump", "elon", "pump",
    "moon", "brett", "toshi", "wif", "frog", "baby", "maga", "safe",
    "chad", "wojak", "bonk", "banana", "boomer"
]

class PairDiscoveryEngine:
    """
    Motore centralizzato per la ricerca, verifica di liquidità e generazione
    di configurazioni di coppie di arbitraggio su Base L2.
    """

    def __init__(self, manager: Optional[MulticallManager] = None):
        self.manager = manager or MulticallManager(RPC_ENDPOINTS, MULTICALL3_ADDRESS)
        self.w3 = self.manager.w3
        self.uni_factory = self.w3.eth.contract(address=UNI_V3_FACTORY, abi=UNI_FACTORY_ABI)
        self.aero_factory = self.w3.eth.contract(address=AERO_FACTORY, abi=AERO_FACTORY_ABI)
        self.pancake_factory = self.w3.eth.contract(address=PANCAKE_V3_FACTORY, abi=UNI_FACTORY_ABI)

    def find_best_univ3_pool(self, token_a: str, token_b: str) -> Optional[Dict[str, Any]]:
        """Trova la pool Uniswap V3 con liquidità attiva maggiore per la coppia."""
        best_pool = None
        max_liq = -1
        t_a = Web3.to_checksum_address(token_a)
        t_b = Web3.to_checksum_address(token_b)

        for fee in [100, 500, 3000, 10000]:
            try:
                p_addr = self.uni_factory.functions.getPool(t_a, t_b, fee).call()
                if p_addr and p_addr != "0x0000000000000000000000000000000000000000":
                    c = self.w3.eth.contract(address=p_addr, abi=POOL_BASE_ABI)
                    liq = c.functions.liquidity().call()
                    if liq > max_liq:
                        max_liq = liq
                        token0 = c.functions.token0().call()
                        best_pool = {
                            "name": "Uniswap V3",
                            "address": p_addr,
                            "type": "v3",
                            "fee_bps": fee // 100,
                            "liquidity": liq,
                            "token0": token0,
                            "token0_is_base": (token0.lower() == t_a.lower())
                        }
            except Exception:
                continue

        return best_pool

    def find_best_aerodrome_pool(self, token_a: str, token_b: str) -> Optional[Dict[str, Any]]:
        """Trova la pool Aerodrome (Stable o V2) con riserve reali maggiori per la coppia."""
        best_pool = None
        max_res = -1
        t_a = Web3.to_checksum_address(token_a)
        t_b = Web3.to_checksum_address(token_b)

        for is_stable in [False, True]:
            try:
                p_addr = self.aero_factory.functions.getPool(t_a, t_b, is_stable).call()
                if p_addr and p_addr != "0x0000000000000000000000000000000000000000":
                    c = self.w3.eth.contract(address=p_addr, abi=POOL_BASE_ABI)
                    r0, r1, _ = c.functions.getReserves().call()
                    tot_res = r0 + r1
                    if tot_res > max_res and r0 > 0 and r1 > 0:
                        max_res = tot_res
                        token0 = c.functions.token0().call()
                        best_pool = {
                            "name": f"Aerodrome {'Stable' if is_stable else 'V2'}",
                            "address": p_addr,
                            "type": "v2",
                            "fee_bps": 5 if is_stable else 30,
                            "reserves": (r0, r1),
                            "token0": token0,
                            "token0_is_base": (token0.lower() == t_a.lower())
                        }
            except Exception:
                continue

        return best_pool

    def build_cross_dex_pair(self, base_sym: str, quote_sym: str) -> Optional[Dict[str, Any]]:
        """
        Costruisce automaticamente l'oggetto coppia cross-DEX pronto per il bot,
        verificando la disponibilità e la liquidità su entrambi i DEX.
        """
        if base_sym not in VERIFIED_TOKENS or quote_sym not in VERIFIED_TOKENS:
            return None

        t_base = VERIFIED_TOKENS[base_sym]["address"]
        t_quote = VERIFIED_TOKENS[quote_sym]["address"]

        pool_u = self.find_best_univ3_pool(t_base, t_quote)
        pool_a = self.find_best_aerodrome_pool(t_base, t_quote)

        if not pool_u or not pool_a:
            return None

        return {
            "id": f"{base_sym}_{quote_sym}",
            "name": f"{base_sym} / {quote_sym}",
            "base_symbol": base_sym,
            "quote_symbol": quote_sym,
            "base_decimals": VERIFIED_TOKENS[base_sym]["decimals"],
            "quote_decimals": VERIFIED_TOKENS[quote_sym]["decimals"],
            "is_quote_eth": (quote_sym == "WETH"),
            "pool_a": {
                "name": pool_u["name"],
                "address": pool_u["address"],
                "type": pool_u["type"],
                "fee_bps": pool_u["fee_bps"],
                "token0_is_base": pool_u["token0_is_base"]
            },
            "pool_b": {
                "name": pool_a["name"],
                "address": pool_a["address"],
                "type": pool_a["type"],
                "fee_bps": pool_a["fee_bps"],
                "token0_is_base": pool_a["token0_is_base"]
            }
        }

    @staticmethod
    def search_gecko_terminal(min_liquidity: float = 50000, min_volume_24h: float = 10000) -> List[Dict[str, Any]]:
        """
        Interroga GeckoTerminal su Base per trovare pool attive ad alto volume
        escludendo automaticamente memecoin e honeypot evidenti.
        """
        url = "https://api.geckoterminal.com/api/v2/networks/base/pools?page=1"
        headers = {"Accept": "application/json;version=20230302"}
        results = []

        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json().get("data", [])
                for item in data:
                    attr = item.get("attributes", {})
                    name = attr.get("name", "")
                    pool_addr = attr.get("address")
                    dex = item.get("relationships", {}).get("dex", {}).get("data", {}).get("id", "")
                    vol = float(attr.get("volume_usd", {}).get("h24") or 0)
                    liq = float(attr.get("reserve_in_usd") or 0)

                    # Filtra memecoin
                    is_meme = any(k in name.lower() for k in MEME_EXCLUSION_KEYWORDS)
                    if is_meme or liq < min_liquidity or vol < min_volume_24h:
                        continue

                    results.append({
                        "name": name,
                        "dex": dex,
                        "address": pool_addr,
                        "volume_24h": vol,
                        "liquidity": liq
                    })
        except Exception as e:
            print(f"[!] Errore interrogazione GeckoTerminal: {e}")

        return results
