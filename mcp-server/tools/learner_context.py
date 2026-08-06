# -*- coding: utf-8 -*-
"""
Learner context analysis tools.
Analyzes learner characteristics, learning environment,
and performance environment to generate strategy implications.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from core.context_rules import (
    CONSTRAINT_RULES,
    IMPLICATION_TEMPLATES,
    ARCS_STRATEGIES,
    GROUPING_STRATEGIES,
)


def _classify_motivation(motivation_text: str) -> str:
    """Classify motivation level from text description."""
    if not motivation_text:
        return "unknown"
    low_keywords = ["不感兴趣", "动机低", "缺乏兴趣", "不愿意", "厌倦"]
    high_keywords = ["感兴趣", "积极性高", "动机强", "热情", "期待"]
    text = motivation_text.lower()
    for kw in low_keywords:
        if kw in text:
            return "low"
    for kw in high_keywords:
        if kw in text:
            return "high"
    return "moderate"


def _assess_entry_skills(entry_skills: list) -> str:
    """Assess entry skills strength."""
    if not entry_skills:
        return "unknown"
    if len(entry_skills) >= 3:
        return "sufficient"
    if len(entry_skills) == 1:
        return "weak"
    return "moderate"


def _assess_data_completeness(fields_checked: dict) -> float:
    """Calculate data completeness ratio."""
    if not fields_checked:
        return 0.0
    filled = sum(1 for v in fields_checked.values() if v)
    return round(filled / len(fields_checked), 2)


def _format_difficulties(difficulties: list) -> str:
    """Format common difficulties into readable text."""
    if not difficulties:
        return ""
    if len(difficulties) == 1:
        return difficulties[0]
    return "、".join(difficulties[:-1]) + "和" + difficulties[-1]


def analyze_learner_profile(input_data: dict) -> dict:
    """
    Analyze learner characteristics from input data.

    Analyzes 8 dimensions:
    1. entry_skills - prior skills level
    2. prior_knowledge - existing knowledge
    3. attitude_content - attitude toward content
    4. attitude_delivery - attitude toward delivery
    5. motivation - motivation level
    6. ability_level - general ability
    7. learning_preferences - preferred learning modes
    8. group_characteristics - group dynamics

    Returns learner_profile with requires_teacher_confirmation
    and data_completeness.
    """
    entry_skills = input_data.get("entry_skills", [])
    prior_knowledge = input_data.get("prior_knowledge", "")
    attitude_content = input_data.get("attitude_content", "")
    attitude_delivery = input_data.get("attitude_delivery", "")
    motivation = input_data.get("motivation", "")
    ability_level = input_data.get("ability_level", "")
    learning_preferences = input_data.get("learning_preferences", [])
    group_characteristics = input_data.get("group_characteristics", {})
    common_difficulties = input_data.get("common_difficulties", [])
    class_size = input_data.get("class_size", None)

    motivation_level = _classify_motivation(motivation)
    entry_skills_assessment = _assess_entry_skills(entry_skills)

    motivation_strategies = []
    if motivation_level == "low":
        motivation_strategies.extend(ARCS_STRATEGIES["attention"][:2])
        motivation_strategies.extend(ARCS_STRATEGIES["relevance"][:2])
    elif motivation_level == "high":
        motivation_strategies.extend(ARCS_STRATEGIES["relevance"][:2])
        motivation_strategies.extend(ARCS_STRATEGIES["confidence"][:2])
    else:
        motivation_strategies.extend(ARCS_STRATEGIES["attention"][:1])
        motivation_strategies.extend(ARCS_STRATEGIES["relevance"][:1])
        motivation_strategies.extend(ARCS_STRATEGIES["confidence"][:1])

    grouping = "whole_class"
    if class_size and class_size > 30:
        grouping = "small_group"
    elif class_size and class_size <= 15:
        grouping = "pairs"

    fields_checked = {
        "entry_skills": bool(entry_skills),
        "prior_knowledge": bool(prior_knowledge),
        "motivation": bool(motivation),
        "learning_preferences": bool(learning_preferences),
        "common_difficulties": bool(common_difficulties),
        "class_size": class_size is not None,
        "attitude_content": bool(attitude_content),
        "attitude_delivery": bool(attitude_delivery),
        "ability_level": bool(ability_level),
        "group_characteristics": bool(group_characteristics),
    }
    data_completeness = _assess_data_completeness(fields_checked)
    requires_confirmation = data_completeness < 0.7

    implications = []
    if entry_skills_assessment == "weak":
        implications.append(IMPLICATION_TEMPLATES["entry_skills_weak"])
    if motivation_level == "low":
        implications.append(IMPLICATION_TEMPLATES["motivation_low"])
    elif motivation_level == "high":
        implications.append(IMPLICATION_TEMPLATES["motivation_high"])
    if common_difficulties:
        diff_text = _format_difficulties(common_difficulties)
        implications.append(
            IMPLICATION_TEMPLATES["common_difficulties"].format(difficulties=diff_text)
        )

    profile = {
        "entry_skills": {
            "level": entry_skills_assessment,
            "items": entry_skills,
            "note": (
                "入门技能较薄弱，需在教学前增加复习环节"
                if entry_skills_assessment == "weak"
                else "入门技能基本满足学习需求"
            ),
        },
        "prior_knowledge": {
            "description": prior_knowledge or "未提供",
            "status": "已知" if prior_knowledge else "待确认",
        },
        "attitude_content": {
            "description": attitude_content or "未提供",
            "status": "已知" if attitude_content else "待确认",
        },
        "attitude_delivery": {
            "description": attitude_delivery or "未提供",
            "status": "已知" if attitude_delivery else "待确认",
        },
        "motivation": {
            "level": motivation_level,
            "description": motivation or "未提供",
            "strategies": motivation_strategies,
        },
        "ability_level": {
            "description": ability_level or "中等",
            "status": "已知" if ability_level else "待确认",
        },
        "learning_preferences": {
            "preferences": learning_preferences or ["情境任务", "小组讨论"],
            "grouping_strategy": GROUPING_STRATEGIES.get(grouping, "全班讨论"),
        },
        "group_characteristics": {
            "class_size": class_size,
            "grouping": grouping,
            "details": group_characteristics or {},
        },
        "common_difficulties": common_difficulties,
        "implications": implications,
        "requires_teacher_confirmation": requires_confirmation,
        "data_completeness": data_completeness,
    }

    return profile


def analyze_learning_context(input_data: dict) -> dict:
    """
    Analyze learning environment (where instruction happens).

    Returns learning_context with constraints, supports, time_allocation.
    """
    class_duration = input_data.get("class_duration", 45)
    class_size = input_data.get("class_size", 40)
    available_media = input_data.get("available_media", [])
    devices = input_data.get("devices", "")
    network = input_data.get("network", "")
    classroom_layout = input_data.get("classroom_layout", "")
    constraints_raw = input_data.get("constraints", [])
    supports_raw = input_data.get("supports", [])

    constraints = list(constraints_raw) if constraints_raw else []

    if class_duration <= CONSTRAINT_RULES["short_duration"]["threshold"]:
        constraints.append(CONSTRAINT_RULES["short_duration"]["implication"])

    if class_size >= CONSTRAINT_RULES["large_class"]["threshold"]:
        constraints.append(CONSTRAINT_RULES["large_class"]["implication"])

    devices_text = str(devices)
    no_device_detected = False
    for kw in CONSTRAINT_RULES["no_individual_devices"]["keywords"]:
        if kw in devices_text:
            no_device_detected = True
            break
    if no_device_detected:
        constraints.append(CONSTRAINT_RULES["no_individual_devices"]["implication"])

    network_text = str(network)
    unstable_detected = False
    for kw in CONSTRAINT_RULES["unstable_network"]["keywords"]:
        if kw in network_text:
            unstable_detected = True
            break
    if unstable_detected:
        constraints.append(CONSTRAINT_RULES["unstable_network"]["implication"])

    supports = list(supports_raw) if supports_raw else []
    if available_media:
        for m in available_media:
            if m not in supports:
                supports.append("可用媒体：" + m)
    if classroom_layout:
        supports.append("教室布局：" + classroom_layout)

    duration_key = class_duration
    if duration_key not in [40, 45, 90]:
        if duration_key <= 30:
            duration_key = 40
        elif duration_key <= 60:
            duration_key = 45
        else:
            duration_key = 90

    from core.strategy_rules import TIME_RULES

    time_allocation = TIME_RULES.get(duration_key, TIME_RULES[45])
    time_allocation["total"] = class_duration

    implications = []
    if no_device_detected:
        implications.append(IMPLICATION_TEMPLATES["no_devices"])
    if class_duration <= 30:
        max_min = class_duration // 5
        implications.append(
            IMPLICATION_TEMPLATES["short_class"].format(
                duration=class_duration, max_minutes=max_min
            )
        )

    fields_checked = {
        "class_duration": class_duration is not None,
        "class_size": class_size is not None,
        "available_media": bool(available_media),
        "devices": bool(devices),
        "network": bool(network),
        "classroom_layout": bool(classroom_layout),
    }
    data_completeness = _assess_data_completeness(fields_checked)

    context = {
        "class_duration": class_duration,
        "class_size": class_size,
        "constraints": constraints,
        "supports": supports,
        "time_allocation": time_allocation,
        "devices": {
            "description": devices or "未提供",
            "available": not no_device_detected,
        },
        "network": {
            "description": network or "未提供",
            "stable": not unstable_detected,
        },
        "classroom_layout": classroom_layout or "未提供",
        "available_media": available_media,
        "implications": implications,
        "requires_teacher_confirmation": data_completeness < 0.5,
        "data_completeness": data_completeness,
    }

    return context


def analyze_performance_context(input_data: dict) -> dict:
    """
    Analyze performance environment (where skills are applied).

    Returns performance_context with transfer_risks, transfer_supports.
    """
    use_environment = input_data.get("use_environment", "")
    expected_transfer = input_data.get("expected_transfer", "")
    real_world_tasks = input_data.get("real_world_tasks", [])
    similarity_to_learning_context = input_data.get(
        "similarity_to_learning_context", "medium"
    )

    transfer_risks = []
    transfer_supports = []

    if similarity_to_learning_context == "low":
        transfer_risks.append(IMPLICATION_TEMPLATES["transfer_low_similarity"])
        transfer_supports.append("设计多种应用情境，帮助学生建立迁移桥梁")

    if not real_world_tasks:
        transfer_risks.append("缺少具体的真实任务描述，迁移设计缺乏依据")
    else:
        transfer_supports.append(
            f"已识别{len(real_world_tasks)}个真实任务可用于迁移练习"
        )

    if use_environment:
        transfer_supports.append(f"应用环境明确：{use_environment}")
    else:
        transfer_risks.append("应用环境未明确，需教师确认")

    if expected_transfer:
        transfer_supports.append(f"预期迁移行为：{expected_transfer}")

    fields_checked = {
        "use_environment": bool(use_environment),
        "expected_transfer": bool(expected_transfer),
        "real_world_tasks": bool(real_world_tasks),
        "similarity_to_learning_context": similarity_to_learning_context != "medium",
    }
    data_completeness = _assess_data_completeness(fields_checked)

    context = {
        "use_environment": use_environment or "未提供",
        "expected_transfer": expected_transfer or "未提供",
        "real_world_tasks": real_world_tasks,
        "similarity_to_learning_context": similarity_to_learning_context,
        "transfer_risks": transfer_risks,
        "transfer_supports": transfer_supports,
        "requires_teacher_confirmation": data_completeness < 0.5,
        "data_completeness": data_completeness,
    }

    return context


def generate_context_implications(
    learner_profile: dict,
    learning_context: dict,
    performance_context: dict,
) -> dict:
    """
    Generate strategy implications from all three contexts.

    Returns strategy_implications list and data_completeness flag.
    """
    implications = []

    if learner_profile.get("implications"):
        for imp in learner_profile["implications"]:
            implications.append({"source": "learner_profile", "implication": imp})

    if learning_context.get("implications"):
        for imp in learning_context["implications"]:
            implications.append({"source": "learning_context", "implication": imp})

    if performance_context.get("transfer_risks"):
        for risk in performance_context["transfer_risks"]:
            implications.append({"source": "performance_context", "implication": risk})
    if performance_context.get("transfer_supports"):
        for support in performance_context["transfer_supports"]:
            implications.append({"source": "performance_context", "implication": support})

    entry_skills = learner_profile.get("entry_skills", [])
    if isinstance(entry_skills, list) and len(entry_skills) == 0:
        implications.append({
            "source": "learner_profile",
            "implication": IMPLICATION_TEMPLATES["entry_skills_weak"],
        })

    if learning_context.get("devices", {}).get("available") is False:
        implications.append({
            "source": "learning_context",
            "implication": IMPLICATION_TEMPLATES["no_devices"],
        })

    completeness_scores = [
        learner_profile.get("data_completeness", 0),
        learning_context.get("data_completeness", 0),
        performance_context.get("data_completeness", 0),
    ]
    overall_completeness = round(sum(completeness_scores) / len(completeness_scores), 2)

    return {
        "strategy_implications": implications,
        "data_completeness": overall_completeness,
        "requires_teacher_confirmation": overall_completeness < 0.6,
    }
