#!/usr/bin/env python
"""Render and inspect exported Word/Draw.io artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_ROOT = ROOT / "mcp-server"
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

from core.visual_qa import inspect_docx_structure, inspect_drawio, render_docx, run_visual_qa


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 Word 和 Draw.io 输出的真实布局")
    parser.add_argument("--export-dir")
    parser.add_argument("--docx", action="append", default=[])
    parser.add_argument("--drawio", action="append", default=[])
    parser.add_argument("--reference-docx", action="append", default=[], help="生成范例报告的结构与分页基线")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if args.export_dir:
        root = Path(args.export_dir)
        files = {}
        for key, names in {
            "dc_report": ["教学系统设计报告.docx", "dc_report.docx"],
            "lesson_plan": ["教师教学指南.docx", "lesson_plan.docx"],
            "student_worksheet": ["学生学习单.docx", "student_worksheet.docx"],
            "ai_process_record": ["AI过程记录.docx", "ai_process_record.docx"],
            "drawio_workbook": ["diagrams/技能流图_多页面.drawio"],
        }.items():
            for name in names:
                candidate = root / name
                if candidate.is_file():
                    files[key] = str(candidate)
                    break
        result = run_visual_qa(files, args.output_dir)
    else:
        result = {"documents": {}, "drawio": {}}
        for index, path in enumerate(args.docx):
            result["documents"][f"docx_{index + 1}"] = render_docx(path, Path(args.output_dir) / "documents")
        for index, path in enumerate(args.drawio):
            result["drawio"][f"drawio_{index + 1}"] = inspect_drawio(path)
        statuses = [item["status"] for group in (result["documents"], result["drawio"]) for item in group.values()]
        result["status"] = "fail" if "fail" in statuses else "pass" if statuses and all(item == "pass" for item in statuses) else "unverified"
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)
        (Path(args.output_dir) / "visual_qa_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.reference_docx:
        baseline = []
        reference_dir = Path(args.output_dir) / "reference"
        for index, path in enumerate(args.reference_docx, start=1):
            structural = inspect_docx_structure(path)
            rendered = render_docx(path, reference_dir / f"reference_{index}")
            baseline.append({
                "name": Path(path).name,
                "structural": {
                    "size": structural.get("size", 0),
                    "tables": structural.get("tables", 0),
                    "drawings": structural.get("drawings", 0),
                    "sections": structural.get("sections", []),
                    "font_families": structural.get("font_families", []),
                    "min_font_half_points": structural.get("min_font_half_points"),
                },
                "render": {
                    "status": rendered.get("render", {}).get("status"),
                    "page_count": len(rendered.get("render", {}).get("pages", [])),
                    "errors": rendered.get("render", {}).get("errors", []),
                    "warnings": rendered.get("render", {}).get("warnings", []),
                },
            })
        result["reference_profile"] = {"schema_version": "1.0.0", "reports": baseline}
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)
        (Path(args.output_dir) / "reference_profile.json").write_text(json.dumps(result["reference_profile"], ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"pass", "unverified"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
