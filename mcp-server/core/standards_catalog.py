"""Versioned official-source catalog for the K12 information-technology scope.

The package ships a small, auditable metadata snapshot. Teacher-triggered online
updates are staged locally and never become active evidence without review.
Full official documents are not copied into the package; records retain links,
short excerpts, summaries, and provenance only.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.runtime_paths import PACKAGE_ROOT, ensure_workspace


BUILTIN_SNAPSHOT = PACKAGE_ROOT / "data" / "standards" / "k12" / "official_snapshot.json"
OFFICIAL_HOST_SUFFIXES = ("moe.gov.cn", "gov.cn")
MAX_UPDATE_BYTES = 12 * 1024 * 1024


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def catalog_paths(workspace: str | None = None) -> dict[str, Path]:
    dirs = ensure_workspace(workspace)
    root = dirs["knowledge"] / "official"
    return {
        "root": root,
        "active": root / "active_sources.json",
        "updates": root / "updates.json",
        "history": root / "history.json",
        "update_documents": root / "update_documents",
        "snapshot": root / "snapshot.json",
    }


def load_builtin_snapshot() -> dict:
    payload = _read_json(BUILTIN_SNAPSHOT, {})
    return payload if isinstance(payload, dict) else {}


def normalize_source(source: dict, *, snapshot_id: str = "") -> dict:
    item = dict(source or {})
    item.setdefault("document_type", "official_document")
    item.setdefault("publication_date", item.get("source_date", ""))
    item.setdefault("effective_date", item.get("publication_date", ""))
    item.setdefault("version", item.get("source_version", ""))
    item.setdefault("status", "current")
    item.setdefault("source_level", "A1")
    item.setdefault("source_category", "official_authority")
    item.setdefault("credibility", "highest")
    item.setdefault("can_be_goal_basis", "limited")
    item.setdefault("copyright_scope", "official_public_reference")
    item.setdefault("use_scope", ["content_reference"])
    item.setdefault("stage", [])
    item.setdefault("subject", "信息科技")
    item.setdefault("source_url", "")
    item.setdefault("retrieved_at", "")
    item.setdefault("metadata_snapshot_at", "")
    item.setdefault("content_sha256", "")
    item.setdefault(
        "content_hash_status",
        "metadata_snapshot_only" if snapshot_id and snapshot_id != "local-update" else "not_recorded",
    )
    item.setdefault("source_record_sha256", "")
    item["source_version"] = item.get("version", "")
    item["snapshot_id"] = snapshot_id
    clauses = []
    for clause in item.get("clauses", []) or []:
        c = dict(clause or {})
        c.setdefault("page_number", c.get("page", ""))
        c.setdefault("anchor", "")
        c.setdefault("excerpt", "")
        c.setdefault("normalized_summary", c.get("clause_text", ""))
        c.setdefault("keywords", [])
        c.setdefault("applicable_topics", ["all"])
        c.setdefault("supports_modules", ["content_reference"])
        c["clause_text"] = c.get("clause_text") or c.get("normalized_summary", "")
        c["source_id"] = item.get("source_id", "")
        c["source_version"] = item.get("source_version", "")
        clauses.append(c)
    item["clauses"] = clauses
    item["specific_clauses"] = clauses
    item["source_hash"] = _canonical_hash({k: v for k, v in item.items() if k not in {"source_hash", "snapshot_id"}})
    item["source_record_sha256"] = item["source_hash"]
    item["provenance"] = {
        "snapshot_id": snapshot_id,
        "retrieved_at": item.get("retrieved_at", ""),
        "metadata_snapshot_at": item.get("metadata_snapshot_at", ""),
        "content_sha256": item.get("content_sha256", ""),
        "content_hash_status": item.get("content_hash_status", "not_recorded"),
        "source_record_sha256": item.get("source_record_sha256", ""),
        "verification_status": "teacher_confirmed" if item.get("verified_by_teacher") else "candidate",
    }
    return item


def load_active_sources(workspace: str | None = None) -> list[dict]:
    payload = _read_json(catalog_paths(workspace)["active"], [])
    return payload if isinstance(payload, list) else []


def load_catalog(workspace: str | None = None) -> dict:
    builtin = load_builtin_snapshot()
    snapshot_id = str(builtin.get("snapshot_id", "builtin-unknown"))
    sources = []
    for source in builtin.get("sources", []):
        source_copy = dict(source or {})
        source_copy.setdefault("metadata_snapshot_at", builtin.get("generated_at", ""))
        source_copy.setdefault("retrieved_at", builtin.get("generated_at", ""))
        normalized = normalize_source(source_copy, snapshot_id=snapshot_id)
        sources.append(normalized)
    by_id = {source.get("source_id"): source for source in sources if source.get("source_id")}
    for source in load_active_sources(workspace):
        normalized = normalize_source(source, snapshot_id=source.get("snapshot_id", "local-update"))
        source_id = normalized.get("source_id")
        if source_id:
            by_id[source_id] = normalized
    merged = list(by_id.values())
    merged.sort(key=lambda item: item.get("source_id", ""))
    snapshot_payload = {
        "snapshot_id": snapshot_id,
        "snapshot_version": builtin.get("snapshot_version", ""),
        "sources": merged,
        "source_count": len(merged),
        "catalog_hash": _canonical_hash(merged),
        "loaded_at": now_iso(),
        "pending_updates": _read_json(catalog_paths(workspace)["updates"], []),
        "source_history": _read_json(catalog_paths(workspace)["history"], []),
    }
    return snapshot_payload


def rebuild_local_snapshot(workspace: str | None = None) -> dict:
    paths = catalog_paths(workspace)
    catalog = load_catalog(workspace)
    path = Path(_write_json(paths["snapshot"], catalog))
    return {"status": "ok", "snapshot": catalog, "path": str(path)}


def delete_local_source(source_id: str, workspace: str | None = None) -> dict:
    """Remove a teacher-approved local source; builtin snapshot records are immutable."""
    paths = catalog_paths(workspace)
    active = load_active_sources(workspace)
    remaining = [item for item in active if item.get("source_id") != source_id]
    if len(remaining) == len(active):
        builtin_ids = {item.get("source_id") for item in load_builtin_snapshot().get("sources", [])}
        if source_id in builtin_ids:
            return {"status": "blocked", "source_id": source_id, "reason": "内置官方快照不可从工作区删除。"}
        return {"status": "not_found", "source_id": source_id}
    _write_json(paths["active"], remaining)
    snapshot = rebuild_local_snapshot(workspace)
    return {"status": "deleted", "source_id": source_id, "snapshot": snapshot}


def is_official_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(str(url or ""))
        host = (parsed.hostname or "").lower().rstrip(".")
        return parsed.scheme == "https" and any(host == suffix or host.endswith("." + suffix) for suffix in OFFICIAL_HOST_SUFFIXES)
    except ValueError:
        return False


def _safe_update_name(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    name = Path(parsed.path).name or "official-document"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name[:100] or "official-document"


def fetch_update_candidate(url: str, workspace: str | None = None, *, timeout: int = 20) -> dict:
    """Fetch an official URL into a pending local update record.

    The function only stages bytes and metadata. It never activates a source
    or calls it a verified clause until a teacher reviews the candidate.
    """
    if not is_official_url(url):
        return {"status": "blocked", "reason": "只允许访问 HTTPS 官方教育域名。", "url": url}
    paths = catalog_paths(workspace)
    request = urllib.request.Request(str(url), headers={"User-Agent": "dc-designer-core-source-updater/1.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            if not is_official_url(final_url):
                return {"status": "blocked", "reason": "重定向目标不是允许的官方域名。", "url": final_url}
            chunks = []
            total = 0
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPDATE_BYTES:
                    return {"status": "blocked", "reason": "官方文件超过本地更新大小限制。", "url": final_url}
                chunks.append(chunk)
            content = b"".join(chunks)
            content_type = response.headers.get("Content-Type", "")
    except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        return {"status": "error", "url": url, "error": str(exc), "warnings": ["联网更新失败，可继续使用本地快照。"]}

    digest = hashlib.sha256(content).hexdigest()
    update_id = f"update-{digest[:16]}"
    document_path = paths["update_documents"] / f"{update_id}_{_safe_update_name(final_url)}"
    document_path.parent.mkdir(parents=True, exist_ok=True)
    document_path.write_bytes(content)
    record = {
        "update_id": update_id,
        "source_id": "",
        "url": final_url,
        "content_type": content_type,
        "file_path": str(document_path),
        "sha256": digest,
        "size_bytes": len(content),
        "retrieved_at": now_iso(),
        "status": "pending_review",
        "source_level": "A1",
        "source_category": "official_authority",
        "notes": "文件已从允许的官方域名获取，尚未经过教师审核或条款级解析。",
    }
    current_matches = [
        source for source in load_catalog(workspace).get("sources", [])
        if source.get("source_url") == final_url
    ]
    record["comparison"] = {
        "status": "same_official_url_pending_version_review" if current_matches else "new_official_url",
        "matching_source_ids": [source.get("source_id", "") for source in current_matches],
        "current_versions": [source.get("version", "") for source in current_matches],
        "note": "内容哈希已记录；版本替换关系需由教师根据文件元数据和条款差异确认。",
    }
    updates = _read_json(paths["updates"], [])
    if not isinstance(updates, list):
        updates = []
    updates = [item for item in updates if item.get("update_id") != update_id]
    updates.append(record)
    _write_json(paths["updates"], updates)
    return {"status": "pending_review", "candidate": record, "updates_path": str(paths["updates"])}


def approve_update(update_id: str, workspace: str | None = None, *, teacher_confirmed: bool = False, source_record: dict | None = None) -> dict:
    if not teacher_confirmed:
        return {"status": "blocked", "reason": "启用官方来源更新前必须经过教师确认。"}
    paths = catalog_paths(workspace)
    updates = _read_json(paths["updates"], [])
    candidate = next((item for item in updates if item.get("update_id") == update_id), None)
    if not candidate:
        return {"status": "not_found", "update_id": update_id}
    record = dict(source_record or {})
    required_metadata = ("title", "issuer", "version", "publication_date", "effective_date", "stage", "subject", "clauses")
    missing_metadata = [key for key in required_metadata if not record.get(key)]
    if missing_metadata:
        return {
            "status": "blocked",
            "update_id": update_id,
            "reason": "启用前必须补齐并核对官方文件元数据。",
            "missing_metadata": missing_metadata,
        }
    record.setdefault("source_id", f"local-official-{update_id.removeprefix('update-')}")
    record.setdefault("title", Path(candidate.get("file_path", "官方文件")).stem)
    record.setdefault("source_url", candidate.get("url", ""))
    record.setdefault("source_version", record.get("version", "待教师补充"))
    record.setdefault("version", record.get("source_version", ""))
    record.setdefault("issuer", "待教师核对")
    record.setdefault("document_type", "official_document")
    record.setdefault("stage", [])
    record.setdefault("subject", "信息科技")
    record.setdefault("source_level", "A1")
    record.setdefault("source_category", "official_authority")
    record.setdefault("credibility", "high")
    record.setdefault("can_be_goal_basis", "limited")
    record.setdefault("status", "teacher_confirmed")
    record.setdefault("verified_by_teacher", True)
    record.setdefault("verification_date", now_iso())
    record["retrieved_at"] = candidate.get("retrieved_at", now_iso())
    record["content_sha256"] = candidate.get("sha256", "")
    record["content_hash_status"] = "retrieved"
    record["update_id"] = update_id
    active = load_active_sources(workspace)
    history = _read_json(paths["history"], [])
    if not isinstance(history, list):
        history = []
    prior = [item for item in active if item.get("source_id") == record.get("source_id")]
    for item in prior:
        superseded = dict(item)
        superseded["status"] = "superseded"
        superseded["superseded_at"] = now_iso()
        history.append(superseded)
    active = [item for item in active if item.get("source_id") != record.get("source_id")]
    active.append(record)
    _write_json(paths["active"], active)
    _write_json(paths["history"], history)
    for item in updates:
        if item.get("update_id") == update_id:
            item["status"] = "approved"
            item["approved_at"] = now_iso()
    _write_json(paths["updates"], updates)
    snapshot = rebuild_local_snapshot(workspace)
    return {"status": "approved", "source": normalize_source(record, snapshot_id="local-update"), "snapshot": snapshot}


def source_citation(source: dict) -> dict:
    """Return teacher-facing provenance without leaking internal enums."""
    return {
        "来源名称": source.get("title", source.get("source_name", "未命名来源")),
        "发布机构": source.get("issuer", "未提供"),
        "版本": source.get("version", source.get("source_version", "未提供")),
        "发布日期": source.get("publication_date", source.get("source_date", "未提供")),
        "适用范围": "、".join(source.get("stage", []) or []) or "待确认",
        "官方链接": source.get("source_url", "未提供"),
        "来源状态": "教师已确认" if source.get("verified_by_teacher") else "条款候选",
        "来源用途": "；".join(source.get("use_scope", []) or []) or "待确认",
        "source_id": source.get("source_id", ""),
        "snapshot_id": source.get("snapshot_id", ""),
    }
