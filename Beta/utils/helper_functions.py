import logging

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='evil_beta.log',
        filemode='a'
    )
    logging.info("Logging initialisiert.")
