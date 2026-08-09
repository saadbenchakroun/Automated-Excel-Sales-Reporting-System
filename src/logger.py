"""Application logging setup."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.config import Config

_configured: bool = False


def setup_logging(config: Config) -> logging.Logger:
    """Configure the root application logger with console and rotating file handlers.

    Safe to call more than once; only the first call creates handlers.
    """
    global _configured

    level = getattr(logging, str(config.log_level).upper(), logging.INFO)
    logger = logging.getLogger("sales_reporting")
    logger.setLevel(level)
    logger.propagate = False

    if _configured:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.setLevel(level)
    logger.addHandler(console)

    if config.log_folder:
        config.log_folder.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            config.log_folder / config.log_file,
            maxBytes=config.log_max_bytes,
            backupCount=config.log_backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

    _configured = True
    logger.debug("Logging configured: level=%s, log_dir=%s", level, config.log_folder)
    return logger


def reset_logging() -> None:
    """Remove all handlers (used by tests)."""
    global _configured
    logger = logging.getLogger("sales_reporting")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    _configured = False
