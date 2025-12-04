# 2025-12-04 实盘前技术准备日记

## 今日亮点
- 完成 TwelveData / Polygon 默认 symbol map 配置，并在 Settings 中合并覆盖逻辑，避免多级降级。
- 新增风控闸门流程图与文档，使 HardRiskBreachError 闭环清晰。
- 更新 Risk/Compliance 提示词，确保按流程文档执行拒单回路。
- 梳理行情供应商订阅与认证动作，明确 IBKR、Polygon、FRED、TradingEconomics 的当日推进步骤。
- 增强 RAG ingest 脚本，支持 namespace/tag、日志写盘，并兼容新版 Chroma 接口。
- 为 RAG 自动 ingest 添加默认语料回退与单元测试，防止配置路径缺失时加载失败。

## 未决事项
- 等待 IBKR 市场数据订阅审批（预计 1-2 个工作日）。
- TradingEconomics 付费计划确认，需财务审批。
- RAG ingest 脚本待新增标签与输出记录功能。

## 风险与阻塞
- 若 Polygon 速率限制低于预期，需要补充缓存策略并评估备援供应商。
- ArbitrageAgent 尚未上线，金银比信号仍依赖 Quant 输出，需关注延迟。
- Chroma 升级后 embedding 接口变更频繁，需持续关注依赖版本。

## 下一步
1. 开 Issue 跟踪 ArbitrageAgent 开发（提示词、工具扩展、测试）。
2. 在 `tests/test_rag.py` 补充标签/命名空间相关用例，巩固新特性。
3. 准备 README 补充关于订阅与凭证管理的引用链接。
