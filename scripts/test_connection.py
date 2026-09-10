from web3 import Web3

NETWORKS = {
    "Base L2 (Mainnet)": "https://mainnet.base.org",
    "Base L2 (PublicNode)": "https://base-rpc.publicnode.com",
    "Base L2 (1RPC)": "https://1rpc.io/base",
    "Arbitrum One": "https://arb1.arbitrum.io/rpc",
    "Polygon": "https://polygon-rpc.com",
}

def test_connections():
    print("=" * 70)
    print("          TEST CONNESSIONI BLOCKCHAIN & RPC ENDPOINTS")
    print("=" * 70)
    for name, rpc_url in NETWORKS.items():
        print(f"\n[+] Connessione a {name} ({rpc_url})...")
        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 6}))
            if w3.is_connected():
                chain_id = w3.eth.chain_id
                block_number = w3.eth.block_number
                gas_price_gwei = w3.from_wei(w3.eth.gas_price, "gwei")
                print("    [OK] Connesso!")
                print(f"    - Chain ID:    {chain_id}")
                print(f"    - Ultimo Blocco: #{block_number}")
                print(f"    - Gas Price:   {gas_price_gwei:.4f} Gwei")
            else:
                print("    [!] Connessione fallita (timeout o rifiutata).")
        except Exception as e:
            print(f"    [ERRORE] {e}")
    print("\n" + "=" * 70)

if __name__ == "__main__":
    test_connections()
