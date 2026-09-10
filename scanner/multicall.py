from web3 import Web3
from typing import List, Dict, Any, Tuple
import logging

MULTICALL3_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "target", "type": "address"},
                    {"name": "allowFailure", "type": "bool"},
                    {"name": "callData", "type": "bytes"}
                ],
                "name": "calls",
                "type": "tuple[]"
            }
        ],
        "name": "aggregate3",
        "outputs": [
            {
                "components": [
                    {"name": "success", "type": "bool"},
                    {"name": "returnData", "type": "bytes"}
                ],
                "name": "returnData",
                "type": "tuple[]"
            }
        ],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getBlockNumber",
        "outputs": [{"name": "blockNumber", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

class MulticallManager:
    def __init__(self, rpc_urls: List[str], multicall_address: str):
        self.rpc_urls = rpc_urls
        self.multicall_address = Web3.to_checksum_address(multicall_address)
        self.current_rpc_index = 0
        self.w3 = self._init_web3()
        self.multicall_contract = self.w3.eth.contract(
            address=self.multicall_address,
            abi=MULTICALL3_ABI
        )

    def _init_web3(self) -> Web3:
        rpc = self.rpc_urls[self.current_rpc_index]
        return Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 6}))

    def _rotate_rpc(self):
        self.current_rpc_index = (self.current_rpc_index + 1) % len(self.rpc_urls)
        rpc = self.rpc_urls[self.current_rpc_index]
        self.w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 6}))
        self.multicall_contract = self.w3.eth.contract(
            address=self.multicall_address,
            abi=MULTICALL3_ABI
        )

    def aggregate(self, calls: List[Dict[str, Any]]) -> Tuple[int, List[Tuple[bool, bytes]]]:
        """Esegue una chiamata multicall batch. In caso di errore RPC fa failover automatico."""
        for _ in range(len(self.rpc_urls)):
            try:
                # Include la chiamata per il numero del blocco insieme alle altre
                formatted_calls = [
                    (c["target"], c.get("allowFailure", True), c["callData"])
                    for c in calls
                ]
                results = self.multicall_contract.functions.aggregate3(formatted_calls).call()
                block_number = self.w3.eth.block_number
                return block_number, results
            except Exception as e:
                self._rotate_rpc()
        raise ConnectionError("Tutti gli endpoint RPC hanno fallito.")
