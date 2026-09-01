#!/usr/bin/env python
"""Serve the static product site briefly and verify its public assets."""

from __future__ import annotations

import json
import threading
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = ROOT / "site"
REQUIRED_PATHS = ("/", "/styles.css", "/site.js")


class _SiteHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:
        return


def run_smoke() -> dict:
    if not SITE_ROOT.is_dir():
        raise RuntimeError("site 目录不存在")
    server = ThreadingHTTPServer(("127.0.0.1", 0), _SiteHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        base = f"http://{host}:{port}"
        assets = {}
        for relative in REQUIRED_PATHS:
            with urllib.request.urlopen(base + relative, timeout=10) as response:
                body = response.read()
                assets[relative] = {"status": response.status, "bytes": len(body)}
                if response.status != 200 or not body:
                    raise RuntimeError(f"站点资源不可用: {relative}")
        return {"status": "pass", "assets": assets}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main() -> int:
    try:
        result = run_smoke()
    except Exception as exc:
        result = {"status": "failed", "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
