# Crypto Arbitrage Bot -- Base Network (L2)

Bot di arbitraggio on-chain decentralizzato (DEX-to-DEX) ad alta frequenza, progettato per operare su **Base Network (Coinbase L2)** attraverso esecuzione atomica e **Flash Loan (Aave V3 & Balancer V2)** a capitale proprio a rischio zero.

---

## 🏛️ Filosofia & Principi Guida

1. **Zero Memecoin & Alta Liquidità Verificata**:
   - Esclusione categorica di token meme, honeypot o contratti non verificati.
   - Monitoraggio esclusivo di coppie istituzionali con **profondità reale certificata on-chain** (*cbBTC, WETH, wstETH, cbETH, weETH, USDC, EURC, USDT, DAI, AERO, VIRTUAL, tBTC*).
   - Eliminazione totale di pool vuote ("zombie") per azzerare lo slippage.

2. **Esecuzione Atomica (Rischio Capitale Zero)**:
   - I trade utilizzano **Flash Loan** (Aave V3 / Balancer V2): il capitale viene preso in prestito, scambiato su due DEX differenti e rimborsato nello stesso identico blocco (2 secondi).
   - Lo Smart Contract garantisce matematicamente che l'operazione si concluda con profitto netto, altrimenti annulla la transazione (*revert*).

3. **Doppio Scudo Difensivo Pre-Flight (`eth_call`)**:
   - Prima di inviare qualsiasi transazione ai miner e spendere commissioni, il bot effettua una simulazione locale on-chain (`eth_call` in ~50ms).
   - Se le condizioni di mercato cambiano o il profitto non supera le fee, la transazione viene **bloccata a monte**. **Spesa di gas: esattamente 0,00 €**.

4. **Micro-Gas su Base L2**:
   - Grazie ai costi di gas ultra-bassi di Base (~0,0025 € per operazione), una riserva di soli **8 € in ETH copre oltre 3.200 transazioni reali**.

5. **Notifiche Real-Time & Controllo Remoto**:
   - Integrazione nativa con **Discord (Webhook con card a colori)** e Telegram.
   - **Kill-Switch di Emergenza** integrato per mettere in pausa o riprendere le operazioni istantaneamente da riga di comando.

---

## 🔗 Informazioni On-Chain

* **Rete**: Base Mainnet (Chain ID: `8453`)
* **Smart Contract Ufficiale**: [`0x367bA197c9CcE95CE7021FF1ae99479D2E7692E1`](https://basescan.org/address/0x367bA197c9CcE95CE7021FF1ae99479D2E7692E1)
* **DEX Connessi**: Uniswap V3 (`SwapRouter02`) & Aerodrome Finance (Pool V2 dirette)
* **Provider Flash Loan**: Aave V3 Pool (`0xA238Dd80C259a72e81d7e4664a9801593F98d1c5`)

---

## 📁 Struttura della Codebase

```text
Crypto-Arbitrage-Bot/
│
├── main.py                     # Entry point principale del bot (LIVE / PAPER)
├── requirements.txt            # Dipendenze Python (web3, requests, python-dotenv, solcx)
├── README.md                   # Documentazione ufficiale del progetto
├── .env.example                # Modello delle variabili d'ambiente
│
├── config/                     # Configurazioni di sistema
│   └── settings.py             # Provider RPC failover, indirizzi Multicall3, coppie
│
├── contracts/                  # Smart contract di esecuzione atomica
│   ├── AtomicArbitrage.sol     # Contratto Solidity definitivo attivo su Base Mainnet
│   ├── AtomicArbitrage_abi.json# ABI compilata per chiamate e simulazioni web3
│   └── reference/              # Implementazioni e studi architetturali di riferimento
│
├── scanner/                    # Motore di scansione e trading live
│   ├── price_scanner.py        # Loop continuo di scansione, spread netti e Kill-Switch
│   ├── live_trader.py          # Esecutore on-chain live con scudo difensivo eth_call
│   ├── notifier.py             # Notificatore Discord (Webhook) e Telegram
│   ├── multicall.py            # Aggregatore Multicall3 ultra-veloce con failover RPC
│   ├── pools.py                # Decodificatore matematico di pool V2, V3 e Slipstream
│   ├── discovery.py            # Motore per la ricerca e validazione liquidità
│   └── db_logger.py            # Persistenza asincrona su SQLite (market_history.db) e CSV
│
├── simulator/                  # Moduli di simulazione e validazione
│   ├── paper_trader.py         # Motore di paper trading per simulazioni virtuali
│   └── fork_trader.py          # Esecutore on-chain su fork locale Anvil al blocco corrente
│
├── scripts/                    # Strumenti operativi e diagnostici
│   ├── run_live_trader.py      # Esecutore diretto del trading live
│   ├── kill_switch.py          # Kill-Switch di emergenza (stop, resume, status)
│   ├── analyze_data.py         # Report statistico del database e storico opportunità
│   ├── run_paper_backtest.py   # Backtest storico su dati reali archiviati
│   ├── run_fork_trader.py      # Test di validazione con capitale reale su fork Anvil
│   ├── create_wallet.py        # Gestore e diagnostica del portafoglio dedicato
│   ├── deploy_mainnet.py       # Script di deploy e verifica on-chain su Base
│   ├── benchmark_rpc.py        # Benchmark di latenza e stabilità degli RPC
│   ├── test_connection.py      # Verifica connettività e gas price
│   └── archive/                # Script storici propedeutici archiviati per riferimento
│       ├── test_sepolia.py     # Deploy e test eseguiti su Testnet Sepolia (Fase 10)
│       └── wait_and_deploy.py  # Script di attesa bridge e primo deploy (Fase 13)
│
└── data/                       # Dati di runtime (protetti e ignorati da Git)
    ├── 25_pairs_config.json    # Configurazione attiva delle coppie liquide certificate
    ├── market_history.db       # Database SQLite (price ticks, live trades, paper trades)
    ├── live_trading_ledger.csv # Libro mastro delle transazioni live su Base Mainnet
    ├── profitable_opportunities.csv # Archivio opportunità con spread netto positivo
    └── spread_snapshots.csv    # Snapshot continui degli spread di tutte le pool
```

---

## 🚀 Guida Rapida ai Comandi

### 1. Avviare il Trading Live On-Chain
Per avviare il bot in modalità reale (collegato allo Smart Contract su Base Mainnet):
```powershell
python main.py
```
*(Oppure in modalità virtuale senza toccare la blockchain: `python main.py --mode PAPER`)*

### 2. Kill-Switch di Emergenza
Per arrestare o riavviare istantaneamente l'operatività del bot da qualsiasi terminale:
```powershell
python scripts/kill_switch.py stop     # Mette immediatamente in pausa il bot e invia alert su Discord
python scripts/kill_switch.py resume   # Rimuove il blocco e riprende le operazioni normali
python scripts/kill_switch.py status   # Mostra se il blocco è attivo o disattivo
```

### 3. Report e Analisi dei Dati
Per visualizzare le statistiche storiche degli spread e delle opportunità registrate nel database SQLite:
```powershell
python scripts/analyze_data.py
```

### 4. Test su Fork Locale Anvil (a Costo Zero)
Per verificare l'esecuzione dello Smart Contract contro un fork locale di Base Mainnet al blocco corrente:
```powershell
python scripts/run_fork_trader.py
```
