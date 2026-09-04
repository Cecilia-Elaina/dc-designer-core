"""
Standards Search MCP Tools

Searches local curriculum standards data stored in:
- data/standards/source_registry.json (master registry)
- data/standards/k12/*.json and data/standards/high_school/*.json
- data/standards/test_fixtures/*.json (test only)

All functions are pure / deterministic -- no AI calls.
"""

import sys
import os
import re
import json
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup so that ``from core.xxx import ...`` works when the file is
# executed directly or when the package is loaded by the MCP server.
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_THIS_DIR)
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

_DATA_ROOT = os.path.join(_PKG_ROOT, "..", "data", "standards")

from core.ids import gen_source_id


# ===================================================================
# Constants
# ===================================================================

# Subject aliases for fuzzy matching -- maps common variants to canonical forms
SUBJECT_ALIASES = {
    "语文": "语文",
    "数学": "数学",
    "英语": "英语",
    "物理": "物理",
    "化学": "化学",
    "生物": "生物",
    "生物学": "生物",
    "历史": "历史",
    "地理": "地理",
    "政治": "道德与法治",
    "思想政治": "道德与法治",
    "道德与法治": "道德与法治",
    "道德与法治": "道德与法治",
    "信息技术": "信息科技",
    "信息科技": "信息科技",
    "科学": "科学",
    "体育": "体育与健康",
    "体育与健康": "体育与健康",
    "音乐": "音乐",
    "美术": "美术",
    "艺术": "艺术",
    "综合实践": "综合实践活动",
    "综合实践活动": "综合实践活动",
    "劳动": "劳动",
}

# Stage level normalization
STAGE_NORMALIZE = {
    "小学": "primary",
    "小学阶段": "primary",
    "primary": "primary",
    "初中": "junior",
    "初中阶段": "junior",
    "junior": "junior",
    "junior_high": "junior",
    "高中": "senior",
    "普通高中": "senior",
    "senior": "senior",
    "senior_high": "senior",
    "义务教育": "compulsory",
    "义务教育阶段": "compulsory",
    "compulsory": "compulsory",
    "k12": "k12",
    "junior_secondary": "junior",
    "senior_secondary": "senior",
}


def _normalize_stage_token(value: str) -> str:
    """Normalize a single stage label without treating compulsory as a grade."""
    text = str(value or "").strip()
    return STAGE_NORMALIZE.get(text, text)


def _stage_set(value: object, grade_values: object = None) -> set[str]:
    """Return the concrete stages represented by a stage/grade field."""
    values = value if isinstance(value, (list, tuple, set)) else [value]
    stages: set[str] = set()
    for raw in values:
        token = _normalize_stage_token(str(raw or ""))
        if token == "compulsory":
            stages.update({"primary", "junior"})
        elif token == "k12":
            stages.update({"primary", "junior", "senior"})
        elif token in {"primary", "junior", "senior"}:
            stages.add(token)
        elif raw:
            inferred, _ = _normalize_grade(str(raw))
            if inferred:
                stages.add(inferred)

    if grade_values:
        grade_items = (
            grade_values
            if isinstance(grade_values, (list, tuple, set))
            else [grade_values]
        )
        for raw in grade_items:
            inferred, _ = _normalize_grade(str(raw or ""))
            if inferred:
                stages.add(inferred)
    return stages


def _standard_stage_set(standard: dict) -> set[str]:
    """Resolve stage from explicit fields and applicable grade ranges."""
    return _stage_set(
        standard.get("stage", standard.get("stages", "")),
        standard.get("grade_levels")
        or standard.get("applicable_grades")
        or standard.get("grades"),
    )


def _stage_matches(standard: dict, query_stage: str) -> float:
    """Return a stage score, or zero when a requested stage is incompatible."""
    if not query_stage:
        return 0.0
    query_stages = _stage_set(query_stage)
    source_stages = _standard_stage_set(standard)
    if not query_stages or not source_stages:
        return 0.0
    overlap = query_stages & source_stages
    if not overlap:
        return 0.0
    if query_stages == source_stages:
        return 1.0
    return 0.9 if len(overlap) == len(query_stages) else 0.75


# ===================================================================
# 1. search_standards
# ===================================================================

def search_standards(query: dict) -> dict:
    """Search local standards by stage, grade, subject, topic, keywords.

    Parameters
    ----------
    query : dict
        Keys:
        - stage (str): educational stage, e.g. "小学", "初中", "高中"
        - grade (str): specific grade, e.g. "三年级", "7年级"
        - subject (str): subject area, e.g. "数学", "信息科技"
        - topic (str): topic or content area, e.g. "分数运算", "算法"
        - keywords (list[str]): additional search keywords
        - scene_type (str): k12, higher_ed, vocational, corporate, general

    Returns
    -------
    dict with keys:
        status, query, matches, sources, fallback_required,
        next_actions, message
    """
    stage = query.get("stage", "")
    grade = query.get("grade", "")
    subject = query.get("subject", "")
    topic = query.get("topic", "")
    keywords = query.get("keywords", [])
    scene_type = query.get("scene_type", "k12")

    if isinstance(keywords, str):
        keywords = [keywords] if keywords else []

    # Build search text from query components
    search_text = " ".join([
        topic,
        " ".join(keywords) if isinstance(keywords, list) else str(keywords),
    ]).strip()

    # Load all available standard records
    all_standards = _load_all_standards()

    if not all_standards:
        return {
            "status": "not_found",
            "query": query,
            "matches": [],
            "sources": [],
            "fallback_required": True,
            "next_actions": [
                "本地标准数据目录为空，请先导入课程标准数据",
                "可上传课程标准原文（PDF/图片）至教师知识库",
            ],
            "message": "标准数据目录为空，无可用标准记录",
        }

    # Filter and score each standard
    scored_matches = []
    for std in all_standards:
        norm = _normalize_standard_fields(std)
        score = _compute_match_score(norm, subject, grade, stage, search_text)
        if score > 0.0:
            scored_matches.append((score, norm))

    # Sort by score descending
    scored_matches.sort(key=lambda x: x[0], reverse=True)

    # Limit to top 20 results
    matches = []
    for score, std in scored_matches[:20]:
        match_record = {
            "standard_id": std.get("source_id", std.get("standard_id", "")),
            "source_name": std.get("source_name", std.get("title", "")),
            "title": std.get("title", std.get("source_name", "")),
            "description": std.get("description", ""),
            "subject": std.get("subject", ""),
            "grade": std.get("grade", ""),
            "stage": std.get("stage", ""),
            "grade_levels": std.get("grade_levels", std.get("applicable_grades", [])),
            "version": std.get("version", std.get("source_version", "")),
            "source_url": std.get("source_url", ""),
            "content_sha256": std.get("content_sha256", ""),
            "content_hash_status": std.get("content_hash_status", ""),
            "keywords": std.get("keywords", []),
            "source_level": std.get("source_level", ""),
            "source_category": std.get("source_category", ""),
            "applicable_scenes": std.get("applicable_scenes", ["k12"]),
            "specific_clauses": std.get("specific_clauses", std.get("clauses", [])),
            "verification_status": std.get("verification_status", ""),
            "teacher_confirmation_required": std.get("teacher_confirmation_required", False),
            "relevance_score": round(score, 3),
            "data_file": std.get("_data_file", ""),
            "is_test_fixture": std.get("is_test_fixture", False),
        }
        matches.append(match_record)

    # Build source records for each match
    sources = [build_source_record_from_standard(m) for m in matches]

    # Determine fallback requirement:
    # - No matches at all, or
    # - No A/B level sources found among matches
    has_ab_source = any(
        s.get("source_level", "").startswith(("A", "B"))
        for s in sources
    )
    fallback_required = len(matches) == 0 or not has_ab_source

    # Determine status and message
    if len(matches) == 0:
        status = "not_found"
        message = f"未找到与查询条件匹配的标准记录（学科: {subject}, 年级: {grade}）"
        next_actions = [
            "尝试扩大搜索范围（减少筛选条件）",
            "请教师上传相关课程标准原文（PDF/图片）",
            "上传后可在教师知识库中检索使用",
        ]
    elif not has_ab_source:
        status = "partial"
        message = (
            f"找到 {len(matches)} 条匹配记录，"
            "但无A/B级官方来源，无法直接作为教学目的依据"
        )
        next_actions = [
            "请教师上传或确认课程标准原文以获取A/B级来源",
            "当前结果可作为内容参考，但不可作为教学目的依据",
        ]
    else:
        status = "found"
        message = f"找到 {len(matches)} 条匹配标准，包含A/B级官方来源"
        next_actions = [
            "选择最匹配的标准记录作为教学目的依据",
            "在设计报告中标注来源追溯信息",
        ]

    return {
        "status": status,
        "query": query,
        "matches": matches,
        "sources": sources,
        "fallback_required": fallback_required,
        "next_actions": next_actions,
        "message": message,
    }


# ===================================================================
# 2. get_standard_source
# ===================================================================

def get_standard_source(source_id: str) -> dict:
    """Get full metadata for a standard source by ID.

    Parameters
    ----------
    source_id : str
        The unique identifier of the standard (e.g. "k12-math-primary-2022").

    Returns
    -------
    dict with keys:
        status, source (full source dict or None), message
    """
    if not source_id or not isinstance(source_id, str):
        return {
            "status": "error",
            "source": None,
            "message": "请提供有效的来源ID",
        }

    all_standards = _load_all_standards()

    for std in all_standards:
        norm = _normalize_standard_fields(std)
        std_id = norm.get("source_id", norm.get("standard_id", ""))
        if std_id == source_id:
            source = build_source_record_from_standard({
                "standard_id": std_id,
                "source_name": norm.get("source_name", norm.get("title", "")),
                "title": norm.get("title", norm.get("source_name", "")),
                "description": norm.get("description", ""),
                "subject": norm.get("subject", ""),
                "grade": norm.get("grade", ""),
                "stage": norm.get("stage", ""),
                "grade_levels": norm.get("grade_levels", norm.get("applicable_grades", [])),
                "version": norm.get("version", norm.get("source_version", "")),
                "source_url": norm.get("source_url", ""),
                "keywords": norm.get("keywords", []),
                "source_level": norm.get("source_level", ""),
                "source_category": norm.get("source_category", ""),
                "applicable_scenes": norm.get("applicable_scenes", ["k12"]),
                "specific_clauses": norm.get("specific_clauses", norm.get("clauses", [])),
                "verification_status": norm.get("verification_status", ""),
                "teacher_confirmation_required": norm.get("teacher_confirmation_required", False),
                "relevance_score": 1.0,
                "data_file": norm.get("_data_file", ""),
                "is_test_fixture": norm.get("is_test_fixture", False),
            })
            return {
                "status": "found",
                "source": source,
                "message": f"已获取来源 {source_id} 的完整信息",
            }

    return {
        "status": "not_found",
        "source": None,
        "message": f"未找到ID为 {source_id} 的标准来源",
    }


# ===================================================================
# 3. rank_standard_matches
# ===================================================================

def rank_standard_matches(matches: list, query: dict) -> dict:
    """Rank matches by subject match, grade match, keyword overlap, source level.

    Parameters
    ----------
    matches : list[dict]
        List of match dicts (from search_standards output).
    query : dict
        Original query dict.

    Returns
    -------
    dict with keys:
        ranked_matches, top_match, scoring_breakdown
    """
    stage = query.get("stage", "")
    grade = query.get("grade", "")
    subject = query.get("subject", "")
    topic = query.get("topic", "")
    keywords = query.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [keywords] if keywords else []

    ranked = []
    for match in matches:
        subject_score = _score_subject_match(match, subject)
        grade_score = _score_grade_match(match, grade, stage)
        keyword_score = _score_keyword_overlap(match, keywords, topic)
        level_score = _score_source_level(match)

        total = (
            subject_score * 0.35
            + grade_score * 0.25
            + keyword_score * 0.25
            + level_score * 0.15
        )

        ranked.append({
            **match,
            "_rank_score": round(total, 3),
            "_scoring_breakdown": {
                "subject": round(subject_score, 3),
                "grade": round(grade_score, 3),
                "keyword": round(keyword_score, 3),
                "level": round(level_score, 3),
                "weighted_total": round(total, 3),
            },
        })

    ranked.sort(key=lambda x: x["_rank_score"], reverse=True)

    # Remove internal scoring keys from final output
    scoring_breakdown = {}
    for m in ranked:
        sid = m.get("standard_id", m.get("source_name", ""))
        scoring_breakdown[sid] = m.pop("_scoring_breakdown")

    top_match = ranked[0] if ranked else None

    return {
        "ranked_matches": ranked,
        "top_match": top_match,
        "scoring_breakdown": scoring_breakdown,
    }


# ===================================================================
# 4. build_source_record_from_standard
# ===================================================================

def build_source_record_from_standard(match: dict) -> dict:
    """Convert a standard match to a source.schema.json compatible record.

    Parameters
    ----------
    match : dict
        A match dict from search_standards, containing at minimum:
        standard_id, source_name, source_level, source_category, etc.

    Returns
    -------
    dict compliant with schemas/source.schema.json.
    Includes: source_id, source_level, source_name, credibility,
    can_be_goal_basis, retrieval_status, copyright_scope, use_scope,
    applicable_scenes, file_reference, is_test_fixture
    """
    # Normalize fields first (handles level->source_level, etc.)
    match = _normalize_standard_fields(match)
    source_level = match.get("source_level", "")
    source_category = match.get("source_category", "")
    is_test_fixture = match.get("is_test_fixture", False)

    # Determine credibility from source level
    credibility = _level_to_credibility(source_level)

    # Determine can_be_goal_basis from source level and test fixture flag
    can_be_goal_basis = _level_to_goal_basis(source_level)

    # Test fixture overrides
    if is_test_fixture:
        can_be_goal_basis = "test_only"
        credibility = "uncertain"
        if "limited" not in (match.get("warnings") or []):
            match.setdefault("warnings", []).append(
                "此来源为测试数据，不可用于正式教学设计"
            )

    # Determine applicable scenes from category
    applicable_scenes = match.get("applicable_scenes", [])
    if not applicable_scenes:
        applicable_scenes = _category_to_scenes(source_category)

    # Determine copyright scope from source level and category
    copyright_scope = match.get(
        "copyright_scope",
        _level_to_copyright(source_level, source_category),
    )

    # Determine use scope from source level and category
    use_scope = match.get(
        "use_scope",
        _level_to_use_scope(source_level, source_category),
    )

    # Build retrieval status
    retrieval_status = match.get("retrieval_status", "found")

    # Generate source ID
    existing_id = match.get("standard_id", "")
    if existing_id:
        source_id = existing_id
    else:
        source_id = gen_source_id()

    specific_clauses = match.get("specific_clauses") or match.get("clauses") or []
    record = {
        "source_id": source_id,
        "source_level": source_level,
        "source_category": source_category,
        "source_name": match.get("source_name", match.get("title", "")),
        "source_description": match.get("description", ""),
        "source_url": match.get("source_url", ""),
        "source_date": match.get("source_date", match.get("publication_date", "")),
        "source_version": match.get("source_version", match.get("version", "")),
        "stage": match.get("stage", ""),
        "subject": match.get("subject", ""),
        "source_file_name": match.get("source_file_name", ""),
        "content_sha256": match.get("content_sha256", ""),
        "content_hash_status": match.get("content_hash_status", ""),
        "grade_levels": match.get(
            "grade_levels",
            match.get("applicable_grades", []),
        ),
        "credibility": credibility,
        "can_be_goal_basis": can_be_goal_basis,
        "retrieval_status": retrieval_status,
        "copyright_scope": copyright_scope,
        "use_scope": use_scope,
        "applicable_scenes": applicable_scenes,
        "is_test_fixture": is_test_fixture,
        "file_reference": match.get("data_file", ""),
        "fallback_required": not source_level.startswith(("A", "B")),
        "specific_clauses": specific_clauses,
        "verified_by_teacher": bool(match.get("verified_by_teacher", False)),
        "teacher_confirmation_required": bool(
            match.get("teacher_confirmation_required", False)
        ),
        "verification_status": match.get("verification_status", ""),
        "notes": match.get("notes", ""),
    }

    # Add source-specific notes
    if is_test_fixture:
        record["notes"] = "测试数据，仅供单元测试使用"
    elif source_level.startswith(("A",)):
        record["notes"] = "官方权威来源"
    elif source_level.startswith(("B",)):
        record["notes"] = "专业权威来源"
    elif source_level.startswith(("C",)):
        record["notes"] = "教师私有来源，需要教师确认"
    elif source_level.startswith(("D",)):
        record["notes"] = "公开来源，不可作为教学目的依据"
    elif source_level.startswith(("E",)):
        record["notes"] = "AI生成来源，不可作为教学目的依据"

    # Add warnings for test fixtures
    if is_test_fixture:
        record.setdefault("warnings", [])
        if "此来源为测试数据，不可用于正式教学设计" not in record["warnings"]:
            record["warnings"].append("此来源为测试数据，不可用于正式教学设计")

    return record


# ===================================================================
# Internal helpers -- data loading
# ===================================================================

def _load_all_standards() -> list[dict]:
    """Load all standard records from local data directories.

    Scans source_registry.json, both stage directories, and test fixtures.
    Records are de-duplicated by source ID because the same official source is
    intentionally present in the registry, snapshot, and subject pack.
    Returns an empty list if no data files exist.
    """
    all_standards = []

    # 1. Load master registry
    registry_path = os.path.join(_DATA_ROOT, "source_registry.json")
    if os.path.isfile(registry_path):
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry_data = json.load(f)
            standards_list = []
            if isinstance(registry_data, list):
                standards_list = registry_data
            elif isinstance(registry_data, dict):
                # Handle { "standards": [...] } or { "sources": [...] } format
                standards_list = (
                    registry_data.get("standards")
                    or registry_data.get("sources")
                    or registry_data.get("records")
                    or []
                )
            for std in standards_list:
                std["_data_file"] = "source_registry.json"
                std.setdefault("is_test_fixture", False)
            all_standards.extend(standards_list)
        except (json.JSONDecodeError, OSError):
            pass

    # 2. Load K12 standards
    k12_dir = os.path.join(_DATA_ROOT, "k12")
    all_standards.extend(_load_standards_from_dir(k12_dir, is_test=False))

    # 3. Load regular senior-secondary standards
    senior_dir = os.path.join(_DATA_ROOT, "high_school")
    all_standards.extend(_load_standards_from_dir(senior_dir, is_test=False))

    # 4. Load test fixtures
    fixture_dir = os.path.join(_DATA_ROOT, "test_fixtures")
    all_standards.extend(_load_standards_from_dir(fixture_dir, is_test=True))

    return _deduplicate_standards(all_standards)


def _deduplicate_standards(records: list[dict]) -> list[dict]:
    """Merge duplicate source IDs while retaining the richest record."""
    by_id: dict[str, dict] = {}
    anonymous: list[dict] = []
    for record in records:
        source_id = record.get("source_id") or record.get("standard_id") or record.get("id")
        if not source_id:
            anonymous.append(record)
            continue
        if source_id not in by_id:
            by_id[source_id] = dict(record)
            continue
        merged = by_id[source_id]
        for key, value in record.items():
            if key == "_data_file":
                continue
            if value not in (None, "", [], {}):
                if key in {"keywords", "clauses", "specific_clauses"}:
                    current = merged.get(key) or []
                    additions = value if isinstance(value, list) else [value]
                    seen = {
                        json.dumps(item, ensure_ascii=False, sort_keys=True)
                        for item in current
                    }
                    for item in additions:
                        marker = json.dumps(item, ensure_ascii=False, sort_keys=True)
                        if marker not in seen:
                            current.append(item)
                            seen.add(marker)
                    merged[key] = current
                elif key not in merged or merged.get(key) in (None, "", [], {}):
                    merged[key] = value
        if record.get("is_test_fixture"):
            merged["is_test_fixture"] = True
    return anonymous + list(by_id.values())


def _load_standards_from_dir(directory: str, is_test: bool = False) -> list[dict]:
    """Load all JSON files from a directory, each expected to contain
    a list of standard records (or a single record dict), recursively."""
    records = []
    if not os.path.isdir(directory):
        return records

    filepaths = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(".json"):
                filepaths.append(os.path.join(root, filename))

    for filepath in sorted(filepaths):
        if not filepath.lower().endswith(".json"):
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        file_records = []
        if isinstance(data, list):
            file_records = data
        elif isinstance(data, dict):
            # Try common wrapper keys
            file_records = (
                data.get("standards")
                or data.get("sources")
                or data.get("records")
                or [data]
            )

        for rec in file_records:
            relative_path = os.path.relpath(filepath, _DATA_ROOT).replace("\\", "/")
            rec["_data_file"] = relative_path
            rec.setdefault("is_test_fixture", is_test)
            if is_test:
                rec["is_test_fixture"] = True
            records.append(rec)

    return records


# ===================================================================
# Internal helpers -- field normalization across data formats
# ===================================================================

def _normalize_standard_fields(std: dict) -> dict:
    """Normalize fields across registry and K12 data formats.

    Registry format uses: level, category, source_id, applicable_grades
    K12 format uses: source_level, source_category, standard_id, grade

    Returns a normalized dict with consistent field names.
    """
    normalized = dict(std)

    # Normalize ID
    if "source_id" not in normalized and "standard_id" in normalized:
        normalized["source_id"] = normalized["standard_id"]
    if "id" not in normalized and "source_id" in normalized:
        normalized["id"] = normalized["source_id"]

    # Normalize name
    if "source_name" not in normalized and "title" in normalized:
        normalized["source_name"] = normalized["title"]
    if "description" not in normalized and "source_description" in normalized:
        normalized["description"] = normalized["source_description"]

    # Normalize level
    if "source_level" not in normalized and "level" in normalized:
        normalized["source_level"] = normalized["level"]

    # Normalize category
    if "source_category" not in normalized and "category" in normalized:
        cat = normalized["category"]
        # Map registry category names to schema category names
        cat_map = {
            "curriculum_standard": "official_authority",
            "curriculum_plan": "official_authority",
            "examination_outline": "official_authority",
            "textbook": "professional_authority",
            "teaching_reference": "professional_authority",
            "teacher_private": "teacher_private",
            "public": "public",
            "ai_generated": "ai_generated",
        }
        normalized["source_category"] = cat_map.get(cat, cat)

    # Normalize grade from applicable_grades list
    if "grade" not in normalized:
        agg = normalized.get("applicable_grades", [])
        if isinstance(agg, list) and agg:
            normalized["grade"] = agg[0]  # Use first applicable grade
        else:
            normalized["grade"] = ""

    # Normalize keywords
    if "keywords" not in normalized:
        normalized["keywords"] = _extract_keywords_from_standard(normalized)

    return normalized


def _extract_keywords_from_standard(std: dict) -> list[str]:
    """Extract keywords from a standard record.

    Handles multiple data formats:
    - Direct 'keywords' field (list of strings)
    - 'content_areas' as list of dicts with 'keywords' sub-lists
    - 'content_areas' as dict with 'keywords' key
    """
    # Direct keywords field
    direct_kw = std.get("keywords")
    if isinstance(direct_kw, list):
        return direct_kw

    # content_areas: list of dicts with keywords sub-lists
    content_areas = std.get("content_areas", [])
    all_keywords = []
    if isinstance(content_areas, list):
        for area in content_areas:
            if isinstance(area, dict):
                area_kw = area.get("keywords", [])
                if isinstance(area_kw, list):
                    all_keywords.extend(area_kw)
    elif isinstance(content_areas, dict):
        area_kw = content_areas.get("keywords", [])
        if isinstance(area_kw, list):
            all_keywords.extend(area_kw)

    return all_keywords


# ===================================================================
# Internal helpers -- fuzzy matching
# ===================================================================

def _fuzzy_subject_match(source_subject: str, query_subject: str) -> float:
    """Fuzzy match between source subject and query subject.

    Returns a score from 0.0 (no match) to 1.0 (exact match).
    Uses alias normalization and substring matching.
    """
    if not source_subject or not query_subject:
        return 0.0

    # Normalize subjects via alias table
    norm_source = SUBJECT_ALIASES.get(source_subject, source_subject)
    norm_query = SUBJECT_ALIASES.get(query_subject, query_subject)

    # Exact match
    if norm_source == norm_query:
        return 1.0

    # Case-insensitive exact match (for English subject names)
    if norm_source.lower() == norm_query.lower():
        return 1.0

    # Short known labels may contain one another; a long free-text subject
    # query such as 古生物化石修复 must not be accepted as 生物.
    if (
        len(norm_source) <= 5
        and len(norm_query) <= 5
        and (norm_source in norm_query or norm_query in norm_source)
    ):
        return 0.8

    # Only accept meaningful CJK overlap. A single shared character must not
    # make unrelated subjects such as 数学 and 化学 match.
    source_chars = set(norm_source)
    query_chars = set(norm_query)
    if source_chars and query_chars:
        overlap = source_chars & query_chars
        union = source_chars | query_chars
        if union:
            jaccard = len(overlap) / len(union)
            if len(overlap) >= 2 and jaccard >= 0.5:
                return jaccard

    return 0.0


def _normalize_grade(grade_str: str) -> tuple:
    """Normalize a grade string to (stage, number) form.

    Examples:
        "三年级" -> ("primary", 3)
        "7年级"  -> ("junior", 7)
        "高一"   -> ("senior", 1)
    """
    if not grade_str:
        return ("", 0)

    grade_str = grade_str.strip()
    stage_only = {
        "小学": "primary",
        "小学阶段": "primary",
        "primary": "primary",
        "初中": "junior",
        "初中阶段": "junior",
        "junior": "junior",
        "高中": "senior",
        "普通高中": "senior",
        "senior": "senior",
    }
    if grade_str in stage_only:
        return (stage_only[grade_str], 0)

    # Chinese grade: X年级 or 第X学段
    m = re.search(r"(\d+)", grade_str)
    if m:
        num = int(m.group(1))
        if "高" in grade_str or "senior" in grade_str.lower():
            return ("senior", num)
        elif "初" in grade_str or "junior" in grade_str.lower():
            return ("junior", num)
        elif "小" in grade_str or "primary" in grade_str.lower():
            return ("primary", num)
        else:
            # Infer stage from number ranges
            if 1 <= num <= 6:
                return ("primary", num)
            elif 7 <= num <= 9:
                return ("junior", num)
            elif 10 <= num <= 12:
                return ("senior", num)
            return ("", num)

    # Chinese ordinal: 高一, 高二, 初一, etc.
    # Sort by length descending so "十二" is tried before "十"
    ordinal_map = {
        "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
        "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12,
    }
    for char_num, val in sorted(ordinal_map.items(), key=lambda x: len(x[0]), reverse=True):
        if char_num in grade_str:
            if "高" in grade_str:
                return ("senior", val)
            elif "初" in grade_str:
                return ("junior", val)
            elif "小" in grade_str:
                return ("primary", val)
            # Infer stage from number when no explicit stage prefix
            if 1 <= val <= 6:
                return ("primary", val)
            elif 7 <= val <= 9:
                return ("junior", val)
            elif 10 <= val <= 12:
                return ("senior", val)
            return ("", val)

    return ("", 0)


def _grade_matches(source_grade: object, query_grade: str, query_stage: str = "") -> float:
    """Check if source grade matches query grade.

    Returns 1.0 for exact match, 0.5 for same-stage match, 0.0 otherwise.
    """
    if not query_grade:
        return 0.2
    if not source_grade:
        return 0.0

    source_values = (
        list(source_grade)
        if isinstance(source_grade, (list, tuple, set))
        else [source_grade]
    )
    q_stage, q_num = _normalize_grade(query_grade)
    query_stage_set = _stage_set(query_stage) if query_stage else set()
    best = 0.0
    for source_value in source_values:
        source_text = str(source_value or "")
        src_stage, src_num = _normalize_grade(source_text)

        if source_text == query_grade:
            best = max(best, 1.0)
            continue
        if src_num == q_num and src_stage == q_stage and q_num:
            best = max(best, 1.0)
            continue
        if src_stage and q_stage and src_stage == q_stage:
            if q_num == 0 or src_num == 0:
                best = max(best, 0.5)
            elif abs(src_num - q_num) <= 1:
                best = max(best, 0.7)
            else:
                best = max(best, 0.4)
            continue
        if query_stage_set and src_stage in query_stage_set:
            best = max(best, 0.4)

    return best


def _source_grade_values(standard: dict) -> object:
    """Return all grade fields so a broad standard does not match one grade only."""
    return (
        standard.get("grade_levels")
        or standard.get("applicable_grades")
        or standard.get("grades")
        or standard.get("grade")
        or standard.get("grade_level")
        or []
    )


def _keyword_overlap(source_keywords: list, search_text: str) -> float:
    """Compute keyword overlap between source keywords and search text.

    Returns a score from 0.0 to 1.0.
    """
    if not source_keywords or not search_text:
        return 0.0

    search_lower = search_text.lower()
    search_chars = set(search_lower)

    overlap_count = 0
    total_keyword_chars = 0

    for kw in source_keywords:
        if not kw:
            continue
        kw_lower = kw.lower()
        total_keyword_chars += len(kw_lower)

        # Exact substring match
        if kw_lower in search_lower:
            overlap_count += len(kw_lower)
        # Character overlap
        else:
            kw_chars = set(kw_lower)
            char_overlap = len(kw_chars & search_chars)
            if char_overlap > len(kw_chars) * 0.5:
                overlap_count += char_overlap

    if total_keyword_chars == 0:
        return 0.0

    return min(overlap_count / total_keyword_chars, 1.0)


def _compute_match_score(
    standard: dict,
    subject: str,
    grade: str,
    stage: str,
    search_text: str,
) -> float:
    """Compute overall match score for a standard against query parameters.

    Returns 0.0 if the standard does not match minimum criteria.
    Otherwise returns a weighted score from >0.0 to 1.0.
    """
    score = 0.0
    has_criteria = False

    # Stage is a hard boundary: a senior-secondary standard cannot satisfy a
    # primary/junior query, and vice versa.
    if stage:
        stage_score = _stage_matches(standard, stage)
        if stage_score == 0.0:
            return 0.0
        score += stage_score * 0.15
        has_criteria = True

    # Subject match (required if provided)
    source_subject = standard.get("subject", "")
    if subject:
        subject_score = _fuzzy_subject_match(source_subject, subject)
        if subject_score == 0.0:
            # Also check subject in keywords -- handle content_areas as dict or list
            content_areas = standard.get("content_areas", {})
            if isinstance(content_areas, dict):
                kw_list = content_areas.get("keywords", [])
            else:
                kw_list = []
            kw_subject = _fuzzy_subject_match(
                " ".join(standard.get("keywords", kw_list)),
                subject,
            )
            if kw_subject == 0.0:
                return 0.0  # Subject mismatch is hard filter
        score += subject_score * 0.35
        has_criteria = True

    # Grade match (if provided)
    source_grade = _source_grade_values(standard)
    if grade:
        grade_score = _grade_matches(source_grade, grade, stage)
        score += grade_score * 0.25
        has_criteria = True

    # Keyword / topic overlap
    content_areas_kw = standard.get("content_areas", {})
    if isinstance(content_areas_kw, dict):
        content_areas_kw = content_areas_kw.get("keywords", [])
    else:
        content_areas_kw = []
    source_keywords = standard.get("keywords", content_areas_kw)
    if search_text:
        kw_score = _keyword_overlap(source_keywords, search_text)
        # Also check in title/name/description
        name_text = standard.get("name", standard.get("title", ""))
        desc_text = standard.get("description", "")
        text_fields = f"{name_text} {desc_text}".lower()
        for word in search_text.lower().split():
            if len(word) >= 2 and word in text_fields:
                kw_score = max(kw_score, 0.3)
        score += kw_score * 0.25 if stage else kw_score * 0.3
        has_criteria = True

    # Bonus for higher source levels
    source_level = standard.get("source_level", standard.get("level", ""))
    if source_level:
        level_bonus = {
            "A": 0.15, "A1": 0.15, "A2": 0.14, "A3": 0.13, "A4": 0.12, "A5": 0.11,
            "B": 0.10, "B1": 0.10, "B2": 0.09, "B3": 0.08, "B4": 0.07, "B5": 0.06,
            "C": 0.03, "C1": 0.03, "C2": 0.02, "C3": 0.02, "C4": 0.01, "C5": 0.01,
        }
        score += level_bonus.get(source_level, 0.0)

    if not has_criteria:
        # No criteria provided -- return minimal score for all standards
        return 0.05

    return min(score, 1.0)


# ===================================================================
# Internal helpers -- scoring for rank_standard_matches
# ===================================================================

def _score_subject_match(match: dict, subject: str) -> float:
    """Score subject match for ranking (0.0 to 1.0)."""
    if not subject:
        return 0.5
    source_subject = match.get("subject", "")
    return _fuzzy_subject_match(source_subject, subject)


def _score_grade_match(match: dict, grade: str, stage: str = "") -> float:
    """Score grade match for ranking (0.0 to 1.0)."""
    if not grade and not stage:
        return 0.5
    source_grade = _source_grade_values(match)
    return _grade_matches(source_grade, grade, stage)


def _score_keyword_overlap(match: dict, keywords: list, topic: str = "") -> float:
    """Score keyword overlap for ranking (0.0 to 1.0)."""
    source_keywords = match.get("keywords", [])
    search_text = " ".join(filter(None, [topic] + keywords))
    return _keyword_overlap(source_keywords, search_text)


def _score_source_level(match: dict) -> float:
    """Score source level for ranking (0.0 to 1.0)."""
    level = match.get("source_level", "")
    level_scores = {
        "A1": 1.0, "A2": 0.95, "A3": 0.9, "A4": 0.85, "A5": 0.8,
        "B1": 0.75, "B2": 0.7, "B3": 0.65, "B4": 0.6, "B5": 0.55,
        "C1": 0.35, "C2": 0.3, "C3": 0.25, "C4": 0.2, "C5": 0.15,
        "D1": 0.1, "D2": 0.05, "D3": 0.05, "D4": 0.05,
        "E1": 0.02, "E2": 0.02, "E3": 0.02,
    }
    return level_scores.get(level, 0.0)


# ===================================================================
# Internal helpers -- source record field mapping
# ===================================================================

def _level_to_credibility(source_level: str) -> str:
    """Map source level to credibility string per source-reliability-policy."""
    prefix = source_level[:1] if source_level else ""
    credibility_map = {
        "A": "highest",
        "B": "high",
        "C": "medium",
        "D": "low",
        "E": "uncertain",
    }
    # Sub-level refinement
    sub_map = {
        "A1": "highest", "A2": "highest", "A3": "highest",
        "A4": "high", "A5": "high",
        "B1": "high", "B2": "high", "B3": "high", "B4": "high",
        "B5": "medium_high",
        "C1": "medium", "C2": "medium", "C3": "medium",
        "C4": "medium", "C5": "medium",
        "D1": "medium_low", "D2": "low", "D3": "low", "D4": "low",
        "E1": "uncertain", "E2": "uncertain", "E3": "uncertain",
    }
    return sub_map.get(source_level, credibility_map.get(prefix, "uncertain"))


def _level_to_goal_basis(source_level: str) -> str:
    """Map source level to can_be_goal_basis string.

    A1-A5, B1-B4: "yes"
    B5: "limited"
    C1-C5: "limited"
    D1-D4: "no"
    E1-E3: "no"
    """
    sub_map = {
        "A1": "yes", "A2": "yes", "A3": "yes", "A4": "yes", "A5": "yes",
        "B1": "yes", "B2": "yes", "B3": "yes", "B4": "yes", "B5": "limited",
        "C1": "limited", "C2": "limited", "C3": "limited",
        "C4": "limited", "C5": "limited",
        "D1": "no", "D2": "no", "D3": "no", "D4": "no",
        "E1": "no", "E2": "no", "E3": "no",
    }
    return sub_map.get(source_level, "no")


def _category_to_scenes(source_category: str) -> list[str]:
    """Map source category to applicable scenes."""
    scene_map = {
        "official_authority": ["k12", "higher_ed", "vocational", "corporate", "general"],
        "professional_authority": ["k12", "higher_ed", "vocational", "corporate", "general"],
        "teacher_private": ["k12", "higher_ed", "vocational", "corporate"],
        "public": ["k12", "higher_ed", "vocational", "corporate", "general"],
        "ai_generated": ["k12", "higher_ed", "vocational", "corporate", "general"],
    }
    return scene_map.get(source_category, ["k12", "higher_ed", "vocational", "corporate", "general"])


def _level_to_copyright(source_level: str, source_category: str) -> str:
    """Determine copyright scope from source level and category."""
    prefix = source_level[:1] if source_level else ""
    if prefix == "A":
        return "official_public"
    elif prefix == "B":
        if source_category == "professional_authority":
            return "licensed"
        return "official_public"
    elif prefix == "C":
        return "teacher_private_use_only"
    elif prefix == "D":
        return "public_domain"
    elif prefix == "E":
        return "unknown"
    return "unknown"


def _level_to_use_scope(source_level: str, source_category: str) -> list[str]:
    """Determine use scope from source level and category."""
    prefix = source_level[:1] if source_level else ""
    if prefix in ("A",):
        return ["goal_basis", "content_reference", "assessment_generation", "strategy_design"]
    elif prefix in ("B",):
        if source_level in ("B1", "B2", "B3", "B4"):
            return ["goal_basis", "content_reference", "assessment_generation", "strategy_design"]
        # B5 -- academic works: limited
        return ["content_reference", "assessment_generation", "strategy_design"]
    elif prefix == "C":
        return ["content_reference", "assessment_generation", "private_reference_only"]
    elif prefix == "D":
        return ["content_reference", "not_for_public_export"]
    elif prefix == "E":
        return ["content_reference", "not_for_public_export"]
    return ["private_reference_only"]
