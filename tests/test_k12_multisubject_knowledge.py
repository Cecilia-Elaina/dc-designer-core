"""Focused checks for the v3 K-12 nine-subject knowledge metadata."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "mcp-server"))

from tools.standards_search import search_standards


SUBJECTS = {
    "语文": "chinese",
    "数学": "mathematics",
    "英语": "english",
    "物理": "physics",
    "化学": "chemistry",
    "生物": "biology",
    "历史": "history",
    "地理": "geography",
    "政治": "politics",
}


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_each_subject_has_compulsory_and_senior_records():
    for display_name, subject_id in SUBJECTS.items():
        compulsory = REPO_ROOT / "data" / "standards" / "k12" / f"{subject_id}_compulsory_2022.json"
        senior = REPO_ROOT / "data" / "standards" / "high_school" / f"{subject_id}_2017_2020.json"
        for path in (compulsory, senior):
            record = _read_json(path)
            assert record["subject_id"] == subject_id
            assert record["source_level"] == "A1"
            assert len(record["content_sha256"]) == 64
            assert record["clauses"]
            assert record["teacher_confirmation_required"] is True
        assert display_name in (
            _read_json(compulsory)["aliases"]
            + _read_json(senior)["aliases"]
            + [_read_json(compulsory)["subject"], _read_json(senior)["subject"]]
        )


def test_search_respects_stage_for_nine_subjects():
    for display_name in SUBJECTS:
        result = search_standards({
            "stage": "高中",
            "subject": display_name,
            "topic": "课程目标与学习表现",
        })
        assert result["status"] in ("found", "partial")
        assert result["matches"]
        assert all(match["stage"] == "senior_secondary" for match in result["matches"])


def test_search_returns_compulsory_record_for_junior_query():
    result = search_standards({
        "stage": "初中",
        "subject": "数学",
        "topic": "建模与问题解决",
    })
    assert result["status"] in ("found", "partial")
    assert result["matches"]
    assert all(match["stage"] == "compulsory" for match in result["matches"])


def test_politics_uses_stage_specific_public_names():
    compulsory = search_standards({"stage": "初中", "subject": "政治", "topic": "法治"})
    senior = search_standards({"stage": "高中", "subject": "政治", "topic": "公共参与"})
    assert compulsory["matches"][0]["subject"] == "道德与法治"
    assert senior["matches"][0]["subject"] == "思想政治"


def test_getting_source_preserves_clause_candidates():
    result = search_standards({"stage": "高中", "subject": "生物", "topic": "遗传"})
    assert result["sources"]
    source = result["sources"][0]
    assert source["source_url"].startswith("https://www.moe.gov.cn/")
    assert source["specific_clauses"]
    assert source["content_hash_status"] == "local_original_verified_not_packaged"


def test_public_registry_contains_no_absolute_private_source_path():
    paths = [
        REPO_ROOT / "data" / "standards" / "source_registry.json",
        REPO_ROOT / "data" / "standards" / "subject_registry_v3.json",
    ]
    paths.extend((REPO_ROOT / "data" / "standards" / "k12").glob("*.json"))
    paths.extend((REPO_ROOT / "data" / "standards" / "high_school").glob("*.json"))
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "D:\\Download" not in text
        assert "D:/Download" not in text
        assert "C:\\Users" not in text


def test_snapshot_contains_the_eighteen_v3_sources():
    snapshot = _read_json(REPO_ROOT / "data" / "standards" / "k12" / "official_snapshot.json")
    source_ids = {source["source_id"] for source in snapshot["sources"]}
    expected = {
        f"std_compulsory_2022_{subject_id if subject_id != 'mathematics' else 'math'}"
        for subject_id in SUBJECTS.values()
    }
    expected.update(
        f"std_senior_2017_2020_{subject_id if subject_id != 'mathematics' else 'math'}"
        for subject_id in SUBJECTS.values()
    )
    assert expected <= source_ids
