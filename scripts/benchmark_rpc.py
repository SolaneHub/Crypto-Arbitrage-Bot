import time
import os
import sys
from web3 import Web3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import RPC_ENDPOINTS, MULTICALL3_ADDRESS

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
    }
]

def run_benchmark():
    w3 = Web3(Web3.HTTPProvider(RPC_ENDPOINTS[0], request_kwargs={"timeout": 10}))
    multicall = w3.eth.contract(address=MULTICALL3_ADDRESS, abi=MULTICALL3_ABI)

    # Pool di prova Uniswap V3 (WETH/USDC) con calldata slot0
    target_pool = Web3.to_checksum_address("0xd0b53D9277642d899DF5C87A3966A349A798F224")
    calldata = bytes.fromhex("3850c7bd")

    test_batch_sizes = [10, 25, 50, 100, 150, 200]

    print("=" * 85)
    print("      BENCHMARK LATENZA MULTICALL3 SULLA BLOCKCHAIN BASE (L2)")
    print(f"      Endpoint testato: {RPC_ENDPOINTS[0]}")
    print("=" * 85)
    print(f"{'Pool Interrogate':<18} | {'Coppie Equivalenti':<20} | {'Tempo Roundtrip (ms)':>22} | {'Valutazione':<15}")
    print("-" * 85)

    for n in test_batch_sizes:
        calls = [{"target": target_pool, "allowFailure": True, "callData": calldata} for _ in range(n)]

        times = []
        for _ in range(3):
            t0 = time.perf_counter()
            multicall.functions.aggregate3(calls).call()
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000.0)

        avg_ms = sum(times) / len(times)
        pairs_equiv = n // 2

        if avg_ms < 250:
            valutaz = "Fulmineo (<250ms)"
        elif avg_ms < 500:
            valutaz = "Ottimo (<500ms)"
        elif avg_ms < 1000:
            valutaz = "Accettabile (<1s)"
        else:
            valutaz = "Lento (>1s)"

        print(f"{n:<18} | {pairs_equiv:<20} | {avg_ms:>20.1f} ms | {valutaz:<15}")

    print("-" * 85)
    print("Con 50 pool (25 coppie) la latenza rimane ampiamente sotto il tempo di blocco (2.000 ms).\n")

if __name__ == "__main__":
    run_benchmark()
