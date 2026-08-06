# K12 教学设计方案

> 基于 Dick & Carey 模型，依据课程标准和教材

## 基本信息

| 项目 | 内容 |
|------|------|
| 课题名称 | {{topic_name}} |
| 学科 | {{subject}} |
| 年级 | {{grade}} |
| 教材版本 | {{textbook_version}} |
| 课时 | {{session_count}}课时 |
| 设计者 | {{designer}} |

---

## 一、课标依据

### 1.1 课程标准要求

{{#each curriculum_standards}}
**{{standard_name}}（{{standard_version}}）**

> {{clause_text}}
<!-- 来源：{{source_level}} - {{source_name}} -->
{{/each}}

### 1.2 学业质量标准

{{quality_standard}}

### 1.3 考试要求

{{exam_requirements}}

---

## 二、教材分析

### 2.1 教材内容结构

{{content_structure}}

### 2.2 编排意图

{{arrangement_intent}}

### 2.3 与其他章节的关联

{{chapter_relations}}

---

## 三、教学目的

### 3.1 教学目的陈述

{{goal_full_statement}}

<!-- 
来源追溯：
- 课标依据：{{curriculum_source}}
- 教材依据：{{textbook_source}}
- 考试依据：{{exam_source}}
-->

### 3.2 目的分析

| 步骤 | 描述 | 学习类型 |
|------|------|---------|
{{#each goal_steps}}
| {{step_id}} | {{description}} | {{learning_type}} |
{{/each}}

---

## 四、学情分析

### 4.1 入门技能

{{entry_skills}}

### 4.2 已有知识

{{prior_knowledge}}

### 4.3 学习动机

{{motivation_analysis}}

### 4.4 群体特征

{{group_characteristics}}

---

## 五、教学目标

### 5.1 学期目标

{{terminal_objective}}

### 5.2 课时目标

| 课次 | 目标编号 | 条件 | 行为 | 标准 |
|------|---------|------|------|------|
{{#each lesson_objectives}}
| {{session}} | {{objective_id}} | {{condition}} | {{behavior}} | {{criteria}} |
{{/each}}

---

## 六、教学重难点

### 6.1 教学重点

{{key_points}}

### 6.2 教学难点

{{difficult_points}}

### 6.3 难点突破策略

{{突破策略}}

---

## 七、教学过程

### 7.1 教学前活动

**导入：** {{introduction}}
**目标说明：** {{objective_statement}}
**预备知识激活：** {{prerequisite_activation}}

### 7.2 新知教学

{{#each new_knowledge}}
**{{step_name}}**

| 环节 | 内容 | 时间 |
|------|------|------|
| 内容呈现 | {{content}} | {{duration}} |
| 举例说明 | {{examples}} | |
| 学生参与 | {{participation}} | {{duration}} |
| 反馈纠正 | {{feedback}} | {{duration}} |
{{/each}}

### 7.3 巩固练习

{{practice_activities}}

### 7.4 课堂小结

{{summary}}

### 7.5 作业布置

{{homework}}

---

## 八、板书设计

```
{{board_design}}
```

---

## 九、教学反思

> 课后填写

### 9.1 目标达成情况

{{goal_achievement}}

### 9.2 学生表现

{{student_performance}}

### 9.3 改进措施

{{improvements}}

---

*本方案基于 Dick & Carey 教学系统化设计模型*
*课标依据：{{curriculum_standard_version}}*
*生成时间：{{generated_at}}*
