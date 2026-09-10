import time
import sys
import os
from web3 import Web3

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.deploy_mainnet import deploy_to_base_mainnet

def wait_and_deploy():
    w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
    addr = '0x6CC40498af8882A714265c57292a524f50EE9280'

    print("=" * 80)
    print("      IN ATTESA DELL'ACCREDITO DEL BRIDGE SU BASE MAINNET...")
    print(f"      Wallet: {addr}")
    print("=" * 80)

    start_time = time.time()
    for attempt in range(1, 35):
        try:
            bal_wei = w3.eth.get_balance(addr)
            bal_eth = w3.from_wei(bal_wei, 'ether')
            elapsed = int(time.time() - start_time)
            print(f"[{time.strftime('%H:%M:%S')}] Tentativo #{attempt} ({elapsed}s): Saldo Base = {bal_eth:.6f} ETH")
            
            if bal_wei >= w3.to_wei(0.0005, 'ether'):
                print("\n" + "#" * 80)
                print(">>> FONDI RICEVUTI CON SUCCESSO SU BASE MAINNET! <<<")
                print("#" * 80 + "\n")
                deploy_to_base_mainnet()
                return
        except Exception as e:
            print(f"Errore connessione: {e}")

        time.sleep(8)

    print("[!] Timeout: controlla l'explorer di Base tra qualche minuto.")

if __name__ == "__main__":
    wait_and_deploy()
