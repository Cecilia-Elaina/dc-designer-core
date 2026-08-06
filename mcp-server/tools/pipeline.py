"""
Unified pipeline for dc-designer-core MVP.
Runs the full flow from seed to report.

Steps:
  1. Load seed project
  2. Goal engine validation
  3. Skill graph construction
  4. Objective generation
  5. Assessment plan generation
  6. Learner context analysis
  7. Instructional strategy generation
  8. Data structure normalization (bridges engine outputs to renderer/checker expectations)
  9. Alignment / quality check
  10. Export JSON + Markdown
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


# ======================================================================
# Main pipeline
# ======================================================================

def run_mvp_pipeline_with_context(
    seed_path: str, output_dir: str = "exports"
) -> dict:
    """
    Run the full MVP pipeline with learner context.

    Parameters
    ----------
    seed_path : str
        Path to a JSON seed file containing at minimum ``goal`` and
        ``metadata`` keys, and optionally ``learner_context_input``,
        ``sources``, etc.
    output_dir : str
        Directory for exported JSON and Markdown files.

    Returns
    -------
    dict with keys ``project``, ``project_path``, ``report_path``,
    ``quality_check``.
    """
    # ------------------------------------------------------------------
    # 1. Load seed
    # ------------------------------------------------------------------
    with open(seed_path, "r", encoding="utf-8") as f:
        project = json.load(f)

    project.setdefault("skill_graph", {})
    project.setdefault("objectives", [])
    project.setdefault("assessment_plan", {})
    project.setdefault("sources", [])
    project.setdefault("metadata", {})

    # ------------------------------------------------------------------
    # 2. Goal engine
    # ------------------------------------------------------------------
    from tools.goal_engine import validate_instructional_goal

    r = validate_instructional_goal(
        project["goal"], project.get("sources", [])
    )
    project["goal"].update(r)

    # ------------------------------------------------------------------
    # 3. Skill graph
    # ------------------------------------------------------------------
    from tools.skill_graph import (
        classify_goal_type,
        generate_goal_steps,
        analyze_subordinate_skills,
        identify_entry_behaviors,
        build_skill_graph,
    )

    r = classify_goal_type(project["goal"])
    project["skill_graph"]["goal_type"] = r["goal_type"]
    project["skill_graph"]["classification_rationale"] = r.get("rationale", "")

    r = generate_goal_steps(project["goal"])
    project["skill_graph"]["goal_steps"] = r["steps"]

    r = analyze_subordinate_skills(project["skill_graph"]["goal_steps"])
    project["skill_graph"]["subordinate_skills"] = r["subordinate_skills"]

    r = identify_entry_behaviors(project["skill_graph"]["subordinate_skills"])
    # Handle both British and American spelling from the engine
    ek = "entry_behaviors" if "entry_behaviors" in r else "entry_behaviours"
    project["skill_graph"]["entry_behaviors"] = r[ek]

    graph = build_skill_graph(
        project["goal"],
        project["skill_graph"]["goal_steps"],
        project["skill_graph"]["subordinate_skills"],
        project["skill_graph"]["entry_behaviors"],
    )
    project["skill_graph"].update(graph)

    # ------------------------------------------------------------------
    # 4. Objectives
    # ------------------------------------------------------------------
    from tools.objective_engine import write_performance_objectives

    r = write_performance_objectives(project["skill_graph"])
    project["objectives"] = r["objectives"]

    # ------------------------------------------------------------------
    # 5. Assessment
    # ------------------------------------------------------------------
    from tools.assessment_engine import generate_assessment_plan

    project["assessment_plan"] = generate_assessment_plan(project["objectives"])

    # ------------------------------------------------------------------
    # 6. Learner context
    # ------------------------------------------------------------------
    from tools.learner_context import (
        analyze_learner_profile,
        analyze_learning_context,
        analyze_performance_context,
        generate_context_implications,
    )

    lctx = project.get("learner_context_input", {})
    learner = analyze_learner_profile(lctx)
    learning = analyze_learning_context(lctx)
    performance = analyze_performance_context(lctx)
    implications = generate_context_implications(learner, learning, performance)

    project["context_analysis"] = _normalize_context_analysis(
        learner, learning, performance, implications, lctx
    )

    # ------------------------------------------------------------------
    # 7. Strategy engine
    # ------------------------------------------------------------------
    from tools.strategy_engine import generate_instructional_strategy

    raw_strategy = generate_instructional_strategy(project)

    # ------------------------------------------------------------------
    # 8. Normalize all data structures
    # ------------------------------------------------------------------
    project["instructional_strategy"] = _normalize_strategy(
        raw_strategy, project
    )

    # ------------------------------------------------------------------
    # 8.1 Enrich lesson_flow with objective_ids and recalculate quality
    # ------------------------------------------------------------------
    _enrich_lesson_flow(project)
    _recalculate_strategy_quality(project)

    # ------------------------------------------------------------------
    # 9. Materials generation
    # ------------------------------------------------------------------
    from tools.materials_engine import generate_instructional_materials
    from core.material_alignment import check_full_material_alignment

    materials = generate_instructional_materials(project)
    project["instructional_materials"] = materials

    # Material alignment check
    material_alignment = check_full_material_alignment(project)
    project["material_alignment"] = material_alignment

    # ------------------------------------------------------------------
    # 10. Alignment check
    # ------------------------------------------------------------------
    from tools.alignment_checker import check_full_alignment

    qc = check_full_alignment(project)
    project["quality_check"] = qc

    # ------------------------------------------------------------------
    # 10. Clean sources & export
    # ------------------------------------------------------------------
    try:
        from core.source_normalizer import clean_project_sources
        project = clean_project_sources(project)
    except ImportError:
        pass

    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(
        output_dir, "mvp_algorithm_project_with_strategy_full.json"
    )
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(project, f, ensure_ascii=False, indent=2)

    from tools.export_package import export_markdown_report

    md_path = os.path.join(
        output_dir, "mvp_algorithm_report_with_strategy.md"
    )
    export_markdown_report(project, md_path)

    # Export materials-only markdown
    materials_md_path = os.path.join(output_dir, "mvp_algorithm_materials.md")
    _export_materials_markdown(project, materials_md_path)

    return {
        "project": project,
        "project_path": json_path,
        "report_path": md_path,
        "materials_path": materials_md_path,
        "quality_check": qc,
    }


def run_mvp_pipeline_with_materials(
    seed_path: str, output_dir: str = "exports"
) -> dict:
    """
    Run the full MVP pipeline with learner context AND materials.

    Generates:
    - mvp_algorithm_project_with_materials_full.json
    - mvp_algorithm_report_with_materials.md
    - mvp_algorithm_materials.md
    """
    # Run the base pipeline first
    base = run_mvp_pipeline_with_context(seed_path, output_dir)

    project = base["project"]

    # Rename output files to Phase 5 naming convention
    json_path = os.path.join(output_dir, "mvp_algorithm_project_with_materials_full.json")
    report_path = os.path.join(output_dir, "mvp_algorithm_report_with_materials.md")
    materials_path = os.path.join(output_dir, "mvp_algorithm_materials.md")

    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(project, f, ensure_ascii=False, indent=2)

    # Save report
    from tools.export_package import export_markdown_report
    export_markdown_report(project, report_path)

    # Save materials
    _export_materials_markdown(project, materials_path)

    return {
        "project": project,
        "project_path": json_path,
        "report_path": report_path,
        "materials_path": materials_path,
        "quality_check": project.get("quality_check", {}),
        "material_alignment": project.get("material_alignment", {}),
    }


def run_mvp_export_package(
    project: dict, output_dir: str = "exports"
) -> dict:
    """
    Run Phase 6 formal file exports from an existing project.
    Generates Word and Excel files plus export index.

    Returns dict with file paths and sizes.
    """
    from tools.document_exporter import export_all

    os.makedirs(output_dir, exist_ok=True)
    return export_all(project, output_dir)


# ======================================================================
# Context-analysis normalization
# ======================================================================

def _normalize_context_analysis(
    learner: dict,
    learning: dict,
    performance: dict,
    implications: dict,
    lctx: dict,
) -> dict:
    """
    Flatten the nested learner_context outputs into the ``context_analysis``
    dict expected by ``report_renderer`` and ``alignment_checker``.

    The three ``analyze_*`` functions return deeply nested dicts (e.g.
    ``learner["entry_skills"]["items"]``).  This function unwraps them
    into the flat / semi-flat structure the downstream consumers expect.
    """

    # --- learner profile (flatten nested sub-dicts) --------------------
    entry_skills_raw = learner.get("entry_skills", {})
    entry_skills = (
        entry_skills_raw.get("items", [])
        if isinstance(entry_skills_raw, dict)
        else entry_skills_raw if isinstance(entry_skills_raw, list)
        else []
    )

    def _desc(obj, key="description"):
        if isinstance(obj, dict):
            return obj.get(key, "")
        return str(obj) if obj else ""

    prior_knowledge = _desc(learner.get("prior_knowledge", {}))
    motivation = _desc(learner.get("motivation", {}))
    ability_level = _desc(learner.get("ability_level", {}))
    attitude_content = _desc(learner.get("attitude_content", {}))
    attitude_delivery = _desc(learner.get("attitude_delivery", {}))

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

    common_difficulties = learner.get("common_difficulties", [])

    # --- learning context (flatten nested sub-dicts) -------------------
    devices_raw = learning.get("devices", {})
    devices = _desc(devices_raw) if isinstance(devices_raw, dict) else str(devices_raw) if devices_raw else ""

    network_raw = learning.get("network", {})
    network = _desc(network_raw) if isinstance(network_raw, dict) else str(network_raw) if network_raw else ""

    # --- performance context -------------------------------------------
    transfer_risks = performance.get("transfer_risks", [])
    real_world_tasks = performance.get("real_world_tasks", [])

    # --- implications --------------------------------------------------
    strategy_implications = implications.get("strategy_implications", [])

    # Also build a flat "implications" list of strings for the
    # alignment_checker which expects plain strings.
    flat_implications = []
    for imp in strategy_implications:
        if isinstance(imp, dict):
            flat_implications.append(imp.get("implication", str(imp)))
        else:
            flat_implications.append(str(imp))

    return {
        # 8.1 Learner profile
        "learner_profile": {
            "entry_skills": entry_skills,
            "prior_knowledge": prior_knowledge,
            "attitude_toward_content": attitude_content,
            "attitude_toward_delivery": attitude_delivery,
            "motivation": motivation,
            "ability_level": ability_level,
            "learning_preferences": learning_preferences,
            "group_characteristics": group_characteristics,
            "common_difficulties": common_difficulties,
        },
        # 8.2 Learning context
        "learning_context": {
            "class_duration": learning.get("class_duration", lctx.get("class_duration", 45)),
            "class_size": learning.get("class_size", lctx.get("class_size", "")),
            "available_media": learning.get("available_media", []),
            "devices": devices,
            "network": network,
            "classroom_layout": learning.get("classroom_layout", lctx.get("classroom_layout", "")),
            "constraints": learning.get("constraints", []),
            "supports": learning.get("supports", []),
        },
        # 8.3 Performance context
        "performance_context": {
            "use_environment": performance.get("use_environment", lctx.get("use_environment", "")),
            "expected_transfer": performance.get("expected_transfer", lctx.get("expected_transfer", "")),
            "real_world_tasks": real_world_tasks,
            "similarity_to_learning_context": performance.get("similarity_to_learning_context", ""),
            "transfer_risks": transfer_risks,
        },
        # 8.4 Strategy implications
        "strategy_implications": strategy_implications,
        # Top-level aliases consumed by alignment_checker
        "implications": flat_implications,
        "common_difficulties": common_difficulties,
        "class_duration": learning.get("class_duration", lctx.get("class_duration", 45)),
        "device_constraints": devices_raw if isinstance(devices_raw, dict) else {},
        # Completeness metadata
        "data_completeness": implications.get("data_completeness", 0),
        "requires_teacher_confirmation": implications.get("requires_teacher_confirmation", True),
    }


# ======================================================================
# Strategy normalization
# ======================================================================

def _normalize_strategy(raw_strategy: dict, project: dict) -> dict:
    """
    Bridge ``strategy_engine`` output to the field structure expected by
    ``report_renderer`` and ``alignment_checker``.

    strategy_engine produces:
      - ``components`` (dict of 5 component sub-dicts)
      - ``lesson_flow`` (list with Chinese keys)
      - ``time_allocation``, ``objective_sequencing``, ``lesson_segments``

    report_renderer / alignment_checker expect:
      - ``learning_components`` (list of 5 component dicts)
      - ``lesson_flow`` with keys "时间", "活动", "学习成分", etc.
      - ``addressed_implications``, ``media_plan``, etc.
    """
    components = raw_strategy.get("components", {})
    lesson_flow = raw_strategy.get("lesson_flow", [])
    time_alloc = raw_strategy.get("time_allocation", {})
    segments = raw_strategy.get("lesson_segments", {}).get("segments", [])

    # --- Build learning_components list --------------------------------
    learning_components = _build_learning_components(components, segments)

    # --- Transform lesson_flow keys ------------------------------------
    transformed_flow = _transform_lesson_flow(lesson_flow)

    # --- Collect covered objective IDs ---------------------------------
    covered_ids: set[str] = set()
    for comp in learning_components:
        for oid in comp.get("linked_objectives", []):
            if oid:
                covered_ids.add(oid)

    # --- Assessment IDs -----------------------------------------------
    assess_comp = components.get("assessment", {})
    assessment_ids = [
        a.get("type", "")
        for a in assess_comp.get("assessments", [])
        if a.get("type")
    ]

    # --- Addressed context implications (deduplicated) --------------------
    context_analysis = project.get("context_analysis", {})
    ctx_implications = context_analysis.get("strategy_implications", [])
    addressed: list[str] = []
    seen_imps: set[str] = set()
    for imp in ctx_implications:
        txt = imp.get("implication", "") if isinstance(imp, dict) else str(imp)
        if txt and len(txt) > 5:
            # Deduplicate by first 40 chars
            key = txt[:40]
            if key not in seen_imps:
                seen_imps.add(key)
                addressed.append(txt[:80])

    # --- Media from learner context ------------------------------------
    lctx = project.get("learner_context_input", {})
    media = lctx.get("available_media", [])

    # --- Quality check from strategy engine ----------------------------
    quality = raw_strategy.get("quality_check", {})
    summary = raw_strategy.get("summary", "")
    duration = time_alloc.get("total", raw_strategy.get("class_duration", 45))

    return {
        "strategy_id": raw_strategy.get("strategy_id", ""),
        "topic": raw_strategy.get("topic", "general"),
        "learning_type": raw_strategy.get("learning_type", ""),
        "lesson_duration": duration,
        "total_duration": f"{duration}分钟",
        "total_duration_minutes": duration,
        "objective_sequence": raw_strategy.get("objective_sequencing", {}),
        "segments": segments,
        "pre_instructional_activities": components.get("pre_instructional", {}),
        "content_presentation": components.get("content_presentation", {}),
        "learner_participation": components.get("learner_participation", {}),
        "assessment_strategy": assess_comp,
        "follow_through_activities": components.get("follow_through", {}),
        "media_and_delivery": {
            "media": media,
            "grouping": "小组协作",
            "delivery_constraints": [],
        },
        "media_plan": {
            "devices": [{"name": m, "description": m} for m in media] if media else [],
            "resources": [],
        },
        "lesson_flow": transformed_flow,
        "covered_objective_ids": list(covered_ids),
        "embedded_assessment_ids": assessment_ids,
        "responded_context_implications": addressed[:5],
        "learning_components": learning_components,
        "addressed_implications": addressed,
        "anticipated_difficulties": lctx.get("common_difficulties", []),
        "summary": summary,
        "overview": summary,
        "quality_check": quality,
        "requires_teacher_confirmation": not quality.get("overall_passed", False),
    }


# ======================================================================
# Materials export
# ======================================================================

def _render_mat_content(content: dict, indent: int = 0) -> list[str]:
    """Recursively render a material's content dict into markdown lines."""
    lines = []
    if not isinstance(content, dict):
        if isinstance(content, str) and content.strip():
            lines.append(content)
        return lines

    for key, val in content.items():
        if not key:
            continue

        prefix = "  " * indent

        if isinstance(val, str) and val.strip():
            lines.append(f"{prefix}**{key}：**")
            lines.append(f"{prefix}{val}")

        elif isinstance(val, list) and val:
            lines.append(f"{prefix}**{key}：**")
            for item in val:
                if isinstance(item, str) and item.strip():
                    lines.append(f"{prefix}- {item}")
                elif isinstance(item, dict):
                    sub = _render_dict_item(item, indent + 1)
                    lines.extend(sub)

        elif isinstance(val, dict) and val:
            lines.append(f"{prefix}**{key}：**")
            sub = _render_mat_content(val, indent + 1)
            lines.extend(sub)

    return lines


def _render_dict_item(item: dict, indent: int = 0) -> list[str]:
    """Render a single dict item from a list into readable markdown."""
    lines = []
    prefix = "  " * indent

    # Objective dict
    if "behavior" in item and ("objective_id" in item or "related_skill_id" in item):
        behavior = item.get("behavior", "")
        condition = item.get("condition", "")
        criterion = item.get("criterion", "")
        if behavior:
            line = f"{prefix}- {behavior}"
            if condition:
                short = condition[:50] + "..." if len(condition) > 50 else condition
                line += f"（条件：{short}）"
            if criterion:
                short = criterion[:40] + "..." if len(criterion) > 40 else criterion
                line += f"【标准：{short}】"
            lines.append(line)
        return lines

    # Flow step dict
    if "环节" in item or "教师行动" in item:
        parts = []
        for k in ["环节", "时间", "教师行动", "教师话术", "追问与反馈", "时间控制"]:
            if k in item and item[k]:
                v = str(item[k])
                if len(v) > 60:
                    v = v[:60] + "..."
                parts.append(f"{k}: {v}")
        if parts:
            lines.append(f"- {' | '.join(parts)}")
        return lines

    # Scoring criteria
    if "维度" in item or ("标准" in item and "分值" in item):
        dim = item.get("维度", item.get("标准", ""))
        score = item.get("分值", item.get("score", ""))
        desc = item.get("描述", item.get("说明", ""))
        line = f"- {dim}"
        if score:
            line += f"（{score}分）"
        if desc:
            line += f"：{desc}"
        lines.append(line)
        return lines

    # Peer review item
    if "检查项" in item or "check" in item:
        check = item.get("检查项", item.get("check", ""))
        scale = item.get("评分", item.get("scale", ""))
        lines.append(f"- {check}" + (f"（{scale}）" if scale else ""))
        return lines

    # Generic dict - render all string values
    parts = []
    for k2, v2 in item.items():
        if isinstance(v2, str) and v2.strip():
            parts.append(f"{k2}: {v2}")
    if parts:
        lines.append(f"- {' | '.join(parts)}")
    return lines


def _export_materials_markdown(project: dict, output_path: str) -> None:
    """Export instructional materials as a standalone Markdown file with real content."""
    materials = project.get("instructional_materials", {})
    if not materials:
        return

    lines = ["# 教学材料包\n"]
    lines.append("> 本文件包含可直接用于课堂实施的教学材料\n")

    # Section mapping: material_key -> section_title
    section_map = [
        ("teacher_guide", "教师授课手册"),
        ("student_worksheet", "学生学习单"),
        ("entry_test_sheet", "入门技能测试单"),
        ("pretest_sheet", "前测任务单"),
        ("group_task_sheet", "小组任务单"),
        ("peer_review_checklist", "互评检查表"),
        ("posttest_sheet", "后测任务单"),
        ("board_design", "板书设计"),
        ("simple_lesson_plan", "简版课堂教案"),
    ]

    for mat_key, section_title in section_map:
        mat = materials.get(mat_key, {})
        if not mat:
            continue

        lines.append(f"\n## {section_title}\n")

        # Extract content - materials may be wrapped with "content" key
        content = mat.get("content", mat)

        # Render the content
        content_lines = _render_mat_content(content)
        if content_lines:
            lines.extend(content_lines)
            lines.append("")
        else:
            lines.append("（材料内容待补充）\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

# ======================================================================
# Lesson flow enrichment
# ======================================================================

def _enrich_lesson_flow(project: dict) -> None:
    """
    Add objective_ids to each lesson_flow segment and normalize time fields.
    Mutates project["instructional_strategy"]["lesson_flow"] in place.
    """
    strategy = project.get("instructional_strategy", {})
    flow = strategy.get("lesson_flow", [])
    objectives = project.get("objectives", [])
    assessment = project.get("assessment_plan", {})

    # Build objective lookup by behavior keywords
    obj_keywords: dict[str, list[str]] = {}
    for obj in objectives:
        oid = obj.get("objective_id", "")
        behavior = obj.get("behavior", "")
        if oid and behavior:
            # Extract 2-char chunks as keywords
            kws = [behavior[i:i+2] for i in range(0, max(0, len(behavior)-1), 2)
                   if behavior[i:i+2].strip()]
            obj_keywords[oid] = kws

    # Activity -> objective mapping rules for algorithm topic
    activity_obj_map = {
        "情境导入": [],  # global
        "学习目标": [],  # global
        "入门技能": ["entry"],  # entry skills
        "对比导入": [],  # comparison
        "前测": ["pretest"],
        "概念讲解": [],  # concept
        "范例演示": [],  # demo
        "小组任务": [],  # practice
        "互评修改": [],  # peer review
        "总结性评价": ["posttest"],
        "后测": ["posttest"],
        "记忆支持": [],  # follow-through
        "迁移": [],  # follow-through
    }

    for seg in flow:
        activity_text = seg.get("活动", seg.get("具体活动", ""))
        component = seg.get("学习成分", seg.get("教学环节", ""))

        # Find matching objectives by keyword overlap
        matched_objs: list[str] = []
        for oid, kws in obj_keywords.items():
            for kw in kws:
                if kw and kw in activity_text:
                    matched_objs.append(oid)
                    break

        # If no keyword match, assign based on component type
        if not matched_objs:
            if "教学前" in component or "pre" in component.lower():
                matched_objs = ["全局目标"]
            elif "内容呈现" in component or "presentation" in component.lower():
                matched_objs = ["o1", "o2"]  # first two objectives
            elif "学习者参与" in component or "participation" in component.lower():
                matched_objs = [o.get("objective_id", "") for o in objectives[:3]]
            elif "评估" in component or "assessment" in component.lower():
                matched_objs = ["后测目标"]
            elif "总结" in component or "follow" in component.lower():
                matched_objs = ["全局目标"]

        # Remove empty strings
        matched_objs = [o for o in matched_objs if o]
        if not matched_objs:
            matched_objs = ["全局目标"]

        seg["objective_ids"] = matched_objs

        # Normalize time field
        if "时间（分钟）" not in seg and "duration_minutes" in seg:
            seg["时间（分钟）"] = seg["duration_minutes"]

    # Deduplicate strategy_implications
    context_analysis = project.get("context_analysis", {})
    imps = context_analysis.get("strategy_implications", [])
    if imps:
        seen = set()
        deduped = []
        for imp in imps:
            txt = imp.get("implication", "") if isinstance(imp, dict) else str(imp)
            key = txt[:40] if txt else ""
            if key and key not in seen:
                seen.add(key)
                deduped.append(imp)
        context_analysis["strategy_implications"] = deduped


def _recalculate_strategy_quality(project: dict) -> None:
    """
    Recalculate strategy quality_check based on normalized data.
    """
    strategy = project.get("instructional_strategy", {})
    objectives = project.get("objectives", [])
    flow = strategy.get("lesson_flow", [])

    # Check five components
    flow_stages = set()
    for seg in flow:
        comp = seg.get("学习成分", seg.get("教学环节", ""))
        if comp:
            flow_stages.add(comp)

    stage_mapping = {
        "教学前活动": "pre_instructional",
        "内容呈现": "content_presentation",
        "学习者参与": "learner_participation",
        "评估": "assessment",
        "总结与迁移": "follow_through",
    }
    covered_comps = set()
    for stage_name, comp_name in stage_mapping.items():
        if stage_name in flow_stages:
            covered_comps.add(comp_name)

    missing_comps = {"pre_instructional", "content_presentation",
                     "learner_participation", "assessment", "follow_through"} - covered_comps

    # Check target coverage
    covered_ids = set(strategy.get("covered_objective_ids", []))
    all_obj_ids = [o.get("objective_id", "") for o in objectives if o.get("objective_id")]
    uncovered_ids = [oid for oid in all_obj_ids if oid and oid not in covered_ids]

    # Check time allocation
    total_time = 0
    for seg in flow:
        dur = seg.get("时间（分钟）", seg.get("duration_minutes", 0))
        if isinstance(dur, (int, float)):
            total_time += dur

    # Build quality_check
    checks = {
        "five_components": {
            "name": "五个教学活动成分",
            "passed": len(missing_comps) == 0,
            "covered": list(covered_comps),
            "missing": list(missing_comps),
        },
        "target_coverage": {
            "name": "目标覆盖",
            "passed": len(uncovered_ids) == 0,
            "total_objectives": len(objectives),
            "uncovered": uncovered_ids,
        },
        "time_allocation": {
            "name": "时间分配合理性",
            "passed": 44 <= total_time <= 46,
            "planned": strategy.get("lesson_duration", 45),
            "actual": total_time,
            "difference": abs(total_time - strategy.get("lesson_duration", 45)),
        },
    }

    passed_count = sum(1 for c in checks.values() if c.get("passed"))
    total_checks = len(checks)
    score = round(passed_count / total_checks * 100) if total_checks > 0 else 0

    strategy["quality_check"] = {
        "checks": checks,
        "overall_score": score,
        "overall_passed": passed_count == total_checks,
        "total_checks": total_checks,
        "passed_checks": passed_count,
    }

    # Regenerate summary with updated quality
    topic = strategy.get("topic", "generic")
    n_obj = len(project.get("objectives", []))
    topic_name = "算法" if topic == "algorithm" else topic
    duration = strategy.get("lesson_duration", 45)

    summary = (
        f"本节课为{duration}分钟的{topic_name}主题教学设计，"
        f"包含{n_obj}个教学目标。"
        f"策略涵盖五项教学活动（教学前活动、内容呈现、学习者参与、评估、总结与迁移），"
        f"质量检查得分{score}分。"
    )
    if not passed_count == total_checks:
        failed = [
            c["name"]
            for c in checks.values()
            if not c.get("passed")
        ]
        if failed:
            summary += f"以下方面需改进：{'、'.join(failed)}。"
    strategy["summary"] = summary
    strategy["overview"] = summary


# ======================================================================
# Learning-components builder
# ======================================================================

def _build_learning_components(components: dict, segments: list) -> list:
    """
    Build the ``learning_components`` list (5 entries) from the
    strategy_engine ``components`` dict and ``lesson_segments``.
    """
    result: list[dict] = []

    # 1. Pre-instructional ------------------------------------------------
    pre = components.get("pre_instructional", {})
    pre_desc = _extract_pre_description(pre)
    result.append({
        "type": "pre_instructional",
        "name": "教学前活动",
        "description": pre_desc,
        "linked_objectives": [],
        "duration": f"{pre.get('total_duration_minutes', 5)}分钟",
        "teacher_activity": "提问、引导、展示目标",
        "learner_activity": "思考、回答、了解学习目标",
    })

    # 2. Content presentation ---------------------------------------------
    pres = components.get("content_presentation", {})
    pres_phases = pres.get("phases", [])
    pres_desc = "；".join(
        f"{p.get('phase', '')}: {p.get('activity', '')}" for p in pres_phases
    )
    pres_dur = sum(p.get("duration_minutes", 0) for p in pres_phases)
    pres_objs = _segment_objective_ids(segments, "content_presentation")
    result.append({
        "type": "content_presentation",
        "name": "内容呈现",
        "description": pres_desc or "概念讲解与范例演示",
        "linked_objectives": pres_objs,
        "duration": f"{pres_dur}分钟",
        "teacher_activity": "讲解、演示、引导",
        "learner_activity": "观察、思考、记录",
        "media": pres_phases[0].get("media", []) if pres_phases else [],
    })

    # 3. Learner participation --------------------------------------------
    part = components.get("learner_participation", {})
    part_phases = part.get("phases", [])
    part_desc = "；".join(
        f"{p.get('phase', '')}: {p.get('activity', '')}" for p in part_phases
    )
    part_dur = sum(p.get("duration_minutes", 0) for p in part_phases)
    part_objs = _segment_objective_ids(segments, "learner_participation")
    result.append({
        "type": "learner_participation",
        "name": "学习者参与",
        "description": part_desc or "练习与反馈",
        "linked_objectives": part_objs,
        "duration": f"{part_dur}分钟",
        "teacher_activity": "巡视、指导、收集反馈",
        "learner_activity": "练习、讨论、合作",
    })

    # 4. Assessment -------------------------------------------------------
    assess = components.get("assessment", {})
    assess_items = assess.get("assessments", [])
    assess_desc = "；".join(
        f"{_assess_label(a.get('type', ''))}: {a.get('activity', '')}"
        for a in assess_items
    )
    result.append({
        "type": "assessment",
        "name": "评估",
        "description": assess_desc or "入门测试、前测、形成性评价、后测",
        "linked_objectives": [],
        "duration": f"{assess.get('total_assessment_minutes', 7)}分钟",
        "teacher_activity": "组织测试、收集作品、给予反馈",
        "learner_activity": "完成测试、提交作品",
        "embedded_assessments": [a.get("type", "") for a in assess_items],
    })

    # 5. Follow-through ---------------------------------------------------
    follow = components.get("follow_through", {})
    follow_parts = follow.get("memory_support", []) + follow.get("transfer_tasks", [])
    follow_desc = "；".join(str(a) for a in follow_parts[:3])
    result.append({
        "type": "follow_through",
        "name": "总结与迁移",
        "description": follow_desc or "记忆支持与迁移任务",
        "linked_objectives": [],
        "duration": f"{follow.get('total_duration_minutes', 4)}分钟",
        "teacher_activity": "总结要点、布置任务",
        "learner_activity": "回顾总结、记录作业",
    })

    return result


# ======================================================================
# Lesson-flow transformation
# ======================================================================

def _transform_lesson_flow(lesson_flow: list) -> list:
    """
    Remap strategy_engine lesson_flow keys to the names expected by
    ``report_renderer``.

    Engine keys:  "时间（分钟）", "教学环节", "具体活动",
                  "教师行为", "学生行为", "评估方式", "媒体/材料"
    Renderer keys: "时间", "活动", "对应目标", "学习成分", "备注"
    """
    transformed: list[dict] = []
    for step in lesson_flow:
        # Time
        time_val = step.get("时间（分钟）", step.get("时间", step.get("time", "")))
        time_display = step.get("时间段", "")
        if time_display:
            time_str = time_display
        elif isinstance(time_val, (int, float)):
            time_str = f"{time_val}分钟"
        else:
            time_str = str(time_val)

        # Activity
        activity = step.get(
            "具体活动",
            step.get("活动", step.get("activity", step.get("description", ""))),
        )

        # Component / learning stage
        comp_type = step.get(
            "教学环节",
            step.get("学习成分", step.get("component", "")),
        )

        # Objectives (may not exist in raw data)
        obj_ref = step.get(
            "对应目标",
            step.get("linked_objectives", step.get("objectives", "")),
        )
        if isinstance(obj_ref, list):
            obj_ref = ", ".join(str(o) for o in obj_ref)

        # Notes / assessment
        notes = step.get(
            "备注",
            step.get("notes", step.get("评估方式", step.get("remark", ""))),
        )

        teacher = step.get("教师行为", "")
        student = step.get("学生行为", "")

        transformed.append({
            # --- keys the report_renderer tries first ---
            "时间": time_str,
            "活动": activity,
            "对应目标": obj_ref,
            "学习成分": comp_type,
            "备注": notes,
            # --- original engine keys (kept for backward compat) ---
            "教师行为": teacher,
            "学生行为": student,
            "时间段": time_display,
            "教学环节": comp_type,
            "具体活动": activity,
            "评估方式": notes,
            "媒体/材料": step.get("媒体/材料", step.get("媒体/材料", "")),
            "时间（分钟）": time_val,
        })

    return transformed


# ======================================================================
# Small helpers
# ======================================================================

def _extract_pre_description(pre: dict) -> str:
    """Combine pre-instructional sub-activities into one description."""
    parts: list[str] = []

    motivation = pre.get("motivation", {})
    if isinstance(motivation, dict):
        for s in motivation.get("strategies", []):
            if isinstance(s, dict) and s.get("activity"):
                parts.append(s["activity"])

    obj = pre.get("objectives_overview", {})
    if isinstance(obj, dict) and obj.get("activity"):
        parts.append(obj["activity"])

    entry = pre.get("entry_skill_activation", {})
    if isinstance(entry, dict) and entry.get("activity"):
        parts.append(entry["activity"])

    return "；".join(parts) if parts else "动机激发、目标呈现、入门技能检测"


def _segment_objective_ids(segments: list, name: str) -> list[str]:
    """Extract objective IDs from a named lesson segment."""
    ids: list[str] = []
    for seg in segments:
        if seg.get("name") == name:
            for obj in seg.get("objectives", []):
                if isinstance(obj, dict):
                    oid = obj.get("objective_id", obj.get("id", ""))
                    if oid:
                        ids.append(oid)
                elif isinstance(obj, str) and obj:
                    ids.append(obj)
    return ids


def _assess_label(assess_type: str) -> str:
    """Map an assessment type key to its Chinese label."""
    return {
        "entry_behavior_test": "入门技能测试",
        "pretest": "前测",
        "practice": "形成性评价",
        "posttest": "后测",
    }.get(assess_type, assess_type)


# ======================================================================
# CLI entry point
# ======================================================================

if __name__ == "__main__":
    import sys as _sys

    seed = (
        _sys.argv[1]
        if len(_sys.argv) > 1
        else "../examples/mvp_algorithm_seed_with_context.json"
    )
    result = run_mvp_pipeline_with_context(seed)
    print(
        json.dumps(
            {
                "project_path": result["project_path"],
                "report_path": result["report_path"],
                "quality_score": result["quality_check"].get("score", 0),
                "quality_status": result["quality_check"].get("overall_status", ""),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
