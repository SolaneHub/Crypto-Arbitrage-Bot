# Smart Contracts di Riferimento per Arbitraggio Flash Loan

Questi due contratti Solidity servono da archivio e base di studio per la **Fase 11** del progetto.

---

### 1. `OptimizedArbitrage.sol` (ex codice1.cs)
* **Approccio:** Massima efficienza del gas (Low-level).
* **Meccanismo:**
  * Richiede un Flash Loan ad Aave V3.
  * Invia i token direttamente alla prima coppia DEX (`pair1`).
  * Chiama `IUniswapV2Pair.swap()`, indirizzando l'output direttamente alla seconda coppia (`pair2`).
  * La seconda coppia effettua lo swap e restituisce i fondi al contratto.
  * Rimborsa il debito ad Aave e trasferisce il profitto direttamente al proprietario (`owner`).
* **Punti di Forza:**
  * Consumo di gas ridotto al minimo indispensabile (zero scritture su storage, nessun passaggio dai router).
  * Velocità d'esecuzione elevata.
* **Punti Critici:**
  * Nessuna whitelist su token o router.
  * I calcoli esatti (`amount0Out`, `amount1Out`) devono essere precalcolati con precisione assoluta dal bot off-chain; una minima variazione di riserva nel blocco causa il revert.

---

### 2. `ArbitrageInterface.sol` (ex codice2.cs)
* **Approccio:** Massima sicurezza e robustezza (Defensive / High-level).
* **Meccanismo:**
  * Flash Loan Aave V3 con validazione rigorosa dell'hash della strategia (`activePlanHash`).
  * Utilizza i Router DEX ufficiali (`IRouterV2Like.swapExactTokensForTokens`) con parametri di slippage (`amountOutMin`) e scadenza temporale (`deadline`).
  * Utilizza una libreria interna (`TokenOps`) per gestire in modo sicuro token non standard (come USDT) che non restituiscono un valore booleano standard nei transfer/approve.
  * Include meccanismi di pausa (`paused`), whitelist per router e token, e funzione di emergenza `sweepToken`.
* **Punti di Forza:**
  * Protezione totale da attacchi di reentrancy, chiamate contraffatte e perdite da slippage imprevisto.
* **Punti Critici:**
  * Costo del gas notevolmente superiore a causa dei passaggi multipli attraverso i contratti Router e delle scritture di stato/storage.

---

### Obiettivo per la Fase 11
Creare il nostro contratto personalizzato fondendo:
* Il routing diretto pair-to-pair e la leggerezza di `OptimizedArbitrage.sol`
* I controlli di sicurezza, whitelist e gestione sicura ERC20 di `ArbitrageInterface.sol`.
