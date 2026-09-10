import sys
from scanner.price_scanner import MultiPairArbitrageScanner

def main():
    try:
        scanner = MultiPairArbitrageScanner()
        scanner.start_continuous_monitoring()
    except Exception as e:
        print(f"\n[ERRORE FATALE] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
