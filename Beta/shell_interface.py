import logging
from modules.core import banner
from modules.network import scan_host
from modules.payload import payload_execution

def run_shell():
    print("Interaktiver Shell-Modus gestartet. Tippe 'exit' oder 'quit' zum Beenden.")
    while True:
        try:
            command = input(">> ").strip()
            if command.lower() in ['exit', 'quit']:
                print("Shell beendet.")
                logging.info("Interaktiver Shell-Modus beendet")
                break
            # Befehlsverarbeitung:
            if command.startswith("scan "):
                parts = command.split(maxsplit=1)
                if len(parts) == 2:
                    target = parts[1]
                    print(f"Starte Scan für Host: {target}")
                    scan_host(target)
                else:
                    print("Usage: scan <target>")
            elif command.startswith("payload "):
                parts = command.split(maxsplit=1)
                if len(parts) == 2:
                    cmd = parts[1]
                    print(f"Führe Payload-Befehl aus: {cmd}")
                    payload_execution(cmd)
                else:
                    print("Usage: payload <command>")
            elif command == "banner":
                banner()
            else:
                print("Unbekannter Befehl. Verfügbare Befehle: scan <target>, payload <command>, banner, exit")
        except Exception as e:
            print(f"[-] Fehler: {e}")
            logging.error("Fehler im Shell-Modus: %s", e)
