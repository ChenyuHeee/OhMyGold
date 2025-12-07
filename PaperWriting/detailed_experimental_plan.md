# Experimental Design: The Hard-Soft Alignment Study

## 1. Research Objective
To empirically investigate how different feedback mechanisms influence the ability of Large Language Model (LLM) agents to align with deterministic "hard" constraints in a high-stakes financial environment. Specifically, we aim to solve the "Alignment Cost" problem, where agents waste computational resources or degrade strategy utility when trying to satisfy safety rules they do not fully comprehend.

## 2. Experimental Setup

### 2.1 The Environment (The "Hard" System)
We utilize the **Gold-Agent** backtesting framework operating on XAU/USD daily data.
*   **Time Period:** Jan 1, 2020 – Dec 31, 2024 (In-sample), Jan 1, 2025 – Dec 31, 2025 (Out-of-sample).
*   **Hard Constraints (The "Risk Gate"):**
    1.  **Position Limit:** Max 5,000 oz.
    2.  **Drawdown Limit:** Max 2.0% daily loss.
    3.  **Stress Test VaR:** Max $1.0M loss under a -5% price shock scenario.
    4.  **Stop-Loss Requirement:** Every trade must have a valid stop-loss order.

### 2.2 The Agent (The "Soft" System)
*   **Model:** `gpt-4-turbo` (or `deepseek-chat` as configured) acting as the `HeadTraderAgent` and `PaperTraderAgent`.
*   **Task:** Generate a trading plan (Buy/Sell, Size, Stop-Loss) based on market data.

## 3. Independent Variables: Feedback Mechanisms

We will run three distinct backtest passes, varying only the information returned by the `RiskManagerAgent` when a `HardRiskBreachError` occurs.

#### Condition A: Blind Feedback (Baseline)
*   **Mechanism:** The agent receives a binary rejection signal.
*   **Prompt Injection:** *"The trading plan was REJECTED by the Risk Engine. It violates one or more internal safety limits. Please revise the plan to reduce risk."*
*   **Hypothesis:** Agents will struggle to converge, likely resorting to "zeroing out" positions to guarantee safety, resulting in near-zero utility.

#### Condition B: Explicit Rule Feedback (Current State)
*   **Mechanism:** The agent receives the exact error message from the deterministic code.
*   **Prompt Injection:** *"REJECTED. Violation details: [1] Stress Test Loss ($1.2M) exceeds limit ($1.0M). [2] Position Size (6,000 oz) exceeds limit (5,000 oz)."*
*   **Hypothesis:** Agents will fix the immediate numbers (e.g., set size to 4,999 oz) but may fail to account for second-order effects (e.g., volatility correlation), leading to multiple iterations or suboptimal strategy adjustments.

#### Condition C: RAG-Enhanced Failure Learning (Proposed Method)
*   **Mechanism:** The system retrieves the top-3 most similar historical "rejection-then-approval" trajectories from a vector database of prior runs.
*   **Prompt Injection:**
    > "REJECTED. Violation: Stress Test Loss ($1.2M) > Limit ($1.0M).
    > **Alignment Hint:** In similar high-volatility conditions (e.g., 2022-03-14), successful plans achieved compliance by **tightening the stop-loss distance** rather than reducing position size. See example:
    > *   *Rejected Plan:* Size 4000, Stop -3.0% -> Stress Loss $1.5M
    > *   *Approved Revision:* Size 4000, Stop -1.5% -> Stress Loss $0.8M"
*   **Hypothesis:** Agents will adopt more sophisticated risk mitigation strategies (e.g., hedging, tightening stops) rather than just cutting size, preserving higher economic utility.

## 4. Dependent Variables (Metrics)

### 4.1 Alignment Efficiency
*   **Iterations to Approval ($N_{iter}$):** Average number of dialogue turns required to pass the Risk Gate.
*   **Pass Rate ($R_{pass}$):** Percentage of days where a valid plan is produced within 5 iterations.

### 4.2 Utility Preservation
*   **Utility Retention Ratio ($U_{ret}$):**
    $$ U_{ret} = \frac{\text{Projected PnL of Final Approved Plan}}{\text{Projected PnL of Initial (Rejected) Plan}} $$
    *   $U_{ret} \approx 1.0$: Ideal alignment (risk reduced without sacrificing return).
    *   $U_{ret} \ll 1.0$: Over-correction (agent killed the trade to be safe).

### 4.3 Economic Performance
*   **Cumulative Return:** Total PnL over the backtest period.
*   **Sharpe Ratio:** Risk-adjusted return.

## 5. Implementation Plan

### Step 1: Data Preparation (The "Memory Bank")
1.  Run a "Warm-up" backtest using Condition B (Explicit Feedback) for 2020-2023.
2.  Log all `(Rejected_Plan, Risk_Feedback, Approved_Plan)` tuples.
3.  Vectorize the `Risk_Feedback` and market context (Volatility, Trend) to create the RAG index.

### Step 2: Code Modification
1.  Modify `src/ohmygold/agents/risk_agent.py`:
    *   Add `feedback_mode` argument to `create_risk_manager_agent`.
    *   In `Condition A`, strip `details` from the JSON response.
    *   In `Condition C`, call `tools.rag.query_risk_memory(current_violation)` and append to `details`.

### Step 3: Execution
1.  Run `scripts/run_experiment.py --mode blind --start-date 2024-01-01`
2.  Run `scripts/run_experiment.py --mode explicit --start-date 2024-01-01`
3.  Run `scripts/run_experiment.py --mode rag --start-date 2024-01-01`

### Step 4: Analysis
1.  Parse `outputs/agent_runs/*.json`.
2.  Compute $N_{iter}$, $R_{pass}$, and $U_{ret}$ for each mode.
3.  Generate comparative plots (Box plot of Iterations, Line chart of Equity Curves).

## 6. Expected Results (for the Paper)

We expect to show that **Condition C (RAG)**:
1.  Reduces iterations by ~40% compared to Condition B.
2.  Increases Utility Retention from ~0.6 (Condition B) to ~0.9 (Condition C).
3.  Demonstrates "Emergent Alignment": The agent learns to use hedging instruments (if available) or tighter stops instead of brute-force size reduction.
