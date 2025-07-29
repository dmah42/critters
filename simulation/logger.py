import logging
import sys


def setup_logging(console_log_enabled=True, log_filename="simulation.log"):
    """
    Configures the root logger to output to both the console and a file.

    Args:
      console_log_enabled (bool): If True, logs will be printed to the console.
      log_filename (str): The name of the file to which to save logs.
    """
    # Define the format for the log messages
    log_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"
    )

    # Get the root logger
    logger = logging.getLogger()
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(logging.INFO)  # Set the minimum level of messages to log

    if console_log_enabled:
        # --- Console Handler ---
        # This handler prints logs to your terminal
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)

    if log_filename:
        # --- File Handler ---
        # This handler writes logs to a file named 'simulation.log'
        # 'w' mode overwrites the file each time; use 'a' to append.
        file_handler = logging.FileHandler(log_filename, mode="w")
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)

    print(f"Logging configured: Console {console_log_enabled}. File {log_filename}")
