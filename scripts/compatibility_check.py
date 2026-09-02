#!/usr/bin/env python
"""Validate the native host adapters without running the full core suite."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMANDS = (
    "commands/dc-info-tech-design.toml",
    "commands/dc-info-tech-review.toml",
    "commands/dc-info-tech-revise.toml",
)


def _load(relative: str, errors: list[str]) -> dict:
    path = ROOT / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"无法解析 {relative}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{relative} 必须是 JSON 对象")
        return {}
    return value


def run_check() -> dict:
    errors: list[str] = []
    codex = _load(".codex-plugin/plugin.json", errors)
    claude = _load(".claude-plugin/plugin.json", errors)
    gemini = _load("gemini-extension.json", errors)
    core = _load("manifest.json", errors)
    _load(".mcp.json", errors)

    expected_version = core.get("version")
    for relative, manifest, name in (
        (".codex-plugin/plugin.json", codex, "Codex"),
        (".claude-plugin/plugin.json", claude, "Claude Code"),
        ("gemini-extension.json", gemini, "Gemini CLI"),
    ):
        if manifest.get("name") != "dc-designer-core":
            errors.append(f"{name} 入口名称必须为 dc-designer-core ({relative})")
        if manifest.get("version") != expected_version:
            errors.append(f"{name} 入口版本必须与 manifest.json 一致 ({relative})")

    if codex.get("skills") != "./skills/":
        errors.append("Codex 入口的 skills 必须指向 ./skills/")
    if codex.get("mcpServers") != "./.mcp.json":
        errors.append("Codex 入口的 mcpServers 必须指向 ./.mcp.json")
    if "../skills" in json.dumps(claude, ensure_ascii=False):
        errors.append("Claude Code 入口不能使用仓库外的 ../skills 路径")

    gemini_servers = gemini.get("mcpServers") or {}
    if "${extensionPath}" not in json.dumps(gemini_servers, ensure_ascii=False):
        errors.append("Gemini CLI MCP 路径必须使用 ${extensionPath}")
    if gemini.get("contextFileName") != "GEMINI.md":
        errors.append("Gemini CLI 入口必须加载 GEMINI.md")

    skill_dirs = {
        path.name
        for path in (ROOT / "skills").iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    }
    if skill_dirs != {"dc-info-tech-design", "dc-info-tech-review", "dc-info-tech-revise"}:
        errors.append("公开 Skill 集合与三条核心设计流程不一致")

    prompt = (ROOT / "prompts/dc-designer-core.md").read_text(encoding="utf-8")
    for marker in ("Codex", "Claude Code", "Gemini CLI", "python mcp-server/server.py"):
        if marker not in prompt:
            errors.append(f"通用启动提示词缺少宿主或接入说明: {marker}")
    for relative in COMMANDS:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        try:
            command = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            errors.append(f"Gemini 命令 TOML 无法解析: {relative}: {exc}")
            continue
        if not command.get("description") or not command.get("prompt"):
            errors.append(f"Gemini 命令缺少 description 或 prompt: {relative}")
        if "{{args}}" not in str(command.get("prompt", "")):
            errors.append(f"Gemini 命令缺少 prompt 或参数占位符: {relative}")

    return {
        "status": "fail" if errors else "pass",
        "version": expected_version,
        "hosts": ["Codex", "Claude Code", "Gemini CLI", "MCP / portable prompt"],
        "errors": errors,
    }


if __name__ == "__main__":
    report = run_check()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(1 if report["status"] == "fail" else 0)
