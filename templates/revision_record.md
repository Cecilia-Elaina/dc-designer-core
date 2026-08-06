# 教学设计修改记录

## 修改概要

| 项目 | 内容 |
|------|------|
| 项目名称 | {{project_name}} |
| 修改编号 | {{revision_number}} |
| 修改日期 | {{revision_date}} |
| 修改触发 | {{trigger}} |
| 修改范围 | {{revision_scope}} |

---

## 一、修改输入

### 1.1 输入类型

{{input_type}}

### 1.2 原始输入内容

{{original_input}}

### 1.3 数据来源

| 数据类型 | 来源 | 可信度 |
|---------|------|--------|
{{#each data_sources}}
| {{type}} | {{source}} | {{credibility}} |
{{/each}}

---

## 二、影响分析

### 2.1 直接受影响模块

| 模块 | 影响程度 | 影响描述 |
|------|---------|---------|
{{#each directly_affected}}
| 模块{{module_id}}：{{module_name}} | {{impact_level}} | {{impact_description}} |
{{/each}}

### 2.2 间接受影响模块

| 模块 | 影响程度 | 影响描述 |
|------|---------|---------|
{{#each indirectly_affected}}
| 模块{{module_id}}：{{module_name}} | {{impact_level}} | {{impact_description}} |
{{/each}}

### 2.3 修改优先级

| 优先级 | 模块 | 修改内容 |
|--------|------|---------|
{{#each priority_list}}
| {{priority}} | 模块{{module_id}} | {{modification}} |
{{/each}}

---

## 三、修改内容

### 3.1 教学目的修改

**修改前：**
{{goal_before}}

**修改后：**
{{goal_after}}

**修改理由：**
{{goal_reason}}

**来源依据：**
{{goal_sources}}

---

### 3.2 教学分析修改

**修改前：**
{{analysis_before}}

**修改后：**
{{analysis_after}}

**修改理由：**
{{analysis_reason}}

**对技能流图的影响：**
{{analysis_impact}}

---

### 3.3 学习者分析修改

**修改前：**
{{learner_before}}

**修改后：**
{{learner_after}}

**修改理由：**
{{learner_reason}}

---

### 3.4 绩效目标修改

| 目标编号 | 修改前 | 修改后 | 修改理由 |
|---------|--------|--------|---------|
{{#each objective_modifications}}
| {{objective_id}} | {{before}} | {{after}} | {{reason}} |
{{/each}}

---

### 3.5 评价方案修改

| 评价项 | 修改前 | 修改后 | 修改理由 |
|--------|--------|--------|---------|
{{#each assessment_modifications}}
| {{item}} | {{before}} | {{after}} | {{reason}} |
{{/each}}

---

### 3.6 教学策略修改

**修改前：**
{{strategy_before}}

**修改后：**
{{strategy_after}}

**修改理由：**
{{strategy_reason}}

---

### 3.7 教学材料修改

| 材料 | 修改前 | 修改后 | 修改理由 |
|------|--------|--------|---------|
{{#each material_modifications}}
| {{material_id}} | {{before}} | {{after}} | {{reason}} |
{{/each}}

---

## 四、一致性检查

### 4.1 修改前一致性

| 检查对 | 状态 | 问题 |
|--------|------|------|
{{#each pre_alignment}}
| {{pair}} | {{status}} | {{issues}} |
{{/each}}

### 4.2 修改后一致性

| 检查对 | 状态 | 问题 |
|--------|------|------|
{{#each post_alignment}}
| {{pair}} | {{status}} | {{issues}} |
{{/each}}

### 4.3 新引入的不一致

{{#if new_inconsistencies}}
| 检查对 | 问题 | 严重程度 |
|--------|------|---------|
{{#each new_inconsistencies}}
| {{pair}} | {{issue}} | {{severity}} |
{{/each}}
{{else}}
无新引入的不一致
{{/if}}

---

## 五、质量门禁

### 5.1 修改前门禁

| 模块 | 状态 | 一票否决项 |
|------|------|-----------|
{{#each pre_quality_gates}}
| 模块{{module_id}} | {{status}} | {{veto_items}} |
{{/each}}

### 5.2 修改后门禁

| 模块 | 状态 | 一票否决项 |
|------|------|-----------|
{{#each post_quality_gates}}
| 模块{{module_id}} | {{status}} | {{veto_items}} |
{{/each}}

---

## 六、教师确认

### 6.1 确认内容

{{teacher_confirmation_content}}

### 6.2 确认状态

{{teacher_confirmation_status}}

### 6.3 确认日期

{{teacher_confirmation_date}}

---

## 七、修改总结

### 7.1 修改完成情况

{{revision_completion_status}}

### 7.2 剩余问题

{{remaining_issues}}

### 7.3 下一步建议

{{next_steps}}

### 7.4 对后续教学的影响

{{impact_on_teaching}}

---

## 附录：修改前后对比

### 教学目的对比

| 项目 | 修改前 | 修改后 |
|------|--------|--------|
| 完整陈述 | {{goal_comparison.before}} | {{goal_comparison.after}} |

### 关键目标对比

| 目标 | 修改前行为动词 | 修改后行为动词 |
|------|--------------|--------------|
{{#each objective_comparison}}
| {{objective_id}} | {{before_verb}} | {{after_verb}} |
{{/each}}

---

*修改记录基于 Dick & Carey 教学系统化设计模型*
*修改编号：{{revision_number}}*
*记录时间：{{recorded_at}}*
