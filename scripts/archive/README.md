# Scripts Archivio & Riferimenti Storici

Questa cartella conserva gli script utilizzati durante le fasi propedeutiche di test e deploy, mantenuti come documentazione e codice riutilizzabile per il futuro:

1. **`test_sepolia.py`**:
   - Utilizzato nella **Fase 10** per il test su Testnet pubblica Ethereum Sepolia (PoW Faucet, compilazione, firma raw e broadcast).
   - Riferimento per testare nuovi contratti su testnet pubbliche prima della produzione.

2. **`wait_and_deploy.py`**:
   - Utilizzato nella **Fase 13** per monitorare l'arrivo dei fondi tramite bridge da Ethereum L1 a Base L2 ed eseguire il deploy automatico al raggiungimento della soglia.
