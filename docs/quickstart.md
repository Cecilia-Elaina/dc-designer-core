# 快速开始

## 1. 检查环境

在项目目录打开 PowerShell：

```text
python scripts/doctor.py
```

至少应满足 Python、python-docx、openpyxl、Pillow 和 LibreOffice 检查。没有 LibreOffice 时仍可生成草案，但视觉质量门禁会保持“待验证”。

## 2. 在任意智能体中使用

本项目的核心 Skill、MCP Server 和通用启动提示词与具体智能体宿主解耦。先阅读[跨智能体接入](agent-compatibility.md)，再按当前宿主选择入口。项目级接入优先，未经明确授权不要写入用户全局配置。

### Codex

从当前仓库的 `.codex-plugin/` 识别插件后，在新建对话中调用：

```text
/dc-designer-core:dc-info-tech-design
```

### Claude Code

在仓库根目录启动项目级插件：

```text
claude --plugin-dir .
```

然后调用共享 Skill：

```text
/dc-designer-core:dc-info-tech-design
```

### Gemini CLI

从 GitHub 仓库安装扩展，重启 Gemini CLI 后调用命令：

```text
gemini extensions install https://github.com/xiajiadi/dc-designer-core
/dc-info-tech-design
```

### 其他智能体

支持 MCP 的宿主可以接入 `.mcp.json` 中的本地 `dc-designer-mcp`；不能使用 MCP 时，直接把 [`prompts/dc-designer-core.md`](../prompts/dc-designer-core.md) 粘贴给智能体。智能体应先报告实际接入方式和权限状态，再开始设计，不得把“读到了仓库文件”描述成“插件已安装”。

可以直接描述课题，也可以明确选择两种模式：

- `standard_fast`：提供学段、年级、课题、教材版本、单元、课时、设备和匿名班级共性学情，系统检索课程标准并生成草案；
- `collaborative`：从评价需求和绩效差距开始，逐阶段回答问题并确认候选方案。

系统会先展示官方依据候选和来源层级。教学目的、入门技能、学情、课时设备和教学策略等关键内容必须由教师确认或修改；“条款候选”不等同于最终依据。

## 3. 查看产品官网

```text
python -m http.server 4173 --directory site
```

打开 `http://127.0.0.1:4173/`。如果该端口已被占用，可改用 `python -m http.server 4174 --directory site` 并打开 `http://127.0.0.1:4174/`。官网用于了解产品、复制通用启动提示词和跳转 GitHub；教学设计通过当前智能体的原生入口、MCP 或本地 Skill 完成。

## 4. 导入教师资料

```text
python scripts/dc_info_tech.py knowledge-ingest --path <文件路径> --metadata-json '{"subject":"信息科技","school_type":"普通高中"}'
```

教师资料会标记为 `C1/teacher_private`，只作为情境和策略参考，不能被伪装成国家课程标准。含学生身份信息或个人成绩的文件会被拒绝。

## 5. 导出与验收

每个项目可以导出完整 Word 报告、教师指南、学生学习单、AI 过程记录、Excel 一致性矩阵、PNG 图和 Draw.io XML。只有来源确认、关键决策、图逻辑、一致性和视觉检查全部通过，才会出现 `final_ready`。

没有真实形成性评价数据时，形成性评价章节保持“待实施/待验证”，不生成虚构的学习效果。
