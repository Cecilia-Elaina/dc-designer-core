---
name: dc-info-tech-review
description: 评审中国 K12 九学科教学系统设计的依据、完整性、图逻辑和一致性；名称保留以兼容既有宿主入口。
---

# dc-info-tech-review

评审中国 K12 九学科教学系统设计，不重写原设计。先确认文件或 `project.json`，再运行：

```text
python scripts/dc_designer.py review --project <project.json> --output-dir <output-dir>
```

评审必须覆盖：

- 学段、学科和课程标准版本是否匹配；
- 课标条款是否具体、可定位，是否把 AI 推断或教师私有资料伪装成官方依据；
- 需求/绩效分析、教学目的、目的分类、目的操作流程、技能层级、从属技能、入门技能；
- 学习者、学习环境和应用环境；
- 每个绩效目标的 CN/B/CR 与技能节点、评价、活动、材料链接；
- 入门测试、前测、练习、形成性检查、后测、真实性任务和量规；
- 当前学科课题是否真的包含其所需的概念、方法、表达/实践、证据和边界条件；
- 两张核心技能图是否为独立图，Draw.io 是否可编辑、无重复 ID、无断链、无节点重叠；
- 课时、分值、人数/百分比等数值是否一致；
- 是否包含学生姓名、学号、具体成绩等敏感信息。

输出每条可执行 finding：`finding_id`、`type`、`severity`、`description`、`evidence`、`suggested_fix`、`affected_modules`、`related_quality_gate`。不要直接替用户重写设计，也不要在依据不足时给出“优秀”结论。

## 会话与报告

如果项目属于可恢复会话，保留 `session_id`、项目版本和来源快照信息。评审结果必须指出当前阶段、待确认事项、来源版本、视觉检查状态和 `can_export_final`；不要把“文件存在”当作报告视觉质量已经通过。
