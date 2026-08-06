# 形成性评价记录表

## 评价概要

| 项目 | 内容 |
|------|------|
| 评价阶段 | {{evaluation_stage}} |
| 评价日期 | {{evaluation_date}} |
| 评价者 | {{evaluator}} |
| 关联项目 | {{project_name}} |

---

## 一、一对一评价

### 1.1 参与者信息

| 参与者编号 | 特征描述 |
|-----------|---------|
{{#each one_on_one_participants}}
| {{participant_id}} | {{profile}} |
{{/each}}

### 1.2 清晰度数据

| 维度 | 参与者1 | 参与者2 | 参与者3 | 总结 |
|------|--------|--------|--------|------|
| 词汇水平 | {{clarity.vocabulary.p1}} | {{clarity.vocabulary.p2}} | {{clarity.vocabulary.p3}} | {{clarity.vocabulary.summary}} |
| 句式复杂度 | {{clarity.sentence.p1}} | {{clarity.sentence.p2}} | {{clarity.sentence.p3}} | {{clarity.sentence.summary}} |
| 导入效果 | {{clarity.intro.p1}} | {{clarity.intro.p2}} | {{clarity.intro.p3}} | {{clarity.intro.summary}} |
| 例子恰当性 | {{clarity.examples.p1}} | {{clarity.examples.p2}} | {{clarity.examples.p3}} | {{clarity.examples.summary}} |
| 过渡自然度 | {{clarity.transitions.p1}} | {{clarity.transitions.p2}} | {{clarity.transitions.p3}} | {{clarity.transitions.summary}} |
| 总结效果 | {{clarity.summary.p1}} | {{clarity.summary.p2}} | {{clarity.summary.p3}} | {{clarity.summary.summary}} |
| 节奏适当性 | {{clarity.pacing.p1}} | {{clarity.pacing.p2}} | {{clarity.pacing.p3}} | {{clarity.pacing.summary}} |

### 1.3 影响力数据

| 维度 | 参与者1 | 参与者2 | 参与者3 | 总结 |
|------|--------|--------|--------|------|
| 有用性 | {{impact.relevance.p1}} | {{impact.relevance.p2}} | {{impact.relevance.p3}} | {{impact.relevance.summary}} |
| 难度适当性 | {{impact.confidence.p1}} | {{impact.confidence.p2}} | {{impact.confidence.p3}} | {{impact.confidence.summary}} |
| 满意程度 | {{impact.satisfaction.p1}} | {{impact.satisfaction.p2}} | {{impact.satisfaction.p3}} | {{impact.satisfaction.summary}} |

### 1.4 可行性数据

| 维度 | 评估结果 |
|------|---------|
| 学习时间 | {{feasibility.time_required}} |
| 设施要求 | {{feasibility.facilities}} |
| 环境要求 | {{feasibility.environment}} |
| 学习者成熟度 | {{feasibility.learner_maturity}} |

### 1.5 学习者标注和评论

{{learner_marks}}

### 1.6 测试成绩

| 参与者 | 前测 | 后测 | 进步 |
|--------|------|------|------|
{{#each test_scores}}
| {{participant_id}} | {{pretest}} | {{posttest}} | {{improvement}} |
{{/each}}

### 1.7 需要修改的内容

| 模块 | 问题 | 建议 |
|------|------|------|
{{#each one_on_one_modifications}}
| {{module_affected}} | {{issue}} | {{recommendation}} |
{{/each}}

---

## 二、小组评价

### 2.1 参与者信息

- 参与者数量：{{participant_count}}
- 选择标准：{{participant_selection}}

### 2.2 测试成绩

| 统计量 | 前测 | 后测 |
|--------|------|------|
| 平均分 | {{pretest_stats.mean}} | {{posttest_stats.mean}} |
| 最高分 | {{pretest_stats.max}} | {{posttest_stats.max}} |
| 最低分 | {{pretest_stats.min}} | {{posttest_stats.min}} |
| 及格率 | {{pretest_stats.pass_rate}} | {{posttest_stats.pass_rate}} |

### 2.3 目标达成情况

| 目标编号 | 前测正确率 | 后测正确率 | 掌握人数 | 掌握率 |
|---------|-----------|-----------|---------|--------|
{{#each objective_achievement}}
| {{objective_id}} | {{pretest_rate}} | {{posttest_rate}} | {{mastered_count}} | {{mastery_rate}} |
{{/each}}

### 2.4 态度问卷结果

| 问题 | 选项A | 选项B | 选项C | 选项D |
|------|-------|-------|-------|-------|
{{#each attitude_survey}}
| {{question}} | {{option_a}} | {{option_b}} | {{option_c}} | {{option_d}} |
{{/each}}

### 2.5 学习时间

| 活动 | 预计时间 | 实际时间 | 差异 |
|------|---------|---------|------|
{{#each time_data}}
| {{activity}} | {{planned}} | {{actual}} | {{difference}} |
{{/each}}

### 2.6 学习者评论

{{learner_comments}}

### 2.7 需要修改的内容

| 模块 | 问题 | 建议 |
|------|------|------|
{{#each small_group_modifications}}
| {{module_affected}} | {{issue}} | {{recommendation}} |
{{/each}}

---

## 三、场景评价

### 3.1 评价环境

- 环境描述：{{environment}}
- 参与者数量：{{participant_count}}
- 设计者角色：{{designer_role}}

### 3.2 学习者成就

{{learner_achievement_data}}

### 3.3 学习者态度

{{learner_attitude_data}}

### 3.4 教师教学过程

{{teacher_process_data}}

### 3.5 资源使用情况

{{resource_data}}

### 3.6 需要修改的内容

| 模块 | 问题 | 建议 |
|------|------|------|
{{#each field_trial_modifications}}
| {{module_affected}} | {{issue}} | {{recommendation}} |
{{/each}}

---

## 四、总体结论

### 4.1 主要发现

{{main_findings}}

### 4.2 优势

{{strengths}}

### 4.3 不足

{{weaknesses}}

### 4.4 修改建议汇总

| 优先级 | 模块 | 问题 | 建议 | 理由 |
|--------|------|------|------|------|
{{#each all_modifications}}
| {{priority}} | {{module_affected}} | {{issue}} | {{recommendation}} | {{reason}} |
{{/each}}

---

## 五、下一步行动

| 行动 | 负责人 | 截止日期 | 状态 |
|------|--------|---------|------|
{{#each next_steps}}
| {{action}} | {{owner}} | {{deadline}} | {{status}} |
{{/each}}

---

*形成性评价基于 Dick & Carey 教学系统化设计模型*
*评价阶段：{{evaluation_stage}}*
*记录时间：{{recorded_at}}*
