"""CLI entry point for running the gold outlook workflow."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

from .config.settings import get_settings
from .services.news_watcher import run_default_watcher
from .services.risk_gate import HardRiskBreachError
from .utils.logging import configure_logging, get_logger
from .workflows.gold_outlook import run_gold_outlook

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the workflow."""

    parser = argparse.ArgumentParser(description="Run the AutoGen gold outlook workflow.")
    parser.add_argument("--symbol", default=None, help="Symbol or ticker to analyze (default from settings)")
    parser.add_argument("--days", type=int, default=None, help="Lookback window in days (default from settings)")
    parser.add_argument("--raw", action="store_true", help="Print raw JSON response instead of formatted text")
    parser.add_argument(
        "--output-file",
        help="Optional path to write the final workflow report; defaults to timestamped file under outputs/",
    )
    parser.add_argument("--watch-news", action="store_true", help="Start the asynchronous news watcher")
    return parser.parse_args()


def _determine_output_path(symbol: str, explicit: str | None) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    default_output = (
        Path(__file__).resolve().parent / "outputs" / f"gold_outlook_{symbol}_{timestamp}.json"
    )
    output_path = Path(explicit).expanduser() if explicit else default_output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def _json_default(value: Any) -> Any:
    if hasattr(value, "to_dict") and callable(getattr(value, "to_dict")):
        try:
            return value.to_dict()
        except Exception:  # pragma: no cover - defensive
            pass
    if hasattr(value, "dict") and callable(getattr(value, "dict")):
        try:
            return value.dict()
        except Exception:  # pragma: no cover - defensive
            pass
    if hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
        try:
            return value.model_dump()
        except Exception:  # pragma: no cover - defensive
            pass
    if hasattr(value, "__dict__"):
        return {key: val for key, val in value.__dict__.items() if not key.startswith("_")}
    return repr(value)


def _safe_json_dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, default=_json_default)


def main() -> None:
    """Bootstrap application settings and execute the workflow."""

    args = parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)

    symbol = args.symbol or settings.default_symbol
    days = args.days or settings.default_days

    if args.watch_news:
        asyncio.run(run_default_watcher())
        return

    logger.info("启动工作流：标的=%s，回溯=%d天", symbol, days)
    try:
        result: Dict[str, Any] = run_gold_outlook(symbol=symbol, days=days, settings=settings)
    except HardRiskBreachError as exc:
        logger.error("硬风控约束触发，流程终止：%s", exc)
        result = exc.partial_result or {}
        result["hard_risk_gate"] = exc.report.to_dict()
        output_path = _determine_output_path(symbol, args.output_file)
        output_path.write_text(_safe_json_dumps(result) + "\n", encoding="utf-8")
        logger.info("硬风控报告已写入：%s", output_path)
        if args.raw:
            print(_safe_json_dumps(result))
        else:
            print(exc.report.summary())
        raise SystemExit(2) from exc

    parsed_response = result.get("response_parsed")
    final_payload: Any = parsed_response if parsed_response is not None else result.get("response")

    output_path = _determine_output_path(symbol, args.output_file)

    if isinstance(final_payload, str):
        try:
            parsed = json.loads(final_payload)
        except json.JSONDecodeError:
            serialized = final_payload
        else:
            serialized = json.dumps(parsed, indent=2)
    else:
        serialized = _safe_json_dumps(final_payload)
    output_path.write_text(serialized + "\n", encoding="utf-8")
    logger.info("工作流输出已写入：%s", output_path)

    if args.raw:
        print(_safe_json_dumps(result))
    else:
        print(result.get("response"))


if __name__ == "__main__":
    main()
