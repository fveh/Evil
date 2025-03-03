import os
import logging

def payload_execution(command):
    try:
        os.system(command)
    except Exception as e:
        print(f"[-] Fehler bei der Payload-Ausführung: {e}")
        logging.error("Fehler bei der Ausführung des Payload-Befehls '%s': %s", command, e)
