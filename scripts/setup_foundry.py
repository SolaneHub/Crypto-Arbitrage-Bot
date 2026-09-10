import os
import sys
import io
import requests
import zipfile
import subprocess

BIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin")

def install_foundry():
    print("=" * 75)
    print("      DOWNLOAD E INSTALLAZIONE LOCALE DI ANVIL / FOUNDRY (WINDOWS)")
    print("=" * 75)

    anvil_path = os.path.join(BIN_DIR, "anvil.exe")
    if os.path.exists(anvil_path):
        print(f"[+] Anvil è già presente in: {anvil_path}")
        try:
            res = subprocess.run([anvil_path, "--version"], capture_output=True, text=True, check=True)
            print(f"    Versione attiva: {res.stdout.strip()}")
            return True
        except Exception:
            pass

    os.makedirs(BIN_DIR, exist_ok=True)

    # Trova l'asset zip per Windows tramite API di GitHub
    print("[+] Ricerca release ufficiale di Foundry per Windows...")
    r = requests.get("https://api.github.com/repos/foundry-rs/foundry/releases/latest", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    if r.status_code != 200:
        print(f"[!] Errore interrogazione GitHub API: {r.status_code}")
        return False

    download_url = None
    file_name = None
    for asset in r.json().get("assets", []):
        name = asset.get("name", "")
        if "win32_amd64.zip" in name:
            download_url = asset.get("browser_download_url")
            file_name = name
            break

    if not download_url:
        print("[!] Asset Windows non trovato nella release.")
        return False

    print(f"[+] Download di {file_name}...")
    resp = requests.get(download_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    if resp.status_code != 200:
        print(f"[!] Errore nel download: {resp.status_code}")
        return False

    print(f"[+] Download completato ({len(resp.content) / 1024 / 1024:.1f} MB). Estrazione...")
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        for item in z.namelist():
            base = os.path.basename(item)
            if base in ["anvil.exe", "cast.exe", "forge.exe"]:
                print(f"    - Estrazione {base}...")
                with open(os.path.join(BIN_DIR, base), "wb") as f_out:
                    f_out.write(z.read(item))

    print("[+] Estrazione completata con successo in bin/")
    res = subprocess.run([anvil_path, "--version"], capture_output=True, text=True, check=True)
    print(f"[+] Verifica Anvil: {res.stdout.strip()}")
    print("=" * 75)
    return True

if __name__ == "__main__":
    install_foundry()
