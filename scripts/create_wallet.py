import os
import sys
from eth_account import Account

ENV_PATH = ".env"
ENV_EXAMPLE_PATH = ".env.example"

def create_dedicated_wallet():
    print("=" * 75)
    print("        CREAZIONE WALLET EVM DEDICATO PER CRYPTO ARBITRAGE BOT")
    print("=" * 75)

    if os.path.exists(ENV_PATH):
        print(f"[!] Attenzione: Il file '{ENV_PATH}' esiste già.")
        print("    Per sicurezza, non sovrascriviamo le chiavi esistenti.")
        print("    Se desideri generare un nuovo wallet, rinomina o rimuovi manualmente il file .env.")
        return

    # Abilita funzionalità di entropia non verificata per account.create
    Account.enable_unaudited_hdwallet_features()

    # Genera account crittograficamente sicuro
    acct = Account.create()
    priv_key_hex = acct.key.hex()
    address = acct.address

    # Crea file .env protetto (già presente in .gitignore)
    with open(ENV_PATH, "w") as f:
        f.write("# CONFIGURAZIONE WALLET DEDICATO ARBITRAGE BOT\n")
        f.write("# NOTA: Questo file è strettamente confidenziale e non va condiviso.\n\n")
        f.write(f"WALLET_ADDRESS={address}\n")
        f.write(f"PRIVATE_KEY={priv_key_hex}\n\n")
        f.write("# ENDPOINT RPC (Default pubblici)\n")
        f.write("BASE_MAINNET_RPC=https://mainnet.base.org\n")
        f.write("BASE_SEPOLIA_RPC=https://sepolia.base.org\n")

    # Crea template .env.example pubblico per reference
    if not os.path.exists(ENV_EXAMPLE_PATH):
        with open(ENV_EXAMPLE_PATH, "w") as f:
            f.write("# TEMPLATE CONFIGURAZIONE (Esempio)\n")
            f.write("WALLET_ADDRESS=0x0000000000000000000000000000000000000000\n")
            f.write("PRIVATE_KEY=0x0000000000000000000000000000000000000000000000000000000000000000\n")
            f.write("BASE_MAINNET_RPC=https://mainnet.base.org\n")
            f.write("BASE_SEPOLIA_RPC=https://sepolia.base.org\n")

    print("[+] Nuovo Wallet Generato con Successo!")
    print(f"    - Indirizzo Pubblico: {address}")
    print(f"    - File di configurazione: {ENV_PATH} (protetto da .gitignore)")
    print("-" * 75)
    print("[!] IMPORTANTE: La tua chiave privata è stata salvata solo nel tuo file locale .env.")
    print("    Non comunicarla a nessuno e non caricarla mai su GitHub.")
    print("=" * 75)

if __name__ == "__main__":
    create_dedicated_wallet()
