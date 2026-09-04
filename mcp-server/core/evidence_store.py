"""Deterministic local evidence retrieval for the v1 information-tech scope."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Iterable

from core.product_config import normalize_stage, normalize_subject
from core.runtime_paths import ensure_workspace, PACKAGE_ROOT
from core.standards_catalog import load_catalog


OFFICIAL_BUNDLE = PACKAGE_ROOT / "data" / "standards" / "k12" / "information_technology_v1.json"


def _load_bundle(workspace: str | None = None) -> list[dict]:
    """Load the versioned catalog, with the legacy bundle as a fallback."""
    catalog = load_catalog(workspace)
    sources = catalog.get("sources", []) if isinstance(catalog, dict) else []
    if sources:
        return sources
    if not OFFICIAL_BUNDLE.exists():
        return []
    with OFFICIAL_BUNDLE.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, list) else payload.get("sources", [])


def _tokens(text: str) -> set[str]:
    text = str(text or "").lower()
    words = set(re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", text))
    for phrase in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        words.add(phrase)
        words.update(phrase[i:i + 2] for i in range(len(phrase) - 1))
    return words


def _canonical_evidence_subject(value: str) -> str:
    """Normalize public subject names before filtering mixed-source evidence."""
    aliases = {
        "信息技术": "信息科技",
        "信息科技": "信息科技",
        "生物": "生物学",
        "生物学": "生物学",
        "政治": "政治",
        "道德与法治": "政治",
        "思想政治": "政治",
    }
    return aliases.get(str(value or "").strip(), str(value or "").strip())


def _evidence_subject_matches(requested: str, actual: str) -> bool:
    """Allow general policy sources, but never leak another subject's source."""
    if actual == "通用":
        return True
    return _canonical_evidence_subject(requested) == _canonical_evidence_subject(actual)


def _iter_clauses(source: dict) -> Iterable[dict]:
    for clause in source.get("clauses", []):
        item = dict(clause)
        item["source_id"] = source.get("source_id", "")
        item["document_title"] = source.get("title", "")
        item["issuer"] = source.get("issuer", "教育部")
        item["version"] = source.get("version", "")
        item["source_version"] = source.get("source_version", source.get("version", ""))
        item["stage"] = source.get("stage", [])
        item["grade_levels"] = source.get("grade_levels", [])
        item["subject"] = source.get("subject", "")
        item["source_url"] = source.get("source_url", "")
        item["retrieved_at"] = source.get("retrieved_at", "")
        item["metadata_snapshot_at"] = source.get("metadata_snapshot_at", "")
        item["status"] = source.get("status", "current")
        item["document_type"] = source.get("document_type", "official_document")
        item["publication_date"] = source.get("publication_date", "")
        item["effective_date"] = source.get("effective_date", "")
        item["source_category"] = source.get("source_category", "official_authority")
        item["credibility"] = source.get("credibility", "highest")
        item["can_be_goal_basis"] = source.get("can_be_goal_basis", "limited")
        item["copyright_scope"] = source.get("copyright_scope", "official_public_reference")
        item["snapshot_id"] = source.get("snapshot_id", "")
        item["content_sha256"] = source.get("content_sha256", "")
        item["content_hash_status"] = source.get("content_hash_status", "not_recorded")
        item["source_record_sha256"] = source.get("source_record_sha256", source.get("source_hash", ""))
        item["verification_status"] = "teacher_confirmed" if source.get("verified_by_teacher") else "candidate"
        # v1 packages metadata and normalized clause candidates, not copied
        # full official documents. A teacher must open the linked source and
        # confirm the exact wording before it becomes formal evidence.
        item["clause_type"] = item.get("clause_type", "normalized_summary")
        yield item


def _db_path(workspace: str | None = None) -> Path:
    return ensure_workspace(workspace)["indexes"] / "evidence.db"


def rebuild_index(workspace: str | None = None) -> str:
    """Build a small SQLite FTS5/BM25 index from packaged public metadata."""
    db_path = _db_path(workspace)
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(
            """
            DROP TABLE IF EXISTS evidence;
            CREATE TABLE evidence (
                evidence_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                document_title TEXT NOT NULL,
                clause_id TEXT NOT NULL,
                clause_text TEXT NOT NULL,
                section_path TEXT NOT NULL,
                stage TEXT NOT NULL,
                subject TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_level TEXT NOT NULL,
                evidence_status TEXT NOT NULL,
                record_json TEXT NOT NULL
            );
            DROP TABLE IF EXISTS evidence_fts;
            CREATE VIRTUAL TABLE evidence_fts USING fts5(
                evidence_id UNINDEXED,
                clause_text,
                section_path,
                document_title,
                keywords
            );
            DROP TABLE IF EXISTS evidence_meta;
            CREATE TABLE evidence_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """
        )
        catalog = load_catalog(workspace)
        for source in catalog.get("sources", _load_bundle(workspace)):
            for clause in _iter_clauses(source):
                clause_id = clause.get("clause_id", "")
                record = {
                    **clause,
                    "evidence_id": f"{clause.get('source_id', '')}:{clause_id}",
                    "evidence_status": "clause_candidate",
                    "provenance_type": "OFFICIAL_STANDARD",
                    "copyright_scope": "official_public_reference",
            "source_snapshot_id": source.get("snapshot_id", ""),
            "content_sha256": source.get("content_sha256", ""),
            "content_hash_status": source.get("content_hash_status", "not_recorded"),
            "source_record_sha256": source.get("source_record_sha256", source.get("source_hash", "")),
            "verification_status": "teacher_confirmed" if source.get("verified_by_teacher") else "candidate",
                }
                evidence_id = record["evidence_id"]
                connection.execute(
                    "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        evidence_id,
                        record.get("source_id", ""),
                        record.get("document_title", ""),
                        clause_id,
                        record.get("clause_text", ""),
                        json.dumps(record.get("section_path", []), ensure_ascii=False),
                        json.dumps(record.get("stage", []), ensure_ascii=False),
                        record.get("subject", ""),
                        record.get("source_url", ""),
                        record.get("source_level", "A1"),
                        record["evidence_status"],
                        json.dumps(record, ensure_ascii=False),
                    ),
                )
                connection.execute(
                    "INSERT INTO evidence_fts VALUES (?, ?, ?, ?, ?)",
                    (
                        evidence_id,
                        record.get("clause_text", ""),
                        " ".join(record.get("section_path", [])) if isinstance(record.get("section_path"), list) else str(record.get("section_path", "")),
                        record.get("document_title", ""),
                        " ".join(record.get("keywords", [])),
                    ),
                )
        connection.execute(
            "INSERT INTO evidence_meta VALUES (?, ?)",
            ("catalog_hash", str(catalog.get("catalog_hash", ""))),
        )
        connection.execute(
            "INSERT INTO evidence_meta VALUES (?, ?)",
            ("snapshot_id", str(catalog.get("snapshot_id", ""))),
        )
        connection.commit()
    finally:
        connection.close()
    return str(db_path)


def _ensure_index(workspace: str | None = None) -> Path:
    path = _db_path(workspace)
    connection = sqlite3.connect(path)
    try:
        exists = connection.execute("SELECT 1 FROM sqlite_master WHERE name='evidence'").fetchone()
        current_hash = ""
        try:
            current_hash = connection.execute(
                "SELECT value FROM evidence_meta WHERE key='catalog_hash'"
            ).fetchone()[0]
        except sqlite3.Error:
            current_hash = ""
    finally:
        connection.close()
    catalog_hash = str(load_catalog(workspace).get("catalog_hash", ""))
    if not exists or current_hash != catalog_hash:
        rebuild_index(workspace)
    return path


def search_official_evidence(query: dict, workspace: str | None = None) -> dict:
    """Return clause-level candidates with metadata and provenance."""
    stage = normalize_stage(query.get("stage"), query.get("grade"))
    subject = normalize_subject(query.get("subject"), stage)
    topic = str(query.get("topic", ""))
    keywords = query.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [keywords]
    aliases = []
    topic_aliases = {
        "循环": ["loop", "迭代", "重复"],
        "分支": ["branch", "条件", "判断"],
        "算法": ["algorithm", "问题解决"],
        "数据": ["data", "计算"],
    }
    for chinese, values in topic_aliases.items():
        if chinese in topic:
            aliases.extend(values)
    query_text = " ".join([topic, *aliases, *[str(item) for item in keywords]]).strip()
    path = _ensure_index(workspace)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        rows = []
        # FTS5's tokenizer is not reliable for every Chinese phrase, so the
        # candidate set is filtered again with deterministic token scoring.
        for row in connection.execute("SELECT * FROM evidence").fetchall():
            stages = json.loads(row["stage"] or "[]")
            if stage == "primary" and not any(s in stages for s in ("primary", "compulsory")):
                continue
            if stage == "junior_secondary" and not any(s in stages for s in ("junior_secondary", "compulsory")):
                continue
            if stage == "senior_secondary" and "senior_secondary" not in stages:
                continue
            if subject and not _evidence_subject_matches(subject, row["subject"]):
                continue
            record = json.loads(row["record_json"])
            haystack = " ".join([
                record.get("document_title", ""),
                record.get("clause_text", ""),
                " ".join(record.get("keywords", [])),
                " ".join(record.get("applicable_topics", [])),
                " ".join(record.get("section_path", [])) if isinstance(record.get("section_path"), list) else str(record.get("section_path", "")),
            ])
            q_tokens = _tokens(query_text)
            score = len(q_tokens & _tokens(haystack)) if q_tokens else 0
            if score == 0 and topic:
                continue
            record["relevance_score"] = round(min(1.0, 0.25 + score / max(4, len(q_tokens) * 2)), 3)
            rows.append(record)
    finally:
        connection.close()

    rows.sort(key=lambda item: item.get("relevance_score", 0), reverse=True)
    matches = rows[:12]
    sources_by_id: dict[str, dict] = {}
    for clause in matches:
        source_id = clause.get("source_id", "")
        sources_by_id.setdefault(source_id, {
            "source_id": source_id,
            "source_name": clause.get("document_title", ""),
            "source_description": "中国教育部公开发布的课程方案/课程标准及相关官方文件",
            "source_level": clause.get("source_level", "A1"),
            "source_category": "official_authority",
            "issuer": clause.get("issuer", ""),
            "credibility": "highest",
            "can_be_goal_basis": "yes",
            "applicable_scenes": ["k12"],
            "stage": clause.get("stage", []),
            "grade_levels": clause.get("grade_levels", []),
            "subject": clause.get("subject", ""),
            "source_url": clause.get("source_url", ""),
            "source_version": clause.get("source_version", clause.get("version", "")),
            "publication_date": clause.get("publication_date", ""),
            "effective_date": clause.get("effective_date", ""),
            "retrieved_at": clause.get("retrieved_at", ""),
            "metadata_snapshot_at": clause.get("metadata_snapshot_at", ""),
            "status": clause.get("status", "current"),
            "document_type": clause.get("document_type", "official_document"),
            "retrieval_status": "found",
            "copyright_scope": "official_public_reference",
            "specific_clauses": [],
            "evidence_status": "clause_candidate",
            "evidence_scope": "metadata_and_normalized_summary_only",
            "provenance_type": "OFFICIAL_STANDARD",
            "source_snapshot_id": clause.get("snapshot_id", ""),
            "content_sha256": clause.get("content_sha256", ""),
            "content_hash_status": clause.get("content_hash_status", "not_recorded"),
            "source_record_sha256": clause.get("source_record_sha256", ""),
            "verified_by_teacher": bool(clause.get("verified_by_teacher")),
        })
        sources_by_id[source_id]["specific_clauses"].append({
            "clause_id": clause.get("clause_id", ""),
            "source_version": clause.get("source_version", clause.get("version", "")),
            "clause_text": clause.get("clause_text", ""),
            "excerpt": clause.get("excerpt", ""),
            "normalized_summary": clause.get("normalized_summary", clause.get("clause_text", "")),
            "section_path": clause.get("section_path", []),
            "page_number": clause.get("page_number", clause.get("page", "")),
            "anchor": clause.get("anchor", ""),
            "supports_modules": clause.get("supports_modules", []),
            "evidence_status": "clause_candidate",
            "clause_type": clause.get("clause_type", "normalized_summary"),
            "content_sha256": clause.get("content_sha256", ""),
            "content_hash_status": clause.get("content_hash_status", "not_recorded"),
            "source_record_sha256": clause.get("source_record_sha256", ""),
            "verification_status": clause.get("verification_status", "candidate"),
        })

    return {
        "status": "found" if matches else "not_found",
        "query": query,
        "matches": matches,
        "sources": list(sources_by_id.values()),
        "evidence_status": "clause_candidate" if matches else "no_source",
        "snapshot_id": load_catalog(workspace).get("snapshot_id", ""),
        "catalog_hash": load_catalog(workspace).get("catalog_hash", ""),
        "index_path": str(path),
        "message": f"找到 {len(matches)} 条条款级候选证据" if matches else "没有找到条款级候选证据",
    }


def confirm_evidence(clause: dict, *, teacher_confirmed: bool = False) -> dict:
    """Move a candidate to a formal state only after explicit confirmation."""
    result = dict(clause)
    if teacher_confirmed:
        result["evidence_status"] = "teacher_confirmed"
        result["verified_by_teacher"] = True
    else:
        result["evidence_status"] = result.get("evidence_status", "clause_candidate")
    return result
