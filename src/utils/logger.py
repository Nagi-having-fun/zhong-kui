import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path


def setup_logger(config: dict) -> logging.Logger:
    logger = logging.getLogger("content_filter")
    logger.setLevel(getattr(logging, config.get("level", "INFO")))

    # Detailed format with milliseconds for tracing timing
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
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
        logger.info(f"Log file: {log_file}")

    return logger


async def log_sleep(seconds: float, reason: str):
    """Sleep with logging so user can trace every wait."""
    logger = logging.getLogger("content_filter")
    logger.info(f"[SLEEP] Waiting {seconds:.1f}s — {reason}")
    await asyncio.sleep(seconds)
    logger.debug(f"[SLEEP] Resumed after {seconds:.1f}s")


class ActionTracer:
    """Context manager that logs the start, duration, and result of an action."""

    def __init__(self, action_name: str):
        self.action_name = action_name
        self.logger = logging.getLogger("content_filter")
        self.start_time = None

    def __enter__(self):
        self.start_time = time.monotonic()
        self.logger.info(f"[START] {self.action_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.monotonic() - self.start_time
        if exc_type:
            self.logger.warning(f"[FAIL]  {self.action_name} — {exc_val} ({elapsed:.1f}s)")
        else:
            self.logger.info(f"[DONE]  {self.action_name} ({elapsed:.1f}s)")
        return False
