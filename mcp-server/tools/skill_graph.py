"""
Skill Graph Engine -- deterministic skill-graph construction.

Classifies goals, decomposes them into steps, identifies subordinate
skills, entry behaviours, and assembles the complete skill graph.

All functions are pure / deterministic -- no AI calls.
"""

import os
import sys
import re
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_THIS_DIR)
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from core.ids import gen_skill_id
from core.verbs import check_observable_verb, suggest_observable_behavior
from core.quality import check_skill_graph_quality

# ===================================================================
# Keyword classification rules
# ===================================================================

VERBAL_KEYWORDS = frozenset({
    "说出", "列举", "描述", "复述", "陈述", "背诵", "知道",
    "写出", "命名", "报告", "转述", "回忆", "识别事实",
})

INTELLECTUAL_KEYWORDS = frozenset({
    "计算", "设计", "分析", "解决", "判断", "区分", "分类",
    "解释", "生成", "评价", "比较", "预测", "推断", "论证",
    "建构", "修改", "运用", "应用", "推理", "归纳", "演绎",
    "综合", "抽象", "建模", "证明", "反驳",
})

PSYCHOMOTOR_KEYWORDS = frozenset({
    "操作", "执行", "绘制", "编写", "安装", "搭建", "测量",
    "拆卸", "修复", "搬运", "演示动作", "手工", "装配",
    "调试", "部署", "配置", "焊接", "切割",
})

ATTITUDE_KEYWORDS = frozenset({
    "选择", "倾向于", "主动", "在情境中选择",
    "在...情况下选择", "表现出", "坚持", "愿意",
    "乐于", "自觉", "积极", "认真", "负责",
})

# Mapping of goal type -> domain label
DOMAIN_MAP = {
    "verbal_information": "认知-记忆",
    "intellectual_skill": "认知-应用",
    "psychomotor_skill": "动作技能",
    "attitude": "情感态度",
    "mixed": "混合",
}

# Mapping of goal type -> common step patterns (for template generation)
STEP_TEMPLATES = {
    "verbal_information": [
        ("识别关键信息", "从材料中识别需要记忆的核心信息"),
        ("理解信息含义", "理解所识别信息的意义和关联"),
        ("组织信息结构", "将信息按逻辑结构组织"),
        ("复述与输出", "用自己的语言准确复述或写出信息"),
    ],
    "intellectual_skill": [
        ("分析问题情境", "理解问题的条件和要求"),
        ("选择策略方法", "根据问题特征选择合适的策略"),
        ("执行解题过程", "运用策略逐步解决问题"),
        ("验证与反思", "检验结果并反思过程"),
    ],
    "psychomotor_skill": [
        ("观察示范", "观看标准操作示范，建立动作表象"),
        ("模仿练习", "在指导下模仿操作动作"),
        ("独立操作", "独立完成操作任务"),
        ("熟练自动化", "反复练习达到熟练自动化水平"),
    ],
    "attitude": [
        ("认知准备", "了解应持有的态度及其价值"),
        ("体验与认同", "在情境中体验态度的重要性"),
        ("行为选择", "在实际情境中做出符合态度的选择"),
        ("持续表现", "在日常中持续表现出积极态度"),
    ],
}

# ===================================================================
# Topic-specific rule libraries
# ===================================================================

# Keywords -> topic identifier
TOPIC_KEYWORDS = {
    "算法": "algorithm",
    "algorithm": "algorithm",
    "流程图": "algorithm",
    "程序设计": "programming",
    "编程": "programming",
}

# Topic -> steps (description, learning_type)
TOPIC_STEPS = {
    "algorithm": [
        ("读懂问题情境并说出要解决的问题", "intellectual_skill"),
        ("识别问题中的已知条件、目标和限制", "intellectual_skill"),
        ("按先后顺序列出解决问题的操作步骤", "intellectual_skill"),
        ("检查步骤是否完整、明确、有限", "intellectual_skill"),
        ("用自然语言或流程图表达算法过程", "intellectual_skill"),
    ],
}

# Topic -> subordinate skills (description, learning_type, parent_step_index)
TOPIC_SUBSKILLS = {
    "algorithm": [
        ("从生活情境中找出问题目标", "intellectual_skill", 0),
        ("区分已知条件和要完成的任务", "intellectual_skill", 1),
        ("判断步骤之间的先后顺序", "intellectual_skill", 2),
        ("使用顺序词（先、再、然后、最后）描述操作步骤", "intellectual_skill", 3),
        ("判断步骤是否缺漏、重复或顺序错误", "intellectual_skill", 3),
        ("按模板绘制简单流程图", "psychomotor_skill", 4),
    ],
}

# Topic -> entry behaviors (description, learning_type, supports_skill_indices)
TOPIC_ENTRIES = {
    "algorithm": [
        ("能阅读七年级水平的生活问题文本", "verbal_information", [0, 1]),
        ("能用日常语言描述做事步骤", "verbal_information", [2]),
        ('能识别"先、再、然后、最后"等顺序词', "verbal_information", [2, 3]),
    ],
}


def _detect_topic(goal: dict) -> str | None:
    """Detect a topic from the goal's text fields."""
    text = " ".join([
        goal.get("behavior", ""),
        goal.get("context", ""),
        goal.get("full_statement", ""),
        goal.get("subject", ""),
    ]).lower()
    for keyword, topic in TOPIC_KEYWORDS.items():
        if keyword in text:
            return topic
    return None


# ===================================================================
# 1. classify_goal_type
# ===================================================================

def classify_goal_type(goal: dict) -> dict:
    """Classify a goal into a learning-result type.

    Uses keyword analysis on the goal's *behavior* and the full-text
    of the goal to produce a classification with confidence and
    rationale.

    Parameters
    ----------
    goal : dict
        Must contain at least *behavior*.  May also contain *context*,
        *tools*, *full_statement*, etc.

    Returns
    -------
    dict with keys: goal_type, confidence, rationale
    """
    if not isinstance(goal, dict):
        return {
            "goal_type": "mixed",
            "confidence": 0.0,
            "rationale": "目标数据无效，无法分类",
        }

    behavior = goal.get("behavior", "")
    full_text = " ".join([
        behavior,
        goal.get("context", ""),
        goal.get("tools", ""),
        goal.get("full_statement", ""),
    ])

    if not full_text.strip():
        return {
            "goal_type": "mixed",
            "confidence": 0.0,
            "rationale": "目标内容为空，无法分类",
        }

    # --- Count keyword hits per category ------------------------------------
    scores = {
        "verbal_information": 0,
        "intellectual_skill": 0,
        "psychomotor_skill": 0,
        "attitude": 0,
    }

    for kw in VERBAL_KEYWORDS:
        if kw in full_text:
            scores["verbal_information"] += 1
    for kw in INTELLECTUAL_KEYWORDS:
        if kw in full_text:
            scores["intellectual_skill"] += 1
    for kw in PSYCHOMOTOR_KEYWORDS:
        if kw in full_text:
            scores["psychomotor_skill"] += 1
    for kw in ATTITUDE_KEYWORDS:
        if kw in full_text:
            scores["attitude"] += 1

    total = sum(scores.values())

    # --- Determine winner(s) ------------------------------------------------
    if total == 0:
        return {
            "goal_type": "intellectual_skill",
            "confidence": 0.3,
            "rationale": "未匹配到明确关键词，默认归类为智力技能",
        }

    sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_type, top_score = sorted_types[0]
    second_type, second_score = sorted_types[1] if len(sorted_types) > 1 else ("", 0)

    # --- Confidence calculation ---------------------------------------------
    if top_score == 0:
        confidence = 0.0
    elif second_score == 0:
        confidence = min(0.95, 0.6 + 0.1 * top_score)
    else:
        # Close race -> lower confidence, likely mixed
        ratio = top_score / (top_score + second_score)
        confidence = round(min(0.95, 0.4 + 0.55 * ratio), 2)

    # --- Mixed classification -----------------------------------------------
    if second_score > 0 and top_score - second_score <= 1:
        goal_type = "mixed"
        rationale = (
            f"同时涉及多个类型: {DOMAIN_MAP.get(top_type, top_type)}({top_score}个关键词) "
            f"和 {DOMAIN_MAP.get(second_type, second_type)}({second_score}个关键词)。"
            f"建议教师确认主要学习类型"
        )
        confidence = round(min(confidence, 0.6), 2)
    else:
        goal_type = top_type
        matched_kws = [kw for kw in (VERBAL_KEYWORDS if top_type == "verbal_information"
                                      else INTELLECTUAL_KEYWORDS if top_type == "intellectual_skill"
                                      else PSYCHOMOTOR_KEYWORDS if top_type == "psychomotor_skill"
                                      else ATTITUDE_KEYWORDS)
                       if kw in full_text]
        rationale = (
            f"匹配到{DOMAIN_MAP.get(top_type, top_type)}类型关键词: "
            f"{', '.join(matched_kws[:5])}。"
            f"置信度: {confidence:.0%}"
        )

    return {
        "goal_type": goal_type,
        "confidence": confidence,
        "rationale": rationale,
    }


# ===================================================================
# 2. generate_goal_steps
# ===================================================================

def generate_goal_steps(
    goal: dict,
    candidate_steps: Optional[list] = None,
) -> dict:
    """Generate or structure the main steps for achieving the goal.

    If *candidate_steps* is provided, each step is given an ID and
    validated.  Otherwise, conservative template steps are generated
    and flagged for teacher confirmation.

    Parameters
    ----------
    goal : dict
        Instructional goal dict.
    candidate_steps : list or None
        Optional list of step dicts or strings provided by the teacher.

    Returns
    -------
    dict with keys: steps (list), requires_teacher_confirmation (bool)
    """
    if not isinstance(goal, dict):
        return {
            "steps": [],
            "requires_teacher_confirmation": True,
        }

    requires_confirmation = False

    # --- If candidate steps were provided, structure them --------------------
    if candidate_steps:
        steps = []
        for idx, raw in enumerate(candidate_steps, start=1):
            if isinstance(raw, str):
                step = {
                    "step_id": gen_skill_id(),
                    "order": idx,
                    "description": raw,
                    "required_skills": [],
                    "is_critical": True,
                    "source": "teacher_provided",
                }
            elif isinstance(raw, dict):
                step = {
                    "step_id": raw.get("step_id", gen_skill_id()),
                    "order": raw.get("order", idx),
                    "description": raw.get("description", raw.get("name", "")),
                    "required_skills": raw.get("required_skills", []),
                    "is_critical": raw.get("is_critical", True),
                    "source": "teacher_provided",
                }
            else:
                continue

            # Validate the step has a description
            if not step["description"]:
                requires_confirmation = True
                step["description"] = f"步骤 {idx} (内容待补充)"

            steps.append(step)

        return {
            "steps": steps,
            "requires_teacher_confirmation": requires_confirmation,
        }

    # --- No candidate steps: generate from topic library or templates --------
    topic = _detect_topic(goal)

    if topic and topic in TOPIC_STEPS:
        # Use topic-specific steps
        topic_steps = TOPIC_STEPS[topic]
        steps = []
        for idx, (desc, ltype) in enumerate(topic_steps, start=1):
            steps.append({
                "step_id": gen_skill_id(),
                "order": idx,
                "description": desc,
                "learning_type": ltype,
                "required_skills": [],
                "is_critical": True,
                "source": f"topic_rule_{topic}",
                "status": "candidate",
            })
        requires_confirmation = True
        return {
            "steps": steps,
            "requires_teacher_confirmation": requires_confirmation,
            "topic": topic,
        }

    # Fallback to generic templates
    classification = classify_goal_type(goal)
    goal_type = classification.get("goal_type", "intellectual_skill")

    templates = STEP_TEMPLATES.get(goal_type, STEP_TEMPLATES["intellectual_skill"])
    if goal_type == "mixed":
        templates = STEP_TEMPLATES["intellectual_skill"][:2] + STEP_TEMPLATES["verbal_information"][:1]

    steps = []
    for idx, (name, desc) in enumerate(templates, start=1):
        steps.append({
            "step_id": gen_skill_id(),
            "order": idx,
            "description": f"{name} -- {desc}",
            "learning_type": goal_type if goal_type != "mixed" else "intellectual_skill",
            "required_skills": [],
            "is_critical": True,
            "source": "template_generated",
            "status": "candidate",
        })

    requires_confirmation = True

    return {
        "steps": steps,
        "requires_teacher_confirmation": requires_confirmation,
    }


# ===================================================================
# 3. analyze_subordinate_skills
# ===================================================================

def analyze_subordinate_skills(
    goal_steps: list,
    candidate_subskills: Optional[list] = None,
) -> dict:
    """Generate subordinate skills for each goal step.

    Parameters
    ----------
    goal_steps : list
        List of step dicts (each with *step_id*, *description*).
    candidate_subskills : list or None
        Optional list of sub-skill dicts provided by the teacher.

    Returns
    -------
    dict with keys: subordinate_skills (list), requires_teacher_confirmation (bool)
    """
    requires_confirmation = False
    all_subskills: list[dict] = []

    # --- If candidate subskills were provided, structure them ---------------
    if candidate_subskills:
        for idx, raw in enumerate(candidate_subskills, start=1):
            if isinstance(raw, str):
                subskill = {
                    "skill_id": gen_skill_id(),
                    "name": raw,
                    "description": raw,
                    "linked_step_id": None,
                    "skill_type": "prerequisite",
                    "priority": idx,
                    "source": "teacher_provided",
                }
            elif isinstance(raw, dict):
                subskill = {
                    "skill_id": raw.get("skill_id", gen_skill_id()),
                    "name": raw.get("name", ""),
                    "description": raw.get("description", raw.get("name", "")),
                    "linked_step_id": raw.get("linked_step_id", None),
                    "skill_type": raw.get("skill_type", "prerequisite"),
                    "priority": raw.get("priority", idx),
                    "source": "teacher_provided",
                }
            else:
                continue

            if not subskill["name"]:
                requires_confirmation = True
                subskill["name"] = f"从属技能 {idx} (名称待补充)"

            all_subskills.append(subskill)

        return {
            "subordinate_skills": all_subskills,
            "requires_teacher_confirmation": requires_confirmation,
        }

    # --- No candidates: check for topic-specific or infer per step -----------
    # Try to detect topic from the first step's source metadata
    topic = None
    for step in goal_steps:
        src = step.get("source", "")
        if src.startswith("topic_rule_"):
            topic = src.replace("topic_rule_", "")
            break

    if topic and topic in TOPIC_SUBSKILLS:
        topic_subs = TOPIC_SUBSKILLS[topic]
        for idx, (desc, ltype, parent_idx) in enumerate(topic_subs):
            parent_step = goal_steps[parent_idx] if parent_idx < len(goal_steps) else {}
            all_subskills.append({
                "skill_id": gen_skill_id(),
                "name": desc,
                "description": desc,
                "learning_type": ltype,
                "linked_step_id": parent_step.get("step_id", ""),
                "parent_step_id": parent_step.get("step_id", ""),
                "skill_type": "subordinate",
                "priority": idx + 1,
                "source": f"topic_rule_{topic}",
                "status": "candidate",
            })
        return {
            "subordinate_skills": all_subskills,
            "requires_teacher_confirmation": True,
        }

    # Fallback: infer per step
    requires_confirmation = True

    for step in goal_steps:
        step_id = step.get("step_id", "")
        step_desc = step.get("description", "")
        step_ltype = step.get("learning_type", "intellectual_skill")

        generated = _infer_subskills_for_step(step_desc)

        for sub_idx, (name, stype, priority) in enumerate(generated, start=1):
            all_subskills.append({
                "skill_id": gen_skill_id(),
                "name": name,
                "description": name,
                "learning_type": step_ltype,
                "linked_step_id": step_id,
                "parent_step_id": step_id,
                "skill_type": stype,
                "priority": priority,
                "source": "auto_generated",
                "status": "candidate",
            })

    return {
        "subordinate_skills": all_subskills,
        "requires_teacher_confirmation": requires_confirmation,
    }


# ===================================================================
# 4. identify_entry_behaviors
# ===================================================================

def identify_entry_behaviors(
    subordinate_skills: list,
    learner_context: Optional[dict] = None,
) -> dict:
    """Identify entry behaviours from subordinate skills and learner context.

    Entry behaviours are the skills / knowledge a learner must already
    possess *before* starting instruction.

    Parameters
    ----------
    subordinate_skills : list
        List of sub-skill dicts from ``analyze_subordinate_skills``.
    learner_context : dict or None
        Optional learner info: grade_level, prior_knowledge, etc.

    Returns
    -------
    dict with keys: entry_behaviours (list)
    """
    entry_behaviours: list[dict] = []

    # --- Check for topic-specific entries -----------------------------------
    # Detect topic from subskills' source metadata
    topic = None
    for sk in subordinate_skills:
        src = sk.get("source", "")
        if src.startswith("topic_rule_"):
            topic = src.replace("topic_rule_", "")
            break

    if topic and topic in TOPIC_ENTRIES:
        topic_entries = TOPIC_ENTRIES[topic]
        for idx, (desc, ltype, supports_indices) in enumerate(topic_entries):
            # Map supports_indices to actual skill_ids
            supports_ids = []
            for si in supports_indices:
                if si < len(subordinate_skills):
                    supports_ids.append(subordinate_skills[si].get("skill_id", ""))

            entry_behaviours.append({
                "entry_id": gen_skill_id(),
                "name": desc,
                "description": desc,
                "learning_type": ltype,
                "related_skill_id": supports_ids[0] if supports_ids else "",
                "supports_skill_ids": supports_ids,
                "source_subskill_id": None,
                "source": f"topic_rule_{topic}",
                "status": "candidate",
            })
        return {
            "entry_behaviours": entry_behaviours,
        }

    # --- Infer from prerequisite-type subskills -----------------------------
    for sk in subordinate_skills:
        stype = sk.get("skill_type", "")
        if stype in ("prerequisite", "prior_knowledge"):
            entry_behaviours.append({
                "entry_id": gen_skill_id(),
                "name": sk.get("name", ""),
                "description": sk.get("description", ""),
                "learning_type": sk.get("learning_type", "unknown_candidate"),
                "related_skill_id": sk.get("skill_id", ""),
                "supports_skill_ids": [sk.get("skill_id", "")],
                "source_subskill_id": sk.get("skill_id", ""),
                "source": "inferred_from_subskills",
                "status": "candidate",
            })

    # --- Augment with learner context if available --------------------------
    if isinstance(learner_context, dict):
        prior = learner_context.get("prior_knowledge", [])
        grade = learner_context.get("grade_level", "")
        foundation = learner_context.get("foundation_skills", [])

        if isinstance(prior, list):
            for item in prior:
                name = item if isinstance(item, str) else item.get("name", str(item))
                entry_behaviours.append({
                    "entry_id": gen_skill_id(),
                    "name": name,
                    "description": f"学习者已有的先备知识: {name}",
                    "source_subskill_id": None,
                    "source": "learner_context",
                })

        if isinstance(foundation, list):
            for item in foundation:
                name = item if isinstance(item, str) else item.get("name", str(item))
                entry_behaviours.append({
                    "entry_id": gen_skill_id(),
                    "name": name,
                    "description": f"学习者应具备的基础技能: {name}",
                    "source_subskill_id": None,
                    "source": "learner_context",
                })

        if grade:
            entry_behaviours.append({
                "entry_id": gen_skill_id(),
                "name": f"学段基础能力 ({grade})",
                "description": f"学习者处于{grade}，应具备该学段的基础学习能力",
                "source_subskill_id": None,
                "source": "learner_context",
            })

    # --- If nothing found, add a generic entry behaviour --------------------
    if not entry_behaviours:
        entry_behaviours.append({
            "entry_id": gen_skill_id(),
            "name": "基本学习能力",
            "description": "具备基本的阅读理解能力和学习习惯",
            "learning_type": "verbal_information",
            "related_skill_id": "",
            "supports_skill_ids": [],
            "source_subskill_id": None,
            "source": "default_assumption",
            "status": "candidate",
        })

    return {"entry_behaviours": entry_behaviours}


# ===================================================================
# 5. build_skill_graph
# ===================================================================

def build_skill_graph(
    goal: dict,
    goal_steps: list,
    subordinate_skills: list,
    entry_behaviours: list,
) -> dict:
    """Assemble the complete skill graph data structure.

    Parameters
    ----------
    goal : dict
        The instructional goal dict.
    goal_steps : list
        Ordered list of goal step dicts.
    subordinate_skills : list
        List of subordinate skill dicts.
    entry_behaviours : list
        List of entry behaviour dicts.

    Returns
    -------
    dict with keys:
        goal_node, goal_steps, subordinate_skills, entry_behaviours,
        nodes, edges, metadata
    """
    # --- Build nodes list ---------------------------------------------------
    nodes: list[dict] = []

    # Goal node (root)
    goal_node = {
        "node_id": goal.get("goal_id", gen_skill_id()),
        "node_type": "goal",
        "label": goal.get("behavior", goal.get("full_statement", "教学目标")),
        "goal_id": goal.get("goal_id", ""),
        "learning_type": "mixed",
    }
    nodes.append(goal_node)

    # Step nodes
    for step in goal_steps:
        nodes.append({
            "node_id": step.get("step_id", gen_skill_id()),
            "node_type": "goal_step",
            "label": step.get("description", ""),
            "order": step.get("order", 0),
            "is_critical": step.get("is_critical", True),
            "learning_type": step.get("learning_type", "unknown_candidate"),
            "parent_step_id": step.get("parent_step_id", ""),
            "status": step.get("status", "candidate"),
        })

    # Subordinate skill nodes
    for sk in subordinate_skills:
        nodes.append({
            "node_id": sk.get("skill_id", gen_skill_id()),
            "node_type": "subordinate_skill",
            "label": sk.get("name", ""),
            "learning_type": sk.get("learning_type", "unknown_candidate"),
            "skill_type": sk.get("skill_type", ""),
            "linked_step_id": sk.get("linked_step_id", ""),
            "parent_step_id": sk.get("parent_step_id", sk.get("linked_step_id", "")),
            "status": sk.get("status", "candidate"),
        })

    # Entry behaviour nodes
    for eb in entry_behaviours:
        nodes.append({
            "node_id": eb.get("entry_id", gen_skill_id()),
            "node_type": "entry_behavior",
            "label": eb.get("name", ""),
            "learning_type": eb.get("learning_type", "unknown_candidate"),
            "related_skill_id": eb.get("related_skill_id", ""),
            "supports_skill_ids": eb.get("supports_skill_ids", []),
            "status": eb.get("status", "candidate"),
        })

    # --- Build edges list ---------------------------------------------------
    edges: list[dict] = []

    # Goal -> steps (sequential)
    sorted_steps = sorted(goal_steps, key=lambda s: s.get("order", 0))
    for i, step in enumerate(sorted_steps):
        # Goal -> first step
        if i == 0:
            edges.append({
                "from": goal_node["node_id"],
                "to": step.get("step_id", ""),
                "edge_type": "goal_to_step",
            })
        # Step -> next step
        if i > 0:
            prev_id = sorted_steps[i - 1].get("step_id", "")
            edges.append({
                "from": prev_id,
                "to": step.get("step_id", ""),
                "edge_type": "step_sequence",
            })

    # Steps -> subordinate skills
    step_id_set = {s.get("step_id", "") for s in goal_steps}
    for sk in subordinate_skills:
        linked = sk.get("linked_step_id", "")
        if linked and linked in step_id_set:
            edges.append({
                "from": linked,
                "to": sk.get("skill_id", ""),
                "edge_type": "step_requires_skill",
            })

    # Entry behaviours -> subordinate skills (prerequisites)
    subskill_ids = {sk.get("skill_id", "") for sk in subordinate_skills}
    for eb in entry_behaviours:
        # Use supports_skill_ids if available
        supports = eb.get("supports_skill_ids", [])
        for sid in supports:
            if sid and sid in subskill_ids:
                edges.append({
                    "from": eb.get("entry_id", ""),
                    "to": sid,
                    "edge_type": "entry_prerequisite",
                })
        # Fallback to source_subskill_id
        if not supports:
            linked = eb.get("source_subskill_id", "")
            if linked and linked in subskill_ids:
                edges.append({
                    "from": eb.get("entry_id", ""),
                    "to": linked,
                    "edge_type": "entry_prerequisite",
                })

    # --- Metadata -----------------------------------------------------------
    metadata = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "goal_type": classify_goal_type(goal).get("goal_type", "unknown"),
        "step_count": len(goal_steps),
        "subskill_count": len(subordinate_skills),
        "entry_count": len(entry_behaviours),
    }

    # --- Assemble graph -----------------------------------------------------
    graph = {
        "goal_node": goal_node,
        "goal_steps": sorted_steps,
        "subordinate_skills": subordinate_skills,
        "entry_behaviours": entry_behaviours,
        "nodes": nodes,
        "edges": edges,
        "metadata": metadata,
    }

    return graph


# ===================================================================
# Internal helpers
# ===================================================================

def _infer_subskills_for_step(step_description: str) -> list[tuple]:
    """Infer reasonable sub-skills for a step based on its description.

    Returns list of (name, skill_type, priority) tuples.
    """
    desc = step_description.lower() if step_description else ""
    subskills: list[tuple] = []

    # Common patterns in step descriptions
    if any(kw in desc for kw in ("分析", "理解", "识别", "辨认")):
        subskills.append(("阅读并理解相关材料", "prerequisite", 1))
        subskills.append(("识别关键信息和概念", "supporting", 2))

    if any(kw in desc for kw in ("计算", "运算", "求解", "公式")):
        subskills.append(("掌握基本计算规则", "prerequisite", 1))
        subskills.append(("选择合适的计算方法", "supporting", 2))

    if any(kw in desc for kw in ("操作", "执行", "演示", "使用")):
        subskills.append(("了解操作工具/设备", "prerequisite", 1))
        subskills.append(("掌握基本操作规范", "supporting", 2))

    if any(kw in desc for kw in ("设计", "创作", "编写", "构建")):
        subskills.append(("了解设计原则/规范", "prerequisite", 1))
        subskills.append(("掌握基本设计方法", "supporting", 2))

    if any(kw in desc for kw in ("选择", "判断", "决策", "评价")):
        subskills.append(("了解评价标准", "prerequisite", 1))
        subskills.append(("掌握比较和判断方法", "supporting", 2))

    if any(kw in desc for kw in ("验证", "检查", "反思", "检验")):
        subskills.append(("了解验证方法", "prerequisite", 1))
        subskills.append(("掌握自我检查策略", "supporting", 2))

    # Fallback: generic sub-skills for any step
    if not subskills:
        subskills.append(("理解步骤要求", "prerequisite", 1))
        subskills.append(("掌握相关基础知识", "supporting", 2))

    return subskills


# ===================================================================
# v1 graph views and structural validation
# ===================================================================

def _graph_node_id(node: dict) -> str:
    return str(
        node.get("node_id")
        or node.get("step_id")
        or node.get("skill_id")
        or node.get("entry_id")
        or node.get("id")
        or ""
    )


def _graph_label(node: dict) -> str:
    return str(
        node.get("label")
        or node.get("description")
        or node.get("name")
        or node.get("behavior")
        or node.get("title")
        or ""
    ).strip()


def _base_nodes(skill_graph: dict) -> tuple[dict, list[dict], list[dict], list[dict]]:
    goal = dict(skill_graph.get("goal_node") or {})
    if not goal:
        goal = {"node_id": "G-01", "node_type": "instructional_goal", "label": "教学目的待确认"}
    goal.setdefault("node_type", "instructional_goal")
    steps = [dict(item) for item in skill_graph.get("goal_steps", []) if isinstance(item, dict)]
    subs = [dict(item) for item in skill_graph.get("subordinate_skills", []) if isinstance(item, dict)]
    entries = [dict(item) for item in skill_graph.get("entry_behaviors", skill_graph.get("entry_behaviours", [])) if isinstance(item, dict)]
    return goal, steps, subs, entries


def build_goal_operation_view(skill_graph: dict) -> dict:
    """Build the expert task procedure view, separate from prerequisites.

    This page intentionally contains only the goal and the major operation
    steps. Subordinate and entry skills belong to the separate hierarchy page;
    mixing them would make the two instructional-analysis questions unreadable.
    """
    goal, steps, _subs, _entries = _base_nodes(skill_graph)
    nodes = [{"id": _graph_node_id(goal), "node_type": "instructional_goal", "label": _graph_label(goal)}]
    edges = []
    ordered = sorted(steps, key=lambda item: item.get("order", 0))
    previous = None
    for step in ordered:
        step_id = _graph_node_id(step)
        nodes.append({
            "id": step_id,
            "node_type": "goal_step",
            "label": _graph_label(step),
            "source_step_id": step_id,
        })
        if previous is None:
            edges.append({"from": _graph_node_id(goal), "to": step_id, "edge_type": "sequence"})
        if previous:
            edges.append({"from": previous, "to": step_id, "edge_type": "sequence"})
        previous = step_id

    # Preserve explicit procedure semantics supplied by the teacher/engine.
    for raw in skill_graph.get("procedure_nodes", []):
        if not isinstance(raw, dict):
            continue
        node_id = _graph_node_id(raw)
        if node_id and node_id not in {node["id"] for node in nodes}:
            nodes.append({"id": node_id, "node_type": raw.get("node_type", "action"), "label": _graph_label(raw)})
    for edge in skill_graph.get("procedure_edges", []):
        if isinstance(edge, dict):
            edges.append(dict(edge))
    return {
        "view_id": "goal_operation_flow",
        "title": "目的操作流程图",
        "description": "表示熟练学习者完成教学目的时的实际操作顺序",
        "nodes": nodes,
        "edges": edges,
    }


def build_skill_hierarchy_view(skill_graph: dict) -> dict:
    """Build the prerequisite hierarchy with a visible entry boundary."""
    goal, steps, subs, entries = _base_nodes(skill_graph)
    nodes = [{"id": _graph_node_id(goal), "node_type": "instructional_goal", "label": _graph_label(goal)}]
    edges = []
    for step in sorted(steps, key=lambda item: item.get("order", 0)):
        step_id = _graph_node_id(step)
        nodes.append({"id": step_id, "node_type": "goal_step", "label": _graph_label(step)})
        edges.append({"from": _graph_node_id(goal), "to": step_id, "edge_type": "component_of"})
    for sub in subs:
        sub_id = _graph_node_id(sub)
        parent = sub.get("parent_step_id") or sub.get("linked_step_id") or ""
        nodes.append({"id": sub_id, "node_type": "intellectual_skill" if sub.get("learning_type") == "intellectual_skill" else sub.get("learning_type", "intellectual_skill"), "label": _graph_label(sub), "parent_step_id": parent})
        if parent:
            edges.append({"from": parent, "to": sub_id, "edge_type": "prerequisite"})
    boundary_id = "ENTRY-BOUNDARY"
    nodes.append({"id": boundary_id, "node_type": "entry_boundary", "label": "入门技能分界线"})
    for entry in entries:
        entry_id = _graph_node_id(entry)
        nodes.append({"id": entry_id, "node_type": "entry_skill", "label": _graph_label(entry)})
        edges.append({"from": boundary_id, "to": entry_id, "edge_type": "entry_boundary"})
        supports = entry.get("supports_skill_ids", []) or entry.get("supports", [])
        for target in supports:
            edges.append({"from": entry_id, "to": target, "edge_type": "entry_boundary"})
        if not supports:
            edges.append({"from": entry_id, "to": boundary_id, "edge_type": "entry_boundary"})
    return {
        "view_id": "skill_hierarchy",
        "title": "从属技能与入门技能图",
        "description": "表示本次教学需要建立的技能层级和已有入门技能边界",
        "nodes": nodes,
        "edges": edges,
    }


def build_control_flow_view(skill_graph: dict) -> dict:
    """Build a programming control-flow view with explicit decisions."""
    goal, steps, _subs, _entries = _base_nodes(skill_graph)
    text = " ".join([_graph_label(goal), *[_graph_label(step) for step in steps], str(skill_graph.get("topic", ""))]).lower()
    is_branch = any(token in text for token in ("分支", "条件", "if", "elif", "else"))
    is_loop = any(token in text for token in ("循环", "for", "while", "迭代", "重复"))
    nodes = [{"id": "CF-START", "node_type": "start", "label": "开始"}]
    edges = []
    ordered = sorted(steps, key=lambda item: item.get("order", 0))
    previous = "CF-START"
    for idx, step in enumerate(ordered, 1):
        node_id = f"CF-A{idx:02d}"
        nodes.append({"id": node_id, "node_type": "action", "label": _graph_label(step), "source_step_id": _graph_node_id(step)})
        if previous == "CF-LOOP":
            edges.append({"from": previous, "to": node_id, "edge_type": "conditional_no", "label": "否，退出循环"})
        else:
            edges.append({"from": previous, "to": node_id, "edge_type": "sequence"})
        previous = node_id
        if is_branch and idx == min(3, max(1, len(ordered))):
            decision_id = "CF-DECISION"
            nodes.append({"id": decision_id, "node_type": "decision", "label": "条件是否满足？"})
            edges.append({"from": node_id, "to": decision_id, "edge_type": "sequence"})
            yes_id = "CF-YES"
            no_id = "CF-NO"
            nodes.extend([
                {"id": yes_id, "node_type": "action", "label": "执行满足条件的分支"},
                {"id": no_id, "node_type": "action", "label": "执行不满足条件的分支"},
            ])
            edges.extend([
                {"from": decision_id, "to": yes_id, "edge_type": "conditional_yes", "label": "是"},
                {"from": decision_id, "to": no_id, "edge_type": "conditional_no", "label": "否"},
            ])
            previous = yes_id
            if idx < len(ordered):
                edges.append({"from": no_id, "to": f"CF-A{idx + 1:02d}", "edge_type": "sequence"})
            else:
                edges.append({"from": no_id, "to": "CF-TEST", "edge_type": "sequence"})
        if is_loop and idx == min(3, max(1, len(ordered))):
            loop_id = "CF-LOOP"
            nodes.append({"id": loop_id, "node_type": "decision", "label": "是否还有下一次迭代？"})
            edges.append({"from": previous, "to": loop_id, "edge_type": "sequence"})
            edges.append({"from": loop_id, "to": previous, "edge_type": "retry", "label": "是，继续迭代"})
            previous = loop_id
    # Every programming topic must show the authentic implementation loop:
    # run, inspect evidence, fix the code, and run the test again when needed.
    test_id = "CF-TEST"
    test_decision_id = "CF-TEST-DECISION"
    debug_id = "CF-DEBUG"
    nodes.extend([
        {"id": test_id, "node_type": "action", "label": "运行程序并测试输出"},
        {"id": test_decision_id, "node_type": "decision", "label": "测试结果是否符合预期？"},
        {"id": debug_id, "node_type": "action", "label": "定位错误、修改代码并重新测试"},
        {"id": "CF-END", "node_type": "end", "label": "结束"},
    ])
    edges.append({"from": previous, "to": test_id, "edge_type": "sequence"})
    edges.append({"from": test_id, "to": test_decision_id, "edge_type": "sequence"})
    edges.extend([
        {"from": test_decision_id, "to": "CF-END", "edge_type": "conditional_yes", "label": "是"},
        {"from": test_decision_id, "to": debug_id, "edge_type": "conditional_no", "label": "否"},
        {"from": debug_id, "to": test_id, "edge_type": "feedback", "label": "修改后重新测试"},
    ])
    if not ordered:
        edges.insert(0, {"from": "CF-START", "to": test_id, "edge_type": "sequence"})
    return {
        "view_id": "control_flow",
        "title": "程序控制流程图",
        "description": "对含条件、循环或调试反馈的程序课题显示决策和回路",
        "nodes": nodes,
        "edges": edges,
        "enabled": bool(is_branch or is_loop),
    }


def build_skill_graph_views(skill_graph: dict) -> dict[str, dict]:
    """Return independent operation, hierarchy and optional control views."""
    views = {
        "goal_operation_flow": build_goal_operation_view(skill_graph),
        "skill_hierarchy": build_skill_hierarchy_view(skill_graph),
    }
    control = build_control_flow_view(skill_graph)
    if control.get("enabled") or skill_graph.get("include_control_flow"):
        views["control_flow"] = control
    return views


def validate_skill_graph_views(views: dict[str, dict]) -> dict:
    """Check IDs, references, isolation and prerequisite cycles."""
    errors: list[str] = []
    for view_id, view in views.items():
        nodes = view.get("nodes", [])
        node_ids = [str(node.get("id", "")) for node in nodes]
        if any(not node_id for node_id in node_ids):
            errors.append(f"{view_id}: 存在空节点 ID")
        duplicates = sorted({node_id for node_id in node_ids if node_ids.count(node_id) > 1})
        if duplicates:
            errors.append(f"{view_id}: 重复节点 ID {duplicates}")
        known = set(node_ids)
        degree = {node_id: 0 for node_id in known}
        prerequisite_adj: dict[str, list[str]] = {node_id: [] for node_id in known}
        for edge in view.get("edges", []):
            source = str(edge.get("from", ""))
            target = str(edge.get("to", ""))
            if source not in known or target not in known:
                errors.append(f"{view_id}: 边 {source}->{target} 引用了不存在节点")
                continue
            degree[source] += 1
            degree[target] += 1
            if edge.get("edge_type") in {"prerequisite", "entry_boundary"}:
                prerequisite_adj[source].append(target)
        isolated = [node_id for node_id, count in degree.items() if count == 0]
        if isolated:
            errors.append(f"{view_id}: 孤立节点 {isolated}")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                errors.append(f"{view_id}: prerequisite 边存在循环依赖")
                return
            if node_id in visited:
                return
            visiting.add(node_id)
            for target in prerequisite_adj.get(node_id, []):
                visit(target)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in known:
            visit(node_id)
    return {"status": "pass" if not errors else "fail", "errors": errors, "views": list(views)}
