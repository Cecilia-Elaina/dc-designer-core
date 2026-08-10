#!/usr/bin/env python
"""Audit the files and metadata that are allowed into a product release."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    ".codex-plugin/plugin.json",
    "README.md",
    "LICENSE",
    ".mcp.json",
    "scripts/dc_info_tech.py",
    "scripts/dc_web.py",
    "data/standards/k12/official_snapshot.json",
]
REQUIRED_SKILLS = [
    "skills/dc-info-tech-design/SKILL.md",
    "skills/dc-info-tech-review/SKILL.md",
    "skills/dc-info-tech-revise/SKILL.md",
]
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".txt", ".html", ".css", ".js"}
USER_PATH_RE = re.compile(r"(?:[A-Za-z]:\\Users\\|[A-Za-z]:\\Download\\|/Users/|/home/)", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"github\.com/dc-designer-core/dc-designer-core|example\.com", re.IGNORECASE)


def _read_json(path: Path, errors: list[str]):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"JSON 无法解析: {path.relative_to(ROOT)}: {exc}")
        return None


def run_check() -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []
    for relative in REQUIRED_FILES + REQUIRED_SKILLS:
        if not (ROOT / relative).is_file():
            errors.append(f"缺少发布必需文件: {relative}")
    plugin = _read_json(ROOT / ".codex-plugin/plugin.json", errors)
    manifest = _read_json(ROOT / "manifest.json", errors)
    if isinstance(plugin, dict):
        if plugin.get("name") != "dc-designer-core":
            errors.append("Codex 插件名称必须为 dc-designer-core")
        if plugin.get("skills") != "./skills/":
            errors.append("Codex manifest 的 skills 必须指向 ./skills/")
        manifest_text = json.dumps(plugin, ensure_ascii=False)
        if "higher_education" in manifest_text or "corporate" in manifest_text:
            errors.append("Codex manifest 泄漏了 v1 不支持范围")
    if isinstance(plugin, dict) and isinstance(manifest, dict):
        if manifest.get("name") != plugin.get("name"):
            errors.append("manifest.json 与 .codex-plugin/plugin.json 的名称不一致")
        if manifest.get("version") != plugin.get("version"):
            errors.append("manifest.json 与 .codex-plugin/plugin.json 的版本不一致")
        manifest_skills = {str(item.get("name")) for item in manifest.get("skills", []) if isinstance(item, dict)}
        available_skills = {path.name for path in (ROOT / "skills").iterdir() if path.is_dir() and (path / "SKILL.md").is_file()}
        if manifest_skills != available_skills:
            errors.append("manifest.json 与 skills 目录公开的 Skill 集合不一致")
    snapshot = _read_json(ROOT / "data/standards/k12/official_snapshot.json", errors)
    if isinstance(snapshot, dict):
        if not snapshot.get("snapshot_id") or not snapshot.get("snapshot_version"):
            errors.append("官方来源快照缺少 snapshot_id 或 snapshot_version")
        if not snapshot.get("content_hash_policy") or not snapshot.get("source_record_fields"):
            errors.append("official snapshot must document content hash policy and source record fields")
        for source in snapshot.get("sources", []):
            required_source_keys = (
                "source_id", "title", "issuer", "document_type", "publication_date",
                "effective_date", "version", "source_url", "stage", "subject",
                "source_level", "source_category", "copyright_scope", "use_scope", "grade_levels", "clauses",
            )
            for key in required_source_keys:
                if not source.get(key):
                    errors.append(f"official source {source.get('source_id', '')} missing {key}")
            if not str(source.get("source_url", "")).startswith("https://"):
                errors.append(f"official source URL is not HTTPS: {source.get('source_id', '')}")
            for clause in source.get("clauses", []) or []:
                required_clause_keys = (
                    "clause_id", "section_path", "page_number", "anchor", "excerpt",
                    "normalized_summary", "keywords", "applicable_topics", "evidence_status", "source_version", "supports_modules",
                )
                for key in required_clause_keys:
                    if not clause.get(key):
                        errors.append(f"source {source.get('source_id', '')} clause {clause.get('clause_id', '')} missing {key}")
            if source.get("content_hash_status") not in {None, "", "metadata_snapshot_only", "retrieved", "not_recorded"}:
                errors.append(f"official source {source.get('source_id', '')} has unknown content_hash_status")
    scan_files = [ROOT / "README.md", ROOT / "manifest.json", ROOT / ".codex-plugin/plugin.json"]
    scan_files += [ROOT / "docs", ROOT / "skills", ROOT / "qa"]
    for item in scan_files:
        paths = [item] if item.is_file() else list(item.rglob("*")) if item.is_dir() else []
        for path in paths:
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            relative = str(path.relative_to(ROOT))
            if USER_PATH_RE.search(text):
                errors.append(f"发布文档包含开发者本机绝对路径: {relative}")
            if PLACEHOLDER_RE.search(text):
                errors.append(f"发布文档包含尚未配置的占位仓库链接: {relative}")
    forbidden_dirs = ["exports", ".pytest_cache", ".test-home", ".dc-designer", "__pycache__"]
    for name in forbidden_dirs:
        if (ROOT / name).exists():
            notes.append(f"发布审计发现工作区目录 {name}，打包器会排除它")
    return {
        "schema_version": "1.0.0",
        "status": "fail" if errors else "warning" if warnings else "pass",
        "errors": errors,
        "warnings": warnings,
        "notes": notes,
        "required_files": REQUIRED_FILES + REQUIRED_SKILLS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="审计 dc-designer-core 发布文件")
    parser.add_argument("--json-output")
    args = parser.parse_args()
    report = run_check()
    if args.json_output:
        output = Path(args.json_output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
