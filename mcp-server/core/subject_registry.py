"""Shared v3 subject and stage registry.

The public standards files contain the source metadata.  This module keeps
the runtime lookup rules in one place so the MCP server, CLI and host-facing
skills agree on the same nine-subject scope and stage-specific labels.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any


_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_CORE_DIR)
_REPO_ROOT = os.path.normpath(os.path.join(_PKG_ROOT, ".."))
REGISTRY_PATH = os.path.join(
    _REPO_ROOT, "data", "standards", "subject_registry_v3.json"
)

V3_EDUCATION_SCOPE = "k12_nine_subjects"
V3_REGISTRY_VERSION = "3.0.0"
V3_SUPPORTED_SUBJECT_IDS = {
    "chinese",
    "mathematics",
    "english",
    "physics",
    "chemistry",
    "biology",
    "history",
    "geography",
    "politics",
}

STAGE_ALIASES = {
    "小学": "primary",
    "小学阶段": "primary",
    "primary": "primary",
    "primary_school": "primary",
    "初中": "junior_secondary",
    "初中阶段": "junior_secondary",
    "junior": "junior_secondary",
    "junior_high": "junior_secondary",
    "junior_secondary": "junior_secondary",
    "高中": "senior_secondary",
    "普通高中": "senior_secondary",
    "普通高中阶段": "senior_secondary",
    "senior": "senior_secondary",
    "senior_high": "senior_secondary",
    "senior_secondary": "senior_secondary",
    "义务教育": "compulsory",
    "义务教育阶段": "compulsory",
    "compulsory": "compulsory",
    "k12": "k12",
}

STAGE_LABELS = {
    "primary": "小学",
    "junior_secondary": "初中",
    "senior_secondary": "普通高中",
}

_STAGE_RULE_KEYS = {
    "primary": "compulsory",
    "junior_secondary": "compulsory",
    "senior_secondary": "senior_secondary",
}


class SubjectRegistryError(ValueError):
    """Raised when the checked-in v3 registry cannot answer a lookup."""


@lru_cache(maxsize=1)
def load_subject_registry() -> dict[str, Any]:
    """Load and lightly validate the checked-in v3 subject registry."""
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as handle:
            registry = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise SubjectRegistryError(f"无法加载九学科注册表: {exc}") from exc

    if not isinstance(registry, dict) or not isinstance(registry.get("subjects"), list):
        raise SubjectRegistryError("九学科注册表缺少 subjects 列表")
    if registry.get("registry_version") != V3_REGISTRY_VERSION:
        raise SubjectRegistryError(
            f"九学科注册表版本不匹配: {registry.get('registry_version')}"
        )
    return registry


@lru_cache(maxsize=1)
def _subjects_by_id() -> dict[str, dict[str, Any]]:
    return {
        str(subject.get("subject_id")): subject
        for subject in load_subject_registry().get("subjects", [])
        if subject.get("subject_id")
    }


def normalize_stage(value: object, *, allow_group: bool = False) -> str:
    """Normalize Chinese or English stage labels to the v3 stage ids."""
    token = str(value or "").strip()
    normalized = STAGE_ALIASES.get(token, token)
    if normalized in {"primary", "junior_secondary", "senior_secondary"}:
        return normalized
    if allow_group and normalized in {"compulsory", "k12"}:
        return normalized
    if not token:
        return ""
    raise SubjectRegistryError(f"不支持的学段: {value}")


def _subject_aliases(subject: dict[str, Any]) -> set[str]:
    aliases = set()
    for value in [subject.get("subject_id"), subject.get("display_name")]:
        if value:
            aliases.add(str(value).strip().lower())
    aliases.update(
        str(value).strip().lower()
        for value in subject.get("terminology_aliases", [])
        if value
    )
    # Political science has different official public names at the two levels.
    if subject.get("subject_id") == "politics":
        aliases.update({"政治", "道德与法治", "思想政治"})
    return aliases


def resolve_subject(subject: object, stage: object = "") -> dict[str, Any] | None:
    """Resolve an id, display name or alias to a stage-aware subject record.

    ``None`` is returned for an unknown subject so callers can preserve the
    historical information-technology route and produce a useful scope error.
    """
    value = str(subject or "").strip().lower()
    if not value:
        return None
    normalized_stage = normalize_stage(stage, allow_group=True) if stage else ""
    if normalized_stage == "compulsory":
        normalized_stage = "junior_secondary"
    if normalized_stage == "k12":
        normalized_stage = ""

    default_stage_subjects = load_subject_registry().get("scope", {}).get("default_stage_subjects", {})
    for candidate in _subjects_by_id().values():
        subject_id = str(candidate.get("subject_id", ""))
        if value not in _subject_aliases(candidate):
            continue
        if normalized_stage in {"primary", "junior_secondary", "senior_secondary"}:
            allowed = default_stage_subjects.get(STAGE_LABELS[normalized_stage], [])
            if allowed and subject_id not in allowed:
                return None
        stage_key = _STAGE_RULE_KEYS.get(normalized_stage)
        stage_rule = candidate.get("stage_rules", {}).get(stage_key) if stage_key else None
        if stage_key and not stage_rule:
            return None
        resolved = dict(candidate)
        resolved["stage"] = normalized_stage or ""
        resolved["stage_rule"] = stage_rule or {}
        resolved["display_name"] = (
            stage_rule.get("display_name") if stage_rule else candidate.get("display_name", subject)
        )
        resolved["official_source_id"] = (
            stage_rule.get("source_id") if stage_rule else ""
        )
        resolved["source_stage"] = stage_key or ""
        return resolved
    return None


def get_subject(subject: object, stage: object = "") -> dict[str, Any]:
    """Resolve a subject or raise a stable, user-facing scope error."""
    resolved = resolve_subject(subject, stage)
    if not resolved:
        stage_label = STAGE_LABELS.get(normalize_stage(stage), str(stage or "")) if stage else ""
        suffix = f"（学段：{stage_label}）" if stage_label else ""
        raise SubjectRegistryError(f"当前 v3 不支持该学科{suffix}: {subject}")
    return resolved


def subject_options(stage: object = "") -> list[dict[str, Any]]:
    """Return public subject options for a stage."""
    normalized_stage = normalize_stage(stage) if stage else ""
    options = []
    for subject in load_subject_registry().get("subjects", []):
        resolved = resolve_subject(subject.get("subject_id"), normalized_stage)
        if not resolved:
            continue
        rule = resolved.get("stage_rule", {})
        options.append({
            "subject_id": resolved.get("subject_id", ""),
            "display_name": resolved.get("display_name", ""),
            "aliases": sorted(_subject_aliases(resolved)),
            "stage": normalized_stage,
            "stage_label": STAGE_LABELS.get(normalized_stage, ""),
            "grade_levels": list(rule.get("grade_levels", [])),
            "official_source_id": rule.get("source_id", ""),
        })
    return options


def supported_subject_ids() -> tuple[str, ...]:
    """Return stable subject ids in registry order."""
    return tuple(
        str(subject.get("subject_id"))
        for subject in load_subject_registry().get("subjects", [])
        if subject.get("subject_id")
    )


def is_v3_subject(subject: object, stage: object = "") -> bool:
    return resolve_subject(subject, stage) is not None


def stage_label(stage: object) -> str:
    normalized = normalize_stage(stage)
    return STAGE_LABELS[normalized]
