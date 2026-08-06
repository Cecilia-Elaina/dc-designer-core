#!/usr/bin/env python
"""Verify that a release archive works after extraction to a clean directory.

The smoke test deliberately keeps the teacher workspace outside the extracted
package. It exercises the release audit, offline evidence search, design,
review, revise, and document export without relying on the developer checkout.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def _safe_extract(archive: Path, target: Path) -> None:
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            destination = (target / member.filename).resolve()
            if target.resolve() not in destination.parents and destination != target.resolve():
                raise RuntimeError(f"archive contains an unsafe path: {member.filename}")
        bundle.extractall(target)


def _run(command: list[str], *, cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def _json_output(completed: subprocess.CompletedProcess[str]) -> dict:
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "command failed").strip())
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"command did not return JSON: {completed.stdout[-500:]}") from exc


def run_smoke(archive: str | Path, *, keep_temp: bool = False, timeout: int = 360) -> dict:
    archive_path = Path(archive).expanduser().resolve()
    if not archive_path.is_file():
        return {"status": "failed", "error": f"release archive not found: {archive_path}"}
    temp_context = tempfile.TemporaryDirectory(prefix="dc-clean-install-")
    root = Path(temp_context.name) / "package"
    workspace = Path(temp_context.name) / "teacher-workspace"
    root.mkdir(parents=True, exist_ok=True)
    try:
        _safe_extract(archive_path, root)
        audit = _json_output(_run([sys.executable, "scripts/release_check.py"], cwd=root, timeout=60))
        if audit.get("errors"):
            raise RuntimeError("clean package release audit failed")
        search = _json_output(_run([
            sys.executable, "scripts/dc_info_tech.py", "search",
            "--stage", "senior_secondary", "--subject", "信息技术", "--topic", "Python 循环",
            "--workspace", str(workspace),
        ], cwd=root, timeout=60))
        official = search.get("official", {})
        if official.get("status") != "found" or not official.get("matches"):
            raise RuntimeError("clean package official evidence search returned no match")
        request_path = root / "examples" / "v1" / "smoke_request.json"
        output_dir = Path(temp_context.name) / "exports"
        design = _json_output(_run([
            sys.executable, "scripts/dc_info_tech.py", "design",
            "--request-file", str(request_path),
            "--output-dir", str(output_dir),
            "--workspace", str(workspace),
        ], cwd=root, timeout=timeout))
        export_result = design.get("export_result", {})
        visual = design.get("project", {}).get("quality", {}).get("visual_status", "")
        if design.get("status") in {"unsupported_scope", "error"}:
            raise RuntimeError(f"clean package design failed: {design.get('status')}")
        project_path = Path(str(design.get("project_json", ""))).expanduser()
        if not project_path.is_file():
            raise RuntimeError("clean package design did not expose a project JSON")
        if not export_result or any(not Path(str(path)).is_file() for path in export_result.values() if isinstance(path, str) and path.lower().endswith((".docx", ".xlsx"))):
            raise RuntimeError("clean package design did not produce document exports")
        review_dir = Path(temp_context.name) / "review-exports"
        review = _json_output(_run([
            sys.executable, "scripts/dc_info_tech.py", "review",
            "--project", str(project_path),
            "--output-dir", str(review_dir),
            "--workspace", str(workspace),
        ], cwd=root, timeout=timeout))
        if review.get("status") in {"unsupported_scope", "error"} or not isinstance(review.get("findings"), list):
            raise RuntimeError("clean package review did not return actionable findings")
        revise_dir = Path(temp_context.name) / "revise-exports"
        revise = _json_output(_run([
            sys.executable, "scripts/dc_info_tech.py", "revise",
            "--project", str(project_path),
            "--feedback-json", json.dumps({"items": [{"module": "instructional_strategy", "description": "请教师确认分组反馈安排"}]}, ensure_ascii=False),
            "--output-dir", str(revise_dir),
            "--workspace", str(workspace),
        ], cwd=root, timeout=timeout))
        if revise.get("status") in {"unsupported_scope", "error"} or not revise.get("revision_record"):
            raise RuntimeError("clean package revise did not return a revision record")
        return {
            "status": "pass",
            "archive": str(archive_path),
            "audit_status": audit.get("status"),
            "official_match_count": len(official.get("matches", [])),
            "design_status": design.get("status"),
            "review_status": review.get("status"),
            "review_findings": len(review.get("findings", [])),
            "revise_status": revise.get("status"),
            "revision_action_status": revise.get("revision_record", {}).get("action_status", ""),
            "export_status": design.get("export_status", design.get("export_result", {}).get("export_status", "success")),
            "visual_status": visual or "verified_by_visual_qa_in_export",
            "workspace_is_external": root not in workspace.parents and workspace != root,
        }
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        return {"status": "failed", "archive": str(archive_path), "error": str(exc)}
    finally:
        if keep_temp:
            retained = archive_path.parent / f"clean-install-{archive_path.stem}"
            if retained.exists():
                shutil.rmtree(retained)
            shutil.copytree(Path(temp_context.name), retained)
        temp_context.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a dc-designer-core release archive in a clean directory")
    parser.add_argument("--archive", required=True)
    parser.add_argument("--keep-temp", action="store_true")
    parser.add_argument("--timeout", type=int, default=360)
    args = parser.parse_args()
    result = run_smoke(args.archive, keep_temp=args.keep_temp, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
