# 模块间输入输出规范

## 1. 概述

本文档定义了 Dick & Carey 模型中每个模块的输入、输出数据格式，以及模块间的数据传递规则。所有模块间的数据交换必须遵循本规范。

## 2. 模块 I/O 定义

### 2.1 模块1：评价需求以确定教学目的

**输入数据：**
```json
{
  "performance_problem": "string — 绩效问题描述",
  "desired_state": "string — 期望状态",
  "current_state": "string — 当前状态",
  "gap": "number — 绩效差距（可量化时）",
  "organizational_context": "string — 组织背景",
  "available_resources": "string — 可用资源"
}
```

**输出数据：**
```json
{
  "instructional_goal": {
    "learner": "string — 学习者描述",
    "behavior": "string — 学习者能做什么",
    "context": "string — 应用环境",
    "tools": "string — 可用工具",
    "full_statement": "string — 完整目的陈述"
  },
  "sources": ["string — 目的依据列表"],
  "feasibility_check": {
    "management_acceptance": "boolean",
    "sufficient_resources": "boolean",
    "content_stability": "boolean",
    "learner_availability": "boolean"
  }
}
```

### 2.2 模块2：进行教学分析

**输入数据：**
```json
{
  "instructional_goal": "object — 从模块1输出的教学目的",
  "goal_classification": "enum — 言语信息|智慧技能|心智运动技能|态度"
}
```

**输出数据：**
```json
{
  "skill_graph": {
    "goal_steps": [
      {
        "step_id": "string — 步骤编号",
        "description": "string — 步骤描述",
        "learning_type": "enum — 学习类型",
        "substeps": ["object — 子步骤（递归结构）"]
      }
    ],
    "subordinate_skills": [
      {
        "skill_id": "string — 技能编号",
        "description": "string — 技能描述",
        "learning_type": "enum — 学习类型",
        "parent_step": "string — 父步骤编号",
        "level": "number — 层次级别"
      }
    ],
    "entry_skills": [
      {
        "skill_id": "string — 技能编号",
        "description": "string — 技能描述",
        "learning_type": "enum — 学习类型",
        "assumed_known": "boolean — 是否假设已知"
      }
    ],
    "analysis_method": "enum — 层次法|簇分析法|综合技术"
  }
}
```

### 2.3 模块3：分析学习者和环境

**输入数据：**
```json
{
  "skill_graph": "object — 从模块2输出的技能流图",
  "target_population": "string — 目标人群描述"
}
```

**输出数据：**
```json
{
  "learner_analysis": {
    "entry_skills": "string — 入门技能评估",
    "prior_knowledge": "string — 领域已有知识",
    "attitudes": "string — 对内容和传递系统的态度",
    "motivation": {
      "attention": "string — 注意力评估",
      "relevance": "string — 关联性评估",
      "confidence": "string — 自信心评估",
      "satisfaction": "string — 满足感评估"
    },
    "ability_level": "string — 学业能力水平",
    "learning_preferences": "string — 学习偏好",
    "institution_attitude": "string — 对机构态度",
    "group_characteristics": "string — 群体特征"
  },
  "performance_context": {
    "physical_conditions": "string — 物理条件",
    "social_environment": "string — 社会环境",
    "management_support": "string — 管理支持",
    "skill_relevance": "string — 技能相关性"
  },
  "learning_context": {
    "current_state": "string — 现状",
    "desired_conditions": "string — 应有条件",
    "facility_match": "string — 设施匹配度",
    "simulation_feasibility": "string — 模拟可行性"
  }
}
```

### 2.4 模块4：编写绩效目标

**输入数据：**
```json
{
  "skill_graph": "object — 从模块2输出的技能流图",
  "learner_analysis": "object — 从模块3输出的学习者分析",
  "performance_context": "object — 从模块3输出的应用环境分析"
}
```

**输出数据：**
```json
{
  "terminal_objective": {
    "condition": "string — 条件",
    "behavior": "string — 行为",
    "criteria": "string — 标准",
    "full_statement": "string — 完整目标陈述"
  },
  "subordinate_objectives": [
    {
      "objective_id": "string — 目标编号",
      "skill_id": "string — 对应技能编号",
      "condition": "string — 条件",
      "behavior": "string — 行为",
      "criteria": "string — 标准",
      "full_statement": "string — 完整目标陈述"
    }
  ]
}
```

### 2.5 模块5：开发评价方案

**输入数据：**
```json
{
  "terminal_objective": "object — 从模块4输出的学期目标",
  "subordinate_objectives": ["object — 从模块4输出的从属目标"]
}
```

**输出数据：**
```json
{
  "entry_behaviors_test": {
    "items": ["object — 测试题目"],
    "mastery_criteria": "string — 掌握标准"
  },
  "pretest": {
    "items": ["object — 测试题目"],
    "mastery_criteria": "string — 掌握标准"
  },
  "practice_tests": ["object — 练习测试"],
  "posttest": {
    "items": ["object — 测试题目"],
    "mastery_criteria": "string — 掌握标准"
  },
  "performance_scales": ["object — 行为表现量表"],
  "portfolio_plan": "string — 学习档案计划"
}
```

### 2.6 模块6：开发教学策略

**输入数据：**
```json
{
  "terminal_objective": "object — 学期目标",
  "subordinate_objectives": ["object — 从属目标"],
  "learner_analysis": "object — 学习者分析",
  "learning_context": "object — 学习环境分析",
  "assessment_plan": "object — 评价方案"
}
```

**输出数据：**
```json
{
  "content_sequence": "string — 内容顺序安排",
  "content_clustering": "string — 内容分块说明",
  "preinstructional_activities": {
    "motivation": "string — 激励策略",
    "objectives": "string — 目标说明策略",
    "prerequisites": "string — 预备技能评估策略"
  },
  "content_presentation": [
    {
      "objective_id": "string — 目标编号",
      "content": "string — 呈现内容",
      "examples": ["string — 例子"],
      "media": "string — 媒体选择"
    }
  ],
  "learner_participation": [
    {
      "objective_id": "string — 目标编号",
      "practice_activities": ["string — 练习活动"],
      "feedback_mechanism": "string — 反馈机制"
    }
  ],
  "assessment_strategy": "string — 评测策略",
  "enhancement_activities": {
    "memory_aids": ["string — 记忆辅助"],
    "transfer_considerations": "string — 迁移考虑"
  },
  "student_grouping": "string — 学生分组说明",
  "media_selection": "string — 媒体选择说明",
  "delivery_system": "string — 传递系统说明"
}
```

### 2.7 模块7：开发教学材料

**输入数据：**
```json
{
  "instructional_strategy": "object — 从模块6输出的教学策略",
  "terminal_objective": "object — 学期目标",
  "subordinate_objectives": ["object — 从属目标"],
  "learner_analysis": "object — 学习者分析"
}
```

**输出数据：**
```json
{
  "instructional_materials": [
    {
      "material_id": "string — 材料编号",
      "type": "enum — 讲义|练习册|多媒体|网页|视频",
      "target_objective": "string — 目标编号",
      "content": "string — 材料内容",
      "media_format": "string — 媒体格式"
    }
  ],
  "assessment_materials": "object — 评测材料",
  "instructor_guide": "string — 教师手册内容"
}
```

### 2.8 模块8：设计和实施形成性评价

**输入数据：**
```json
{
  "instructional_materials": ["object — 从模块7输出的教学材料"],
  "assessment_plan": "object — 评价方案",
  "learner_analysis": "object — 学习者分析"
}
```

**输出数据：**
```json
{
  "one_on_one_evaluation": {
    "participants": ["object — 参与学习者"],
    "data_collected": {
      "clarity": "string — 清晰度数据",
      "impact": "string — 影响力数据",
      "feasibility": "string — 可行性数据"
    },
    "modifications_needed": ["string — 需要修改的内容"]
  },
  "small_group_evaluation": {
    "participants": ["object — 参与学习者"],
    "data_collected": {
      "pretest_scores": ["number — 前测成绩"],
      "posttest_scores": ["number — 后测成绩"],
      "attitude_survey": "string — 态度问卷结果",
      "time_on_task": "string — 学习时间",
      "comments": ["string — 学习者评论"]
    },
    "modifications_needed": ["string — 需要修改的内容"]
  },
  "field_trial": {
    "participants": ["object — 参与学习者"],
    "data_collected": "string — 实地试验数据",
    "modifications_needed": ["string — 需要修改的内容"]
  }
}
```

### 2.9 模块9：修改教学

**输入数据：**
```json
{
  "formative_evaluation_data": "object — 从模块8输出的形成性评价数据",
  "current_project": "object — 当前项目完整状态"
}
```

**输出数据：**
```json
{
  "analysis_results": {
    "entry_skills_issues": "string — 入门技能问题",
    "sequencing_issues": "string — 教学顺序问题",
    "problematic_objectives": ["string — 有问题的目标"],
    "strategy_issues": "string — 策略问题",
    "material_issues": "string — 材料问题"
  },
  "modifications": [
    {
      "module_affected": "string — 受影响的模块",
      "modification_type": "string — 修改类型",
      "description": "string — 修改描述",
      "reason": "string — 修改理由",
      "impact_on_other_modules": ["string — 对其他模块的影响"]
    }
  ],
  "revision_record": "string — 修改记录"
}
```

## 3. 数据传递规则

### 3.1 前向传递
- 每个模块的输出是下一个模块的输入
- 数据格式必须符合 Schema 定义
- 数据必须通过质量门禁才能传递

### 3.2 反馈传递
- 形成性评价数据可反馈到任何前序模块
- 反馈传递必须记录修改原因和影响
- 反馈传递后必须重新验证一致性

### 3.3 数据完整性
- 所有必填字段必须提供
- 可选字段应尽可能提供
- 数据来源必须标注

## 4. 一致性检查点

| 检查点 | 检查内容 | 不一致时的处理 |
|--------|---------|--------------|
| 目的→分析 | 分析是否覆盖目的中的所有行为 | 补充分析步骤 |
| 分析→目标 | 目标是否覆盖分析中的所有技能 | 补充目标 |
| 目标→评价 | 评价是否能测量所有目标 | 补充评价证据 |
| 评价→策略 | 策略是否支持所有评价活动 | 调整策略 |
| 策略→材料 | 材料是否实现所有策略成分 | 补充材料 |
| 材料→形成性评价 | 评价是否收集了必要数据 | 调整评价方案 |
