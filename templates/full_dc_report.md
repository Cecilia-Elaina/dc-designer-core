# 教学系统设计报告

> 基于 Dick & Carey 教学系统化设计模型

## 项目信息

| 项目 | 内容 |
|------|------|
| 项目名称 | {{project_name}} |
| 教学场景 | {{scene_type}} |
| 学科/领域 | {{subject}} |
| 年级/层次 | {{grade_level}} |
| 教材版本 | {{textbook}} |
| 课时安排 | {{session_count}}课时，共{{total_hours}}学时 |
| 设计者 | {{designer}} |
| 设计日期 | {{created_at}} |

---

## 一、教学目的

### 1.1 绩效问题描述

{{performance_problem}}

### 1.2 教学目的陈述

{{goal_full_statement}}

<!-- 
来源追溯：
{{#each sources}}
- {{source_name}} — 可信度：{{credibility}} — 作为目标依据：{{can_be_goal_basis}}
{{/each}}
-->

### 1.3 目的分析

| 要素 | 内容 |
|------|------|
| 学习者 | {{learner}} |
| 行为 | {{behavior}} |
| 环境 | {{context}} |
| 工具 | {{tools}} |

### 1.4 可行性检查

| 检查项 | 结果 |
|--------|------|
| 管理层接受 | {{management_acceptance}} |
| 资源充足 | {{sufficient_resources}} |
| 内容稳定 | {{content_stability}} |
| 学习者可用 | {{learner_availability}} |

---

## 二、教学分析

### 2.1 目的分类

{{goal_classification}}

### 2.2 教学分析流图

{{skill_graph_visual}}

### 2.3 主要步骤

| 步骤编号 | 描述 | 学习类型 |
|---------|------|---------|
{{#each goal_steps}}
| {{step_id}} | {{description}} | {{learning_type}} |
{{/each}}

### 2.4 从属技能

| 技能编号 | 描述 | 学习类型 | 父步骤 |
|---------|------|---------|--------|
{{#each subordinate_skills}}
| {{skill_id}} | {{description}} | {{learning_type}} | {{parent_step}} |
{{/each}}

### 2.5 入门技能

| 技能编号 | 描述 | 学习类型 | 假设已知 |
|---------|------|---------|---------|
{{#each entry_skills}}
| {{skill_id}} | {{description}} | {{learning_type}} | {{assumed_known}} |
{{/each}}

---

## 三、学习者和环境分析

### 3.1 学习者分析

{{#each learner_dimensions}}
**{{dimension_name}}：** {{description}}
{{/each}}

### 3.2 应用环境分析

**物理条件：** {{physical_conditions}}
**社会环境：** {{social_environment}}
**管理支持：** {{management_support}}
**技能相关性：** {{skill_relevance}}

### 3.3 学习环境分析

**现状：** {{current_state}}
**应有条件：** {{desired_conditions}}
**设施匹配：** {{facility_match}}
**模拟可行性：** {{simulation_feasibility}}

---

## 四、绩效目标

### 4.1 学期目标

{{terminal_objective.full_statement}}

<!-- 
条件：{{terminal_objective.condition}}
行为：{{terminal_objective.behavior}}
标准：{{terminal_objective.criteria}}
-->

### 4.2 从属目标

| 目标编号 | 关联技能 | 条件 | 行为 | 标准 |
|---------|---------|------|------|------|
{{#each subordinate_objectives}}
| {{objective_id}} | {{linked_skill_id}} | {{condition}} | {{behavior}} | {{criteria}} |
{{/each}}

---

## 五、评价方案

### 5.1 入门技能测试

**目的：** {{entry_behaviors_test.purpose}}
**掌握标准：** {{entry_behaviors_test.mastery_criteria}}

| 题号 | 题型 | 题目 | 关联技能 |
|------|------|------|---------|
{{#each entry_behaviors_test.items}}
| {{item_id}} | {{item_type}} | {{question}} | {{linked_skill}} |
{{/each}}

### 5.2 前测

**目的：** {{pretest.purpose}}
**掌握标准：** {{pretest.mastery_criteria}}

| 题号 | 题型 | 题目 | 关联目标 |
|------|------|------|---------|
{{#each pretest.items}}
| {{item_id}} | {{item_type}} | {{question}} | {{linked_objective}} |
{{/each}}

### 5.3 后测

**目的：** {{posttest.purpose}}
**掌握标准：** {{posttest.mastery_criteria}}

| 题号 | 题型 | 题目 | 关联目标 |
|------|------|------|---------|
{{#each posttest.items}}
| {{item_id}} | {{item_type}} | {{question}} | {{linked_objective}} |
{{/each}}

### 5.4 行为表现量表

{{#each performance_scales}}
**{{scale_name}}**

| 要素 | 评判类型 |
|------|---------|
{{#each elements}}
| {{description}} | {{scale_type}} |
{{/each}}

**给学习者的操作说明：** {{instructions_for_learners}}
{{/each}}

---

## 六、教学策略

### 6.1 内容顺序安排

{{content_sequence}}

### 6.2 内容分块

{{content_clustering}}

### 6.3 教学前活动

**激励策略：** {{learning_components.preinstructional.motivation}}
**目标说明：** {{learning_components.preinstructional.objectives}}
**预备技能评估：** {{learning_components.preinstructional.prerequisites}}

### 6.4 内容呈现

| 目标编号 | 呈现内容 | 例子 | 媒体 |
|---------|---------|------|------|
{{#each learning_components.content_presentation}}
| {{objective_id}} | {{content}} | {{examples}} | {{media}} |
{{/each}}

### 6.5 学习者参与

| 目标编号 | 练习活动 | 反馈机制 |
|---------|---------|---------|
{{#each learning_components.learner_participation}}
| {{objective_id}} | {{practice_activities}} | {{feedback_mechanism}} |
{{/each}}

### 6.6 评测策略

{{learning_components.assessment}}

### 6.7 增强活动

**记忆辅助：** {{learning_components.enhancement.memory_aids}}
**迁移考虑：** {{learning_components.enhancement.transfer_considerations}}

### 6.8 媒体选择

{{media_selection}}

### 6.9 传递系统

{{delivery_system}}

### 6.10 课时分配

| 课次 | 标题 | 时长 | 覆盖目标 | 活动 |
|------|------|------|---------|------|
{{#each session_plan}}
| {{session_number}} | {{session_title}} | {{duration}} | {{objectives_covered}} | {{activities}} |
{{/each}}

---

## 七、教学材料

{{#each instructional_materials}}
### {{material_id}}：{{type}}

**目标：** {{target_objective}}
**内容：** {{content}}
**媒体格式：** {{media_format}}
{{/each}}

---

## 八、形成性评价方案

### 8.1 一对一评价

**目的：** {{one_on_one.purpose}}
**参与者：** {{one_on_one.participants}}
**数据收集：**
- 清晰度：{{one_on_one.data_collection.clarity}}
- 影响力：{{one_on_one.data_collection.impact}}
- 可行性：{{one_on_one.data_collection.feasibility}}

### 8.2 小组评价

**目的：** {{small_group.purpose}}
**参与者数量：** {{small_group.participant_count}}
**选择标准：** {{small_group.participant_selection}}

### 8.3 场景评价

**目的：** {{field_trial.purpose}}
**参与者数量：** {{field_trial.participant_count}}
**环境：** {{field_trial.environment}}

---

## 九、质量总结

### 9.1 质量门禁检查

| 模块 | 状态 | 一票否决项 |
|------|------|-----------|
{{#each quality_gates}}
| 模块{{module_id}} | {{#if passed}}✅ 通过{{else}}❌ 未通过{{/if}} | {{veto_items}} |
{{/each}}

### 9.2 一致性检查

| 检查对 | 状态 | 问题 |
|--------|------|------|
{{#each alignment_checks}}
| {{pair}} | {{#if consistent}}✅ 一致{{else}}❌ 不一致{{/if}} | {{issues}} |
{{/each}}

---

## 十、来源追溯报告

### 来源统计

| 等级 | 数量 | 占比 |
|------|------|------|
| A-官方权威 | {{source_stats.A_count}} | {{source_stats.A_percent}} |
| B-专业权威 | {{source_stats.B_count}} | {{source_stats.B_percent}} |
| C-教师私有 | {{source_stats.C_count}} | {{source_stats.C_percent}} |
| D-公开来源 | {{source_stats.D_count}} | {{source_stats.D_percent}} |
| E-AI生成 | {{source_stats.E_count}} | {{source_stats.E_percent}} |

### 来源详细列表

{{#each full_source_list}}
| 来源名称 | 等级 | 可信度 | 作为目标依据 |
|---------|------|--------|------------|
| {{source_name}} | {{source_level}} | {{credibility}} | {{can_be_goal_basis}} |
{{/each}}

---

## 附录

### 附录A：修改历史

| 修改次数 | 日期 | 触发原因 | 受影响模块 |
|---------|------|---------|-----------|
{{#each revision_history}}
| {{revision_number}} | {{created_at}} | {{trigger}} | {{modules_affected}} |
{{/each}}

### 附录B：教师确认记录

| 确认内容 | 确认日期 |
|---------|---------|
{{#each teacher_confirmations}}
| {{content}} | {{confirmation_date}} |
{{/each}}

---

*本报告由 dc-designer-core 插件生成*
*遵循 Dick & Carey 教学系统化设计模型（第五版）*
*生成时间：{{generated_at}}*
