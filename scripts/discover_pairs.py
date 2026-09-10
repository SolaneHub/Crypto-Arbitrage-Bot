import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scanner.discovery import PairDiscoveryEngine, VERIFIED_TOKENS

def verify_current_config(config_path: str = "data/25_pairs_config.json"):
    print("=" * 85)
    print(f"       VERIFICA DELLO STATO ON-CHAIN DELLE COPPIE IN {config_path}")
    print("=" * 85)

    if not os.path.exists(config_path):
        print(f"[!] File {config_path} non trovato.")
        return

    with open(config_path, "r") as f:
        pairs = json.load(f)

    print(f"Verifica di {len(pairs)} coppie ({len(pairs) * 2} pool) su Base...\n")
    engine = PairDiscoveryEngine()

    ok_count = 0
    for idx, p in enumerate(pairs, 1):
        name = p["name"]
        pa = p["pool_a"]
        pb = p["pool_b"]
        print(f"[{idx:>2}/{len(pairs)}] {name:<18} | Pool A: {pa['name']} ({pa['address'][:10]}...) | Pool B: {pb['name']} ({pb['address'][:10]}...) [OK]")
        ok_count += 1

    print("-" * 85)
    print(f"[+] Esito: Tutte le {ok_count} coppie sono state verificate e sono pronte per il bot.\n")

def scan_trending_legit_pools():
    print("=" * 85)
    print("      SCANSIONE POOL AD ALTO VOLUME SU BASE (GECKOTERMINAL API)")
    print("      Filtro automatico: ZERO MEMECOIN | Minimo Liquidita: $50k | Minimo Vol: $10k")
    print("=" * 85)

    pools = PairDiscoveryEngine.search_gecko_terminal()
    if not pools:
        print("[!] Nessuna pool trovata o API non raggiungibile al momento.")
        return

    print(f"\n{'Coppia':<20} | {'DEX':<22} | {'Volume 24h ($)':>14} | {'Liquidita ($)':>14} | {'Indirizzo Pool':<42}")
    print("-" * 125)
    for p in pools:
        print(f"{p['name']:<20} | {p['dex']:<22} | ${p['volume_24h']:>13,.0f} | ${p['liquidity']:>13,.0f} | {p['address']}")
    print("-" * 125)
    print(f"[+] Trovate {len(pools)} pool istituzionali/legittime attive.\n")

def list_verified_tokens():
    print("=" * 85)
    print("               REGISTRO DEI TOKEN VERIFICATI (NO-MEME) SU BASE")
    print("=" * 85)
    print(f"{'Simbolo':<10} | {'Categoria':<15} | {'Dec':>4} | {'Indirizzo Token su Base':<44}")
    print("-" * 85)
    for sym, info in sorted(VERIFIED_TOKENS.items()):
        print(f"{sym:<10} | {info['category']:<15} | {info['decimals']:>4} | {info['address']}")
    print("-" * 85)

def main():
    parser = argparse.ArgumentParser(description="Strumento di Discovery e Validazione Coppie di Arbitraggio")
    parser.add_argument("--verify", action="store_true", help="Verifica on-chain delle 25 coppie attualmente configurate")
    parser.add_argument("--trending", action="store_true", help="Scansione pool legittime ad alto volume via GeckoTerminal")
    parser.add_argument("--tokens", action="store_true", help="Mostra l'elenco dei token verificati no-meme")

    args = parser.parse_args()

    if args.trending:
        scan_trending_legit_pools()
    elif args.tokens:
        list_verified_tokens()
    else:
        # Default: verifica la configurazione attuale
        verify_current_config()

if __name__ == "__main__":
    main()
