"""Focused integration checks for the v3 nine-subject runtime contract."""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "mcp-server"))

from core.subject_registry import subject_options
from core.evidence_store import search_official_evidence
from server import _is_v3_request, call_tool
from tools.v3_orchestrator import run_v3_design, run_v3_revise


SUBJECT_IDS = (
    "chinese",
    "mathematics",
    "english",
    "physics",
    "chemistry",
    "biology",
    "history",
    "geography",
    "politics",
)


def _request(subject_id: str, *, mode: str = "standard_fast") -> dict:
    return {
        "v3": True,
        "education_scope": "k12_nine_subjects",
        "subject_id": subject_id,
        "grade_level": "初中八年级",
        "topic": f"{subject_id}示例主题",
        "mode": mode,
        "export": False,
    }


class TestV3MultisubjectIntegration(unittest.TestCase):
    def test_registry_exposes_all_nine_subjects_for_each_stage(self):
        self.assertEqual(
            {item["subject_id"] for item in subject_options("小学")},
            {"chinese", "mathematics", "english", "politics"},
        )
        for stage in ("初中", "普通高中"):
            self.assertEqual(
                {item["subject_id"] for item in subject_options(stage)},
                set(SUBJECT_IDS),
            )

    def test_each_subject_runs_through_the_same_design_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            for subject_id in SUBJECT_IDS:
                output_dir = Path(temp) / subject_id
                result = run_v3_design(_request(subject_id), str(output_dir))
                self.assertIn(result["status"], {"completed", "completed_with_warnings"})
                self.assertEqual(result["education_scope"], "k12_nine_subjects")
                self.assertEqual(result["subject_id"], subject_id)
                self.assertEqual(result["project"]["subject_adapter"]["subject_id"], subject_id)
                self.assertTrue(result["project"]["sources"])
                self.assertTrue(result["project"]["objectives"])
                self.assertTrue(result["project"]["assessment_plan"])
                self.assertTrue(result["project"]["instructional_materials"])
                self.assertEqual(result["project"]["mode"]["id"], "standard_fast")
                project_json = output_dir / "v3_design_project.json"
                self.assertTrue(project_json.is_file())
                stored = json.loads(project_json.read_text(encoding="utf-8"))
                self.assertTrue(stored["exports"]["files"])

    def test_collaborative_mode_and_single_objective_revision_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            design_dir = Path(temp) / "design"
            design = run_v3_design(_request("mathematics", mode="collaborative"), str(design_dir))
            self.assertEqual(design["project"]["mode"]["id"], "collaborative")
            objective_id = design["project"]["objectives"][0]["objective_id"]
            revised = run_v3_revise(
                design["project"],
                {
                    "feedback_type": "teacher_feedback",
                    "items": [{
                        "module": "objective",
                        "objective_id": objective_id,
                        "field": "criterion",
                        "value": "提交过程记录，并用一句话说明判断依据",
                    }],
                },
                str(Path(temp) / "revise"),
            )
            self.assertEqual(revised["revision_log"][0]["module"], "objective")
            self.assertEqual(
                revised["project"]["objectives"][0]["criterion"],
                "提交过程记录，并用一句话说明判断依据",
            )

    def test_mcp_routes_explicit_v3_request_to_v3_orchestrator(self):
        with tempfile.TemporaryDirectory() as temp:
            response = asyncio.run(call_tool(
                "dc_design_session",
                {
                    **_request("english"),
                    "topic": "英语说明文阅读",
                    "output_dir": temp,
                },
            ))
        payload = json.loads(response[0].text)
        self.assertEqual(payload["education_scope"], "k12_nine_subjects")
        self.assertEqual(payload["subject_id"], "english")
        self.assertEqual(payload["project"]["schema_version"], "3.0.0")

    def test_mcp_infers_v3_from_subject_without_treating_grade_as_stage(self):
        self.assertTrue(_is_v3_request({
            "subject": "数学",
            "grade_level": "八年级",
            "topic": "一次函数",
        }))

    def test_shared_evidence_search_does_not_leak_other_subjects(self):
        with tempfile.TemporaryDirectory() as temp:
            result = search_official_evidence(
                {"stage": "高中", "subject": "信息技术", "topic": "算法"},
                temp,
            )
        self.assertTrue(result["sources"])
        self.assertTrue(all(
            source.get("subject") in {"信息技术", "信息科技", "通用"}
            for source in result["sources"]
        ))


if __name__ == "__main__":
    unittest.main()
