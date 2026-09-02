#!/usr/bin/env python
"""Create a clean, deterministic-enough release archive from a whitelist."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSION = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8")).get("version", "0.0.0")
INCLUDE_DIRS = [".agents/plugins", ".codex-plugin", ".claude-plugin", "commands", "prompts", "skills", "scripts", "mcp-server", "data/standards", "schemas", "templates", "site", "examples"]
INCLUDE_FILES = [
    "README.md", "LICENSE", "manifest.json", ".mcp.json",
    "GEMINI.md", "gemini-extension.json",
    "requirements-core.txt", "requirements-mcp.txt", "requirements-dev.txt",
    "requirements-qa.txt", "qa/reference_profile.json",
    "docs/quickstart.md", "docs/agent-compatibility.md", "docs/source_provenance.md", "docs/v1_plugin_contract.md",
    "docs/release_notes.md", "docs/release_notes_v2.0.0.md",
]
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".test-home", ".dc-designer", "exports", "dist", "test_fixtures"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def _files() -> list[Path]:
    selected: set[Path] = set()
    for relative in INCLUDE_FILES:
        path = ROOT / relative
        if path.is_file():
            selected.add(path)
    for relative in INCLUDE_DIRS:
        directory = ROOT / relative
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.lower() in EXCLUDED_SUFFIXES:
                continue
            parts = set(path.relative_to(ROOT).parts)
            relative_parts = path.relative_to(ROOT).parts
            if parts & EXCLUDED_PARTS or relative_parts[:2] == ("qa", "reference"):
                continue
            selected.add(path)
    return sorted(selected, key=lambda path: path.relative_to(ROOT).as_posix())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dependency_summary() -> dict[str, list[str]]:
    summary: dict[str, list[str]] = {}
    for relative in ("requirements-core.txt", "requirements-mcp.txt", "requirements-qa.txt", "requirements-dev.txt"):
        path = ROOT / relative
        if not path.is_file():
            continue
        requirements = []
        for line in path.read_text(encoding="utf-8").splitlines():
            item = line.strip()
            if item and not item.startswith("#"):
                requirements.append(item)
        summary[relative] = requirements
    return summary


def build_release(output_dir: Path, version: str) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from release_check import run_check

    audit = run_check()
    if audit["status"] == "fail":
        raise RuntimeError("发布审计未通过: " + "；".join(audit["errors"]))
    files = _files()
    if not files:
        raise RuntimeError("白名单没有收集到发布文件")
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"dc-designer-core-v{version}.zip"
    manifest = {
        "schema_version": "1.0.0",
        "package_name": "dc-designer-core",
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(files),
        "files": [],
        "audit": {
            "status": audit["status"],
            "errors": audit.get("errors", []),
            "warnings": audit.get("warnings", []),
            "notes": audit.get("notes", []),
            "required_files": audit.get("required_files", []),
        },
        "dependency_summary": _dependency_summary(),
        "release_readiness": "本地安装包已审计；远程仓库地址和官方平台提交仍需发布者绑定",
    }
    for path in files:
        manifest["files"].append({"path": path.relative_to(ROOT).as_posix(), "size": path.stat().st_size, "sha256": _sha256(path)})
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            bundle.write(path, path.relative_to(ROOT).as_posix())
        bundle.writestr("RELEASE_MANIFEST.json", manifest_bytes)
    digest = _sha256(archive)
    (output_dir / f"dc-designer-core-v{version}.zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    manifest["archive"] = {"path": str(archive), "size": archive.stat().st_size, "sha256": digest}
    manifest_path = output_dir / f"dc-designer-core-v{version}.release.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "success", "archive": str(archive), "manifest": str(manifest_path), "sha256": digest, "file_count": len(files), "warnings": audit["warnings"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 dc-designer-core 发布压缩包")
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--output-dir", default=str(ROOT / "dist"))
    args = parser.parse_args()
    try:
        result = build_release(Path(args.output_dir).expanduser().resolve(), args.version)
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
