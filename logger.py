import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Create logs directory
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Log file path
LOG_FILE = os.path.join(LOG_DIR, "wisper.log")


def setup_logger(name="wisper"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # File handler with rotation (5MB max, keep 3 backups)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Format
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger(name="wisper"):
    return logging.getLogger(name)


def log_exception(logger, msg="Unhandled exception"):
    """Log exception with full traceback"""
    logger.exception(msg)


# Global exception handler
def setup_global_exception_handler():
    logger = get_logger("wisper.crash")

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical(
            "CRASH - Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_exception

    # Handle thread exceptions
    import threading
    original_init = threading.Thread.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        original_run = self.run

        def wrapped_run(*args, **kwargs):
            try:
                original_run(*args, **kwargs)
            except Exception:
                logger.exception(f"CRASH in thread {self.name}")

        self.run = wrapped_run

    threading.Thread.__init__ = patched_init
