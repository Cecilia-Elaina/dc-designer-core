"""Local, consent-gated teacher memory for the v1 plugin."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from core.runtime_paths import ensure_workspace


_ALLOWED_PROFILE_FIELDS = {
    "display_name", "subjects", "grade_levels", "teaching_style", "preferences",
    "school_type", "district", "textbook_versions", "class_common_difficulties",
    "device_preferences", "language",
}
_PII_KEYS = {
    "student_name", "student_names", "student_id", "student_ids", "id_card",
    "phone", "家庭住址", "学生姓名", "学号", "身份证号",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _profile_path(teacher_id: str) -> Path:
    dirs = ensure_workspace()
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(teacher_id or "teacher"))
    return dirs["profile"] / f"{safe}.json"


def _load_profile(teacher_id: str) -> dict:
    path = _profile_path(teacher_id)
    if not path.exists():
        return {"teacher_id": teacher_id, "preferences": {}, "created_at": _now()}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"teacher_id": teacher_id, "preferences": {}, "created_at": _now()}


def _save_profile(profile: dict) -> None:
    _profile_path(profile["teacher_id"]).write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


def read_teacher_profile(teacher_id: str) -> dict:
    if not teacher_id or not isinstance(teacher_id, str):
        raise ValueError("teacher_id must be a non-empty string")
    return _load_profile(teacher_id)


def write_teacher_profile(teacher_id: str, data: dict, consent_confirmed: bool) -> dict:
    if not consent_confirmed:
        raise PermissionError("写入教师长期记忆前必须明确确认")
    if not teacher_id or not isinstance(teacher_id, str) or not isinstance(data, dict):
        raise ValueError("teacher_id 或 data 无效")
    compliance = check_privacy_compliance(data)
    if not compliance["passed"]:
        raise ValueError("资料未通过隐私检查: " + "; ".join(compliance["issues"]))
    profile = _load_profile(teacher_id)
    updated = []
    for key, value in data.items():
        if key in _ALLOWED_PROFILE_FIELDS:
            profile[key] = value
            updated.append(key)
    profile["teacher_id"] = teacher_id
    profile["updated_at"] = _now()
    profile["consent_recorded"] = True
    _save_profile(profile)
    return {"teacher_id": teacher_id, "updated_fields": updated, "updated_at": profile["updated_at"], "consent_recorded": True}


def delete_teacher_data(teacher_id: str, data_type: str) -> bool:
    allowed = {"profile", "knowledge", "projects", "preferences", "all"}
    if data_type not in allowed:
        raise ValueError(f"data_type must be one of {sorted(allowed)}")
    deleted = False
    if data_type in {"profile", "preferences", "all"}:
        path = _profile_path(teacher_id)
        if path.exists():
            if data_type == "preferences":
                profile = _load_profile(teacher_id)
                if profile.get("preferences"):
                    profile["preferences"] = {}
                    _save_profile(profile)
                    deleted = True
            else:
                path.unlink(missing_ok=True)
                deleted = True
    dirs = ensure_workspace()
    if data_type in {"projects", "all"}:
        for path in dirs["projects"].glob(f"*{teacher_id}*.json"):
            path.unlink(missing_ok=True)
            deleted = True
    if data_type in {"knowledge", "all"}:
        path = dirs["indexes"] / "private_knowledge.json"
        if path.exists():
            path.unlink()
            deleted = True
    return deleted


def export_teacher_data(teacher_id: str) -> dict:
    profile = _load_profile(teacher_id)
    dirs = ensure_workspace()
    knowledge = []
    index_path = dirs["indexes"] / "private_knowledge.json"
    if index_path.exists():
        try:
            knowledge = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            knowledge = []
    projects = []
    for path in dirs["projects"].glob(f"*{teacher_id}*.json"):
        try:
            projects.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return {
        "teacher_id": teacher_id,
        "profile": profile,
        "knowledge_entries": knowledge,
        "historical_projects": projects,
        "preferences": profile.get("preferences", {}),
        "exported_at": _now(),
        "data_version": "1.0.0",
    }


def list_historical_projects(teacher_id: str) -> List[dict]:
    bundle = export_teacher_data(teacher_id)
    summaries = []
    for project in bundle["historical_projects"]:
        metadata = project.get("project", project.get("metadata", {}))
        summaries.append({
            "project_id": project.get("project_id", ""),
            "title": metadata.get("title", metadata.get("project_name", "")),
            "subject": metadata.get("subject", ""),
            "grade_level": metadata.get("grade", metadata.get("grade_level", "")),
            "created_at": metadata.get("created_at", ""),
            "last_modified_at": metadata.get("updated_at", ""),
            "status": project.get("quality", {}).get("draft_status", "draft"),
            "design_sources": [source.get("source_id", "") for source in project.get("sources", [])],
        })
    return sorted(summaries, key=lambda item: item.get("last_modified_at", ""), reverse=True)


def check_privacy_compliance(data: dict) -> dict:
    if not isinstance(data, dict):
        raise TypeError("data must be a dict")
    pii_detected: list[str] = []

    def visit(value: object, path: str = "") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key)
                if key_text in _PII_KEYS or any(token in key_text.lower() for token in ("student_name", "student_id", "id_card")):
                    pii_detected.append(path + key_text)
                visit(item, path + key_text + ".")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, path + f"{index}.")

    visit(data)
    issues = [f"发现禁止保存的学生身份字段: {', '.join(pii_detected)}"] if pii_detected else []
    consent_valid = bool(data.get("consent_confirmed", data.get("consent_recorded", True)))
    if data.get("requires_consent") and not consent_valid:
        issues.append("需要教师明确确认后才能保存")
    return {
        "passed": not issues,
        "issues": issues,
        "pii_detected": pii_detected,
        "consent_valid": consent_valid,
        "recommendations": ["只保存匿名聚合的班级共性困难，不保存学生姓名、学号、个人成绩。"] if issues else [],
    }
