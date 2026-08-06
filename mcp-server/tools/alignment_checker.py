"""
Alignment Checker Tools

Quality gate and alignment checking engine for the Dick & Carey
instructional design model.  Verifies cross-component consistency
between goals, skill analysis, objectives, and assessments, and
evaluates the ten-rule MVP quality gate.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import json
import re
from typing import Any

from core.quality import (
    check_goal_quality,
    check_skill_graph_quality,
    check_objectives_quality,
    check_assessment_quality,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_UNOBSERVABLE_VERBS = {
    "知道", "了解", "理解", "掌握", "熟悉", "认识", "体会", "感受",
    "领会", "鉴赏", "欣赏", "内化", "领悟",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _split_behaviors(behavior_text: str) -> list[str]:
    """Split a behaviour description into individual sub-behaviours.

    Uses common Chinese delimiters (、，,;；) and conjunctions (和, 以及)
    to decompose a compound behaviour statement.
    """
    if not behavior_text:
        return []
    parts = re.split(r"[、，,;；]+", behavior_text)
    result: list[str] = []
    for p in parts:
        p = p.strip()
        sub = re.split(r"(?:\s*和\s*|\s*以及\s*)", p)
        for s in sub:
            s = s.strip()
            if s:
                result.append(s)
    return result


def _extract_text(item: Any) -> str:
    """Extract readable text from a step / skill / arbitrary item."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("text", "description", "name", "skill_name", "step_name", "title"):
            val = item.get(key)
            if val:
                return str(val)
        return str(item)
    return str(item) if item else ""


def _extract_skill_id(item: Any) -> str:
    """Extract an identifier from a skill / step item."""
    if isinstance(item, dict):
        for key in ("skill_id", "id", "objective_id", "step_id"):
            val = item.get(key)
            if val:
                return str(val)
    return ""


# Synonym groups for alignment matching
_SYNONYM_GROUPS = [
    {"描述", "表达", "表述", "说明", "阐述"},
    {"算法步骤", "算法过程", "操作步骤", "解题步骤", "解决问题的步骤"},
    {"自然语言", "文字描述", "口头描述"},
    {"流程图", "程序框图", "结构图"},
    {"识别", "找出", "发现", "辨认"},
    {"列出", "写出", "罗列", "列举"},
    {"检查", "验证", "校验", "核对"},
    {"问题情境", "问题场景", "实际问题", "生活问题"},
    {"已知条件", "给定条件", "已知信息"},
    {"先后顺序", "顺序", "步骤顺序", "逻辑顺序"},
]

# Subject prefixes to strip before matching
_SUBJECT_PREFIXES = [
    "学生能", "学生能够", "学生会", "学习者能", "学习者能够",
    "能够", "能", "会", "应该",
]


def _normalize_text(text: str) -> str:
    """Normalize text for alignment matching.

    Strips subject prefixes, whitespace, and common grammatical particles.
    """
    if not text:
        return ""
    result = text.strip()
    for prefix in _SUBJECT_PREFIXES:
        if result.startswith(prefix):
            result = result[len(prefix):]
            break
    # Remove common particles
    result = re.sub(r"[的了着过在与和或把被]", "", result)
    return result.strip()


def _expand_synonyms(term: str) -> set[str]:
    """Expand a term to include all its synonyms."""
    result = {term}
    for group in _SYNONYM_GROUPS:
        if term in group:
            result.update(group)
    return result


def _behavior_in_text(behavior: str, text: str) -> bool:
    """Check whether *behavior* is substantially covered by *text*.

    Uses synonym-aware matching:
    1. Direct substring match (after normalization)
    2. Synonym-expanded bigram matching
    3. Character-overlap heuristic (fallback)
    """
    if not behavior or not text:
        return False

    norm_behavior = _normalize_text(behavior)
    norm_text = _normalize_text(text)

    # Direct substring match
    if norm_behavior in norm_text:
        return True
    if behavior in text:
        return True

    # Synonym-expanded bigram matching
    # Extract 2-char bigrams from both texts and check synonym overlap
    behavior_bigrams = set()
    for i in range(len(norm_behavior) - 1):
        bg = norm_behavior[i:i+2]
        if all(c.strip() for c in bg):
            behavior_bigrams.add(bg)

    text_bigrams = set()
    for i in range(len(norm_text) - 1):
        bg = norm_text[i:i+2]
        if all(c.strip() for c in bg):
            text_bigrams.add(bg)

    # Check if any behavior bigram has a synonym match in text bigrams
    for bg in behavior_bigrams:
        expanded = _expand_synonyms(bg)
        for tbg in text_bigrams:
            if tbg in expanded:
                return True

    # Also check if synonym groups cover the core meaning
    # Extract all 2-char terms from synonym groups that appear in behavior
    behavior_terms = set()
    for i in range(len(norm_behavior) - 1):
        term = norm_behavior[i:i+2]
        for group in _SYNONYM_GROUPS:
            if term in group:
                behavior_terms.update(group)

    text_terms = set()
    for i in range(len(norm_text) - 1):
        term = norm_text[i:i+2]
        for group in _SYNONYM_GROUPS:
            if term in group:
                text_terms.update(group)

    # If significant overlap between expanded term sets, consider matched
    if behavior_terms and text_terms:
        overlap = behavior_terms & text_terms
        if len(overlap) >= 2:
            return True

    # Character-overlap fallback (relaxed threshold for synonym awareness)
    meaningful = [c for c in norm_behavior if c.strip()]
    if not meaningful:
        return False
    matched = sum(1 for c in meaningful if c in norm_text)
    return matched / len(meaningful) >= 0.5


def _make_alignment_recommendations(
    issues: list[str], redundancies: list[str], coverage_rate: float
) -> list[str]:
    """Generate human-readable remediation recommendations."""
    recs: list[str] = []
    if coverage_rate < 0.5:
        recs.append(
            "技能流图对教学目的的覆盖严重不足，建议重新分析目的行为并补充技能步骤"
        )
    elif coverage_rate < 0.8:
        recs.append(
            "技能流图对教学目的的覆盖不完整，建议检查是否遗漏了部分目的行为"
        )
    if redundancies:
        recs.append(
            f"发现 {len(redundancies)} 个与教学目的无关的步骤，建议精简技能流图"
        )
    if any("分解可能不充分" in i for i in issues):
        recs.append(
            "多个目的行为只对应一个技能步骤，建议增加行为分解的粒度"
        )
    return recs


def _skill_obj_recommendations(
    uncovered: list[str], orphaned: list[str], coverage_rate: float
) -> list[str]:
    recs: list[str] = []
    if uncovered:
        recs.append(
            f"有 {len(uncovered)} 个技能缺少绩效目标，建议为每个技能设计对应目标"
        )
    if orphaned:
        recs.append(
            f"有 {len(orphaned)} 个绩效目标未关联到技能，建议检查目标与技能的映射关系"
        )
    if coverage_rate < 0.5:
        recs.append("技能-目标覆盖率低于 50%，建议重新检查技能分解和目标设计")
    return recs


def _obj_assess_recommendations(
    uncovered: list[str], mismatches: list[str], coverage_rate: float
) -> list[str]:
    recs: list[str] = []
    if uncovered:
        recs.append(
            f"有 {len(uncovered)} 个目标缺少评价证据，建议为每个目标设计评价方案"
        )
    if mismatches:
        recs.append(
            f"有 {len(mismatches)} 个评价类型不匹配，建议调整证据类型以匹配学习目标类型"
        )
    if coverage_rate < 0.5:
        recs.append("目标-评价覆盖率低于 50%，评价方案需要大幅补充")
    return recs


# ---------------------------------------------------------------------------
# Pairwise alignment checks
# ---------------------------------------------------------------------------

def check_goal_analysis_alignment(goal: dict, skill_graph: dict) -> dict:
    """Check that *skill_graph* covers all behaviours in the *goal*.

    Heuristics applied:
    * goal.behaviour is decomposed by common Chinese delimiters.
    * Each sub-behaviour must be traceable to at least one goal_step or
      subordinate_skill via direct substring or character-overlap matching.
    * If the goal describes multiple behaviours but the skill graph has only
      one step, a warning is raised about insufficient decomposition.

    Returns:
        ``{aligned: bool, issues: list[str], coverage_rate: float,
          redundancies: list[str], recommendations: list[str]}``
    """
    issues: list[str] = []
    redundancies: list[str] = []

    goal_behavior = goal.get("behavior", "")
    goal_steps = skill_graph.get("goal_steps", [])
    subordinate_skills = skill_graph.get("subordinate_skills", [])

    # Decompose the goal behaviour string
    behaviors = _split_behaviors(goal_behavior)
    non_empty_behaviors = [b for b in behaviors if b.strip()]

    # --- Check: goal_steps exist ---
    if not goal_steps:
        issues.append("技能流图缺少目标步骤 (goal_steps)，无法覆盖教学目的行为")

    # Build a combined corpus of skill texts for matching
    all_skill_texts: list[str] = []
    for step in goal_steps:
        all_skill_texts.append(_extract_text(step))
    for skill in subordinate_skills:
        all_skill_texts.append(_extract_text(skill))

    # --- Check: each sub-behaviour is covered ---
    covered_count = 0
    for b in non_empty_behaviors:
        found = any(_behavior_in_text(b, txt) for txt in all_skill_texts)
        if found:
            covered_count += 1
        else:
            issues.append(f"技能流图中未找到与目的行为「{b}」对应的步骤或子技能")

    # --- Check: redundancies (steps unrelated to any behaviour) ---
    for step in goal_steps:
        step_text = _extract_text(step)
        related = any(
            _behavior_in_text(b, step_text) for b in non_empty_behaviors
        )
        if not related and non_empty_behaviors:
            redundancies.append(f"步骤「{step_text}」与教学目的行为无直接关联")

    # --- Check: behaviour count vs step count ---
    if len(non_empty_behaviors) > 1 and len(goal_steps) == 1:
        issues.append(
            f"教学目的包含 {len(non_empty_behaviors)} 个行为描述，"
            f"但技能流图只有 1 个目标步骤，分解可能不充分"
        )

    # --- Coverage rate ---
    total = max(len(non_empty_behaviors), 1)
    coverage_rate = (
        covered_count / total
        if non_empty_behaviors
        else (1.0 if goal_steps else 0.0)
    )

    recommendations = _make_alignment_recommendations(
        issues, redundancies, coverage_rate
    )

    return {
        "aligned": len(issues) == 0,
        "issues": issues,
        "coverage_rate": round(coverage_rate, 2),
        "redundancies": redundancies,
        "recommendations": recommendations,
    }


def check_analysis_objective_alignment(
    skill_graph: dict, objectives: list
) -> dict:
    """Check that each goal_step and subordinate_skill has a corresponding objective.

    A subordinate_skill is exempt when its dictionary carries a truthy
    ``not_assessed_individually`` flag.

    Returns:
        ``{aligned: bool, issues: list[str], coverage_rate: float,
          uncovered_skills: list[str], orphaned_objectives: list[str],
          recommendations: list[str]}``
    """
    issues: list[str] = []
    uncovered_skills: list[str] = []
    orphaned_objectives: list[str] = []

    goal_steps = skill_graph.get("goal_steps", [])
    subordinate_skills = skill_graph.get("subordinate_skills", [])

    # Collect all skills/steps that need objective coverage
    all_skills: list[dict] = []
    for step in goal_steps:
        all_skills.append({
            "id": _extract_skill_id(step),
            "text": _extract_text(step),
            "type": "goal_step",
        })
    for skill in subordinate_skills:
        if isinstance(skill, dict) and skill.get("not_assessed_individually"):
            continue
        all_skills.append({
            "id": _extract_skill_id(skill),
            "text": _extract_text(skill),
            "type": "subordinate_skill",
        })

    # Collect objective information
    obj_texts: list[str] = []
    obj_skill_refs: set[str] = set()
    for obj in objectives:
        obj_texts.append(_extract_text(obj))
        ref = obj.get("linked_skill_id", "") or obj.get("skill_id", "")
        if ref:
            obj_skill_refs.add(ref)

    # --- Check: each skill has a matching objective ---
    covered_count = 0
    for skill_info in all_skills:
        skill_text = skill_info["text"]
        skill_id = skill_info["id"]

        # Explicit ID reference match
        if skill_id and skill_id in obj_skill_refs:
            covered_count += 1
            continue

        # Behavioural text matching
        found = any(
            _behavior_in_text(skill_text, ot) for ot in obj_texts if ot
        )
        if found:
            covered_count += 1
        else:
            label = (
                "目标步骤"
                if skill_info["type"] == "goal_step"
                else "子技能"
            )
            uncovered_skills.append(
                f"{label}「{skill_text}」缺少对应绩效目标"
            )

    # --- Check: orphaned objectives (not linked to any skill) ---
    all_skill_texts_full = [_extract_text(s) for s in all_skills]
    for obj in objectives:
        oid = obj.get("objective_id", "?")
        ref = obj.get("linked_skill_id", "") or obj.get("skill_id", "")
        if ref:
            continue
        obj_text = _extract_text(obj)
        linked = any(
            _behavior_in_text(st, obj_text)
            for st in all_skill_texts_full
            if st
        )
        if not linked and all_skills:
            orphaned_objectives.append(
                f"目标 {oid} 未关联到技能流图中的任何技能"
            )

    issues.extend(uncovered_skills)
    issues.extend(orphaned_objectives)

    total = max(len(all_skills), 1)
    coverage_rate = covered_count / total if all_skills else 1.0

    return {
        "aligned": len(issues) == 0,
        "issues": issues,
        "coverage_rate": round(coverage_rate, 2),
        "uncovered_skills": uncovered_skills,
        "orphaned_objectives": orphaned_objectives,
        "recommendations": _skill_obj_recommendations(
            uncovered_skills, orphaned_objectives, coverage_rate
        ),
    }


def check_objective_assessment_alignment(
    objectives: list, assessment_plan: dict
) -> dict:
    """Check that each objective has assessment evidence of an appropriate type.

    Uses ``core.evidence.suggest_evidence_type`` to determine which evidence
    types are valid for a given ``goal_type``.

    Returns:
        ``{aligned: bool, issues: list[str], coverage_rate: float,
          uncovered_objectives: list[str], type_mismatches: list[str],
          recommendations: list[str]}``
    """
    issues: list[str] = []
    uncovered_objectives: list[str] = []
    type_mismatches: list[str] = []

    evidence_list = assessment_plan.get("evidence", [])
    default_goal_type = assessment_plan.get("goal_type", "")

    # Index evidence by objective
    evidence_by_obj: dict[str, list[dict]] = {}
    for ev in evidence_list:
        linked_id = ev.get("linked_objective_id", "")
        if linked_id:
            evidence_by_obj.setdefault(linked_id, []).append(ev)

    covered_count = 0
    for obj in objectives:
        oid = obj.get("objective_id", "")
        if not oid:
            continue

        ev_list = evidence_by_obj.get(oid, [])
        if not ev_list:
            uncovered_objectives.append(f"目标 {oid} 缺少对应评价证据")
            continue

        covered_count += 1

        # Validate evidence type against goal_type
        obj_goal_type = obj.get("goal_type", default_goal_type)
        if obj_goal_type:
            try:
                from core.evidence import suggest_evidence_type

                appropriate_types = suggest_evidence_type(obj_goal_type)
                for ev in ev_list:
                    ev_type = ev.get("evidence_type", "")
                    if ev_type and ev_type not in appropriate_types:
                        type_mismatches.append(
                            f"目标 {oid} 的评价类型「{ev_type}」与学习类型"
                            f"「{obj_goal_type}」不匹配，"
                            f"建议使用: {', '.join(appropriate_types)}"
                        )
            except ImportError:
                pass

    issues.extend(uncovered_objectives)
    issues.extend(type_mismatches)

    total = max(len(objectives), 1)
    coverage_rate = covered_count / total if objectives else 1.0

    return {
        "aligned": len(issues) == 0,
        "issues": issues,
        "coverage_rate": round(coverage_rate, 2),
        "uncovered_objectives": uncovered_objectives,
        "type_mismatches": type_mismatches,
        "recommendations": _obj_assess_recommendations(
            uncovered_objectives, type_mismatches, coverage_rate
        ),
    }


# ---------------------------------------------------------------------------
# MVP quality gates  (13 rules)
# ---------------------------------------------------------------------------

def check_quality_gates(project: dict) -> dict:
    """Execute the thirteen-rule MVP quality gate.

    Rules
    -----
    1. Goal not empty
    2. K12 without official sources --> draft only
    3. Goal must have learner, behaviour, context
    4. Skill graph must have goal_node, goal_steps, subordinate_skills,
       entry_behaviours
    5. Each subordinate skill has objective or is marked
       ``not_assessed_individually``
    6. Each objective has condition, behaviour, criterion
    7. No unobservable verbs (or must have suggestions)
    8. Each objective has assessment evidence
    9. Evidence type matches goal type
    10. Alignment report generated
    11. Strategy must have 5 learning components
    12. Strategy must cover key objectives
    13. Strategy must embed assessment

    Scoring
    -------
    * Start at 100 points.
    * Each critical issue: -15 points.
    * Each warning: -5 points.
    * Score clamped to [0, 100].

    Returns::

        {
            "overall_status": "pass" | "warning" | "fail",
            "score": int,
            "critical_issues": list[str],
            "warnings": list[str],
            "recommendations": list[str],
            "can_export_as_final": bool,
            "can_export_as_draft": bool,          # always True
        }
    """
    goal = project.get("goal", {})
    skill_graph = project.get("skill_graph", {})
    objectives = project.get("objectives", [])
    assessment_plan = project.get("assessment_plan", {})

    critical_issues: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []

    # --- Rule 1: Goal not empty ---
    if not goal or not any(goal.values()):
        critical_issues.append("规则 1: 教学目的为空，必须先定义教学目的")

    # --- Rule 2: K12 without official sources -> draft only ---
    goal_result = check_goal_quality(goal)
    if goal_result.get("is_draft"):
        warnings.append(
            "规则 2: K12 场景无官方来源，教学目的仅可作为草案导出"
        )
        recommendations.append("建议补充官方教材或教师确认的教学资源")

    # --- Rule 3: Goal must have learner, behaviour, context ---
    if not goal.get("learner"):
        critical_issues.append("规则 3: 教学目的缺少学习者 (learner) 描述")
    if not goal.get("behavior"):
        critical_issues.append("规则 3: 教学目的缺少行为 (behavior) 描述")
    if not goal.get("context") and not goal.get("condition"):
        critical_issues.append(
            "规则 3: 教学目的缺少应用环境 (context) 或条件 (condition)"
        )

    # --- Rule 4: Skill graph structure ---
    sg_result = check_skill_graph_quality(skill_graph)
    for issue in sg_result.get("issues", []):
        critical_issues.append(f"规则 4: {issue}")

    # --- Rule 5: Subordinate skill -> objective mapping ---
    sub_skills = skill_graph.get("subordinate_skills", [])
    obj_skill_refs: set[str] = set()
    for obj in objectives:
        ref = obj.get("linked_skill_id", "") or obj.get("skill_id", "")
        if ref:
            obj_skill_refs.add(ref)
    obj_texts = [_extract_text(obj) for obj in objectives]

    for skill in sub_skills:
        if isinstance(skill, dict) and skill.get("not_assessed_individually"):
            continue
        skill_text = _extract_text(skill)
        skill_id = _extract_skill_id(skill)
        has_obj = False
        if skill_id and skill_id in obj_skill_refs:
            has_obj = True
        elif any(_behavior_in_text(skill_text, ot) for ot in obj_texts if ot):
            has_obj = True
        if not has_obj:
            warnings.append(
                f"规则 5: 子技能「{skill_text}」缺少对应绩效目标"
            )
            recommendations.append(
                f"为子技能「{skill_text}」设计绩效目标，"
                f"或标记为 not_assessed_individually"
            )

    # --- Rule 6: Each objective has condition, behaviour, criterion ---
    obj_result = check_objectives_quality(objectives)
    for issue in obj_result.get("issues", []):
        critical_issues.append(f"规则 6: {issue}")

    # --- Rule 7: No unobservable verbs ---
    for obj in objectives:
        behavior = obj.get("behavior", "")
        if not behavior:
            continue
        found_unobservable = [v for v in _UNOBSERVABLE_VERBS if v in behavior]
        if found_unobservable:
            oid = obj.get("objective_id", "?")
            warnings.append(
                f"规则 7: 目标 {oid} 行为描述含不可观测动词: "
                f"{'、'.join(found_unobservable)}"
            )
            recommendations.append(
                f"将目标 {oid} 中的不可观测动词替换为可观测行为动词"
            )

    # --- Rule 8: Each objective has assessment evidence ---
    assess_result = check_assessment_quality(objectives, assessment_plan)
    for issue in assess_result.get("issues", []):
        critical_issues.append(f"规则 8: {issue}")

    # --- Rule 9: Evidence type matches goal type ---
    evidence_list = assessment_plan.get("evidence", [])
    default_goal_type = assessment_plan.get("goal_type", "")
    if default_goal_type and evidence_list:
        try:
            from core.evidence import suggest_evidence_type

            appropriate_types = suggest_evidence_type(default_goal_type)
            for ev in evidence_list:
                ev_type = ev.get("evidence_type", "")
                linked_id = ev.get("linked_objective_id", "")
                if ev_type and ev_type not in appropriate_types:
                    warnings.append(
                        f"规则 9: 证据「{ev_type}」(关联目标 {linked_id}) "
                        f"与学习类型「{default_goal_type}」不匹配"
                    )
                    recommendations.append(
                        f"将目标 {linked_id} 的评价类型调整为: "
                        f"{', '.join(appropriate_types)}"
                    )
        except ImportError:
            pass

    # --- Rule 10: Alignment report generated ---
    # This rule is satisfied by executing this function.
    if not project.get("quality_check"):
        recommendations.append(
            "建议将本次质量门禁检查结果保存到项目的 quality_check 字段"
        )

    # --- Rule 11: Strategy must have 5 learning components ---
    instructional_strategy = project.get("instructional_strategy", {})
    if instructional_strategy:
        learning_components = instructional_strategy.get("learning_components", [])
        if len(learning_components) < 5:
            warnings.append(
                f"规则 11: 教学策略仅包含 {len(learning_components)} 个学习成分，"
                f"建议至少包含 5 个（导入、呈现、练习、反馈、测评）"
            )
            recommendations.append(
                "补充教学策略的学习成分至 5 个：导入、呈现、练习、反馈、测评"
            )

    # --- Rule 12: Strategy must cover key objectives ---
    if instructional_strategy and objectives:
        strategy_covered = set()
        for comp in instructional_strategy.get("learning_components", []):
            for oid in comp.get("linked_objectives", []):
                strategy_covered.add(oid)
        obj_ids = {o.get("objective_id", "") for o in objectives if o.get("objective_id")}
        uncovered_by_strategy = obj_ids - strategy_covered
        if uncovered_by_strategy and obj_ids:
            warnings.append(
                f"规则 12: 教学策略未覆盖 {len(uncovered_by_strategy)} 个绩效目标: "
                f"{', '.join(sorted(uncovered_by_strategy))}"
            )
            recommendations.append(
                "在教学策略的学习成分中为未覆盖的绩效目标设计对应教学活动"
            )

    # --- Rule 13: Strategy must embed assessment ---
    if instructional_strategy:
        has_assessment = False
        for comp in instructional_strategy.get("learning_components", []):
            if comp.get("type") in ("assessment", "entry_test", "pretest", "posttest", "practice"):
                has_assessment = True
                break
        assessment_plan = project.get("assessment_plan", {})
        if assessment_plan:
            for key in ("entry_behavior_test", "pretest", "practice_evidence", "posttest"):
                if assessment_plan.get(key):
                    has_assessment = True
                    break
        if not has_assessment:
            warnings.append(
                "规则 13: 教学策略中未发现嵌入式评价环节（入门测试、前测、练习、后测）"
            )
            recommendations.append(
                "在教学策略中嵌入评价环节，确保评价与教学活动有机结合"
            )

    # --- Scoring ---
    score = 100
    score -= len(critical_issues) * 15
    score -= len(warnings) * 5
    score = max(0, min(100, score))

    # --- Overall status ---
    if critical_issues:
        overall_status = "fail"
    elif score >= 80:
        overall_status = "pass"
    elif score >= 50:
        overall_status = "warning"
    else:
        overall_status = "fail"

    # --- Project-level final export gate ---
    # Rule A: If goal.can_use_as_final_goal == false → can_export_as_final = false
    can_use_as_final_goal = goal.get("can_use_as_final_goal", False)
    verification_status = goal.get("verification_status", "unknown")

    # Rule B: If verification is draft → can_export_as_final = false
    is_draft = verification_status in ("draft_pending_verification", "draft_unverified")

    # Rule C: If any critical_issue → overall_status = fail
    # (already handled above)

    # Rule D: Check actual pairwise alignment results
    # Only block if pairwise checks actually report misalignment
    has_realignment_issues = False
    # Check for blocking-level alignment warnings
    has_blocking_alignment = False
    for w in warnings:
        if "不对齐" in w or "未覆盖" in w or "未嵌入" in w:
            has_blocking_alignment = True
            break
            break

    # Determine blocking reasons - only include real issues
    blocking_reasons = []
    if not can_use_as_final_goal:
        blocking_reasons.append("K12 教学目的缺少 A/B 级官方课程标准或教材依据")
    if is_draft:
        blocking_reasons.append("教学目的当前为待验证草案状态")
    if critical_issues:
        blocking_reasons.append("存在严重质量问题（一票否决项）")
    if has_realignment_issues or has_blocking_alignment:
        blocking_reasons.append("模块间一致性存在问题")

    # Final status determination
    can_export_as_final = (
        overall_status == "pass"
        and can_use_as_final_goal
        and not is_draft
        and not critical_issues
        and not has_blocking_alignment
    )

    # Cap score when blocking conditions exist
    if not can_export_as_final:
        if overall_status == "pass":
            overall_status = "warning"
        if blocking_reasons:
            score = min(score, 84)
        if has_blocking_alignment:
            score = min(score, 89)

    can_export_as_draft = True

    return {
        "overall_status": overall_status,
        "score": score,
        "critical_issues": critical_issues,
        "warnings": warnings,
        "recommendations": recommendations,
        "can_export_as_final": can_export_as_final,
        "can_export_as_draft": can_export_as_draft,
        "blocking_reasons": blocking_reasons,
    }


# ---------------------------------------------------------------------------
# Full alignment aggregation
# ---------------------------------------------------------------------------

def check_full_alignment(project: dict) -> dict:
    """Run all alignment checks and aggregate results.

    Returns the same top-level structure as :func:`check_quality_gates`
    plus per-check details under ``pairwise_checks``.
    """
    goal = project.get("goal", {})
    skill_graph = project.get("skill_graph", {})
    objectives = project.get("objectives", [])
    assessment_plan = project.get("assessment_plan", {})
    context_analysis = project.get("context_analysis", {})
    instructional_strategy = project.get("instructional_strategy", {})

    # Pairwise checks
    goal_skill = check_goal_analysis_alignment(goal, skill_graph)
    skill_obj = check_analysis_objective_alignment(skill_graph, objectives)
    obj_assess = check_objective_assessment_alignment(objectives, assessment_plan)

    # New pairwise checks for context/strategy/assessment integration
    ctx_strategy = check_context_strategy_alignment(
        context_analysis, instructional_strategy
    )
    obj_strategy = check_objective_strategy_alignment(
        objectives, instructional_strategy
    )
    assess_strategy = check_assessment_strategy_integration(
        assessment_plan, instructional_strategy
    )

    # Collect all pairwise check results for alignment analysis
    pairwise_check_results = [goal_skill, skill_obj, obj_assess,
                              ctx_strategy, obj_strategy, assess_strategy]

    # Quality gates
    gates = check_quality_gates(project)

    # Aggregate
    all_critical: list[str] = list(gates.get("critical_issues", []))
    all_warnings: list[str] = list(gates.get("warnings", []))
    all_recommendations: list[str] = list(gates.get("recommendations", []))

    for issue in goal_skill.get("issues", []):
        all_warnings.append(f"[目的-技能对齐] {issue}")
    for issue in skill_obj.get("issues", []):
        all_warnings.append(f"[技能-目标对齐] {issue}")
    for issue in obj_assess.get("issues", []):
        all_warnings.append(f"[目标-评价对齐] {issue}")
    for issue in ctx_strategy.get("issues", []):
        all_warnings.append(f"[情境-策略对齐] {issue}")
    for issue in obj_strategy.get("issues", []):
        all_warnings.append(f"[目标-策略对齐] {issue}")
    for issue in assess_strategy.get("issues", []):
        all_warnings.append(f"[评价-策略整合] {issue}")

    all_recommendations.extend(goal_skill.get("recommendations", []))
    all_recommendations.extend(skill_obj.get("recommendations", []))
    all_recommendations.extend(obj_assess.get("recommendations", []))
    all_recommendations.extend(ctx_strategy.get("recommendations", []))
    all_recommendations.extend(obj_strategy.get("recommendations", []))
    all_recommendations.extend(assess_strategy.get("recommendations", []))

    # Start from quality gates base score, then subtract pairwise issues
    pairwise_issue_count = (
        len(goal_skill.get("issues", []))
        + len(skill_obj.get("issues", []))
        + len(obj_assess.get("issues", []))
        + len(ctx_strategy.get("issues", []))
        + len(obj_strategy.get("issues", []))
        + len(assess_strategy.get("issues", []))
    )
    score = gates.get("score", 100) - pairwise_issue_count * 5
    score = max(0, min(100, score))

    # Determine overall status from gates + pairwise
    gates_status = gates.get("overall_status", "fail")
    if all_critical or gates_status == "fail":
        overall_status = "fail"
    elif gates_status == "warning" or score < 80:
        overall_status = "warning"
    else:
        overall_status = "pass"

    # Project-level final export gate (inherit from quality gates)
    can_use_as_final_goal = goal.get("can_use_as_final_goal", False)
    verification_status = goal.get("verification_status", "unknown")
    is_draft = verification_status in ("draft_pending_verification", "draft_unverified")

    # Check actual pairwise alignment results from check results
    has_realignment_issues = False
    for check_result in pairwise_check_results:
        if isinstance(check_result, dict) and not check_result.get("aligned", True):
            has_realignment_issues = True
            break

    # Determine blocking reasons - only include real issues
    blocking_reasons = []
    if not can_use_as_final_goal:
        blocking_reasons.append("K12 教学目的缺少 A/B 级官方课程标准或教材依据")
    if is_draft:
        blocking_reasons.append("教学目的当前为待验证草案状态")
    if all_critical:
        blocking_reasons.append("存在严重质量问题（一票否决项）")
    if has_realignment_issues:
        blocking_reasons.append("模块间一致性存在问题")

    can_export_as_final = (
        overall_status == "pass"
        and can_use_as_final_goal
        and not is_draft
        and not all_critical
        and not has_blocking_alignment
    )

    # Cap score when blocking conditions exist
    if not can_export_as_final:
        if overall_status == "pass":
            overall_status = "warning"
        if blocking_reasons:
            score = min(score, 84)

    return {
        "overall_status": overall_status,
        "score": score,
        "critical_issues": all_critical,
        "warnings": all_warnings,
        "recommendations": all_recommendations,
        "can_export_as_final": can_export_as_final,
        "can_export_as_draft": True,
        "blocking_reasons": blocking_reasons,
        "pairwise_checks": {
            "goal_skill_alignment": goal_skill,
            "skill_objective_alignment": skill_obj,
            "objective_assessment_alignment": obj_assess,
            "context_strategy_alignment": ctx_strategy,
            "objective_strategy_alignment": obj_strategy,
            "assessment_strategy_integration": assess_strategy,
        },
        "quality_gates": gates,
    }


# ---------------------------------------------------------------------------
# Context / Strategy / Assessment integration checks
# ---------------------------------------------------------------------------

def check_context_strategy_alignment(context_analysis: dict, instructional_strategy: dict) -> dict:
    """
    Check that instructional strategy responds to learner and environment analysis.

    Handles both the normalised format (from ``pipeline.py``) and raw
    engine outputs by checking multiple possible key locations.

    Checks:
    - Strategy addresses at least some implications from context analysis
    - Strategy considers device/media constraints
    - Strategy considers class duration
    - Strategy considers common difficulties

    Returns: {aligned: bool, issues: list, coverage_rate: float, recommendations: list}
    """
    issues: list[str] = []
    recommendations: list[str] = []

    if not context_analysis:
        return {
            "aligned": True,
            "issues": [],
            "coverage_rate": 1.0,
            "recommendations": ["缺少情境分析数据，无法评估情境-策略对齐"],
        }

    if not instructional_strategy:
        return {
            "aligned": False,
            "issues": ["缺少教学策略数据，无法评估情境-策略对齐"],
            "coverage_rate": 0.0,
            "recommendations": ["请先设计教学策略"],
        }

    # --- Collect implications from various possible locations ------------
    implications = context_analysis.get("implications", [])
    # Also check strategy_implications (pipeline normalisation stores both)
    if not implications:
        raw_imps = context_analysis.get("strategy_implications", [])
        implications = [
            imp.get("implication", str(imp)) if isinstance(imp, dict) else str(imp)
            for imp in raw_imps
        ]

    # Strategy-side addressed implications
    addressed = instructional_strategy.get("addressed_implications", [])
    # Also check responded_context_implications (normalised key)
    if not addressed:
        addressed = instructional_strategy.get("responded_context_implications", [])

    # --- Check 1: Strategy addresses implications ----------------------
    covered_count = 0
    for imp in implications:
        imp_text = _extract_text(imp) if not isinstance(imp, str) else imp
        if any(_behavior_in_text(imp_text, _extract_text(s) if not isinstance(s, str) else s)
               for s in addressed):
            covered_count += 1

    # Require at least some coverage if implications exist
    min_required = min(3, len(implications)) if implications else 0
    if implications and covered_count < min_required:
        issues.append(
            f"教学策略仅回应了 {covered_count}/{len(implications)} 个情境分析推论，"
            f"建议至少回应 {min_required} 个关键推论"
        )

    # --- Check 2: Device / media constraints ---------------------------
    device_constraints = context_analysis.get("device_constraints", {})
    learning_ctx = context_analysis.get("learning_context", {})
    # Flatten devices if nested
    devices_desc = learning_ctx.get("devices", "") if isinstance(learning_ctx, dict) else ""
    if isinstance(devices_desc, dict):
        devices_desc = devices_desc.get("description", "")

    if device_constraints or devices_desc:
        strategy_media = instructional_strategy.get("media_plan", {})
        strategy_devices = strategy_media.get("devices", [])
        media_delivery = instructional_strategy.get("media_and_delivery", {})
        media_list = media_delivery.get("media", []) if isinstance(media_delivery, dict) else []
        if not strategy_devices and not media_list:
            # Only flag if we actually detected constraints
            has_constraint_kw = False
            constraint_text = json.dumps(device_constraints, ensure_ascii=False) if isinstance(device_constraints, dict) else str(devices_desc)
            for kw in ["无", "不足", "缺少", "没有", "limited", "none"]:
                if kw in constraint_text.lower():
                    has_constraint_kw = True
                    break
            if has_constraint_kw:
                issues.append("教学策略未考虑设备/媒体约束条件")
                recommendations.append("根据学习者可用设备设计对应媒体方案")

    # --- Check 3: Class duration ----------------------------------------
    class_duration = context_analysis.get("class_duration", "")
    if not class_duration and isinstance(learning_ctx, dict):
        class_duration = learning_ctx.get("class_duration", "")
    if class_duration:
        strategy_duration = (
            instructional_strategy.get("total_duration", "")
            or instructional_strategy.get("total_duration_minutes", "")
            or instructional_strategy.get("lesson_duration", "")
        )
        if not strategy_duration:
            issues.append(f"教学策略未考虑课时安排（{class_duration}）")
            recommendations.append("根据课时安排规划教学活动时间分配")

    # --- Check 4: Common difficulties -----------------------------------
    difficulties = context_analysis.get("common_difficulties", [])
    if not difficulties:
        learner_profile = context_analysis.get("learner_profile", {})
        if isinstance(learner_profile, dict):
            difficulties = learner_profile.get("common_difficulties", [])
    if difficulties:
        strategy_difficulties = instructional_strategy.get("anticipated_difficulties", [])
        # Also check differentiation in components
        components = instructional_strategy.get("components", {})
        part = components.get("learner_participation", {})
        differentiation = part.get("differentiation", []) if isinstance(part, dict) else []
        if not strategy_difficulties and not differentiation:
            issues.append("教学策略未考虑学习者常见困难")
            recommendations.append("分析学习者常见困难并设计针对性的教学策略")

    total_checks = 4
    passed_checks = total_checks - len(issues)
    coverage_rate = passed_checks / total_checks if total_checks > 0 else 1.0

    return {
        "aligned": len(issues) == 0,
        "issues": issues,
        "coverage_rate": round(coverage_rate, 2),
        "recommendations": recommendations,
    }


def check_objective_strategy_alignment(objectives: list, instructional_strategy: dict) -> dict:
    """
    Check that instructional strategy covers all key performance objectives.

    Checks both the normalised ``learning_components`` list and the raw
    ``components`` dict so that the check works whether or not the
    project was run through ``pipeline.py``.

    Returns: {aligned: bool, issues: list, coverage_rate: float, uncovered_objectives: list}
    """
    issues: list[str] = []
    uncovered_objectives: list[str] = []
    recommendations: list[str] = []

    if not objectives:
        return {
            "aligned": True,
            "issues": [],
            "coverage_rate": 1.0,
            "uncovered_objectives": [],
            "recommendations": [],
        }

    if not instructional_strategy:
        return {
            "aligned": False,
            "issues": ["缺少教学策略数据，无法评估目标-策略对齐"],
            "coverage_rate": 0.0,
            "uncovered_objectives": [o.get("objective_id", "?") for o in objectives],
            "recommendations": ["请先设计教学策略"],
        }

    # --- Collect covered objective IDs from multiple sources ------------
    covered_ids: set[str] = set()

    # Source 1: normalised learning_components
    for comp in instructional_strategy.get("learning_components", []):
        for oid in comp.get("linked_objectives", []):
            if oid:
                covered_ids.add(oid)

    # Source 2: raw components dict (strategy_engine output)
    components = instructional_strategy.get("components", {})
    if isinstance(components, dict):
        for comp_name, comp_data in components.items():
            if isinstance(comp_data, dict):
                for oid in comp_data.get("linked_objectives", []):
                    if oid:
                        covered_ids.add(oid)

    # Source 3: covered_objective_ids (normalised top-level list)
    for oid in instructional_strategy.get("covered_objective_ids", []):
        if oid:
            covered_ids.add(oid)

    # Source 4: lesson_segments
    segments = instructional_strategy.get("segments", [])
    if isinstance(segments, list):
        for seg in segments:
            for obj in seg.get("objectives", []):
                if isinstance(obj, dict):
                    oid = obj.get("objective_id", obj.get("id", ""))
                    if oid:
                        covered_ids.add(oid)
                elif isinstance(obj, str) and obj:
                    covered_ids.add(obj)

    # --- Check each objective -------------------------------------------
    for obj in objectives:
        oid = obj.get("objective_id", "")
        if oid and oid not in covered_ids:
            uncovered_objectives.append(oid)
            issues.append(f"绩效目标 {oid} 未被教学策略覆盖")

    if uncovered_objectives:
        recommendations.append(
            f"在教学策略中为 {len(uncovered_objectives)} 个未覆盖的目标设计对应教学活动"
        )

    total = max(len(objectives), 1)
    coverage_rate = (total - len(uncovered_objectives)) / total

    return {
        "aligned": len(issues) == 0,
        "issues": issues,
        "coverage_rate": round(coverage_rate, 2),
        "uncovered_objectives": uncovered_objectives,
        "recommendations": recommendations,
    }


def check_assessment_strategy_integration(assessment_plan: dict, instructional_strategy: dict) -> dict:
    """
    Check that entry test, pretest, practice, posttest are embedded in strategy.

    Checks both the normalised ``learning_components`` list and the raw
    ``components`` dict so that the check works whether or not the
    project was run through ``pipeline.py``.

    Returns: {integrated: bool, issues: list, integration_rate: float}
    """
    issues: list[str] = []
    recommendations: list[str] = []

    if not assessment_plan:
        return {
            "integrated": True,
            "issues": [],
            "integration_rate": 1.0,
            "recommendations": ["缺少评价方案数据，无法评估评价-策略整合"],
        }

    if not instructional_strategy:
        return {
            "integrated": False,
            "issues": ["缺少教学策略数据，无法评估评价-策略整合"],
            "integration_rate": 0.0,
            "recommendations": ["请先设计教学策略"],
        }

    # Assessment types to check
    assessment_components = {
        "entry_behavior_test": "入门技能测试",
        "pretest": "前测",
        "practice_evidence": "练习",
        "posttest": "后测",
    }

    # Build lookup sets from strategy
    strategy_components = instructional_strategy.get("learning_components", [])
    # Fallback: build from raw components
    if not strategy_components:
        raw_components = instructional_strategy.get("components", {})
        assess_raw = raw_components.get("assessment", {})
        if isinstance(assess_raw, dict):
            assess_items = assess_raw.get("assessments", [])
            strategy_components = [
                {"type": "assessment", "embedded_assessments": [a.get("type", "") for a in assess_items]}
            ]

    # Also check the assessment_strategy key (raw engine output)
    assess_strategy_raw = instructional_strategy.get("assessment_strategy", {})
    raw_assess_items = []
    if isinstance(assess_strategy_raw, dict):
        raw_assess_items = assess_strategy_raw.get("assessments", [])

    # Build a set of all assessment types present in strategy
    strategy_assessment_types: set[str] = set()
    for comp in strategy_components:
        comp_type = comp.get("type", "")
        if comp_type == "assessment":
            strategy_assessment_types.add("assessment")
        for a in comp.get("embedded_assessments", []):
            strategy_assessment_types.add(a)
    for item in raw_assess_items:
        if isinstance(item, dict):
            strategy_assessment_types.add(item.get("type", ""))

    embedded_count = 0
    total_components = 0

    for key, label in assessment_components.items():
        if assessment_plan.get(key):
            total_components += 1
            is_embedded = False

            # Check normalised learning_components
            for comp in strategy_components:
                comp_type = comp.get("type", "")
                comp_assessments = comp.get("embedded_assessments", [])
                if (comp_type in (key, "assessment")
                    or key in comp_assessments
                    or label in _extract_text(comp)):
                    is_embedded = True
                    break

            # Check raw assessment types
            if not is_embedded:
                # Map assessment_plan key to strategy_engine assessment type
                type_mapping = {
                    "entry_behavior_test": "entry_behavior_test",
                    "pretest": "pretest",
                    "practice_evidence": "practice",
                    "posttest": "posttest",
                }
                mapped_type = type_mapping.get(key, key)
                if mapped_type in strategy_assessment_types:
                    is_embedded = True

            # Check raw components.assessment.assessments list
            if not is_embedded:
                for item in raw_assess_items:
                    if isinstance(item, dict) and item.get("type") == key.replace("_evidence", ""):
                        is_embedded = True
                        break

            if is_embedded:
                embedded_count += 1
            else:
                issues.append(f"评价组件「{label}」未嵌入教学策略中")
                recommendations.append(
                    f"在教学策略的学习成分中嵌入「{label}」环节"
                )

    integration_rate = embedded_count / total_components if total_components > 0 else 1.0

    return {
        "integrated": len(issues) == 0,
        "issues": issues,
        "integration_rate": round(integration_rate, 2),
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# Stub functions (imported by tools/__init__.py -- kept for compatibility)
# ---------------------------------------------------------------------------

def check_analysis_learner_alignment(
    skill_graph: dict, learner_analysis: dict
) -> dict:
    """Check alignment between skill analysis and learner characteristics.

    Stub -- not yet implemented.
    """
    return {
        "aligned": True,
        "score": 0.0,
        "issues": [],
        "mismatches": [],
        "pacing_concerns": [],
        "recommendations": ["学习者对齐检查尚未实现"],
    }


def check_assessment_strategy_alignment(
    assessment: dict, strategy: dict
) -> dict:
    """Check alignment between assessment plan and instructional strategy.

    Stub -- not yet implemented.
    """
    return {
        "aligned": True,
        "score": 0.0,
        "issues": [],
        "unlinked_assessments": [],
        "missing_strategy_activities": [],
        "recommendations": ["评价-策略对齐检查尚未实现"],
    }


def check_strategy_material_alignment(
    strategy: dict, materials: list[dict]
) -> dict:
    """Check alignment between instructional strategy and materials.

    Stub -- not yet implemented.
    """
    return {
        "aligned": True,
        "score": 0.0,
        "issues": [],
        "unsupported_activities": [],
        "unlinked_materials": [],
        "recommendations": ["策略-材料对齐检查尚未实现"],
    }


def check_quality_gate(module_id: str, module_output: dict) -> dict:
    """Evaluate a design module output against quality gate criteria.

    Stub -- not yet implemented.
    """
    return {
        "module_id": module_id,
        "gate_decision": "conditional_pass",
        "criteria": [],
        "blocking_issues": [],
        "warnings": [],
        "recommendations": [f"模块 {module_id} 质量门禁检查尚未实现"],
    }
