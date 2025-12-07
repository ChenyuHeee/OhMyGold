"""Helper functions for optional chart generation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import matplotlib.pyplot as plt
import pandas as pd

from .logging import get_logger

logger = get_logger(__name__)


def plot_price_history(history: pd.DataFrame, output_dir: Path, symbol: str) -> Optional[Path]:
    """Render a simple closing price plot and save it to the outputs directory."""

    if history.empty:
        logger.warning("绘图数据为空：%s", symbol)
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
    logger.info("价格曲线已保存：%s", output_path)
    return output_path


def plot_volatility_cone(
    history: pd.DataFrame,
    output_dir: Path,
    symbol: str,
    windows: Sequence[int] | None = None,
    quantiles: Sequence[float] | None = None,
) -> Optional[Path]:
    """Render a realized volatility cone chart highlighting percentile bands."""

    if history.empty:
        logger.warning("绘制波动率锥失败（行情为空）：%s", symbol)
        return None

    returns = history["Close"].pct_change().dropna()
    if returns.empty:
        logger.warning("缺少有效收益率序列，无法绘制波动率锥：%s", symbol)
        return None

    windows = tuple(sorted(set(windows or (5, 10, 20, 60, 120))))
    quantiles = tuple(quantiles or (0.1, 0.5, 0.9))

    stats: dict[int, dict[float, float]] = {}
    latest_vals: dict[int, float] = {}

    for window in windows:
        if window <= 1 or len(returns) < window:
            continue
        window_vol = returns.rolling(window).std().dropna() * (252 ** 0.5)
        if window_vol.empty:
            continue
        stats[window] = {q: float(window_vol.quantile(q)) for q in quantiles}
        latest_vals[window] = float(window_vol.iloc[-1])

    if not stats:
        logger.warning("无法生成波动率锥，窗口无有效统计：%s", symbol)
        return None

    effective_windows = sorted(stats.keys())
    labels = [f"{window}d" for window in effective_windows]

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{symbol.lower()}_volatility_cone.png"

    plt.figure(figsize=(10, 6))
    for index, quantile in enumerate(quantiles):
        values = [stats[window].get(quantile) for window in effective_windows]
        plt.plot(labels, values, marker="o", label=f"q{int(quantile * 100)}")

    current_values = [latest_vals.get(window) for window in effective_windows]
    plt.plot(labels, current_values, marker="s", linestyle="--", color="#d62728", label="Latest")

    plt.title(f"{symbol} Volatility Cone")
    plt.ylabel("Annualised Volatility")
    plt.xlabel("Lookback Window")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logger.info("波动率锥已保存：%s", output_path)
    return output_path
