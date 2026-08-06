"""Private teacher knowledge base stored outside the plugin package."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.runtime_paths import ensure_workspace


PII_PATTERNS = [
    ("student_name_score", re.compile(r"[一-鿿]{2,4}\s*[0-9]{1,3}\s*分")),
    ("student_id", re.compile(r"(?:学号|学籍号|student\s*id)\s*[:：]?\s*[\w-]{4,20}", re.I)),
    ("national_id", re.compile(r"[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]")),
    ("phone", re.compile(r"(?:手机|电话|联系电话|phone)\s*[:：]?\s*1[3-9]\d{9}", re.I)),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _index_path(workspace: str | None) -> Path:
    return ensure_workspace(workspace)["indexes"] / "private_knowledge.json"


def _load_index(workspace: str | None) -> list[dict]:
    path = _index_path(workspace)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_index(entries: list[dict], workspace: str | None) -> None:
    path = _index_path(workspace)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_text(path: Path) -> str:
    """Extract searchable text without distributing the original document."""
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".csv", ".json", ".yaml", ".yml"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".docx":
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
        xml = re.sub(r"</w:p>|</w:tr>", "\n", xml)
        return re.sub(r"<[^>]+>", "", xml).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        except Exception:
            return ""
    return ""


def scan_privacy(text: str) -> list[str]:
    return [name for name, pattern in PII_PATTERNS if pattern.search(text or "")]


def ingest_private_document(
    file_path: str,
    metadata: dict[str, Any],
    *,
    workspace: str | None = None,
) -> dict:
    """Ingest a teacher-owned file, blocking suspected student PII by default."""
    source = Path(file_path).expanduser().resolve()
    if not source.is_file():
        return {"status": "error", "errors": [f"文件不存在: {source}"], "warnings": []}
    text = extract_text(source)
    pii = scan_privacy(text)
    if pii:
        return {
            "status": "blocked_privacy",
            "ingested": False,
            "warnings": ["检测到疑似学生个人信息，文件未复制到知识库。", *pii],
            "privacy_status": "blocked",
            "source_path": str(source),
        }

    dirs = ensure_workspace(workspace)
    document_id = f"teacher-doc-{uuid.uuid4().hex[:12]}"
    safe_name = re.sub(r"[^\w\-.一-龥]+", "_", source.name).strip("._") or "document"
    target = dirs["knowledge_documents"] / f"{document_id}_{safe_name}"
    shutil.copy2(source, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    entry = {
        "document_id": document_id,
        "title": metadata.get("title") or source.stem,
        "file_path": str(target),
        "file_name": target.name,
        "file_checksum_sha256": digest,
        "file_size_bytes": target.stat().st_size,
        "document_type": metadata.get("document_type", "teacher_material"),
        "subject": metadata.get("subject", "信息科技"),
        "stage": metadata.get("stage", ""),
        "grade": metadata.get("grade") or metadata.get("grade_level", ""),
        "topic": metadata.get("topic", ""),
        "scope": metadata.get("scope", "personal"),
        "organization": metadata.get("organization", ""),
        "copyright_scope": metadata.get("copyright_scope", "teacher_uploaded_private"),
        "distribution_allowed": False,
        "source_level": "C1",
        "source_category": "teacher_private",
        "provenance_type": "TEACHER_INPUT",
        "can_be_goal_basis": "limited",
        "retrieval_status": "user_provided",
        "privacy_status": "clear",
        "content_indexed": bool(text),
        "content_excerpt": text[:240] if text else "",
        "ingested_at": _now(),
    }
    entries = _load_index(workspace)
    entries.append(entry)
    _save_index(entries, workspace)
    return {
        "status": "ok",
        "ingested": True,
        "document_id": document_id,
        "source_record": entry,
        "index_path": str(_index_path(workspace)),
        "warnings": ["商业教材或教师资料仅保存在本机私有工作区，不会写入插件包。"] if metadata.get("document_type") == "textbook" else [],
    }


def search_private_knowledge(query: dict, *, workspace: str | None = None) -> dict:
    entries = _load_index(workspace)
    keywords = query.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [keywords]
    terms = [str(term).lower() for term in keywords if term]
    results = []
    for entry in entries:
        if query.get("subject") and entry.get("subject") not in {query["subject"], "信息科技", "信息技术"}:
            continue
        haystack = " ".join(str(entry.get(key, "")) for key in ("title", "topic", "content_excerpt", "document_type")).lower()
        score = sum(1 for term in terms if term in haystack)
        if terms and score == 0:
            continue
        result = dict(entry)
        result.pop("content_excerpt", None)
        result["relevance_score"] = score
        results.append(result)
    results.sort(key=lambda item: item.get("relevance_score", 0), reverse=True)
    return {"status": "found" if results else "not_found", "matches": results, "count": len(results)}


def delete_private_document(document_id: str, *, workspace: str | None = None) -> dict:
    entries = _load_index(workspace)
    kept = []
    deleted = None
    for entry in entries:
        if entry.get("document_id") == document_id:
            deleted = entry
            try:
                Path(entry.get("file_path", "")).unlink(missing_ok=True)
            except OSError:
                pass
        else:
            kept.append(entry)
    _save_index(kept, workspace)
    return {"status": "deleted" if deleted else "not_found", "document_id": document_id}

