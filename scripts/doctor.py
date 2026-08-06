#!/usr/bin/env python
"""Check the local runtime needed by dc-designer-core."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_ROOT = ROOT / "mcp-server"
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

from core.runtime_paths import ensure_workspace
from core.visual_qa import find_pdftoppm, find_soffice


def _find_drawio() -> str:
    candidates = [
        os.environ.get("DRAWIO_PATH", ""),
        r"C:\Program Files\draw.io\draw.io.exe",
        r"C:\Program Files\diagrams.net\diagrams.net.exe",
        shutil.which("draw.io") or "",
        shutil.which("diagrams.net") or "",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    return ""


def _module_check(name: str, *, required: bool) -> dict:
    try:
        module = importlib.import_module(name)
        return {"name": name, "status": "pass", "version": getattr(module, "__version__", "")}
    except Exception as exc:
        return {"name": name, "status": "fail" if required else "warning", "error": str(exc)}


def build_report() -> dict:
    checks = [
        {
            "name": "python",
            "status": "pass" if sys.version_info >= (3, 10) else "fail",
            "version": sys.version.split()[0],
            "detail": "需要 Python 3.10 或更高版本",
        },
        _module_check("docx", required=True),
        _module_check("openpyxl", required=True),
        _module_check("PIL", required=True),
        _module_check("mcp", required=False),
        _module_check("matplotlib", required=False),
    ]
    soffice = find_soffice()
    pdftoppm = find_pdftoppm()
    drawio = _find_drawio()
    checks.extend([
        {"name": "LibreOffice", "status": "pass" if soffice else "warning", "path": soffice, "detail": "Word 逐页视觉检查"},
        {"name": "pdftoppm", "status": "pass" if pdftoppm else "warning", "path": pdftoppm, "detail": "PDF 页面栅格化"},
        {"name": "Draw.io", "status": "pass" if drawio else "warning", "path": drawio, "detail": "外部编辑器可选，插件生成标准 XML"},
    ])
    with tempfile.TemporaryDirectory(prefix="dc-doctor-") as temp:
        try:
            dirs = ensure_workspace(temp)
            probe = dirs["root"] / "doctor-probe.txt"
            probe.write_text("local-only", encoding="utf-8")
            checks.append({"name": "workspace_write", "status": "pass", "path": str(probe)})
        except Exception as exc:
            checks.append({"name": "workspace_write", "status": "fail", "error": str(exc)})
    try:
        import tools.v1_orchestrator  # noqa: F401
        checks.append({"name": "core_import", "status": "pass", "detail": "v1 核心入口可加载"})
    except Exception as exc:
        checks.append({"name": "core_import", "status": "fail", "error": str(exc)})
    failures = [item for item in checks if item.get("status") == "fail"]
    warnings = [item for item in checks if item.get("status") == "warning"]
    return {
        "schema_version": "1.0.0",
        "status": "fail" if failures else "warning" if warnings else "pass",
        "python_executable": sys.executable,
        "package_root": str(ROOT),
        "checks": checks,
        "failure_count": len(failures),
        "warning_count": len(warnings),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 dc-designer-core 本机运行环境")
    parser.add_argument("--json-output", help="额外写出 JSON 诊断报告")
    args = parser.parse_args()
    report = build_report()
    if args.json_output:
        output = Path(args.json_output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
