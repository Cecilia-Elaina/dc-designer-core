# dc-designer-mcp Server

## 概述

`dc-designer-mcp` 是 DC Designer 的跨智能体 MCP Server，提供外部能力接口，包括课程标准检索、教师知识库管理、教学分析流图生成、绩效目标生成、评价方案生成、教学策略生成、形成性评价数据采集、修改教学、文件导出等。Codex、Claude Code、Gemini CLI 和其他支持 MCP 的宿主可以共用这一个本地入口。

## 安装

```bash
cd mcp-server
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

## 运行

```bash
.venv/Scripts/python server.py
```

上面的环境位于当前项目目录，只服务于当前仓库；其他智能体也可以直接复用宿主已经配置好的项目 Python 环境。

## 工具列表

| 工具名称 | 功能 | 对应模块 |
|---------|------|---------|
| `standards_search` | 课程标准/政策/专业教学标准检索 | 模块1 |
| `knowledge_ingest` | 教师私有知识库管理 | 模块1-7 |
| `teacher_memory` | 教师长期记忆管理 | 全流程 |
| `goal_engine` | 教学目的生成与验证 | 模块1 |
| `skill_graph` | 教学分析流图生成 | 模块2 |
| `objective_engine` | 绩效目标生成与验证 | 模块4 |
| `assessment_engine` | 评价方案生成 | 模块5 |
| `strategy_engine` | 教学策略生成 | 模块6 |
| `formative_evaluation` | 形成性评价数据采集与分析 | 模块8 |
| `revision_engine` | 教学修改引擎 | 模块9 |
| `alignment_checker` | 模块间一致性检查 | 全流程 |
| `export_package` | 设计包导出 | 模块10 |

## 数据存储

- 项目数据：`data/projects/`
- 教师档案：`data/teachers/`
- 知识库：`data/knowledge/`
- 模板：`templates/`

## 隐私保护

- 不存储学生个人信息
- 教师数据需要确认才能保存
- 所有数据存储在本地

## 开发状态

**第一阶段**：接口草案（当前）
**第二阶段**：核心功能实现
**第三阶段**：完整功能实现
