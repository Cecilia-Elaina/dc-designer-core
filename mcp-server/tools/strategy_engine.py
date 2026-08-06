# -*- coding: utf-8 -*-
"""
Instructional strategy engine based on Dick-Carey model.
Generates complete instructional strategies including objective sequencing,
lesson segmentation, and all five instructional components.
"""

import sys
import os
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from core.strategy_rules import (
    FIVE_COMPONENTS,
    TIME_RULES,
    ASSESSMENT_EMBEDDING,
    LEARNING_TYPE_STRATEGIES,
    PRE_INSTRUCTIONAL,
    QUALITY_CRITERIA,
    LESSON_FLOW_COLUMNS,
)
from core.context_rules import (
    TOPIC_STRATEGY_TEMPLATES,
    ARCS_STRATEGIES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_time_allocation(class_duration: int) -> dict:
    """Get time allocation for given duration, finding nearest match."""
    if class_duration in TIME_RULES:
        return dict(TIME_RULES[class_duration])
    available = sorted(TIME_RULES.keys())
    for d in available:
        if class_duration <= d:
            return dict(TIME_RULES[d])
    return dict(TIME_RULES[available[-1]])


def _detect_learning_type(project: dict) -> str:
    """Detect the primary learning result type from the project goal."""
    goal = project.get("goal", {})
    behavior = goal.get("behavior", "")

    psychomotor_kw = ["操作", "使用工具", "动手", "制作"]
    for kw in psychomotor_kw:
        if kw in behavior:
            return "psychomotor_skill"

    attitude_kw = ["态度", "价值观", "意识", "习惯"]
    for kw in attitude_kw:
        if kw in behavior:
            return "attitude"

    intellectual_kw = ["分析", "比较", "判断", "解决问题", "设计", "描述"]
    for kw in intellectual_kw:
        if kw in behavior:
            return "intellectual_skill"

    verbal_kw = ["知道", "了解", "说出", "列举"]
    for kw in verbal_kw:
        if kw in behavior:
            return "verbal_information"

    return "intellectual_skill"


def _detect_topic(project: dict) -> str:
    """Detect topic category from project metadata and goal."""
    meta = project.get("metadata", {})
    goal = project.get("goal", {})
    subject = meta.get("subject", "")
    behavior = goal.get("behavior", "")

    topic_text = " ".join([str(meta.get("topic", "")), str(project.get("topic", "")), behavior]).lower()
    if any(token in topic_text for token in ("分支", "if", "elif", "else", "条件判断")):
        return "branch"
    if any(token in topic_text for token in ("循环", "for", "while", "迭代", "重复")):
        return "loop"
    if "信息科技" in subject or "信息技术" in subject or "算法" in behavior or "程序" in behavior:
        return "algorithm"
    return "general"


# ---------------------------------------------------------------------------
# Objective sequencing
# ---------------------------------------------------------------------------

def sequence_objectives(
    objectives: list,
    skill_graph: dict,
    context: dict | None = None,
) -> dict:
    """
    Sequence objectives based on skill graph dependency and context.

    Args:
        objectives: list of objective dicts with 'id', 'description', 'type'.
        skill_graph: dict mapping objective_id -> list of prerequisite ids.
        context: optional dict with ordering preferences.

    Returns:
        dict with ordered objectives and sequencing rationale.
    """
    if not objectives:
        return {"ordered": [], "rationale": "无目标需要排序"}

    id_to_obj: dict[str, dict] = {}
    for i, o in enumerate(objectives):
        oid = o.get("id", f"obj_{i}")
        id_to_obj[oid] = o

    prereqs = skill_graph or {}

    # Build adjacency lists and in-degree
    adjacency: dict[str, list[str]] = {oid: [] for oid in id_to_obj}
    in_degree: dict[str, int] = {oid: 0 for oid in id_to_obj}

    for oid, deps in prereqs.items():
        if oid not in id_to_obj:
            continue
        for dep in deps:
            if dep in id_to_obj:
                adjacency[dep].append(oid)
                in_degree[oid] += 1

    # Kahn's algorithm for topological sort
    queue = [oid for oid, deg in in_degree.items() if deg == 0]
    ordered: list[str] = []
    original_order = list(id_to_obj.keys())

    while queue:
        queue.sort(key=lambda x: original_order.index(x) if x in original_order else 0)
        current = queue.pop(0)
        ordered.append(current)
        for neighbor in adjacency[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Handle cycles or unreachable nodes
    remaining = [oid for oid in id_to_obj if oid not in ordered]
    ordered.extend(remaining)

    # Context adjustments
    rationale_parts = ["基于技能依赖图排序"]
    if context:
        pref = context.get("preference", "")
        if pref == "simple_to_complex":
            rationale_parts.append("兼顾由简到繁原则")
        elif pref == "high_frequency_first":
            rationale_parts.append("优先安排高频技能目标")

    ordered_objs = [id_to_obj[oid] for oid in ordered if oid in id_to_obj]

    return {
        "ordered": ordered_objs,
        "rationale": "，".join(rationale_parts),
        "total_objectives": len(objectives),
    }


# ---------------------------------------------------------------------------
# Lesson segmentation
# ---------------------------------------------------------------------------

def group_objectives_into_lesson_segments(
    objectives: list,
    class_duration: int | None = None,
) -> dict:
    """
    Group objectives into lesson segments with time allocation.

    Args:
        objectives: list of objective dicts.
        class_duration: total lesson duration in minutes.

    Returns:
        dict with segments, time_allocation, and coverage info.
    """
    duration = class_duration or 45
    time_alloc = _get_time_allocation(duration)

    total = len(objectives)
    if total == 0:
        return {
            "segments": [],
            "time_allocation": time_alloc,
            "coverage": "无目标需要分组",
        }

    n_presentation = max(1, total // 2)
    n_practice = total - n_presentation

    segments = [
        {
            "name": "content_presentation",
            "objectives": objectives[:n_presentation],
            "time_minutes": time_alloc.get("presentation", 13),
            "rationale": "新知识讲解与示范",
        },
        {
            "name": "learner_participation",
            "objectives": objectives[n_presentation:],
            "time_minutes": time_alloc.get("practice", 15),
            "rationale": "练习与应用",
        },
    ]

    return {
        "segments": segments,
        "time_allocation": time_alloc,
        "coverage": f"已将{total}个目标分配到{len(segments)}个教学段",
    }


# ---------------------------------------------------------------------------
# Component generators
# ---------------------------------------------------------------------------

def generate_pre_instructional_activities(project: dict) -> dict:
    """Generate motivation, objectives overview, entry skill activation."""
    topic = _detect_topic(project)
    goal = project.get("goal", {})
    learner_ctx = project.get("learner_context_input", {})

    topic_template = TOPIC_STRATEGY_TEMPLATES.get(topic, {}).get(
        "pre_instructional", {}
    )

    motivation_strategies: list[dict] = []
    if topic_template.get("motivation"):
        motivation_strategies.append(
            {
                "activity": topic_template["motivation"],
                "arcs_component": "attention_relevance",
                "duration_minutes": 2,
            }
        )
    else:
        motivation_strategies.append(
            {
                "activity": "使用生活情境引入，引起学生注意和兴趣",
                "arcs_component": "attention",
                "duration_minutes": 1,
            }
        )
        motivation_strategies.append(
            {
                "activity": "说明学习内容与学生生活的关联",
                "arcs_component": "relevance",
                "duration_minutes": 1,
            }
        )

    full_statement = goal.get("full_statement", goal.get("behavior", ""))
    objectives_overview = topic_template.get(
        "objectives_overview",
        f"清晰呈现本节课的学习目标：{full_statement}",
    )

    entry_skills = learner_ctx.get("entry_skills", [])
    if topic_template.get("entry_skill_activation"):
        entry_skill_text = topic_template["entry_skill_activation"]
    elif entry_skills:
        skill_list = "、".join(entry_skills[:3])
        entry_skill_text = f"激活已有技能：{skill_list}"
    else:
        entry_skill_text = PRE_INSTRUCTIONAL["entry_skill_activation"]

    confidence_activity = "告知学习目标，让学生知道学完后能做什么，建立学习信心"

    return {
        "motivation": {
            "strategies": motivation_strategies,
            "total_duration_minutes": 2,
        },
        "objectives_overview": {
            "activity": objectives_overview,
            "duration_minutes": 2,
        },
        "entry_skill_activation": {
            "activity": entry_skill_text,
            "duration_minutes": 1,
        },
        "confidence_building": {
            "activity": confidence_activity,
            "duration_minutes": 0.5,
        },
        "total_duration_minutes": 5,
    }


def generate_content_presentation(project: dict) -> dict:
    """Generate content presentation with examples, non-examples, media."""
    topic = _detect_topic(project)
    learning_type = _detect_learning_type(project)
    goal = project.get("goal", {})
    learner_ctx = project.get("learner_context_input", {})

    type_strategy = LEARNING_TYPE_STRATEGIES.get(
        learning_type, LEARNING_TYPE_STRATEGIES["intellectual_skill"]
    )

    topic_phases = TOPIC_STRATEGY_TEMPLATES.get(topic, {}).get(
        "content_presentation", []
    )

    phases: list[dict] = []
    media = learner_ctx.get("available_media", ["黑板", "投影"])

    if topic_phases:
        for tp in topic_phases:
            phases.append(
                {
                    "phase": tp["phase"],
                    "activity": tp["activity"],
                    "duration_minutes": tp["duration"],
                    "teacher_behavior": "讲解、演示、引导",
                    "student_behavior": "观察、思考、记录",
                    "media": media,
                }
            )
    else:
        behavior = goal.get("behavior", "完成学习目标")
        phases.append(
            {
                "phase": "导入",
                "activity": "通过生活情境引入，建立学习需求",
                "duration_minutes": 3,
                "teacher_behavior": "提问、引导讨论",
                "student_behavior": "思考、回答",
                "media": media,
            }
        )
        phases.append(
            {
                "phase": "概念讲解",
                "activity": f"讲解核心概念和{type_strategy['presentation']}",
                "duration_minutes": 5,
                "teacher_behavior": "讲解、举例",
                "student_behavior": "听讲、笔记",
                "media": media,
            }
        )
        phases.append(
            {
                "phase": "范例演示",
                "activity": f"教师示范{behavior}的方法和过程",
                "duration_minutes": 5,
                "teacher_behavior": "示范、解说",
                "student_behavior": "观察、模仿",
                "media": media,
            }
        )

    total_duration = sum(p["duration_minutes"] for p in phases)

    return {
        "phases": phases,
        "learning_type": learning_type,
        "type_strategy": type_strategy["presentation"],
        "total_duration_minutes": total_duration,
    }


def generate_learner_participation(project: dict) -> dict:
    """Generate practice activities, exercises, feedback mechanisms."""
    topic = _detect_topic(project)
    learning_type = _detect_learning_type(project)
    goal = project.get("goal", {})
    learner_ctx = project.get("learner_context_input", {})

    type_strategy = LEARNING_TYPE_STRATEGIES.get(
        learning_type, LEARNING_TYPE_STRATEGIES["intellectual_skill"]
    )

    topic_participation = TOPIC_STRATEGY_TEMPLATES.get(topic, {}).get(
        "learner_participation", []
    )

    common_difficulties = learner_ctx.get("common_difficulties", [])
    class_size_raw = learner_ctx.get("class_size", 0)
    try:
        class_size = int(class_size_raw or 0)
    except (TypeError, ValueError):
        # An omitted class size is a data gap, not a reason to invent a
        # number. Use zero only to keep the renderer deterministic.
        class_size = 0

    phases: list[dict] = []

    if topic_participation:
        for tp in topic_participation:
            phases.append(
                {
                    "phase": tp["phase"],
                    "activity": tp["activity"],
                    "duration_minutes": tp["duration"],
                    "grouping": "小组协作" if class_size > 30 else "结对学习",
                    "teacher_behavior": "巡视、指导、收集反馈",
                    "student_behavior": "合作、讨论、练习",
                    "feedback": "组间互评",
                }
            )
    else:
        behavior = goal.get("behavior", "完成练习")
        phases.append(
            {
                "phase": "独立练习",
                "activity": f"学生独立{behavior}，教师巡视指导",
                "duration_minutes": 8,
                "grouping": "个别学习",
                "teacher_behavior": "巡视、个别指导",
                "student_behavior": "独立完成任务",
                "feedback": "即时反馈",
            }
        )
        phases.append(
            {
                "phase": "合作练习",
                "activity": "小组合作完成拓展任务",
                "duration_minutes": 7,
                "grouping": "小组协作",
                "teacher_behavior": "参与讨论、引导",
                "student_behavior": "讨论、合作",
                "feedback": "同伴互评",
            }
        )

    differentiation: list[dict] = []
    if common_difficulties:
        for diff in common_difficulties:
            differentiation.append(
                {
                    "difficulty": diff,
                    "support_strategy": f"针对“{diff}”提供支架式引导和即时反馈",
                }
            )

    total_duration = sum(p["duration_minutes"] for p in phases)

    return {
        "phases": phases,
        "differentiation": differentiation,
        "practice_strategy": type_strategy["practice"],
        "total_duration_minutes": total_duration,
    }


def generate_assessment_strategy(project: dict) -> dict:
    """Embed entry test, pretest, practice, posttest into strategy."""
    learning_type = _detect_learning_type(project)
    goal = project.get("goal", {})

    type_strategy = LEARNING_TYPE_STRATEGIES.get(
        learning_type, LEARNING_TYPE_STRATEGIES["intellectual_skill"]
    )

    behavior = goal.get("behavior", "完成学习目标")

    assessments: list[dict] = [
        {
            "type": "entry_behavior_test",
            "timing": ASSESSMENT_EMBEDDING["entry_behavior_test"]["timing"],
            "purpose": ASSESSMENT_EMBEDDING["entry_behavior_test"]["purpose"],
            "activity": "快速检测学生是否具备学习新内容所需的入门技能",
            "method": "口头提问或学习单前测",
            "duration_minutes": 1,
        },
        {
            "type": "pretest",
            "timing": ASSESSMENT_EMBEDDING["pretest"]["timing"],
            "purpose": ASSESSMENT_EMBEDDING["pretest"]["purpose"],
            "activity": "了解学生对将学习内容的已有认知水平",
            "method": "选择题或判断题",
            "duration_minutes": 1,
        },
        {
            "type": "practice",
            "timing": ASSESSMENT_EMBEDDING["practice"]["timing"],
            "purpose": ASSESSMENT_EMBEDDING["practice"]["purpose"],
            "activity": f"在练习过程中收集学生{behavior}的表现数据",
            "method": type_strategy["assessment"],
            "duration_minutes": 0,
            "embedded": True,
        },
        {
            "type": "posttest",
            "timing": ASSESSMENT_EMBEDDING["posttest"]["timing"],
            "purpose": ASSESSMENT_EMBEDDING["posttest"]["purpose"],
            "activity": f"检测学生是否达成目标：{behavior}",
            "method": type_strategy["assessment"],
            "duration_minutes": 5,
        },
    ]

    return {
        "assessments": assessments,
        "assessment_strategy": type_strategy["assessment"],
        "total_assessment_minutes": 7,
    }


def generate_follow_through_activities(project: dict) -> dict:
    """Generate memory support and transfer tasks."""
    topic = _detect_topic(project)
    goal = project.get("goal", {})
    learner_ctx = project.get("learner_context_input", {})

    topic_follow = TOPIC_STRATEGY_TEMPLATES.get(topic, {}).get(
        "follow_through", {}
    )

    context_desc = goal.get("context", "在学习情境中")

    memory_supports = topic_follow.get("memory_support", [])
    if not memory_supports:
        behavior = goal.get("behavior", "完成学习目标")
        memory_supports = [
            f"提供{behavior}的检查清单",
            "使用总结性回顾巩固关键概念",
        ]

    transfer_tasks = topic_follow.get("transfer_tasks", [])
    if not transfer_tasks:
        transfer_tasks = [
            f"课后在{context_desc}中运用所学知识完成真实任务",
            "预习下一课时内容",
        ]

    reflection = {
        "activity": "学生反思本节课的学习过程和收获",
        "method": "学习反思单或口头分享",
        "duration_minutes": 1,
    }

    return {
        "memory_support": memory_supports,
        "transfer_tasks": transfer_tasks,
        "reflection": reflection,
        "total_duration_minutes": 3,
    }


# ---------------------------------------------------------------------------
# Lesson flow builder
# ---------------------------------------------------------------------------

def _build_lesson_flow(
    pre_instructional: dict,
    content_presentation: dict,
    learner_participation: dict,
    assessment: dict,
    follow_through: dict,
    class_duration: int,
) -> list:
    """Build a lesson flow table as a list of row dicts."""
    flow: list[dict] = []
    current_time = 0

    # --- Pre-instructional ---
    pre_items = [
        (
            "情境导入与动机激发",
            pre_instructional["motivation"]["strategies"][0]["activity"]
            if pre_instructional["motivation"]["strategies"]
            else "情境导入",
            "提问、引导",
            "思考、回答",
            "口头观察",
            "黑板/投影",
            2,
        ),
        (
            "学习目标呈现",
            pre_instructional["objectives_overview"]["activity"],
            "展示目标",
            "了解目标",
            "—",
            "投影",
            2,
        ),
        (
            "入门技能检测",
            pre_instructional["entry_skill_activation"]["activity"],
            "提问、检测",
            "回答、展示",
            "前测/提问",
            "学习单",
            1,
        ),
    ]

    for item_name, activity, teacher, student, assess, media, dur in pre_items:
        flow.append(
            {
                "时间段": f"{current_time}-{current_time + dur}分钟",
                "教学环节": "教学前活动",
                "具体活动": f"{item_name}：{activity}",
                "教师行为": teacher,
                "学生行为": student,
                "评估方式": assess,
                "媒体/材料": media,
                "时间（分钟）": dur,
            }
        )
        current_time += dur

    # --- Content Presentation ---
    for phase in content_presentation["phases"]:
        dur = phase["duration_minutes"]
        flow.append(
            {
                "时间段": f"{current_time}-{current_time + dur}分钟",
                "教学环节": "内容呈现",
                "具体活动": f"{phase['phase']}：{phase['activity']}",
                "教师行为": phase.get("teacher_behavior", "讲解、演示"),
                "学生行为": phase.get("student_behavior", "观察、思考"),
                "评估方式": "观察提问",
                "媒体/材料": "、".join(phase.get("media", ["投影"])),
                "时间（分钟）": dur,
            }
        )
        current_time += dur

    # --- Learner Participation ---
    for phase in learner_participation["phases"]:
        dur = phase["duration_minutes"]
        flow.append(
            {
                "时间段": f"{current_time}-{current_time + dur}分钟",
                "教学环节": "学习者参与",
                "具体活动": f"{phase['phase']}：{phase['activity']}",
                "教师行为": phase.get("teacher_behavior", "巡视指导"),
                "学生行为": phase.get("student_behavior", "练习"),
                "评估方式": phase.get("feedback", "形成性反馈"),
                "媒体/材料": "学习单",
                "时间（分钟）": dur,
            }
        )
        current_time += dur

    # --- Assessment (posttest) ---
    posttest = None
    for a in assessment["assessments"]:
        if a["type"] == "posttest":
            posttest = a
            break

    if posttest:
        dur = posttest["duration_minutes"]
        flow.append(
            {
                "时间段": f"{current_time}-{current_time + dur}分钟",
                "教学环节": "评估",
                "具体活动": f"总结性评价：{posttest['activity']}",
                "教师行为": "组织测试、收集作品",
                "学生行为": "完成测试、提交作品",
                "评估方式": posttest["method"],
                "媒体/材料": "测试题/学习单",
                "时间（分钟）": dur,
            }
        )
        current_time += dur

    # --- Follow Through ---
    follow_dur = follow_through["total_duration_minutes"]
    memory_text = "；".join(follow_through["memory_support"][:2])
    transfer_text = "；".join(follow_through["transfer_tasks"][:2])

    flow.append(
        {
            "时间段": f"{current_time}-{current_time + follow_dur}分钟",
            "教学环节": "总结与迁移",
            "具体活动": f"记忆支持：{memory_text}；迁移任务：{transfer_text}",
            "教师行为": "总结要点、布置任务",
            "学生行为": "回顾总结、记录作业",
            "评估方式": "学习反思",
            "媒体/材料": "学习单",
            "时间（分钟）": follow_dur,
        }
    )
    current_time += follow_dur

    # Fill remaining time if any
    remaining = class_duration - current_time
    if remaining > 0:
        flow.append(
            {
                "时间段": f"{current_time}-{class_duration}分钟",
                "教学环节": "弹性时间",
                "具体活动": "根据课堂实际情况灵活安排",
                "教师行为": "观察、调整",
                "学生行为": "按需活动",
                "评估方式": "—",
                "媒体/材料": "—",
                "时间（分钟）": remaining,
            }
        )

    return flow


# ---------------------------------------------------------------------------
# Quality check
# ---------------------------------------------------------------------------

def _check_strategy_quality(
    objectives: list,
    lesson_flow: list,
    time_alloc: dict,
    class_duration: int,
) -> dict:
    """Check strategy quality against quality criteria."""
    checks: dict[str, dict] = {}

    # 1. Five components
    flow_stages = {row.get("教学环节", "") for row in lesson_flow}
    stage_mapping = {
        "教学前活动": "pre_instructional",
        "内容呈现": "content_presentation",
        "学习者参与": "learner_participation",
        "评估": "assessment",
        "总结与迁移": "follow_through",
    }
    covered = set()
    for stage_name, comp_name in stage_mapping.items():
        if stage_name in flow_stages:
            covered.add(comp_name)

    missing = set(FIVE_COMPONENTS) - covered
    checks["five_components"] = {
        "name": QUALITY_CRITERIA["five_components"]["name"],
        "passed": len(missing) == 0,
        "covered": list(covered),
        "missing": list(missing),
    }

    # 2. Target coverage - check if objectives are covered by flow activities
    flow_activities = " ".join(
        str(row.get("具体活动", "")) + str(row.get("活动", ""))
        for row in lesson_flow
    )
    uncovered_objs: list[str] = []
    for obj in objectives:
        # Try multiple ID fields
        obj_id = obj.get("objective_id", obj.get("id", ""))
        behavior = obj.get("behavior", obj.get("description", ""))
        # Check if behavior keywords appear in flow
        if behavior and len(behavior) >= 4:
            # Extract meaningful 2-char chunks from behavior
            keywords = [behavior[i:i+2] for i in range(0, len(behavior)-1, 2) if behavior[i:i+2].strip()]
            found = any(kw in flow_activities for kw in keywords[:6] if kw)
        else:
            found = True  # Can't check, assume covered
        if not found:
            uncovered_objs.append(obj_id or "unknown")

    checks["target_coverage"] = {
        "name": QUALITY_CRITERIA["target_coverage"]["name"],
        "passed": len(uncovered_objs) == 0,
        "total_objectives": len(objectives),
        "uncovered": uncovered_objs,
    }

    # 3. Assessment integration
    assess_stages = [
        row for row in lesson_flow if row.get("教学环节") == "评估"
    ]
    has_entry_assess = any(
        "检测" in row.get("具体活动", "") or "前测" in row.get("评估方式", "")
        for row in lesson_flow
        if row.get("教学环节") == "教学前活动"
    )
    has_final_assess = len(assess_stages) > 0
    has_formative = any(
        "形成性" in row.get("评估方式", "") or "反馈" in row.get("评估方式", "")
        for row in lesson_flow
        if row.get("教学环节") == "学习者参与"
    )

    checks["assessment_integration"] = {
        "name": QUALITY_CRITERIA["assessment_integration"]["name"],
        "passed": has_final_assess,
        "entry_assessment": has_entry_assess,
        "formative_assessment": has_formative,
        "summative_assessment": has_final_assess,
    }

    # 4. Time allocation
    total_flow_time = sum(row.get("时间（分钟）", 0) for row in lesson_flow)
    time_match = abs(total_flow_time - class_duration) <= 2

    checks["time_allocation"] = {
        "name": QUALITY_CRITERIA["time_allocation"]["name"],
        "passed": time_match,
        "planned": class_duration,
        "actual": total_flow_time,
        "difference": total_flow_time - class_duration,
    }

    # Overall score
    total_checks = len(checks)
    passed_checks = sum(1 for c in checks.values() if c["passed"])
    overall_score = (
        round(passed_checks / total_checks * 100, 1) if total_checks > 0 else 0
    )

    return {
        "checks": checks,
        "overall_score": overall_score,
        "overall_passed": passed_checks == total_checks,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
    }


def _build_strategy_summary(
    objectives: list,
    class_duration: int,
    topic: str,
    quality_check: dict,
) -> str:
    """Build a human-readable strategy summary."""
    n_obj = len(objectives)
    score = quality_check.get("overall_score", 0)
    passed = quality_check.get("overall_passed", False)

    topic_name = "算法" if topic == "algorithm" else topic

    summary = (
        f"本节课为{class_duration}分钟的{topic_name}主题教学设计，"
        f"包含{n_obj}个教学目标。"
        f"策略涵盖五项教学活动（教学前活动、内容呈现、学习者参与、评估、总结与迁移），"
        f"质量检查得分{score}分。"
    )

    if not passed:
        failed = [
            c["name"]
            for c in quality_check.get("checks", {}).values()
            if not c.get("passed")
        ]
        if failed:
            summary += f"以下方面需改进：{'、'.join(failed)}。"

    return summary


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_instructional_strategy(project: dict) -> dict:
    """
    Generate complete instructional strategy with all 5 components.

    Steps:
        1. Call sequence_objectives to get ordered objectives
        2. Call group_objectives_into_lesson_segments for time allocation
        3. Generate all 5 components
        4. Create a lesson flow table with time segments
        5. Check strategy quality (5 components, target coverage, assessment integration)
        6. Return complete strategy dict
    """
    goal = project.get("goal", {})
    learner_ctx = project.get("learner_context_input", {})
    class_duration = learner_ctx.get("class_duration", 45)

    # --- Step 1: Sequence objectives ---
    objectives = project.get("objectives", [])
    if not objectives:
        behavior = goal.get("behavior", "完成学习目标")
        objectives = [
            {
                "id": "obj_1",
                "description": f"学生能理解{behavior}的基本概念和方法",
                "type": "knowledge",
            },
            {
                "id": "obj_2",
                "description": f"学生能运用所学知识{behavior}",
                "type": "skill",
            },
        ]

    skill_graph = project.get("skill_graph", {})
    seq_result = sequence_objectives(objectives, skill_graph)
    ordered_objectives = seq_result["ordered"]

    # --- Step 2: Group into lesson segments ---
    segment_result = group_objectives_into_lesson_segments(
        ordered_objectives, class_duration
    )
    time_alloc = segment_result["time_allocation"]

    # --- Step 3: Generate all 5 components ---
    pre_instructional = generate_pre_instructional_activities(project)
    content_presentation = generate_content_presentation(project)
    learner_participation = generate_learner_participation(project)
    assessment = generate_assessment_strategy(project)
    follow_through = generate_follow_through_activities(project)

    # --- Step 4: Create lesson flow table ---
    lesson_flow = _build_lesson_flow(
        pre_instructional,
        content_presentation,
        learner_participation,
        assessment,
        follow_through,
        class_duration,
    )

    # --- Step 5: Quality check ---
    quality_check = _check_strategy_quality(
        objectives=ordered_objectives,
        lesson_flow=lesson_flow,
        time_alloc=time_alloc,
        class_duration=class_duration,
    )

    # --- Step 6: Assemble result ---
    topic = _detect_topic(project)
    learning_type = _detect_learning_type(project)

    strategy = {
        "topic": topic,
        "learning_type": learning_type,
        "class_duration": class_duration,
        "objective_sequencing": seq_result,
        "lesson_segments": segment_result,
        "components": {
            "pre_instructional": pre_instructional,
            "content_presentation": content_presentation,
            "learner_participation": learner_participation,
            "assessment": assessment,
            "follow_through": follow_through,
        },
        "lesson_flow": lesson_flow,
        "time_allocation": time_alloc,
        "quality_check": quality_check,
        "summary": _build_strategy_summary(
            ordered_objectives,
            class_duration,
            topic,
            quality_check,
        ),
    }

    return strategy
