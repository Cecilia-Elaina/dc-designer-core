"""Product-level acceptance tests for the Codex v1 information-tech plugin."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp-server"))

from core.evidence_store import search_official_evidence
from core.local_knowledge import ingest_private_document
from core.product_config import normalize_stage, validate_scope
from core.runtime_paths import workspace_root
from tools.drawio_exporter import generate_drawio_workbook_xml
from tools.skill_graph import build_skill_graph_views, validate_skill_graph_views
from tools.teacher_memory import read_teacher_profile, write_teacher_profile
from tools.v1_orchestrator import run_v1_design, run_v1_review, run_v1_revise


class TestV1ManifestAndScope(unittest.TestCase):
    def test_codex_manifest_exposes_only_three_v1_skills(self):
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir()), [
            "dc-info-tech-design", "dc-info-tech-review", "dc-info-tech-revise"
        ])
        self.assertNotIn("higher", json.dumps(manifest, ensure_ascii=False).lower())
        self.assertNotIn("corporate", json.dumps(manifest, ensure_ascii=False).lower())

    def test_stage_normalization_handles_high_school_before_numerals(self):
        self.assertEqual(normalize_stage("高中", "高一"), "senior_secondary")
        self.assertEqual(normalize_stage("", "七年级"), "junior_secondary")
        self.assertEqual(normalize_stage("", "六年级"), "primary")

    def test_scope_rejects_other_subjects_and_user_types(self):
        self.assertFalse(validate_scope({"subject": "数学", "grade_level": "七年级"})["valid"])
        self.assertFalse(validate_scope({"subject": "信息科技", "grade_level": "七年级", "user_type": "高校教师"})["valid"])
        self.assertTrue(validate_scope({"subject": "信息科技", "grade_level": "七年级"})["valid"])

    def test_default_workspace_is_not_plugin_directory(self):
        self.assertNotIn(str(ROOT).lower(), str(workspace_root()).lower())


class TestV1EvidenceAndPrivateKnowledge(unittest.TestCase):
    def test_official_search_returns_traceable_clause_candidate(self):
        with tempfile.TemporaryDirectory() as workspace:
            result = search_official_evidence({
                "stage": "junior_secondary",
                "subject": "信息科技",
                "topic": "算法与程序设计",
            }, workspace)
        self.assertEqual(result["status"], "found")
        self.assertTrue(result["sources"])
        source = result["sources"][0]
        self.assertEqual(source["source_level"], "A1")
        self.assertTrue(source["source_url"].startswith("https://"))
        self.assertTrue(source["specific_clauses"])
        self.assertEqual(source["specific_clauses"][0]["clause_type"], "normalized_summary")
        self.assertEqual(source["evidence_status"], "clause_candidate")

    def test_private_document_is_local_c1_and_pii_is_blocked(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            workspace = root_path / "teacher-workspace"
            clean = root_path / "校本经验.md"
            clean.write_text("本班共性困难：学生容易遗漏边界测试。", encoding="utf-8")
            result = ingest_private_document(str(clean), {"subject": "信息科技"}, workspace=str(workspace))
            self.assertEqual(result["status"], "ok")
            record = result["source_record"]
            self.assertEqual(record["source_level"], "C1")
            self.assertEqual(record["source_category"], "teacher_private")
            self.assertFalse(record["distribution_allowed"])
            self.assertNotIn(str(ROOT).lower(), record["file_path"].lower())

            pii = root_path / "学生成绩.md"
            pii.write_text("张三 95分", encoding="utf-8")
            blocked = ingest_private_document(str(pii), {"subject": "信息科技"}, workspace=str(workspace))
            self.assertEqual(blocked["status"], "blocked_privacy")
            self.assertFalse(blocked["ingested"])

    def test_teacher_memory_requires_consent_and_rejects_student_identity(self):
        with tempfile.TemporaryDirectory() as root:
            old = os.environ.get("DC_DESIGNER_HOME")
            os.environ["DC_DESIGNER_HOME"] = root
            try:
                with self.assertRaises(PermissionError):
                    write_teacher_profile("teacher-1", {"school_type": "普通中学"}, False)
                result = write_teacher_profile("teacher-1", {"school_type": "普通中学", "preferences": {"font": "SimSun"}}, True)
                self.assertTrue(result["consent_recorded"])
                self.assertEqual(read_teacher_profile("teacher-1")["school_type"], "普通中学")
                with self.assertRaises(ValueError):
                    write_teacher_profile("teacher-1", {"student_id": "S001"}, True)
            finally:
                if old is None:
                    os.environ.pop("DC_DESIGNER_HOME", None)
                else:
                    os.environ["DC_DESIGNER_HOME"] = old


def _request(confirmations=None):
    request = {
        "education_scope": "k12_info_technology",
        "subject": "信息科技",
        "stage": "junior_secondary",
        "grade_level": "七年级",
        "topic": "Python 分支结构",
        "textbook_version": "教师提供教材版本",
        "unit": "程序设计单元",
        "periods": "2课时",
        "equipment": "Windows、Python、VSCode",
        "class_profile": {"ability_level": "差异较大", "common_difficulties": ["边界测试不完整"]},
        "mode": "standard_fast",
    }
    if confirmations is not None:
        request["confirmations"] = confirmations
    return request


class TestV1EndToEndDesign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        cls.workspace = root / "workspace"
        cls.output = root / "design"
        cls.result = run_v1_design(_request(), str(cls.output), str(cls.workspace))
        cls.project = cls.result["project"]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_design_is_draft_until_teacher_confirmations(self):
        self.assertEqual(self.result["status"], "completed_with_warnings")
        self.assertFalse(self.result["can_export_final"])
        self.assertTrue(self.result["required_confirmations"])

    def test_goal_and_performance_model_is_complete(self):
        goal = self.project["goal"]
        performance = self.project["performance_analysis"]
        self.assertTrue(goal["condition"])
        self.assertTrue(goal["behavior"])
        self.assertTrue(goal["criterion"])
        self.assertIn(goal["behavior"], goal["full_statement"])
        self.assertIn(goal["criterion"], goal["full_statement"])
        self.assertIn("达到标准", goal["full_statement"])
        self.assertIn(goal["behavior"], performance["expected_performance"])
        self.assertIn("待验证", performance["current_performance"])
        self.assertEqual(self.project["skill_graph"]["goal_type"], "mixed")

    def test_graph_has_two_independent_views_and_control_flow(self):
        graph = self.project["skill_graph"]
        views = build_skill_graph_views(graph)
        check = validate_skill_graph_views(views)
        self.assertEqual(check["status"], "pass", check["errors"])
        self.assertEqual(set((node["node_type"] for node in views["goal_operation_flow"]["nodes"])), {"instructional_goal", "goal_step"})
        self.assertIn("skill_hierarchy", views)
        self.assertIn("control_flow", views)
        self.assertTrue(any(node["node_type"] == "decision" for node in views["control_flow"]["nodes"]))
        self.assertTrue(any(edge.get("label") == "是" for edge in views["control_flow"]["edges"]))
        self.assertTrue(any(edge.get("label") == "否" for edge in views["control_flow"]["edges"]))
        self.assertTrue(any(edge.get("edge_type") == "feedback" for edge in views["control_flow"]["edges"]))

    def test_drawio_workbook_is_editable_xml_with_three_pages(self):
        xml = generate_drawio_workbook_xml(self.project["skill_graph"])
        root = ET.fromstring(xml)
        self.assertGreaterEqual(len(root.findall("diagram")), 3)
        self.assertIn("rhombus=1", xml)
        self.assertIn("条件是否满足", xml)

    def test_export_contains_stable_word_files_and_images(self):
        files = self.result["export"]["files"]
        report = Path(files["dc_report"])
        self.assertTrue(report.is_file())
        self.assertTrue((report.parent / "教学系统设计报告.docx").is_file())
        self.assertTrue((report.parent / "学生学习单.docx").is_file())
        self.assertEqual(self.result["export_status"], "success")
        self.assertTrue(Path(files["goal_operation_png"]).is_file())
        self.assertTrue(Path(files["skill_hierarchy_png"]).is_file())
        self.assertTrue(Path(files["control_flow_png"]).is_file())
        with zipfile.ZipFile(report) as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")
            media = [name for name in archive.namelist() if name.startswith("word/media/")]
        self.assertGreaterEqual(document_xml.count("w:drawing"), 4)
        self.assertGreaterEqual(len(media), 4)
        self.assertNotIn("{'objective_id'", document_xml)

    def test_pillow_graph_fallback_is_available(self):
        import tools.document_exporter as exporter

        original = exporter.HAS_MATPLOTLIB
        exporter.HAS_MATPLOTLIB = False
        try:
            image = exporter._create_v1_graph_image(self.project, "skill_hierarchy")
        finally:
            exporter.HAS_MATPLOTLIB = original
        self.assertIsNotNone(image)
        self.assertGreater(len(image.getvalue()), 1000)

    def test_confirmed_request_can_reach_final_gate(self):
        keys = [item["confirmation_id"] for item in self.result["required_confirmations"]]
        confirmations = {key: True for key in keys}
        with tempfile.TemporaryDirectory() as root:
            result = run_v1_design(_request(confirmations), str(Path(root) / "confirmed"), str(Path(root) / "workspace"))
        self.assertTrue(result["can_export_final"], result["final_blocking_reasons"])
        self.assertEqual(result["project"]["quality"]["evidence_status"], "teacher_confirmed")

    def test_review_and_revise_return_actionable_records(self):
        review = run_v1_review(str(self.output / "project.json"), str(self.output / "review"), str(self.workspace))
        for finding in review["findings"]:
            for key in ("finding_id", "type", "severity", "description", "evidence", "suggested_fix", "affected_modules", "related_quality_gate"):
                self.assertIn(key, finding)
        revise = run_v1_revise(str(self.output / "project.json"), {
            "feedback_type": "teacher_feedback",
            "items": [{"module": "instructional_strategy", "description": "增加边界测试讨论"}],
        }, str(self.output / "revise"), str(self.workspace))
        self.assertIn("pre_revision_alignment", revise)
        self.assertIn("post_revision_alignment", revise)
        self.assertIn("impact_analysis", revise["revision_record"])
        self.assertIn("unresolved_items", revise)


class TestV1MCPRouting(unittest.TestCase):
    def test_explicit_v1_design_uses_local_core(self):
        from server import call_tool

        async def invoke():
            return await call_tool("dc_design_session", {
                **_request(),
                "v1": True,
                "output_dir": tempfile.mkdtemp(),
            })

        blocks = asyncio.run(invoke())
        payload = json.loads(blocks[0].text)
        self.assertEqual(payload["education_scope"], "k12_info_technology")
        self.assertIn("required_confirmations", payload)


if __name__ == "__main__":
    unittest.main()
