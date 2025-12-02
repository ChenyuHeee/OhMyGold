"""Helper functions for optional chart generation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd

from .logging import get_logger

logger = get_logger(__name__)


def plot_price_history(history: pd.DataFrame, output_dir: Path, symbol: str) -> Optional[Path]:
    """Render a simple closing price plot and save it to the outputs directory."""

    if history.empty:
        logger.warning("No data available to plot for %s", symbol)
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{symbol.lower()}_close.png"

    plt.figure(figsize=(10, 4))
    plt.plot(history.index, history["Close"], label="Close")
    plt.title(f"{symbol} closing price")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logger.info("Saved price history chart to %s", output_path)
    return output_path
