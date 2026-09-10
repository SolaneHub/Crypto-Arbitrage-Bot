import os
import sys
import time
import solcx
from dotenv import load_dotenv
from web3 import Web3

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

BASE_SEPOLIA_RPC = os.getenv("BASE_SEPOLIA_RPC", "https://sepolia.base.org")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CHAIN_ID = 84532

def check_or_deploy_sepolia(deploy: bool = False):
    print("=" * 85)
    print("      FASE 10 -- TESTNET BASE SEPOLIA (CHAIN ID: 84532)")
    print("      Verifica Connessione, Saldo Testnet e Deploy On-Chain")
    print("=" * 85)

    w3 = Web3(Web3.HTTPProvider(BASE_SEPOLIA_RPC, request_kwargs={"timeout": 15}))
    if not w3.is_connected():
        print(f"[!] Impossibile connettersi all'RPC di Base Sepolia: {BASE_SEPOLIA_RPC}")
        return

    curr_block = w3.eth.block_number
    gas_price_gwei = w3.from_wei(w3.eth.gas_price, "gwei")

    print(f"\n[1/3] Stato della Rete Base Sepolia:")
    print(f"      - Connessione RPC: [OK] {BASE_SEPOLIA_RPC}")
    print(f"      - Blocco Corrente: #{curr_block:,}")
    print(f"      - Gas Price Attuale: {gas_price_gwei:.4f} Gwei")

    if not WALLET_ADDRESS or not PRIVATE_KEY:
        print("[!] Credenziali del wallet non trovate nel file .env.")
        return

    bal_wei = w3.eth.get_balance(WALLET_ADDRESS)
    bal_eth = w3.from_wei(bal_wei, "ether")

    print(f"\n[2/3] Stato del Wallet Dedicato:")
    print(f"      - Indirizzo Pubblico: {WALLET_ADDRESS}")
    print(f"      - Saldo Sepolia ETH:  {bal_eth:.6f} ETH (Testnet gratuita)")
    print(f"      - Explorer:           https://sepolia.basescan.org/address/{WALLET_ADDRESS}")

    if bal_eth == 0:
        print("\n" + "!" * 85)
        print("  [ATTENZIONE] Il wallet non ha ancora ETH di prova su Base Sepolia.")
        print("  Per eseguire transazioni e deployare lo Smart Contract su testnet,")
        print("  è sufficiente richiedere gratuitamente una frazione di ETH da uno di questi faucet:")
        print("")
        print("  1. QuickNode Faucet:    https://faucet.quicknode.com/base/sepolia")
        print("  2. Superchain Faucet:   https://console.optimism.io/faucet")
        print("  3. Alchemy Faucet:      https://www.alchemy.com/faucets/base-sepolia")
        print("  4. BwareLabs Faucet:    https://bwarelabs.com/faucets/base-sepolia")
        print("  5. Chainlink Faucet:    https://faucets.chain.link/base-sepolia")
        print("")
        print(f"  Basta incollare il tuo indirizzo: {WALLET_ADDRESS}")
        print("!" * 85)
        return

    print("\n[3/3] Il wallet ha fondi sufficienti per le operazioni di testnet!")
    
    if not deploy:
        print("      Per procedere con il Deploy dello Smart Contract 'AtomicArbitrage.sol',")
        print("      esegui il comando: python scripts/test_sepolia.py --deploy")
        return

    print("\n[DEPLOY] Compilazione di contracts/AtomicArbitrage.sol...")
    compiled = solcx.compile_files(["contracts/AtomicArbitrage.sol"], solc_version="0.8.21")
    data = compiled["contracts/AtomicArbitrage.sol:AtomicArbitrage"]
    abi = data["abi"]
    bytecode = data["bin"]

    print("[DEPLOY] Creazione e firma della transazione di Deploy con chiave privata...")
    nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)
    contract_factory = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    construct_txn = contract_factory.constructor().build_transaction({
        "from": WALLET_ADDRESS,
        "nonce": nonce,
        "gas": 3000000,
        "gasPrice": w3.eth.gas_price,
        "chainId": CHAIN_ID
    })

    signed_txn = w3.eth.account.sign_transaction(construct_txn, private_key=PRIVATE_KEY)
    print(f"[DEPLOY] Invio transazione alla rete Base Sepolia...")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"      -> Tx Hash: {tx_hash.hex()}")
    print(f"      -> In attesa della conferma nel blocco (~2-4 secondi)...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    print("\n" + "=" * 85)
    print("      [CONFERMATO] SMART CONTRACT DEPLOYATO CON SUCCESSO SU BASE SEPOLIA!")
    print("=" * 85)
    print(f"  Indirizzo Contratto:  {receipt.contractAddress}")
    print(f"  Incluso nel Blocco:   #{receipt.blockNumber}")
    print(f"  Gas Consumato:        {receipt.gasUsed:,} unità")
    print(f"  Transazione Explorer: https://sepolia.basescan.org/tx/{tx_hash.hex()}")
    print(f"  Contratto Explorer:   https://sepolia.basescan.org/address/{receipt.contractAddress}")
    print("=" * 85)

if __name__ == "__main__":
    is_deploy = ("--deploy" in sys.argv)
    check_or_deploy_sepolia(deploy=is_deploy)
