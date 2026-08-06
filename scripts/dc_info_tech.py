#!/usr/bin/env python
"""Command-line entry point used by the three Codex v1 Skills."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_ROOT = ROOT / "mcp-server"
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

from core.evidence_store import rebuild_index, search_official_evidence
from core.local_knowledge import ingest_private_document, search_private_knowledge
from core.session_service import (
    compare_session_versions,
    create_session,
    copy_session,
    get_session_view,
    list_sessions,
    resume_session,
    rollback_session,
)
from core.standards_catalog import approve_update, fetch_update_candidate, rebuild_local_snapshot
from tools.v1_orchestrator import run_v1_design, run_v1_review, run_v1_revise


def _json_file(path: str) -> dict:
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def _request(args: argparse.Namespace) -> dict:
    if args.request_file:
        return _json_file(args.request_file)
    return json.loads(args.request_json)


def main() -> int:
    parser = argparse.ArgumentParser(description="dc-designer-core v1 local tools")
    sub = parser.add_subparsers(dest="command", required=True)

    design = sub.add_parser("design")
    design.add_argument("--request-file")
    design.add_argument("--request-json")
    design.add_argument("--output-dir")
    design.add_argument("--workspace")

    review = sub.add_parser("review")
    review.add_argument("--project", required=True)
    review.add_argument("--output-dir")
    review.add_argument("--workspace")

    revise = sub.add_parser("revise")
    revise.add_argument("--project", required=True)
    revise.add_argument("--feedback-file")
    revise.add_argument("--feedback-json")
    revise.add_argument("--output-dir")
    revise.add_argument("--workspace")

    ingest = sub.add_parser("knowledge-ingest")
    ingest.add_argument("--path", required=True)
    ingest.add_argument("--metadata-json", required=True)
    ingest.add_argument("--workspace")

    search = sub.add_parser("search")
    search.add_argument("--stage", default="")
    search.add_argument("--grade", default="")
    search.add_argument("--subject", default="信息科技")
    search.add_argument("--topic", default="")
    search.add_argument("--workspace")

    session_create = sub.add_parser("session-create")
    session_create.add_argument("--request-file")
    session_create.add_argument("--request-json")
    session_create.add_argument("--output-dir")
    session_create.add_argument("--workspace")

    session_resume = sub.add_parser("session-resume")
    session_resume.add_argument("--session-id", required=True)
    session_resume.add_argument("--decisions-file")
    session_resume.add_argument("--decisions-json")
    session_resume.add_argument("--output-dir")
    session_resume.add_argument("--workspace")

    session_list = sub.add_parser("session-list")
    session_list.add_argument("--workspace")

    session_rollback = sub.add_parser("session-rollback")
    session_rollback.add_argument("--session-id", required=True)
    session_rollback.add_argument("--version", required=True, type=int)
    session_rollback.add_argument("--workspace")

    session_status = sub.add_parser("session-status")
    session_status.add_argument("--session-id", required=True)
    session_status.add_argument("--workspace")

    session_compare = sub.add_parser("session-compare")
    session_compare.add_argument("--session-id", required=True)
    session_compare.add_argument("--from-version", required=True, type=int)
    session_compare.add_argument("--to-version", required=True, type=int)
    session_compare.add_argument("--workspace")

    session_copy = sub.add_parser("session-copy")
    session_copy.add_argument("--session-id", required=True)
    session_copy.add_argument("--workspace")

    source_update = sub.add_parser("source-update")
    source_update.add_argument("--url", required=True)
    source_update.add_argument("--workspace")

    source_approve = sub.add_parser("source-approve")
    source_approve.add_argument("--update-id", required=True)
    source_approve.add_argument("--source-record-file")
    source_approve.add_argument("--source-record-json")
    source_approve.add_argument("--teacher-confirmed", action="store_true")
    source_approve.add_argument("--workspace")

    source_rebuild = sub.add_parser("source-rebuild")
    source_rebuild.add_argument("--workspace")

    args = parser.parse_args()
    if args.command == "design":
        if not args.request_file and not args.request_json:
            parser.error("design 需要 --request-file 或 --request-json")
        result = run_v1_design(_request(args), args.output_dir, args.workspace)
    elif args.command == "review":
        result = run_v1_review(args.project, args.output_dir, args.workspace)
    elif args.command == "revise":
        if not args.feedback_file and not args.feedback_json:
            parser.error("revise 需要 --feedback-file 或 --feedback-json")
        feedback = _json_file(args.feedback_file) if args.feedback_file else json.loads(args.feedback_json)
        result = run_v1_revise(args.project, feedback, args.output_dir, args.workspace)
    elif args.command == "knowledge-ingest":
        result = ingest_private_document(args.path, json.loads(args.metadata_json), workspace=args.workspace)
    elif args.command == "search":
        result = {
            "official": search_official_evidence({"stage": args.stage, "grade": args.grade, "subject": args.subject, "topic": args.topic}, args.workspace),
            "private": search_private_knowledge({"keywords": args.topic, "subject": args.subject}, workspace=args.workspace),
        }
    elif args.command == "session-create":
        if not args.request_file and not args.request_json:
            parser.error("session-create 需要 --request-file 或 --request-json")
        result = create_session(_request(args), args.output_dir, args.workspace)
    elif args.command == "session-resume":
        if not args.decisions_file and not args.decisions_json:
            parser.error("session-resume 需要 --decisions-file 或 --decisions-json")
        updates = _json_file(args.decisions_file) if args.decisions_file else json.loads(args.decisions_json)
        if isinstance(updates, dict):
            updates = updates.get("decisions", updates.get("items", [updates]))
        result = resume_session(args.session_id, decision_updates=updates, workspace=args.workspace, output_dir=args.output_dir)
    elif args.command == "session-list":
        result = {"status": "ok", "sessions": list_sessions(args.workspace)}
    elif args.command == "session-rollback":
        result = rollback_session(args.session_id, args.version, args.workspace)
    elif args.command == "session-status":
        result = get_session_view(args.session_id, args.workspace) or {"status": "not_found", "session_id": args.session_id}
    elif args.command == "session-compare":
        result = compare_session_versions(args.session_id, args.from_version, args.to_version, args.workspace)
    elif args.command == "session-copy":
        result = copy_session(args.session_id, args.workspace)
    elif args.command == "source-update":
        result = fetch_update_candidate(args.url, args.workspace)
    elif args.command == "source-approve":
        source_record = None
        if args.source_record_file:
            source_record = _json_file(args.source_record_file)
        elif args.source_record_json:
            source_record = json.loads(args.source_record_json)
        result = approve_update(args.update_id, args.workspace, teacher_confirmed=args.teacher_confirmed, source_record=source_record)
    elif args.command == "source-rebuild":
        result = rebuild_local_snapshot(args.workspace)
    else:
        result = {"status": "error", "errors": [f"unknown command: {args.command}"]}
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("status") not in {"error", "unsupported_scope"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
