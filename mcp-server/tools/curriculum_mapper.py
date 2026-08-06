"""
Curriculum Mapper MCP Tools

Maps topics and instructional goals to curriculum standards, teaching
materials, and exam requirements.  Generates alignment tables that show
coverage and gaps across the three pillars: curriculum standards, teaching
materials, and examination requirements.

All functions are deterministic / pure -- no AI calls.
"""

import sys
import os
import re
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from core.ids import gen_source_id

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Alignment status keywords used throughout this module
ALIGNMENT_FORMAL = "formal"       # strong, official-level alignment
ALIGNMENT_LIMITED = "limited"     # partial / teacher-private alignment
ALIGNMENT_MISSING = "missing"     # no alignment found

# Source level prefixes that count as "formal"
_FORMAL_LEVEL_PREFIXES = ("A", "B")
_LIMITED_LEVEL_PREFIXES = ("C",)
_WEAK_LEVEL_PREFIXES = ("D", "E")

# Mapping from source_level first character to a human-readable label
_LEVEL_LABELS = {
    "A": "国家级/部委级标准",
    "B": "教材/考试大纲",
    "C": "参考资料",
    "D": "非正式来源",
    "E": "教师私有/未验证",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    """Lower-case, strip whitespace, remove common Chinese particles."""
    if not text:
        return ""
    result = text.strip().lower()
    result = re.sub(r"[的了着过在与和或把被]", "", result)
    return result


def _keyword_overlap(text_a: str, text_b: str) -> float:
    """Return a 0-1 overlap score between two strings' character sets.

    Uses a simple character-bigram Jaccard-like measure, which works well
    for Chinese text where words are not space-separated.
    """
    if not text_a or not text_b:
        return 0.0

    a_norm = _normalise(text_a)
    b_norm = _normalise(text_b)

    a_bigrams = {a_norm[i:i+2] for i in range(max(0, len(a_norm) - 1))}
    b_bigrams = {b_norm[i:i+2] for i in range(max(0, len(b_norm) - 1))}

    if not a_bigrams or not b_bigrams:
        # Fallback to single-character overlap
        a_chars = set(a_norm)
        b_chars = set(b_norm)
        if not a_chars or not b_chars:
            return 0.0
        intersection = a_chars & b_chars
        union = a_chars | b_chars
        return len(intersection) / len(union)

    intersection = a_bigrams & b_bigrams
    union = a_bigrams | b_bigrams
    return len(intersection) / len(union) if union else 0.0


def _level_tier(source_level: str) -> str:
    """Classify a source_level string into 'formal', 'limited', or 'weak'."""
    if not source_level:
        return "weak"
    first = source_level[0].upper()
    if first in _FORMAL_LEVEL_PREFIXES:
        return "formal"
    if first in _LIMITED_LEVEL_PREFIXES:
        return "limited"
    return "weak"


def _extract_keywords(topic: dict) -> list[str]:
    """Extract a flat list of keyword strings from a topic dict."""
    keywords: list[str] = []
    for key in ("keywords", "topic_name"):
        val = topic.get(key, "")
        if isinstance(val, str) and val:
            keywords.append(val)
        elif isinstance(val, list):
            keywords.extend(str(v) for v in val)
    return keywords


def _match_score(topic_keywords: list[str], standard: dict) -> float:
    """Compute a relevance score between a topic and a standard entry.

    The score is the maximum keyword overlap across all standard text fields
    (title, description, knowledge_points).
    """
    if not topic_keywords:
        return 0.0

    standard_text = " ".join([
        standard.get("title", ""),
        standard.get("description", ""),
        " ".join(standard.get("knowledge_points", [])),
    ])

    if not standard_text.strip():
        return 0.0

    best = 0.0
    for kw in topic_keywords:
        score = _keyword_overlap(kw, standard_text)
        if score > best:
            best = score
    return best


# ---------------------------------------------------------------------------
# 1. map_topic_to_standards
# ---------------------------------------------------------------------------

def map_topic_to_standards(topic: dict, standard_matches: list) -> dict:
    """Map a topic to candidate curriculum standard clauses.

    Evaluates each candidate standard match and classifies the overall
    alignment status as ``"formal"``, ``"limited"``, or ``"missing"``.

    Parameters
    ----------
    topic : dict
        Topic descriptor with keys: ``stage``, ``grade``, ``subject``,
        ``topic_name``, ``keywords``.
    standard_matches : list
        List of standard entries (as returned by ``standards_search``).
        Each entry should have ``standard_id``, ``standard_code``,
        ``title``, ``description``, ``knowledge_points``,
        ``relevance_score``.

    Returns
    -------
    dict
        ``{alignment_status, aligned_sources, missing_evidence, recommendations}``
    """
    topic_keywords = _extract_keywords(topic)
    topic_name = topic.get("topic_name", "")
    subject = topic.get("subject", "")
    grade = topic.get("grade", "")

    aligned_sources: list[dict] = []
    missing_evidence: list[str] = []
    recommendations: list[str] = []

    best_tier = "weak"  # track the strongest tier found

    for standard in standard_matches:
        std_level = standard.get("standard_code", "")
        title = standard.get("title", "")
        description = standard.get("description", "")
        knowledge_points = standard.get("knowledge_points", [])

        # Compute match score
        score = _match_score(topic_keywords, standard)
        # Boost by the relevance_score already provided
        relevance = standard.get("relevance_score", 0.0)
        combined_score = max(score, relevance)

        tier = _level_tier(std_level)

        if combined_score >= 0.15 or tier in ("formal", "limited"):
            aligned_sources.append({
                "standard_id": standard.get("standard_id", ""),
                "standard_code": std_level,
                "title": title,
                "description": description,
                "knowledge_points": knowledge_points,
                "match_score": round(combined_score, 3),
                "alignment_tier": tier,
            })
            if _tier_rank(tier) > _tier_rank(best_tier):
                best_tier = tier

    # --- Determine overall alignment status ---------------------------------
    if best_tier == "formal":
        alignment_status = ALIGNMENT_FORMAL
    elif best_tier == "limited":
        alignment_status = ALIGNMENT_LIMITED
    else:
        alignment_status = ALIGNMENT_MISSING

    # --- Missing evidence ---------------------------------------------------
    if alignment_status == ALIGNMENT_MISSING:
        missing_evidence.append(
            f"未找到与主题「{topic_name}」(学科: {subject}, 年级: {grade}) "
            f"对齐的课程标准条款"
        )
        recommendations.append(
            "建议通过 standards_search 工具检索更多课程标准，"
            "或手动补充教材/课标依据"
        )
    elif alignment_status == ALIGNMENT_LIMITED:
        missing_evidence.append(
            "已有参考级别的标准来源，但缺少 A/B 级官方课程标准依据"
        )
        recommendations.append(
            "建议查找对应的国家课程标准或经审定教材以增强权威性"
        )
    else:
        recommendations.append(
            "已有官方课程标准对齐，建议在设计文档中明确引用标准条款编号"
        )

    # Sort aligned sources by match_score descending
    aligned_sources.sort(key=lambda s: s.get("match_score", 0), reverse=True)

    return {
        "alignment_status": alignment_status,
        "aligned_sources": aligned_sources,
        "missing_evidence": missing_evidence,
        "recommendations": recommendations,
    }


def _tier_rank(tier: str) -> int:
    """Numeric rank for tier comparison. Higher = stronger."""
    return {"formal": 3, "limited": 2, "weak": 1}.get(tier, 0)


# ---------------------------------------------------------------------------
# 2. map_goal_to_sources
# ---------------------------------------------------------------------------

def map_goal_to_sources(goal: dict, sources: list) -> dict:
    """Map an instructional goal to its supporting source records.

    Classifies each source into *formal*, *limited*, or *unsupported* based
    on its ``source_level``, ``can_be_goal_basis``, and
    ``copyright_scope`` fields.

    Parameters
    ----------
    goal : dict
        Instructional goal descriptor.  Expected keys: ``behavior``,
        ``context``, ``scene_type``, and optionally ``learner``,
        ``sources``.
    sources : list
        List of source records (conforming to ``source.schema.json``).

    Returns
    -------
    dict
        ``{has_formal_basis, formal_sources, limited_sources,
          unsupported_claims, recommendations}``
    """
    behavior = goal.get("behavior", "")
    context = goal.get("context", "")
    scene_type = goal.get("scene_type", "k12")

    formal_sources: list[dict] = []
    limited_sources: list[dict] = []
    unsupported_claims: list[str] = []
    recommendations: list[str] = []

    for src in sources:
        source_level = src.get("source_level", "")
        can_be_basis = src.get("can_be_goal_basis", "no")
        copyright_scope = src.get("copyright_scope", "unknown")
        tier = _level_tier(source_level)

        # A source is "formal" if it is A/B-level AND can serve as goal basis
        # AND is not restricted to private use only.
        is_formal_candidate = (
            tier == "formal"
            and can_be_basis in ("yes", "limited")
            and copyright_scope != "teacher_private_use_only"
        )

        # A source is "limited" if it is C-level or teacher-private but
        # still carries some evidentiary value.
        is_limited_candidate = (
            tier == "limited"
            or (tier == "formal" and copyright_scope == "teacher_private_use_only")
            or can_be_basis == "limited"
        )

        record = {
            "source_id": src.get("source_id", ""),
            "source_name": src.get("source_name", ""),
            "source_level": source_level,
            "source_category": src.get("source_category", ""),
            "can_be_goal_basis": can_be_basis,
            "credibility": src.get("credibility", "uncertain"),
        }

        if is_formal_candidate:
            formal_sources.append(record)
        elif is_limited_candidate:
            limited_sources.append(record)
        # else: not counted -- does not support the goal

    # --- Determine overall support status -----------------------------------
    has_formal_basis = len(formal_sources) > 0

    if not has_formal_basis and not limited_sources:
        unsupported_claims.append(
            f"教学目的「{behavior}」当前无任何来源支撑"
        )
        recommendations.append(
            "建议通过 knowledge_ingest 上传教师参考资料，"
            "或通过 standards_search 检索官方课程标准"
        )
    elif not has_formal_basis:
        unsupported_claims.append(
            f"教学目的「{behavior}」仅有有限来源支撑，缺少 A/B 级正式依据"
        )
        recommendations.append(
            "建议补充官方课程标准或审定教材以增强教学目的的权威性"
        )
    else:
        recommendations.append(
            "已有正式来源支撑教学目的，建议在设计文档中保留引用路径"
        )

    # Scene-specific notes
    if scene_type == "k12":
        if not has_formal_basis:
            recommendations.append(
                "K12 场景必须有 A/B 级课程标准或教材依据方可作为正式教学目的"
            )
    elif scene_type == "corporate":
        if not formal_sources and not limited_sources:
            recommendations.append(
                "企业培训场景建议提供岗位分析、SOP 或绩效数据作为目的依据"
            )

    return {
        "has_formal_basis": has_formal_basis,
        "formal_sources": formal_sources,
        "limited_sources": limited_sources,
        "unsupported_claims": unsupported_claims,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 3. generate_curriculum_alignment_table
# ---------------------------------------------------------------------------

def generate_curriculum_alignment_table(project: dict) -> dict:
    """Generate a curriculum / teaching material / exam alignment table.

    Analyses the project's ``sources``, ``goal``, and ``metadata`` to
    produce a structured alignment table covering three pillars:

    1. **Curriculum standards** (课程标准)
    2. **Teaching materials** (教材)
    3. **Exam requirements** (考试要求)

    Parameters
    ----------
    project : dict
        Full project dict.  Expected keys: ``goal``, ``sources``,
        ``metadata`` (with ``subject``, ``grade_level``), and optionally
        ``skill_graph``, ``objectives``.

    Returns
    -------
    dict
        ``{curriculum_standards, teaching_materials, exam_requirements,
          alignment_status, missing_gaps}``
    """
    goal = project.get("goal", {})
    sources = project.get("sources", [])
    metadata = project.get("metadata", {})
    subject = metadata.get("subject", "")
    grade_level = metadata.get("grade_level", "")

    curriculum_standards: list[dict] = []
    teaching_materials: list[dict] = []
    exam_requirements: list[dict] = []
    missing_gaps: list[str] = []

    # --- Classify each source into a pillar ---------------------------------
    for src in sources:
        src_level = src.get("source_level", "")
        src_category = src.get("source_category", "")
        src_name = src.get("source_name", "")
        tier = _level_tier(src_level)

        record = {
            "source_id": src.get("source_id", ""),
            "source_name": src_name,
            "source_level": src_level,
            "alignment_tier": tier,
            "credibility": src.get("credibility", "uncertain"),
            "can_be_goal_basis": src.get("can_be_goal_basis", "no"),
            "copyright_scope": src.get("copyright_scope", "unknown"),
            "specific_clauses": src.get("specific_clauses", []),
        }

        # Heuristic classification
        level_first = src_level[0].upper() if src_level else ""

        is_curriculum = (
            src_category == "official_authority"
            or level_first == "A"
            or any(kw in src_name for kw in ("课程标准", "课标", "纲要", "标准"))
        )

        is_material = (
            level_first == "B"
            or src_category == "professional_authority"
            or any(kw in src_name for kw in ("教材", "课本", "教科书", "教学参考"))
        )

        is_exam = (
            any(kw in src_name for kw in ("考试", "考纲", "中考", "高考", "会考", "期末"))
            or "exam" in src_name.lower()
        )

        if is_curriculum:
            curriculum_standards.append(record)
        if is_material:
            teaching_materials.append(record)
        if is_exam:
            exam_requirements.append(record)

        # If none of the categories matched, file under teaching materials
        # as a generic reference
        if not (is_curriculum or is_material or is_exam):
            teaching_materials.append(record)

    # --- Identify missing gaps ----------------------------------------------
    has_curriculum = len(curriculum_standards) > 0
    has_material = len(teaching_materials) > 0
    has_exam = len(exam_requirements) > 0

    scene_type = goal.get("scene_type", metadata.get("scene_type", "k12"))

    if not has_curriculum:
        missing_gaps.append(
            f"缺少课程标准来源 (学科: {subject}, 年级: {grade_level})"
        )
    if not has_material:
        missing_gaps.append(
            f"缺少教材来源 (学科: {subject}, 年级: {grade_level})"
        )
    if not has_exam:
        missing_gaps.append(
            f"缺少考试要求来源 (学科: {subject}, 年级: {grade_level})"
        )

    # K12-specific: curriculum + material are mandatory
    if scene_type == "k12":
        if not has_curriculum:
            missing_gaps.append(
                "K12 场景要求必须有课程标准依据，当前缺失"
            )
        if not has_material:
            missing_gaps.append(
                "K12 场景要求必须有教材依据，当前缺失"
            )

    # --- Determine overall alignment status ---------------------------------
    if not has_curriculum and not has_material:
        alignment_status = ALIGNMENT_MISSING
    elif not has_curriculum or not has_material:
        alignment_status = ALIGNMENT_LIMITED
    else:
        # Check if at least one is formal-tier
        any_formal = any(
            s.get("alignment_tier") == "formal"
            for s in curriculum_standards + teaching_materials
        )
        alignment_status = ALIGNMENT_FORMAL if any_formal else ALIGNMENT_LIMITED

    return {
        "curriculum_standards": curriculum_standards,
        "teaching_materials": teaching_materials,
        "exam_requirements": exam_requirements,
        "alignment_status": alignment_status,
        "missing_gaps": missing_gaps,
    }
