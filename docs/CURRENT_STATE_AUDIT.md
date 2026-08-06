# CURRENT_STATE_AUDIT

审查日期：2026-07-30

## 结论

当前仓库是一个已经覆盖教学系统设计模块的历史 MVP，但尚未达到 v1.0 中国 K12 信息科技 Codex 插件的发布条件。现有实现可以复用部分领域引擎和报告导出代码，但必须以新的产品边界、统一数据模型、本地知识库和图形导出协议重新组织。

## 基线证据

- `python -m pytest -q`：394 个测试中 393 个通过，1 个失败。
- 失败测试：`tests/test_phase7_agent_contract.py::TestExportIndexFilesHaveExistsAndSize::test_nine_files_in_index`。实际导出索引包含 10 个文件，旧测试仍硬编码期待 9 个。
- 当前仓库已有 `mcp-server/server.py`，但 v1.0 规格要求以 Skills + 本地脚本为发布主路径，远程 MCP 不应成为安装前置条件。
- 当前没有 `.codex-plugin/plugin.json`；已有 `.claude-plugin/plugin.json` 仍暴露 `dc-higher-ed` 和 `dc-corporate-training`。
- 当前 `data/standards` 主要是一个信息科技样例文件和旧测试数据，尚未形成可定位到章节/条款的完整国家标准库。
- 当前 `knowledge_ingest.py` 默认写入仓库内 `data/knowledge_base`，不符合教师私有资料保存在本机工作区且不被插件升级覆盖的要求。
- 当前 `teacher_memory.py` 的读写、删除、导出和隐私检查仍为 TODO。
- 当前 `drawio_exporter.py` 只生成单页基础图，缺少目的操作流程与技能层级结构的独立页面、决策菱形、分支标签、反馈边和图逻辑门禁。

## 范围核对

| 项目 | 现状 | v1.0 要求 | 判定 |
|---|---|---|---|
| 学段 | K12、高校、职教、企业均有旧入口或文字 | 仅小学、初中、普通高中 | REFACTOR |
| 学科 | 旧代码支持多学科关键词 | 仅信息科技/信息技术 | REWRITE |
| 方法 | Dick–Carey 模块已存在 | 统一为 v1.0 数据模型和门禁 | REFACTOR |
| 权威来源 | 本地元数据和样例标准 | 国家文件、版本、条款、状态、URL、哈希 | REWRITE |
| 私有知识库 | 仓库内文件索引 | 本机 `.dc-designer` 工作区、可导入和删除 | REWRITE |
| 设计模式 | 一次性 agent session | 课标快速设计 + 完整协同设计 | REFACTOR |
| 图形 | 单页 Draw.io/PNG | 至少两张独立图，多页可编辑 XML | REWRITE |
| 报告 | 已有 Word/Markdown/Excel 导出 | 真实内容、图像嵌入、全链路可追溯 | REFACTOR |
| Codex 发布 | 仅 Claude manifest | `.codex-plugin/plugin.json` + 三个 Skills | REWRITE |

## 模块事实分类

| 模块 | 分类 | 说明 |
|---|---|---|
| `core/ids.py`、`core/quality.py`、`core/alignment_checker.py` | KEEP/REFACTOR | 可复用稳定编号、质量和一致性思想，但需接入新 schema。 |
| `tools/goal_engine.py`、`objective_engine.py`、`assessment_engine.py` | REFACTOR | 有可复用规则，但输入仍依赖旧 pipeline。 |
| `tools/strategy_engine.py`、`materials_engine.py` | REFACTOR | 可作为生成器底层，必须由真实教学分析和评价驱动。 |
| `tools/skill_graph.py` | REWRITE | 需区分操作流程、技能层级和程序控制流。 |
| `tools/drawio_exporter.py` | REWRITE | 需多页 XML、稳定 ID、决策/反馈/边界和自动布局。 |
| `tools/knowledge_ingest.py` | REWRITE | 需本机工作区、DOCX/PDF/TXT 导入、元数据、索引和隐私门禁。 |
| `tools/teacher_memory.py` | REWRITE | 当前为 TODO，需实现本地、最小化、可删除存储。 |
| `tools/standards_search.py` | REFACTOR | 需收敛到信息科技并支持条款级检索。 |
| `tools/document_exporter.py` | REFACTOR | 可复用 Word 表格骨架，必须嵌入新图像和真实过程记录。 |
| `tools/agent_session.py`、`server.py` | REFACTOR/COMPAT | 保留兼容性，但不作为 v1 Skill 主入口。 |
| `skills/*`、`manifest.json`、`.claude-plugin/*` | REWRITE | 只保留三个信息科技 Skills 的 Codex 发布结构。 |
| 旧 `exports/`、旧 phase examples/tests | DEPRECATE/COMPAT | 作为回归材料保留，不应污染 v1 默认输出。 |

## 主要风险

1. 旧的 K12 判断会把高校教师误判为 K12，且旧 manifest 仍暴露非目标用户。
2. `source_documents` 当前主要被记录为来源元数据，并不等同于真实文档解析和条款检索。
3. 报告中的默认迭代记录如果没有明确标为合成数据，会造成伪造过程记录风险。
4. 现有测试数量较多，但存在与实际导出文件数脱节的硬编码测试，必须增加 v1 端到端和负向测试。

