"""
Source Reliability -- source level classification and usage validation.

Classifies source reliability based on source_category, publisher,
and level fields. Validates whether sources can support instructional
goals, and checks copyright / usage constraints.

All functions are pure / deterministic -- no AI calls.
"""

import sys
import os

# ---------------------------------------------------------------------------
# Path setup so that ``from core.xxx import ...`` works when the file is
# executed directly or when the package is loaded by the MCP server.
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_THIS_DIR)
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)


# ===================================================================
# Constants -- source level definitions per source-reliability-policy.md
# ===================================================================

# Source level -> (category, base_credibility, can_be_goal_basis)
# can_be_goal_basis values: "yes", "limited", "no"
LEVEL_DEFINITIONS = {
    # A: Official authority
    "A1": ("official_authority", "highest", "yes"),
    "A2": ("official_authority", "highest", "yes"),
    "A3": ("official_authority", "highest", "yes"),
    "A4": ("official_authority", "high", "yes"),
    "A5": ("official_authority", "high", "yes"),
    # B: Professional authority
    "B1": ("professional_authority", "high", "yes"),
    "B2": ("professional_authority", "high", "yes"),
    "B3": ("professional_authority", "high", "yes"),
    "B4": ("professional_authority", "high", "yes"),
    "B5": ("professional_authority", "medium_high", "limited"),
    # C: Teacher private
    "C1": ("teacher_private", "medium", "limited"),
    "C2": ("teacher_private", "medium", "limited"),
    "C3": ("teacher_private", "medium", "limited"),
    "C4": ("teacher_private", "medium", "limited"),
    "C5": ("teacher_private", "medium", "limited"),
    # D: Public
    "D1": ("public", "medium_low", "no"),
    "D2": ("public", "low", "no"),
    "D3": ("public", "low", "no"),
    "D4": ("public", "low", "no"),
    # E: AI generated
    "E1": ("ai_generated", "uncertain", "no"),
    "E2": ("ai_generated", "uncertain", "no"),
    "E3": ("ai_generated", "uncertain", "no"),
}

# Scene type -> set of source levels that count as formal goal basis
# Per source-reliability-policy.md section 3.1
SCENE_GOAL_BASIS_LEVELS = {
    "k12": {"A1", "A2", "A3", "A4", "A5", "B1", "B2"},
    "higher_ed": {"A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5"},
    "vocational": {"A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5"},
    "corporate": {"B4", "C1", "C2", "C3", "C4", "C5"},
    "general": {"A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5"},
    "self_study": {"A1", "A2", "A3", "A4", "A5", "B1", "B2", "B3", "B4", "B5"},
}

# Scene type -> description in Chinese
SCENE_DESCRIPTIONS = {
    "k12": "K12中小学教学",
    "higher_ed": "高校教学",
    "vocational": "职业教育",
    "corporate": "企业培训",
    "general": "通用教学",
    "self_study": "自学",
}


# ===================================================================
# 1. classify_source_level
# ===================================================================

def classify_source_level(source: dict) -> dict:
    """Classify source level based on source_category, publisher, level field.

    Examines the source dict for explicit level fields, category information,
    and publisher metadata to determine the authoritative source level.

    Parameters
    ----------
    source : dict
        Source record.  Expected keys (optional but helpful):
        - source_level (str): explicit level code, e.g. "A1", "B2"
        - source_category (str): category, e.g. "official_authority"
        - source_name (str): name of the source
        - publisher (str): publisher name
        - notes (str): additional notes

    Returns
    -------
    dict with keys:
        level (str): classified level code, e.g. "A1"
        credibility (str): credibility rating
        can_be_goal_basis (str): "yes", "limited", or "no"
        category (str): source category
    """
    # 1. If explicit source_level is provided and valid, use it directly
    explicit_level = source.get("source_level", "")
    if explicit_level and explicit_level in LEVEL_DEFINITIONS:
        cat, cred, goal_basis = LEVEL_DEFINITIONS[explicit_level]
        return {
            "level": explicit_level,
            "credibility": cred,
            "can_be_goal_basis": goal_basis,
            "category": source.get("source_category", cat),
        }

    # 2. If only the prefix letter is provided (e.g. "A", "B")
    if len(explicit_level) == 1 and explicit_level in ("A", "B", "C", "D", "E"):
        # Use the first sub-level for that letter
        cat, cred, goal_basis = LEVEL_DEFINITIONS[explicit_level + "1"]
        return {
            "level": explicit_level + "1",
            "credibility": cred,
            "can_be_goal_basis": goal_basis,
            "category": source.get("source_category", cat),
        }

    # 3. Try to infer from source_category
    source_category = source.get("source_category", "")
    if source_category:
        inferred = _infer_level_from_category(source_category, source)
        if inferred:
            return inferred

    # 4. Try to infer from publisher name
    publisher = source.get("publisher", "")
    source_name = source.get("source_name", "")
    inferred = _infer_level_from_publisher(publisher or source_name)
    if inferred:
        return inferred

    # 5. Default to D1 (public/unverified) -- safest assumption
    return {
        "level": "D1",
        "credibility": "medium_low",
        "can_be_goal_basis": "no",
        "category": source_category or "public",
    }


def _infer_level_from_category(category: str, source: dict) -> dict | None:
    """Infer source level from the source_category field."""
    category_level_map = {
        "official_authority": ("A1", "highest", "yes"),
        "professional_authority": ("B1", "high", "yes"),
        "teacher_private": ("C1", "medium", "limited"),
        "public": ("D1", "medium_low", "no"),
        "ai_generated": ("E1", "uncertain", "no"),
    }
    if category in category_level_map:
        level, cred, goal = category_level_map[category]
        # For official_authority, check if it's national vs provincial
        if category == "official_authority":
            name = source.get("source_name", "") + " " + source.get("notes", "")
            if "省" in name or "地方" in name:
                level = "A4"
            elif "国家" in name or "教育部" in name or "义务教育" in name:
                level = "A1"
        elif category == "professional_authority":
            name = source.get("source_name", "") + " " + source.get("notes", "")
            if "学术" in name or "著作" in name:
                level = "B5"
                cred = "medium_high"
                goal = "limited"
        return {
            "level": level,
            "credibility": cred,
            "can_be_goal_basis": goal,
            "category": category,
        }
    return None


def _infer_level_from_publisher(publisher: str) -> dict | None:
    """Infer source level from publisher name patterns."""
    if not publisher:
        return None

    pub_lower = publisher.lower()

    # National-level publishers / organizations
    national_keywords = [
        "教育部", "人民教育出版社", "北京师范大学出版社", "高等教育出版社",
        "人教版", "北师大版", "苏教版", "pep", "bnu",
    ]
    for kw in national_keywords:
        if kw.lower() in pub_lower:
            return {
                "level": "A1",
                "credibility": "highest",
                "can_be_goal_basis": "yes",
                "category": "official_authority",
            }

    # Provincial / municipal education authorities
    provincial_keywords = ["省教育厅", "市教育局", "省教研", "市教研"]
    for kw in provincial_keywords:
        if kw in publisher:
            return {
                "level": "A4",
                "credibility": "high",
                "can_be_goal_basis": "yes",
                "category": "official_authority",
            }

    # Textbook publishers (professional)
    textbook_keywords = ["出版社", "出版", "教材", "教参"]
    for kw in textbook_keywords:
        if kw in publisher:
            return {
                "level": "B1",
                "credibility": "high",
                "can_be_goal_basis": "yes",
                "category": "professional_authority",
            }

    # Wikipedia / encyclopedia
    encyclopedia_keywords = ["维基", "百科", "wikipedia", "baike"]
    for kw in encyclopedia_keywords:
        if kw in pub_lower:
            return {
                "level": "D2",
                "credibility": "low",
                "can_be_goal_basis": "no",
                "category": "public",
            }

    # Blog / social media
    blog_keywords = ["博客", "blog", "公众号", "自媒体", "知乎", "微博"]
    for kw in blog_keywords:
        if kw in pub_lower:
            return {
                "level": "D3",
                "credibility": "low",
                "can_be_goal_basis": "no",
                "category": "public",
            }

    return None


# ===================================================================
# 2. can_source_support_goal
# ===================================================================

def can_source_support_goal(source: dict, scene_type: str) -> dict:
    """Check if source can support instructional goal as formal basis.

    Implements the rules from source-reliability-policy.md section 3.1:
    - K12: A/B level official = formal, C = limited, D/E = not allowed
    - Higher ed: A/B = formal, C = limited, D/E = not allowed
    - Vocational: A/B = formal, C = limited, D/E = not allowed
    - Corporate: B4 + C = formal, D/E = not allowed
    - General: A/B = formal, C = limited, D/E = not allowed

    Parameters
    ----------
    source : dict
        Source record with at least source_level.
    scene_type : str
        The instructional scene (k12, higher_ed, vocational, corporate,
        general).

    Returns
    -------
    dict with keys:
        can_support (bool): whether the source can support the goal
        support_level (str): "formal", "limited", or "not_allowed"
        reason (str): explanation in Chinese
    """
    # Normalize scene type
    scene_map = {
        "k12": "k12", "K12": "k12",
        "higher_ed": "higher_ed", "higher": "higher_ed",
        "vocational": "vocational",
        "corporate": "corporate", "企业": "corporate",
        "general": "general",
        "self_study": "self_study",
    }
    normalized_scene = scene_map.get(scene_type, scene_type)

    # Get source level
    level = source.get("source_level", "")
    if not level:
        # Try to classify from other fields
        classification = classify_source_level(source)
        level = classification.get("level", "")

    # Get the goal basis levels for this scene
    allowed_levels = SCENE_GOAL_BASIS_LEVELS.get(normalized_scene, set())

    # Special corporate handling: C level counts as formal basis
    if normalized_scene == "corporate":
        prefix = level[:1] if level else ""
        if level in allowed_levels or (prefix == "C"):
            return {
                "can_support": True,
                "support_level": "formal",
                "reason": f"企业培训场景下，{level}级别来源可以作为教学目的正式依据",
            }
        elif prefix == "A" or (prefix == "B" and level not in {"B5"}):
            return {
                "can_support": True,
                "support_level": "formal",
                "reason": f"{level}级别来源高于企业培训场景最低要求，可以作为正式依据",
            }
        elif prefix == "D":
            return {
                "can_support": False,
                "support_level": "not_allowed",
                "reason": "D级别公开来源不可作为企业培训的教学目的依据",
            }
        elif prefix == "E":
            return {
                "can_support": False,
                "support_level": "not_allowed",
                "reason": "AI生成来源不可作为教学目的依据",
            }
        else:
            return {
                "can_support": False,
                "support_level": "not_allowed",
                "reason": f"{level}级别来源不可作为企业培训的教学目的依据",
            }

    # Standard scenes (K12, higher_ed, vocational, general)
    if level in allowed_levels:
        # Determine if formal or limited
        prefix = level[:1] if level else ""
        if prefix in ("A", "B") and level != "B5":
            return {
                "can_support": True,
                "support_level": "formal",
                "reason": f"{level}级别来源可以作为{SCENE_DESCRIPTIONS.get(normalized_scene, normalized_scene)}的教学目的正式依据",
            }
        elif level == "B5":
            return {
                "can_support": True,
                "support_level": "limited",
                "reason": "B5学术著作来源作为目标依据时效力有限，建议配合更高级别来源",
            }

    # Check for limited support
    prefix = level[:1] if level else ""
    if prefix == "C":
        return {
            "can_support": True,
            "support_level": "limited",
            "reason": f"C级别教师私有来源在{SCENE_DESCRIPTIONS.get(normalized_scene, normalized_scene)}场景下作为目标依据效力有限，需要教师确认验证",
        }

    # Not allowed
    if prefix == "D":
        return {
            "can_support": False,
            "support_level": "not_allowed",
            "reason": "D级别公开来源不可作为教学目的依据",
        }
    if prefix == "E":
        return {
            "can_support": False,
            "support_level": "not_allowed",
            "reason": "AI生成来源不可作为教学目的依据",
        }

    return {
        "can_support": False,
        "support_level": "not_allowed",
        "reason": f"无法确认{level}级别来源的适用性",
    }


# ===================================================================
# 3. validate_source_usage
# ===================================================================

def validate_source_usage(source: dict, intended_use: str) -> dict:
    """Check copyright and usage scope constraints.

    Implements the rules from source-reliability-policy.md section 7:
    - teacher_private_use_only cannot be publicly exported
    - official_public can be referenced but not redistributed
    - Each use scope has specific constraints

    Parameters
    ----------
    source : dict
        Source record with copyright_scope and use_scope fields.
    intended_use : str
        How the source will be used. One of:
        - "goal_basis": use as formal basis for instructional goal
        - "content_reference": reference for content design
        - "assessment_generation": generate assessments from source
        - "strategy_design": use for instructional strategy
        - "public_export": include in exported design package
        - "private_reference_only": use only as private reference

    Returns
    -------
    dict with keys:
        valid (bool): whether the intended use is allowed
        violations (list[str]): list of violation descriptions
        recommendations (list[str]): list of alternative recommendations
    """
    violations = []
    recommendations = []

    copyright_scope = source.get("copyright_scope", "unknown")
    use_scope = source.get("use_scope", [])
    source_name = source.get("source_name", "未知来源")
    source_level = source.get("source_level", "")

    # --- Check copyright constraints -------------------------------------------
    if copyright_scope == "teacher_private_use_only":
        if intended_use == "public_export":
            violations.append(
                f"来源 \"{source_name}\" 版权范围为仅教师私用，"
                "不得包含在公开导出的设计包中"
            )
            recommendations.append(
                f"将 \"{source_name}\" 的引用替换为设计生成的内容摘要，"
                "不包含原文"
            )
            recommendations.append(
                "在设计报告中标注来源名称（不暴露原文内容）"
            )
        elif intended_use == "goal_basis":
            violations.append(
                f"来源 \"{source_name}\" 版权范围为仅教师私用，"
                "作为教学目的依据时需要教师明确确认"
            )
            recommendations.append(
                "请教师确认该来源可以作为教学目的依据"
            )
            recommendations.append(
                "考虑使用更高权威级别的公开来源替代"
            )
        elif intended_use == "strategy_design":
            recommendations.append(
                f"来源 \"{source_name}\" 为教师私用，"
                "策略设计中引用时请注明为教师个人资料"
            )

    elif copyright_scope == "public_domain":
        if intended_use == "goal_basis":
            recommendations.append(
                f"来源 \"{source_name}\" 为公共领域内容，"
                "作为教学目的依据时可信度较低，建议配合权威来源使用"
            )

    elif copyright_scope == "official_public":
        if intended_use == "public_export":
            recommendations.append(
                f"来源 \"{source_name}\" 为官方公开内容，"
                "导出时应注明出处并标注引用信息"
            )

    elif copyright_scope == "licensed":
        if intended_use == "public_export":
            recommendations.append(
                f"来源 \"{source_name}\" 为授权使用内容，"
                "导出前请确认授权范围是否覆盖公开分发"
            )

    elif copyright_scope == "unknown":
        if intended_use == "public_export":
            violations.append(
                f"来源 \"{source_name}\" 版权范围未知，"
                "不得在未确认版权的情况下公开导出"
            )
            recommendations.append(
                "请确认该来源的版权范围后再进行导出操作"
            )

    # --- Check use_scope constraints -------------------------------------------
    if isinstance(use_scope, list) and use_scope:
        # Map intended_use to the corresponding use_scope tag
        scope_tag_map = {
            "goal_basis": "goal_basis",
            "content_reference": "content_reference",
            "assessment_generation": "assessment_generation",
            "strategy_design": "strategy_design",
            "public_export": "not_for_public_export",
            "private_reference_only": "private_reference_only",
        }
        required_tag = scope_tag_map.get(intended_use, "")

        if intended_use == "public_export":
            # Check if "not_for_public_export" is in use_scope
            if "not_for_public_export" in use_scope:
                violations.append(
                    f"来源 \"{source_name}\" 的使用范围包含"
                    "\"not_for_public_export\"，不得公开导出"
                )
                recommendations.append(
                    "在导出包中移除此来源的直接引用"
                )
                recommendations.append(
                    "仅引用基于此来源生成的设计内容"
                )
        elif intended_use == "goal_basis":
            if "goal_basis" not in use_scope and "private_reference_only" in use_scope:
                violations.append(
                    f"来源 \"{source_name}\" 的使用范围仅限私用参考，"
                    "不可作为教学目的的正式依据"
                )
                recommendations.append(
                    "请获取更高级别来源，或由教师确认此来源可作为目标依据"
                )
            elif "goal_basis" not in use_scope:
                violations.append(
                    f"来源 \"{source_name}\" 的使用范围不包含"
                    "\"goal_basis\"，不可作为教学目的依据"
                )
                recommendations.append(
                    "检查来源等级和版权范围，确认是否需要更高级别的来源"
                )

        # Check for "private_reference_only" in use_scope
        if "private_reference_only" in use_scope:
            if intended_use in ("public_export", "strategy_design"):
                recommendations.append(
                    f"来源 \"{source_name}\" 标记为仅私用参考，"
                    f"在{intended_use}中使用时请注意不公开暴露原文内容"
                )

    # --- Additional level-based checks -----------------------------------------
    if source_level:
        prefix = source_level[:1]
        if prefix in ("D", "E") and intended_use == "goal_basis":
            if not violations:
                violations.append(
                    f"来源 \"{source_name}\" 等级为 {source_level}，"
                    "不可作为教学目的依据"
                )
            recommendations.append(
                "请使用A/B级别的官方或专业来源作为教学目的依据"
            )

    valid = len(violations) == 0

    return {
        "valid": valid,
        "violations": violations,
        "recommendations": recommendations,
    }


# ===================================================================
# 4. summarize_source_chain
# ===================================================================

def summarize_source_chain(sources: list) -> dict:
    """Summarize all sources to determine if final goal basis is met.

    Evaluates the entire collection of sources to determine overall
    reliability, identifies blocked sources, and provides actionable
    recommendations.

    Parameters
    ----------
    sources : list[dict]
        List of source records (each conforming to source.schema.json).

    Returns
    -------
    dict with keys:
        status (str): "sufficient", "partial", "insufficient", "unknown"
        highest_level (str): the highest source level found
        has_formal_goal_basis (bool): whether any source provides formal basis
        limited_sources (list[dict]): sources with limited support
        blocked_sources (list[dict]): sources that cannot be used
        recommendations (list[str]): actionable next steps
    """
    if not sources:
        return {
            "status": "insufficient",
            "highest_level": "",
            "has_formal_goal_basis": False,
            "limited_sources": [],
            "blocked_sources": [],
            "recommendations": [
                "未提供任何来源，请添加课程标准、教材或其他权威来源",
            ],
        }

    recommendations = []
    limited_sources = []
    blocked_sources = []
    formal_sources = []
    level_priority = {
        "A1": 1, "A2": 2, "A3": 3, "A4": 4, "A5": 5,
        "B1": 6, "B2": 7, "B3": 8, "B4": 9, "B5": 10,
        "C1": 11, "C2": 12, "C3": 13, "C4": 14, "C5": 15,
        "D1": 16, "D2": 17, "D3": 18, "D4": 19,
        "E1": 20, "E2": 21, "E3": 22,
    }

    highest_priority = 999  # lower = better
    highest_level = ""

    for source in sources:
        level = source.get("source_level", "")
        classification = classify_source_level(source)
        effective_level = level or classification.get("level", "")

        # Update highest level
        priority = level_priority.get(effective_level, 999)
        if priority < highest_priority:
            highest_priority = priority
            highest_level = effective_level

        # Check goal basis
        goal_basis = source.get("can_be_goal_basis", classification.get("can_be_goal_basis", "no"))
        if goal_basis == "yes":
            formal_sources.append(source)
        elif goal_basis == "limited":
            limited_sources.append(source)
        else:
            blocked_sources.append(source)

        # Check for test fixture warnings
        if source.get("is_test_fixture", False):
            if source not in limited_sources and source not in blocked_sources:
                limited_sources.append(source)
                recommendations.append(
                    f"来源 \"{source.get('source_name', '')}\" 为测试数据，"
                    "不可用于正式教学设计"
                )

    has_formal = len(formal_sources) > 0

    # Determine status
    if has_formal and len(blocked_sources) == 0:
        status = "sufficient"
    elif has_formal and len(blocked_sources) > 0:
        status = "partial"
        recommendations.append(
            f"有 {len(blocked_sources)} 个来源不可用，"
            "但已有足够的正式依据来源"
        )
    elif not has_formal and len(limited_sources) > 0:
        status = "partial"
        recommendations.append(
            f"仅有 {len(limited_sources)} 个效力有限的来源，"
            "建议补充A/B级别的官方或专业来源"
        )
    elif len(sources) > 0 and not has_formal and not limited_sources:
        status = "insufficient"
        recommendations.append(
            "所有来源均不可作为教学目的依据，"
            "请添加A/B级别的官方或专业来源"
        )
    else:
        status = "unknown"

    # Generate specific recommendations based on blocked sources
    if blocked_sources:
        d_count = sum(
            1 for s in blocked_sources
            if s.get("source_level", "").startswith("D")
        )
        e_count = sum(
            1 for s in blocked_sources
            if s.get("source_level", "").startswith("E")
        )
        if d_count > 0:
            recommendations.append(
                f"有 {d_count} 个D级别公开来源不可作为依据，"
                "请替换为官方或专业来源"
            )
        if e_count > 0:
            recommendations.append(
                f"有 {e_count} 个AI生成来源不可作为依据，"
                "请使用真实来源替代"
            )

    # Count level distribution for status detail
    level_counts = {}
    for source in sources:
        level = source.get("source_level", "")
        prefix = level[:1] if level else "?"
        level_counts[prefix] = level_counts.get(prefix, 0) + 1

    # Deduplicate recommendations
    seen_recs = set()
    unique_recommendations = []
    for rec in recommendations:
        if rec not in seen_recs:
            seen_recs.add(rec)
            unique_recommendations.append(rec)

    return {
        "status": status,
        "highest_level": highest_level,
        "has_formal_goal_basis": has_formal,
        "limited_sources": limited_sources,
        "blocked_sources": blocked_sources,
        "recommendations": unique_recommendations,
        "_level_distribution": level_counts,
        "_formal_count": len(formal_sources),
        "_limited_count": len(limited_sources),
        "_blocked_count": len(blocked_sources),
    }
