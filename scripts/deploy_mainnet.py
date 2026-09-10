import os
import sys
import solcx
from dotenv import load_dotenv
from web3 import Web3

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

BASE_MAINNET_RPC = os.getenv("BASE_MAINNET_RPC", "https://mainnet.base.org")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CHAIN_ID = 8453  # Base Mainnet

def deploy_to_base_mainnet():
    print("=" * 90)
    print("      FASE 13 -- DEPLOY SMART CONTRACT SU BASE MAINNET UFFICIALE (CHAIN ID: 8453)")
    print("      AtomicArbitrage.sol con supporto Flash Loan (Aave V3 & Balancer V2)")
    print("=" * 90)

    w3 = Web3(Web3.HTTPProvider(BASE_MAINNET_RPC, request_kwargs={"timeout": 15}))
    if not w3.is_connected():
        print(f"[!] Impossibile connettersi all'RPC di Base Mainnet: {BASE_MAINNET_RPC}")
        return

    curr_block = w3.eth.block_number
    gas_price_wei = w3.eth.gas_price
    gas_price_gwei = w3.from_wei(gas_price_wei, "gwei")

    print(f"\n[1/3] Stato della Rete Base Mainnet:")
    print(f"      - Connessione RPC:   [OK] {BASE_MAINNET_RPC}")
    print(f"      - Blocco Corrente:   #{curr_block:,}")
    print(f"      - Gas Price Attuale: {gas_price_gwei:.4f} Gwei (ultra-economico)")

    if not WALLET_ADDRESS or not PRIVATE_KEY:
        print("[!] Credenziali del wallet non trovate nel file .env.")
        return

    bal_wei = w3.eth.get_balance(WALLET_ADDRESS)
    bal_eth = w3.from_wei(bal_wei, "ether")
    eth_usd_est = 2465.0
    bal_eur_est = (float(bal_eth) * eth_usd_est) / 1.085

    print(f"\n[2/3] Stato del Tuo Wallet Dedicato:")
    print(f"      - Indirizzo Pubblico: {WALLET_ADDRESS}")
    print(f"      - Saldo Attuale:      {bal_eth:.6f} ETH (~{bal_eur_est:.2f} €)")
    print(f"      - Explorer Ufficiale: https://basescan.org/address/{WALLET_ADDRESS}")

    min_required_eth = 0.0003  # Circa 0.70 € per coprire abbondantemente il deploy (~0.20 €)
    if bal_eth < min_required_eth:
        print("\n" + "!" * 90)
        print("  [AZIONE RICHIESTA] Il wallet ha bisogno di una frazione di ETH per pagare il deploy.")
        print("  Il costo del deploy su Base Mainnet è di appena ~0,20 € (venti centesimi).")
        print("")
        print("  Come finanziare il wallet con un micro-versamento (5 € o 10 €):")
        print("  1. Dal tuo account exchange (Coinbase, Kraken, Binance, Bybit, Revolut, ecc.):")
        print("     - Scegli 'Preleva / Invia ETH'")
        print(f"     - Indirizzo di destinazione: {WALLET_ADDRESS}")
        print("     - IMPORTANTE: Seleziona come Rete di prelievo 'Base' (Base L2), NON Ethereum!")
        print("     - Importo consigliato: 5 € - 10 € (circa 0.002 - 0.004 ETH)")
        print("")
        print("  La transazione su Base arriva in appena 2-5 secondi.")
        print("  Non appena hai inviato, rilancia questo script per eseguire il deploy automatico!")
        print("!" * 90)
        return

    print("\n[3/3] Saldo verificato! Compilazione e Deploy on-chain di AtomicArbitrage.sol...")
    compiled = solcx.compile_files(["contracts/AtomicArbitrage.sol"], solc_version="0.8.21")
    data = compiled["contracts/AtomicArbitrage.sol:AtomicArbitrage"]
    abi = data["abi"]
    bytecode = data["bin"]

    nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)
    contract_factory = w3.eth.contract(abi=abi, bytecode=bytecode)

    # Costo gas stimato (~1.800.000 gas * 0.006 Gwei = ~$0.02 - $0.20)
    construct_txn = contract_factory.constructor().build_transaction({
        "from": WALLET_ADDRESS,
        "nonce": nonce,
        "gas": 3000000,
        "gasPrice": int(gas_price_wei * 1.2),  # +20% buffer per inclusione istantanea
        "chainId": CHAIN_ID
    })

    signed_txn = w3.eth.account.sign_transaction(construct_txn, private_key=PRIVATE_KEY)
    print(f"[DEPLOY] Invio transazione a Base Mainnet...")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"      -> Tx Hash: {tx_hash.hex()}")
    print(f"      -> In attesa dell'inclusione nel blocco (~2 secondi)...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    actual_gas_cost_usd = (receipt.gasUsed * receipt.effectiveGasPrice / 1e18) * eth_usd_est
    actual_gas_cost_eur = actual_gas_cost_usd / 1.085

    print("\n" + "=" * 90)
    print("      🎉 [SUCCESSO] SMART CONTRACT UFFICIALE DEPLOYATO SU BASE MAINNET!")
    print("=" * 90)
    print(f"  Indirizzo Contratto:  {receipt.contractAddress}")
    print(f"  Incluso nel Blocco:   #{receipt.blockNumber:,}")
    print(f"  Gas Utilizzato:       {receipt.gasUsed:,} unità")
    print(f"  Costo Reale Deploy:   {actual_gas_cost_eur:.4f} € (~${actual_gas_cost_usd:.4f} USD)")
    print(f"  Transazione Basescan: https://basescan.org/tx/{tx_hash.hex()}")
    print(f"  Contratto Basescan:   https://basescan.org/address/{receipt.contractAddress}")
    print("=" * 90)

    # Salva l'indirizzo del contratto nel file .env
    _update_env_contract(receipt.contractAddress)

def _update_env_contract(address: str):
    env_file = ".env"
    lines = []
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

    found = False
    new_lines = []
    for line in lines:
        if line.startswith("ATOMIC_ARBITRAGE_ADDRESS="):
            new_lines.append(f"ATOMIC_ARBITRAGE_ADDRESS={address}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"\n# Smart Contract Ufficiale Deployato su Base Mainnet\nATOMIC_ARBITRAGE_ADDRESS={address}\n")

    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"  [OK] Indirizzo salvato in .env: ATOMIC_ARBITRAGE_ADDRESS={address}")

if __name__ == "__main__":
    deploy_to_base_mainnet()
