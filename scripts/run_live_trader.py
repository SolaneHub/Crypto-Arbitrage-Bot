import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner.price_scanner import MultiPairArbitrageScanner

def run():
    print("=" * 95)
    print("           AVVIO DEL MOTORE DI ARBITRAGGIO LIVE ON-CHAIN SU BASE MAINNET")
    print("=" * 95)
    scanner = MultiPairArbitrageScanner(mode="LIVE")
    scanner.start_continuous_monitoring()

if __name__ == "__main__":
    run()
