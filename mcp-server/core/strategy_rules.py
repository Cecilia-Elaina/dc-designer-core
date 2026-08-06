"""
Instructional strategy rules based on Dick-Carey model.
Defines learning components, time allocation, assessment embedding,
learning type strategies, and pre-instructional activity templates.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Five learning components (Gagne's instructional events)
FIVE_COMPONENTS = [
    "pre_instructional",
    "content_presentation",
    "learner_participation",
    "assessment",
    "follow_through",
]

# Time allocation rules for different durations (minutes)
TIME_RULES = {
    40: {
        "pre": 5,
        "presentation": 12,
        "practice": 13,
        "assessment": 8,
        "follow": 2,
    },
    45: {
        "pre": 5,
        "presentation": 13,
        "practice": 15,
        "assessment": 8,
        "follow": 4,
    },
    90: {
        "pre": 8,
        "presentation": 25,
        "practice": 35,
        "assessment": 15,
        "follow": 7,
    },
}

# Assessment embedding rules
ASSESSMENT_EMBEDDING = {
    "entry_behavior_test": {
        "timing": "教学前活动末尾",
        "purpose": "检测入门技能",
    },
    "pretest": {
        "timing": "教学前活动末尾",
        "purpose": "了解已有知识",
    },
    "practice": {
        "timing": "学习者参与阶段",
        "purpose": "形成性反馈",
    },
    "posttest": {
        "timing": "教学结束前",
        "purpose": "总结性评价",
    },
}

# Learning result type specific strategies (Gagne's five categories)
LEARNING_TYPE_STRATEGIES = {
    "verbal_information": {
        "presentation": "关联已有知识，使用精细加工策略，提供记忆线索",
        "practice": "复述、列举、填空、概念图",
        "assessment": "客观题、简答题",
    },
    "intellectual_skill": {
        "presentation": "层次递进，从简单到复杂，提供正例和反例",
        "practice": "问题解决、案例分析、情境任务",
        "assessment": "情境题、表现性任务、作品",
    },
    "psychomotor_skill": {
        "presentation": "示范操作，分解步骤，逐步练习",
        "practice": "模仿练习→独立操作→熟练自动化",
        "assessment": "操作核查表、现场表现",
    },
    "attitude": {
        "presentation": "榜样示范，情境体验，价值讨论",
        "practice": "角色扮演、情境选择、反思日记",
        "assessment": "情境选择、行为观察、态度量表",
    },
}

# Pre-instructional activity templates
PRE_INSTRUCTIONAL = {
    "motivation": {
        "arcs_attention": "使用对比、生活情境、问题悬念引起注意",
        "arcs_relevance": "说明学习内容与学生生活的关联",
        "arcs_confidence": "告知学习目标，让学生知道能做到",
        "arcs_satisfaction": "预告学习成果和获得认可的方式",
    },
    "objectives_overview": "清晰呈现本节课的学习目标，让学生知道学完后能做什么",
    "entry_skill_activation": "激活与新内容相关的已有知识和技能，建立新旧知识联系",
}

# Objective dependency graph patterns
OBJECTIVE_SEQUENCING_RULES = {
    "prerequisite_first": "前置目标必须在后续目标之前",
    "simple_to_complex": "简单目标在前，复杂目标在后",
    "concrete_to_abstract": "具体目标在前，抽象目标在后",
    "high_frequency_first": "高频使用的目标优先安排",
}

# Quality check criteria
QUALITY_CRITERIA = {
    "five_components": {
        "name": "五项教学活动完整性",
        "description": "是否包含pre_instructional, content_presentation, learner_participation, assessment, follow_through",
        "required": True,
    },
    "target_coverage": {
        "name": "目标覆盖率",
        "description": "每个教学目标是否都有对应的教学活动",
        "required": True,
    },
    "assessment_integration": {
        "name": "评估嵌入",
        "description": "评估是否贯穿教学各阶段",
        "required": True,
    },
    "time_allocation": {
        "name": "时间分配合理性",
        "description": "各环节时间总和是否等于课时长度",
        "required": True,
    },
}

# Lesson flow template
LESSON_FLOW_COLUMNS = [
    "时间段",
    "教学环节",
    "具体活动",
    "教师行为",
    "学生行为",
    "评估方式",
    "媒体/材料",
    "时间（分钟）",
]
