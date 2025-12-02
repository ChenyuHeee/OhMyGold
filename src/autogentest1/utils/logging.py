"""Logging configuration utilities."""

from __future__ import annotations

import logging
from typing import Optional


def configure_logging(level_name: str = "INFO") -> None:
    """Configure root logging with a simple console formatter."""

    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a module-level logger, configuring defaults on first use."""

    logger = logging.getLogger(name)
    if not logging.getLogger().handlers:
        configure_logging()
    return logger
