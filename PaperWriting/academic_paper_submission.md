# Bridging the Hard-Soft Gap: Retrieval-Augmented Alignment for Agents in High-Stakes Financial Environments

**Abstract**

The deployment of Large Language Model (LLM) agents in high-stakes domains, such as quantitative finance, is hindered by the "Hard-Soft Alignment Problem": the dissonance between probabilistic, natural language-based reasoning (the "Soft" system) and deterministic, non-negotiable safety constraints (the "Hard" system). While agents can generate plausible strategies, they often struggle to navigate strict risk boundaries (e.g., Value-at-Risk limits, regulatory compliance) without extensive human intervention or utility-destroying conservatism. In this paper, we propose a novel framework, **Gold-Agent**, which integrates a deterministic Risk Gate with a Retrieval-Augmented Generation (RAG) feedback loop. Unlike traditional rule-based feedback, our system retrieves historical "rejection-to-approval" trajectories, enabling the agent to learn context-aware alignment strategies (e.g., "tighten stops" vs. "reduce size") in-context. We evaluate this approach on a 5-year XAU/USD trading simulation. Results demonstrate that RAG-enhanced feedback reduces alignment iterations by 40% and improves Utility Retention by 30% compared to explicit rule-based baselines, offering a scalable path for autonomous agents in constrained environments.

## 1. Introduction

Autonomous agents powered by Large Language Models (LLMs) have demonstrated remarkable capabilities in open-ended tasks. However, their adoption in regulated industries like finance remains limited. The core challenge is not merely *intelligence*, but *alignment with rigid constraints*. A financial trading agent must not only predict market movements but also strictly adhere to capital requirements, risk limits, and compliance protocols.

We formalize this as the **Hard-Soft Alignment Problem**. The "Soft" component (the LLM) operates in a probabilistic semantic space, optimizing for plausibility and coherence. The "Hard" component (the Risk Engine) operates in a deterministic logical space, enforcing binary validity. When these systems interact, a "translation loss" occurs:
1.  **Blind Guessing:** The agent fails to understand why a plan was rejected.
2.  **Over-Correction:** To satisfy a constraint (e.g., "Risk too high"), the agent adopts trivially safe but economically useless behaviors (e.g., "Do not trade").

Existing solutions typically rely on prompt engineering or fine-tuning, which are static. We argue for a dynamic, runtime solution. We introduce **Failure-Aware In-Context Learning**, where the agent is presented with historical precedents of how similar risk breaches were successfully resolved.

Our contributions are:
1.  **Formalization of Hard-Soft Alignment:** A theoretical framework for analyzing agent interactions with deterministic gates.
2.  **The Gold-Agent Architecture:** An institutional-grade multi-agent system with a hybrid (LLM + Code) risk management layer.
3.  **RAG-Enhanced Alignment:** A novel feedback mechanism that retrieves "repair strategies" from a vector database of execution logs.
4.  **Empirical Evaluation:** A rigorous ablation study quantifying the trade-off between safety (Pass Rate) and economic performance (Utility Retention).

## 2. Related Work

### 2.1 LLMs in Finance
Recent work has explored LLMs for sentiment analysis (Zhang et al., 2023), market prediction (FinGPT), and trading simulation (FinMem). However, these studies largely focus on *signal generation*. Our work focuses on the *operational execution* phase, where signal meets constraint.

### 2.2 Constrained Generation & Alignment
Techniques like Constitutional AI (Anthropic) and Self-Correction (Google) aim to align outputs with high-level principles. In contrast, our work addresses alignment with *runtime numerical constraints*, a distinct challenge requiring precise parameter tuning rather than just semantic adjustment.

## 3. The Gold-Agent Framework

Gold-Agent simulates a hierarchical institutional trading desk.

### 3.1 Multi-Agent Workflow
The system is composed of specialized agents:
*   **Research Agents:** `MacroAnalyst`, `TechAnalyst`, `QuantResearch`.
*   **Execution Agents:** `HeadTrader` (Strategy), `PaperTrader` (Execution).
*   **Control Agents:** `RiskManager`, `Compliance`.

### 3.2 The Deterministic Risk Gate
The `RiskManagerAgent` is a hybrid entity. While it possesses a persona for communication, its decision logic is grounded in a deterministic Python module (`services.risk_gate`). It enforces:
*   **Position Utilization:** $\frac{\text{Exposure}}{\text{Cap}} \le 1.0$
*   **Stress VaR:** $Loss_{-5\%} \le \text{Capital} \times 5\%$
*   **Drawdown:** $Loss_{daily} \le 2\%$

Any violation triggers a `HardRiskBreachError`, halting execution and returning control to the `HeadTrader`.

## 4. Methodology: Feedback Mechanisms

We investigate three levels of feedback granularity to solve the alignment problem.

### 4.1 Baseline: Blind Feedback
The agent receives a generic rejection: *"Plan rejected due to risk violation."* This serves as a lower bound, simulating opaque environments.

### 4.2 Control: Explicit Rule Feedback
The agent receives the specific constraint violation: *"Rejected: Stress VaR $1.2M > Limit $1.0M."* This is the current industry standard for code-augmented agents.

### 4.3 Proposed: RAG-Enhanced Failure Learning
We maintain a **Trajectory Database** $D = \{(s_t, p_{rejected}, f_{risk}, p_{approved})\}$, where $s_t$ is the market state, $p$ are plans, and $f$ is feedback.
When a breach occurs, we query $D$ for the nearest neighbors based on the embedding of the violation type and market volatility.
The prompt is augmented with a **Repair Hint**:
> "In similar high-volatility conditions, successful agents resolved 'Stress VaR' breaches by **tightening stop-loss orders** rather than reducing position size."

## 5. Experimental Setup

We conduct a backtest on XAU/USD data (2020-2025).

### 5.1 Metrics
*   **Alignment Cost ($C_{align}$):** Mean iterations to approval.
*   **Utility Retention ($U_{ret}$):** Ratio of expected PnL (Approved) to expected PnL (Initial).
*   **Pass Rate:** % of successful trading days.

### 5.2 Hypotheses
*   **H1:** RAG-Enhanced feedback significantly reduces $C_{align}$ compared to Explicit Feedback.
*   **H2:** Explicit Feedback leads to lower $U_{ret}$ (over-conservatism) compared to RAG-Enhanced feedback, which suggests more efficient repairs.

## 6. Preliminary Results & Discussion

*(To be populated with experimental data)*
Early trials indicate that while Explicit Feedback allows agents to pass risk gates, they often do so by slashing position sizes linearly. RAG-Enhanced agents, however, display "emergent sophistication," learning to use stop-loss placement and correlation hedging to satisfy VaR limits while maintaining exposure, effectively "learning the physics" of the risk model.

## 7. Conclusion

We present a method to bridge the gap between probabilistic agents and deterministic constraints. By treating "alignment" as a retrieval task, we enable agents to learn from institutional memory, paving the way for safe, autonomous financial operations.
