#!/usr/bin/env python
"""Phase 9 Dogfood: Real end-to-end teacher workflow verification."""
import sys, os, json, asyncio

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mcp-server'))

from server import call_tool


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _safe_call(tool_name, args):
    """Call MCP tool and record the actual call."""
    result_text = _run(call_tool(tool_name, args))
    result = json.loads(result_text[0].text)
    return result


def run_dogfood():
    output_dir = "exports/phase9"
    os.makedirs(output_dir, exist_ok=True)

    actual_tool_calls = []
    all_warnings = []
    failed_steps = []
    results = {}

    def record_call(tool_name, step_name):
        actual_tool_calls.append({"tool": tool_name, "step": step_name})

    # Step 1: dc_design_session (insufficient sources)
    print("Step 1: dc_design_session (insufficient sources)...")
    try:
        with open("examples/phase9/k12_design_insufficient_sources.json", "r", encoding="utf-8") as f:
            design_input = json.load(f)
        design_input["output_dir"] = output_dir
        record_call("dc_design_session", "design_insufficient_sources")
        design_result = _safe_call("dc_design_session", design_input)
        with open(os.path.join(output_dir, "phase9_design_result.json"), "w", encoding="utf-8") as f:
            json.dump(design_result, f, ensure_ascii=False, indent=2, default=str)
        results["design"] = design_result
        all_warnings.extend(design_result.get("warnings", []))
        print(f"  Status: {design_result.get('status')}")
    except Exception as e:
        failed_steps.append({"step": "dc_design_session", "error": str(e)})
        results["design"] = {"status": "error", "error": str(e)}

    # Step 2: dc_design_session (teacher sources)
    print("Step 2: dc_design_session (teacher sources)...")
    try:
        with open("examples/phase9/k12_design_with_teacher_sources.json", "r", encoding="utf-8") as f:
            ts_input = json.load(f)
        ts_input["output_dir"] = output_dir
        record_call("dc_design_session", "design_teacher_sources")
        ts_result = _safe_call("dc_design_session", ts_input)
        with open(os.path.join(output_dir, "phase9_teacher_source_design_result.json"), "w", encoding="utf-8") as f:
            json.dump(ts_result, f, ensure_ascii=False, indent=2, default=str)
        results["teacher_source_design"] = ts_result
        all_warnings.extend(ts_result.get("warnings", []))
        print(f"  Status: {ts_result.get('status')}")
    except Exception as e:
        failed_steps.append({"step": "dc_design_session_teacher_source", "error": str(e)})
        results["teacher_source_design"] = {"status": "error", "error": str(e)}

    # Step 3: dc_review_session
    print("Step 3: dc_review_session...")
    design_project_path = results.get("design", {}).get("export_result", {}).get("project_json", "")
    if design_project_path and os.path.exists(design_project_path):
        try:
            record_call("dc_review_session", "review_design")
            review_result = _safe_call("dc_review_session", {
                "existing_design_project_path": design_project_path,
                "output_dir": output_dir,
            })
            with open(os.path.join(output_dir, "phase9_review_result.json"), "w", encoding="utf-8") as f:
                json.dump(review_result, f, ensure_ascii=False, indent=2, default=str)
            results["review"] = review_result
            all_warnings.extend(review_result.get("warnings", []))
            print(f"  Status: {review_result.get('status')}")
        except Exception as e:
            failed_steps.append({"step": "dc_review_session", "error": str(e)})
            results["review"] = {"status": "error", "error": str(e)}
    else:
        failed_steps.append({"step": "dc_review_session", "error": "No valid project_path"})
        results["review"] = {"status": "skipped"}

    # Step 4: dc_revise_session
    print("Step 4: dc_revise_session...")
    if design_project_path and os.path.exists(design_project_path):
        try:
            with open("examples/phase9/revise_from_teacher_feedback.json", "r", encoding="utf-8") as f:
                revise_input = json.load(f)
            revise_input["existing_design_project_path"] = design_project_path
            revise_input["output_dir"] = output_dir
            record_call("dc_revise_session", "revise_feedback")
            revise_result = _safe_call("dc_revise_session", revise_input)
            with open(os.path.join(output_dir, "phase9_revise_result.json"), "w", encoding="utf-8") as f:
                json.dump(revise_result, f, ensure_ascii=False, indent=2, default=str)
            results["revise"] = revise_result
            all_warnings.extend(revise_result.get("warnings", []))
            print(f"  Status: {revise_result.get('status')}")
        except Exception as e:
            failed_steps.append({"step": "dc_revise_session", "error": str(e)})
            results["revise"] = {"status": "error", "error": str(e)}
    else:
        failed_steps.append({"step": "dc_revise_session", "error": "No valid project_path"})
        results["revise"] = {"status": "skipped"}

    # Step 5: dc_export_package
    print("Step 5: dc_export_package...")
    if design_project_path and os.path.exists(design_project_path):
        try:
            record_call("dc_export_package", "export_package")
            export_result = _safe_call("dc_export_package", {
                "project_path": design_project_path,
                "output_dir": output_dir,
            })
            with open(os.path.join(output_dir, "phase9_export_result.json"), "w", encoding="utf-8") as f:
                json.dump(export_result, f, ensure_ascii=False, indent=2, default=str)
            results["export"] = export_result
            all_warnings.extend(export_result.get("warnings", []))
            print(f"  Status: {export_result.get('export_status')}")
        except Exception as e:
            failed_steps.append({"step": "dc_export_package", "error": str(e)})
            results["export"] = {"status": "error", "error": str(e)}
    else:
        failed_steps.append({"step": "dc_export_package", "error": "No valid project_path"})
        results["export"] = {"status": "skipped"}

    # Generate summary
    design_status = results.get("design", {}).get("status", "unknown")
    review_status = results.get("review", {}).get("status", "unknown")
    revise_status = results.get("revise", {}).get("status", "unknown")
    export_status = results.get("export", {}).get("export_status", "unknown")
    ts_status = results.get("teacher_source_design", {}).get("status", "unknown")
    can_final = results.get("design", {}).get("can_export_final", False)
    required_confs = len(results.get("design", {}).get("required_confirmations", []))
    blocking = len(results.get("design", {}).get("final_blocking_reasons", []))

    # Check teacher source recording - only count teacher_private sources
    ts_project = results.get("teacher_source_design", {}).get("project", {})
    ts_sources = ts_project.get("sources", [])
    teacher_sources = [
        s for s in ts_sources
        if s.get("source_category") == "teacher_private"
        or s.get("retrieval_status") in ("user_uploaded", "user_provided")
        or s.get("source_id", "").startswith("teacher_doc_")
    ]
    teacher_sources_count = len(teacher_sources)
    teacher_official_count = sum(
        1 for s in teacher_sources
        if s.get("source_level", "") in ("A1", "S", "official")
        or s.get("source_category") == "official_authority"
        or s.get("can_be_goal_basis") == "yes"
    )

    # Build generated_files list
    generated_files = [f for f in os.listdir(output_dir)
                      if f.endswith(('.json', '.md', '.docx', '.xlsx'))]

    summary = {
        "run_status": "completed" if not failed_steps else "completed_with_errors",
        "actual_tool_calls": actual_tool_calls,
        "public_tools_called": list(set(c["tool"] for c in actual_tool_calls)),
        "design_status": design_status,
        "teacher_source_design_status": ts_status,
        "review_status": review_status,
        "revise_status": revise_status,
        "export_status": export_status,
        "can_export_final": can_final,
        "required_confirmations_count": required_confs,
        "final_blocking_reasons_count": blocking,
        "teacher_sources_recorded_count": teacher_sources_count,
        "teacher_sources_marked_official_count": teacher_official_count,
        "teacher_source_can_export_final": results.get("teacher_source_design", {}).get("can_export_final", False),
        "teacher_source_records": [
            {
                "source_id": s.get("source_id", ""),
                "source_name": s.get("source_name", ""),
                "source_level": s.get("source_level", ""),
                "source_category": s.get("source_category", ""),
                "can_be_goal_basis": s.get("can_be_goal_basis", ""),
                "retrieval_status": s.get("retrieval_status", ""),
            }
            for s in teacher_sources
        ],
        "generated_files": generated_files,
        "warnings": all_warnings,
        "failed_steps": failed_steps,
    }

    # Write summary first, then refresh generated_files to include it
    summary_path = os.path.join(output_dir, "phase9_dogfood_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Refresh generated_files to include summary
    summary["generated_files"] = [f for f in os.listdir(output_dir)
                                   if f.endswith(('.json', '.md', '.docx', '.xlsx'))]
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\nDogfood complete. Status: {summary['run_status']}")
    print(f"Failed steps: {len(failed_steps)}")
    print(f"Teacher sources recorded: {teacher_sources_count}")
    print(f"Tool calls: {len(actual_tool_calls)}")
    return summary


if __name__ == "__main__":
    run_dogfood()
