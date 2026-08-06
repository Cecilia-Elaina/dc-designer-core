"""Frozen v1 product boundary and project initialization helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


EDUCATION_SCOPE = "k12_info_technology"
FUTURE_SCOPES = ["higher_education", "general_instructional_design"]
SUPPORTED_STAGES = {"primary", "junior_secondary", "senior_secondary"}
SUPPORTED_SUBJECTS = {"信息科技", "信息技术"}
SUPPORTED_MODES = {"standard_fast", "collaborative"}
OFFICIAL_CORE_COMPETENCIES = [
    "信息意识",
    "计算思维",
    "数字化学习与创新",
    "信息社会责任",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_mode(value: Any) -> str:
    text = str(value or "").strip().lower()
    aliases = {
        "a": "standard_fast",
        "mode_a": "standard_fast",
        "fast": "standard_fast",
        "quick": "standard_fast",
        "课标约束快速设计": "standard_fast",
        "快速设计": "standard_fast",
        "b": "collaborative",
        "mode_b": "collaborative",
        "full": "collaborative",
        "协同设计": "collaborative",
        "完整协同设计": "collaborative",
    }
    return aliases.get(text, text if text in SUPPORTED_MODES else "standard_fast")


def normalize_subject(subject: Any, stage: str = "") -> str:
    text = str(subject or "").strip()
    if text in {"信息技术", "信息科技"}:
        return "信息技术" if stage == "senior_secondary" else "信息科技"
    return text


def normalize_stage(stage: Any, grade: Any = "") -> str:
    text = str(stage or "").strip().lower()
    grade_text = str(grade or "").strip().lower()
    if text in {"小学", "primary", "elementary"}:
        return "primary"
    if text in {"初中", "junior", "junior_secondary", "junior_high"}:
        return "junior_secondary"
    if text in {"高中", "senior", "senior_secondary", "senior_high"}:
        return "senior_secondary"
    # Check explicit high-school markers before the generic Chinese numeral
    # test; otherwise "高一" would be misclassified as primary because it
    # contains the character "一".
    if any(token in grade_text for token in ("高中", "高一", "高二", "高三", "十", "十一", "十二")):
        return "senior_secondary"
    if any(token in grade_text for token in ("初中", "初一", "初二", "初三", "七", "八", "九")):
        return "junior_secondary"
    if any(token in grade_text for token in ("小学", "一年级", "二年级", "三年级", "四年级", "五年级", "六年级")):
        return "primary"
    return ""


def validate_scope(request: dict) -> dict:
    """Validate the non-negotiable v1 scope before any generation."""
    request = request if isinstance(request, dict) else {}
    stage = normalize_stage(request.get("stage"), request.get("grade_level") or request.get("grade"))
    subject = normalize_subject(request.get("subject"), stage)
    user_type = str(request.get("user_type", "")).strip()
    errors: list[str] = []
    warnings: list[str] = []

    if subject not in SUPPORTED_SUBJECTS:
        errors.append("v1.0 仅支持中国 K12 信息科技/信息技术，不支持其他学科。")
    if stage not in SUPPORTED_STAGES:
        errors.append("请明确学段为小学、初中或普通高中。")
    if any(token in user_type for token in ("高校", "大学", "职教", "职业", "企业")):
        errors.append("当前版本仅支持 K12 信息科技/信息技术教师，尚未开放高校、职教或企业培训入口。")
    if request.get("education_scope") and request.get("education_scope") != EDUCATION_SCOPE:
        errors.append(f"education_scope 必须为 {EDUCATION_SCOPE}。")

    mode = normalize_mode(request.get("mode") or request.get("design_mode"))
    if request.get("mode") and mode not in SUPPORTED_MODES:
        errors.append("设计模式只能是 standard_fast（课标约束快速设计）或 collaborative（完整协同设计）。")
    if not request.get("textbook_version"):
        warnings.append("尚未提供教材版本，教材对应关系只能标记为待确认。")
    if not request.get("class_profile") and not request.get("teacher_inputs", {}).get("class_profile"):
        warnings.append("尚未提供班级共性学情，差异化策略只能先生成待确认草案。")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "education_scope": EDUCATION_SCOPE,
        "future_scopes": list(FUTURE_SCOPES),
        "stage": stage,
        "subject": subject,
        "mode": mode,
    }


def initialize_project(request: dict, *, project_id: str | None = None) -> dict:
    """Create the stable v1 project envelope used by every renderer."""
    check = validate_scope(request)
    stage = check["stage"]
    subject = check["subject"]
    mode = check["mode"]
    timestamp = now_iso()
    project_id = project_id or f"dc-{timestamp.replace(':', '').replace('+', '-')[:19]}"
    teacher_inputs = request.get("teacher_inputs", {}) if isinstance(request.get("teacher_inputs", {}), dict) else {}
    class_profile = request.get("class_profile") or teacher_inputs.get("class_profile") or {}

    return {
        "schema_version": "1.0.0",
        "project_id": project_id,
        "education_scope": EDUCATION_SCOPE,
        "future_scopes": list(FUTURE_SCOPES),
        "project": {
            "title": request.get("title") or request.get("topic") or "未命名信息科技教学设计",
            "topic": request.get("topic", ""),
            "stage": stage,
            "grade": request.get("grade_level") or request.get("grade", ""),
            "subject": subject,
            "textbook_version": request.get("textbook_version", ""),
            "unit": request.get("unit", ""),
            "periods": request.get("periods") or request.get("period") or "",
            "scenario": request.get("scenario", "新课设计"),
            "created_at": timestamp,
            "updated_at": timestamp,
        },
        "mode": {
            "id": mode,
            "label": "课标约束快速设计" if mode == "standard_fast" else "完整协同设计",
            "interaction": "auto_with_teacher_confirmations" if mode == "standard_fast" else "stage_by_stage_confirmation",
        },
        "curriculum_context": {
            "stage": stage,
            "subject": subject,
            "core_competencies": list(OFFICIAL_CORE_COMPETENCIES),
            "standard_version": "2022" if stage in {"primary", "junior_secondary"} else "2017/2020修订",
            "standard_status": "current_candidate",
        },
        "sources": [],
        "evidence_claims": [],
        "needs_analysis": {},
        "instructional_goal": {},
        "goal_analysis": {},
        "skill_graphs": {},
        "learner_analysis": {"class_profile": class_profile},
        "learning_context": request.get("learning_context") or teacher_inputs.get("learning_context") or {},
        "performance_context": request.get("performance_context") or teacher_inputs.get("performance_context") or {},
        "performance_objectives": [],
        "assessments": {},
        "instructional_sequence": [],
        "instructional_strategy": {},
        "instructional_materials": {},
        "formative_evaluation": {},
        "revision_plan": {},
        "alignment_report": {},
        "decision_log": [],
        "exports": {},
        "quality": {
            "scope_check": check,
            "draft_status": "draft",
            "evidence_status": "no_source",
        },
    }
