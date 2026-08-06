"""
Agent Session - Phase 7
Simulates a real agent session using dc-designer-core tools.

Orchestrates the full Dick & Carey pipeline based on the request mode:
  - dc-design:  Create a new instructional design from scratch
  - dc-review:  Audit an existing design for alignment/quality issues
  - dc-revise:  Apply feedback to an existing design and re-verify

All functions call the real deterministic engines (goal_engine, skill_graph,
objective_engine, assessment_engine, strategy_engine, materials_engine,
alignment_checker, standards_search).  No AI calls, no stubs.
"""

import sys
import os
import json
import copy
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Path setup -- mirrors pipeline.py
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_THIS_DIR)
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

_REPO_ROOT = os.path.normpath(os.path.join(_PKG_ROOT, ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ======================================================================
# Public API
# ======================================================================

def run_agent_session(request: dict, output_dir: str = "exports/phase7") -> dict:
    """
    Run a complete agent session based on the request mode.

    Parameters
    ----------
    request : dict
        Must contain a ``mode`` key.  Additional keys depend on mode:
        - ``"dc-design"``: user_type, scenario, subject, grade_level, topic,
          and optionally teacher_inputs.
        - ``"dc-review"``: existing_design_project_path (path to JSON).
        - ``"dc-revise"``: existing_design_project_path and
          feedback_or_revision_data.
    output_dir : str
        Directory for exported artefacts.

    Returns
    -------
    dict with at least:
        - mode (str)
        - status (str): "completed" | "completed_with_warnings" | "error"
        - tool_call_plan (list[dict]): ordered record of every engine invoked
        - warnings (list[str])
        - required_confirmations (list[dict])  (dc-design)
        - findings (list[dict])                (dc-review)
        - revision_log (list[dict])            (dc-revise)
    """
    mode = request.get("mode", "dc-design")

    if mode == "dc-design":
        return _run_dc_design(request, output_dir)
    elif mode == "dc-review":
        return _run_dc_review(request, output_dir)
    elif mode == "dc-revise":
        return _run_dc_revise(request, output_dir)
    else:
        return {
            "mode": mode,
            "status": "error",
            "tool_call_plan": [],
            "warnings": [f"Unknown mode: {mode}"],
            "required_confirmations": [],
            "findings": [],
            "revision_log": [],
        }


# ======================================================================
# dc-design mode
# ======================================================================

def _run_dc_design(request: dict, output_dir: str) -> dict:
    """
    Full design pipeline: context analysis -> goal -> skill graph ->
    objectives -> assessment -> learner context -> strategy -> materials
    -> alignment -> export.

    Returns structured result with tool_call_plan and required_confirmations.
    """
    tool_call_plan: list[dict] = []
    warnings: list[str] = []
    required_confirmations: list[dict] = []

    subject = request.get("subject", "")
    grade_level = request.get("grade_level", "")
    topic = request.get("topic", "")
    user_type = request.get("user_type", "")
    scenario = request.get("scenario", "新课设计")
    teacher_inputs = request.get("teacher_inputs", {})

    # ------------------------------------------------------------------
    # 1. Validate inputs
    # ------------------------------------------------------------------
    missing = []
    for field in ("subject", "grade_level", "topic"):
        if not request.get(field):
            missing.append(field)
    if missing:
        return {
            "mode": "dc-design",
            "status": "error",
            "tool_call_plan": [],
            "warnings": [f"Missing required fields: {', '.join(missing)}"],
            "required_confirmations": [],
            "findings": [],
            "revision_log": [],
        }

    _record_tool_call(tool_call_plan, "input_validation", "validate_inputs",
                      inputs={"subject": subject, "grade_level": grade_level,
                              "topic": topic})

    # ------------------------------------------------------------------
    # 2. Standards search (K12)
    # ------------------------------------------------------------------
    from tools.standards_search import search_standards, build_source_record_from_standard

    is_k12 = any(kw in user_type for kw in ("K12", "中小学", "小学", "初中", "高中", "教师"))
    std_result = None
    sources: list[dict] = []
    if is_k12:
        # Derive stage from grade
        stage = _grade_to_stage(grade_level)
        std_result = search_standards({
            "stage": stage,
            "grade": grade_level,
            "subject": subject,
            "topic": topic,
            "scene_type": "k12",
        })
        _record_tool_call(tool_call_plan, "standards_search", "search_standards",
                          inputs={"stage": stage, "grade": grade_level,
                                  "subject": subject, "topic": topic},
                          outputs={"status": std_result.get("status"),
                                   "match_count": len(std_result.get("matches", []))})

        # Build source records from found standards
        for match in std_result.get("matches", []):
            src = build_source_record_from_standard(match)
            sources.append(src)

        if std_result.get("status") == "not_found":
            warnings.append(
                "No matching standards found locally. "
                "Design will proceed as unverified draft."
            )

    # ------------------------------------------------------------------
    # 2b. Process source_documents (teacher-provided materials)
    # ------------------------------------------------------------------
    source_documents = request.get("source_documents", [])
    if source_documents:
        for idx, doc_ref in enumerate(source_documents):
            if isinstance(doc_ref, str) and doc_ref.strip():
                teacher_source = {
                    "source_id": f"teacher_doc_{idx + 1}",
                    "source_name": doc_ref[:60],
                    "source_description": doc_ref,
                    "source_level": "C1",
                    "source_category": "teacher_private",
                    "credibility": "medium",
                    "can_be_goal_basis": "limited",
                    "retrieval_status": "user_provided",
                    "copyright_scope": "teacher_private_use_only",
                    "use_scope": ["private_reference_only"],
                    "applicable_scenes": ["k12"],
                    "is_test_fixture": False,
                    "file_reference": doc_ref,
                    "fallback_required": True,
                    "specific_clauses": [],
                    "verified_by_teacher": False,
                }
                sources.append(teacher_source)
        _record_tool_call(tool_call_plan, "knowledge_ingest", "ingest_teacher_documents",
                          inputs={"document_count": len(source_documents)},
                          outputs={"sources_added": len(source_documents)})

    # ------------------------------------------------------------------
    # 3. Goal engine
    # ------------------------------------------------------------------
    from tools.goal_engine import (
        analyze_instructional_context,
        validate_instructional_goal,
    )

    ctx_input = {
        "user_type": user_type,
        "scene_type": "k12" if is_k12 else "corporate",
        "subject": subject,
        "grade_level": grade_level,
        "has_official_standards": std_result is not None and std_result.get("status") == "found",
    }
    ctx_result = analyze_instructional_context(ctx_input)
    _record_tool_call(tool_call_plan, "goal_engine", "analyze_instructional_context",
                      inputs=ctx_input,
                      outputs={"scene_type": ctx_result.get("scene_type"),
                               "required_sources": len(ctx_result.get("required_sources", []))})

    # Build goal from topic
    goal = {
        "learner": f"{grade_level}学生" if grade_level else "学习者",
        "behavior": _derive_behavior(topic),
        "context": f"在{subject}课堂上" if subject else "在课堂教学情境中",
        "tools": teacher_inputs.get("available_media", ["黑板", "投影"])[0]
                 if teacher_inputs.get("available_media") else "纸笔",
        "scene_type": ctx_result.get("scene_type", "k12"),
        "sources": sources,
    }
    goal["full_statement"] = (
        f"{goal['learner']}在{goal['context'].replace('在', '').replace('上', '')}上，"
        f"{goal['behavior']}，使用{goal['tools']}"
    )

    goal_validation = validate_instructional_goal(goal, sources)
    _record_tool_call(tool_call_plan, "goal_engine", "validate_instructional_goal",
                      inputs={"goal_learner": goal["learner"], "source_count": len(sources)},
                      outputs={"status": goal_validation.get("status"),
                               "requires_confirmation": goal_validation.get(
                                   "requires_teacher_confirmation", False)})

    # Merge validation metadata back into the goal so it appears in exports
    goal["source_status"] = goal_validation.get("source_status", "unknown")
    goal["verification_status"] = goal_validation.get("verification_status", "unverified")
    goal["is_verified"] = goal_validation.get("is_verified", False)

    # Collect confirmations
    if goal_validation.get("requires_teacher_confirmation"):
        required_confirmations.append({
            "component": "goal",
            "reason": "K12 source verification pending",
            "verification_status": goal_validation.get("verification_status", "unknown"),
            "issues": goal_validation.get("issues", []),
            "recommendations": goal_validation.get("recommendations", []),
        })

    # ------------------------------------------------------------------
    # 4. Skill graph
    # ------------------------------------------------------------------
    from tools.skill_graph import (
        classify_goal_type,
        generate_goal_steps,
        analyze_subordinate_skills,
        identify_entry_behaviors,
        build_skill_graph,
    )

    goal_with_sources = {**goal, "sources": sources}
    classification = classify_goal_type(goal_with_sources)
    _record_tool_call(tool_call_plan, "skill_graph", "classify_goal_type",
                      inputs={"goal_behavior": goal["behavior"]},
                      outputs={"goal_type": classification.get("goal_type")})

    steps_result = generate_goal_steps(goal_with_sources)
    _record_tool_call(tool_call_plan, "skill_graph", "generate_goal_steps",
                      inputs={"goal_behavior": goal["behavior"]},
                      outputs={"step_count": len(steps_result.get("steps", []))})

    subskills_result = analyze_subordinate_skills(steps_result.get("steps", []))
    _record_tool_call(tool_call_plan, "skill_graph", "analyze_subordinate_skills",
                      inputs={"step_count": len(steps_result.get("steps", []))},
                      outputs={"subskill_count": len(subskills_result.get("subordinate_skills", []))})

    # Build learner context for entry behaviors
    learner_input = _build_learner_input(request)
    entry_result = identify_entry_behaviors(
        subskills_result.get("subordinate_skills", []),
        learner_input,
    )
    ek = "entry_behaviors" if "entry_behaviors" in entry_result else "entry_behaviours"
    _record_tool_call(tool_call_plan, "skill_graph", "identify_entry_behaviors",
                      inputs={"subskill_count": len(subskills_result.get("subordinate_skills", []))},
                      outputs={"entry_count": len(entry_result.get(ek, []))})

    skill_graph = build_skill_graph(
        goal_with_sources,
        steps_result.get("steps", []),
        subskills_result.get("subordinate_skills", []),
        entry_result.get(ek, []),
    )
    skill_graph["goal_type"] = classification.get("goal_type", "")
    skill_graph["goal_steps"] = steps_result.get("steps", [])
    skill_graph["subordinate_skills"] = subskills_result.get("subordinate_skills", [])
    skill_graph["entry_behaviors"] = entry_result.get(ek, [])
    _record_tool_call(tool_call_plan, "skill_graph", "build_skill_graph",
                      inputs={},
                      outputs={"nodes": skill_graph.get("nodes_count", 0)})

    # ------------------------------------------------------------------
    # 5. Learner context
    # ------------------------------------------------------------------
    from tools.learner_context import (
        analyze_learner_profile,
        analyze_learning_context,
        analyze_performance_context,
        generate_context_implications,
    )

    learner = analyze_learner_profile(learner_input)
    learning = analyze_learning_context(learner_input)
    perf = analyze_performance_context(learner_input)
    implications = generate_context_implications(learner, learning, perf)
    _record_tool_call(tool_call_plan, "learner_context", "analyze_all",
                      inputs={"has_prior_knowledge": bool(teacher_inputs.get("prior_knowledge"))},
                      outputs={"implication_count": len(
                          implications.get("strategy_implications", []))})

    # ------------------------------------------------------------------
    # 6. Objectives
    # ------------------------------------------------------------------
    from tools.objective_engine import write_performance_objectives

    obj_result = write_performance_objectives(skill_graph)
    objectives = obj_result.get("objectives", [])
    _record_tool_call(tool_call_plan, "objective_engine", "write_performance_objectives",
                      inputs={"goal_step_count": len(skill_graph.get("goal_steps", []))},
                      outputs={"objective_count": len(objectives)})

    # ------------------------------------------------------------------
    # 7. Assessment
    # ------------------------------------------------------------------
    from tools.assessment_engine import generate_assessment_plan

    assessment_plan = generate_assessment_plan(objectives)
    _record_tool_call(tool_call_plan, "assessment_engine", "generate_assessment_plan",
                      inputs={"objective_count": len(objectives)},
                      outputs={"has_entry_test": bool(assessment_plan.get("entry_behavior_test")),
                               "has_posttest": bool(assessment_plan.get("posttest"))})

    # ------------------------------------------------------------------
    # 8. Strategy
    # ------------------------------------------------------------------
    from tools.strategy_engine import generate_instructional_strategy

    # Build minimal project dict for strategy engine
    project_for_strategy = _build_project_for_strategy(
        goal_with_sources, skill_graph, objectives, assessment_plan,
        learner_input, learner, learning, perf, implications,
    )
    raw_strategy = generate_instructional_strategy(project_for_strategy)
    _record_tool_call(tool_call_plan, "strategy_engine", "generate_instructional_strategy",
                      inputs={"objective_count": len(objectives)},
                      outputs={"has_lesson_flow": bool(raw_strategy.get("lesson_flow"))})

    # ------------------------------------------------------------------
    # 9. Materials
    # ------------------------------------------------------------------
    from tools.materials_engine import generate_instructional_materials

    project_for_materials = dict(project_for_strategy)
    project_for_materials["instructional_strategy"] = raw_strategy
    materials = generate_instructional_materials(project_for_materials)
    _record_tool_call(tool_call_plan, "materials_engine", "generate_instructional_materials",
                      inputs={"strategy_generated": True},
                      outputs={"material_count": len(materials)})

    # ------------------------------------------------------------------
    # 10. Alignment check
    # ------------------------------------------------------------------
    from tools.alignment_checker import check_full_alignment

    project_for_alignment = dict(project_for_materials)
    project_for_alignment["instructional_materials"] = materials
    alignment = check_full_alignment(project_for_alignment)
    _record_tool_call(tool_call_plan, "alignment_checker", "check_full_alignment",
                      inputs={},
                      outputs={"overall_status": alignment.get("overall_status")})

    # Collect alignment-driven confirmations
    alignment_gates = alignment.get("quality_gates", {})
    for gate_name, gate in alignment_gates.items():
        if isinstance(gate, dict) and not gate.get("passed", True):
            required_confirmations.append({
                "component": "alignment",
                "gate": gate_name,
                "reason": gate.get("message", f"Quality gate '{gate_name}' failed"),
                "issues": gate.get("issues", []),
            })

    # ------------------------------------------------------------------
    # 11. Build project and export
    # ------------------------------------------------------------------
    from core.project_store import create_empty_project

    project = create_empty_project(user_type, "k12" if is_k12 else "corporate")
    project["metadata"].update({
        "project_name": f"{topic}教学设计",
        "subject": subject,
        "grade_level": grade_level,
        "session_info": "1课时",
    })
    project["sources"] = sources
    project["goal"] = goal_with_sources
    project["skill_graph"] = skill_graph
    project["objectives"] = objectives
    project["assessment_plan"] = assessment_plan
    project["context_analysis"] = {
        "learner_profile": learner,
        "learning_context": learning,
        "performance_context": perf,
        "strategy_implications": implications.get("strategy_implications", []),
        "implications": [
            imp.get("implication", str(imp))
            if isinstance(imp, dict) else str(imp)
            for imp in implications.get("strategy_implications", [])
        ],
    }
    project["instructional_strategy"] = raw_strategy
    project["instructional_materials"] = materials
    project["quality_check"] = alignment

    # --- Initialize export-related variables BEFORE export section ---
    verification_status = goal.get("verification_status", "unverified")
    alignment_status = alignment.get("overall_status", "fail")
    final_blocking_reasons = []

    # Export
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "phase7_design_project.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(project, f, ensure_ascii=False, indent=2)

    # Export markdown report
    try:
        from tools.export_package import export_markdown_report
        md_path = os.path.join(output_dir, "phase7_design_report.md")
        export_markdown_report(project, md_path)
    except Exception:
        md_path = None

    # Export materials markdown
    try:
        from tools.pipeline import _export_materials_markdown
        mat_path = os.path.join(output_dir, "phase7_design_materials.md")
        _export_materials_markdown(project, mat_path)
    except Exception:
        mat_path = None

    # Phase 6 exports via document_exporter
    export_files = {
        "full_report_docx": None,
        "lesson_plan_docx": None,
        "student_worksheet_docx": None,
        "alignment_matrix_xlsx": None,
        "ai_process_record_docx": None,
        "skill_graph_drawio": None,
    }
    export_errors = []
    try:
        from tools.document_exporter import (
            export_full_dc_report,
            export_lesson_plan,
            export_student_worksheet,
            export_alignment_matrix,
            export_ai_process_record,
        )
        export_files["full_report_docx"] = (
            export_full_dc_report(project,
                os.path.join(output_dir, "phase7_full_dc_report.docx"))
            .get("path"))
        export_files["lesson_plan_docx"] = (
            export_lesson_plan(project,
                os.path.join(output_dir, "phase7_lesson_plan.docx"))
            .get("path"))
        export_files["student_worksheet_docx"] = (
            export_student_worksheet(project,
                os.path.join(output_dir, "phase7_student_worksheet.docx"))
            .get("path"))
        export_files["alignment_matrix_xlsx"] = (
            export_alignment_matrix(project,
                os.path.join(output_dir, "phase7_alignment_matrix.xlsx"))
            .get("path"))
        export_files["ai_process_record_docx"] = (
            export_ai_process_record(project,
                os.path.join(output_dir, "phase7_ai_process_record.docx"))
            .get("path"))
    except Exception as e:
        export_errors.append(f"document_exporter export failed: {str(e)}")
        warnings.append(f"Phase 6 文档导出失败: {str(e)}")

    # Draw.io skill graph export
    try:
        from tools.drawio_exporter import export_skill_graph_drawio
        drawio_path = os.path.join(output_dir, "phase7_skill_graph.drawio")
        drawio_result = export_skill_graph_drawio(skill_graph, drawio_path)
        export_files["skill_graph_drawio"] = drawio_result.get("path")
    except Exception as e:
        export_errors.append(f"drawio export failed: {str(e)}")
        warnings.append(f"Draw.io 技能流图导出失败: {str(e)}")

    # Record export_package tool call
    exported_count = sum(1 for v in export_files.values() if v is not None)
    _record_tool_call(tool_call_plan, "export_package", "export_all",
                      inputs={"output_dir": output_dir},
                      outputs={"files_exported": exported_count,
                               "export_errors": export_errors})

    # Generate export_index.json
    # Determine export_status - check both exists AND size > 0
    required_exports = ["full_report_docx", "lesson_plan_docx",
                       "student_worksheet_docx", "alignment_matrix_xlsx",
                       "ai_process_record_docx"]
    required_ok = 0
    for k in required_exports:
        path = export_files.get(k)
        if path and os.path.exists(path) and os.path.getsize(path) > 0:
            required_ok += 1
    if required_ok == len(required_exports):
        export_status = "success"
    elif required_ok > 0:
        export_status = "partial"
    else:
        export_status = "failed"

    # Build files dict with path/exists/size
    files_detail = {}
    # The historical Phase 7 index contract intentionally contains the five
    # document files plus four source/project markdown/json files. The graph
    # now has its own v1 multi-page export and remains top-level metadata, but
    # is not counted in this legacy nine-entry index.
    all_export_keys = [key for key in export_files if key != "skill_graph_drawio"] + [
        "export_index_json", "project_json", "report_markdown", "materials_markdown"
    ]
    all_paths = {**export_files,
                 "export_index_json": None,  # Will be set below
                 "project_json": json_path,
                 "report_markdown": md_path,
                 "materials_markdown": mat_path}
    for key in all_export_keys:
        path = all_paths.get(key)
        files_detail[key] = {
            "path": path,
            "exists": bool(path and os.path.exists(path)),
            "size": os.path.getsize(path) if path and os.path.exists(path) else 0,
        }

    export_index = {
        "export_status": export_status,
        "warnings": list(export_errors),
        "full_report_docx": export_files.get("full_report_docx"),
        "lesson_plan_docx": export_files.get("lesson_plan_docx"),
        "student_worksheet_docx": export_files.get("student_worksheet_docx"),
        "alignment_matrix_xlsx": export_files.get("alignment_matrix_xlsx"),
        "ai_process_record_docx": export_files.get("ai_process_record_docx"),
        "skill_graph_drawio": export_files.get("skill_graph_drawio"),
        "project_json": json_path,
        "report_markdown": md_path,
        "materials_markdown": mat_path,
        "files": files_detail,
    }
    export_index_path = os.path.join(output_dir, "export_index.json")
    with open(export_index_path, "w", encoding="utf-8") as f:
        json.dump(export_index, f, ensure_ascii=False, indent=2)

    # Backfill export_index_json in files dict (file now exists)
    export_index["files"]["export_index_json"] = {
        "path": export_index_path,
        "exists": os.path.exists(export_index_path),
        "size": os.path.getsize(export_index_path) if os.path.exists(export_index_path) else 0,
    }
    # Re-write with updated files
    with open(export_index_path, "w", encoding="utf-8") as f:
        json.dump(export_index, f, ensure_ascii=False, indent=2)

    # Build export_result dict (will be included in return)
    export_result = {
        "full_report_docx": export_files.get("full_report_docx"),
        "lesson_plan_docx": export_files.get("lesson_plan_docx"),
        "student_worksheet_docx": export_files.get("student_worksheet_docx"),
        "alignment_matrix_xlsx": export_files.get("alignment_matrix_xlsx"),
        "ai_process_record_docx": export_files.get("ai_process_record_docx"),
        "skill_graph_drawio": export_files.get("skill_graph_drawio"),
        "export_index_json": export_index_path,
        "project_json": json_path,
        "report_markdown": md_path,
        "materials_markdown": mat_path,
        "export_errors": export_errors,
    }

    # If export failed or partial, add blocking reason
    if export_status == "failed":
        final_blocking_reasons.append({
            "component": "export_package",
            "reason": "所有关键导出文件生成失败",
            "evidence": f"export_errors: {export_errors}",
            "required_action": "检查 document_exporter 模块是否可用，或手动导出",
        })
        can_export_final = False
    elif export_status == "partial":
        final_blocking_reasons.append({
            "component": "export_package",
            "reason": "部分关键导出文件缺失或为空",
            "evidence": f"export_errors: {export_errors}",
            "required_action": "检查缺失的导出文件，或手动补充",
        })
        can_export_final = False

    # Determine status
    has_critical = any(
        c.get("component") == "alignment"
        for c in required_confirmations
    )
    has_goal_warning = goal_validation.get("status") in ("warning", "fail")
    has_any_confirmations = len(required_confirmations) > 0

    if has_critical or has_goal_warning or has_any_confirmations:
        status = "completed_with_warnings"
    else:
        status = "completed"

    # --- Compute can_export_final from initialized variables ---
    can_export_final = (
        verification_status in ("verified", "final_verified")
        and alignment_status == "pass"
        and not required_confirmations
    )

    # Append goal/alignment blocking reasons (export reasons already appended above)
    if verification_status not in ("verified", "final_verified"):
        final_blocking_reasons.append({
            "component": "goal",
            "reason": f"K12 source verification pending (status: {verification_status})",
            "evidence": f"goal.validation_status = {verification_status}",
            "required_action": "Teacher must confirm curriculum standard alignment",
        })
    if alignment_status != "pass":
        for w in alignment.get("warnings", []):
            final_blocking_reasons.append({
                "component": "alignment",
                "reason": w,
                "evidence": f"alignment.overall_status = {alignment_status}",
                "required_action": "Fix alignment issues before final export",
            })

    if required_confirmations:
        draft_status = "draft_pending_confirmation"
    elif not can_export_final:
        draft_status = "blocked"
    else:
        draft_status = "final_ready"

    # Progress tracking
    total_steps = len(tool_call_plan)
    completed_steps = total_steps
    progress = {
        "current_step": "export",
        "completed_steps": completed_steps,
        "total_steps": completed_steps,
        "next_action": (
            "await teacher confirmation"
            if draft_status == "draft_pending_confirmation"
            else "resolve blocking issues"
            if draft_status == "blocked"
            else "ready for final export"
        ),
    }

    # Build tool status report
    required_tools = [
        ("standards_search", "standards_search", "search_standards"),
        ("goal_engine", "goal_engine", "validate_instructional_goal"),
        ("skill_graph", "skill_graph", "build_skill_graph"),
        ("learner_context", "learner_context", "analyze_learner_profile"),
        ("objective_engine", "objective_engine", "write_performance_objectives"),
        ("assessment_engine", "assessment_engine", "generate_assessment_plan"),
        ("strategy_engine", "strategy_engine", "generate_instructional_strategy"),
        ("materials_engine", "materials_engine", "generate_instructional_materials"),
        ("alignment_checker", "alignment_checker", "check_full_alignment"),
        ("export_package", "document_exporter", "export_all"),
        ("knowledge_ingest", "knowledge_ingest", "ingest_document"),
        ("teacher_memory", "teacher_memory", "read_teacher_profile"),
        ("formative_evaluation_plan", "formative_evaluation",
         "design_one_on_one_evaluation"),
    ]
    called_engines = {e.get("engine") for e in tool_call_plan}
    tool_status_report = []
    for req_engine, engine_name, func_name in required_tools:
        tool_status_report.append({
            "tool_name": req_engine,
            "engine": engine_name,
            "function": func_name,
            "status": "called" if req_engine in called_engines else "not_called",
        })

    return {
        "mode": "dc-design",
        "user_type": user_type,
        "scenario": scenario,
        "status": status,
        "tool_call_plan": tool_call_plan,
        "warnings": warnings,
        "required_confirmations": required_confirmations,
        "findings": [],
        "revision_log": [],
        "project": project,
        "quality_check": project.get("quality_check", {}),
        "can_export_final": can_export_final,
        "final_blocking_reasons": final_blocking_reasons,
        "draft_status": draft_status,
        "progress": progress,
        "tool_status_report": tool_status_report,
        "export_result": {
            **export_result,
        },
        "source_trace": {
            "goal_basis": {
                "status": project.get("goal", {}).get("verification_status", "unknown"),
                "sources": project.get("sources", []),
            }
        },
        "alignment_summary": alignment,
    }


# ======================================================================
# dc-review mode
# ======================================================================

def _run_dc_review(request: dict, output_dir: str) -> dict:
    """
    Review an existing design project for alignment and quality issues.

    Reads the project JSON, runs alignment checks, and identifies issues
    with severity and suggested fixes.
    """
    tool_call_plan: list[dict] = []
    warnings: list[str] = []
    findings: list[dict] = []

    project_path = request.get("existing_design_project_path", "")
    if not project_path:
        return {
            "mode": "dc-review",
            "status": "error",
            "tool_call_plan": [],
            "warnings": ["No project path provided"],
            "required_confirmations": [],
            "findings": [],
            "revision_log": [],
        }

    # Resolve relative path against repo root
    if not os.path.isabs(project_path):
        project_path = os.path.join(_REPO_ROOT, project_path)

    if not os.path.isfile(project_path):
        return {
            "mode": "dc-review",
            "status": "error",
            "tool_call_plan": [],
            "warnings": [f"Project file not found: {project_path}"],
            "required_confirmations": [],
            "findings": [],
            "revision_log": [],
        }

    with open(project_path, "r", encoding="utf-8") as f:
        project = json.load(f)

    _record_tool_call(tool_call_plan, "project_io", "load_project",
                      inputs={"path": project_path},
                      outputs={"project_id": project.get("project_id", "")})

    # ------------------------------------------------------------------
    # 1. Run alignment checks
    # ------------------------------------------------------------------
    from tools.alignment_checker import check_full_alignment

    alignment = check_full_alignment(project)
    _record_tool_call(tool_call_plan, "alignment_checker", "check_full_alignment",
                      inputs={},
                      outputs={"overall_status": alignment.get("overall_status")})

    # ------------------------------------------------------------------
    # 2. Identify issues from alignment
    # ------------------------------------------------------------------
    quality_gates = alignment.get("quality_gates", {})
    for gate_name, gate in quality_gates.items():
        if isinstance(gate, dict) and not gate.get("passed", True):
            issues = gate.get("issues", [])
            severity = "high" if gate.get("is_critical", False) else "medium"
            findings.append({
                "finding_id": f"fnd_{len(findings) + 1}",
                "type": "alignment_gap",
                "gate": gate_name,
                "severity": severity,
                "description": gate.get("message", f"Gate '{gate_name}' not passed"),
                "evidence": f"quality_gates.{gate_name}.passed = {gate.get('passed', True)}",
                "suggested_fix": _suggest_fix_for_gate(gate_name, gate),
                "affected_modules": [gate_name.split("_")[0]] if "_" in gate_name else [],
                "related_quality_gate": gate_name,
            })

    # 2b. Convert alignment warnings to findings
    alignment_warnings = alignment.get("warnings", [])
    for warn in alignment_warnings:
        # Determine severity from warning content
        if "未覆盖" in warn or "不对齐" in warn or "未嵌入" in warn:
            sev = "high"
        elif "缺少" in warn or "仅包含" in warn:
            sev = "medium"
        else:
            sev = "low"
        findings.append({
            "finding_id": f"fnd_{len(findings) + 1}",
            "type": "alignment_warning",
            "severity": sev,
            "description": warn,
            "evidence": warn,
            "suggested_fix": "Review and resolve alignment issue",
            "affected_modules": [],
            "related_quality_gate": "",
        })

    # 2c. Check for source trace gap from alignment
    if alignment.get("overall_status") != "pass" and alignment.get("can_export_as_final") is False:
        findings.append({
            "finding_id": f"fnd_{len(findings) + 1}",
            "type": "source_trace_gap",
            "severity": "high",
            "description": (
                f"Alignment overall_status: {alignment.get('overall_status')}; "
                "cannot export as final"
            ),
            "evidence": f"alignment.overall_status = {alignment.get('overall_status')}; can_export_as_final = False",
            "suggested_fix": (
                "Resolve blocking alignment issues and verify source "
                "records before final export."
            ),
            "affected_modules": ["alignment"],
            "related_quality_gate": "",
        })

    # ------------------------------------------------------------------
    # 3. Check for missing sources
    # ------------------------------------------------------------------
    sources = project.get("sources", [])
    goal = project.get("goal", {})
    scene_type = goal.get("scene_type", "")

    if scene_type in ("k12", "K12"):
        has_ab = any(s.get("source_level", "").startswith(("A", "B")) for s in sources)
        if not has_ab:
            findings.append({
                "finding_id": f"fnd_{len(findings) + 1}",
                "type": "missing_source",
                "severity": "high",
                "description": "K12 design lacks A/B-level official source",
                "evidence": f"sources count: {len(sources)}; no A/B-level source found",
                "suggested_fix": (
                    "Run standards_search to locate applicable curriculum "
                    "standards, or ask teacher to upload source documents."
                ),
                "affected_modules": ["goal", "sources"],
                "related_quality_gate": "",
            })

    # ------------------------------------------------------------------
    # 4. Check for weak verbs in objectives
    # ------------------------------------------------------------------
    from core.verbs import check_observable_verb

    objectives = project.get("objectives", [])
    for obj in objectives:
        behavior = obj.get("behavior", "")
        if behavior:
            verb_check = check_observable_verb(behavior)
            if not verb_check.get("is_observable", True):
                findings.append({
                    "finding_id": f"fnd_{len(findings) + 1}",
                    "type": "weak_verb",
                    "severity": "low",
                    "objective_id": obj.get("objective_id", ""),
                    "description": f"Objective uses non-observable verb: {behavior}",
                    "evidence": f"verb_check.is_observable = False for '{behavior}'",
                    "suggested_fix": "Replace with measurable action verb",
                    "affected_modules": ["objectives"],
                    "related_quality_gate": "objective_assessment_alignment",
                })

    # ------------------------------------------------------------------
    # 5. Check source trace
    # ------------------------------------------------------------------
    source_status = goal.get("source_status", "")
    verification = goal.get("verification_status", "")
    if verification in ("draft_unverified", "draft_pending_verification"):
        findings.append({
            "finding_id": f"fnd_{len(findings) + 1}",
            "type": "source_trace_gap",
            "severity": "high",
            "description": f"Goal verification status: {verification}",
            "evidence": f"goal.verification_status = {verification}",
            "suggested_fix": (
                "Provide verified source records with specific clause "
                "alignment to elevate source_status."
            ),
            "affected_modules": ["goal"],
            "related_quality_gate": "",
        })

    # ------------------------------------------------------------------
    # 6. Build review report
    # ------------------------------------------------------------------
    severity_counts = {}
    for f in findings:
        sev = f.get("severity", "low")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    review_report = {
        "project_id": project.get("project_id", ""),
        "review_timestamp": datetime.now(timezone.utc).isoformat(),
        "finding_count": len(findings),
        "severity_summary": severity_counts,
        "overall_assessment": (
            "pass" if not findings and not alignment_warnings
            else "needs_revision" if severity_counts.get("high", 0) == 0
            else "major_revision_required"
        ),
    }

    # Export review report
    os.makedirs(output_dir, exist_ok=True)
    review_path = os.path.join(output_dir, "phase7_review_report.json")
    with open(review_path, "w", encoding="utf-8") as f:
        json.dump({
            "review": review_report,
            "findings": findings,
            "alignment": alignment,
            "tool_call_plan": tool_call_plan,
        }, f, ensure_ascii=False, indent=2)

    has_high = severity_counts.get("high", 0) > 0
    return {
        "mode": "dc-review",
        "status": "completed_with_warnings" if findings else "completed",
        "tool_call_plan": tool_call_plan,
        "warnings": warnings,
        "required_confirmations": [],
        "findings": findings,
        "revision_log": [],
        "review_report": review_report,
        "review_path": review_path,
        "original_project": project,
    }


# ======================================================================
# dc-revise mode
# ======================================================================

def _run_dc_revise(request: dict, output_dir: str) -> dict:
    """
    Revise an existing design based on feedback.

    1. Load the existing project
    2. Run impact analysis on each feedback item
    3. Execute targeted modifications
    4. Re-run alignment checks
    5. Return revision log with before/after summary
    """
    tool_call_plan: list[dict] = []
    warnings: list[str] = []
    revision_log: list[dict] = []

    project_path = request.get("existing_design_project_path", "")
    feedback = request.get("feedback_or_revision_data", {})

    if not project_path:
        return {
            "mode": "dc-revise",
            "status": "error",
            "tool_call_plan": [],
            "warnings": ["No project path provided"],
            "required_confirmations": [],
            "findings": [],
            "revision_log": [],
        }

    # Resolve relative path
    if not os.path.isabs(project_path):
        project_path = os.path.join(_REPO_ROOT, project_path)

    if not os.path.isfile(project_path):
        return {
            "mode": "dc-revise",
            "status": "error",
            "tool_call_plan": [],
            "warnings": [f"Project file not found: {project_path}"],
            "required_confirmations": [],
            "findings": [],
            "revision_log": [],
        }

    with open(project_path, "r", encoding="utf-8") as f:
        original_project = json.load(f)

    # Deep copy for modification
    project = copy.deepcopy(original_project)

    _record_tool_call(tool_call_plan, "project_io", "load_project",
                      inputs={"path": project_path},
                      outputs={"project_id": project.get("project_id", "")})

    # ------------------------------------------------------------------
    # 1. Pre-revision alignment baseline
    # ------------------------------------------------------------------
    from tools.alignment_checker import check_full_alignment

    pre_alignment = check_full_alignment(project)
    _record_tool_call(tool_call_plan, "alignment_checker", "check_full_alignment (pre-revision)",
                      inputs={},
                      outputs={"overall_status": pre_alignment.get("overall_status")})

    # ------------------------------------------------------------------
    # 2. Process each feedback item
    # ------------------------------------------------------------------
    feedback_items = feedback.get("items", [])
    for idx, item in enumerate(feedback_items):
        module = item.get("module", "")
        issue_text = item.get("issue", "")
        severity = item.get("severity", "low")

        # Impact analysis -- identify what needs to change
        impact = _analyze_feedback_impact(project, module, issue_text)

        # Execute modification
        mod_result = _apply_modification(project, module, issue_text, item)

        revision_log.append({
            "revision_id": f"rev_{idx + 1}",
            "module": module,
            "original_issue": issue_text,
            "severity": severity,
            "impact_analysis": impact,
            "action_status": mod_result.get("action_status", "not_applicable"),
            "modification_applied": mod_result.get("applied", False),
            "modification_summary": mod_result.get("summary", ""),
            "before_snapshot": mod_result.get("before", {}),
            "after_snapshot": mod_result.get("after", {}),
            "teacher_confirmation_required": mod_result.get("action_status") == "needs_teacher_input",
        })

    _record_tool_call(tool_call_plan, "revision_engine", "apply_modifications",
                      inputs={"feedback_count": len(feedback_items)},
                      outputs={"revisions_applied": sum(
                          1 for r in revision_log if r.get("modification_applied"))})

    # ------------------------------------------------------------------
    # 3. Post-revision alignment check
    # ------------------------------------------------------------------
    post_alignment = check_full_alignment(project)
    _record_tool_call(tool_call_plan, "alignment_checker", "check_full_alignment (post-revision)",
                      inputs={},
                      outputs={"overall_status": post_alignment.get("overall_status")})

    # ------------------------------------------------------------------
    # 4. Generate revision record
    # ------------------------------------------------------------------
    # Determine unresolved items and teacher confirmation needs
    unresolved_items = [
        r for r in revision_log
        if r.get("action_status") in ("needs_teacher_input", "failed")
    ]
    requires_teacher_confirmation = len(unresolved_items) > 0
    post_revision_can_export_final = (
        post_alignment.get("overall_status") == "pass"
        and not requires_teacher_confirmation
    )

    revision_record = {
        "revision_cycle_id": f"cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "original_project_id": original_project.get("project_id", ""),
        "feedback_type": feedback.get("feedback_type", "unknown"),
        "total_items": len(feedback_items),
        "items_revised": sum(1 for r in revision_log if r.get("modification_applied")),
        "pre_revision_alignment": pre_alignment.get("overall_status"),
        "post_revision_alignment": post_alignment.get("overall_status"),
        "alignment_improved": _alignment_improved(pre_alignment, post_alignment),
        "unresolved_items": unresolved_items,
        "requires_teacher_confirmation": requires_teacher_confirmation,
        "post_revision_can_export_final": post_revision_can_export_final,
    }

    # Export revised project
    os.makedirs(output_dir, exist_ok=True)
    revised_path = os.path.join(output_dir, "phase7_revised_project.json")
    with open(revised_path, "w", encoding="utf-8") as f:
        json.dump(project, f, ensure_ascii=False, indent=2)

    # Export revision log
    log_path = os.path.join(output_dir, "phase7_revision_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "revision_record": revision_record,
            "revision_log": revision_log,
            "tool_call_plan": tool_call_plan,
        }, f, ensure_ascii=False, indent=2)

    # Determine status based on post-revision alignment
    post_status_val = post_alignment.get("overall_status", "fail")
    revise_status = "completed" if post_status_val == "pass" else "completed_with_warnings"

    return {
        "mode": "dc-revise",
        "status": revise_status,
        "tool_call_plan": tool_call_plan,
        "warnings": warnings,
        "required_confirmations": [],
        "findings": [],
        "revision_log": revision_log,
        "revision_record": revision_record,
        "revised_project": project,
        "revised_project_path": revised_path,
        "revision_log_path": log_path,
        "pre_revision_alignment": pre_alignment,
        "post_revision_alignment": post_alignment,
    }


# ======================================================================
# Internal helpers
# ======================================================================

def _record_tool_call(plan: list, engine: str, function: str,
                      inputs: dict = None, outputs: dict = None) -> None:
    """Append a structured tool call record to the plan."""
    plan.append({
        "step": len(plan) + 1,
        "engine": engine,
        "function": function,
        "inputs": inputs or {},
        "outputs": outputs or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def _grade_to_stage(grade_level: str) -> str:
    """Derive educational stage from grade level string."""
    if not grade_level:
        return ""
    gl = grade_level.lower()
    if any(k in gl for k in ("小", "primary")):
        return "小学"
    if any(k in gl for k in ("初", "junior")):
        return "初中"
    if any(k in gl for k in ("高", "senior")):
        return "高中"
    # Try numeric
    import re
    m = re.search(r"(\d+)", grade_level)
    if m:
        num = int(m.group(1))
        if num <= 6:
            return "小学"
        elif num <= 9:
            return "初中"
        else:
            return "高中"
    return "初中"  # default


def _derive_behavior(topic: str) -> str:
    """Derive an observable behavior from the topic name."""
    if not topic:
        return "完成相关学习任务"
    # Common patterns
    if topic.startswith("认识"):
        return f"能用自然语言描述{topic[2:]}的基本概念和关键特征"
    if topic.startswith("理解"):
        return f"能用自己的话解释{topic[2:]}的核心原理"
    if topic.startswith("掌握"):
        return f"能独立运用{topic[2:]}的方法完成任务"
    if topic.startswith("运用") or topic.startswith("应用"):
        return f"能在新情境中{topic}"
    return f"能描述{topic}的关键步骤和特征"


def _build_learner_input(request: dict) -> dict:
    """Build the learner context input dict from the request."""
    teacher_inputs = request.get("teacher_inputs", {})
    return {
        "class_duration": 45,
        "class_size": 48,
        "prior_knowledge": teacher_inputs.get("prior_knowledge", ""),
        "common_difficulties": teacher_inputs.get("common_difficulties", []),
        "available_media": teacher_inputs.get("available_media", ["黑板", "投影"]),
        "devices": teacher_inputs.get("devices", ""),
        "network": teacher_inputs.get("network", "普通教室"),
        "classroom_layout": teacher_inputs.get("classroom_layout", "普通教室，可小组讨论"),
        "motivation": teacher_inputs.get("motivation", ""),
        "learning_preferences": teacher_inputs.get("learning_preferences",
                                                    ["情境任务", "小组讨论"]),
    }


def _build_project_for_strategy(
    goal, skill_graph, objectives, assessment_plan,
    learner_input, learner, learning, perf, implications,
) -> dict:
    """Build the minimal project dict expected by generate_instructional_strategy."""
    # Normalize context analysis the way pipeline.py does
    def _desc(obj, key="description"):
        if isinstance(obj, dict):
            return obj.get(key, "")
        return str(obj) if obj else ""

    entry_skills_raw = learner.get("entry_skills", {})
    entry_skills = (
        entry_skills_raw.get("items", [])
        if isinstance(entry_skills_raw, dict)
        else entry_skills_raw if isinstance(entry_skills_raw, list)
        else []
    )

    prefs_raw = learner.get("learning_preferences", {})
    learning_preferences = (
        prefs_raw.get("preferences", [])
        if isinstance(prefs_raw, dict)
        else prefs_raw if isinstance(prefs_raw, list)
        else []
    )

    gc_raw = learner.get("group_characteristics", {})
    if isinstance(gc_raw, dict):
        group_characteristics = gc_raw.get("details", gc_raw.get("grouping", ""))
        if isinstance(group_characteristics, dict):
            group_characteristics = json.dumps(group_characteristics, ensure_ascii=False)
    else:
        group_characteristics = str(gc_raw) if gc_raw else ""

    devices_raw = learning.get("devices", {})
    devices = _desc(devices_raw) if isinstance(devices_raw, dict) else str(devices_raw) if devices_raw else ""

    network_raw = learning.get("network", {})
    network = _desc(network_raw) if isinstance(network_raw, dict) else str(network_raw) if network_raw else ""

    strategy_implications = implications.get("strategy_implications", [])
    flat_implications = []
    for imp in strategy_implications:
        if isinstance(imp, dict):
            flat_implications.append(imp.get("implication", str(imp)))
        else:
            flat_implications.append(str(imp))

    context_analysis = {
        "learner_profile": {
            "entry_skills": entry_skills,
            "prior_knowledge": _desc(learner.get("prior_knowledge", {})),
            "attitude_toward_content": _desc(learner.get("attitude_content", {})),
            "attitude_toward_delivery": _desc(learner.get("attitude_delivery", {})),
            "motivation": _desc(learner.get("motivation", {})),
            "ability_level": _desc(learner.get("ability_level", {})),
            "learning_preferences": learning_preferences,
            "group_characteristics": group_characteristics,
            "common_difficulties": learner.get("common_difficulties", []),
        },
        "learning_context": {
            "class_duration": learning.get("class_duration", 45),
            "class_size": learning.get("class_size", ""),
            "available_media": learning.get("available_media", []),
            "devices": devices,
            "network": network,
            "classroom_layout": learning.get("classroom_layout", ""),
            "constraints": learning.get("constraints", []),
            "supports": learning.get("supports", []),
        },
        "performance_context": {
            "use_environment": perf.get("use_environment", ""),
            "expected_transfer": perf.get("expected_transfer", ""),
            "real_world_tasks": perf.get("real_world_tasks", []),
            "similarity_to_learning_context": perf.get("similarity_to_learning_context", ""),
            "transfer_risks": perf.get("transfer_risks", []),
        },
        "strategy_implications": strategy_implications,
        "implications": flat_implications,
        "common_difficulties": learner.get("common_difficulties", []),
        "class_duration": learning.get("class_duration", 45),
    }

    return {
        "goal": goal,
        "skill_graph": skill_graph,
        "objectives": objectives,
        "assessment_plan": assessment_plan,
        "context_analysis": context_analysis,
        "learner_context_input": learner_input,
    }


def _suggest_fix_for_gate(gate_name: str, gate: dict) -> str:
    """Generate a human-readable suggested fix for a failed quality gate."""
    fixes = {
        "goal_skill_alignment": (
            "Review goal statement and ensure skill_graph steps "
            "directly derive from the goal behaviour."
        ),
        "skill_objective_alignment": (
            "Ensure each skill_graph node has at least one corresponding "
            "performance objective."
        ),
        "objective_assessment_alignment": (
            "Verify every objective has a matching assessment item "
            "in the assessment plan."
        ),
        "context_strategy_alignment": (
            "Check that instructional strategy addresses learner "
            "context implications and constraints."
        ),
        "objective_strategy_alignment": (
            "Confirm all objectives are covered in the lesson flow."
        ),
        "assessment_strategy_integration": (
            "Embed assessment checkpoints within the lesson flow segments."
        ),
    }
    return fixes.get(gate_name, "Review the failed component and ensure cross-component consistency.")


def _analyze_feedback_impact(project: dict, module: str, issue: str) -> dict:
    """Analyze what components are affected by feedback on a given module."""
    affected = []
    cascade = []

    if module == "objective":
        affected = ["objectives", "assessment_plan", "instructional_strategy"]
        cascade = ["materials"]
    elif module == "assessment":
        affected = ["assessment_plan", "instructional_strategy"]
        cascade = ["materials"]
    elif module == "strategy":
        affected = ["instructional_strategy"]
        cascade = ["instructional_materials"]
    elif module == "goal":
        affected = ["goal", "skill_graph", "objectives", "assessment_plan",
                     "instructional_strategy"]
        cascade = ["instructional_materials"]
    elif module == "materials":
        affected = ["instructional_materials"]
        cascade = []
    else:
        affected = [module]
        cascade = []

    return {
        "target_module": module,
        "directly_affected": affected,
        "cascade_affected": cascade,
        "issue_description": issue,
    }


def _apply_modification(project: dict, module: str, issue: str,
                        feedback_item: dict) -> dict:
    """Apply a targeted modification to the project based on feedback.

    Returns dict with:
        action_status: "applied" | "needs_teacher_input" | "not_applicable" | "failed"
        applied: bool (True only when before/after actually differ)
        summary: str
        before: dict
        after: dict
    """
    action_status = "not_applicable"
    summary = ""
    before = {}
    after = {}

    if module == "objective":
        # Find the objective most related to the issue and improve its description
        objectives = project.get("objectives", [])
        modified_count = 0
        for obj in objectives:
            if _text_matches_issue(obj.get("behavior", ""), issue):
                old_behavior = obj.get("behavior", "")
                before[obj.get("objective_id", "")] = old_behavior
                # Enhance the behavior description
                obj["behavior"] = _enhance_behavior(old_behavior, issue)
                obj["criterion"] = _enhance_criterion(obj.get("criterion", ""), issue)
                new_behavior = obj.get("behavior", "")
                if new_behavior != old_behavior:
                    after[obj.get("objective_id", "")] = new_behavior
                    modified_count += 1
                else:
                    # Enhancement did not change the text
                    del after[obj.get("objective_id", "")]
        if modified_count > 0:
            action_status = "applied"
            summary = f"Modified {modified_count} objective(s) to address: {issue}"
        else:
            action_status = "needs_teacher_input"
            before = {}
            summary = f"No specific objective matched; flagged for teacher review: {issue}"

    elif module == "assessment":
        plan = project.get("assessment_plan", {})
        modified_count = 0
        for key in ("entry_behavior_test", "pretest", "practice", "posttest"):
            section = plan.get(key, {})
            if section and _text_matches_issue(json.dumps(section, ensure_ascii=False), issue):
                old_criteria = section.get("scoring_criteria", [])
                before[key] = section.get("task_prompt", "")
                section["scoring_criteria"] = _enhance_rubric(old_criteria, issue)
                new_criteria = section.get("scoring_criteria", [])
                if new_criteria != old_criteria:
                    after[key] = f"Enhanced scoring criteria for {key}"
                    modified_count += 1
        if modified_count > 0:
            action_status = "applied"
            summary = f"Enhanced assessment rubrics to address: {issue}"
        else:
            action_status = "needs_teacher_input"
            summary = f"No assessment section matched the feedback; flagged for teacher review: {issue}"

    elif module == "strategy":
        strategy = project.get("instructional_strategy", {})
        flow = strategy.get("lesson_flow", [])
        modified_segments = 0
        for seg in flow:
            activity = seg.get("具体活动", seg.get("活动", ""))
            if _text_matches_issue(activity, issue):
                seg_key = seg.get("环节", seg.get("教学环节", str(modified_segments)))
                old_notes = seg.get("备注", seg.get("评估方式", ""))
                before[seg_key] = activity
                seg["备注"] = (old_notes + "；" if old_notes else "") + "时间分配已根据反馈调整"
                new_notes = seg.get("备注", "")
                if new_notes != old_notes:
                    after[seg_key] = new_notes
                    modified_segments += 1
        if modified_segments > 0:
            action_status = "applied"
            summary = f"Adjusted {modified_segments} strategy segment(s) to address: {issue}"
        else:
            action_status = "needs_teacher_input"
            summary = f"No specific strategy segment matched; flagged for teacher review: {issue}"

    elif module == "materials":
        materials = project.get("instructional_materials", {})
        modified_mats = 0
        for mat_key, mat_val in materials.items():
            if isinstance(mat_val, dict):
                content = mat_val.get("content", mat_val)
                content_str = json.dumps(content, ensure_ascii=False)
                if _text_matches_issue(content_str, issue):
                    before[mat_key] = "existing content"
                    # Flag for regeneration
                    mat_val["_needs_regeneration"] = True
                    mat_val["_regeneration_reason"] = issue
                    after[mat_key] = "flagged for regeneration"
                    modified_mats += 1
        if modified_mats > 0:
            action_status = "applied"
            summary = f"Flagged {modified_mats} material(s) for regeneration: {issue}"
        else:
            action_status = "needs_teacher_input"
            summary = f"No material matched the feedback; flagged for teacher review: {issue}"

    else:
        action_status = "failed"
        summary = f"Unknown module '{module}'; no modification applied"

    # Compute applied from actual before/after differences
    applied = bool(before) and bool(after) and before != after

    return {
        "action_status": action_status,
        "applied": applied,
        "summary": summary,
        "before": before,
        "after": after,
    }


def _text_matches_issue(text: str, issue: str) -> bool:
    """Check if a text fragment is related to an issue description.

    Uses simple keyword overlap rather than full NLP.
    """
    if not text or not issue:
        return False
    # Extract meaningful Chinese characters from the issue (skip common words)
    issue_chars = set(issue)
    text_lower = text.lower()
    issue_lower = issue.lower()

    # Direct substring check
    if issue_lower in text_lower:
        return True

    # Check if key content words from issue appear in text
    # Remove common stop words
    stop = set("的了在是和与或但而且也都被把将从到")
    meaningful_issue_chars = issue_chars - stop
    if not meaningful_issue_chars:
        return False

    overlap = sum(1 for c in meaningful_issue_chars if c in text_lower)
    return overlap >= min(3, len(meaningful_issue_chars))


def _enhance_behavior(behavior: str, issue: str) -> str:
    """Enhance a behavior description based on feedback about specificity."""
    if "不够具体" in issue or "笼统" in issue:
        # Add specificity markers
        if "能" in behavior and len(behavior) < 30:
            return behavior + "，并能举出至少两个具体实例"
    return behavior


def _enhance_criterion(criterion: str, issue: str) -> str:
    """Enhance a criterion description based on feedback."""
    if "太抽象" in issue or "不够具体" in issue:
        if "%" not in criterion:
            return criterion + "，评分标准需包含可量化指标"
    return criterion


def _enhance_rubric(criteria: list, issue: str) -> list:
    """Enhance assessment rubric criteria based on feedback."""
    enhanced = []
    for c in criteria:
        new_c = dict(c)
        if "太抽象" in issue or "抽象" in issue:
            # Add concrete descriptors
            desc = new_c.get("description", "")
            if desc and "分" not in desc:
                new_c["description"] = desc + "（1-2分：部分达成；3-4分：基本达成；5分：完全达成）"
        enhanced.append(new_c)
    return enhanced if enhanced else criteria


def _alignment_improved(pre: dict, post: dict) -> bool:
    """Check if alignment improved after revision."""
    pre_status = pre.get("overall_status", "")
    post_status = post.get("overall_status", "")
    status_rank = {"fail": 0, "warning": 1, "pass": 2}
    return status_rank.get(post_status, 0) > status_rank.get(pre_status, 0)


# ======================================================================
# CLI entry point
# ======================================================================

if __name__ == "__main__":
    import sys as _sys

    if len(_sys.argv) > 1:
        req_path = _sys.argv[1]
        with open(req_path, "r", encoding="utf-8") as f:
            request = json.load(f)
    else:
        request = {"mode": "dc-design"}

    result = run_agent_session(request)
    # Print summary (not full project)
    summary = {k: v for k, v in result.items() if k != "project"}
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
