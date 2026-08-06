"""Objective Generation Engine Module.

Deterministic engine for generating and validating performance objectives
from a skill graph. Produces one objective per goal_step and
subordinate_skill, checks each behaviour verb for observability, and
returns the collection together with any issues found.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from core.ids import gen_objective_id
from core.verbs import (
    check_observable_verb,
    suggest_observable_behavior,
    UNOBSERVABLE_VERBS,
)

# ---------------------------------------------------------------------------
# Condition / criterion heuristics keyed on goal_type
# ---------------------------------------------------------------------------

_CONDITION_TEMPLATES: dict[str, str] = {
    "verbal_information": "给定相关的学习材料或情境提示",
    "intellectual_skill": "给定适当的例题或问题情境",
    "psychomotor_skill": "给定必要的工具、设备或操作环境",
    "attitude": "给定包含价值判断的学习情境",
}

_CRITERIA_TEMPLATES: dict[str, str] = {
    "verbal_information": "正确复述或列举要点，准确率>=80%",
    "intellectual_skill": "完成任务，结果正确且步骤完整",
    "psychomotor_skill": "按规范操作，流程正确且结果达标",
    "attitude": "在情境中做出合理的价值判断或选择",
}


# ---------------------------------------------------------------------------
# Helper – derive a keyword from behaviour text for template filling
# ---------------------------------------------------------------------------

def _extract_topic(behaviour: str) -> str:
    """Return the full behaviour text for use in condition templates.

    Uses the complete skill description instead of slicing, to avoid
    truncated phrases like '后顺序' or '然语言'.
    """
    return behaviour.strip() if behaviour else ""


def _generate_condition(behavior: str, goal_type: str, step_desc: str) -> str:
    """Generate a reasonable condition string for an objective.

    Uses the full skill description in the condition, avoiding truncation.
    """
    base = _CONDITION_TEMPLATES.get(
        goal_type, _CONDITION_TEMPLATES["intellectual_skill"]
    )
    # Use the full behavior/skill description, not a sliced topic
    if behavior and behavior.strip():
        return f'{base}，围绕"{behavior.strip()}"完成任务'
    return base


def _generate_criterion(behavior: str, goal_type: str, step_desc: str) -> str:
    """Generate a reasonable criterion string for an objective."""
    return _CRITERIA_TEMPLATES.get(
        goal_type, _CRITERIA_TEMPLATES["intellectual_skill"]
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_performance_objectives(
    skill_graph: dict, context: dict | None = None
) -> dict:
    """Generate performance objectives for all goal_steps and subordinate_skills.

    Each objective contains: objective_id, related_skill_id, condition,
    behaviour, criterion, goal_type, and status.

    Args:
        skill_graph: A dictionary with at least ``goal_steps`` (list of step
            dicts) and ``subordinate_skills`` (list of skill dicts).  Each
            step/skill is expected to have ``description`` and
            ``goal_type`` keys; steps use ``step_id`` and skills use
            ``skill_id``.
        context: Optional instructional context dictionary (currently unused
            reserved for future enhancement).

    Returns:
        A dictionary with keys:
            - objectives: list of objective dicts
            - issues: list of issue dicts for any problems found
            - requires_teacher_confirmation: bool, True when warnings exist
    """
    objectives: list[dict] = []
    issues: list[dict] = []

    goal_steps = skill_graph.get("goal_steps", [])
    sub_skills = skill_graph.get("subordinate_skills", [])

    # --- process goal steps ---
    for step in goal_steps:
        description = step.get("description", "")
        goal_type = step.get("goal_type", step.get("learning_type", "intellectual_skill"))
        skill_id = step.get("step_id", step.get("skill_id", ""))

        verb_check = check_observable_verb(description)

        # Auto-replace weak verbs with suggested observable behavior
        behavior = description
        original_behavior = None
        if not verb_check["is_observable"]:
            suggestion = suggest_observable_behavior(description, goal_type)
            suggested_behaviors = suggestion.get("suggested_behaviors", [])
            if suggested_behaviors:
                original_behavior = description
                behavior = suggested_behaviors[0]
            status = "warning"
        else:
            status = "pass"

        condition = _generate_condition(behavior, goal_type, description)
        criterion = _generate_criterion(behavior, goal_type, description)

        objective = {
            "objective_id": gen_objective_id(),
            "related_skill_id": skill_id,
            "condition": condition,
            "behavior": behavior,
            "criterion": criterion,
            "goal_type": goal_type,
            "status": status,
        }
        if original_behavior:
            objective["original_behavior"] = original_behavior
            objective["suggested_behavior"] = behavior

        objectives.append(objective)

        if not verb_check["is_observable"]:
            issues.append({
                "objective_id": objective["objective_id"],
                "severity": "warning",
                "field": "behavior",
                "message": f"行为描述中包含不可观测动词: {', '.join(verb_check['unobservable_verbs'])}",
                "suggestions": verb_check["suggestions"],
                "recommendation": verb_check["recommendation"],
                "original_behavior": original_behavior,
                "suggested_behavior": behavior,
            })

    # --- process subordinate skills ---
    for skill in sub_skills:
        description = skill.get("description", skill.get("name", ""))
        goal_type = skill.get("goal_type", skill.get("learning_type", "intellectual_skill"))
        skill_id = skill.get("skill_id", "")

        verb_check = check_observable_verb(description)

        # Auto-replace weak verbs
        behavior = description
        original_behavior = None
        if not verb_check["is_observable"]:
            suggestion = suggest_observable_behavior(description, goal_type)
            suggested_behaviors = suggestion.get("suggested_behaviors", [])
            if suggested_behaviors:
                original_behavior = description
                behavior = suggested_behaviors[0]
            status = "warning"
        else:
            status = "pass"

        condition = _generate_condition(behavior, goal_type, description)
        criterion = _generate_criterion(behavior, goal_type, description)

        objective = {
            "objective_id": gen_objective_id(),
            "related_skill_id": skill_id,
            "condition": condition,
            "behavior": behavior,
            "criterion": criterion,
            "goal_type": goal_type,
            "status": status,
        }
        if original_behavior:
            objective["original_behavior"] = original_behavior
            objective["suggested_behavior"] = behavior

        objectives.append(objective)

        if not verb_check["is_observable"]:
            issues.append({
                "objective_id": objective["objective_id"],
                "severity": "warning",
                "field": "behavior",
                "message": f"行为描述中包含不可观测动词: {', '.join(verb_check['unobservable_verbs'])}",
                "suggestions": verb_check["suggestions"],
                "recommendation": verb_check["recommendation"],
                "original_behavior": original_behavior,
                "suggested_behavior": behavior,
            })

    return {
        "objectives": objectives,
        "issues": issues,
        "requires_teacher_confirmation": len(issues) > 0,
    }


def validate_performance_objective(objective: dict) -> dict:
    """Validate a single performance objective.

    Checks that condition, behaviour, and criterion are present and
    non-empty, and that the behaviour verb is observable.

    Args:
        objective: A dict with keys ``condition``, ``behavior``,
            ``criterion``, and optionally ``goal_type``.

    Returns:
        A dictionary with keys:
            - passed: bool
            - issues: list of issue dicts
            - verb_check: the raw result from core.verbs.check_observable_verb
    """
    issues: list[dict] = []

    # Check required fields
    for field, label in [
        ("condition", "条件"),
        ("behavior", "行为"),
        ("criterion", "标准"),
    ]:
        value = objective.get(field, "")
        if not value or not value.strip():
            issues.append({
                "severity": "error",
                "field": field,
                "message": f"缺少{label}描述",
                "suggestion": f"请为该目标添加明确的{label}描述",
            })

    # Check verb observability
    behavior = objective.get("behavior", "")
    verb_check = check_observable_verb(behavior) if behavior else {
        "is_observable": False,
        "found_verbs": [],
        "unobservable_verbs": [],
        "suggestions": {},
        "recommendation": "行为描述为空，无法检查动词可观测性",
    }

    # Generate suggestions for weak verbs
    suggested_behavior = None
    suggested_objective = None
    if not verb_check["is_observable"] and behavior:
        goal_type = objective.get("goal_type", "intellectual_skill")
        suggestion = suggest_observable_behavior(behavior, goal_type)
        suggested_behaviors = suggestion.get("suggested_behaviors", [])
        if suggested_behaviors:
            suggested_behavior = suggested_behaviors[0]
            suggested_objective = {
                "condition": objective.get("condition", ""),
                "behavior": suggested_behavior,
                "criterion": objective.get("criterion", ""),
            }
        issues.append({
            "severity": "warning",
            "field": "behavior",
            "message": verb_check["recommendation"],
            "suggestions": verb_check["suggestions"],
        })

    all_errors = [i for i in issues if i["severity"] == "error"]
    passed = len(all_errors) == 0

    result = {
        "passed": passed,
        "issues": issues,
        "verb_check": verb_check,
    }
    if suggested_behavior:
        result["suggested_behavior"] = suggested_behavior
    if suggested_objective:
        result["suggested_objective"] = suggested_objective
    if not verb_check["is_observable"]:
        result["weak_verbs"] = verb_check.get("unobservable_verbs", [])

    return result


# ---------------------------------------------------------------------------
# Delegate wrappers
# ---------------------------------------------------------------------------

def check_observable_verb(behavior: str) -> dict:  # noqa: F811 – re-exports
    """Delegate to core.verbs.check_observable_verb."""
    from core.verbs import check_observable_verb as _check
    return _check(behavior)


def suggest_observable_behavior(weak_behavior: str, goal_type: str) -> dict:
    """Delegate to core.verbs.suggest_observable_behavior."""
    from core.verbs import suggest_observable_behavior as _suggest
    return _suggest(weak_behavior, goal_type)
