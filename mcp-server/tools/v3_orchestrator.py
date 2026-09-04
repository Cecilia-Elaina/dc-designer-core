"""v3 orchestration for China K-12 nine-subject instructional design.

The engines in this module are deliberately deterministic.  They assemble a
subject adapter, locally indexed official-source candidates, teacher inputs,
and the existing Dick-Carey engines into one portable project object.  Every
generated conclusion remains a candidate until the teacher confirms it.
"""

from __future__ import annotations

import copy
import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from core.product_config import initialize_v3_project, validate_v3_scope
from core.subject_registry import STAGE_LABELS, SubjectRegistryError, get_subject
from core.v3_quality import check_v3_alignment


_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_THIS_DIR)
_REPO_ROOT = os.path.normpath(os.path.join(_PKG_ROOT, ".."))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record(plan: list[dict], engine: str, function: str, inputs: dict | None = None, outputs: dict | None = None) -> None:
    from tools.agent_session import _record_tool_call

    _record_tool_call(plan, engine, function, inputs or {}, outputs or {})


def _error(mode: str, messages: list[str], *, check: dict | None = None) -> dict:
    return {
        "mode": mode,
        "status": "error",
        "tool_call_plan": [],
        "warnings": list(messages),
        "required_confirmations": [],
        "findings": [],
        "revision_log": [],
        "scope_check": check or {},
    }


def _clean_topic(topic: str) -> str:
    value = str(topic or "").strip()
    value = re.sub(r"^(认识|理解|掌握|了解)", "", value).strip(" ：:，,")
    return value or str(topic or "学习主题")


def _default_behavior(topic: str, adapter: dict[str, Any]) -> str:
    verbs = [
        str(verb).strip()
        for verb in adapter.get("observable_verbs", [])
        if str(verb).strip() not in {"理解", "掌握", "认识", "了解"}
    ]
    verb = verbs[0] if verbs else "完成"
    focus = _clean_topic(topic)
    return f"能{verb}{focus}的关键内容，并依据证据完成一次可核验的学科任务"


def _source_query(request: dict, adapter: dict[str, Any], stage: str) -> dict:
    pattern_keywords = []
    for pattern in adapter.get("concept_and_skill_patterns", []):
        pattern_keywords.append(pattern.get("name", ""))
        pattern_keywords.extend(pattern.get("keywords", []))
    pattern_keywords.extend(adapter.get("core_competencies", []))
    return {
        "stage": STAGE_LABELS[stage],
        "grade": request.get("grade_level") or request.get("grade", ""),
        "subject": adapter.get("display_name", request.get("subject", "")),
        "topic": request.get("topic", ""),
        "keywords": [item for item in pattern_keywords if item],
        "scene_type": "k12",
    }


def _build_candidate_steps(topic: str, adapter: dict[str, Any]) -> list[dict]:
    focus = _clean_topic(topic)
    patterns = adapter.get("concept_and_skill_patterns", [])
    names = [str(item.get("name", "学科对象")) for item in patterns if item.get("name")]
    first = names[0] if names else "核心对象"
    second = names[1] if len(names) > 1 else first
    third = names[2] if len(names) > 2 else second
    descriptions = [
        f"从“{focus}”情境中识别关键对象、任务条件和已有信息",
        f"依据“{first}”整理概念、关系或方法，并说明选择理由",
        f"运用“{second}”完成一项与“{focus}”对应的学科任务",
        f"用“{third}”要求的表达方式呈现过程、结果和证据",
        "依据评价证据检查表现，说明差距并完成一次修订",
    ]
    return [
        {
            "description": description,
            "learning_type": "intellectual_skill",
            "is_critical": True,
        }
        for description in descriptions
    ]


def _build_candidate_subskills(steps: list[dict], adapter: dict[str, Any]) -> list[dict]:
    concepts = [
        str(item.get("name", ""))
        for item in adapter.get("concept_and_skill_patterns", [])
        if item.get("name")
    ]
    subskills = []
    for index, step in enumerate(steps):
        name = concepts[index % len(concepts)] if concepts else "学科核心概念"
        if index == 0:
            description = f"识别{name}涉及的基本对象和任务条件"
            skill_type = "prerequisite"
        elif index == 1:
            description = f"说明{name}与当前学习任务之间的关系"
            skill_type = "subordinate"
        elif index == 2:
            description = f"运用{name}完成相关学科任务"
            skill_type = "subordinate"
        elif index == 3:
            description = f"依据{name}表达过程、结果和证据"
            skill_type = "subordinate"
        else:
            description = "根据评价证据检查并修订学习表现"
            skill_type = "subordinate"
        subskills.append({
            "name": description,
            "description": description,
            "linked_step_id": step.get("step_id", ""),
            "skill_type": skill_type,
            "learning_type": "intellectual_skill",
        })
    return subskills


def _build_sources(request: dict, adapter: dict[str, Any], stage: str, warnings: list[str], plan: list[dict]) -> tuple[list[dict], dict]:
    from tools.standards_search import build_source_record_from_standard, search_standards

    query = _source_query(request, adapter, stage)
    result = search_standards(query)
    _record(plan, "standards_search", "search_standards", query, {
        "status": result.get("status"),
        "match_count": len(result.get("matches", [])),
    })
    sources = []
    for match in result.get("matches", []):
        source = build_source_record_from_standard(match)
        source["subject_id"] = adapter.get("subject_id", "")
        source["stage_id"] = stage
        source["teacher_confirmation_required"] = True
        source["verified_by_teacher"] = bool(match.get("verified_by_teacher", False))
        sources.append(source)
    if not sources:
        warnings.append("未找到本学段本学科的本地官方条款候选，设计只能作为待验证草案。")
    return sources, result


def _ingest_teacher_documents(request: dict, adapter: dict[str, Any], stage: str, workspace: str | None, sources: list[dict], warnings: list[str], plan: list[dict]) -> None:
    documents = request.get("source_documents", [])
    if not documents:
        return
    from core.local_knowledge import ingest_private_document

    initial_source_count = len(sources)
    for index, reference in enumerate(documents, 1):
        if not isinstance(reference, str) or not reference.strip():
            continue
        result = ingest_private_document(
            reference,
            {
                "title": os.path.basename(reference),
                "subject": adapter.get("display_name", ""),
                "stage": stage,
                "grade": request.get("grade_level") or request.get("grade", ""),
                "topic": request.get("topic", ""),
                "document_type": "teacher_material",
            },
            workspace=workspace,
        )
        if result.get("status") == "ok" and result.get("source_record"):
            source = dict(result["source_record"])
            source["subject_id"] = adapter.get("subject_id", "")
            source["stage_id"] = stage
            sources.append(source)
        else:
            warnings.extend(str(item) for item in result.get("warnings", []) if item)
            warnings.extend(str(item) for item in result.get("errors", []) if item)
    _record(plan, "knowledge_ingest", "ingest_teacher_documents", {
        "document_count": len(documents),
        "subject_id": adapter.get("subject_id", ""),
    }, {"sources_added": max(0, len(sources) - initial_source_count)})


def _build_goal(request: dict, adapter: dict[str, Any], stage: str, sources: list[dict]) -> tuple[dict, dict]:
    from tools.goal_engine import validate_instructional_goal
    from core.ids import gen_goal_id

    teacher_inputs = request.get("teacher_inputs", {})
    if not isinstance(teacher_inputs, dict):
        teacher_inputs = {}
    display_name = adapter.get("display_name", request.get("subject", ""))
    grade = request.get("grade_level") or request.get("grade", "")
    topic = request.get("topic", "")
    behavior = request.get("goal_behavior") or teacher_inputs.get("goal_behavior") or _default_behavior(topic, adapter)
    behavior = str(behavior).strip()
    context = request.get("performance_context") or teacher_inputs.get("performance_context") or {}
    if isinstance(context, dict):
        context_text = context.get("use_environment") or context.get("description") or "真实或适龄的课堂任务情境"
    else:
        context_text = str(context or "真实或适龄的课堂任务情境")
    tools = teacher_inputs.get("available_media") or ["教材、板书和学习单"]
    if isinstance(tools, list):
        tools = tools[0] if tools else "教材、板书和学习单"
    goal = {
        "goal_id": gen_goal_id(),
        "learner": f"{grade}学生" if grade else "学习者",
        "behavior": behavior,
        "context": context_text,
        "tools": str(tools),
        "scene_type": "k12",
        "sources": sources,
        "subject_id": adapter.get("subject_id", ""),
        "subject": display_name,
        "stage": stage,
        "topic": topic,
    }
    goal["full_statement"] = (
        f"{goal['learner']}在{display_name}“{topic}”学习任务中，{behavior}，"
        f"在{context_text}下借助{goal['tools']}。"
    )
    validation = validate_instructional_goal(goal, sources)
    # An official candidate with clause evidence is not teacher-confirmed yet.
    goal["source_status"] = "sufficient" if sources else "insufficient"
    goal["verification_status"] = "draft_pending_teacher_confirmation"
    goal["is_verified"] = False
    goal["teacher_confirmation_required"] = True
    goal["validation_issues"] = validation.get("issues", [])
    goal["validation_recommendations"] = validation.get("recommendations", [])
    return goal, validation


def _build_learner_context(request: dict) -> tuple[dict, dict]:
    from tools.agent_session import _build_learner_input
    from tools.learner_context import (
        analyze_learner_profile,
        analyze_learning_context,
        analyze_performance_context,
        generate_context_implications,
    )

    learner_input = _build_learner_input(request)
    learner = analyze_learner_profile(learner_input)
    learning = analyze_learning_context(learner_input)
    performance = analyze_performance_context(learner_input)
    implications = generate_context_implications(learner, learning, performance)
    context = {
        "learner_profile": learner,
        "learning_context": learning,
        "performance_context": performance,
        "strategy_implications": implications.get("strategy_implications", []),
        "implications": [
            item.get("implication", str(item)) if isinstance(item, dict) else str(item)
            for item in implications.get("strategy_implications", [])
        ],
    }
    return learner_input, {"analysis": context, "learner": learner, "learning": learning, "performance": performance, "implications": implications}


def _build_objectives(skill_graph: dict, adapter: dict[str, Any], grade: str, display_name: str, topic: str, plan: list[dict]) -> list[dict]:
    from tools.objective_engine import write_performance_objectives

    result = write_performance_objectives(skill_graph, {"subject_adapter": adapter})
    objectives = result.get("objectives", [])
    evidence_patterns = list(adapter.get("assessment_evidence_patterns", []))
    focus = _clean_topic(topic)
    for objective in objectives:
        behavior = str(objective.get("behavior", "")).strip()
        for weak in ("理解", "掌握", "认识", "了解"):
            behavior = behavior.replace(weak, "")
        behavior = behavior.strip(" ，,：:") or f"完成{focus}相关学习表现"
        condition = f"在{grade or '本学段'}{display_name}“{topic}”任务情境中，提供必要的教材、资料或工具"
        criterion = "提交与目标对应的过程、作品、表达或操作证据，并能说明关键依据"
        objective.update({
            "condition": condition,
            "behavior": behavior,
            "criterion": criterion,
            "CN": condition,
            "B": behavior,
            "CR": criterion,
            "provenance_type": "AI_SUGGESTION",
            "status": "candidate",
            "teacher_confirmation_required": True,
            "subject_id": adapter.get("subject_id", ""),
            "evidence_patterns": evidence_patterns,
        })
    _record(plan, "objective_engine", "write_performance_objectives", {
        "goal_step_count": len(skill_graph.get("goal_steps", [])),
        "subject_id": adapter.get("subject_id", ""),
    }, {"objective_count": len(objectives)})
    return objectives


def _build_assessment(objectives: list[dict], adapter: dict[str, Any], plan: list[dict]) -> dict:
    from tools.assessment_engine import generate_assessment_plan

    assessment = generate_assessment_plan(objectives, {"subject_adapter": adapter})
    phases = ("entry_behavior_test", "pretest", "practice_evidence", "posttest")
    patterns = list(adapter.get("assessment_evidence_patterns", []))
    for phase_name in phases:
        phase = assessment.get(phase_name, {})
        if not isinstance(phase, dict):
            continue
        phase["subject_id"] = adapter.get("subject_id", "")
        phase["status"] = "planned"
        phase["teacher_confirmation_required"] = True
        phase["evidence_patterns"] = patterns
        phase.pop("pass_threshold", None)
        rubric = phase.get("scoring_rubric")
        if isinstance(rubric, dict):
            rubric.pop("pass_threshold", None)
            rubric["teacher_confirmation_required"] = True
        for item in phase.get("items", []):
            if not isinstance(item, dict):
                continue
            item["status"] = "planned"
            item["teacher_confirmation_required"] = True
            item["evidence_patterns"] = patterns
            if not item.get("expected_evidence"):
                item["expected_evidence"] = patterns[0] if patterns else "可核验的学习表现证据"
    assessment["subject_id"] = adapter.get("subject_id", "")
    assessment["status"] = "planned"
    assessment["teacher_confirmation_required"] = True
    assessment["evidence_patterns"] = patterns
    _record(plan, "assessment_engine", "generate_assessment_plan", {
        "objective_count": len(objectives),
        "subject_id": adapter.get("subject_id", ""),
    }, {"evidence_count": len(assessment.get("evidence", []))})
    return assessment


def _build_strategy(goal: dict, skill_graph: dict, objectives: list[dict], assessment: dict, learner_input: dict, context_bundle: dict, adapter: dict, plan: list[dict]) -> dict:
    from tools.agent_session import _build_project_for_strategy
    from tools.strategy_engine import generate_instructional_strategy

    project_for_strategy = _build_project_for_strategy(
        goal,
        skill_graph,
        objectives,
        assessment,
        learner_input,
        context_bundle["learner"],
        context_bundle["learning"],
        context_bundle["performance"],
        context_bundle["implications"],
    )
    # Avoid applying the old information-technology topic templates to a
    # subject whose title happens to contain words such as “循环”.
    strategy_goal = copy.deepcopy(goal)
    strategy_goal["behavior"] = "完成本学科学习任务"
    project_for_strategy["goal"] = strategy_goal
    project_for_strategy["metadata"] = {"subject": adapter.get("display_name", ""), "topic": ""}
    project_for_strategy["topic"] = ""
    project_for_strategy["subject"] = adapter.get("display_name", "")
    project_for_strategy["grade"] = goal.get("learner", "")
    raw = generate_instructional_strategy(project_for_strategy)
    raw["subject_id"] = adapter.get("subject_id", "")
    raw["subject"] = adapter.get("display_name", "")
    raw["topic"] = goal.get("topic", "")
    raw["subject_strategy_patterns"] = list(adapter.get("strategy_patterns", []))
    raw["formative_feedback_patterns"] = list(adapter.get("formative_feedback_patterns", []))
    raw["teacher_confirmation_required"] = True
    raw["summary"] = (
        str(raw.get("summary", ""))
        + "；本学科策略建议："
        + "；".join(str(item) for item in adapter.get("strategy_patterns", [])[:3])
    )
    _record(plan, "strategy_engine", "generate_instructional_strategy", {
        "objective_count": len(objectives),
        "subject_id": adapter.get("subject_id", ""),
    }, {"has_lesson_flow": bool(raw.get("lesson_flow"))})
    return raw


def _wrap_material(raw: dict, material_type: str, title: str, objective_ids: list[str], assessment_ids: list[str], time_minutes: int) -> dict:
    return {
        "material_id": f"mat_{material_type}",
        "title": title,
        "material_type": material_type,
        "target_users": ["teacher"] if material_type in {"teacher_guide", "board", "lesson_plan"} else ["student"],
        "related_objective_ids": objective_ids,
        "related_strategy_segments": ["全部"],
        "related_assessment_ids": assessment_ids,
        "estimated_time_minutes": time_minutes,
        "content": raw,
        "usage_notes": ["使用前由教师确认学科内容、教材对应关系和课堂条件。"],
        "status": "candidate",
        "teacher_confirmation_required": True,
    }


def _build_materials(project: dict, adapter: dict[str, Any], objectives: list[dict], assessment: dict, strategy: dict, plan: list[dict]) -> dict:
    display_name = adapter.get("display_name", "")
    topic = project.get("topic", "")
    grade = project.get("grade", "")
    objective_ids = [str(item.get("objective_id")) for item in objectives if item.get("objective_id")]
    assessment_ids = []
    for name in ("entry_behavior_test", "pretest", "practice_evidence", "posttest"):
        item = assessment.get(name, {})
        if isinstance(item, dict) and item.get("test_id"):
            assessment_ids.append(str(item["test_id"]))
    entry_skills = [
        item.get("name", "")
        for item in project.get("skill_graph", {}).get("entry_behaviors", [])
        if item.get("name")
    ]
    evidence = list(adapter.get("assessment_evidence_patterns", []))
    patterns = list(adapter.get("material_patterns", []))
    flow = strategy.get("lesson_flow", [])
    raw = {
        "teacher_guide": {
            "标题": f"{grade}{display_name}——{topic}教师授课手册",
            "教学依据": f"{display_name} v3 学科适配器；官方课标条款候选由教师核对。",
            "教学目标": [
                {"objective_id": item.get("objective_id", ""), "behavior": item.get("behavior", ""), "condition": item.get("condition", ""), "criterion": item.get("criterion", "")}
                for item in objectives
            ],
            "学情与入门技能": entry_skills or ["待教师补充本班学生已有知识与技能"],
            "课堂流程": flow,
            "评价证据": evidence,
            "常见误区": adapter.get("common_misconceptions", []),
            "反馈与修订": adapter.get("formative_feedback_patterns", []),
            "课前确认": ["教材版本与单元", "课标条款候选", "课时和设备", "匿名班级共性学情"],
        },
        "student_worksheet": {
            "标题": f"{grade}{display_name}——{topic}学习单",
            "说明": "请根据任务条件完成记录，保留过程证据和修改痕迹。",
            "任务一：情境识别": f"从“{topic}”情境中写出任务目标、已知条件和需要使用的学科概念。",
            "任务二：过程记录": ["关键对象或概念：________________", "我的方法与理由：________________", "过程证据：________________"],
            "任务三：表达与检查": ["我的结论/作品/操作结果：________________", "我依据的证据：________________", "我还需要修订的地方：________________"],
            "目标对照": [item.get("behavior", "") for item in objectives],
        },
        "entry_test_sheet": {
            "标题": f"{grade}{display_name}——入门技能检测",
            "说明": "用于了解开始本课前的已有表现，不直接写成学习效果结论。",
            "检测内容": entry_skills or [f"与“{topic}”相关的基础知识、表达或操作"],
            "学生记录": "我会做的：________________；我需要帮助的：________________",
        },
        "pretest_sheet": {
            "标题": f"{grade}{display_name}——课前诊断任务",
            "任务": f"面对“{topic}”的简短问题情境，请先写出你的判断、方法或表达方案。",
            "依据": "我这样做的理由和依据：________________",
            "教师观察": "记录共性困难，不记录学生身份信息。",
        },
        "group_task_sheet": {
            "标题": f"{grade}{display_name}——小组任务单",
            "任务": f"围绕“{topic}”完成一个可观察、可提交的学科任务。",
            "小组产出": ["任务目标：________________", "分工与过程：________________", "作品/表达/操作结果：________________", "证据与理由：________________"],
            "自检": ["目标是否清楚", "方法是否与条件匹配", "证据是否支持结论", "是否留下修订记录"],
        },
        "peer_review_checklist": {
            "标题": f"{grade}{display_name}——同伴互评检查表",
            "说明": "只评价作品、过程和证据，不评价同伴身份。",
            "检查项目": [
                "是否回应任务条件",
                "是否使用了恰当的学科概念或方法",
                "过程、结论或作品是否可核验",
                "是否说明证据与结论的关系",
                "是否根据反馈完成修订",
            ],
            "具体反馈": "我看到的证据：________________；建议修订：________________",
        },
        "posttest_sheet": {
            "标题": f"{grade}{display_name}——迁移与总结任务",
            "说明": f"在新的“{topic}”相关情境中独立完成任务，并提交可核验证据。",
            "任务要求": ["任务条件：________________", "我的表现/作品/操作：________________", "我的证据与理由：________________", "根据检查结果进行的修订：________________"],
            "评价依据": evidence,
        },
        "board_design": {
            "标题": f"{display_name}《{topic}》板书/课堂记录结构",
            "结构": ["问题情境与目标", "关键概念、关系或方法", "示范过程与证据", "学生表现与反馈", "修订后的结论或作品"],
            "提示": "保留来源、条件和关键推理，不把教师示例写成学生真实结果。",
        },
        "simple_lesson_plan": {
            "标题": f"{grade}{display_name}《{topic}》简版教案",
            "设计主线": "情境进入 → 概念/方法示范 → 学习者任务 → 证据评价 → 反馈修订 → 迁移",
            "学科材料建议": patterns,
            "课堂流程": flow,
            "实施边界": "课标、教材、学情和评价结果由教师在使用前确认。",
        },
    }
    metadata = {
        "teacher_guide": ("teacher_guide", "教师授课手册", objective_ids, assessment_ids, 45),
        "student_worksheet": ("student_worksheet", "学生学习单", objective_ids, assessment_ids, 45),
        "entry_test_sheet": ("entry_test", "入门技能测试单", objective_ids[:1], assessment_ids[:1], 5),
        "pretest_sheet": ("pretest", "前测任务单", objective_ids[:2], assessment_ids[1:2], 8),
        "group_task_sheet": ("group_task", "小组任务单", objective_ids, assessment_ids[2:3], 15),
        "peer_review_checklist": ("peer_review", "互评检查表", objective_ids, assessment_ids[2:3], 8),
        "posttest_sheet": ("posttest", "后测任务单", objective_ids, assessment_ids[3:4], 15),
        "board_design": ("board", "板书设计", objective_ids, [], 0),
        "simple_lesson_plan": ("lesson_plan", "简版课堂教案", objective_ids, assessment_ids, 45),
    }
    materials = {}
    for key, content in raw.items():
        material_type, title, oids, aids, minutes = metadata[key]
        materials[key] = _wrap_material(content, material_type, title, oids, aids, minutes)
    _record(plan, "materials_engine", "generate_subject_aware_materials", {
        "subject_id": adapter.get("subject_id", ""),
    }, {"material_count": len(materials)})
    return materials


def _required_confirmations(project: dict, sources: list[dict], adapter: dict[str, Any]) -> list[dict]:
    source_id = project.get("curriculum_context", {}).get("official_source_id", "")
    return [
        {"component": "curriculum_standard", "status": "pending", "reason": "核对本学科官方课标版本、适用学段和条款候选。", "source_ids": [source_id] if source_id else []},
        {"component": "textbook_unit", "status": "pending", "reason": "确认教材版本、单元位置与课题对应关系。"},
        {"component": "instructional_goal", "status": "pending", "reason": "确认真实绩效差距、最终表现和教学目的陈述。"},
        {"component": "skill_graph", "status": "pending", "reason": "确认主要步骤、从属技能和入门技能是否符合本班学习路径。"},
        {"component": "learner_context", "status": "pending", "reason": "补充匿名班级共性学情、设备和课时条件。"},
        {"component": "assessment_plan", "status": "pending", "reason": "确认评价任务能够证明目标行为，不把候选阈值当成真实结果。"},
        {"component": "instructional_strategy", "status": "pending", "reason": "确认学科策略、课堂流程和迁移任务。"},
        {"component": "instructional_materials", "status": "pending", "reason": "确认材料内容、版权边界和可直接使用程度。"},
    ]


def _write_json(path: str, value: dict) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)


def _export_v3_project(project: dict, output_dir: str, *, include_documents: bool = True) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    files: dict[str, dict] = {}
    json_path = os.path.join(output_dir, "v3_design_project.json")
    _write_json(json_path, project)
    files["project_json"] = {"path": os.path.abspath(json_path), "exists": True, "size": os.path.getsize(json_path)}

    try:
        from tools.export_package import export_markdown_report

        md_path = os.path.join(output_dir, "v3_design_report.md")
        export_markdown_report(project, md_path)
        files["report_markdown"] = {"path": os.path.abspath(md_path), "exists": True, "size": os.path.getsize(md_path)}
    except Exception as exc:
        files["report_markdown"] = {"path": "", "exists": False, "size": 0, "error": str(exc)}

    try:
        from tools.pipeline import _export_materials_markdown

        materials_path = os.path.join(output_dir, "v3_design_materials.md")
        _export_materials_markdown(project, materials_path)
        files["materials_markdown"] = {"path": os.path.abspath(materials_path), "exists": True, "size": os.path.getsize(materials_path)}
    except Exception as exc:
        files["materials_markdown"] = {"path": "", "exists": False, "size": 0, "error": str(exc)}

    errors = []
    if include_documents:
        try:
            from tools.document_exporter import export_all

            raw = export_all(project, output_dir)
            for key, info in raw.get("files", {}).items():
                files[key] = {
                    "path": info.get("path", ""),
                    "exists": bool(info.get("path") and os.path.exists(info.get("path"))),
                    "size": info.get("size", 0),
                }
                if info.get("error"):
                    errors.append(str(info["error"]))
            files["export_index_json"] = {"path": raw.get("index_path", ""), "exists": bool(raw.get("index_path") and os.path.exists(raw.get("index_path"))), "size": os.path.getsize(raw["index_path"]) if raw.get("index_path") and os.path.exists(raw["index_path"]) else 0}
        except Exception as exc:
            errors.append(f"文档导出失败: {exc}")

        try:
            from tools.drawio_exporter import export_skill_graph_drawio

            drawio_path = os.path.join(output_dir, "v3_skill_graph.drawio")
            result = export_skill_graph_drawio(project.get("skill_graph", {}), drawio_path)
            files["skill_graph_drawio"] = {"path": result.get("path", ""), "exists": True, "size": result.get("size", 0)}
        except Exception as exc:
            errors.append(f"Draw.io 导出失败: {exc}")

    # Keep the generated project self-describing without putting its own JSON
    # entry inside the file manifest (which would make its recorded size
    # recursive).  The initial write above still gives callers an artifact if
    # a later document exporter fails.
    project["exports"] = {
        "output_dir": os.path.abspath(output_dir),
        "status": "success" if not errors else "partial",
        "files": {
            key: value for key, value in files.items() if key != "project_json"
        },
    }
    _write_json(json_path, project)
    files["project_json"] = {
        "path": os.path.abspath(json_path),
        "exists": True,
        "size": os.path.getsize(json_path),
    }

    return {
        "status": "success" if not errors else "partial",
        "files": files,
        "errors": errors,
    }


def run_v3_design(request: dict, output_dir: str = "exports/v3", workspace: str | None = None) -> dict:
    """Run a nine-subject v3 design session."""
    request = dict(request or {})
    missing = [field for field in ("subject", "grade_level", "topic") if not request.get(field) and not (field == "subject" and request.get("subject_id"))]
    if missing:
        return _error("dc-design", [f"缺少必要字段: {', '.join(missing)}"])
    check = validate_v3_scope(request)
    if not check["valid"]:
        return _error("dc-design", check["errors"], check=check)

    plan: list[dict] = []
    warnings = list(check.get("warnings", []))
    adapter = check["subject_adapter"]
    stage = check["stage"]
    project = initialize_v3_project(request)
    display_name = adapter.get("display_name", check.get("subject", ""))
    grade = request.get("grade_level") or request.get("grade", "")
    topic = request.get("topic", "")
    project["metadata"] = {
        "user_type": request.get("user_type", "K12教师"),
        "scene_type": "k12",
        "project_name": request.get("title") or f"{topic}教学设计",
        "subject": display_name,
        "subject_id": adapter.get("subject_id", ""),
        "grade_level": grade,
        "textbook": request.get("textbook_version", ""),
        "session_info": str(request.get("periods") or request.get("period") or "1课时"),
    }
    project["topic"] = topic
    project["grade"] = grade
    project["subject"] = display_name
    project["stage"] = stage

    sources, standards_result = _build_sources(request, adapter, stage, warnings, plan)
    _ingest_teacher_documents(request, adapter, stage, workspace, sources, warnings, plan)
    project["sources"] = sources
    project["evidence_claims"] = [
        {
            "claim_id": f"claim_{index}",
            "source_id": source.get("source_id", ""),
            "status": "candidate",
            "teacher_confirmation_required": True,
            "specific_clauses": source.get("specific_clauses", []),
        }
        for index, source in enumerate(sources, 1)
        if source.get("source_level") == "A1"
    ]

    goal, goal_validation = _build_goal(request, adapter, stage, sources)
    project["goal"] = goal
    project["instructional_goal"] = goal
    _record(plan, "goal_engine", "validate_instructional_goal", {"subject_id": adapter.get("subject_id", ""), "source_count": len(sources)}, {"status": goal_validation.get("status"), "requires_teacher_confirmation": True})

    from tools.skill_graph import (
        analyze_subordinate_skills,
        build_skill_graph,
        build_skill_graph_views,
        classify_goal_type,
        generate_goal_steps,
        identify_entry_behaviors,
    )

    candidate_steps = _build_candidate_steps(topic, adapter)
    steps_result = generate_goal_steps(goal, candidate_steps)
    steps = steps_result.get("steps", [])
    for step in steps:
        step.setdefault("learning_type", "intellectual_skill")
        step.setdefault("status", "candidate")
    _record(plan, "skill_graph", "generate_goal_steps", {"subject_id": adapter.get("subject_id", "")}, {"step_count": len(steps)})
    candidate_subskills = _build_candidate_subskills(steps, adapter)
    subskill_result = analyze_subordinate_skills(steps, candidate_subskills)
    subskills = subskill_result.get("subordinate_skills", [])
    for skill in subskills:
        skill.setdefault("learning_type", "intellectual_skill")
        skill.setdefault("status", "candidate")
    _record(plan, "skill_graph", "analyze_subordinate_skills", {"step_count": len(steps)}, {"subskill_count": len(subskills)})
    learner_input, context_bundle = _build_learner_context(request)
    entry_result = identify_entry_behaviors(subskills, learner_input)
    entries = entry_result.get("entry_behaviours", entry_result.get("entry_behaviors", []))
    _record(plan, "skill_graph", "identify_entry_behaviors", {"subskill_count": len(subskills)}, {"entry_count": len(entries)})
    skill_graph = build_skill_graph(goal, steps, subskills, entries)
    skill_graph["goal_type"] = classify_goal_type(goal).get("goal_type", "intellectual_skill")
    skill_graph["goal_steps"] = steps
    skill_graph["subordinate_skills"] = subskills
    skill_graph["entry_behaviors"] = entries
    skill_graph["requires_teacher_confirmation"] = True
    skill_graph["subject_id"] = adapter.get("subject_id", "")
    skill_graph["views"] = build_skill_graph_views(skill_graph)
    project["skill_graph"] = skill_graph
    project["skill_graphs"] = {"main": skill_graph, "views": skill_graph.get("views", {})}
    project["goal_analysis"] = {
        "goal_type": skill_graph.get("goal_type", ""),
        "main_steps": steps,
        "subordinate_skills": subskills,
        "entry_behaviors": entries,
        "status": "candidate",
    }

    project["context_analysis"] = context_bundle["analysis"]
    project["learner_context_input"] = learner_input
    objectives = _build_objectives(skill_graph, adapter, grade, display_name, topic, plan)
    assessment = _build_assessment(objectives, adapter, plan)
    strategy = _build_strategy(goal, skill_graph, objectives, assessment, learner_input, context_bundle, adapter, plan)
    project["objectives"] = objectives
    project["performance_objectives"] = objectives
    project["assessment_plan"] = assessment
    project["assessments"] = assessment
    project["instructional_strategy"] = strategy
    project["instructional_sequence"] = strategy.get("lesson_flow", [])
    project["instructional_materials"] = _build_materials({"topic": topic, "grade": grade, "skill_graph": skill_graph}, adapter, objectives, assessment, strategy, plan)
    project["formative_evaluation"] = {
        "status": "planned_pending_implementation",
        "label": "待实施",
        "subject_id": adapter.get("subject_id", ""),
        "plan": list(adapter.get("formative_feedback_patterns", [])),
        "data_status": "待实施；没有真实课堂数据时不生成效果结论。",
        "revision_trigger": "根据匿名聚合的学习表现、作品和教师观察修订目标、策略或材料。",
    }
    project["required_confirmations"] = _required_confirmations(project, sources, adapter)
    project["decision_log"] = [{
        "decision_id": "v3-initial",
        "status": "candidate",
        "subject_id": adapter.get("subject_id", ""),
        "summary": "已按学段、本学科适配器和官方来源候选建立初始设计对象。",
        "teacher_confirmation_required": True,
    }]
    project["quality"]["evidence_status"] = "candidate" if sources else "no_source"
    project["quality"]["draft_status"] = "draft_pending_teacher_confirmation"
    quality = check_v3_alignment(project)
    project["quality_check"] = quality
    project["alignment_report"] = quality
    _record(plan, "v3_quality", "check_v3_alignment", {"subject_id": adapter.get("subject_id", "")}, {"overall_status": quality.get("overall_status"), "score": quality.get("score")})

    export_result = _export_v3_project(project, output_dir, include_documents=bool(request.get("export", True)))
    _record(plan, "export_package", "export_v3_project", {"output_dir": output_dir}, {"status": export_result.get("status"), "file_count": len(export_result.get("files", {}))})
    if export_result.get("errors"):
        warnings.extend(export_result["errors"])

    status = "completed_with_warnings" if warnings or quality.get("overall_status") != "pass" else "completed"
    pending = project.get("required_confirmations", [])
    return {
        "mode": "dc-design",
        "version": "3.0.0",
        "education_scope": project.get("education_scope"),
        "subject_id": adapter.get("subject_id", ""),
        "subject": display_name,
        "stage": stage,
        "stage_label": STAGE_LABELS.get(stage, stage),
        "status": status,
        "tool_call_plan": plan,
        "warnings": warnings,
        "required_confirmations": pending,
        "findings": [],
        "revision_log": [],
        "project": project,
        "quality_check": quality,
        "alignment_summary": quality,
        "can_export_final": quality.get("can_export_as_final", False),
        "final_blocking_reasons": quality.get("blocking_reasons", []),
        "draft_status": "draft_pending_confirmation",
        "progress": {"current_step": "await_teacher_confirmation", "completed_steps": len(plan), "total_steps": len(plan), "next_action": "confirm curriculum, goal, skills, context, assessment and strategy"},
        "subject_source": {"source_id": project.get("curriculum_context", {}).get("official_source_id", ""), "search_status": standards_result.get("status", "")},
        "export_result": export_result,
        "source_trace": {"goal_basis": {"status": project.get("quality", {}).get("evidence_status", "no_source"), "sources": sources}},
    }


def _load_project(source: Any) -> tuple[dict | None, str]:
    if isinstance(source, dict):
        return copy.deepcopy(source), "<object>"
    path = str(source or "")
    if not path:
        return None, ""
    if not os.path.isabs(path):
        path = os.path.join(_REPO_ROOT, path)
    if not os.path.isfile(path):
        return None, path
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle), path
    except (OSError, json.JSONDecodeError):
        return None, path


def run_v3_review(source: Any, output_dir: str = "exports/v3", workspace: str | None = None) -> dict:
    """Review a v3 project without modifying the source project."""
    project, source_label = _load_project(source)
    if not project:
        return _error("dc-review", [f"项目文件不存在或无法解析: {source_label}"])
    if project.get("education_scope") != "k12_nine_subjects":
        return _error("dc-review", ["dc-review v3 只能评审 education_scope=k12_nine_subjects 的项目"])
    quality = check_v3_alignment(project)
    findings = []
    for gate_name, gate in quality.get("quality_gates", {}).items():
        if isinstance(gate, dict) and not gate.get("passed", True):
            findings.append({
                "finding_id": f"fnd_{len(findings) + 1}",
                "type": "alignment_gap",
                "gate": gate_name,
                "severity": "high" if gate.get("is_critical", True) else "medium",
                "description": gate.get("message", f"门禁未通过: {gate_name}"),
                "evidence": gate.get("issues", []),
                "suggested_fix": "根据门禁证据补充或确认对应模块。",
                "affected_modules": [gate_name],
            })
    for warning in quality.get("warnings", []):
        findings.append({
            "finding_id": f"fnd_{len(findings) + 1}",
            "type": "quality_warning",
            "gate": warning.get("gate", "") if isinstance(warning, dict) else "",
            "severity": "low",
            "description": warning.get("description", str(warning)) if isinstance(warning, dict) else str(warning),
            "evidence": warning.get("evidence", "") if isinstance(warning, dict) else str(warning),
            "suggested_fix": "在教师确认或形成性评价后处理。",
            "affected_modules": [],
        })
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, "v3_review_report.json")
    report = {"mode": "dc-review", "status": "completed_with_warnings" if findings else "completed", "source": source_label, "subject_id": quality.get("subject_id", ""), "quality_check": quality, "findings": findings, "warnings": [], "tool_call_plan": [{"engine": "v3_quality", "function": "check_v3_alignment"}], "project": project}
    _write_json(report_path, report)
    report["report_path"] = os.path.abspath(report_path)
    return report


def _apply_feedback(project: dict, feedback: dict) -> list[dict]:
    items = feedback.get("items", []) if isinstance(feedback, dict) else []
    if isinstance(items, dict):
        items = [items]
    applied = []
    for item in items:
        if isinstance(item, str):
            item = {"module": "revision_notes", "description": item}
        if not isinstance(item, dict):
            continue
        module = str(item.get("module") or item.get("target") or item.get("field") or "revision_notes")
        field = str(item.get("field") or "")
        value = item.get("value", item.get("replacement"))
        if module in {"goal", "instructional_goal"}:
            goal = project.setdefault("goal", project.get("instructional_goal", {}))
            if field and value is not None:
                goal[field] = value
            elif item.get("behavior"):
                goal["behavior"] = item["behavior"]
            goal["full_statement"] = "；".join(str(goal.get(key, "")) for key in ("learner", "behavior", "context", "tools") if goal.get(key))
            project["instructional_goal"] = goal
        elif module in {"objective", "objectives", "performance_objective", "performance_objectives"}:
            objective_id = str(item.get("objective_id") or "")
            for objective in project.get("objectives", []):
                if objective_id and str(objective.get("objective_id")) != objective_id:
                    continue
                if field and value is not None:
                    objective[field] = value
                elif item.get("behavior"):
                    objective.update({"behavior": item["behavior"], "B": item["behavior"]})
                break
            project["performance_objectives"] = project.get("objectives", [])
        elif module in {"strategy", "instructional_strategy"}:
            strategy = project.setdefault("instructional_strategy", {})
            if field and value is not None:
                strategy[field] = value
            else:
                strategy.setdefault("teacher_revision_notes", []).append(item.get("description", str(item)))
        elif module in {"assessment", "assessment_plan", "assessments"}:
            assessment = project.setdefault("assessment_plan", project.get("assessments", {}))
            if field and value is not None:
                assessment[field] = value
            else:
                assessment.setdefault("teacher_revision_notes", []).append(item.get("description", str(item)))
            project["assessments"] = assessment
        elif module in {"context", "learner_context", "learning_context"}:
            project.setdefault("context_analysis", {}).setdefault("teacher_revision_notes", []).append(item.get("description", str(item)))
        else:
            project.setdefault("revision_notes", []).append(item.get("description", str(item)))
        applied.append({"module": module, "field": field, "description": item.get("description", ""), "status": "applied"})
    return applied


def run_v3_revise(source: Any, feedback: dict, output_dir: str = "exports/v3", workspace: str | None = None) -> dict:
    """Apply explicit teacher feedback, then rerun v3 quality gates."""
    project, source_label = _load_project(source)
    if not project:
        return _error("dc-revise", [f"项目文件不存在或无法解析: {source_label}"])
    if project.get("education_scope") != "k12_nine_subjects":
        return _error("dc-revise", ["dc-revise v3 只能修改 education_scope=k12_nine_subjects 的项目"])
    applied = _apply_feedback(project, feedback or {})
    timestamp = _now()
    project.setdefault("revision_history", []).append({"revision_id": f"v3-{len(project['revision_history']) + 1}", "date": timestamp, "feedback_type": (feedback or {}).get("feedback_type", "teacher_feedback"), "items": applied, "status": "candidate"})
    project["updated_at"] = timestamp
    if isinstance(project.get("project"), dict):
        project["project"]["updated_at"] = timestamp
    project.setdefault("quality", {})["evidence_status"] = "candidate"
    quality = check_v3_alignment(project)
    project["quality_check"] = quality
    project["alignment_report"] = quality
    export_result = _export_v3_project(project, output_dir, include_documents=True)
    return {
        "mode": "dc-revise",
        "status": "completed_with_warnings" if quality.get("overall_status") != "pass" else "completed",
        "source": source_label,
        "subject_id": quality.get("subject_id", ""),
        "revision_log": applied,
        "project": project,
        "quality_check": quality,
        "warnings": export_result.get("errors", []),
        "export_result": export_result,
        "can_export_final": quality.get("can_export_as_final", False),
    }
