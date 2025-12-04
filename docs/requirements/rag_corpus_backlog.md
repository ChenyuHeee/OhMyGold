# RAG 知识库素材规划

目标：扩充 `data/rag/` 目录，使 Phase 1 研究角色能检索高价值案例、政策文件与交易原则。以下分层列出首批建议与对应 ingest 需求。

## 历史交易剧本
- **素材**：
  - 《2011-2012 黄金牛市回顾》
  - 《2013 Taper Tantrum 避险策略》
  - 《2020 疫情流动性危机黄金对冲记录》
- **格式**：Markdown + JSON 摘要。
- **ingest 动作**：
  1. 将文档存放于 `data/rag/trading_playbook/`。
  2. 运行 `scripts/ingest_macro_history.py --namespace trading-playbook`。
  3. 更新索引成功后在日志中记录 chunk 数量。

## 央行与官方报告
- **素材**：
  - 世界黄金协会季度报告（WGC Q3/Q4）
  - IMF SDR 黄金储备数据摘要
  - 各国央行购金动态（PBoC、俄罗斯央行、土耳其央行）。
- **格式**：PDF 提取文本 → Markdown 总结。
- **ingest 动作**：
  1. 清洗 PDF，剔除表格噪音。
  2. 转存为 Markdown 后放入 `data/rag/macro_history/`。
  3. 在 `ingest_macro_history.py` 增加 `--tag central-bank` 参数以方便查询（需要新增 CLI 选项）。

## 交易原则与风控守则
- **素材**：
  - 伦敦金 OTC 操作流程。
  - 高频波动时段对冲守则。
  - 头寸调节与限价单布置手册。
- **格式**：短文 Markdown，突出 checklist。
- **ingest 动作**：添加至 `data/rag/trading_playbook/`，运行 ingest，并在 `rag_index/default.json` 更新 metadata。

## 其他拓展
- **宏观时间线**：FOMC 会议摘要、美国 CPI/就业事件窗口。
- **舆情数据**：与 `news_watcher` 对接的关键词解读。

## 工程需求
1. **脚本增强**：`scripts/ingest_macro_history.py` 已支持 `--namespace`、`--tag` 与 `--log-dir`，后续可考虑为 tag 写入 schema 校验。
2. **测试补充**：在 `tests/test_rag.py` 添加针对标签过滤的用例（待补充）。
3. **文档更新**：在 README Data 工具章节补充 ingest 指南及新参数说明。
