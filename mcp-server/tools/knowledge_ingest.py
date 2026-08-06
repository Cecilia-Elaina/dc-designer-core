"""
Knowledge Ingest MCP Tools

Manages a teacher's private knowledge base. Files are stored in:
- data/knowledge_base/documents/ (actual files)
- data/knowledge_base/indexes/   (JSON index)

Supports ingesting documents with metadata, searching by keywords/subject/grade,
converting entries to source.schema.json-compatible records, and detecting
suspected student personal information.
"""

import sys
import os
import re
import json
import uuid
import shutil
import hashlib
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from core.ids import gen_source_id

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

try:
    from core.runtime_paths import ensure_workspace
    _LOCAL_DIRS = ensure_workspace()
    _BASE_DATA_DIR = str(_LOCAL_DIRS["knowledge"])
except Exception:
    # Legacy tests/imports can still run if the new core package is unavailable.
    _BASE_DATA_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "knowledge_base",
    )
_DOCUMENTS_DIR = os.path.join(_BASE_DATA_DIR, "documents")
_INDEXES_DIR = os.path.join(_BASE_DATA_DIR, "indexes")
_INDEX_FILE = os.path.join(_INDEXES_DIR, "knowledge_index.json")

# ---------------------------------------------------------------------------
# Required metadata keys for ingestion
# ---------------------------------------------------------------------------

_REQUIRED_META_KEYS = (
    "document_type",
    "subject",
    "grade_level",
    "topic",
    "copyright_scope",
    "use_scope",
)

# ---------------------------------------------------------------------------
# Personal-information detection patterns (Chinese context)
# ---------------------------------------------------------------------------

# Pattern: a Chinese-name-shaped token plus score on the same line.
_PAT_NAME_SCORE = re.compile(
    r"[一-鿿]{2,4}\s*[\d]{1,3}\s*分"
)

# Student ID (学号)
_PAT_STUDENT_ID = re.compile(
    r"(?:学号|学籍号|student\s*id)\s*[:：]?\s*[\w\d\-]{4,20}",
    re.IGNORECASE,
)

# Chinese ID card number (18 digits, last may be X)
_PAT_ID_CARD = re.compile(
    r"[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]"
)

# Phone number (mobile)
_PAT_PHONE = re.compile(
    r"(?:手机|电话|联系电话|phone)\s*[:：]?\s*1[3-9]\d{9}",
    re.IGNORECASE,
)

# Address (家庭住址)
_PAT_ADDRESS = re.compile(
    r"(?:家庭住址|家庭地址|现住址|通讯地址|address)\s*[:：]?\s*.{5,60}",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_dirs() -> None:
    """Create storage directories if they do not exist."""
    os.makedirs(_DOCUMENTS_DIR, exist_ok=True)
    os.makedirs(_INDEXES_DIR, exist_ok=True)


def _load_index() -> list[dict]:
    """Load the master index from disk. Returns an empty list if missing."""
    if not os.path.isfile(_INDEX_FILE):
        return []
    with open(_INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_index(entries: list[dict]) -> None:
    """Persist the master index to disk."""
    _ensure_dirs()
    with open(_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def _gen_document_id() -> str:
    """Generate a unique document identifier."""
    return f"kb_{uuid.uuid4().hex[:12]}"


def _safe_filename(original_name: str) -> str:
    """Sanitise a filename while preserving the extension."""
    base, ext = os.path.splitext(original_name)
    # Replace path separators and other problematic characters
    safe = re.sub(r'[\\/:*?"<>|]', "_", base)
    safe = safe.strip(". ")
    if not safe:
        safe = "document"
    return f"{safe}{ext}"


def _file_checksum(path: str) -> str:
    """SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_snippet(text: str, max_len: int = 200) -> str:
    """Return a short snippet from text content."""
    text = text.strip().replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ingest_document(file_path: str, metadata: dict) -> dict:
    """Ingest a teacher's document into the knowledge base.

    Copies the file to ``data/knowledge_base/documents/``, creates an index
    entry in ``data/knowledge_base/indexes/knowledge_index.json``, and
    optionally inspects the file text for suspected student personal
    information.

    Parameters
    ----------
    file_path : str
        Absolute or relative path to the source file on disk.
    metadata : dict
        Must include: ``document_type``, ``subject``, ``grade_level``,
        ``topic``, ``copyright_scope``, ``use_scope``.

    Returns
    -------
    dict
        ``{ingested: bool, document_id: str, warnings: list, index_path: str}``

    Raises
    ------
    FileNotFoundError
        If *file_path* does not exist.
    ValueError
        If required metadata keys are missing.
    """
    _ensure_dirs()

    # --- Validate file exists -----------------------------------------------
    abs_path = os.path.abspath(file_path)
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"File not found: {abs_path}")

    # --- Validate required metadata -----------------------------------------
    missing = [k for k in _REQUIRED_META_KEYS if k not in metadata or not metadata[k]]
    if missing:
        raise ValueError(
            f"Missing required metadata keys: {', '.join(missing)}"
        )

    # --- Copy file to documents directory -----------------------------------
    doc_id = _gen_document_id()
    dest_name = _safe_filename(os.path.basename(abs_path))
    # Prefix with doc_id to avoid collisions
    dest_name = f"{doc_id}_{dest_name}"
    dest_path = os.path.join(_DOCUMENTS_DIR, dest_name)
    shutil.copy2(abs_path, dest_path)

    # --- Read text for personal-info check -----------------------------------
    warnings: list[str] = []
    try:
        with open(dest_path, "r", encoding="utf-8", errors="ignore") as f:
            content_text = f.read()
        warnings.extend(_check_personal_info(content_text))
    except (UnicodeDecodeError, PermissionError):
        # Binary file -- skip text-based personal-info check
        pass

    # --- Build index entry ---------------------------------------------------
    now = datetime.now().isoformat()
    entry = {
        "document_id": doc_id,
        "title": metadata.get("title", os.path.basename(abs_path)),
        "file_name": dest_name,
        "file_path": dest_path,
        "file_size_bytes": os.path.getsize(dest_path),
        "file_checksum_sha256": _file_checksum(dest_path),
        "document_type": metadata["document_type"],
        "subject": metadata["subject"],
        "grade_level": metadata["grade_level"],
        "topic": metadata["topic"],
        "copyright_scope": metadata["copyright_scope"],
        "use_scope": metadata["use_scope"],
        "ingested_at": now,
        "updated_at": now,
    }

    # Merge any extra metadata fields the caller provided
    for k, v in metadata.items():
        if k not in entry and k not in _REQUIRED_META_KEYS:
            entry[k] = v

    # --- Persist index -------------------------------------------------------
    index_entries = _load_index()
    index_entries.append(entry)
    _save_index(index_entries)

    return {
        "ingested": True,
        "document_id": doc_id,
        "warnings": warnings,
        "index_path": _INDEX_FILE,
    }


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_knowledge_base(query: dict) -> dict:
    """Search the teacher's knowledge base by keywords and filters.

    Parameters
    ----------
    query : dict
        Supported keys (all optional):
        - ``keywords``  (str)  -- free-text keywords to match against title
          and topic.
        - ``subject``   (str)  -- filter by subject.
        - ``grade_level`` (str) -- filter by grade level.
        - ``topic``     (str)  -- filter by topic.
        - ``document_type`` (str) -- filter by document type.

    Returns
    -------
    dict
        ``{status: str, matches: list, total_count: int}``

        Each match contains: ``document_id``, ``title``, ``subject``,
        ``grade_level``, ``topic``, ``document_type``, ``file_path``,
        ``snippet``.
    """
    index_entries = _load_index()
    keywords = (query.get("keywords") or "").strip().lower()
    filter_subject = (query.get("subject") or "").strip().lower()
    filter_grade = (query.get("grade_level") or "").strip().lower()
    filter_topic = (query.get("topic") or "").strip().lower()
    filter_type = (query.get("document_type") or "").strip().lower()

    matches: list[dict] = []

    for entry in index_entries:
        # --- Apply filters ---------------------------------------------------
        if filter_subject and entry.get("subject", "").lower() != filter_subject:
            continue
        if filter_grade and entry.get("grade_level", "").lower() != filter_grade:
            continue
        if filter_topic and filter_topic not in entry.get("topic", "").lower():
            continue
        if filter_type and entry.get("document_type", "").lower() != filter_type:
            continue

        # --- Keyword matching ------------------------------------------------
        if keywords:
            searchable = " ".join([
                entry.get("title", ""),
                entry.get("topic", ""),
                entry.get("document_type", ""),
            ]).lower()
            # Simple word-level matching: all keywords must appear
            kw_parts = keywords.split()
            if not all(kw in searchable for kw in kw_parts):
                continue

        # --- Build snippet ---------------------------------------------------
        snippet = _make_snippet(entry.get("topic", entry.get("title", "")))

        matches.append({
            "document_id": entry.get("document_id", ""),
            "title": entry.get("title", ""),
            "subject": entry.get("subject", ""),
            "grade_level": entry.get("grade_level", ""),
            "topic": entry.get("topic", ""),
            "document_type": entry.get("document_type", ""),
            "file_path": entry.get("file_path", ""),
            "snippet": snippet,
        })

    return {
        "status": "ok",
        "matches": matches,
        "total_count": len(matches),
    }


# ---------------------------------------------------------------------------
# Source record conversion
# ---------------------------------------------------------------------------

def build_source_record_from_document(document: dict) -> dict:
    """Convert a knowledge-base document entry into a source.schema.json record.

    The generated record sets ``copyright_scope`` to
    ``teacher_private_use_only`` and ``use_scope`` to
    ``[private_reference_only]`` by default, ensuring teacher-uploaded
    material is never mistakenly treated as a public or official source.

    Parameters
    ----------
    document : dict
        A single document entry as returned by ``ingest_document`` or
        stored in the index.

    Returns
    -------
    dict
        A dict conforming to ``source.schema.json`` with the key
        ``source_id`` auto-generated and credibility set to ``"medium"``.
    """
    title = document.get("title", "Untitled Document")
    doc_type = document.get("document_type", "reference")

    # Map document_type to source_category
    category_map = {
        "curriculum_standard": "official_authority",
        "textbook": "professional_authority",
        "exam_outline": "professional_authority",
        "teaching_reference": "professional_authority",
        "research_paper": "professional_authority",
        "teacher_notes": "teacher_private",
        "worksheet": "teacher_private",
        "presentation": "teacher_private",
        "other": "public",
    }
    source_category = category_map.get(doc_type, "teacher_private")

    # Determine source_level from copyright / document type
    source_level_map = {
        "curriculum_standard": "A1",
        "textbook": "B1",
        "exam_outline": "B2",
        "teaching_reference": "C1",
        "research_paper": "C2",
    }
    source_level = source_level_map.get(doc_type, "E1")

    # can_be_goal_basis for teacher-private is always "limited"
    can_be_goal_basis = "limited" if source_category == "teacher_private" else "no"

    now = datetime.now().isoformat()

    return {
        "source_id": gen_source_id(),
        "source_level": source_level,
        "source_category": source_category,
        "source_name": title,
        "source_description": document.get("topic", ""),
        "source_url": document.get("file_path", ""),
        "source_date": document.get("ingested_at", now),
        "credibility": "medium",
        "can_be_goal_basis": can_be_goal_basis,
        "applicable_scenes": ["k12"],
        "specific_clauses": [],
        "verified_by_teacher": True,
        "verification_date": now,
        "notes": (
            f"从教师私有知识库导入，文档类型: {doc_type}，"
            f"学科: {document.get('subject', '未知')}，"
            f"年级: {document.get('grade_level', '未知')}"
        ),
        "retrieval_status": "user_uploaded",
        "copyright_scope": "teacher_private_use_only",
        "use_scope": ["private_reference_only"],
        "fallback_required": True,
    }


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

def list_knowledge_documents(filter_dict: Optional[dict] = None) -> dict:
    """List all documents in the knowledge base with optional filters.

    Parameters
    ----------
    filter_dict : dict or None
        Optional filter criteria.  Supported keys: ``subject``,
        ``grade_level``, ``document_type``.  Values are compared
        case-insensitively.

    Returns
    -------
    dict
        ``{status: str, documents: list, total_count: int}``

        Each document contains: ``document_id``, ``title``, ``subject``,
        ``grade_level``, ``topic``, ``document_type``, ``file_path``,
        ``ingested_at``.
    """
    index_entries = _load_index()
    filter_dict = filter_dict or {}

    results: list[dict] = []
    for entry in index_entries:
        if "subject" in filter_dict:
            if entry.get("subject", "").lower() != filter_dict["subject"].lower():
                continue
        if "grade_level" in filter_dict:
            if entry.get("grade_level", "").lower() != filter_dict["grade_level"].lower():
                continue
        if "document_type" in filter_dict:
            if entry.get("document_type", "").lower() != filter_dict["document_type"].lower():
                continue

        results.append({
            "document_id": entry.get("document_id", ""),
            "title": entry.get("title", ""),
            "subject": entry.get("subject", ""),
            "grade_level": entry.get("grade_level", ""),
            "topic": entry.get("topic", ""),
            "document_type": entry.get("document_type", ""),
            "file_path": entry.get("file_path", ""),
            "ingested_at": entry.get("ingested_at", ""),
        })

    return {
        "status": "ok",
        "documents": results,
        "total_count": len(results),
    }


# ---------------------------------------------------------------------------
# Personal-information detection
# ---------------------------------------------------------------------------

def _check_personal_info(text: str) -> list:
    """Check text for suspected student personal information.

    Scans for the following patterns and returns a list of warning messages
    for every hit found:

    - **姓名+分数** -- A Chinese-name-shaped token immediately followed by a
      numeric score (for example, ``"学生甲 98分"``).
    - **学号** -- Student ID numbers.
    - **身份证号** -- 18-digit Chinese national ID card numbers.
    - **手机号** -- Mobile phone numbers.
    - **家庭住址** -- Home / mailing addresses.

    Parameters
    ----------
    text : str
        The text content to inspect.

    Returns
    -------
    list[str]
        Warning messages, one per detected pattern.
    """
    warnings: list[str] = []

    if not text:
        return warnings

    if _PAT_NAME_SCORE.search(text):
        warnings.append(
            "检测到疑似学生姓名+分数信息，建议在导出或共享前脱敏处理"
        )

    if _PAT_STUDENT_ID.search(text):
        warnings.append(
            "检测到疑似学号信息，建议在导出或共享前脱敏处理"
        )

    if _PAT_ID_CARD.search(text):
        warnings.append(
            "检测到疑似身份证号信息，建议在导出或共享前脱敏处理"
        )

    if _PAT_PHONE.search(text):
        warnings.append(
            "检测到疑似手机号信息，建议在导出或共享前脱敏处理"
        )

    if _PAT_ADDRESS.search(text):
        warnings.append(
            "检测到疑似家庭住址信息，建议在导出或共享前脱敏处理"
        )

    return warnings
