#!/usr/bin/env python
"""Run the three product acceptance cases without using real student data."""

from __future__ import annotations

import argparse
import json
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_ROOT = ROOT / "mcp-server"
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

from tools.v1_orchestrator import run_v1_design


CASES = {
    "junior_branch": {
        "education_scope": "k12_info_technology",
        "mode": "standard_fast",
        "stage": "junior_secondary",
        "grade": "七年级",
        "subject": "信息科技",
        "topic": "Python 分支结构",
        "title": "初中 Python 分支结构教学系统设计",
        "textbook_version": "教师待确认的本机教材资料",
        "unit": "程序设计基础",
        "periods": 2,
        "equipment": "Windows 计算机、VSCode",
        "class_profile": {"class_size": 48, "common_difficulties": ["条件表达式、分支覆盖和边界测试不完整"]},
    },
    "senior_loop": {
        "education_scope": "k12_info_technology",
        "mode": "standard_fast",
        "stage": "senior_secondary",
        "grade": "高中一年级",
        "subject": "信息技术",
        "topic": "Python 循环结构设计",
        "title": "高中 Python 循环程序设计教学系统设计",
        "textbook_version": "教师待确认的本机教材资料",
        "unit": "程序设计基础",
        "periods": 2,
        "equipment": "Windows 计算机、VSCode",
        "class_profile": {"class_size": 48, "common_difficulties": ["循环变量更新和终止条件不完整"]},
    },
    "primary_algorithm": {
        "education_scope": "k12_info_technology",
        "mode": "collaborative",
        "stage": "primary",
        "grade": "六年级",
        "subject": "信息科技",
        "topic": "生活中的算法与步骤表达",
        "title": "小学算法与步骤表达教学系统设计",
        "textbook_version": "教师待确认的本机教材资料",
        "unit": "算法与问题解决",
        "periods": 1,
        "equipment": "教室投影、纸笔、平板或计算机",
        "class_profile": {"class_size": 40, "common_difficulties": ["步骤遗漏、重复或顺序混乱"]},
    },
}


def run_cases(selected: list[str] | None = None, *, timeout_note: str = "") -> dict:
    names = selected or list(CASES)
    unknown = [name for name in names if name not in CASES]
    if unknown:
        return {"status": "failed", "error": f"unknown cases: {', '.join(unknown)}"}
    rows = []
    with tempfile.TemporaryDirectory(prefix="dc-acceptance-") as temp:
        root = Path(temp)
        for name in names:
            case_root = root / name
            result = run_v1_design(
                CASES[name],
                str(case_root / "exports"),
                str(case_root / "teacher-workspace"),
            )
            export = result.get("export", {}) if isinstance(result, dict) else {}
            visual = export.get("visual_qa", {}) if isinstance(export, dict) else {}
            row = {
                "case": name,
                "status": result.get("status"),
                "export_status": export.get("export_status"),
                "visual_status": visual.get("status"),
                "can_export_final": result.get("can_export_final", False),
                "confirmation_count": len(result.get("required_confirmations", [])),
                "blocking_reason_count": len(result.get("final_blocking_reasons", [])),
            }
            rows.append(row)
    failures = [row for row in rows if row["status"] in {"unsupported_scope", "error"} or row["export_status"] != "success" or row["visual_status"] != "pass"]
    return {"status": "failed" if failures else "pass", "cases": rows, "failures": failures, "note": timeout_note}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run dc-designer-core K12 acceptance cases")
    parser.add_argument("--case", action="append", dest="cases", choices=list(CASES))
    args = parser.parse_args()
    result = run_cases(args.cases)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
