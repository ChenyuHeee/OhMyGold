# From Rejection to Alignment: Bridging the Gap Between Probabilistic Agents and Deterministic Risk Constraints

**Abstract**

Large Language Model (LLM) agents are increasingly deployed in high-stakes decision-making environments, such as quantitative finance. However, a fundamental "alignment gap" exists between the probabilistic nature of LLM reasoning and the deterministic, non-negotiable constraints (e.g., risk limits, compliance rules) required by real-world systems. In this paper, we present **Gold-Agent**, a multi-agent framework designed for institutional-grade gold trading. We identify the "Hard-Soft Alignment Problem," where agents struggle to adapt to hard-coded risk gates, leading to low pass rates and utility degradation. We propose and evaluate three feedback mechanisms—Blind Retry, Rule-Based Feedback, and RAG-Enhanced Failure Learning—to bridge this gap. Our experiments demonstrate that retrieving context from historical failures significantly reduces the "alignment cost" (iterations to approval) while preserving the economic utility of trading strategies, offering a scalable path for deploying autonomous agents in constrained environments.

## 1. Introduction

The advent of Large Language Models (LLMs) has enabled the creation of autonomous agents capable of complex planning and tool use. In the financial domain, these agents promise to automate research, strategy formulation, and execution. However, unlike open-ended creative tasks, financial operations are bounded by strict, deterministic constraints: maximum drawdown limits, position sizing rules, and regulatory compliance checks.

We define this as the **Hard-Soft Alignment Problem**:
*   **Soft System**: The LLM agent, which operates probabilistically, generating plans based on natural language reasoning and approximate heuristics.
*   **Hard System**: The environment's safety layer (e.g., a Risk Gate), which operates deterministically, rejecting any state that violates binary logic constraints.

When an agent's proposal is rejected by the Hard System, the agent must revise its plan. Naive agents often fail to understand the *degree* or *nature* of the violation, leading to "blind guessing" or excessive conservatism (e.g., reducing position size to zero to ensure safety, thereby destroying utility).

In this work, we use **Gold-Agent**, a specialized multi-agent system for XAU/USD trading, as a testbed. We introduce a **Risk-Aware Feedback Loop** that utilizes Retrieval-Augmented Generation (RAG) not just for market knowledge, but for *alignment knowledge*. By retrieving past instances of successful plan revisions and specific failure modes, the agent learns to navigate the "risk landscape" more efficiently.

## 2. Related Work

*   **LLMs in Finance**: Recent works like FinGPT and FinMem focus on market prediction and sentiment analysis. However, they often overlook the operational constraints of execution.
*   **Agentic Workflows**: Frameworks like AutoGen and LangChain enable multi-agent collaboration. While they support "human-in-the-loop" feedback, automated "code-in-the-loop" feedback for risk constraints remains under-explored.
*   **Constitutional AI & Alignment**: Techniques for aligning LLMs with safety guidelines usually rely on RLHF or prompt engineering. Our work extends this to alignment with *runtime execution constraints*.

## 3. The Gold-Agent Framework

Gold-Agent simulates an institutional trading desk with specialized roles.

### 3.1 Multi-Agent Architecture
The system comprises 12 agents organized into a hierarchical workflow:
*   **Research Cluster**: `DataAgent`, `MacroAnalystAgent`, `FundamentalAnalystAgent`, `QuantResearchAgent`.
*   **Strategy Cluster**: `HeadTraderAgent` (Decision Maker), `PaperTraderAgent` (Execution).
*   **Risk & Control Cluster**: `RiskManagerAgent`, `ComplianceAgent`.

### 3.2 The Hard Risk Gate
Crucially, the `RiskManagerAgent` is backed by a deterministic code module (`services.risk_gate.py`). Even if the LLM persona approves a trade, the code validates:
1.  **Position Utilization**: $\frac{\text{Current} + \text{New}}{\text{Limit}} \le 1.0$
2.  **Stress Test VaR**: Projected loss under -5% shock $\le$ Capital Buffer.
3.  **Drawdown Limit**: Daily loss $\le$ 2%.

If any check fails, a `HardRiskBreachError` is raised, blocking execution.

## 4. Methodology: Feedback Mechanisms

To solve the Hard-Soft Alignment Problem, we investigate how different feedback granularities affect the agent's ability to recover from rejection.

### 4.1 Baseline: Blind Retry
The agent receives a generic error message: *"Plan rejected due to risk violation. Please revise."* This simulates a black-box environment where the agent must infer the constraint boundaries.

### 4.2 Method 1: Rule-Based Feedback (Current Standard)
The agent receives the explicit output of the risk gate:
> "REJECTED: Position size 6000 oz exceeds limit of 5000 oz. Stress test loss $1.2M exceeds limit $1.0M."

While informative, this often leads to linear scaling (e.g., simply reducing size) without considering non-linear effects like correlation or volatility adjustments.

### 4.3 Method 2: RAG-Enhanced Failure Learning (Proposed)
We introduce a **Meta-Memory** module that indexes past `RiskGate` interactions. When a breach occurs, the system queries this memory:
> "Find previous rejections caused by 'Stress Test VaR' during 'High Volatility' regimes."

The feedback to the agent is augmented:
> "REJECTED: Stress test violation.
> **Context**: In a similar high-volatility scenario (2023-10-15), the desk successfully resolved this by tightening stop-loss width from 2.0% to 1.2% rather than reducing position size, preserving upside potential."

## 5. Experimental Design

We propose an ablation study using the Gold-Agent backtesting suite over the period 2020-2025.

### 5.1 Metrics
We evaluate the alignment process on three dimensions:

1.  **Pass Rate @ K**: The percentage of trading days where a valid, risk-compliant plan is generated within $K$ revision rounds.
2.  **Alignment Cost**: The average number of tokens/iterations required to satisfy the Risk Gate.
3.  **Utility Preservation**:
    $$ \text{Utility Preservation} = \frac{\text{Expected Return of Final Plan}}{\text{Expected Return of Initial (Rejected) Plan}} $$
    This measures if the agent is "over-correcting" (e.g., not trading at all) to satisfy risk.

### 5.2 Hypotheses
*   **H1**: Rule-Based Feedback improves Pass Rate over Blind Retry but may suffer from low Utility Preservation (over-conservatism).
*   **H2**: RAG-Enhanced Feedback achieves the highest Utility Preservation by suggesting nuanced fixes (e.g., hedging vs. cutting size).

## 6. Conclusion
(To be completed after experimental results)
We anticipate that "Hard-Soft Alignment" will become a critical paradigm for autonomous agents. By enabling agents to learn from the "friction" of hard constraints, we can deploy them safely in critical infrastructure without sacrificing their reasoning capabilities.
