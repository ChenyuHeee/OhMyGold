# 贡献指南

感谢关注 AutoGen DeepSeek 黄金分析项目！为了让协作更加顺畅，请在提交 Issue 或 Pull Request 前阅读以下指南。

## 环境准备
1. Fork 仓库并克隆到本地。
2. 创建 Python 3.10+ 虚拟环境并安装依赖：
   ```bash
   pip install -e .[dev]
   ```
3. 复制 `.env.example` 为 `.env`，填入必要的 API Key（可使用假值以便本地测试）。

## 提交 Issue
- 描述问题或需求的背景与动机。
- 给出复现步骤、期望行为以及实际行为。
- 如涉及日志，请脱敏后附上关键信息。

## 提交 Pull Request
1. PR 须基于 `main` 最新代码，必要时请 rebase。
2. 提交前运行完整测试：
   ```bash
   pytest
   ```
3. 若修改涉及文档、配置或接口，请同步更新 README 或相关文档。
4. PR 描述应包含：
   - 变更概述
   - 测试情况
   - 可能的风险与兼容性影响

## 代码风格
- 遵循项目现有结构与命名方式。
- 配置、文档与代码中的时间使用 UTC（`datetime.now(datetime.UTC)`）。
- 所有代理/工具输出需保持 JSON Schema 约定。

## 行为准则
参与贡献即表示同意遵守 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)。如遇冲突或需要帮助，请通过 Issue 或邮件联系维护团队。

再次感谢你的贡献！
