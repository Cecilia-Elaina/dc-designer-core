#!/usr/bin/env python
"""Local teacher workspace for dc-designer-core.

This server is deliberately local-only. It exposes the same session and
source services used by the Codex skills and never sends teacher files to a
remote service.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
MCP_ROOT = ROOT / "mcp-server"
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

from core.runtime_paths import ensure_workspace
from core.local_knowledge import delete_private_document, ingest_private_document, search_private_knowledge
from core.session_service import (
    compare_session_versions,
    copy_session,
    create_session,
    delete_session,
    get_session_view,
    list_sessions,
    resume_session,
    rollback_session,
    session_health,
)
from core.standards_catalog import delete_local_source, fetch_update_candidate, load_catalog

WEB_ROOT = ROOT / "web"


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "dc-designer-local/1.1"

    def _send(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8", headers: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _payload(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 2 * 1024 * 1024:
            raise ValueError("请求内容超过 2 MB 限制")
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}

    def _workspace(self) -> str | None:
        return self.server.workspace  # type: ignore[attr-defined]

    def _api(self, method: str, path: str, payload: dict | None = None):
        parts = [unquote(item) for item in path.split("/") if item]
        workspace = self._workspace()
        if parts == ["health"]:
            return 200, session_health(workspace)
        if parts == ["doctor"]:
            from scripts.doctor import build_report
            return 200, build_report()
        if parts == ["projects"] and method == "GET":
            return 200, {"status": "ok", "sessions": list_sessions(workspace)}
        if parts == ["projects"] and method == "POST":
            return 200, create_session(payload or {}, workspace=workspace)
        if parts == ["sources"] and method == "GET":
            return 200, {"status": "ok", **load_catalog(workspace)}
        if parts == ["sources", "update"] and method == "POST":
            return 200, fetch_update_candidate(str((payload or {}).get("url", "")), workspace)
        if parts == ["sources", "approve"] and method == "POST":
            from core.standards_catalog import approve_update
            result = approve_update(
                str((payload or {}).get("update_id", "")),
                workspace,
                teacher_confirmed=bool((payload or {}).get("teacher_confirmed")),
                source_record=(payload or {}).get("source_record") if isinstance((payload or {}).get("source_record"), dict) else None,
            )
            return (200 if result.get("status") == "approved" else 400, result)
        if len(parts) == 2 and parts[0] == "sources" and method == "DELETE":
            result = delete_local_source(parts[1], workspace)
            return (200 if result.get("status") == "deleted" else 400, result)
        if parts == ["knowledge"] and method == "GET":
            return 200, {"status": "ok", **search_private_knowledge({}, workspace=workspace)}
        if parts == ["knowledge"] and method == "POST":
            data = payload or {}
            source_path = str(data.get("path", "")).strip()
            metadata = data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {}
            result = ingest_private_document(source_path, metadata, workspace=workspace)
            return (200 if result.get("status") == "ok" else 400, result)
        if len(parts) == 2 and parts[0] == "knowledge" and method == "DELETE":
            result = delete_private_document(parts[1], workspace=workspace)
            return (200 if result.get("status") == "deleted" else 404, result)
        if len(parts) == 2 and parts[0] == "sessions" and method == "GET":
            view = get_session_view(parts[1], workspace)
            return (200, view) if view else (404, {"status": "not_found", "error": "找不到设计会话"})
        if len(parts) == 2 and parts[0] == "sessions" and method == "DELETE":
            result = delete_session(parts[1], workspace)
            return (200 if result.get("status") == "deleted" else 404, result)
        if len(parts) == 3 and parts[0] == "sessions" and parts[2] == "copy" and method == "POST":
            result = copy_session(parts[1], workspace)
            return (200 if result.get("status") != "not_found" else 404, result)
        if len(parts) == 5 and parts[0] == "sessions" and parts[2] == "compare" and method == "GET":
            result = compare_session_versions(parts[1], int(parts[3]), int(parts[4]), workspace)
            return (200 if result.get("status") == "ok" else 404, result)
        if len(parts) == 3 and parts[0] == "sessions" and parts[2] in {"decisions", "advance"} and method == "POST":
            updates = (payload or {}).get("decisions", (payload or {}).get("items", []))
            if isinstance(updates, dict):
                updates = [updates]
            result = resume_session(parts[1], decision_updates=updates, workspace=workspace)
            return (200 if result.get("status") != "error" else 404, result)
        if len(parts) == 3 and parts[0] == "sessions" and parts[2] == "rollback" and method == "POST":
            result = rollback_session(parts[1], int((payload or {}).get("version", 0)), workspace)
            return (200 if result.get("status") != "error" else 404, result)
        if len(parts) == 3 and parts[0] == "projects" and parts[2] == "exports" and method == "GET":
            for session in list_sessions(workspace):
                if session.get("project_id") == parts[1]:
                    return 200, {"status": "ok", "exports": session.get("last_result", {}).get("export_result", {})}
            return 404, {"status": "not_found", "error": "找不到项目导出记录"}
        return 404, {"status": "not_found", "error": "接口不存在"}

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/api/file", "/api/preview"}:
            try:
                raw_path = parse_qs(parsed.query).get("path", [""])[0]
                target = Path(unquote(raw_path)).expanduser().resolve()
                workspace_root = ensure_workspace(self._workspace())["root"].resolve()
                if workspace_root not in target.parents or not target.is_file():
                    self._send(403, _json_bytes({"status": "forbidden", "error": "只能访问本地工作区内的文件"}))
                    return
                content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
                if parsed.path == "/api/preview":
                    if target.suffix.lower() not in {".md", ".txt", ".json", ".csv"} or target.stat().st_size > 2 * 1024 * 1024:
                        self._send(415, _json_bytes({"status": "unsupported", "error": "只支持预览小型文本报告"}))
                        return
                    self._send(200, target.read_bytes(), "text/plain; charset=utf-8")
                else:
                    self._send(200, target.read_bytes(), content_type, {"Content-Disposition": f'attachment; filename="{target.name}"'})
            except Exception as exc:
                self._send(400, _json_bytes({"status": "error", "error": str(exc)}))
            return
        if parsed.path.startswith("/api/"):
            try:
                status, payload = self._api("GET", parsed.path[5:])
                self._send(status, _json_bytes(payload))
            except Exception as exc:
                self._send(500, _json_bytes({"status": "error", "error": str(exc)}))
            return
        if parsed.path == "/" or parsed.path == "/index.html":
            self._serve(WEB_ROOT / "index.html")
            return
        relative = parsed.path.lstrip("/")
        target = (WEB_ROOT / relative).resolve()
        if WEB_ROOT.resolve() not in target.parents and target != WEB_ROOT.resolve():
            self._send(403, b"forbidden", "text/plain; charset=utf-8")
            return
        self._serve(target)

    def _serve(self, target: Path) -> None:
        if not target.is_file():
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self._send(200, target.read_bytes(), f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        try:
            status, payload = self._api("POST", parsed.path[5:], self._payload())
            self._send(status, _json_bytes(payload))
        except ValueError as exc:
            self._send(400, _json_bytes({"status": "error", "error": str(exc)}))
        except Exception as exc:
            self._send(500, _json_bytes({"status": "error", "error": str(exc)}))

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        try:
            status, payload = self._api("DELETE", parsed.path[5:])
            self._send(status, _json_bytes(payload))
        except Exception as exc:
            self._send(500, _json_bytes({"status": "error", "error": str(exc)}))

    def log_message(self, format: str, *args) -> None:
        print(f"[dc-web] {format % args}")


def main() -> int:
    parser = argparse.ArgumentParser(description="启动本地教学系统设计工作区")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--workspace")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("本地网页只能绑定回环地址，不允许开放公网")
    ensure_workspace(args.workspace)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.workspace = args.workspace  # type: ignore[attr-defined]
    print(f"dc-designer-core 本地工作区：http://{args.host}:{args.port}/")
    print(f"工作区：{ensure_workspace(args.workspace)['root']}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
