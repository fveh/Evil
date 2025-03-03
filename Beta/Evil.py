#!/usr/bin/env python3
import argparse
import logging
from modules.core import run_core
from shell_interface import run_shell
from utils.helper_functions import setup_logging

def main():
    setup_logging()  # Initialisiert das Logging
    parser = argparse.ArgumentParser(description="Evil Beta")
    parser.add_argument('--shell', action='store_true', help='Starte den interaktiven Shell-Modus')
    parser.add_argument('target', nargs='?', help='Zielhost für den Netzwerk-Scan')
    args = parser.parse_args()

    if args.shell:
        logging.info("Starte interaktiven Shell-Modus")
        run_shell()
    else:
        if not args.target:
            parser.print_help()
            return
        logging.info("Starte regulären Modus auf Zielhost: %s", args.target)
        run_core(args.target)

if __name__ == '__main__':
    main()
