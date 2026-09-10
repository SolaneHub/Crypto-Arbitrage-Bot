import sys
import os
import argparse
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
load_dotenv()

from scanner.price_scanner import MultiPairArbitrageScanner

def main():
    parser = argparse.ArgumentParser(description="Arbitrage Bot su Base Network L2")
    parser.add_argument(
        "--mode",
        choices=["LIVE", "PAPER"],
        default=os.getenv("EXECUTION_MODE", "LIVE"),
        help="Modalità di esecuzione: LIVE (trading on-chain su Base Mainnet) o PAPER (simulazione locale)"
    )
    args = parser.parse_args()

    try:
        scanner = MultiPairArbitrageScanner(mode=args.mode)
        scanner.start_continuous_monitoring()
    except Exception as e:
        print(f"\n[ERRORE FATALE] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
