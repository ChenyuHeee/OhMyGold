# API Key 清单

| 服务名称 | 环境变量 | 用途 | 必须/可选 | 备注 |
|---------|----------|------|-----------|------|
| DeepSeek | `DEEPSEEK_API_KEY` | 作为云端主力模型，驱动 HeadTrader 等关键 Agent 的推理 | 必须 | 官网获取密钥，注意请求配额；`DEEPSEEK_MODEL`、`DEEPSEEK_BASE_URL` 同步配置 |
| NewsAPI | `NEWS_API_KEY` | 聚合外部新闻源，增强舆情情绪量化 | 可选 | 若留空将使用 RSS 和内置占位数据；启用后建议设置请求频率上限 |
| Alpha Vantage | `ALPHAVANTAGE_API_KEY` | 备用宏观/经济指标数据源 | 可选 | 当前未默认使用，可按需接入 |
| 本地 Ollama | — | 运行 `qwen2.5-14b-instruct` 等本地模型 | 必须（用于本地模型） | 需提前在本机通过 Ollama 拉取模型，无需额外密钥 |
| 其他外部数据供应商 | 自定义 | 扩展宏观/舆情数据源时使用 | 可选 | 将新增的密钥写入 `.env` 并更新 `settings.py` 对应字段 |

> 小贴士：
> - 所有密钥建议放入 `.env` 并避免提交到版本库。
> - 生产环境可结合密钥管理服务（如 AWS Secrets Manager）进行分发与轮换。
