# 行情与宏观数据调用链梳理

## 1. 入口：`run_gold_outlook`
- 触发位置：`src/autogentest1/workflows/gold_outlook.py` → `build_conversation_context`
- 调用函数：
  - `fetch_price_history`（`services/market_data.py`）
  - `compute_indicators`（技术指标）
  - `collect_macro_highlights` / `collect_fundamental_snapshot`
  - `collect_sentiment_snapshot`
  - `build_risk_snapshot` / `build_settlement_checklist`

## 2. 行情数据流程
- `fetch_price_history` 根据 `settings.data_mode`
  - `mock` → `_mock_price_history`
  - `live/hybrid` → `_build_provider_chain` → 适配器集合
- 适配器实现：`services/data_providers/*.py`
  - `MarketDataAdapter.fetch_price_history` 接收 `start/end` 与可选 `Session`
- 缓存与重试
  - `_cached_session` 基于 `requests_cache` 与 `Retry`
  - `_retry_fetch` 按指数退避重试 + 捕获异常
- 成功后：截取近 `days` 天数据，`_ensure_freshness` 校验时效
- 下游使用：
  - `price_history_payload` 转 JSON 记录
  - `market_snapshot` → `compute_indicators`
  - 工具层 `get_gold_market_snapshot`

## 3. 宏观/情绪数据
- `collect_macro_highlights`：聚合宏观新闻/事件（依赖 `data/rag`）
- `collect_sentiment_snapshot`：访问 News API / Alpha Vantage（基于设置）
- 工具层 `get_macro_snapshot` 与 `get_news_sentiment`
  - 目前直接通过 `yfinance` 下载 DXY、TIP

## 4. DataAgent → Scribe 输出路径
- Phase 1 智能体顺序：Data → Tech → Macro → Fundamental → Quant
- `ScribeAgent` 将每次回复整合成 `phase/status/summary/details`
- 最终 `SettlementAgent` 输出整合报告，`main.py` 打印并写入文件

## 5. 痛点标记
- 行情适配器仅覆盖 REST 历史接口，无统一实时/回测切换层
- 工具函数 `get_macro_snapshot` / `get_gold_silver_ratio` 直接 `yfinance.download`，未复用统一适配器
- 风控与执行层对数据来源无显式标记，难以追踪主备链路
