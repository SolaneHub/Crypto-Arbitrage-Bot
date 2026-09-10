import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
KILL_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "KILL_SWITCH")

def main():
    if len(sys.argv) < 2 or sys.argv[1].lower() not in ("stop", "pause", "resume", "start", "status"):
        print("Uso:")
        print("  python scripts/kill_switch.py stop    -> Blocca immediatamente ogni operazione del bot (Kill-Switch)")
        print("  python scripts/kill_switch.py resume  -> Rimuove il blocco e riprende le operazioni")
        print("  python scripts/kill_switch.py status  -> Mostra se il Kill-Switch è attivo o disattivo")
        return

    cmd = sys.argv[1].lower()

    if cmd in ("stop", "pause"):
        os.makedirs(os.path.dirname(KILL_FILE), exist_ok=True)
        with open(KILL_FILE, "w", encoding="utf-8") as f:
            f.write("STOP")
        print("🛑 [KILL-SWITCH ATTIVATO] Il file di blocco è stato creato.")
        print("   Il bot non invierà alcuna transazione finché non verrà dato il comando 'resume'.")

    elif cmd in ("resume", "start"):
        if os.path.exists(KILL_FILE):
            os.remove(KILL_FILE)
            print("🟢 [KILL-SWITCH DISATTIVATO] Il file di blocco è stato rimosso.")
            print("   Il bot riprende la scansione e l'operatività normale.")
        else:
            print("ℹ️ Il Kill-Switch era già disattivo (nessun blocco presente).")

    elif cmd == "status":
        if os.path.exists(KILL_FILE):
            print("🛑 STATO: KILL-SWITCH ATTIVO (Il bot è bloccato in sicurezza)")
        else:
            print("🟢 STATO: NORMALE (Operazioni attive e abilitate)")

if __name__ == "__main__":
    main()
