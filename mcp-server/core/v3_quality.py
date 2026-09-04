"""Nine-subject v3 alignment and privacy gates.

These checks deliberately stay domain-neutral.  Subject-specific expectations
come from ``subject_adapter`` and the source records, while the gates keep the
Dick-Carey relationships and provenance contract stable across subjects.
"""

from __future__ import annotations

import re
from typing import Any

from core.subject_registry import V3_EDUCATION_SCOPE, V3_SUPPORTED_SUBJECT_IDS
from tools.skill_graph import build_skill_graph_views, validate_skill_graph_views


_AMBIGUOUS_BEHAVIORS = ("知道", "了解", "理解", "掌握")
_PII_KEYS = {
    "student_name",
    "student_id",
    "学生姓名",
    "学号",
    "身份证号",
    "phone",
    "电话",
}


def _text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {_text(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(_text(item) for item in value)
    return str(value or "")


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _finding(gate: str, description: str, evidence: Any, severity: str = "warning") -> dict:
    return {
        "gate": gate,
        "severity": severity,
        "description": description,
        "evidence": _text(evidence)[:600],
    }


def _gate(name: str, passed: bool, message: str, issues: list | None = None, critical: bool = True) -> dict:
    return {
        "passed": bool(passed),
        "message": message,
        "issues": list(issues or []),
        "is_critical": critical,
    }


def _objective_ids(project: dict) -> list[str]:
    return [
        str(item.get("objective_id") or item.get("id"))
        for item in project.get("objectives", [])
        if isinstance(item, dict) and (item.get("objective_id") or item.get("id"))
    ]


def _evidence_by_objective(project: dict) -> dict[str, dict]:
    plan = project.get("assessment_plan") or project.get("assessments") or {}
    result = {}
    evidence = plan.get("evidence", []) if isinstance(plan, dict) else []
    for item in evidence:
        if isinstance(item, dict) and item.get("linked_objective_id"):
            result[str(item["linked_objective_id"])] = item
    for key in ("pretest", "practice_evidence", "posttest", "entry_behavior_test"):
        for item in (plan.get(key, {}).get("items", []) if isinstance(plan, dict) else []):
            if isinstance(item, dict) and item.get("objective_id"):
                result.setdefault(str(item["objective_id"]), item)
    return result


def _material_objective_ids(project: dict) -> set[str]:
    ids: set[str] = set()
    for item in _walk(project.get("instructional_materials", {})):
        values = item.get("related_objective_ids", [])
        if isinstance(values, list):
            ids.update(str(value) for value in values if value)
    return ids


def check_v3_alignment(project: dict) -> dict:
    """Run stable v3 gates and return a report suitable for all exporters."""
    project = project if isinstance(project, dict) else {}
    critical: list[dict] = []
    warnings: list[dict] = []
    recommendations: list[str] = []
    gates: dict[str, dict] = {}

    scope_ok = project.get("education_scope") == V3_EDUCATION_SCOPE
    adapter = project.get("subject_adapter", {})
    subject_id = adapter.get("subject_id") or project.get("project", {}).get("subject_id")
    subject_ok = scope_ok and subject_id in V3_SUPPORTED_SUBJECT_IDS
    scope_issues = []
    if not scope_ok:
        scope_issues.append("项目 education_scope 不是 k12_nine_subjects")
    if not subject_ok:
        scope_issues.append("缺少受支持的九学科 subject_adapter")
    gates["scope"] = _gate("scope", not scope_issues, "v3 学科范围有效", scope_issues)
    if scope_issues:
        critical.append(_finding("scope", "项目不属于中国 K-12 九学科 v3 范围。", scope_issues, "critical"))

    goal = project.get("goal") or project.get("instructional_goal") or {}
    behavior = str(goal.get("behavior", "")).strip()
    ambiguous = [term for term in _AMBIGUOUS_BEHAVIORS if term in behavior]
    goal_ok = bool(behavior) and not ambiguous
    gates["observable_goal"] = _gate(
        "observable_goal", goal_ok, "教学目的包含可观察行为", ambiguous, True
    )
    if not behavior:
        critical.append(_finding("observable_goal", "教学目的缺少可观察的最终行为。", goal, "critical"))
    elif ambiguous:
        critical.append(_finding("observable_goal", "教学目的仍含有不可直接评价的模糊行为动词。", behavior, "critical"))

    sources = project.get("sources", [])
    official = [
        source for source in sources
        if isinstance(source, dict)
        and source.get("source_level") == "A1"
        and source.get("source_category") == "official_authority"
    ]
    official_with_clause = [
        source for source in official
        if source.get("specific_clauses") and source.get("source_url")
    ]
    subject_official = [
        source for source in official_with_clause
        if source.get("subject_id", subject_id) == subject_id
    ]
    evidence_ok = bool(subject_official)
    gates["evidence"] = _gate(
        "evidence", evidence_ok,
        "已接入本学科 A1 官方条款候选",
        [] if evidence_ok else ["缺少带官方链接和具体条款候选的本学科来源"],
    )
    if not evidence_ok:
        critical.append(_finding("evidence", "没有可追溯的本学科 A1 官方条款候选。", sources, "critical"))
    quality = project.get("quality", {})
    evidence_status = quality.get("evidence_status", "no_source")
    if evidence_status not in {"teacher_confirmed", "final_verified"}:
        warnings.append(_finding(
            "evidence_confirmation",
            "官方条款目前仍是候选证据，需要教师核对版本、单元和条款映射。",
            evidence_status,
        ))

    graph = project.get("skill_graph", {}) or project.get("skill_graphs", {})
    views = build_skill_graph_views(graph) if graph else {}
    graph_check = validate_skill_graph_views(views) if views else {"status": "fail", "errors": ["技能图为空"]}
    graph_ok = graph_check.get("status") == "pass" and "goal_operation_flow" in views and "skill_hierarchy" in views
    gates["graph"] = _gate("graph", graph_ok, "技能图和操作视图有效", graph_check.get("errors", []))
    if not graph_ok:
        critical.append(_finding("graph", "技能图存在空节点、断链，或缺少必要视图。", graph_check, "critical"))

    objectives = project.get("objectives", [])
    evidence_map = _evidence_by_objective(project)
    material_ids = _material_objective_ids(project)
    objective_rows = []
    objective_issues = []
    for objective in objectives:
        if not isinstance(objective, dict):
            continue
        objective_id = str(objective.get("objective_id") or objective.get("id") or "")
        has_abcd = all(str(objective.get(field, "")).strip() for field in ("CN", "B", "CR"))
        has_triplet = all(str(objective.get(field, "")).strip() for field in ("condition", "behavior", "criterion"))
        # The legacy fields remain useful to exporters, but v3 accepts the
        # equivalent condition/behavior/criterion triplet as well.
        missing = [] if has_abcd or has_triplet else [
            field for field in ("CN", "B", "CR") if not str(objective.get(field, "")).strip()
        ]
        if missing and not has_abcd:
            missing = [
                field for field in ("condition", "behavior", "criterion")
                if not str(objective.get(field, "")).strip()
            ] or missing
        row_status = "pass"
        row_warnings = []
        if missing:
            objective_issues.append(f"绩效目标 {objective_id} 缺少 {', '.join(missing)}")
            row_status = "fail"
        if objective_id not in evidence_map:
            objective_issues.append(f"绩效目标 {objective_id} 没有对应评价证据")
            row_status = "fail"
        if objective_id not in material_ids:
            row_warnings.append("材料关联待补充")
            warnings.append(_finding("objective_material", f"绩效目标 {objective_id} 尚未在材料中建立关联。", objective))
        objective_rows.append({
            "objective_id": objective_id,
            "skill_id": objective.get("related_skill_id", ""),
            "evidence_id": evidence_map.get(objective_id, {}).get("evidence_id", ""),
            "material_linked": objective_id in material_ids,
            "status": row_status,
            "warnings": row_warnings,
        })
    objective_ok = bool(objectives) and not objective_issues
    gates["objective_assessment_alignment"] = _gate(
        "objective_assessment_alignment", objective_ok, "绩效目标和评价证据已建立对应关系", objective_issues
    )
    if objective_issues:
        critical.append(_finding("objective_assessment_alignment", "绩效目标、评价证据或 ABCD 字段尚未完整对应。", objective_issues, "critical"))

    strategy = project.get("instructional_strategy", {})
    strategy_ok = bool(strategy.get("lesson_flow"))
    gates["strategy"] = _gate("strategy", strategy_ok, "教学策略包含课堂流程", [] if strategy_ok else ["缺少 lesson_flow"])
    if not strategy_ok:
        critical.append(_finding("strategy", "教学策略缺少可执行的课堂流程。", strategy, "critical"))

    formative = project.get("formative_evaluation", {})
    formative_text = _text(formative)
    formative_ok = bool(formative) and any(token in formative_text for token in ("待实施", "待验证", "planned", "pending"))
    gates["formative_evaluation"] = _gate(
        "formative_evaluation", formative_ok,
        "形成性评价状态明确，且没有把未实施数据写成结果",
        [] if formative_ok else ["缺少待实施/待验证状态"],
        False,
    )
    if not formative_ok:
        warnings.append(_finding("formative_evaluation", "形成性评价需要明确记录为待实施或待验证。", formative))

    pii_hits = []
    for mapping in _walk(project):
        for key in mapping:
            key_text = str(key)
            normalized = key_text.lower().replace("-", "_")
            if key_text in _PII_KEYS or any(token in normalized for token in ("student_name", "student_id", "id_card")):
                pii_hits.append(key_text)
    gates["privacy"] = _gate("privacy", not pii_hits, "未发现禁止保存的学生身份字段", pii_hits)
    if pii_hits:
        critical.append(_finding("privacy", "项目包含禁止保存的学生身份字段。", pii_hits, "critical"))

    confirmations = project.get("required_confirmations", [])
    pending = [item for item in confirmations if isinstance(item, dict) and item.get("status") != "confirmed"]
    if pending:
        warnings.append(_finding("teacher_confirmation", "仍有关键决策等待教师确认，当前只能作为草案导出。", pending))
    gates["teacher_confirmation"] = _gate(
        "teacher_confirmation", not pending, "关键决策均已确认", pending, False
    )

    if not recommendations:
        recommendations.append("教师确认官方条款、教材单元、入门技能、学情和教学策略后，再进行最终导出。")

    final_ready = (
        not critical
        and not pending
        and evidence_status in {"teacher_confirmed", "final_verified"}
        and quality.get("visual_status") == "pass"
    )
    blocking = [item["description"] for item in critical]
    if pending:
        blocking.append("仍有关键教学决策待教师确认")
    if evidence_status not in {"teacher_confirmed", "final_verified"}:
        blocking.append("教学目的的官方条款尚未完成教师确认")
    if quality.get("visual_status") != "pass":
        blocking.append("Word/Draw.io 视觉质量门禁尚未通过")

    status = "fail" if critical else "warning" if warnings else "pass"
    score = max(0, 100 - len(critical) * 18 - len(warnings) * 3)
    return {
        "overall_status": status,
        "score": score,
        "critical_issues": critical,
        "warnings": warnings,
        "recommendations": recommendations,
        "blocking_reasons": blocking,
        "can_export_as_final": final_ready,
        "can_export_as_draft": not critical,
        "export_as_final": final_ready,
        "quality_gates": gates,
        "alignment_matrix": objective_rows,
        "pending_confirmations": pending,
        "subject_id": subject_id or "",
        "evidence_status": evidence_status,
    }
