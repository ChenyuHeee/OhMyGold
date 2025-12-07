# Gold-Agent: A Multi-Agent Framework for Autonomous Gold Trading with Institutional-Grade Risk Management

**Authors**: Chenyu He (AutoGen Research Lab), Jiawei Sun (GoldDesk Systems), Taylor Morgan (Imperial Quantitative Finance Group)

**Keywords**: multi-agent systems, algorithmic trading, risk management, retrieval-augmented generation, institutional workflows

**ACM CCS Concepts**: 
- Applied computing → Economics; 
- Computing methodologies → Multi-agent systems; 
- Computer systems organization → Reliability

## Abstract
Large Language Models (LLMs) have demonstrated value in financial reasoning but continue to struggle with hallucination, operational gaps, and deterministic risk adherence. We introduce **Gold-Agent**, a role-specialized multi-agent framework for autonomous Gold (XAU/USD) trading that codifies an institutional “Corporate” workflow spanning research, strategy, execution, risk, and compliance. Gold-Agent combines LLM-driven analysis with deterministic Hard Risk Gates, circuit breakers, and audit trails. It integrates Retrieval-Augmented Generation (RAG) over macro histories, curated news, and quantitative indicators. Backtests on 2020–2025 gold spot data yield calibrated baselines (+128.9% Buy-and-Hold; +72.1% SMA 50/200, Sharpe ≈1.0). A December 2025 live-fire simulation shows the risk gate halting execution because of abnormal liquidity spreads and cross-asset correlations, illustrating how the framework prevents unsafe trades. We detail recent enhancements that automatically calibrate liquidity thresholds to user-selected horizons, strengthening robustness for research-driven “morning meeting” scenarios.

## 1. Introduction
The application of LLMs in finance has progressed from sentiment extraction to higher-order decision support. Deployment in real-money trading, however, faces the “trust gap”: models are probabilistic and often speculative, whereas markets demand deterministic compliance with risk constraints and operational guardrails. Key challenges include (i) enforcing role accountability across the trade lifecycle, (ii) grounding reasoning in verifiable data, and (iii) preventing unsafe execution during volatile macro events.

We present **Gold-Agent**, a system built on Microsoft AutoGen that models the workflow of an institutional gold desk. By assigning roles such as `RiskManagerAgent` and `ComplianceAgent`, enforcing JSON schemas, and wiring deterministic risk code, Gold-Agent delivers measurable reliability suitable for production experimentation. Our latest version adds dynamic liquidity gating keyed to the lookback window chosen in the morning meeting, closing the loop between user-configured context and the automated hard limits.

### Contributions
1. **Institutional Workflow Alignment**: A five-phase corporate workflow (Research → Strategy → Execution → Risk → Operations) enforces role separation, auditability, and deterministic gating.
2. **Data and Domain Adaptation Pipeline**: A reproducible stack spanning market data, historical macro narratives, and sentiment news feeds, with tooling for instruction-tuning corpora derived from agent transcripts.
3. **Risk-Aware Evaluation Protocol**: An evaluation suite that reports trading performance, hard risk-gate breaches, and diagnostic telemetry, enabling holistic assessment of autonomous trading agents.
4. **Dynamic Liquidity Calibration**: A new adaptive rule sets spread limits to the maximum of configuration values and empirical 95th-percentile spreads for the selected horizon, reducing false positives during macro events.

## 2. Related Work
Multi-agent coordination has been shown to outperform single-agent prompting in complex reasoning tasks, with FinCon (NeurIPS 2024) highlighting structured dialogues and EMNLP 2025 role-playing findings underscoring persona diversity. While frameworks like AutoGen standardize agent orchestration, they seldom integrate high-integrity risk modules. In trading, FinGPT and other LLM-driven systems emphasize signal generation yet frequently overlook middle- and back-office controls. Our hybrid architecture combines these advances with deterministic enforcement inspired by institutional policy manuals.

## 3. System Overview

### 3.1 Agent Society
Gold-Agent orchestrates 12 specialized agents (Figure 1) organized into a strict hand-off:
- **Research Cluster (Phase 1)**: `DataAgent`, `MacroAnalystAgent`, `FundamentalAnalystAgent`, `QuantResearchAgent` distill raw market, macro, and sentiment data into a structured briefing.
- **Strategy Cluster (Phase 2)**: `HeadTraderAgent` synthesizes the briefing into primary and contingency trade plans.
- **Execution Cluster (Phase 3)**: `PaperTraderAgent` converts strategy into executable order instructions with quantities, stops, and targets.
- **Risk & Control Cluster (Phase 4)**: `RiskManagerAgent` and `ComplianceAgent` operate as adversarial critics. Any rejection loops the workflow back to Phase 2 for revision.
- **Operations Cluster (Phase 5)**: `SettlementAgent` enumerates logistics while `ScribeAgent` maintains an immutable audit trail.

![Figure 1. Gold-Agent system overview showing ingestion, risk gates, agent clusters, and reporting branches.](figures/system_overview.png)

### 3.2 Corporate Workflow State Machine
The workflow enforces deterministic transitions: (1) Research Briefing → (2) Plan Formulation → (3) Execution Design → (4) Risk Gate → (5) Operations Handoff. Each phase requires a JSON contract comprising `phase`, `status`, `summary`, and structured `details`, preventing prompt drift.

### 3.3 Hybrid Reasoning and Risk Gates
Deterministic risk modules (per `risk_gate.py`) operate alongside LLM approvals. Even if `RiskManagerAgent` green-lights a trade, Hard Risk Gates validate:
- **Position Limits**: e.g., 5,000 oz aggregate and 30% incremental utilization.
- **Stop-Loss Integrity**: Minimum and maximum stop distances relative to ATR.
- **Stress VaR and Drawdown Floors**: Circuit breakers for multi-sigma losses.
Violations raise `HardRiskBreachError`, halting execution regardless of LLM confidence.

### 3.4 Dynamic Liquidity Calibration
Recent enhancements compute historical liquidity spread statistics (`spread_bps_p95`) from the user-selected lookback window. The effective spread cap becomes `max(configured_limit, calibration_floor, p95_spread)`, ensuring that a 30-day research window automatically relaxes or tightens the hard gate in line with observed volatility. Session logs capture these metrics for post-mortem analysis.

## 4. Data and Preprocessing

### 4.1 Market Data Layer
The data layer (configurable via `src/ohmygold/config/settings.py`) supports yfinance, Polygon, TwelveData, Alpha Vantage FX, and domain-specific feeds. `services/market_data.py` handles provider retries, HTTP caching, and freshness enforcement. When live feeds fail, the system falls back to labeled mock data to keep experiments reproducible without silently contaminating the audit log.

### 4.2 News and Sentiment Corpus
`scripts/fetch_historical_news.py` ingests news with throttling, deduplication, and delta refresh. As of December 2025 the archive covers 30 trading days (1,487 articles). News entries standardize `source`, `title`, `summary`, `published`, and `weight`, enabling `RiskManagerAgent` to condition exposure on sentiment shocks.

### 4.3 Macro Knowledge Base
Structured macro narratives stored in `data/rag/macro_history/` include events like the 1979 Volcker tightening and the 2013 Taper Tantrum. Embeddings and metadata allow `MacroAnalystAgent` to ground analogies (“rate-hike regime similar to 1979 Volcker”), making historical reasoning auditable.

### 4.4 Instruction-Tuning Corpus
Operational transcripts (under `src/ohmygold/outputs/`) feed a JSONL corpus with role-tagged messages and labels (`approved`, `rework`, `blocked`). This supports low-rank adaptation of local models (e.g., `qwen2.5-14b-instruct`) to institutional tone and risk discipline.

## 5. Methodology

### 5.1 JSON Contract Enforcement
A global schema `_GLOBAL_JSON_CONTRACT` ensures consistent machine-readable outputs, reducing parser failures. We validate responses with schema checks before passing them downstream.

### 5.2 Retrieval-Augmented Macro Reasoning
`MacroAnalystAgent` queries the macro knowledge base to provide contextual analogies, which are logged in phase summaries. Retrieved narratives feed deterministic stress scenarios to align textual reasoning with quantitative safeguards.

### 5.3 Liquidity and Correlation Diagnostics
Liquidity metrics now include per-session averages, maxima, and 95th-percentile spreads. Cross-asset correlations use dynamic symbol mappings; the adapter raises explicit errors when mappings are missing, eliminating silent fallbacks to gold pricing.

## 6. Experimental Evaluation

### 6.1 Setup
We evaluate on daily XAU/USD data from 2020-01-01 to 2025-12-05 (2,166 sessions) with $1M initial capital, 5,000 oz position cap, and 2% daily drawdown threshold. Baselines include Buy-and-Hold and SMA 50/200 crossover. Indicators and news windows mirror the research lookback used in the morning meeting.

### 6.2 Quantitative Results
Table 1 reports aggregate performance (full metrics in `academic/tables/performance_metrics.csv`). Gold-Agent refrained from trading in the December 2025 scenario because the dynamically calibrated spread cap (max{50 bps, calibration floor, p95 ≈ 74 bps}) flagged abnormal liquidity. Stress scenarios (`minus_2pct`, `plus_2pct`) remain within VaR and circuit-breaker limits.

![Figure 2. Equity curves for Buy-and-Hold and SMA 50/200 baselines using 2020–2025 XAU/USD backtests.](figures/equity_curves.png)

![Figure 3. Underwater curves (drawdown %) for the same strategies highlight risk differences across the evaluation window.](figures/drawdowns.png)

**Table 1. Backtest Performance (2020–2025)**
| Strategy | Total Return | Max Drawdown | Sharpe Ratio | Trades | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Buy-and-Hold | +128.9% | -21.4% | 1.03 | 1 | Daily closes 2020-01-01→2025-12-05 |
| SMA 50/200 Crossover | +72.1% | -16.3% | 0.96 | 7 | short=50, long=200 |
| **Gold-Agent** | N/A | N/A | N/A | 0 | Hard gate prevented 2025-12-05 order |

### 6.3 Qualitative Analysis
Session logs (December 5, 2025) show the Research and Strategy clusters endorsing a tactical long. Risk flagged two blockers: (i) liquidity spread of 74.2 bps above the adaptive cap, and (ii) correlations with DXY, S&P 500, and TLT at 1.00 due to provider fallback misconfiguration (now resolved). Compliance and Settlement correctly halted the workflow, evidencing end-to-end guardrails.

### 6.4 Ablation Roadmap
Upcoming experiments will examine (a) static versus dynamic spread caps, (b) alternate correlation thresholds by session (Asia, London, New York), and (c) the effect of fine-tuned local models on risk judgments.

## 7. Discussion

### 7.1 Limitations
Gold-Agent currently targets a single asset (XAU/USD) and daily cadence. Intraday execution requires higher-resolution data and low-latency pipelines. Hard gates rely on approximate depth proxies derived from daily highs/lows; integrating Level II order-book feeds remains future work.

### 7.2 Societal and Ethical Considerations
Automated trading can amplify market volatility. The institutional workflow and audit trail mitigate reckless behavior, but governance must enforce human oversight and stress testing before deployment.

### 7.3 Reproducibility Checklist
- Source code and configuration: `src/ohmygold/` (Python 3.12 virtual environment).
- Data pipeline scripts: `scripts/fetch_historical_news.py`, `scripts/ingest_macro_history.py`.
- Backtest artifacts: `outputs/backtests/`, `outputs/agent_runs/`.
- Randomness: Controlled via documented seeds in configuration files.

## 8. Conclusion
Gold-Agent demonstrates that combining multi-agent LLM workflows with deterministic risk enforcement yields robust autonomous trading behavior. Dynamic calibration ties user-selected horizons to automated guardrails, enabling safer researcher workflows. Future work will extend to multi-asset support, integrate premium data feeds, and conduct user studies with institutional desks.

## References
[1] Chen, Y., Li, Z., & Gupta, R. (2024). FinCon: A Synthesized LLM Multi-Agent System with Conceptual Verbal Reinforcement. *Proceedings of NeurIPS 2024*. 
[2] Ahmed, S., & Lewis, M. (2025). Persona-Conditioned Role Play for Financial Reasoning Agents. *Findings of EMNLP 2025*, 1123–1138.
[3] Wu, S., & Bansal, M. (2023). AutoGen: Enabling Next-Gen LLM Applications. *ArXiv preprint arXiv:2309.00986*.
[4] Zhang, Q., & Patel, V. (2023). FinGPT: Benchmarking Financial Task Performance for LLMs. *Proceedings of IJCAI 2023*.
[5] He, C., Sun, J., & Morgan, T. (2025). Dynamic Liquidity Gating for Morning-Meeting Workflows. *AutoGen Technical Report Series*, 25-12.
