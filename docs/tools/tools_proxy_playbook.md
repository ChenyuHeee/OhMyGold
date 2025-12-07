# ToolsProxy Playbook for Analysts

The ToolsProxy agent lets LLM analysts run deterministic Python helpers during the gold morning call. Use the following patterns to keep outputs auditable and to plug RAG plus risk math directly into the JSON reply.

## 1. Preparing the proxy message

When a research agent wants to enrich its draft, it should insert a message such as:

```
@ToolsProxy run
from ohmygold.tools import data_tools, compute_risk_profile
from ohmygold.tools.rag import RagConfig, RagService
from pathlib import Path

# 1) Pull current market snapshot
snapshot = data_tools.get_gold_market_snapshot(symbol="GC=F")

# 2) Query historical precedents
config = RagConfig(index_root=Path("data/rag-index"))
rag = RagService(config)
result = rag.query(
    "Episodes where the Fed tightened policy quickly and gold reacted",
    top_k=3,
)

# 3) Compute extra risk diagnostics leveraging deterministic helpers
risk_profile = compute_risk_profile(symbol="GC=F", days=90)
correlation = None
if risk_profile["cross_asset_correlations"]:
    correlation = risk_profile["cross_asset_correlations"][0]["value"]

print({
    "market": snapshot,
    "historical_references": result.metadata,
    "rag_top_passages": result.passages,
    "risk_note": {
        "annualised_vol": snapshot["atr"]["annualised_vol"],
        "rolling_correlation": correlation,
        "portfolio_var_millions": risk_profile["portfolio_var_millions"],
        "risk_alerts": risk_profile["risk_alerts"],
    },
})
```

The proxy captures stdout and returns JSON that the agent can embed into `details`. Always perform `print()` on a dictionary so downstream roles can parse the response cleanly.

## 2. Recommended response structure

- Set `phase` and `status` first (`"Phase 1"`, `"IN_PROGRESS"` while gathering data, then `"COMPLETE"`).
- Add `details.market_snapshot` from the ToolsProxy call.
- Map `details.historical_references` to `result.metadata`, each item containing `event`, `year`, `category`, and `source`.
- Include `details.rag_quotes` with the top passages (short excerpts only).
- Forward `details.risk_check` containing the supplemental metrics your team will care about（如最新滚动相关系数、组合 VaR、`risk_alerts` 列表等）。
- Always hand off by setting `details.next_agent` (e.g. `"TechAnalystAgent"`).

## 3. Keeping the index warm

Before the trading session, run:

```
python scripts/ingest_macro_history.py --index-root data/rag-index
```

This command loads the curated corpora under `data/rag/macro_history` and `data/rag/trading_playbook` into the local vector store so queries resolve immediately during the meeting. Re-run the script whenever you add new macro case studies or trading playbooks.

By following these conventions the research agents can cite past regimes, surface structured metrics, and keep the JSON handshake intact for downstream risk and compliance review.
