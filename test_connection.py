from web3 import Web3

# Lista di RPC pubblici gratuiti per iniziare i test
NETWORKS = {
    "Base": "https://mainnet.base.org",
    "Arbitrum One": "https://arb1.arbitrum.io/rpc",
    "Polygon": "https://polygon-rpc.com",
}

def test_connections():
    print("=== TEST CONNESSIONE BLOCKCHAIN ===")
    for name, rpc_url in NETWORKS.items():
        print(f"\n[+] Connessione a {name} ({rpc_url})...")
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={'timeout': 10}))
            if w3.is_connected():
                chain_id = w3.eth.chain_id
                block_number = w3.eth.block_number
                gas_price_gwei = w3.from_wei(w3.eth.gas_price, 'gwei')
                print(f"    [OK] Connesso!")
                print(f"    - Chain ID: {chain_id}")
                print(f"    - Ultimo Blocco: {block_number}")
                print(f"    - Gas Price: {gas_price_gwei:.4f} Gwei")
            else:
                print("    [!] Connessione fallita.")
        except Exception as e:
            print(f"    [ERRORE] {e}")

if __name__ == "__main__":
    test_connections()
