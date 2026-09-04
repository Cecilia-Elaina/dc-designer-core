# DC Designer v3.0.0

## 这次更新

DC Designer v3 将公开支持范围扩展为中国大陆小学、初中和普通高中九个学科：语文、数学、英语、物理、化学、生物、历史、地理和政治。

核心流程仍然遵循 Dick–Carey 模型。v3 通过学科适配器把每个学科的课程标准来源、核心能力、可观察行为、评价证据、策略提示和材料类型接入同一条设计链。

## 使用方式

- 支持 `standard_fast` 课标约束快速设计和 `collaborative` 完整协同设计；
- MCP 工具 `dc_design_session`、`dc_review_session`、`dc_revise_session` 和 `dc_export_package` 支持 `education_scope=k12_nine_subjects`；
- 没有原生插件入口时，可运行 `python scripts/dc_designer.py`，或把 `prompts/dc-designer-core.md` 粘贴给能读取项目文件的智能体；
- 原有 `dc-info-tech-*` Skill 和 `scripts/dc_info_tech.py` 继续作为信息科技 v1 兼容入口保留。

## 证据与边界

仓库内九学科课程标准仅保留官方来源元数据、公开链接和条款候选。条款、教材版本、单元位置、班级共性学情、教学策略和材料都需要教师确认；没有真实形成性评价数据时，项目保持“待实施 / 待验证”，不会生成学生效果结论。高校、职业教育、企业培训和九学科之外的学科不在 v3 范围内。
