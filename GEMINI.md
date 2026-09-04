# DC Designer

这是一个面向中国大陆小学、初中和普通高中九学科教师的 Dick–Carey 教学系统设计扩展。v3 支持语文、数学、英语、物理、化学、生物、历史、地理和政治。

使用本扩展时：

- 先读取 `DESIGN.md`、`docs/agent-compatibility.md` 和对应的 `skills/*/SKILL.md`；历史 v1 信息科技合同仍可按需读取 `docs/v1_plugin_contract.md`；
- 优先使用 `dc-designer-mcp`，没有 MCP 时运行 `python scripts/dc_designer.py`；
- 默认从 `dc-info-tech-design` 开始，评审和修订分别使用对应 Skill。三个名称保留用于兼容旧入口，内容按学科和学段选择 v3 适配器；
- 关键决策必须由教师确认，来源保持分层；
- 不保存学生身份信息，不把教师私有资料写回公开仓库，不伪造形成性评价效果；
- 缺少信息时只问当前阶段最必要的问题，并保留草案状态。
