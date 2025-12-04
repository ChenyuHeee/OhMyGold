# 行情供应商订阅与认证清单

此清单聚焦 IBKR、Polygon.io、FRED 与 TradingEconomics 四个数据源，帮助当天内识别可立即推进的对接动作。

## IBKR (Interactive Brokers)
- **计划与权限**：
  - 申请 `IBKR Lite` 或 `IBKR Pro` 账户，确保启用 `Market Data Subscription - Metals`（CME、COMEX）。
  - 需要订阅 `US Metals Bundle` (实时) 与 `US Bond & FX Bundle` (美元指数、国债代理)。
- **认证步骤**：
  1. 在 IBKR Client Portal 开通 `FIX CTCI` 或 `IB Gateway`，用于 API 访问。
  2. 通过 `IBKR Client Portal > Settings > API` 生成 `Client ID` 与 `Access Token`。
  3. 安装 `ib_insync` 并配置 TWS / Gateway，记录 `host`, `port`, `clientId`。
- **今日可执行**：
  - 提交市场数据订阅申请（需账户余额≥2,000 USD）。
  - 下载最新版 `IB Gateway`，验证能以只读模式登录沙箱。
  - 建立内部凭证管理表（token、client id、订阅状态）。

## Polygon.io
- **计划与权限**：
  - 选择 `Launch` (免费) 或 `Developer` (付费) 计划；实时外汇需要 `Developer` 级别以上。
  - 金属与指数需 `Indices` / `Commodities` 附加包。
- **认证步骤**：
  1. 注册账号并生成 `API Key`。
  2. 在 Dashboard 确认启用 `Currencies`, `Indices`, `Commodities` 数据集。
  3. 将 API Key 纳入 `.env` (`POLYGON_API_KEY`)，更新 Settings。
- **今日可执行**：
  - 完成付费计划升级并记录账单信息。
  - 运行 `curl https://api.polygon.io/v2/aggs/ticker/C:XAUUSD/range/1/day/...` 验证权限。
  - 在内部 wiki 登记速率限制与回退策略。

## FRED (Federal Reserve Economic Data)
- **计划与权限**：
  - 免费 API；需注册邮箱获取 `API Key`。
  - 主要用于 DXY proxy (`DTWEXBGS`), TIPS (`DFII10`) 等宏观序列。
- **认证步骤**：
  1. 注册 FRED 账户并申请 API Key。
  2. 将 Key 写入 `.env` (`FRED_API_KEY`)，在 data adapter 中实现脚手架。
  3. 配置 `requests-cache` 以减少频繁请求。
- **今日可执行**：
  - 提交 API Key 申请，预计即时返回。
  - 创建简单脚本拉取 `DTWEXBGS` 验证响应。
  - 记录 API 限额（3 次/秒，10 万次/日）。

## TradingEconomics
- **计划与权限**：
  - 免费层提供 1,000 次/月；实时指标需付费计划。
  - 黄金相关关键系列：`Gold` 现货、`US Government Bond 10Y`、`Inflation Rate`。
- **认证步骤**：
  1. 注册账号并申请 `Client Key/Secret`。
  2. 通过 `https://api.tradingeconomics.com/markets/symbol/XAUUSD:CURR?c=client:secret` 验证。
  3. 确认契约允许缓存并在 `.env` 中存储凭证。
- **今日可执行**：
  - 确认是否升级至 `Global` 计划以获取更高配额。
  - 建立调用示例并测试速率限制。
  - 评估与现有 DataSourceRouter 的接口映射。

## 总体下一步
1. 建立 `credentials.yaml`（存储在受控密钥库）映射供应商 → 凭证 → 维护人。
2. 在 `scripts/` 目录创建 smoke test 脚本，纳入 CI（后续待办）。
3. 更新 `config/settings.py`，补齐新供应商的 symbol map（TBD：FRED/TradingEconomics）。
