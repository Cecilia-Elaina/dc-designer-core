"""
Goal Engine -- deterministic goal-setting pipeline.

Analyses instructional context, drafts goals, validates them against
quality gates, and checks whether the problem is truly instructional.

All functions are pure / deterministic -- no AI calls.
"""

import os
import sys
import re
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup so that ``from core.xxx import ...`` works when the file is
# executed directly or when the package is loaded by the MCP server.
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_THIS_DIR)
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from core.ids import gen_goal_id, gen_source_id
from core.verbs import check_observable_verb, suggest_observable_behavior
from core.quality import check_goal_quality
from core.evidence import suggest_evidence_type

# ===================================================================
# Constants
# ===================================================================

# Scene types the system understands
VALID_SCENE_TYPES = frozenset({"k12", "corporate", "higher_ed", "vocational", "self_study"})

# User (learner) types
VALID_USER_TYPES = frozenset({
    "student", "teacher", "corporate_employee", "corporate_manager",
    "new_hire", "intern", "instructor", "self_learner",
})

# Source levels
SOURCE_LEVELS = {
    "A": "official_standard",      # national / ministry standard
    "B": "official_textbook",      # approved textbook / curriculum doc
    "C": "reference",              # reputable reference
    "D": "unverified",             # unverified / ad-hoc
}

# K12-specific: types of official sources that count for verification
K12_OFFICIAL_SOURCE_TYPES = frozenset({
    "curriculum_standard", "textbook", "examination_outline",
    "ministry_document", "official_syllabus",
})

# Corporate non-training problem indicators
NON_TRAINING_KEYWORDS = {
    "process": ["流程不合理", "流程缺失", "流程冗余", "制度缺失", "制度不完善"],
    "environment": ["工具不足", "设备老化", "资源缺乏", "环境恶劣", "人手不足"],
    "motivation": ["激励不足", "绩效考核", "薪酬不合理", "晋升通道"],
    "information": ["信息不对称", "知识库缺失", "文档缺失", "没有标准"],
    "selection": ["招聘不当", "人岗不匹配", "能力不足", "用人失误"],
}

# Instructional-solution indicators
INSTRUCTIONAL_KEYWORDS = frozenset({
    "不会", "不熟悉", "错误率", "达标率", "技能不足", "知识欠缺",
    "操作不规范", "理解有误", "方法不当", "缺乏练习",
})


# ===================================================================
# 1. analyze_instructional_context
# ===================================================================

def analyze_instructional_context(input_data: dict) -> dict:
    """Analyse user type, scene type, and required / optional sources.

    Parameters
    ----------
    input_data : dict
        Expected keys (all optional except *scene_type* and *user_type*):
        - user_type (str): one of ``VALID_USER_TYPES`` or free text.
        - scene_type (str): one of ``VALID_SCENE_TYPES``.
        - subject (str): subject area, e.g. "数学", "Python编程".
        - grade_level (str): grade or level, e.g. "三年级", "初级".
        - has_official_standards (bool): whether official standards exist.
        - additional_info (str): free-text extra context.

    Returns
    -------
    dict with keys:
        scene_type, user_type, required_sources, optional_sources, notes
    """
    user_type = input_data.get("user_type", "").strip()
    scene_type = input_data.get("scene_type", "").strip().lower()
    subject = input_data.get("subject", "").strip()
    grade_level = input_data.get("grade_level", "").strip()
    has_official = input_data.get("has_official_standards", None)
    additional_info = input_data.get("additional_info", "").strip()

    notes: list[str] = []
    required_sources: list[dict] = []
    optional_sources: list[dict] = []

    # --- Validate scene type ------------------------------------------------
    if scene_type not in VALID_SCENE_TYPES:
        # Try fuzzy match
        _fuzzy = _fuzzy_match_scene(scene_type)
        if _fuzzy:
            notes.append(f"场景类型 '{scene_type}' 已自动匹配为 '{_fuzzy}'")
            scene_type = _fuzzy
        else:
            notes.append(f"未识别的场景类型 '{scene_type}'，默认按 'k12' 处理")
            scene_type = "k12"

    # --- Validate user type -------------------------------------------------
    if user_type not in VALID_USER_TYPES:
        notes.append(f"用户类型 '{user_type}' 不在预设列表中，将按自由文本处理")

    # --- Derive required / optional sources by scene -----------------------
    if scene_type == "k12":
        required_sources.append({
            "source_type": "curriculum_standard",
            "description": "课程标准（对应学段学科）",
            "level": "A",
            "mandatory": True,
        })
        required_sources.append({
            "source_type": "textbook",
            "description": "教材（对应版本年级）",
            "level": "B",
            "mandatory": True,
        })
        optional_sources.append({
            "source_type": "examination_outline",
            "description": "考试大纲 / 考试说明",
            "level": "B",
            "mandatory": False,
        })
        optional_sources.append({
            "source_type": "teaching_reference",
            "description": "教师用书 / 教学参考",
            "level": "C",
            "mandatory": False,
        })
        if has_official is False:
            notes.append("用户声明无官方来源，目的将标记为待验证草案")

    elif scene_type == "corporate":
        required_sources.append({
            "source_type": "job_analysis",
            "description": "岗位分析文档 / 任务清单",
            "level": "B",
            "mandatory": True,
        })
        optional_sources.append({
            "source_type": "performance_data",
            "description": "绩效数据 / 绩效差距报告",
            "level": "C",
            "mandatory": False,
        })
        optional_sources.append({
            "source_type": "sop",
            "description": "标准操作流程 (SOP)",
            "level": "B",
            "mandatory": False,
        })
        optional_sources.append({
            "source_type": "expert_interview",
            "description": "领域专家访谈记录",
            "level": "C",
            "mandatory": False,
        })

    elif scene_type == "higher_ed":
        required_sources.append({
            "source_type": "syllabus",
            "description": "教学大纲 / 课程标准",
            "level": "A",
            "mandatory": True,
        })
        optional_sources.append({
            "source_type": "textbook",
            "description": "推荐教材",
            "level": "B",
            "mandatory": False,
        })
        optional_sources.append({
            "source_type": "research_paper",
            "description": "学科前沿论文 / 行业报告",
            "level": "C",
            "mandatory": False,
        })

    elif scene_type == "vocational":
        required_sources.append({
            "source_type": "vocational_standard",
            "description": "职业技能标准",
            "level": "A",
            "mandatory": True,
        })
        required_sources.append({
            "source_type": "sop",
            "description": "岗位操作规范 / SOP",
            "level": "B",
            "mandatory": True,
        })
        optional_sources.append({
            "source_type": "industry_case",
            "description": "行业案例 / 真实工单",
            "level": "C",
            "mandatory": False,
        })

    elif scene_type == "self_study":
        optional_sources.append({
            "source_type": "reference",
            "description": "参考资料 / 在线教程",
            "level": "C",
            "mandatory": False,
        })
        notes.append("自学场景：无强制来源要求，但建议使用可靠参考资料")

    # --- General notes ------------------------------------------------------
    if subject:
        notes.append(f"学科领域: {subject}")
    if grade_level:
        notes.append(f"学段/水平: {grade_level}")
    if additional_info:
        notes.append(f"补充信息: {additional_info}")

    return {
        "scene_type": scene_type,
        "user_type": user_type,
        "required_sources": required_sources,
        "optional_sources": optional_sources,
        "notes": notes,
    }


# ===================================================================
# 2. generate_goal_draft
# ===================================================================

def generate_goal_draft(input_data: dict) -> dict:
    """Generate an instructional goal draft from user input.

    Parameters
    ----------
    input_data : dict
        Required keys:
        - learner (str): target learner description.
        - behavior (str): observable final behaviour.
        - context (str): application context / conditions.
        - tools (str): tools or resources available.
        Optional keys:
        - performance_problem (str): for corporate scene.
        - scene_type (str): k12 / corporate / etc.
        - sources (list[dict]): reference sources.

    Returns
    -------
    dict with keys:
        goal_id, status, full_statement, learner, behavior, context,
        tools, scene_type, sources, issues, recommendations
    """
    learner = input_data.get("learner", "").strip()
    behavior = input_data.get("behavior", "").strip()
    context = input_data.get("context", "").strip()
    tools = input_data.get("tools", "").strip()
    performance_problem = input_data.get("performance_problem", "").strip()
    scene_type = input_data.get("scene_type", "").strip().lower()
    sources = input_data.get("sources", [])

    issues: list[str] = []
    recommendations: list[str] = []

    # --- Basic field validation ---------------------------------------------
    if not learner:
        issues.append("缺少学习者描述 (learner)")
    if not behavior:
        issues.append("缺少最终行为描述 (behavior)")
    if not context:
        issues.append("缺少应用环境描述 (context)")
    if not tools:
        recommendations.append("建议补充工具/资源说明 (tools)")

    # --- Verb observability check -------------------------------------------
    verb_check = check_observable_verb(behavior) if behavior else None
    if verb_check and not verb_check.get("is_observable", True):
        for verb, replacements in verb_check.get("suggestions", {}).items():
            issues.append(f'行为动词 "{verb}" 不可观测，建议替换为: {", ".join(replacements[:3])}')

    # --- Assemble goal dict -------------------------------------------------
    goal: dict = {
        "goal_id": gen_goal_id(),
        "learner": learner,
        "behavior": behavior,
        "context": context,
        "tools": tools,
        "scene_type": scene_type or "k12",
        "sources": sources,
    }
    if performance_problem:
        goal["performance_problem"] = performance_problem

    # --- Build full statement (Mager-style) --------------------------------
    parts: list[str] = []
    if learner:
        parts.append(learner)
    if behavior:
        parts.append(behavior)
    if context:
        parts.append(f"在{context}条件下")
    if tools:
        parts.append(f"借助{tools}")
    full_statement = "，".join(parts) + "。" if parts else ""

    goal["full_statement"] = full_statement

    # --- K12 without official sources -> draft pending verification ----------
    status = "draft"
    if scene_type == "k12" or not scene_type:
        has_official = any(
            s.get("source_level", "").startswith(("A", "B"))
            for s in sources
        )
        has_teacher = any(
            s.get("retrieval_status") in ("user_uploaded", "teacher_confirmed")
            for s in sources
        )
        if not has_official and not has_teacher:
            status = "draft_pending_verification"
            recommendations.append(
                "K12场景无官方来源或教师确认资料，"
                "目的标记为待验证草案，请教师确认内容准确性"
            )

    # Corporate: performance_problem is recommended
    if scene_type in ("corporate", "企业") and not performance_problem:
        recommendations.append("企业培训场景建议提供绩效问题描述 (performance_problem)")

    return {
        "goal_id": goal["goal_id"],
        "status": status,
        "full_statement": full_statement,
        "learner": learner,
        "behavior": behavior,
        "context": context,
        "tools": tools,
        "scene_type": goal["scene_type"],
        "sources": sources,
        "issues": issues,
        "recommendations": recommendations,
    }


# ===================================================================
# 3. validate_instructional_goal
# ===================================================================

def validate_instructional_goal(
    goal: dict,
    sources: Optional[list] = None,
) -> dict:
    """Validate an instructional goal for completeness and quality.

    Checks required fields, verb observability, source requirements,
    and delegates to ``core.quality.check_goal_quality``.

    Parameters
    ----------
    goal : dict
        Instructional goal dict.  Expected keys: learner, behaviour,
        context, tools, and optionally scene_type, sources.
    sources : list or None
        Optional list of source dicts.  Merged into *goal["sources"]*
        for validation if the goal does not already carry them.

    Returns
    -------
    dict with keys:
        status, goal, issues, recommendations,
        requires_teacher_confirmation, is_verified
    """
    if not isinstance(goal, dict):
        return {
            "status": "error",
            "goal": goal,
            "issues": ["目标必须是一个字典"],
            "recommendations": [],
            "requires_teacher_confirmation": True,
            "is_verified": False,
        }

    # Merge sources
    if sources:
        goal_sources = goal.get("sources", [])
        goal = {**goal, "sources": goal_sources + sources}

    issues: list[str] = []
    recommendations: list[str] = []

    # --- Required field checks ----------------------------------------------
    if not goal.get("learner"):
        issues.append("缺少学习者描述 (learner)")
    if not goal.get("behavior"):
        issues.append("缺少最终行为描述 (behavior)")
    if not goal.get("context"):
        issues.append("缺少应用环境描述 (context)")
    if not goal.get("tools"):
        recommendations.append("建议补充工具/资源说明 (tools)")
    if not goal.get("sources"):
        recommendations.append("建议提供参考来源 (sources)")

    # --- Verb observability -------------------------------------------------
    behavior = goal.get("behavior", "")
    if behavior:
        verb_check = check_observable_verb(behavior)
        if not verb_check.get("is_observable", True):
            for verb, replacements in verb_check.get("suggestions", {}).items():
                issues.append(
                    f'行为动词 "{verb}" 不可观测，建议替换为: '
                    f'{", ".join(replacements[:3])}'
                )

    # --- Delegate to core quality gate --------------------------------------
    quality_result = check_goal_quality(goal)
    issues.extend(quality_result.get("issues", []))

    # --- Source verification (5-level K12 system) ---------------------------
    scene_type = goal.get("scene_type", "")
    goal_sources = goal.get("sources", [])
    is_verified = False
    requires_teacher_confirmation = False
    source_status = "unknown"
    verification_status = "unverified"

    # Normalize sources
    try:
        from core.source_normalizer import normalize_source_record, merge_source_records
        goal_sources = merge_source_records(goal_sources)
        goal["sources"] = goal_sources
    except ImportError:
        pass

    # Filter out test fixtures for formal basis check
    real_sources = [s for s in goal_sources if not s.get("is_test_fixture", False)]
    test_sources = [s for s in goal_sources if s.get("is_test_fixture", False)]

    # Check for A/B level real sources
    has_ab_source = any(
        s.get("source_level", "").startswith(("A", "B"))
        for s in real_sources
    )

    # Check for clause-level matches (specific_clauses non-empty)
    has_clauses = any(
        len(s.get("specific_clauses", [])) > 0
        for s in real_sources
    )

    # Check for sample-only metadata (cannot be used for final)
    has_sample_only = any(
        s.get("is_sample_metadata_only", False)
        for s in real_sources
    )

    # Check for teacher sources
    has_teacher = any(
        s.get("retrieval_status") in ("user_uploaded", "teacher_confirmed")
        for s in goal_sources
    )

    # Check if teacher has confirmed
    teacher_confirmed = any(
        s.get("verified_by_teacher", False)
        for s in goal_sources
    )

    if scene_type in ("k12", "K12"):
        if has_ab_source and has_clauses and not has_sample_only:
            # Level 4: standard_clause_aligned
            is_verified = True
            source_status = "sufficient"
            verification_status = "standard_clause_aligned"
            if teacher_confirmed:
                verification_status = "final_verified"
                requires_teacher_confirmation = False
            else:
                requires_teacher_confirmation = True
                recommendations.append(
                    "已找到课标条款级依据，但需要教师确认后方可作为最终依据"
                )
        elif has_ab_source and not has_clauses:
            # Level 3: standard_file_found
            is_verified = False
            source_status = "partial"
            verification_status = "source_found_pending_clause_alignment"
            requires_teacher_confirmation = True
            recommendations.append(
                "已找到官方课程标准文件，但尚未定位到具体条款。"
                "请上传/确认对应课标条款、教材章节或教研组资料"
            )
        elif has_teacher:
            # Level 2: teacher_limited
            is_verified = False
            source_status = "partial"
            verification_status = "draft_pending_verification"
            requires_teacher_confirmation = True
            recommendations.append(
                "仅有教师确认资料，无A/B级官方来源，教学目的标记为待验证草案"
            )
        else:
            # Level 1: no_source
            is_verified = False
            source_status = "insufficient"
            verification_status = "draft_unverified"
            requires_teacher_confirmation = True
            issues.append(
                "K12场景无任何可靠来源依据，教学目的只能标记为未验证草案"
            )
    elif scene_type in ("corporate", "企业"):
        if goal.get("performance_problem"):
            is_verified = True
            source_status = "sufficient"
            verification_status = "verified"
        else:
            requires_teacher_confirmation = True
            source_status = "partial"
            verification_status = "draft_pending_verification"
            recommendations.append(
                "企业培训场景建议提供绩效问题描述以验证培训必要性"
            )
    else:
        if goal_sources:
            is_verified = True
            source_status = "sufficient"
            verification_status = "verified"
        else:
            source_status = "unknown"
            verification_status = "unverified"

    # --- Determine overall status -------------------------------------------
    structure_ok = not issues

    if issues:
        status = "fail"
    elif verification_status == "draft_pending_verification":
        status = "warning"
    elif verification_status == "draft_unverified":
        status = "fail"
    else:
        status = "pass"

    can_use_as_final = (status == "pass" and is_verified)
    can_use_as_draft = True  # always can export as draft

    return {
        "status": status,
        "structure_status": "pass" if structure_ok else "fail",
        "source_status": source_status,
        "verification_status": verification_status,
        "can_use_as_final_goal": can_use_as_final,
        "can_use_as_draft": can_use_as_draft,
        "goal": goal,
        "issues": issues,
        "recommendations": recommendations,
        "requires_teacher_confirmation": requires_teacher_confirmation,
        "is_verified": is_verified,
    }


# ===================================================================
# 4. check_instructional_feasibility
# ===================================================================

def check_instructional_feasibility(goal: dict) -> dict:
    """Check whether a goal is suitable for an instructional solution.

    Distinguishes training problems from non-training (process,
    environment, motivation, information, selection) problems.

    Parameters
    ----------
    goal : dict
        Instructional goal dict.  For corporate scenes, the
        *performance_problem* field is key.

    Returns
    -------
    dict with keys:
        is_instructional, non_instructional_factors, recommendations
    """
    if not isinstance(goal, dict):
        return {
            "is_instructional": False,
            "non_instructional_factors": ["目标数据无效"],
            "recommendations": ["请提供有效的目标字典"],
        }

    scene_type = goal.get("scene_type", "").strip().lower()
    behavior = goal.get("behavior", "")
    performance_problem = goal.get("performance_problem", "")
    context = goal.get("context", "")
    tools = goal.get("tools", "")

    non_instructional_factors: list[str] = []
    recommendations: list[str] = []

    # --- Check for non-training root causes ---------------------------------
    check_text = f"{behavior} {performance_problem} {context}"

    for category, keywords in NON_TRAINING_KEYWORDS.items():
        for kw in keywords:
            if kw in check_text:
                factor_label = {
                    "process": "流程/制度问题",
                    "environment": "工具/环境问题",
                    "motivation": "激励/动机问题",
                    "information": "信息/资源缺失问题",
                    "selection": "人员选拔问题",
                }.get(category, f"{category}问题")
                non_instructional_factors.append(
                    f'发现 "{kw}" -- 可能属于{factor_label}，'
                    f"非培训能解决"
                )

    # --- Check for instructional-solution indicators -----------------------
    has_instructional_signal = False
    for kw in INSTRUCTIONAL_KEYWORDS:
        if kw in check_text:
            has_instructional_signal = True
            break

    # --- Corporate: extra scrutiny ------------------------------------------
    if scene_type in ("corporate", "企业"):
        if non_instructional_factors:
            # Mixed signals: some training, some non-training
            recommendations.append(
                "该目标同时包含培训和非培训因素。建议："
                "先排除非培训因素（流程、工具、激励等），"
                "再确认剩余差距是否可通过培训解决"
            )
            is_instructional = has_instructional_signal and len(
                non_instructional_factors
            ) < 3
        elif not performance_problem:
            recommendations.append(
                "企业培训场景缺少绩效问题描述，"
                "建议先进行绩效分析确认是否需要培训"
            )
            is_instructional = has_instructional_signal
        else:
            # Has performance problem and no non-training factors
            is_instructional = True
    else:
        # K12 / higher-ed: usually instructional
        if non_instructional_factors:
            is_instructional = has_instructional_signal
            recommendations.append(
                "检测到非培训因素，建议重新审视问题是否适合用教学手段解决"
            )
        else:
            is_instructional = True

    # --- General recommendations -------------------------------------------
    if not is_instructional:
        recommendations.append(
            "当前问题可能不适合直接用教学方案解决，"
            "建议考虑以下替代方案：流程优化、工具改进、制度调整、"
            "激励机制设计、人员调配等"
        )
    elif has_instructional_signal and not non_instructional_factors:
        recommendations.append("该目标适合用教学/培训方案解决")

    return {
        "is_instructional": is_instructional,
        "non_instructional_factors": non_instructional_factors,
        "recommendations": recommendations,
    }


# ===================================================================
# Helpers
# ===================================================================

def _fuzzy_match_scene(raw: str) -> str | None:
    """Try to map a free-text scene label to a valid scene type."""
    raw_lower = raw.lower()
    mapping = {
        "k12": "k12",
        "中小学": "k12",
        "小学": "k12",
        "初中": "k12",
        "高中": "k12",
        "企业": "corporate",
        "corporate": "corporate",
        "培训": "corporate",
        "职场": "corporate",
        "大学": "higher_ed",
        "本科": "higher_ed",
        "研究生": "higher_ed",
        "higher": "higher_ed",
        "高职": "vocational",
        "技校": "vocational",
        "职业": "vocational",
        "vocational": "vocational",
        "自学": "self_study",
        "self": "self_study",
    }
    for key, val in mapping.items():
        if key in raw_lower:
            return val
    return None
