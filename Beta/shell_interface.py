import logging

def run_shell():
    print("Interaktiver Shell-Modus gestartet. Gib 'exit' oder 'quit' ein, um zu beenden.")
    while True:
        try:
            command = input(">> ")
            if command.lower() in ['exit', 'quit']:
                print("Shell beendet.")
                logging.info("Interaktiver Shell-Modus beendet.")
                break
            # === BEGIN Shell-Befehlsverarbeitung ===
            # Hier kannst du Befehle parsen und die entsprechenden Funktionen aus den Modulen aufrufen.
            print(f"Befehl ausgeführt: {command}")
            logging.info(f"Shell-Befehl: {command}")
            # === ENDE Shell-Befehlsverarbeitung ===
        except Exception as e:
            print(f"Fehler: {e}")
            logging.error(f"Fehler im Shell-Modus: {e}")
