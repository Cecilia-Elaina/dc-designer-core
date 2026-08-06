"""Deterministic v1 quality gates for the information-tech project contract."""

from __future__ import annotations

import json
import re
from typing import Any

from core.product_config import EDUCATION_SCOPE
from tools.skill_graph import build_skill_graph_views, validate_skill_graph_views


_FORBIDDEN_BEHAVIORS = ("知道", "理解", "了解")
_PROGRAMMING_TERMS = ("编写", "运行", "测试", "调试")
_PII_KEYS = ("student_name", "student_id", "学生姓名", "学号", "身份证号")


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
        "evidence": _text(evidence)[:500],
    }


def check_v1_alignment(project: dict) -> dict:
    """Run the v1 gates and return a report plus an objective alignment matrix.

    The historical alignment checker remains useful for migration diagnostics,
    but its generic assumptions are intentionally kept separate from this
    scope-specific report.
    """
    critical: list[dict] = []
    warnings: list[dict] = []
    recommendations: list[str] = []
    gates: list[dict] = []

    scope_ok = project.get("education_scope") == EDUCATION_SCOPE
    gates.append({"gate": "scope", "status": "pass" if scope_ok else "fail"})
    if not scope_ok:
        critical.append(_finding("scope", "项目不属于 v1 K12 信息科技范围。", project.get("education_scope"), "critical"))

    goal = project.get("instructional_goal") or project.get("goal") or {}
    behavior = str(goal.get("behavior", ""))
    goal_ok = bool(behavior.strip()) and not any(term in behavior for term in _FORBIDDEN_BEHAVIORS)
    gates.append({"gate": "observable_goal", "status": "pass" if goal_ok else "fail"})
    if not behavior.strip():
        critical.append(_finding("observable_goal", "教学目的缺少可观察的最终行为。", goal, "critical"))
    elif any(term in behavior for term in _FORBIDDEN_BEHAVIORS):
        critical.append(_finding("observable_goal", "教学目的使用了不可直接评价的模糊行为动词。", behavior, "critical"))

    sources = project.get("sources", [])
    official = [source for source in sources if source.get("source_level") == "A1" and source.get("source_category") == "official_authority"]
    official_with_clause = [source for source in official if source.get("specific_clauses") and source.get("source_url")]
    private_as_official = [source for source in sources if source.get("source_category") == "teacher_private" and source.get("source_level") in {"A1", "A2", "official"}]
    source_ok = bool(official_with_clause) and not private_as_official
    gates.append({"gate": "evidence", "status": "pass" if source_ok else "fail"})
    if not official_with_clause:
        critical.append(_finding("evidence", "没有可追溯的 A1 官方条款候选，教学目的不能通过依据门禁。", sources, "critical"))
    if private_as_official:
        critical.append(_finding("provenance", "教师私有资料被标成官方依据。", private_as_official, "critical"))
    if project.get("quality", {}).get("evidence_status") not in {"teacher_confirmed", "final_verified"}:
        warnings.append(_finding("evidence_confirmation", "官方条款目前仍是候选证据，需要教师核对版本、单元和条款映射。", project.get("quality", {}).get("evidence_status")))

    graph = project.get("skill_graph", {})
    views = build_skill_graph_views(graph)
    graph_check = validate_skill_graph_views(views)
    gates.append({"gate": "graph", "status": "pass" if graph_check["status"] == "pass" else "fail", "views": list(views)})
    if graph_check["status"] != "pass":
        critical.append(_finding("graph", "技能图存在空节点、断链、孤立节点或循环依赖。", graph_check.get("errors"), "critical"))
    if "goal_operation_flow" not in views or "skill_hierarchy" not in views:
        critical.append(_finding("graph_views", "缺少目的操作流程图或从属技能层级图。", list(views), "critical"))
    if graph.get("include_control_flow") and "control_flow" not in views:
        critical.append(_finding("control_flow", "编程课题声明需要控制流图，但没有生成该视图。", graph, "critical"))
    if graph.get("include_control_flow") and "control_flow" in views:
        feedback_edges = [edge for edge in views["control_flow"].get("edges", []) if edge.get("edge_type") == "feedback"]
        if not feedback_edges:
            critical.append(_finding("control_flow_feedback", "编程课题控制流图缺少运行、调试后返回重新测试的反馈回路。", views["control_flow"], "critical"))

    objectives = project.get("performance_objectives") or project.get("objectives") or []
    objective_ids = {str(item.get("objective_id") or item.get("id")) for item in objectives if isinstance(item, dict)}
    objective_rows = []
    evidence_items = project.get("assessments", {}).get("evidence", [])
    if isinstance(evidence_items, dict):
        evidence_items = list(evidence_items.values())
    evidence_by_objective = {
        str(item.get("linked_objective_id")): item
        for item in evidence_items if isinstance(item, dict) and item.get("linked_objective_id")
    }
    material_ids: set[str] = set()
    for item in _walk(project.get("instructional_materials", {})):
        for value in item.get("related_objective_ids", []) if isinstance(item.get("related_objective_ids", []), list) else []:
            material_ids.add(str(value))
    for objective in objectives:
        if not isinstance(objective, dict):
            continue
        objective_id = str(objective.get("objective_id") or objective.get("id") or "")
        missing = [field for field in ("CN", "B", "CR") if not str(objective.get(field, "")).strip()]
        row_status = "pass"
        row_warnings = []
        if missing:
            critical.append(_finding("objective", f"绩效目标 {objective_id} 缺少 {', '.join(missing)}。", objective, "critical"))
            row_status = "fail"
        if objective_id not in evidence_by_objective:
            critical.append(_finding("objective_evidence", f"绩效目标 {objective_id} 没有对应评价证据。", objective, "critical"))
            row_status = "fail"
        if objective_id not in material_ids:
            row_warnings.append("没有发现材料关联")
            warnings.append(_finding("objective_material", f"绩效目标 {objective_id} 尚未在材料中建立关联。", objective))
        objective_rows.append({
            "objective_id": objective_id,
            "skill_id": objective.get("related_skill_id", ""),
            "evidence_id": evidence_by_objective.get(objective_id, {}).get("evidence_id", ""),
            "material_linked": objective_id in material_ids,
            "status": row_status,
            "warnings": row_warnings,
        })
    gates.append({"gate": "objective_alignment", "status": "pass" if not any(row["status"] == "fail" for row in objective_rows) else "fail", "count": len(objective_rows)})

    topic = str(project.get("project", {}).get("topic") or project.get("topic") or "")
    is_programming = any(term in topic.lower() for term in ("python", "编程", "分支", "循环", "程序"))
    content_text = _text({
        "assessment": project.get("assessments", {}),
        "strategy": project.get("instructional_strategy", {}),
        "materials": project.get("instructional_materials", {}),
    })
    programming_missing = [term for term in _PROGRAMMING_TERMS if term not in content_text]
    if is_programming and programming_missing:
        critical.append(_finding("programming_authenticity", f"信息科技编程课题缺少：{', '.join(programming_missing)}。", content_text, "critical"))
    if is_programming and "authentic_programming_task" not in content_text:
        warnings.append(_finding("programming_authenticity", "尚未明确标出真实编程任务证据类型。", project.get("assessments", {})))
    gates.append({"gate": "programming_authenticity", "status": "pass" if not programming_missing else "fail" if is_programming else "not_applicable"})

    formative = project.get("formative_evaluation", {})
    if formative and not any(key in _text(formative).lower() for key in ("待实施", "待验证", "not_implemented")):
        warnings.append(_finding("formative_data", "形成性评价结果应明确标注为待实施或待验证。", formative))
    gates.append({"gate": "formative_data", "status": "pass" if not formative or any(key in _text(formative) for key in ("待实施", "待验证", "not_implemented")) else "warning"})

    pii_hits = []
    for mapping in _walk(project):
        for key in mapping:
            key_text = str(key)
            normalized = key_text.lower().replace("-", "_")
            if key_text in _PII_KEYS or any(token in normalized for token in ("student_name", "student_id", "id_card")):
                pii_hits.append(key_text)
    if pii_hits:
        critical.append(_finding("privacy", "项目包含禁止保存的学生身份字段。", pii_hits, "critical"))
    gates.append({"gate": "privacy", "status": "pass" if not pii_hits else "fail"})

    confirmations = project.get("required_confirmations", [])
    pending_confirmations = [item for item in confirmations if item.get("status") != "confirmed"] if isinstance(confirmations, list) else []
    if pending_confirmations:
        warnings.append(_finding("teacher_confirmation", "仍有关键决策等待教师确认，当前只能作为草案导出。", pending_confirmations))
    final_ready = not critical and not pending_confirmations and project.get("quality", {}).get("evidence_status") in {"teacher_confirmed", "final_verified"}
    blocking = [item["description"] for item in critical]
    if pending_confirmations:
        blocking.append("仍有关键教学决策待教师确认")
    if project.get("quality", {}).get("evidence_status") not in {"teacher_confirmed", "final_verified"}:
        blocking.append("教学目的的官方条款尚未完成教师确认")
    visual_status = project.get("quality", {}).get("visual_status", "unverified")
    if visual_status != "pass":
        warnings.append(_finding("visual_quality", "Word/Draw.io 视觉质量尚未通过真实渲染门禁。", project.get("quality", {}).get("visual_check", {})))
        blocking.append("Word/Draw.io 视觉质量门禁尚未通过")
    final_ready = final_ready and visual_status == "pass"
    if critical:
        overall = "fail"
    elif warnings:
        overall = "warning"
    else:
        overall = "pass"
    if not recommendations:
        recommendations.append("教师确认课标条款、教材单元、入门技能、学情和教学策略后，再进行最终导出。")
    return {
        "overall_status": overall,
        "score": round(max(0.0, 1.0 - min(1.0, (len(critical) * 0.2 + len(warnings) * 0.03))), 3),
        "critical_issues": critical,
        "warnings": warnings,
        "recommendations": recommendations,
        "blocking_reasons": blocking,
        "can_export_as_final": final_ready,
        "can_export_as_draft": not critical,
        "quality_gates": gates,
        "alignment_matrix": objective_rows,
        "graph_validation": graph_check,
        "pending_confirmations": pending_confirmations,
    }
