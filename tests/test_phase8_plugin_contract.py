"""
Phase 8: Plugin Contract and MCP Tool Verification Tests
"""
import sys
import os
import json
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mcp-server'))

REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


# ======================================================================
# 1. Plugin Manifest Contract
# ======================================================================

class TestPluginManifestContract(unittest.TestCase):
    """Test: manifest.json, plugin.json, .mcp.json exist and are consistent."""

    def test_manifest_json_exists(self):
        self.assertTrue(os.path.exists(os.path.join(REPO_ROOT, "manifest.json")))

    def test_plugin_json_exists(self):
        self.assertTrue(os.path.exists(os.path.join(REPO_ROOT, ".codex-plugin", "plugin.json")))

    def test_mcp_json_exists(self):
        self.assertTrue(os.path.exists(os.path.join(REPO_ROOT, ".mcp.json")))

    def test_plugin_json_has_correct_name(self):
        with open(os.path.join(REPO_ROOT, ".codex-plugin", "plugin.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["name"], "dc-designer-core")

    def test_plugin_json_has_three_modes(self):
        with open(os.path.join(REPO_ROOT, ".codex-plugin", "plugin.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(sorted(os.listdir(os.path.join(REPO_ROOT, "skills"))), [
            "dc-info-tech-design", "dc-info-tech-review", "dc-info-tech-revise"
        ])
        self.assertEqual(data.get("skills"), "./skills/")

    def test_plugin_json_description_not_wrong_positioning(self):
        with open(os.path.join(REPO_ROOT, ".codex-plugin", "plugin.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        desc = data.get("description", "")
        self.assertNotIn("自动教案机", desc)
        self.assertNotIn("全自动生成最终教案", desc)
        self.assertIn("教学系统设计", desc)

    def test_mcp_json_has_server_config(self):
        with open(os.path.join(REPO_ROOT, ".mcp.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        servers = data.get("mcpServers", {})
        self.assertIn("dc-designer-mcp", servers)
        self.assertEqual(servers["dc-designer-mcp"]["command"], "python")


# ======================================================================
# 2. MCP Tool Discovery
# ======================================================================

class TestMCPToolDiscovery(unittest.TestCase):
    """Test: MCP server tools are properly defined."""

    def test_server_has_tools(self):
        from server import TOOLS
        self.assertTrue(len(TOOLS) >= 4, f"Expected >= 4 tools, got {len(TOOLS)}")

    def test_design_session_tool_exists(self):
        from server import TOOLS
        names = [t["name"] for t in TOOLS]
        self.assertIn("dc_design_session", names)

    def test_review_session_tool_exists(self):
        from server import TOOLS
        names = [t["name"] for t in TOOLS]
        self.assertIn("dc_review_session", names)

    def test_revise_session_tool_exists(self):
        from server import TOOLS
        names = [t["name"] for t in TOOLS]
        self.assertIn("dc_revise_session", names)

    def test_export_package_tool_exists(self):
        from server import TOOLS
        names = [t["name"] for t in TOOLS]
        self.assertIn("dc_export_package", names)

    def test_all_tools_have_description(self):
        from server import TOOLS
        for tool in TOOLS:
            self.assertTrue(tool.get("description"), f"Tool {tool['name']} missing description")

    def test_all_tools_have_input_schema(self):
        from server import TOOLS
        for tool in TOOLS:
            self.assertIn("inputSchema", tool, f"Tool {tool['name']} missing inputSchema")


# ======================================================================
# 3. Design Session via MCP Tool
# ======================================================================

class TestMCPDesignSession(unittest.TestCase):
    """Test: dc_design_session via agent_session."""

    @classmethod
    def setUpClass(cls):
        from tools.agent_session import run_agent_session
        cls.result = run_agent_session({
            "mode": "dc-design",
            "user_type": "K12教师",
            "scenario": "新课设计",
            "subject": "信息科技",
            "grade_level": "七年级",
            "topic": "认识算法",
            "teacher_inputs": {
                "prior_knowledge": "学生能描述做事步骤",
                "common_difficulties": ["步骤笼统"],
                "available_media": ["黑板", "投影"],
                "devices": "不保证一人一机"
            }
        }, "exports/phase8")

    def test_mode_is_dc_design(self):
        self.assertEqual(self.result["mode"], "dc-design")

    def test_status_is_completed_with_warnings(self):
        self.assertEqual(self.result["status"], "completed_with_warnings")

    def test_can_export_final_is_false(self):
        self.assertFalse(self.result.get("can_export_final", True))

    def test_final_blocking_reasons_non_empty(self):
        blocking = self.result.get("final_blocking_reasons", [])
        self.assertTrue(len(blocking) > 0)

    def test_required_confirmations_non_empty(self):
        confs = self.result.get("required_confirmations", [])
        self.assertTrue(len(confs) > 0)

    def test_export_result_has_files(self):
        er = self.result.get("export_result", {})
        for key in ["full_report_docx", "lesson_plan_docx", "student_worksheet_docx",
                    "alignment_matrix_xlsx", "ai_process_record_docx"]:
            path = er.get(key)
            self.assertTrue(path, f"export_result.{key} is empty")
            self.assertTrue(os.path.exists(path), f"export_result.{key} file missing")

    def test_tool_status_report_has_tools(self):
        tsr = self.result.get("tool_status_report", [])
        self.assertTrue(len(tsr) >= 10, f"tool_status_report has only {len(tsr)} tools")


# ======================================================================
# 4. Review Session
# ======================================================================

class TestMCPReviewSession(unittest.TestCase):
    """Test: dc_review_session via agent_session."""

    @classmethod
    def setUpClass(cls):
        from tools.agent_session import run_agent_session
        # First run design
        design = run_agent_session({
            "mode": "dc-design", "user_type": "K12教师", "scenario": "新课设计",
            "subject": "信息科技", "grade_level": "七年级", "topic": "认识算法",
            "teacher_inputs": {}
        }, "exports/phase8")
        project_path = design.get("export_result", {}).get("project_json", "")
        # Then review
        cls.result = run_agent_session({
            "mode": "dc-review",
            "existing_design_project_path": project_path,
        }, "exports/phase8")

    def test_mode_is_dc_review(self):
        self.assertEqual(self.result["mode"], "dc-review")

    def test_findings_non_empty(self):
        findings = self.result.get("findings", [])
        self.assertTrue(len(findings) > 0, "Review should find issues")

    def test_overall_assessment_not_pass(self):
        rr = self.result.get("review_report", {})
        self.assertNotEqual(rr.get("overall_assessment", "pass"), "pass")


# ======================================================================
# 5. Revise Session
# ======================================================================

class TestMCPReviseSession(unittest.TestCase):
    """Test: dc_revise_session via agent_session."""

    @classmethod
    def setUpClass(cls):
        from tools.agent_session import run_agent_session
        design = run_agent_session({
            "mode": "dc-design", "user_type": "K12教师", "scenario": "新课设计",
            "subject": "信息科技", "grade_level": "七年级", "topic": "认识算法",
            "teacher_inputs": {}
        }, "exports/phase8")
        project_path = design.get("export_result", {}).get("project_json", "")
        cls.result = run_agent_session({
            "mode": "dc-revise",
            "existing_design_project_path": project_path,
            "feedback_or_revision_data": {
                "feedback_type": "teacher_reflection",
                "items": [
                    {"module": "objective", "issue": "任务三描述不够具体", "severity": "medium"},
                ]
            }
        }, "exports/phase8")

    def test_revision_log_non_empty(self):
        log = self.result.get("revision_log", [])
        self.assertTrue(len(log) > 0)

    def test_action_status_exists(self):
        for entry in self.result.get("revision_log", []):
            self.assertIn("action_status", entry)

    def test_post_revision_alignment_exists(self):
        self.assertIn("post_revision_alignment", self.result)

    def test_warning_status_not_completed(self):
        post = self.result.get("post_revision_alignment", {})
        if post.get("overall_status") != "pass":
            self.assertNotEqual(self.result.get("status"), "completed")


# ======================================================================
# 6. Export Package
# ======================================================================

class TestMCPExportPackage(unittest.TestCase):
    """Test: dc_export_package produces valid export_index."""

    @classmethod
    def setUpClass(cls):
        from tools.pipeline import run_mvp_pipeline_with_materials
        result = run_mvp_pipeline_with_materials(
            os.path.join(REPO_ROOT, 'examples', 'mvp_algorithm_seed_with_context.json'),
            os.path.join(REPO_ROOT, 'exports', 'phase8'))
        cls.project = result['project']

    def test_export_index_exists(self):
        from tools.document_exporter import export_all
        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_all(self.project, tmpdir)
            index_path = result.get("index_path", "")
            self.assertTrue(os.path.exists(index_path))

    def test_export_files_have_path_exists_size(self):
        from tools.document_exporter import export_all
        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_all(self.project, tmpdir)
            # Check that result files dict has path/size
            files = result.get("files", {})
            self.assertTrue(len(files) >= 5, f"Expected >= 5 files, got {len(files)}")
            for key, info in files.items():
                path = info.get("path", "")
                self.assertTrue(path, f"{key} path empty")
                self.assertTrue(os.path.exists(path), f"{key} file missing: {path}")
                self.assertGreater(info.get("size", 0), 0, f"{key} size 0")


import tempfile


# ======================================================================
# 7. Skills Match Agents Policy
# ======================================================================

class TestSkillsMatchAgentsPolicy(unittest.TestCase):
    """Test: skills align with AGENTS.md policy."""

    def test_dc_design_skill_has_confirmation_requirements(self):
        with open(os.path.join(REPO_ROOT, "skills", "dc-info-tech-design", "SKILL.md"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("确认", content)
        self.assertIn("来源", content)
        self.assertIn("质量门禁", content)

    def test_dc_k12_skill_emphasizes_sources(self):
        with open(os.path.join(REPO_ROOT, "skills", "dc-info-tech-design", "SKILL.md"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("课标", content)
        self.assertIn("教材", content)
        self.assertIn("K12", content)

    def test_dc_review_is_review_not_rewrite(self):
        with open(os.path.join(REPO_ROOT, "skills", "dc-info-tech-review", "SKILL.md"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("评审", content)

    def test_dc_revise_has_impact_analysis(self):
        with open(os.path.join(REPO_ROOT, "skills", "dc-info-tech-revise", "SKILL.md"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("影响分析", content)
        self.assertIn("一致性", content)


# ======================================================================
# 8. No Fake Final
# ======================================================================

class TestPluginNoFakeFinal(unittest.TestCase):
    """Test: K12 without clause-level source cannot return final_ready."""

    def test_no_final_ready_without_sources(self):
        from tools.agent_session import run_agent_session
        result = run_agent_session({
            "mode": "dc-design",
            "user_type": "K12教师",
            "scenario": "新课设计",
            "subject": "测试学科",
            "grade_level": "七年级",
            "topic": "测试课题",
            "teacher_inputs": {},
        }, "exports/phase8_no_source")
        self.assertFalse(result.get("can_export_final", True))
        self.assertNotEqual(result.get("draft_status"), "final_ready")


if __name__ == "__main__":
    unittest.main()
