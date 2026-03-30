import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logger(config: dict) -> logging.Logger:
    logger = logging.getLogger("content_filter")
    logger.setLevel(getattr(logging, config.get("level", "INFO")))

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if config.get("log_to_file", True):
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"filter_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
