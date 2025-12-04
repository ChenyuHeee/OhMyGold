# 2025-12-04 工作待办（黄金量化）

## 早盘优先事项
- [x] 梳理 `autogentest1/services/market_data.py` 与 `autogentest1/tools/data_tools.py` 的调用链，输出当前行情/宏观数据来源图，标记依赖 `yfinance` 的薄弱点。
- [x] 起草 `DataSourceAdapter` 设计草图：定义实时（WebSocket）与批量（REST）接口方法、缓存策略以及回测数据切换钩子。
- [x] 收集 IBKR / Polygon.io / FRED / TradingEconomics 订阅方案与认证流程，列出今日内可启动的接入动作（账号、API Key、沙箱环境）。

## 行情与工具一致性强化
- [x] 将 `tools/data_tools.py` 中的金银比、宏观快照工具切换为统一调用 `fetch_price_history`，提供 `XAUUSD/XAGUSD → GC=F/SI=F → GLD/SLV` 的降级链并写入 `tests/test_data_tools.py`。
- [x] 配置 TwelveData / Polygon symbol map，确保 `XAUUSD/XAGUSD/GC=F/SI=F/DXY/TIP` 均能直接命中，无需多级降级。
- [x] 为统一行情接口补充使用说明（README / runbook），提醒使用者不要再自行引用 `yfinance`。
- [x] 消除 `datetime.utcnow()` Deprecation Warning（替换为 `datetime.now(datetime.UTC)`），避免测试输出噪音。

## 风控硬约束落地
- [x] 阅读 `autogentest1/workflows/gold_outlook.py` 运行链路，现于 `services/risk_gate.py` 注入硬风控拦截，并在 CLI 层处理 `HardRiskBreachError`。
- [x] 罗列并落实硬编码指标（仓位利用率、单笔敞口、止损覆盖、压力损失、当日回撤、相关性），以 `tests/test_risk_gate.py` 验证可复用 `risk_math.py` 输出。
- [x] 输出一版风控闸门触发流程图（事件 → 校验 → 拒单/平仓 → 通知链路），同步给合规/风控代理提示词更新。

## 策略与知识库强化
- [x] 审查 Phase 1 相关智能体提示词（`agents/macro_agent.py`, `agents/tech_agent.py`, `agents/quant_agent.py`），标记需要转向 H4/D1 周期、共振触发条件的 Prompt 更新点。
- [x] 规划 `ArbitrageAgent` 原型：复用 `tools/quant_helpers.py` 的金银比计算，定义信号判定与对冲权重输出格式。
- [x] 为 RAG 知识库列出首批高价值素材（历史剧本、央行报告、交易原则），并确认 `scripts/ingest_macro_history.py` 的扩展需求。

## 收盘前检查
- [x] 汇总以上工作进度，形成《实盘前技术准备》日更记录，包含风险与阻塞项，准备晚间同步给交易台。
