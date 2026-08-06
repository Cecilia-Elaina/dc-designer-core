"""
Source Normalizer -- normalize, merge, and clean source records.

Ensures all source records follow source.schema.json format,
deduplicates by source_id, resolves conflicts, and cleans
goal payloads of nested/redundant fields.
"""

import sys
import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_THIS_DIR)
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)


def normalize_source_record(source: dict) -> dict:
    """
    Normalize a source record to source.schema.json format.

    Handles field name differences between:
    - source_registry format (level, category, source_id, title)
    - K12 metadata format (source_level, source_category, standard_id)
    - teacher document format (document_id, document_type)
    - goal_engine embedded sources
    """
    if not isinstance(source, dict):
        return {}

    result = dict(source)

    # Normalize ID
    if "source_id" not in result:
        for key in ("standard_id", "document_id", "id"):
            if key in result and result[key]:
                result["source_id"] = result[key]
                break
    if "source_id" not in result:
        result["source_id"] = ""

    # Normalize name
    if "source_name" not in result:
        for key in ("title", "name", "document_name"):
            if key in result and result[key]:
                result["source_name"] = result[key]
                break
    if "source_name" not in result:
        result["source_name"] = ""

    # Normalize level
    if "source_level" not in result:
        for key in ("level", "standard_level"):
            if key in result and result[key]:
                result["source_level"] = result[key]
                break
    if "source_level" not in result:
        result["source_level"] = ""

    # Normalize category
    if "source_category" not in result:
        for key in ("category", "document_type"):
            if key in result and result[key]:
                raw = result[key]
                cat_map = {
                    "curriculum_standard": "official_authority",
                    "curriculum_plan": "official_authority",
                    "examination_outline": "official_authority",
                    "textbook": "professional_authority",
                    "teaching_reference": "professional_authority",
                    "lesson_plan": "teacher_private",
                    "teacher_private": "teacher_private",
                    "public": "public",
                    "ai_generated": "ai_generated",
                }
                result["source_category"] = cat_map.get(raw, raw)
                break
    if "source_category" not in result:
        result["source_category"] = ""

    # Normalize boolean fields
    for key in ("is_test_fixture", "is_sample_metadata_only", "verified_by_teacher"):
        if key in result:
            result[key] = bool(result[key])

    # Normalize lists
    for key in ("use_scope", "applicable_grades", "applicable_scenes", "specific_clauses"):
        if key in result and not isinstance(result[key], list):
            result[key] = []

    # Ensure required fields exist
    result.setdefault("credibility", "unknown")
    result.setdefault("can_be_goal_basis", "unknown")
    result.setdefault("retrieval_status", "unknown")
    result.setdefault("copyright_scope", "unknown")
    result.setdefault("use_scope", [])
    result.setdefault("applicable_scenes", [])
    result.setdefault("specific_clauses", [])
    result.setdefault("is_test_fixture", False)
    result.setdefault("is_sample_metadata_only", False)
    result.setdefault("verified_by_teacher", False)

    return result


def merge_source_records(sources: list) -> list:
    """
    Merge duplicate source records by source_id.

    Merge rules:
    - Keep highest credibility level
    - Merge clauses / citation_span / use_scope
    - Record conflict_warnings if same source_id has conflicting fields
    - Compute normalized_can_be_goal_basis
    """
    if not sources:
        return []

    # Group by source_id
    groups: dict[str, list[dict]] = {}
    for src in sources:
        normalized = normalize_source_record(src)
        sid = normalized.get("source_id", "") or f"_unknown_{id(src)}"
        groups.setdefault(sid, []).append(normalized)

    # Credibility ranking
    cred_rank = {
        "highest": 5, "high": 4, "medium_high": 3,
        "medium": 2, "medium_low": 1, "low": 0, "uncertain": -1, "unknown": -1,
    }

    # Goal basis ranking
    basis_rank = {"yes": 3, "limited": 2, "test_only": 1, "no": 0, "unknown": -1}

    merged = []
    for sid, group in groups.items():
        if len(group) == 1:
            record = group[0]
            record["normalized_can_be_goal_basis"] = record.get("can_be_goal_basis", "unknown")
            merged.append(record)
            continue

        # Multiple records for same source_id
        conflict_warnings = []

        # Pick best by credibility
        best = max(group, key=lambda s: cred_rank.get(s.get("credibility", "unknown"), -1))

        # Merge clauses
        all_clauses = []
        for s in group:
            all_clauses.extend(s.get("specific_clauses", []))
        # Deduplicate clauses by clause_id
        seen_clause_ids = set()
        unique_clauses = []
        for c in all_clauses:
            cid = c.get("clause_id", "")
            if cid and cid not in seen_clause_ids:
                seen_clause_ids.add(cid)
                unique_clauses.append(c)
            elif not cid:
                unique_clauses.append(c)
        best["specific_clauses"] = unique_clauses

        # Merge use_scope
        all_use_scope = set()
        for s in group:
            all_use_scope.update(s.get("use_scope", []))
        best["use_scope"] = sorted(all_use_scope)

        # Check for goal_basis conflicts
        goal_bases = set(s.get("can_be_goal_basis", "unknown") for s in group)
        if "yes" in goal_bases and "no" in goal_bases:
            conflict_warnings.append(
                f"来源 {sid} 存在 can_be_goal_basis 冲突: {goal_bases}"
            )
            best["normalized_can_be_goal_basis"] = "limited"
        elif "yes" in goal_bases:
            best["normalized_can_be_goal_basis"] = "yes"
        elif "limited" in goal_bases:
            best["normalized_can_be_goal_basis"] = "limited"
        elif "test_only" in goal_bases:
            best["normalized_can_be_goal_basis"] = "test_only"
        else:
            best["normalized_can_be_goal_basis"] = best.get("can_be_goal_basis", "unknown")

        # Check for test fixture conflict
        has_test = any(s.get("is_test_fixture", False) for s in group)
        has_real = any(not s.get("is_test_fixture", False) for s in group)
        if has_test and has_real:
            conflict_warnings.append(
                f"来源 {sid} 同时包含测试夹具和真实来源记录"
            )

        if conflict_warnings:
            best.setdefault("conflict_warnings", []).extend(conflict_warnings)

        merged.append(best)

    return merged


def remove_nested_goal_payload(goal: dict) -> dict:
    """
    Remove nested/redundant fields from goal dict.

    Cleans:
    - Nested 'goal' field inside goal
    - Duplicate 'status' fields
    - Ensures consistent field names
    """
    if not isinstance(goal, dict):
        return goal

    result = dict(goal)

    # Remove nested goal
    if "goal" in result and isinstance(result["goal"], dict):
        nested = result["goal"]
        # Merge nested fields into parent if parent doesn't have them
        for key, val in nested.items():
            if key not in result or result[key] is None:
                result[key] = val
        del result["goal"]

    # Ensure consistent status fields
    if "status" in result and "verification_status" not in result:
        # Map old status to new verification_status
        status_map = {
            "pass": "verified",
            "passed": "verified",
            "warning": "draft_pending_verification",
            "fail": "draft_unverified",
            "failed": "draft_unverified",
            "draft_pending_verification": "draft_pending_verification",
            "draft_unverified": "draft_unverified",
            "verified": "verified",
        }
        result["verification_status"] = status_map.get(result["status"], result["status"])

    return result


def clean_project_sources(project: dict) -> dict:
    """
    Clean and normalize all sources in a project.

    - Normalize each source record
    - Merge duplicates by source_id
    - Remove nested goal payload
    - Ensure consistent entry_behaviors/entry_behaviours
    """
    if not isinstance(project, dict):
        return project

    result = dict(project)

    # Clean goal
    if "goal" in result:
        result["goal"] = remove_nested_goal_payload(result["goal"])

    # Normalize and merge sources
    if "sources" in result:
        result["sources"] = merge_source_records(result["sources"])

    # Fix entry_behaviours -> entry_behaviors
    sg = result.get("skill_graph", {})
    if "entry_behaviours" in sg and "entry_behaviors" not in sg:
        sg["entry_behaviors"] = sg.pop("entry_behaviours")
    elif "entry_behaviours" in sg and "entry_behaviors" in sg:
        # Keep entry_behaviors, remove entry_behaviours
        sg.pop("entry_behaviours", None)

    # Also fix in nodes
    for node in sg.get("nodes", []):
        if node.get("node_type") == "entry_behavior":
            if "entry_behaviours" in node:
                node.pop("entry_behaviours", None)

    return result
