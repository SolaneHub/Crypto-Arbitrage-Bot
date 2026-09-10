import time
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://base-rpc.publicnode.com"))
MULTICALL3_ADDRESS = Web3.to_checksum_address("0xcA11bde05977b3631167028862bE2a173976CA11")

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

multicall = w3.eth.contract(address=MULTICALL3_ADDRESS, abi=MULTICALL3_ABI)

# Pool di prova
target_pool = Web3.to_checksum_address("0xd0b53D9277642d899DF5C87A3966A349A798F224")
calldata = bytes.fromhex("3850c7bd")

test_batch_sizes = [16, 30, 50, 100, 150, 200, 300]

print("=== BENCHMARK LATENZA MULTICALL3 SU BASE NETWORK ===")
print(f"{'Pool Interrogate':<18} | {'Coppie Equivalenti':<20} | {'Tempo Roundtrip (ms)':>22} | {'Valutazione':<15}")
print("-" * 85)

for n in test_batch_sizes:
    calls = [{"target": target_pool, "allowFailure": True, "callData": calldata} for _ in range(n)]
    
    # Eseguiamo 3 tentativi e facciamo la media
    times = []
    for _ in range(3):
        t0 = time.perf_counter()
        results = multicall.functions.aggregate3(calls).call()
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
