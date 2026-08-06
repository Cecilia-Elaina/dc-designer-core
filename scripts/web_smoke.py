#!/usr/bin/env python
"""Start the local teacher web service and exercise its read-only endpoints."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dc_web import Handler


def _request(base: str, path: str) -> tuple[int, object]:
    with urllib.request.urlopen(base + path, timeout=10) as response:
        body = response.read().decode("utf-8")
        content_type = response.headers.get("Content-Type", "")
        if "json" in content_type:
            return response.status, json.loads(body)
        return response.status, body


def run_smoke() -> dict:
    with tempfile.TemporaryDirectory(prefix="dc-web-smoke-") as temp:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.workspace = str(Path(temp) / "teacher-workspace")  # type: ignore[attr-defined]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address
            base = f"http://{host}:{port}"
            health_status, health = _request(base, "/api/health")
            projects_status, projects = _request(base, "/api/projects")
            sources_status, sources = _request(base, "/api/sources")
            page_status, page = _request(base, "/")
            if health_status != 200 or not isinstance(health, dict):
                raise RuntimeError("/api/health 未返回结构化健康状态")
            if projects_status != 200 or not isinstance(projects, dict) or "sessions" not in projects:
                raise RuntimeError("/api/projects 未返回项目列表")
            if sources_status != 200 or not isinstance(sources, dict) or not sources.get("sources"):
                raise RuntimeError("/api/sources 未返回内置来源")
            if page_status != 200 or not isinstance(page, str) or "dc" not in page.lower():
                raise RuntimeError("本地网页首页未返回")
            return {
                "status": "pass",
                "bound_host": host,
                "health_status": health_status,
                "projects_status": projects_status,
                "sources_status": sources_status,
                "page_status": page_status,
                "workspace_is_external": True,
            }
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description="验证本地教师网页服务可以启动并返回核心接口")
    parser.parse_args()
    try:
        result = run_smoke()
    except Exception as exc:
        result = {"status": "failed", "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
