"""Logging configuration utilities."""

from __future__ import annotations

import logging
from typing import Optional

_LEVEL_TRANSLATIONS = {
    logging.DEBUG: "调试",
    logging.INFO: "信息",
    logging.WARNING: "警示",
    logging.ERROR: "错误",
    logging.CRITICAL: "致命",
}


def configure_logging(level_name: str = "INFO") -> None:
    """Configure root logging with a simple console formatter."""

    for level, translated in _LEVEL_TRANSLATIONS.items():
        logging.addLevelName(level, translated)

    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )

    # Reduce noise from third-party libraries that spam verbose logs.
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a module-level logger, configuring defaults on first use."""

    logger = logging.getLogger(name)
    if not logging.getLogger().handlers:
        configure_logging()
    return logger
