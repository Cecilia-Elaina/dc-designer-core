#!/usr/bin/env python
"""Portable v3 entry point for any agent that can run local Python."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MCP_ROOT = ROOT / "mcp-server"
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

from core.subject_registry import subject_options
from tools.v3_orchestrator import (
    _export_v3_project,
    run_v3_design,
    run_v3_revise,
    run_v3_review,
)


def _json_file(path: str) -> dict:
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def _json_input(args: argparse.Namespace, label: str) -> dict:
    if args.input_file:
        return _json_file(args.input_file)
    if args.input_json:
        return json.loads(args.input_json)
    raise SystemExit(f"{label} 需要 --input-file 或 --input-json")


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="DC Designer v3：面向中国 K-12 九学科的本地教学系统设计工具"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    design = sub.add_parser("design", help="生成一个九学科教学设计草案")
    design.add_argument("--input-file", dest="input_file")
    design.add_argument("--input-json", dest="input_json")
    design.add_argument("--output-dir", default="exports/v3")
    design.add_argument("--workspace")
    design.add_argument("--no-export", action="store_true")

    review = sub.add_parser("review", help="评审已有 v3 项目")
    review.add_argument("--project", required=True)
    review.add_argument("--output-dir", default="exports/v3")
    review.add_argument("--workspace")

    revise = sub.add_parser("revise", help="根据教师反馈生成 v3 修订候选")
    revise.add_argument("--project", required=True)
    revise.add_argument("--input-file", dest="input_file")
    revise.add_argument("--input-json", dest="input_json")
    revise.add_argument("--output-dir", default="exports/v3")
    revise.add_argument("--workspace")

    export = sub.add_parser("export", help="重新导出已有 v3 项目")
    export.add_argument("--project", required=True)
    export.add_argument("--output-dir", default="exports/v3")

    subjects = sub.add_parser("subjects", help="列出某个学段可用的九学科")
    subjects.add_argument("--stage", default="")

    args = parser.parse_args()
    if args.command == "design":
        request = _json_input(args, "design")
        request["v3"] = True
        request["education_scope"] = "k12_nine_subjects"
        if args.no_export:
            request["export"] = False
        result = run_v3_design(request, args.output_dir, args.workspace)
    elif args.command == "review":
        result = run_v3_review(args.project, args.output_dir, args.workspace)
    elif args.command == "revise":
        feedback = _json_input(args, "revise")
        result = run_v3_revise(args.project, feedback, args.output_dir, args.workspace)
    elif args.command == "export":
        project = _json_file(args.project)
        result = _export_v3_project(project, args.output_dir, include_documents=True)
    else:
        result = {"status": "ok", "stage": args.stage, "subjects": subject_options(args.stage)}

    _print(result)
    return 0 if result.get("status") not in {"error", "fail", "failed"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
