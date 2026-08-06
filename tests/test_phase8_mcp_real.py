"""
Phase 8.2: Real MCP Layer Tests
These tests call server.list_tools() and server.call_tool() directly,
proving the plugin entry layer works.

Unlike test_phase8_plugin_contract.py (which tests agent_session.run_agent_session),
these tests verify the MCP server decorators, tool registration, and call_tool
dispatch -- the actual plugin entry point that Claude / MCP clients hit.
"""
import sys
import os
import json
import asyncio
import tempfile
import unittest
from unittest.mock import patch

# Ensure mcp-server is on the path so `from server import ...` works
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mcp-server'))

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def _run_async(coro):
    """Run an async coroutine to completion in a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ======================================================================
# 1. list_tools() exposes exactly 4 public tools
# ======================================================================

class TestMCPListToolsExposesFourPublicTools(unittest.TestCase):
    """Test: server.list_tools() exposes 4 public tools."""

    def test_list_tools_returns_four_tools(self):
        from server import list_tools
        tools = _run_async(list_tools())
        names = [t.name for t in tools]
        self.assertIn("dc_design_session", names)
        self.assertIn("dc_review_session", names)
        self.assertIn("dc_revise_session", names)
        self.assertIn("dc_export_package", names)
        self.assertEqual(len(tools), 4)

    def test_all_tools_have_description(self):
        from server import list_tools
        tools = _run_async(list_tools())
        for tool in tools:
            self.assertTrue(tool.description, f"Tool {tool.name} missing description")

    def test_all_tools_have_input_schema(self):
        from server import list_tools
        tools = _run_async(list_tools())
        for tool in tools:
            self.assertTrue(tool.inputSchema, f"Tool {tool.name} missing inputSchema")


# ======================================================================
# 2. call_tool('dc_design_session') returns agent contract
# ======================================================================

class TestMCPDesignCallTool(unittest.TestCase):
    """Test: server.call_tool('dc_design_session') returns agent contract."""

    @classmethod
    def setUpClass(cls):
        from server import call_tool
        cls.result_text = _run_async(call_tool("dc_design_session", {
            "user_type": "K12教师",
            "scenario": "新课设计",
            "subject": "信息科技",
            "grade_level": "七年级",
            "topic": "认识算法",
            "teacher_inputs": {"prior_knowledge": "学生能描述做事步骤"},
            "output_dir": "exports/phase8_mcp_test",
        }))
        cls.result = json.loads(cls.result_text[0].text)

    def test_returns_text_content_list(self):
        self.assertIsInstance(self.result_text, list)
        self.assertEqual(len(self.result_text), 1)
        self.assertEqual(self.result_text[0].type, "text")

    def test_mode_is_dc_design(self):
        self.assertEqual(self.result.get("mode"), "dc-design")

    def test_status_exists(self):
        self.assertIn("status", self.result)

    def test_tool_call_plan_or_status_report(self):
        has_plan = "tool_call_plan" in self.result
        has_report = "tool_status_report" in self.result
        self.assertTrue(has_plan or has_report)

    def test_k12_no_final_without_sources(self):
        self.assertFalse(self.result.get("can_export_final", True))

    def test_export_result_has_project_json(self):
        er = self.result.get("export_result", {})
        self.assertTrue(er.get("project_json"), "export_result.project_json is empty")


# ======================================================================
# 3. call_tool('dc_review_session') returns findings
# ======================================================================

class TestMCPReviewCallTool(unittest.TestCase):
    """Test: server.call_tool('dc_review_session') returns findings."""

    @classmethod
    def setUpClass(cls):
        from server import call_tool
        # First run design to get a project
        design_text = _run_async(call_tool("dc_design_session", {
            "user_type": "K12教师", "scenario": "新课设计",
            "subject": "信息科技", "grade_level": "七年级", "topic": "认识算法",
            "teacher_inputs": {},
            "output_dir": "exports/phase8_mcp_review_test",
        }))
        design = json.loads(design_text[0].text)
        project_path = design.get("export_result", {}).get("project_json", "")

        # Then review
        review_text = _run_async(call_tool("dc_review_session", {
            "existing_design_project_path": project_path,
            "output_dir": "exports/phase8_mcp_review_test",
        }))
        cls.result = json.loads(review_text[0].text)

    def test_mode_is_dc_review(self):
        self.assertEqual(self.result.get("mode"), "dc-review")

    def test_findings_non_empty(self):
        findings = self.result.get("findings", [])
        self.assertIsInstance(findings, list)
        self.assertTrue(len(findings) > 0)

    def test_findings_have_required_fields(self):
        for finding in self.result.get("findings", []):
            for field in ["finding_id", "severity", "description", "suggested_fix", "affected_modules"]:
                self.assertIn(field, finding, f"Finding missing: {field}")


# ======================================================================
# 4. call_tool('dc_revise_session') returns revision record
# ======================================================================

class TestMCPReviseCallTool(unittest.TestCase):
    """Test: server.call_tool('dc_revise_session') returns revision record."""

    @classmethod
    def setUpClass(cls):
        from server import call_tool
        design_text = _run_async(call_tool("dc_design_session", {
            "user_type": "K12教师", "scenario": "新课设计",
            "subject": "信息科技", "grade_level": "七年级", "topic": "认识算法",
            "teacher_inputs": {},
            "output_dir": "exports/phase8_mcp_revise_test",
        }))
        design = json.loads(design_text[0].text)
        project_path = design.get("export_result", {}).get("project_json", "")

        revise_text = _run_async(call_tool("dc_revise_session", {
            "existing_design_project_path": project_path,
            "feedback_or_revision_data": {
                "feedback_type": "teacher_reflection",
                "items": [{"module": "objective", "issue": "描述不具体", "severity": "medium"}]
            },
            "output_dir": "exports/phase8_mcp_revise_test",
        }))
        cls.result = json.loads(revise_text[0].text)

    def test_mode_is_dc_revise(self):
        self.assertEqual(self.result.get("mode"), "dc-revise")

    def test_revision_log_exists(self):
        has_log = "revision_log" in self.result
        has_record = "revision_record" in self.result
        self.assertTrue(has_log or has_record)

    def test_alignment_status_exists(self):
        has_pre = "pre_revision_alignment" in self.result
        has_post = "post_revision_alignment" in self.result
        has_status = "alignment_status" in self.result
        self.assertTrue(has_pre or has_post or has_status)


# ======================================================================
# 5. call_tool('dc_export_package') with project_path loads real project
# ======================================================================

class TestMCPExportPackageLoadsProjectPath(unittest.TestCase):
    """Test: dc_export_package with project_path loads real project."""

    def test_project_path_loads_real_project(self):
        from server import call_tool
        # First create a project
        design_text = _run_async(call_tool("dc_design_session", {
            "user_type": "K12教师", "scenario": "新课设计",
            "subject": "信息科技", "grade_level": "七年级", "topic": "认识算法",
            "teacher_inputs": {},
            "output_dir": "exports/phase8_mcp_export_test",
        }))
        design = json.loads(design_text[0].text)
        project_path = design.get("export_result", {}).get("project_json", "")

        # Export using project_path
        export_text = _run_async(call_tool("dc_export_package", {
            "project_path": project_path,
            "output_dir": "exports/phase8_mcp_export_test",
        }))
        result = json.loads(export_text[0].text)

        # Must have export_status and files
        self.assertIn("export_status", result)
        self.assertIn("files", result)
        # Files must have path/exists/size
        files = result.get("files", {})
        self.assertTrue(len(files) > 0)
        for key, entry in files.items():
            self.assertIn("path", entry)
            self.assertIn("exists", entry)
            self.assertIn("size", entry)

    def test_project_path_not_empty_project(self):
        """Must load real project, not empty dict."""
        from server import call_tool
        design_text = _run_async(call_tool("dc_design_session", {
            "user_type": "K12教师", "scenario": "新课设计",
            "subject": "信息科技", "grade_level": "七年级", "topic": "认识算法",
            "teacher_inputs": {},
            "output_dir": "exports/phase8_mcp_export_test2",
        }))
        design = json.loads(design_text[0].text)
        project_path = design.get("export_result", {}).get("project_json", "")

        export_text = _run_async(call_tool("dc_export_package", {
            "project_path": project_path,
            "output_dir": "exports/phase8_mcp_export_test2",
        }))
        result = json.loads(export_text[0].text)
        # export_status should not be "failed"
        self.assertNotEqual(result.get("export_status"), "failed")


# ======================================================================
# 6. call_tool('dc_export_package') rejects missing project
# ======================================================================

class TestMCPExportPackageRejectsMissing(unittest.TestCase):
    """Test: dc_export_package rejects missing project."""

    def test_no_project_returns_error(self):
        from server import call_tool
        result_text = _run_async(call_tool("dc_export_package", {}))
        result = json.loads(result_text[0].text)
        # Must return error or failed status
        self.assertIn(result.get("status", ""), ["error", "failed"])
        self.assertTrue(
            len(result.get("errors", [])) > 0 or len(result.get("export_errors", [])) > 0,
            "Must have errors when no project provided"
        )

    def test_missing_project_path_returns_error(self):
        from server import call_tool
        result_text = _run_async(call_tool("dc_export_package", {
            "project_path": "/nonexistent/path/to/project.json"
        }))
        result = json.loads(result_text[0].text)
        self.assertIn(result.get("status", ""), ["error", "failed"])
        self.assertTrue(
            len(result.get("errors", [])) > 0,
            "Must have errors when project_path doesn't exist"
        )


# ======================================================================
# 7. Export result has all required fields
# ======================================================================

class TestMCPExportPackageResult(unittest.TestCase):
    """Test: export result has all required fields."""

    @classmethod
    def setUpClass(cls):
        from server import call_tool
        design_text = _run_async(call_tool("dc_design_session", {
            "user_type": "K12教师", "scenario": "新课设计",
            "subject": "信息科技", "grade_level": "七年级", "topic": "认识算法",
            "teacher_inputs": {},
            "output_dir": "exports/phase8_mcp_export_final_test",
        }))
        design = json.loads(design_text[0].text)
        project_path = design.get("export_result", {}).get("project_json", "")

        export_text = _run_async(call_tool("dc_export_package", {
            "project_path": project_path,
            "output_dir": "exports/phase8_mcp_export_final_test",
        }))
        cls.result = json.loads(export_text[0].text)

    def test_has_status(self):
        self.assertIn("status", self.result)

    def test_has_export_status(self):
        self.assertIn("export_status", self.result)

    def test_has_files(self):
        files = self.result.get("files", {})
        self.assertTrue(len(files) > 0)

    def test_has_export_index_json(self):
        self.assertIn("export_index_json", self.result)

    def test_has_warnings_or_errors(self):
        has_warnings = "warnings" in self.result
        has_errors = "errors" in self.result or "export_errors" in self.result
        self.assertTrue(has_warnings or has_errors)


# ======================================================================
# Phase 8.4: Export contract fixes
# ======================================================================

class TestExportStatusPartialForProjectObject(unittest.TestCase):
    """Test: project object path returns partial when required files missing."""

    def test_partial_when_only_one_file_exported(self):
        from unittest.mock import patch
        from server import call_tool

        def _fake_export(project, output_dir):
            # Create only dc_report file
            path = os.path.join(output_dir, "test.docx")
            with open(path, "w") as f:
                f.write("test content")
            return {
                "files": {
                    "dc_report": {"path": path, "exported": True, "size": 1000},
                    "lesson_plan": {"path": None, "exported": False, "size": 0},
                    "student_worksheet": {"path": None, "exported": False, "size": 0},
                    "alignment_matrix": {"path": None, "exported": False, "size": 0},
                    "ai_process_record": {"path": None, "exported": False, "size": 0},
                },
                "index_path": os.path.join(output_dir, "index.json"),
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("tools.document_exporter.export_all", _fake_export):
                result_text = _run_async(call_tool("dc_export_package", {
                    "project": {"metadata": {"project_name": "test"}},
                    "output_dir": tmpdir,
                }))
            result = json.loads(result_text[0].text)
            self.assertEqual(result.get("export_status"), "partial")
            self.assertEqual(result.get("status"), "completed_with_warnings")
            self.assertTrue(len(result.get("warnings", [])) > 0)


class TestExportStatusSuccessRequiresAll(unittest.TestCase):
    """Test: success requires all 5 required files."""

    def test_success_with_all_required_files(self):
        from unittest.mock import patch
        from server import call_tool

        def _fake_export(project, output_dir):
            files = {}
            for key in ["dc_report", "lesson_plan", "student_worksheet",
                        "alignment_matrix", "ai_process_record"]:
                path = os.path.join(output_dir, f"test_{key}.docx")
                with open(path, "w") as f:
                    f.write("test")
                files[key] = {"path": path, "exported": True, "size": 100}
            return {"files": files, "index_path": os.path.join(output_dir, "index.json")}

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("tools.document_exporter.export_all", _fake_export):
                result_text = _run_async(call_tool("dc_export_package", {
                    "project": {"metadata": {"project_name": "test"}},
                    "output_dir": tmpdir,
                }))
            result = json.loads(result_text[0].text)
            self.assertEqual(result.get("export_status"), "success")
            self.assertEqual(result.get("status"), "completed")


class TestExportResultHasExportIndexJson(unittest.TestCase):
    """Test: export result has export_index_json field."""

    def test_export_result_has_export_index_json(self):
        from server import call_tool
        import glob

        # Find an existing project
        project_files = glob.glob("exports/phase8/*design_project.json")
        if not project_files:
            self.skipTest("No project files found")

        result_text = _run_async(call_tool("dc_export_package", {
            "project_path": project_files[0],
            "output_dir": "exports/phase8_index_test",
        }))
        result = json.loads(result_text[0].text)
        self.assertIn("export_index_json", result)
        self.assertTrue(result.get("export_index_json"), "export_index_json should be non-empty")


class TestCallToolDoesNotMutateArguments(unittest.TestCase):
    """Test: call_tool does not mutate the input arguments dict."""

    def test_arguments_not_mutated(self):
        from server import call_tool

        original_args = {
            "user_type": "K12教师",
            "scenario": "新课设计",
            "subject": "信息科技",
            "grade_level": "七年级",
            "topic": "认识算法",
            "teacher_inputs": {},
            "output_dir": "exports/phase8_mutation_test",
        }
        # Make a copy to compare later
        original_copy = dict(original_args)

        result_text = _run_async(call_tool("dc_design_session", original_args))

        # Original should not have 'mode' added
        self.assertNotIn("mode", original_args, "arguments was mutated with 'mode'")
        # Original should still have 'output_dir'
        self.assertEqual(original_args.get("output_dir"), original_copy["output_dir"])


if __name__ == "__main__":
    unittest.main()
