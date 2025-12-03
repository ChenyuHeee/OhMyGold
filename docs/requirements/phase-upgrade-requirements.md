# Phase Upgrade Requirements Inventory

| ID | Theme | Description | Owner | Dependencies | Target Phase |
|----|-------|-------------|-------|--------------|--------------|
| RAG-01 | Financial Brain | Collect macro history (FOMC, CPI, geopolitical events) into structured JSON/Markdown corpus ready for embedding. | TBD | Data licensing confirmation | Phase 1 |
| RAG-02 | Financial Brain | Implement vector-store ingestion pipeline (`scripts/ingest_macro_history.py`) that chunks documents and persists embeddings. | TBD | RAG-01 | Phase 1 |
| RAG-03 | Financial Brain | Expose `rag.query_macro_context(question)` helper for agents; include citation list in JSON outputs. | TBD | RAG-02 | Phase 1 |
| DATA-01 | Data Plumbing | Add intraday data adapter for secondary provider (e.g., Polygon or AlphaVantage). | TBD | Provider credentials | Phase 1 |
| DATA-02 | Data Plumbing | Harmonize sentiment payload schema (score, confidence, topics, source). | TBD | Existing news pipeline | Phase 1 |
| RISK-01 | Risk Math | Extend risk snapshot with historical VaR, rolling correlations, scenario shocks computed via `services.risk_math`. | TBD | `risk_math` utilities | Phase 2 |
| RISK-02 | Risk Math | Update RiskManagerAgent to surface new metrics and mitigation guidance. | TBD | RISK-01 | Phase 2 |
| RISK-03 | Risk Math | Write automated tests validating risk metrics against hand-calculated benchmarks. | TBD | RISK-01 | Phase 2 |
| QUANT-01 | Quant Sandbox | Enable safe Python execution for QuantResearchAgent and TechAnalystAgent with timeouts. | Copilot | Sandbox configuration | Phase 2 |
| QUANT-02 | Quant Sandbox | Provide helper library for charting and factor analysis (resides in `tools/quant_helpers.py`). | Copilot | QUANT-01 | Phase 2 |
| BACK-01 | Backtesting | Design backtest harness to replay workflow steps over historical windows. | TBD | Phase 1 data ingestion | Phase 3 |
| BACK-02 | Backtesting | Integrate CI smoke tests ensuring multi-agent flow completes under sample scenario. | TBD | BACK-01 | Phase 3 |
| OPS-01 | Ops Hardening | Document deployment scenarios, feature flags, and rollback procedures. | TBD | All above | Phase 3 |

## Notes
- Owners to be assigned during sprint planning; placeholder `TBD` until team availability confirmed.
- Each requirement should have accompanying acceptance criteria logged in the issue tracker.
- Any new external data must pass compliance review before ingestion.
