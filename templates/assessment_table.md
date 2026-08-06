# 评价方案模板

## 评价概要

| 项目 | 内容 |
|------|------|
| 评价名称 | {{assessment_name}} |
| 关联目标 | {{linked_objectives}} |
| 评价类型 | {{assessment_type}} |
| 预计时长 | {{duration}} |

---

## 一、入门技能测试

### 测试目的

{{entry_test_purpose}}

### 测试题目

| 题号 | 题型 | 题目内容 | 关联技能 | 分值 |
|------|------|---------|---------|------|
{{#each entry_test_items}}
| {{item_id}} | {{item_type}} | {{question}} | {{linked_skill}} | {{score}} |
{{/each}}

### 掌握标准

{{entry_mastery_criteria}}

---

## 二、前测

### 测试目的

{{pretest_purpose}}

### 测试题目

| 题号 | 题型 | 题目内容 | 关联目标 | 分值 |
|------|------|---------|---------|------|
{{#each pretest_items}}
| {{item_id}} | {{item_type}} | {{question}} | {{linked_objective}} | {{score}} |
{{/each}}

### 掌握标准

{{pretest_mastery_criteria}}

---

## 三、练习测试

{{#each practice_tests}}
### 练习{{practice_number}}：{{session}}

| 题号 | 题型 | 题目内容 | 关联目标 | 反馈方式 |
|------|------|---------|---------|---------|
{{#each items}}
| {{item_id}} | {{item_type}} | {{question}} | {{linked_objective}} | {{feedback}} |
{{/each}}
{{/each}}

---

## 四、后测

### 测试目的

{{posttest_purpose}}

### 测试题目

| 题号 | 题型 | 题目内容 | 关联目标 | 分值 | 难度 |
|------|------|---------|---------|------|------|
{{#each posttest_items}}
| {{item_id}} | {{item_type}} | {{question}} | {{linked_objective}} | {{score}} | {{difficulty}} |
{{/each}}

### 掌握标准

{{posttest_mastery_criteria}}

---

## 五、行为表现评价

{{#each performance_scales}}
### {{scale_name}}

**关联目标：** {{target_objective}}

**操作说明（给学习者）：**
{{instructions_for_learners}}

**评价量表：**

| 要素 | 评判类型 | 评分标准 |
|------|---------|---------|
{{#each elements}}
| {{description}} | {{scale_type}} | {{scoring_criteria}} |
{{/each}}
{{/each}}

---

## 六、学习档案评价

### 档案内容

{{portfolio_contents}}

### 评价标准

{{portfolio_criteria}}

### 提交要求

{{portfolio_requirements}}

---

## 七、评价对齐检查

| 绩效目标 | 评价证据 | 对齐状态 |
|---------|--------|---------|
{{#each alignment_check}}
| {{objective_id}} | {{assessment_item}} | {{status}} |
{{/each}}

---

## 八、答题指示

### 整体指示

{{overall_instructions}}

### 分题型指示

{{#each item_type_instructions}}
**{{item_type}}：**
{{instructions}}
{{/each}}

---

*评价方案基于 Dick & Carey 教学系统化设计模型*
*遵循四类质量评判原则：以目标为中心、以学生为中心、以环境为中心、以评测为中心*
*生成时间：{{generated_at}}*
