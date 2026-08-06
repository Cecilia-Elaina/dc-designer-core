"""Shared resumable design-session service.

Codex Skills, the local web UI, and compatibility callers use this module for
session persistence. The instructional engines remain the source of generated
content; this layer owns checkpoints, decisions, versions, and recovery.
"""

from __future__ import annotations

import copy
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.runtime_paths import ensure_workspace


STAGES = [
    ("scope", "范围、学段和课题确认", None),
    ("sources", "课程标准和来源确认", "curriculum_standard"),
    ("goal", "评价需求与教学目的", "instructional_goal"),
    ("analysis", "教学分析、技能图和入门技能", "entry_skills"),
    ("learner_context", "学习者与学习环境", "learner_context"),
    ("objectives_assessment", "绩效目标和评价", None),
    ("strategy_materials", "教学策略、流程和材料", "instructional_strategy"),
    ("quality_export", "一致性检查、视觉检查和导出", None),
]

CONFIRMATION_STAGE = {
    "curriculum_standard": "sources",
    "textbook_unit": "sources",
    "instructional_goal": "goal",
    "entry_skills": "analysis",
    "learner_context": "learner_context",
    "periods_equipment": "strategy_materials",
    "instructional_strategy": "strategy_materials",
}

ALLOWED_DECISION_FIELDS = {
    "goal_behavior",
    "goal_condition",
    "goal_criterion",
    "textbook_version",
    "unit",
    "periods",
    "equipment",
    "topic",
    "title",
    "class_profile",
    "learning_context",
    "performance_context",
    "application_context",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(value or "session"))[:80]


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)
    return str(path)


def _session_path(session_id: str, workspace: str | None) -> Path:
    return ensure_workspace(workspace)["projects"] / _safe_name(session_id) / "session.json"


def _session_dir(session_id: str, workspace: str | None) -> Path:
    return _session_path(session_id, workspace).parent


def _stage_for_result(result: dict) -> tuple[str, str]:
    pending = result.get("required_confirmations", []) or []
    for item in pending:
        if item.get("status") != "confirmed":
            stage_id = CONFIRMATION_STAGE.get(item.get("confirmation_id"), "quality_export")
            label = next((label for sid, label, _ in STAGES if sid == stage_id), "当前设计阶段")
            return stage_id, label
    if not result.get("can_export_final", False):
        return "quality_export", "一致性检查、视觉检查和导出"
    return "quality_export", "一致性检查、视觉检查和导出"


def _export_result(result: dict | None) -> dict:
    payload = result if isinstance(result, dict) else {}
    for key in ("export_result", "export", "exports"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _session_view(session: dict, result: dict | None = None) -> dict:
    result = result or {}
    stage_id, stage_label = _stage_for_result(result or session.get("last_result", {}))
    pending = (result or session.get("last_result", {})).get("required_confirmations", session.get("pending_confirmations", []))
    return {
        "session_id": session.get("session_id", ""),
        "project_id": session.get("project_id", ""),
        "project_title": session.get("project_title", ""),
        "session_status": session.get("session_status", "collecting"),
        "current_stage": stage_id,
        "current_stage_label": stage_label,
        "completed_stages": session.get("completed_stages", []),
        "pending_confirmations": pending or [],
        "confirmed_decisions": session.get("confirmed_decisions", []),
        "decision_log": session.get("decision_log", []),
        "assumptions": session.get("assumptions", []),
        "unresolved_items": session.get("unresolved_items", []),
        "project_version": session.get("project_version", 0),
        "source_snapshot": session.get("source_snapshot", {}),
        "last_error": session.get("last_error", ""),
        "next_action": (result or session.get("last_result", {})).get("progress", {}).get("next_action", "继续确认当前阶段"),
        "can_export_final": bool((result or session.get("last_result", {})).get("can_export_final", False)),
        "final_blocking_reasons": (result or session.get("last_result", {})).get("final_blocking_reasons", []),
        "export_result": _export_result(result or session.get("last_result", {})),
        "warnings": (result or session.get("last_result", {})).get("warnings", []),
        "created_at": session.get("created_at", ""),
        "updated_at": session.get("updated_at", ""),
    }


def _merge_decision(request: dict, decision: dict) -> tuple[dict, dict]:
    merged = copy.deepcopy(request)
    field = str(decision.get("field_path", "")).strip()
    value = decision.get("value")
    if field not in ALLOWED_DECISION_FIELDS:
        return merged, {"status": "rejected", "reason": "不允许直接修改该内部字段。", "field_path": field}
    merged[field] = value
    if field == "class_profile" and not isinstance(value, dict):
        return request, {"status": "rejected", "reason": "class_profile 必须是匿名的班级共性信息对象。", "field_path": field}
    return merged, {"status": "accepted", "field_path": field, "value": value}


def _apply_confirmations(request: dict, existing: dict, updates: list[dict]) -> tuple[dict, list[dict], list[dict]]:
    merged = copy.deepcopy(request)
    confirmations = dict(existing or {})
    accepted: list[dict] = []
    rejected: list[dict] = []
    for update in updates or []:
        confirmation_id = str(update.get("confirmation_id", "")).strip()
        if confirmation_id:
            confirmations[confirmation_id] = bool(update.get("confirmed", update.get("value", True)))
            accepted.append({"status": "accepted", "confirmation_id": confirmation_id, "confirmed": confirmations[confirmation_id]})
        if update.get("field_path"):
            merged, result = _merge_decision(merged, update)
            (accepted if result.get("status") == "accepted" else rejected).append(result)
    merged["confirmations"] = confirmations
    return merged, accepted, rejected


def _copy_active_project(result: dict, session_dir: Path, version: int) -> str:
    project = result.get("project", {})
    version_dir = session_dir / "versions" / f"v{version:03d}"
    version_dir.mkdir(parents=True, exist_ok=True)
    project_path = version_dir / "project.json"
    _write_json(project_path, project)
    return str(project_path)


def _record_session(session: dict, result: dict, workspace: str | None) -> dict:
    session_dir = _session_dir(session["session_id"], workspace)
    session["updated_at"] = _now()
    project = result.get("project", {}) if isinstance(result.get("project", {}), dict) else {}
    nested_project = project.get("project", {}) if isinstance(project.get("project", {}), dict) else {}
    session["project_title"] = nested_project.get("title") or project.get("title") or session.get("project_title", "")
    session["last_result"] = {
        "status": result.get("status"),
        "can_export_final": result.get("can_export_final", False),
        "final_blocking_reasons": result.get("final_blocking_reasons", []),
        "required_confirmations": result.get("required_confirmations", []),
        "progress": result.get("progress", {}),
        "warnings": result.get("warnings", []),
        "export_result": _export_result(result),
    }
    session["pending_confirmations"] = result.get("required_confirmations", [])
    session["source_snapshot"] = result.get("project", {}).get("source_snapshot", {})
    session["session_status"] = (
        "final_ready" if result.get("can_export_final") else
        "blocked" if result.get("status") in {"blocked", "unsupported_scope", "error"} else
        "awaiting_confirmation" if result.get("required_confirmations") else
        "completed_with_warnings"
    )
    _write_json(session_dir / "session.json", session)
    return _session_view(session, result)


def create_session(request: dict, output_dir: str | None = None, workspace: str | None = None) -> dict:
    from tools.v1_orchestrator import run_v1_design

    session_id = f"session-{uuid.uuid4().hex[:12]}"
    session_dir = _session_dir(session_id, workspace)
    session = {
        "session_id": session_id,
        "project_id": "",
        "project_title": "",
        "request": copy.deepcopy(request or {}),
        "created_at": _now(),
        "updated_at": _now(),
        "project_version": 1,
        "completed_stages": [],
        "confirmed_decisions": [],
        "decision_log": [],
        "assumptions": [],
        "unresolved_items": [],
        "last_error": "",
    }
    result = run_v1_design(request or {}, output_dir or str(session_dir / "exports" / "v001"), workspace)
    session["project_id"] = result.get("project", {}).get("project_id", session_id)
    session["project_version"] = 1
    session["decision_log"].append({"decision_id": "SESSION-001", "type": "session_created", "timestamp": _now()})
    _copy_active_project(result, session_dir, 1)
    view = _record_session(session, result, workspace)
    return {**result, "session": view}


def load_session(session_id: str, workspace: str | None = None) -> dict | None:
    path = _session_path(session_id, workspace)
    payload = _read_json(path, None)
    return payload if isinstance(payload, dict) else None


def get_session_view(session_id: str, workspace: str | None = None) -> dict | None:
    session = load_session(session_id, workspace)
    if not session:
        return None
    return _session_view(session)


def list_sessions(workspace: str | None = None) -> list[dict]:
    projects = ensure_workspace(workspace)["projects"]
    rows = []
    for path in projects.glob("*/session.json"):
        session = _read_json(path, {})
        if isinstance(session, dict) and session.get("session_id"):
            rows.append(_session_view(session))
    return sorted(rows, key=lambda item: item.get("updated_at", ""), reverse=True)


def delete_session(session_id: str, workspace: str | None = None) -> dict:
    """Delete one locally persisted design session and its generated files."""
    session_dir = _session_dir(session_id, workspace)
    if not session_dir.is_dir():
        return {"status": "not_found", "session_id": session_id}
    root = ensure_workspace(workspace)["projects"].resolve()
    target = session_dir.resolve()
    if root not in target.parents:
        return {"status": "blocked", "session_id": session_id, "error": "只能删除本地工作区内的设计项目"}
    shutil.rmtree(target)
    return {"status": "deleted", "session_id": session_id}


def compare_session_versions(session_id: str, from_version: int, to_version: int, workspace: str | None = None) -> dict:
    """Compare two saved project checkpoints without exposing student data."""
    session_dir = _session_dir(session_id, workspace)
    old_path = session_dir / "versions" / f"v{int(from_version):03d}" / "project.json"
    new_path = session_dir / "versions" / f"v{int(to_version):03d}" / "project.json"
    old = _read_json(old_path, None)
    new = _read_json(new_path, None)
    if not isinstance(old, dict) or not isinstance(new, dict):
        return {"status": "not_found", "session_id": session_id, "from_version": from_version, "to_version": to_version}
    changed_sections = []
    all_keys = sorted(set(old) | set(new))
    for key in all_keys:
        if old.get(key) != new.get(key):
            changed_sections.append({"section": key, "from": old.get(key), "to": new.get(key)})
    return {
        "status": "ok",
        "session_id": session_id,
        "from_version": int(from_version),
        "to_version": int(to_version),
        "changed_section_count": len(changed_sections),
        "changed_sections": changed_sections,
    }


def copy_session(session_id: str, workspace: str | None = None) -> dict:
    """Create a new branch from the current request, preserving local-only storage."""
    session = load_session(session_id, workspace)
    if not session:
        return {"status": "not_found", "session_id": session_id}
    copied = create_session(session.get("request", {}), workspace=workspace)
    copied["copied_from_session_id"] = session_id
    return copied


def resume_session(session_id: str, *, decision_updates: list[dict] | None = None, workspace: str | None = None, output_dir: str | None = None) -> dict:
    from tools.v1_orchestrator import run_v1_design

    session = load_session(session_id, workspace)
    if not session:
        return {"status": "error", "errors": [f"找不到设计会话: {session_id}"], "session_id": session_id}
    request, accepted, rejected = _apply_confirmations(
        session.get("request", {}),
        session.get("request", {}).get("confirmations", {}),
        decision_updates or [],
    )
    session["request"] = request
    session["decision_log"].append({
        "decision_id": f"SESSION-{len(session.get('decision_log', [])) + 1:03d}",
        "type": "teacher_updates",
        "accepted": accepted,
        "rejected": rejected,
        "timestamp": _now(),
    })
    next_version = int(session.get("project_version", 0)) + 1
    session_dir = _session_dir(session_id, workspace)
    destination = output_dir or str(session_dir / "exports" / f"v{next_version:03d}")
    result = run_v1_design(request, destination, workspace)
    session["project_version"] = next_version
    _copy_active_project(result, session_dir, next_version)
    view = _record_session(session, result, workspace)
    return {**result, "session": view, "decision_update_results": {"accepted": accepted, "rejected": rejected}}


def rollback_session(session_id: str, version: int, workspace: str | None = None) -> dict:
    session = load_session(session_id, workspace)
    if not session:
        return {"status": "error", "errors": [f"找不到设计会话: {session_id}"], "session_id": session_id}
    version_path = _session_dir(session_id, workspace) / "versions" / f"v{int(version):03d}" / "project.json"
    project = _read_json(version_path, None)
    if not isinstance(project, dict):
        return {"status": "error", "errors": [f"找不到项目版本: v{version}"], "session_id": session_id}
    session["project_version"] = int(version)
    session["decision_log"].append({"decision_id": f"SESSION-{len(session.get('decision_log', [])) + 1:03d}", "type": "rollback", "version": int(version), "timestamp": _now()})
    session["last_result"] = {"status": "completed_with_warnings", "can_export_final": False, "final_blocking_reasons": ["回退后需要重新确认受影响的教学决策"], "required_confirmations": project.get("required_confirmations", []), "progress": {"next_action": "重新确认回退版本的受影响内容"}, "warnings": [], "export_result": project.get("exports", {})}
    session["session_status"] = "awaiting_confirmation"
    session["updated_at"] = _now()
    _write_json(_session_path(session_id, workspace), session)
    return {"status": "rolled_back", "project": project, "session": _session_view(session)}


def session_health(workspace: str | None = None) -> dict:
    dirs = ensure_workspace(workspace)
    return {"status": "ok", "workspace": str(dirs["root"]), "session_count": len(list(dirs["projects"].glob("*/session.json")))}
