# ArbitrageAgent 原型规划

目标：在 Phase 1 研究阶段提供跨品种价差/对冲机会，聚焦金银比与相关金属 ETF。该 Agent 暂不直接下单，而是生成策略建议供 HeadTrader 评估。

## 角色定位
- **名称**：ArbitrageAgent
- **性格**：理性套利者，偏好统计套利与对冲结构，强调执行纪律。
- **触发阶段**：Phase 1，建议在 QuantResearchAgent 之后执行，向 HeadTrader 提供备选方案。

## 数据依赖
1. `ohmygold.tools.quant_helpers.get_gold_silver_ratio()`：返回金银比序列（UTC 时间戳、ratio、rolling z-score）。
2. `ohmygold.tools.data_tools.get_gold_market_snapshot()`：获取金价、波动率、交易量。
3. `services.market_data.fetch_price_history()`：必要时拉取 GLD/SLV、XAUUSD/XAGUSD 替换数据。
4. 未来扩展：铂金/钯金、铜与黄金的交叉指标。

## 提示词要点
- 明确要求输出 JSON：
  ```json
  {
    "phase": "Phase 1 - Research Briefing",
    "status": "IN_PROGRESS|COMPLETE|BLOCKED",
    "summary": "Arbitrage headline",
    "details": {
      "spread_signals": [{"name": str, "value": number|null, "zscore": number|null, "bias": "long_gold|long_silver|neutral"}],
      "hedge_weights": [{"leg": str, "weight": number, "rationale": str}],
      "entry_band": [number, number],
      "risk_controls": [str],
      "historical_hit_rate": {"window": str, "win_rate": number|null},
      "data_sources": ["tool_name"],
      "missing_inputs": [str],
      "next_agent": "HeadTraderAgent"
    }
  }
  ```
- 要求引用 UTC 时间并注明所用滑点假设。
- 强调需检查金银比的 H4 突破是否与 D1 偏离共振；若无信号立刻 `status='BLOCKED'` 并解释。

## 工程实现步骤
1. **Agent 工厂**：在 `agents/arbitrage_agent.py` 内实现 `create_arbitrage_agent`，复用现有 `create_llm_agent`。
2. **Supervisor 编排**：在 `workflows/gold_outlook.py` 插入 ArbitrageAgent（可配置开关）。
3. **ToolsProxy 扩展**：提供 `get_gold_silver_ratio_summary`，返回最新 z-score、均值、标准差。
4. **测试**：新增 `tests/test_arbitrage_agent_prompt.py`（快照测试 JSON Schema）与工具层单测。
5. **文档**：在 README“智能体编制”章节补充角色说明。

## 今日可执行动作
- 确认 quant_helpers 对 UTC 时间戳的支持（已完成）。
- 草拟提示词（见上）并开 Issue 落实开发顺序。
- 标记需要的配置项：`arbitrage_enabled`, `arbitrage_spread_threshold` 等。
