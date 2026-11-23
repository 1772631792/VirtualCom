from __future__ import annotations

import logging
import os
from pathlib import Path

from .constants import APP_NAME, LOG_FILE


def log_directory() -> Path:
    base = os.getenv("APPDATA")
    path = Path(base) / APP_NAME if base else Path.home() / f".{APP_NAME.lower()}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_logging() -> logging.Logger:
    logger = logging.getLogger(APP_NAME.lower())
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    try:
        file_handler = logging.FileHandler(log_directory() / LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        pass

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logger.addHandler(stream)
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(APP_NAME.lower())
