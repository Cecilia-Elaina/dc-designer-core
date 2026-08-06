# REUSE_MATRIX

本矩阵以 v1.0 规格为准，说明旧实现的复用边界。

## 直接复用

| 资产 | 复用方式 |
|---|---|
| `core/ids.py` | 作为旧项目兼容入口；新项目编号使用同一确定性原则并补齐 G/S/SS/SK/E/PO/AS/MAT/SRC/CLM 前缀。 |
| `core/quality.py` | 复用基础门禁函数，补充信息科技、来源和数值门禁。 |
| `core/alignment_checker.py` | 复用检查框架，改为读取统一项目对象。 |
| `tools/goal_engine.py` | 复用可观测行为和目的校验逻辑。 |
| `tools/objective_engine.py` | 复用 CN/B/CR 目标生成和检查逻辑。 |
| `tools/assessment_engine.py` | 复用评价骨架，补充真实编程、运行、测试、调试证据。 |

## 需要重构

| 资产 | 重构要求 |
|---|---|
| `tools/standards_search.py` | 统一学段、科目、版本和条款记录；禁止将宏观政策直接变成课时目标。 |
| `tools/knowledge_ingest.py` | 使用 `DC_DESIGNER_HOME`/教师工作区；增加文档解析、哈希、元数据和隐私扫描。 |
| `tools/teacher_memory.py` | 以本地 JSON/SQLite 实现读写、删除、导出和教师确认。 |
| `tools/agent_session.py` | 增加两个模式和信息科技范围验证；保留旧 MCP 作为兼容层。 |
| `tools/document_exporter.py` | 以实际项目数据生成报告，嵌入技能图和来源证据，不生成伪造 AI 过程。 |
| `server.py` | 与本地核心保持兼容；Codex 安装不依赖它。 |

## 必须重写

| 资产 | 原因 |
|---|---|
| `tools/skill_graph.py` | 旧图只有通用层级节点，无法表达两类教学分析、决策、循环和反馈。 |
| `tools/drawio_exporter.py` | 旧导出为单页基础 XML，无法满足多页面、可编辑和图逻辑质量门禁。 |
| `.codex-plugin/plugin.json` | 当前不存在，必须新增官方 Codex 入口。 |
| 三个公开 Skills | 旧 Skills 仍包含高校、企业和多学科边界，必须收敛到信息科技。 |

## 历史兼容资产

旧 `mcp-server`、`exports`、Phase 7-9 示例和测试暂时保留。它们只能用于回归和迁移，不得成为 v1 默认路径或官方产品文案。

