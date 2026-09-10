import sys
from scanner.price_scanner import ArbitrageScanner

def main():
    try:
        scanner = ArbitrageScanner()
        scanner.start_monitoring()
    except Exception as e:
        print(f"[ERRORE FATALE] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
