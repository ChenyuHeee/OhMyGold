# AutoGen Gold Trading System Upgrade Roadmap

## 0. Background
- Context: the current workflow mirrors a trading-desk morning meeting but behaves like a demo.
- Trigger: veteran trader feedback highlights missing historical reasoning, mathematical risk checks, executable quant research, and event-aware sentiment handling.
- Objective: evolve the system into a production-ready decision co-pilot while preserving existing multi-agent flow.

## 1. Guiding Principles
- Preserve the five-phase collaboration model; extend rather than replace it.
- Prefer additive feature flags and layered services so experimental modules can be toggled.
- Keep all outputs machine-parseable JSON; new insights must fit into structured schemas.
- Couple every new capability with observability (logging, metrics, or artifacts such as charts).

## 2. Phase Breakdown

### Phase 0 – Discovery and Baseline (in progress)
- Catalogue current agent prompts, tool access, and data sources.
- Draft detailed requirements derived from veteran feedback.
- Evaluate infrastructure choices (vector store, code sandbox, NLP models, intraday market feeds).
- Deliverables: this roadmap, dependency matrix, and updated configuration defaults.

### Phase 1 – Financial Brain & Data Plumbing
- Stand up a Retrieval-Augmented Generation (RAG) service backed by macro history and trading playbooks.
- Extend Data/Macro/Fundamental/Quant agents to call the RAG lookup tool and report cited precedents.
- Harden data ingestion: add live intraday feed adapters, enhance caching, and standardize sentiment payloads.
- Deliverables: `tools/rag` package, ingestion scripts, enriched context payload (with provenance fields).

### Phase 2 – Quant & Risk Math Enrichment
- Introduce reusable analytics utilities (rolling correlations, scenario analysis, simple VaR) for agents.
- Refactor RiskManagerAgent prompt to require quantified metrics and ComplianceAgent to run executable checks.
- Expand QuantResearchAgent and TechAnalystAgent to execute Python snippets (code execution guardrails in place).
- Deliverables: `services/risk_math.py`, quant helper library, sample notebooks/artifacts saved under `outputs/`.

### Phase 3 – Backtesting & Operational Hardening
- Build a backtest harness that replays historical windows through the multi-agent workflow.
- Add regression tests and CI hooks to ensure JSON contract and key metrics stay intact.
- Document deployment options, including switching between cloud and local models, and roll-out guidance.
- Deliverables: `backtesting/` module, automated test suite extensions, operations manual updates.

## 3. Immediate Sprint Goals (Week 1)
- Finalize requirements inventory (assign owners, effort, dependencies).
- Prototype RAG ingestion using a small macro dataset (e.g., last 24 FOMC statements and gold reactions).
- Design the risk analytics API surface (function signatures, return schema) and capture in ADR or design doc.
- Enable code execution for QuantResearchAgent in `.env`, validate sandbox timeout settings.
- Align JSON schemas: add fields for historical references, risk metrics, and visualization artifacts.

## 4. Dependencies & Risks
- **Data Licensing**: confirm usage rights for macro/market archives before large-scale ingestion.
- **Model Latency**: remote LLM calls can stall the workflow; keep local fallbacks and timeout handling.
- **Security**: executing agent code demands strict sandboxing, resource limits, and audit logging.
- **Team Capacity**: schedule phase transitions once earlier deliverables are demonstrably stable.

## 5. Metrics & Validation
- RAG coverage: percentage of macro events ingested vs target corpus.
- Risk accuracy: difference between agent-computed VaR and benchmark calculation.
- Execution fidelity: number of workflows completing all five phases without manual intervention.
- Backtest confidence: Sharpe ratio and drawdown of sample strategies before and after enhancements.

## 6. Next Steps Checklist
- [ ] Populate requirement inventory sheet in `docs/requirements/` (to be created).
- [ ] Spin up vector store prototype and log index statistics.
- [ ] Draft risk analytics function stubs (see `services/risk_math.py`).
- [ ] Update agent prompts to reference new tools once stubs are stable.
- [ ] Schedule review with veteran advisor after Phase 1 prototype demo.
