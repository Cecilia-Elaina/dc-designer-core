"""Assessment Generation Engine Module.

Deterministic engine for producing assessment plans aligned to
instructional objectives.  Creates evidence entries for each objective,
generates entry-behaviour tests, pretests, practice-evidence items, and
posttests, then validates full coverage.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from core.ids import gen_assessment_id
from core.evidence import (
    generate_evidence_for_objective as _core_generate_evidence,
    EVIDENCE_BY_GOAL_TYPE,
    EVIDENCE_TYPE_NAMES,
)


# ---------------------------------------------------------------------------
# Topic-specific evidence templates
# ---------------------------------------------------------------------------

_ALGORITHM_ENTRY_TEST = {
    "task_prompt": '给出一个生活任务，如"泡一杯热牛奶"，让学生按顺序写出4-6个步骤',
    "expected_evidence": '学生能用"先、再、然后、最后"等顺序词写出完整步骤',
    "scoring_criteria": [
        {"criterion": "步骤完整性", "description": "包含4个以上步骤", "max_score": 2},
        {"criterion": "顺序合理性", "description": "步骤先后顺序正确", "max_score": 2},
        {"criterion": "语言规范", "description": "使用顺序词描述", "max_score": 1},
    ],
}

_ALGORITHM_PRETEST = {
    "task_prompt": '给出一个简单问题情境（如"整理书包"），让学生判断哪一组步骤更清晰，并说明理由',
    "expected_evidence": "学生能比较两组步骤的优劣，指出清晰步骤的特征",
    "scoring_criteria": [
        {"criterion": "判断正确", "description": "正确识别更清晰的步骤组", "max_score": 1},
        {"criterion": "理由合理", "description": "能说明判断依据", "max_score": 2},
    ],
}

_ALGORITHM_PRACTICE = {
    "task_prompt": '小组选择一个校园生活问题（如"组织课间操"），用自然语言写出算法步骤，并互相检查是否存在步骤缺漏、重复或顺序错误',
    "expected_evidence": "小组合作产出3-5个步骤的算法描述，能互相检查并修正",
    "scoring_criteria": [
        {"criterion": "问题明确", "description": "清晰定义要解决的问题", "max_score": 1},
        {"criterion": "步骤合理", "description": "步骤顺序正确、无遗漏", "max_score": 2},
        {"criterion": "互评质量", "description": "能发现并指出他人步骤中的问题", "max_score": 2},
    ],
}

_ALGORITHM_POSTTEST = {
    "task_prompt": '给定一个新的生活问题情境（如"制作三明治"），学生独立用自然语言或流程图描述解决该问题的算法过程',
    "expected_evidence": "学生独立完成包含4-6个步骤的算法描述，步骤完整、顺序合理、表达清晰",
    "scoring_criteria": [
        {"criterion": "问题目标明确", "description": "清楚说明要解决的问题", "max_score": 1},
        {"criterion": "步骤顺序合理", "description": "步骤先后顺序正确", "max_score": 2},
        {"criterion": "表达清晰", "description": "使用顺序词或流程图规范表达", "max_score": 2},
        {"criterion": "过程完整", "description": "覆盖从输入到输出的完整过程", "max_score": 1},
    ],
}


def _detect_topic_from_objectives(objectives: list) -> str | None:
    """Detect a topic from the objectives' behavior text."""
    text = " ".join(obj.get("behavior", "") for obj in objectives)
    text += " ".join(obj.get("condition", "") for obj in objectives)
    if "算法" in text or "流程图" in text:
        return "algorithm"
    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _generate_entry_behavior_test(
    objectives: list, context: dict | None
) -> dict:
    """Build an entry-behaviour test with topic-specific or generic tasks."""
    topic = _detect_topic_from_objectives(objectives)

    if topic == "algorithm":
        return {
            "test_id": gen_assessment_id(),
            "title": "入门行为测试",
            "purpose": "检测学习者是否具备开始学习算法的前提知识和技能",
            "items": [{
                "item_id": gen_assessment_id(),
                "item_type": "performance_task",
                "task_prompt": _ALGORITHM_ENTRY_TEST["task_prompt"],
                "expected_evidence": _ALGORITHM_ENTRY_TEST["expected_evidence"],
                "scoring_criteria": _ALGORITHM_ENTRY_TEST["scoring_criteria"],
                "difficulty": "easy",
            }],
            "scoring_rubric": {
                "pass_threshold": 0.7,
                "description": "总分达到70%以上视为通过",
            },
            "estimated_minutes": 5,
        }

    # Generic fallback
    items: list[dict] = []
    for obj in objectives[:3]:  # Only first 3 for entry test
        items.append({
            "item_id": gen_assessment_id(),
            "objective_id": obj.get("objective_id", ""),
            "item_type": "multiple_choice",
            "task_prompt": f"关于\"{obj.get('behavior', '')}\"的基础知识检测",
            "expected_evidence": "学习者能正确回答基础问题",
            "scoring_criteria": [
                {"criterion": "正确性", "description": "答案正确", "max_score": 1},
            ],
            "options": ["是", "否", "不确定"],
            "correct_answer": "是",
            "difficulty": "easy",
        })

    return {
        "test_id": gen_assessment_id(),
        "title": "入门行为测试",
        "purpose": "检测学习者是否具备开始学习所需的前提知识和技能",
        "items": items,
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "description": "正确回答70%以上视为通过",
        },
        "estimated_minutes": max(5, len(items) * 1),
    }


def _generate_pretest(
    objectives: list, context: dict | None
) -> dict:
    """Build a diagnostic pretest with topic-specific or generic tasks."""
    topic = _detect_topic_from_objectives(objectives)

    if topic == "algorithm":
        return {
            "test_id": gen_assessment_id(),
            "title": "诊断性前测",
            "purpose": "了解学习者对算法概念的已有认知水平",
            "items": [{
                "item_id": gen_assessment_id(),
                "item_type": "constructed_response",
                "task_prompt": _ALGORITHM_PRETEST["task_prompt"],
                "expected_evidence": _ALGORITHM_PRETEST["expected_evidence"],
                "scoring_criteria": _ALGORITHM_PRETEST["scoring_criteria"],
                "difficulty": "easy",
            }],
            "scoring_rubric": {
                "description": "记录回答质量，用于教学调整",
            },
            "estimated_minutes": 8,
        }

    # Generic fallback
    items: list[dict] = []
    for obj in objectives:
        goal_type = obj.get("goal_type", "intellectual_skill")
        item_type = (
            "multiple_choice"
            if goal_type == "verbal_information"
            else "constructed_response"
        )
        items.append({
            "item_id": gen_assessment_id(),
            "objective_id": obj.get("objective_id", ""),
            "item_type": item_type,
            "task_prompt": f"关于\"{obj.get('behavior', '')}\"的前测题",
            "expected_evidence": "学习者展示已有知识水平",
            "scoring_criteria": [
                {"criterion": "正确性", "description": "答案正确", "max_score": 1},
            ],
            "options": ["A", "B", "C", "D"] if item_type == "multiple_choice" else [],
            "correct_answer": "A" if item_type == "multiple_choice" else "",
            "difficulty": "easy",
        })

    return {
        "test_id": gen_assessment_id(),
        "title": "诊断性前测",
        "purpose": "了解学习者在教学开始前的已有知识水平，以便调整教学策略",
        "items": items,
        "scoring_rubric": {
            "description": "记录各题正确率，用于教学调整",
        },
        "estimated_minutes": max(10, len(items) * 2),
    }


def _generate_practice_evidence(
    objectives: list, context: dict | None
) -> dict:
    """Build formative practice-evidence with topic-specific or generic tasks."""
    topic = _detect_topic_from_objectives(objectives)

    if topic == "algorithm":
        return {
            "test_id": gen_assessment_id(),
            "title": "形成性练习证据",
            "purpose": "在教学过程中收集学习者的形成性评价数据",
            "items": [{
                "item_id": gen_assessment_id(),
                "evidence_type": "performance_task",
                "evidence_type_name": "表现性任务",
                "task_prompt": _ALGORITHM_PRACTICE["task_prompt"],
                "expected_evidence": _ALGORITHM_PRACTICE["expected_evidence"],
                "scoring_criteria": _ALGORITHM_PRACTICE["scoring_criteria"],
                "feedback": "完成任务后小组互评，指出步骤中的问题",
                "difficulty": "medium",
            }],
            "estimated_minutes": 15,
        }

    # Generic fallback
    items: list[dict] = []
    for obj in objectives:
        goal_type = obj.get("goal_type", "intellectual_skill")
        suggested = EVIDENCE_BY_GOAL_TYPE.get(
            goal_type, EVIDENCE_BY_GOAL_TYPE["intellectual_skill"]
        )
        evidence_type = suggested[0] if suggested else "constructed_response"
        evidence_name = EVIDENCE_TYPE_NAMES.get(evidence_type, evidence_type)

        items.append({
            "item_id": gen_assessment_id(),
            "objective_id": obj.get("objective_id", ""),
            "evidence_type": evidence_type,
            "evidence_type_name": evidence_name,
            "task_prompt": f"在学习过程中，要求学习者完成：{obj.get('behavior', '')}",
            "expected_evidence": f"学习者在{obj.get('condition', '适当条件')}下完成任务",
            "scoring_criteria": [
                {"criterion": "完成度", "description": "任务完成情况", "max_score": 2},
                {"criterion": "正确性", "description": "结果正确性", "max_score": 2},
            ],
            "feedback": "完成任务后给予即时反馈，指出不足之处",
            "difficulty": "medium",
        })

    return {
        "test_id": gen_assessment_id(),
        "title": "形成性练习证据",
        "purpose": "在教学过程中收集学习者的形成性评价数据",
        "items": items,
        "estimated_minutes": max(15, len(items) * 3),
    }


def _generate_posttest(
    objectives: list, context: dict | None
) -> dict:
    """Build a summative posttest with topic-specific or generic tasks."""
    topic = _detect_topic_from_objectives(objectives)

    if topic == "algorithm":
        return {
            "test_id": gen_assessment_id(),
            "title": "总结性后测",
            "purpose": "评估学习者是否达成算法理解的教学目标",
            "items": [{
                "item_id": gen_assessment_id(),
                "item_type": "performance_task",
                "task_prompt": _ALGORITHM_POSTTEST["task_prompt"],
                "expected_evidence": _ALGORITHM_POSTTEST["expected_evidence"],
                "scoring_criteria": _ALGORITHM_POSTTEST["scoring_criteria"],
                "bloom_level": "apply",
                "difficulty": "medium",
            }],
            "scoring_rubric": {
                "pass_threshold": 0.6,
                "description": "总分达到60%视为达标",
            },
            "estimated_minutes": 15,
            "pass_threshold": 0.6,
        }

    # Generic fallback
    items: list[dict] = []
    for obj in objectives:
        goal_type = obj.get("goal_type", "intellectual_skill")
        suggested = EVIDENCE_BY_GOAL_TYPE.get(
            goal_type, EVIDENCE_BY_GOAL_TYPE["intellectual_skill"]
        )
        evidence_type = suggested[0] if suggested else "constructed_response"

        items.append({
            "item_id": gen_assessment_id(),
            "objective_id": obj.get("objective_id", ""),
            "item_type": evidence_type,
            "task_prompt": (
                f"在{obj.get('condition', '适当条件')}下，"
                f"{obj.get('behavior', '')}"
            ),
            "expected_evidence": f"学习者达到{obj.get('criterion', '规定标准')}",
            "scoring_criteria": [
                {"criterion": "正确性", "description": "结果正确", "max_score": 2},
                {"criterion": "完整性", "description": "过程完整", "max_score": 2},
            ],
            "bloom_level": _goal_type_to_bloom(goal_type),
            "difficulty": "medium",
        })

    return {
        "test_id": gen_assessment_id(),
        "title": "总结性后测",
        "purpose": "评估学习者是否达成全部教学目标",
        "items": items,
        "scoring_rubric": {
            "pass_threshold": 0.6,
            "description": "总分达到60%视为达标",
        },
        "estimated_minutes": max(20, len(items) * 3),
        "pass_threshold": 0.6,
    }


def _goal_type_to_bloom(goal_type: str) -> str:
    """Map a goal_type to an approximate Bloom's taxonomy level."""
    mapping = {
        "verbal_information": "remember",
        "intellectual_skill": "apply",
        "psychomotor_skill": "apply",
        "attitude": "evaluate",
    }
    return mapping.get(goal_type, "apply")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_assessment_plan(
    objectives: list, context: dict | None = None
) -> dict:
    """Generate a complete assessment plan from a list of objectives.

    Produces four assessment phases -- entry-behaviour test, pretest,
    formative practice evidence, and summative posttest -- each aligned
    to the supplied objectives via ``core.evidence``.

    Args:
        objectives: A list of objective dicts.  Each must contain at least
            ``objective_id``, ``behavior``, ``goal_type``, ``condition``,
            and ``criterion``.
        context: Optional instructional context dictionary (reserved for
            future enhancement).

    Returns:
        A dictionary with keys:
            - entry_behavior_test: the prerequisite verification test
            - pretest: the diagnostic pretest
            - practice_evidence: formative practice-evidence items
            - posttest: the summative posttest
            - evidence: a flat list of individual evidence dicts (one per
              objective) for downstream consumers
    """
    evidence_list: list[dict] = []
    for obj in objectives:
        evidence = _core_generate_evidence(obj)
        evidence_list.append(evidence)

    entry_behavior_test = _generate_entry_behavior_test(objectives, context)
    pretest = _generate_pretest(objectives, context)
    practice_evidence = _generate_practice_evidence(objectives, context)
    posttest = _generate_posttest(objectives, context)

    return {
        "entry_behavior_test": entry_behavior_test,
        "pretest": pretest,
        "practice_evidence": practice_evidence,
        "posttest": posttest,
        "evidence": evidence_list,
    }


def generate_evidence_for_objective(objective: dict) -> dict:
    """Delegate to core.evidence.generate_evidence_for_objective."""
    return _core_generate_evidence(objective)


def validate_assessment_alignment(
    objectives: list, assessment_plan: dict
) -> dict:
    """Check that every objective has corresponding assessment evidence.

    Compares the set of objective IDs present in the objectives list
    against those referenced in the assessment plan's evidence entries
    and posttest items.

    Args:
        objectives: A list of objective dicts, each with ``objective_id``.
        assessment_plan: A plan dict as returned by
            ``generate_assessment_plan()``.

    Returns:
        A dictionary with keys:
            - aligned: bool, True if every objective is covered
            - uncovered_objectives: list of objective_id strings that lack
              assessment evidence
            - coverage_rate: float between 0.0 and 1.0
    """
    if not objectives:
        return {
            "aligned": True,
            "uncovered_objectives": [],
            "coverage_rate": 1.0,
        }

    # Collect all objective IDs referenced in the plan
    covered_ids: set[str] = set()

    # Check evidence list
    for ev in assessment_plan.get("evidence", []):
        link = ev.get("linked_objective_id", "")
        if link:
            covered_ids.add(link)

    # Check posttest items
    for item in assessment_plan.get("posttest", {}).get("items", []):
        link = item.get("objective_id", "")
        if link:
            covered_ids.add(link)

    # Check practice evidence items
    for item in assessment_plan.get("practice_evidence", {}).get("items", []):
        link = item.get("objective_id", "")
        if link:
            covered_ids.add(link)

    # Check pretest items
    for item in assessment_plan.get("pretest", {}).get("items", []):
        link = item.get("objective_id", "")
        if link:
            covered_ids.add(link)

    # Check entry-behaviour test items
    for item in assessment_plan.get("entry_behavior_test", {}).get("items", []):
        link = item.get("objective_id", "")
        if link:
            covered_ids.add(link)

    # Compute coverage
    all_ids = [obj.get("objective_id", "") for obj in objectives if obj.get("objective_id")]
    uncovered = [oid for oid in all_ids if oid not in covered_ids]
    total = len(all_ids)
    covered_count = total - len(uncovered)
    coverage_rate = covered_count / total if total > 0 else 1.0

    return {
        "aligned": len(uncovered) == 0,
        "uncovered_objectives": uncovered,
        "coverage_rate": coverage_rate,
    }
