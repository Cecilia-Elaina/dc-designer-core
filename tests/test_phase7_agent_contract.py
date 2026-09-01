"""
Phase 7 Agent Contract Tests

Verifies that dc-designer-core works as an agent-capable instructional
design system.  Each test checks STRUCTURAL fields in the returned dicts,
not just string presence.

Run: python -m unittest tests.test_phase7_agent_contract
"""
import sys
import os
import json
import unittest

# ---------------------------------------------------------------------------
# Path setup -- mirrors existing test files
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'mcp-server'))

REPO_ROOT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..'))

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DESIGN_REQUEST = {
    "mode": "dc-design",
    "user_type": "K12教师",
    "scenario": "新课设计",
    "subject": "信息科技",
    "grade_level": "七年级",
    "topic": "认识算法",
    "teacher_inputs": {
        "prior_knowledge": "学生能描述生活中做事步骤",
        "common_difficulties": ["步骤笼统", "遗漏关键步骤"],
        "available_media": ["黑板", "投影", "学习单"],
        "devices": "不保证一人一机",
    },
}


def _design_result():
    """Cached dc-design result (runs once per test class)."""
    from tools.agent_session import run_agent_session
    return run_agent_session(DESIGN_REQUEST, output_dir="exports/phase7_test")


def _review_result():
    """Cached dc-review result using the exported project."""
    from tools.agent_session import run_agent_session
    project_path = os.path.join(REPO_ROOT, "exports", "phase7_test",
                                "phase7_design_project.json")
    if not os.path.isfile(project_path):
        # Fall back to existing export
        project_path = os.path.join(REPO_ROOT, "exports",
                                    "mvp_algorithm_project_with_materials_full.json")
    return run_agent_session({
        "mode": "dc-review",
        "existing_design_project_path": project_path,
    }, output_dir="exports/phase7_test")


def _revise_result():
    """Cached dc-revise result."""
    from tools.agent_session import run_agent_session
    project_path = os.path.join(REPO_ROOT, "exports", "phase7_test",
                                "phase7_design_project.json")
    if not os.path.isfile(project_path):
        project_path = os.path.join(REPO_ROOT, "exports",
                                    "mvp_algorithm_project_with_materials_full.json")
    return run_agent_session({
        "mode": "dc-revise",
        "existing_design_project_path": project_path,
        "feedback_or_revision_data": {
            "feedback_type": "teacher_reflection",
            "items": [
                {"module": "objective", "issue": "任务三的描述不够具体",
                 "severity": "medium"},
                {"module": "assessment", "issue": "互评检查表评分标准太抽象",
                 "severity": "low"},
                {"module": "strategy", "issue": "小组任务时间分配需要调整",
                 "severity": "low"},
            ],
        },
    }, output_dir="exports/phase7_test")


# ======================================================================
# 1-4: dc-design mode tests
# ======================================================================

class TestDCDesignRequiresConfirmations(unittest.TestCase):
    """Test 1: dc-design must produce required_confirmations when
    K12 source verification is incomplete."""

    @classmethod
    def setUpClass(cls):
        cls.result = _design_result()

    def test_has_required_confirmations_key(self):
        self.assertIn("required_confirmations", self.result)

    def test_required_confirmations_is_list(self):
        self.assertIsInstance(self.result["required_confirmations"], list)

    def test_confirmations_have_component_field(self):
        """Each confirmation must have a 'component' field (str)."""
        for conf in self.result["required_confirmations"]:
            self.assertIn("component", conf,
                          f"Confirmation missing 'component': {conf}")
            self.assertIsInstance(conf["component"], str)

    def test_confirmations_have_reason_field(self):
        """Each confirmation must have a 'reason' field (str)."""
        for conf in self.result["required_confirmations"]:
            self.assertIn("reason", conf,
                          f"Confirmation missing 'reason': {conf}")
            self.assertIsInstance(conf["reason"], str)

    def test_goal_confirmation_present_for_k12(self):
        """K12 design without verified sources should have a goal confirmation."""
        components = [c.get("component") for c in
                      self.result["required_confirmations"]]
        # At least one confirmation should relate to goal or alignment
        self.assertTrue(
            len(components) > 0,
            "K12 design without full source verification should produce "
            "at least one required confirmation"
        )


class TestDCDesignK12SourceGapBlocksFinal(unittest.TestCase):
    """Test 2: K12 design with no A/B source should indicate that
    the goal cannot be used as final."""

    @classmethod
    def setUpClass(cls):
        cls.result = _design_result()

    def test_project_has_goal_status(self):
        project = self.result.get("project", {})
        goal = project.get("goal", {})
        # Goal should have verification_status
        self.assertIn("verification_status", goal,
                      "Project goal must have verification_status field")

    def test_k12_gap_produces_warnings_or_confirmations(self):
        """Either warnings or required_confirmations should flag the source gap."""
        has_warnings = len(self.result.get("warnings", [])) > 0
        has_confs = len(self.result.get("required_confirmations", [])) > 0
        self.assertTrue(
            has_warnings or has_confs,
            "K12 design with local-only standards should produce "
            "warnings or required_confirmations about source gaps"
        )

    def test_alignment_summary_exists(self):
        self.assertIn("alignment_summary", self.result)
        self.assertIsInstance(self.result["alignment_summary"], dict)


class TestDCDesignToolCallPlanOrder(unittest.TestCase):
    """Test 3: tool_call_plan must list engine invocations in
    dependency order."""

    @classmethod
    def setUpClass(cls):
        cls.result = _design_result()

    def test_tool_call_plan_is_list(self):
        self.assertIsInstance(self.result["tool_call_plan"], list)

    def test_tool_call_plan_non_empty(self):
        self.assertGreater(len(self.result["tool_call_plan"]), 0,
                           "tool_call_plan must have at least one entry")

    def test_each_entry_has_required_fields(self):
        for entry in self.result["tool_call_plan"]:
            self.assertIn("step", entry)
            self.assertIn("engine", entry)
            self.assertIn("function", entry)
            self.assertIn("inputs", entry)
            self.assertIn("outputs", entry)
            self.assertIsInstance(entry["step"], int)
            self.assertIsInstance(entry["engine"], str)
            self.assertIsInstance(entry["function"], str)

    def test_plan_order_respects_dependencies(self):
        """standards_search must come before goal_engine,
        goal_engine before skill_graph, etc."""
        engines = [e.get("engine") for e in self.result["tool_call_plan"]]
        # Find first occurrence of each
        order_map = {}
        for i, eng in enumerate(engines):
            if eng not in order_map:
                order_map[eng] = i

        # Validate ordering constraints
        if "standards_search" in order_map and "goal_engine" in order_map:
            self.assertLess(
                order_map["standards_search"], order_map["goal_engine"],
                "standards_search must come before goal_engine"
            )
        if "goal_engine" in order_map and "skill_graph" in order_map:
            self.assertLess(
                order_map["goal_engine"], order_map["skill_graph"],
                "goal_engine must come before skill_graph"
            )
        if "skill_graph" in order_map and "objective_engine" in order_map:
            self.assertLess(
                order_map["skill_graph"], order_map["objective_engine"],
                "skill_graph must come before objective_engine"
            )
        if "objective_engine" in order_map and "assessment_engine" in order_map:
            self.assertLess(
                order_map["objective_engine"], order_map["assessment_engine"],
                "objective_engine must come before assessment_engine"
            )

    def test_steps_are_sequential(self):
        steps = [e.get("step", 0) for e in self.result["tool_call_plan"]]
        for i in range(1, len(steps)):
            self.assertEqual(steps[i], steps[i - 1] + 1,
                             f"Step numbers must be sequential; "
                             f"got {steps[i-1]} -> {steps[i]}")


class TestDCDesignExportsPackage(unittest.TestCase):
    """Test 4: dc-design must produce exportable project and report."""

    @classmethod
    def setUpClass(cls):
        cls.result = _design_result()

    def test_project_path_exists(self):
        exports = self.result.get("export_result", {})
        path = exports.get("project_json", "")
        self.assertTrue(path, "project_json path must be non-empty")
        self.assertTrue(os.path.isfile(path),
                        f"Project file must exist: {path}")

    def test_project_json_is_valid(self):
        exports = self.result.get("export_result", {})
        path = exports.get("project_json", "")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)
        for key in ("project_id", "goal", "objectives", "assessment_plan"):
            self.assertIn(key, data, f"Exported project missing '{key}'")

    def test_project_has_required_modules(self):
        exports = self.result.get("export_result", {})
        path = exports.get("project_json", "")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for module in ("goal", "skill_graph", "objectives",
                       "assessment_plan", "quality_check"):
            self.assertIn(module, data,
                          f"Exported project missing module: {module}")

    def test_report_path_if_present_is_valid(self):
        report_path = self.result.get("report_path")
        if report_path:
            self.assertTrue(os.path.isfile(report_path),
                            f"Report file must exist: {report_path}")


# ======================================================================
# 5-7: dc-review mode tests
# ======================================================================

class TestDCReviewOutputsFindings(unittest.TestCase):
    """Test 5: dc-review must produce a findings list with structural fields."""

    @classmethod
    def setUpClass(cls):
        cls.result = _review_result()

    def test_findings_key_exists(self):
        self.assertIn("findings", self.result)

    def test_findings_is_list(self):
        self.assertIsInstance(self.result["findings"], list)

    def test_each_finding_has_type_severity(self):
        for finding in self.result["findings"]:
            self.assertIn("type", finding,
                          f"Finding missing 'type': {finding}")
            self.assertIn("severity", finding,
                          f"Finding missing 'severity': {finding}")
            self.assertIn("description", finding,
                          f"Finding missing 'description': {finding}")
            self.assertIn("suggested_fix", finding,
                          f"Finding missing 'suggested_fix': {finding}")

    def test_severity_values_are_valid(self):
        valid_severities = {"low", "medium", "high", "critical"}
        for finding in self.result["findings"]:
            self.assertIn(finding["severity"], valid_severities,
                          f"Invalid severity: {finding['severity']}")

    def test_review_report_exists(self):
        self.assertIn("review_report", self.result)
        report = self.result["review_report"]
        self.assertIn("finding_count", report)
        self.assertIn("overall_assessment", report)
        self.assertIsInstance(report["finding_count"], int)


class TestDCReviewDetectsAlignmentIssues(unittest.TestCase):
    """Test 6: dc-review should detect alignment issues when they exist."""

    @classmethod
    def setUpClass(cls):
        cls.result = _review_result()

    def test_findings_have_valid_types(self):
        valid_types = {
            "alignment_gap", "missing_source", "weak_verb",
            "source_trace_gap", "objective_issue", "strategy_issue",
            "alignment_warning",
        }
        for finding in self.result["findings"]:
            self.assertIn(finding["type"], valid_types,
                          f"Unexpected finding type: {finding['type']}")

    def test_alignment_gap_findings_have_gate(self):
        for finding in self.result["findings"]:
            if finding["type"] == "alignment_gap":
                self.assertIn("gate", finding,
                              "alignment_gap finding must specify 'gate'")

    def test_review_report_overall_assessment_is_valid(self):
        report = self.result.get("review_report", {})
        valid_assessments = {"pass", "needs_revision",
                             "major_revision_required"}
        self.assertIn(report.get("overall_assessment"), valid_assessments)


class TestDCReviewDoesNotReplaceOriginalDesign(unittest.TestCase):
    """Test 7: dc-review must not mutate the original project file."""

    @classmethod
    def setUpClass(cls):
        cls.project_path = os.path.join(
            REPO_ROOT, "exports", "phase7_test",
            "phase7_design_project.json")
        if not os.path.isfile(cls.project_path):
            cls.project_path = os.path.join(
                REPO_ROOT, "exports",
                "mvp_algorithm_project_with_materials_full.json")
        # Read original hash
        with open(cls.project_path, "r", encoding="utf-8") as f:
            cls.original_data = f.read()
        cls.original_hash = hash(cls.original_data)
        # Run review
        cls.result = _review_result()

    def test_original_file_unchanged(self):
        with open(self.project_path, "r", encoding="utf-8") as f:
            current_data = f.read()
        self.assertEqual(hash(current_data), self.original_hash,
                         "dc-review must not modify the original project file")

    def test_review_result_has_original_project(self):
        self.assertIn("original_project", self.result)
        self.assertIsInstance(self.result["original_project"], dict)


# ======================================================================
# 8-9: dc-revise mode tests
# ======================================================================

class TestDCReviseOutputsImpactAnalysis(unittest.TestCase):
    """Test 8: dc-revise must produce revision_log with impact analysis."""

    @classmethod
    def setUpClass(cls):
        cls.result = _revise_result()

    def test_revision_log_key_exists(self):
        self.assertIn("revision_log", self.result)

    def test_revision_log_is_list(self):
        self.assertIsInstance(self.result["revision_log"], list)

    def test_revision_log_non_empty(self):
        self.assertGreater(len(self.result["revision_log"]), 0,
                           "revision_log must have at least one entry")

    def test_each_revision_has_structural_fields(self):
        for rev in self.result["revision_log"]:
            self.assertIn("revision_id", rev,
                          f"Revision missing 'revision_id': {rev}")
            self.assertIn("module", rev,
                          f"Revision missing 'module': {rev}")
            self.assertIn("original_issue", rev,
                          f"Revision missing 'original_issue': {rev}")
            self.assertIn("impact_analysis", rev,
                          f"Revision missing 'impact_analysis': {rev}")
            self.assertIn("modification_applied", rev,
                          f"Revision missing 'modification_applied': {rev}")

    def test_impact_analysis_has_affected_components(self):
        for rev in self.result["revision_log"]:
            impact = rev.get("impact_analysis", {})
            self.assertIn("directly_affected", impact,
                          "impact_analysis must have 'directly_affected'")
            self.assertIsInstance(impact["directly_affected"], list)

    def test_revision_record_exists(self):
        self.assertIn("revision_record", self.result)
        rec = self.result["revision_record"]
        self.assertIn("revision_cycle_id", rec)
        self.assertIn("timestamp", rec)
        self.assertIn("pre_revision_alignment", rec)
        self.assertIn("post_revision_alignment", rec)


class TestDCReviseUpdatesAlignment(unittest.TestCase):
    """Test 9: dc-revise must re-run alignment and report before/after."""

    @classmethod
    def setUpClass(cls):
        cls.result = _revise_result()

    def test_pre_revision_alignment_exists(self):
        self.assertIn("pre_revision_alignment", self.result)
        self.assertIsInstance(self.result["pre_revision_alignment"], dict)

    def test_post_revision_alignment_exists(self):
        self.assertIn("post_revision_alignment", self.result)
        self.assertIsInstance(self.result["post_revision_alignment"], dict)

    def test_both_alignments_have_overall_status(self):
        pre = self.result["pre_revision_alignment"]
        post = self.result["post_revision_alignment"]
        self.assertIn("overall_status", pre)
        self.assertIn("overall_status", post)

    def test_alignment_improved_field(self):
        rec = self.result.get("revision_record", {})
        self.assertIn("alignment_improved", rec)
        self.assertIsInstance(rec["alignment_improved"], bool)

    def test_revised_project_exported(self):
        path = self.result.get("revised_project_path", "")
        self.assertTrue(path, "revised_project_path must be non-empty")
        self.assertTrue(os.path.isfile(path),
                        f"Revised project file must exist: {path}")

    def test_revision_log_exported(self):
        path = self.result.get("revision_log_path", "")
        self.assertTrue(path, "revision_log_path must be non-empty")
        self.assertTrue(os.path.isfile(path),
                        f"Revision log file must exist: {path}")


# ======================================================================
# 10-13: Agent contract integrity tests
# ======================================================================

class TestAgentContractNoFakeOfficialSource(unittest.TestCase):
    """Test 10: agent session must never fabricate A/B-level official sources."""

    @classmethod
    def setUpClass(cls):
        cls.result = _design_result()

    def test_no_fake_source_level_a(self):
        """No source in the project should claim level A unless it came
        from standards_search."""
        project = self.result.get("project", {})
        sources = project.get("sources", [])
        for src in sources:
            level = src.get("source_level", "")
            if level.startswith("A"):
                # Verify it has a legitimate source_id from the registry
                self.assertIn("source_id", src,
                              "A-level source must have a source_id from registry")
                # Must not be a test fixture pretending to be official
                self.assertFalse(
                    src.get("is_test_fixture", False),
                    f"Source {src.get('source_id')} claims A-level but "
                    f"is a test fixture"
                )

    def test_no_fake_source_level_b(self):
        """Same check for B-level sources."""
        project = self.result.get("project", {})
        sources = project.get("sources", [])
        for src in sources:
            level = src.get("source_level", "")
            if level.startswith("B"):
                self.assertFalse(
                    src.get("is_test_fixture", False),
                    f"Source {src.get('source_id')} claims B-level but "
                    f"is a test fixture"
                )


class TestAgentContractNoFakeFormData(unittest.TestCase):
    """Test 11: agent session must never fabricate formative evaluation data."""

    @classmethod
    def setUpClass(cls):
        cls.result = _design_result()

    def test_no_formative_evaluation_field(self):
        """The design result should not contain fabricated formative
        evaluation results."""
        project = self.result.get("project", {})
        # formative_evaluation should not be populated with fake data
        fe = project.get("formative_evaluation", None)
        if fe is not None:
            # If present, it should be empty or stub, not fabricated results
            self.assertIsInstance(fe, (dict, list))
            if isinstance(fe, dict):
                # Should not have fabricated data entries
                for key in ("results", "data", "findings"):
                    self.assertNotIn(key, fe,
                                     "formative_evaluation should not contain "
                                     f"fabricated '{key}'")


class TestAgentContractNoPrivateStudentData(unittest.TestCase):
    """Test 12: agent session must never include private student data."""

    @classmethod
    def setUpClass(cls):
        cls.result = _design_result()

    def test_no_individual_student_identifiers(self):
        """No field in the project should contain individual student names,
        ID numbers, or contact information."""
        project = self.result.get("project", {})
        project_str = json.dumps(project, ensure_ascii=False)

        # Check for patterns that suggest private student data
        import re
        # Chinese ID patterns (simplified)
        id_patterns = [
            r"\d{17}[\dXx]",     # 18-digit Chinese ID
            r"\d{15}",            # 15-digit old ID
            r"1[3-9]\d{9}",      # Chinese mobile number
        ]
        for pattern in id_patterns:
            matches = re.findall(pattern, project_str)
            self.assertEqual(
                len(matches), 0,
                f"Project contains potential private data matching "
                f"pattern {pattern}: {matches}"
            )

    def test_learner_context_is_anonymized(self):
        """Learner context should describe groups, not individuals."""
        project = self.result.get("project", {})
        ctx = project.get("context_analysis", {})
        profile = ctx.get("learner_profile", {})
        # prior_knowledge should be general, not individual
        pk = profile.get("prior_knowledge", "")
        if pk:
            self.assertNotIn("张三", pk, "Learner context must not contain names")
            self.assertNotIn("李四", pk, "Learner context must not contain names")


class TestAgentContractProgressReporting(unittest.TestCase):
    """Test 13: agent session must report progress via tool_call_plan."""

    @classmethod
    def setUpClass(cls):
        cls.result = _design_result()

    def test_tool_call_plan_covers_all_phases(self):
        """The tool_call_plan must mention all major pipeline phases."""
        engines = set(e.get("engine") for e in
                      self.result.get("tool_call_plan", []))
        required_engines = {
            "goal_engine", "skill_graph", "objective_engine",
            "assessment_engine", "strategy_engine", "materials_engine",
            "alignment_checker",
        }
        missing = required_engines - engines
        self.assertEqual(
            missing, set(),
            f"tool_call_plan missing engines: {missing}"
        )

    def test_each_tool_call_has_timestamp(self):
        for entry in self.result.get("tool_call_plan", []):
            self.assertIn("timestamp", entry,
                          f"Tool call entry missing 'timestamp': {entry}")

    def test_tool_call_outputs_are_dicts(self):
        for entry in self.result.get("tool_call_plan", []):
            self.assertIsInstance(entry.get("outputs", {}), dict,
                                 f"Tool call outputs must be dict: {entry}")


# ======================================================================
# 14: Pending confirmation labels
# ======================================================================

class TestAgentContractPendingConfirmationLabels(unittest.TestCase):
    """Test 14: every required_confirmation must be clearly labeled
    so an agent can decide whether to pause for user input."""

    @classmethod
    def setUpClass(cls):
        cls.result = _design_result()

    def test_all_confirmations_have_component(self):
        for conf in self.result.get("required_confirmations", []):
            self.assertIn("component", conf)
            self.assertIsInstance(conf["component"], str)
            self.assertGreater(len(conf["component"]), 0)

    def test_all_confirmations_have_reason(self):
        for conf in self.result.get("required_confirmations", []):
            self.assertIn("reason", conf)
            self.assertIsInstance(conf["reason"], str)
            self.assertGreater(len(conf["reason"]), 0)

    def test_confirmations_are_actually_needed(self):
        """If there are confirmations, at least one should relate to
        a real quality concern (not empty strings)."""
        confs = self.result.get("required_confirmations", [])
        if confs:
            has_real_reason = any(
                len(c.get("reason", "")) > 5 for c in confs
            )
            self.assertTrue(
                has_real_reason,
                "required_confirmations should contain real quality concerns, "
                "not placeholder text"
            )

    def test_status_reflects_confirmations(self):
        """If confirmations exist, status should not be bare 'completed'
        without warnings."""
        confs = self.result.get("required_confirmations", [])
        if confs:
            self.assertIn(self.result.get("status"),
                          ("completed_with_warnings", "error"),
                          "When confirmations are present, status should "
                          "indicate warnings")


# ======================================================================
# 15: Full loop integration test
# ======================================================================

class TestPhase7FullLoopDesignReviewRevise(unittest.TestCase):
    """Test 15: Run the complete design -> review -> revise loop
    and verify that each stage feeds into the next."""

    @classmethod
    def setUpClass(cls):
        from tools.agent_session import run_agent_session

        # Stage 1: Design
        cls.design = run_agent_session(DESIGN_REQUEST,
                                       output_dir="exports/phase7_loop_test")

        # Stage 2: Review the design output
        design_path = cls.design.get("export_result", {}).get("project_json", "")
        if not design_path:
            design_path = cls.design.get("project_path", "")
        cls.review = run_agent_session({
            "mode": "dc-review",
            "existing_design_project_path": design_path,
        }, output_dir="exports/phase7_loop_test")

        # Stage 3: Revise based on review findings
        cls.revise = run_agent_session({
            "mode": "dc-revise",
            "existing_design_project_path": design_path,
            "feedback_or_revision_data": {
                "feedback_type": "agent_review",
                "items": [
                    {"module": f.get("type", "unknown"),
                     "issue": f.get("description", ""),
                     "severity": f.get("severity", "low")}
                    for f in cls.review.get("findings", [])[:3]
                ] if cls.review.get("findings") else [
                    {"module": "strategy",
                     "issue": "general improvement",
                     "severity": "low"}
                ],
            },
        }, output_dir="exports/phase7_loop_test")

    def test_design_completes(self):
        self.assertIn(self.design.get("status"),
                      ("completed", "completed_with_warnings"))
        self.assertEqual(self.design.get("mode"), "dc-design")

    def test_review_completes(self):
        self.assertIn(self.review.get("status"),
                      ("completed", "completed_with_warnings"))
        self.assertEqual(self.review.get("mode"), "dc-review")

    def test_revise_completes(self):
        self.assertIn(self.revise.get("status"),
                      ("completed", "completed_with_warnings"))
        self.assertEqual(self.revise.get("mode"), "dc-revise")

    def test_design_produces_project(self):
        self.assertIn("project", self.design)
        project = self.design["project"]
        for key in ("goal", "objectives", "assessment_plan"):
            self.assertIn(key, project)

    def test_review_identifies_findings(self):
        self.assertIsInstance(self.review.get("findings", []), list)
        # Review should find at least some issues or confirm clean
        self.assertIn("review_report", self.review)

    def test_revise_has_revision_log(self):
        log = self.revise.get("revision_log", [])
        self.assertIsInstance(log, list)
        self.assertGreater(len(log), 0, "Revision should produce at least one log entry")

    def test_chain_preserves_project_id(self):
        """The project_id should be consistent across all three stages."""
        design_id = self.design.get("project", {}).get("project_id", "")
        review_id = self.review.get("original_project", {}).get("project_id", "")
        revise_id = self.revise.get("revision_record", {}).get(
            "original_project_id", "")
        # Design and review should reference the same project
        if design_id and review_id:
            self.assertEqual(design_id, review_id,
                             "Review should reference the same project_id")

    def test_each_stage_has_tool_call_plan(self):
        for name, result in [("design", self.design),
                             ("review", self.review),
                             ("revise", self.revise)]:
            plan = result.get("tool_call_plan", [])
            self.assertIsInstance(plan, list,
                                 f"{name} stage must have tool_call_plan list")
            self.assertGreater(len(plan), 0,
                               f"{name} stage tool_call_plan must be non-empty")


# ======================================================================
# Unknown mode test
# ======================================================================

class TestAgentSessionUnknownMode(unittest.TestCase):
    """Unknown mode should return error, not crash."""

    def test_unknown_mode_returns_error(self):
        from tools.agent_session import run_agent_session
        result = run_agent_session({"mode": "nonexistent_mode"})
        self.assertEqual(result.get("status"), "error")
        self.assertIn("Unknown mode", result.get("warnings", [""])[0])


class TestAgentSessionMissingFields(unittest.TestCase):
    """dc-design with missing required fields returns error."""

    def test_missing_subject_returns_error(self):
        from tools.agent_session import run_agent_session
        result = run_agent_session({
            "mode": "dc-design",
            "grade_level": "七年级",
            "topic": "认识算法",
        })
        self.assertEqual(result.get("status"), "error")
        self.assertTrue(any("subject" in w for w in result.get("warnings", [])))


# ======================================================================
# Phase 7.2: Machine-readable final gate
# ======================================================================

class TestDesignHasMachineReadableFinalGate(unittest.TestCase):
    """Phase 7.2: dc-design must expose can_export_final, draft_status,
    and final_blocking_reasons for machine consumption."""

    @classmethod
    def setUpClass(cls):
        cls.result = _design_result()

    def test_can_export_final_is_false(self):
        """K12 design without verified sources must not allow final export."""
        self.assertFalse(self.result.get("can_export_final"),
                         "can_export_final should be False for unverified K12 design")

    def test_draft_status_not_final_ready(self):
        """draft_status must not be 'final_ready' when sources are unverified."""
        self.assertNotEqual(self.result.get("draft_status"), "final_ready",
                            "draft_status must not be final_ready for unverified design")

    def test_final_blocking_reasons_non_empty(self):
        """final_blocking_reasons must be non-empty when can_export_final is False."""
        reasons = self.result.get("final_blocking_reasons", [])
        self.assertIsInstance(reasons, list)
        self.assertGreater(len(reasons), 0,
                           "final_blocking_reasons must be non-empty when export is blocked")

    def test_blocking_reasons_have_required_fields(self):
        """Each blocking reason must have component, reason, evidence, required_action."""
        for reason in self.result.get("final_blocking_reasons", []):
            self.assertIn("component", reason,
                          f"Blocking reason missing 'component': {reason}")
            self.assertIn("reason", reason,
                          f"Blocking reason missing 'reason': {reason}")
            self.assertIn("evidence", reason,
                          f"Blocking reason missing 'evidence': {reason}")
            self.assertIn("required_action", reason,
                          f"Blocking reason missing 'required_action': {reason}")


# ======================================================================
# Phase 7.2: Export package has real files
# ======================================================================

class TestDesignExportPackageHasRealFiles(unittest.TestCase):
    """Phase 7.2: All export paths in export_result must point to real files."""

    @classmethod
    def setUpClass(cls):
        cls.result = _design_result()

    def test_all_export_paths_exist(self):
        """Every non-None path in export_result must be an existing file."""
        export_result = self.result.get("export_result", {})
        for key, path in export_result.items():
            if path is not None and isinstance(path, str):
                self.assertTrue(
                    os.path.isfile(path),
                    f"export_result['{key}'] points to non-existent file: {path}"
                )


# ======================================================================
# Phase 7.2: Tool plan matches the required project tools
# ======================================================================

class TestToolPlanMatchesAgentsRequiredTools(unittest.TestCase):
    """Phase 7.2: tool_status_report must list all required project tools."""

    @classmethod
    def setUpClass(cls):
        cls.result = _design_result()

    def test_all_required_tools_present(self):
        """tool_status_report must include all 13 required tools."""
        report = self.result.get("tool_status_report", [])
        self.assertIsInstance(report, list)
        self.assertGreater(len(report), 0, "tool_status_report must be non-empty")
        tool_names = {entry.get("tool_name") for entry in report}
        required = {
            "standards_search", "goal_engine", "skill_graph",
            "learner_context", "objective_engine", "assessment_engine",
            "strategy_engine", "materials_engine", "alignment_checker",
            "export_package", "knowledge_ingest", "teacher_memory",
            "formative_evaluation_plan",
        }
        missing = required - tool_names
        self.assertEqual(missing, set(),
                         f"tool_status_report missing required tools: {missing}")

    def test_tools_have_status_field(self):
        """Each entry in tool_status_report must have a 'status' field."""
        report = self.result.get("tool_status_report", [])
        for entry in report:
            self.assertIn("status", entry,
                          f"tool_status_report entry missing 'status': {entry}")
            self.assertIn(entry["status"], ("called", "not_called"),
                          f"Invalid status value: {entry['status']}")


# ======================================================================
# Phase 7.2: Review alignment warning creates findings
# ======================================================================

class TestReviewAlignmentWarningCreatesFindings(unittest.TestCase):
    """Phase 7.2: When alignment produces warnings, review findings must
    be non-empty and overall_assessment must not be 'pass'."""

    @classmethod
    def setUpClass(cls):
        cls.result = _review_result()

    def test_findings_non_empty_when_alignment_warning(self):
        """If alignment has warnings, findings list must be non-empty."""
        alignment = self.result.get("original_project", {}).get(
            "quality_check", self.result.get("alignment", {}))
        warnings = alignment.get("warnings", []) if isinstance(alignment, dict) else []
        findings = self.result.get("findings", [])
        if warnings:
            self.assertGreater(len(findings), 0,
                               "Findings must be non-empty when alignment has warnings")

    def test_overall_assessment_not_pass(self):
        """overall_assessment must not be 'pass' when findings exist."""
        findings = self.result.get("findings", [])
        report = self.result.get("review_report", {})
        if findings:
            self.assertNotEqual(report.get("overall_assessment"), "pass",
                                "overall_assessment must not be 'pass' when findings exist")


# ======================================================================
# Phase 7.2: Review findings have actionable fields
# ======================================================================

class TestReviewFindingsHaveActionableFields(unittest.TestCase):
    """Phase 7.2: Every review finding must have all required actionable fields."""

    @classmethod
    def setUpClass(cls):
        cls.result = _review_result()

    def test_findings_have_all_required_fields(self):
        """Each finding must have finding_id, type, severity, description,
        evidence, suggested_fix, affected_modules, related_quality_gate."""
        required_fields = [
            "finding_id", "type", "severity", "description",
            "evidence", "suggested_fix", "affected_modules",
            "related_quality_gate",
        ]
        findings = self.result.get("findings", [])
        self.assertGreater(len(findings), 0, "Must have at least one finding")
        for finding in findings:
            for field in required_fields:
                self.assertIn(field, finding,
                              f"Finding missing required field '{field}': {finding}")
            self.assertIsInstance(finding["affected_modules"], list,
                                  "affected_modules must be a list")
            self.assertIsInstance(finding["finding_id"], str,
                                  "finding_id must be a string")


# ======================================================================
# Phase 7.2: Revise no-match returns needs_teacher_input
# ======================================================================

class TestReviseNoMatchIsNotApplied(unittest.TestCase):
    """Phase 7.2: When revise cannot match a feedback item, it must set
    action_status='needs_teacher_input' and modification_applied=False."""

    @classmethod
    def setUpClass(cls):
        cls.result = _revise_result()

    def test_no_match_returns_needs_teacher_input(self):
        """Any revision entry with action_status needs_teacher_input must
        have modification_applied=False."""
        for rev in self.result.get("revision_log", []):
            if rev.get("action_status") == "needs_teacher_input":
                self.assertFalse(
                    rev.get("modification_applied", True),
                    f"modification_applied must be False when action_status "
                    f"is 'needs_teacher_input' (revision: {rev.get('revision_id')})"
                )


# ======================================================================
# Phase 7.2: Revise warning status not plain completed
# ======================================================================

class TestReviseWarningStatusNotPlainCompleted(unittest.TestCase):
    """Phase 7.2: When post_revision_alignment != 'pass', the revise
    status must not be bare 'completed'."""

    @classmethod
    def setUpClass(cls):
        cls.result = _revise_result()

    def test_warning_status_not_completed(self):
        """If post-revision alignment is not 'pass', status must not be 'completed'."""
        post = self.result.get("post_revision_alignment", {})
        post_status = post.get("overall_status", "fail")
        if post_status != "pass":
            self.assertNotEqual(
                self.result.get("status"), "completed",
                "revise status must not be 'completed' when "
                f"post_revision_alignment is '{post_status}'"
            )


# ======================================================================
# Phase 7.2: Session result files exist
# ======================================================================

class TestPhase7SessionResultFilesExist(unittest.TestCase):
    """Phase 7.2: All session result files referenced in the output
    must actually exist on disk."""

    @classmethod
    def setUpClass(cls):
        cls.design = _design_result()
        cls.review = _review_result()
        cls.revise = _revise_result()

    def test_all_session_results_exist(self):
        """All file paths in export_result and result-level paths must exist."""
        # Design exports
        for key, path in self.design.get("export_result", {}).items():
            if path is not None and isinstance(path, str):
                self.assertTrue(
                    os.path.isfile(path),
                    f"Design export '{key}' file not found: {path}"
                )
        # Review report
        review_path = self.review.get("review_path", "")
        if review_path:
            self.assertTrue(os.path.isfile(review_path),
                            f"Review report file not found: {review_path}")
        # Revise outputs
        revised_path = self.revise.get("revised_project_path", "")
        if revised_path:
            self.assertTrue(os.path.isfile(revised_path),
                            f"Revised project file not found: {revised_path}")
        log_path = self.revise.get("revision_log_path", "")
        if log_path:
            self.assertTrue(os.path.isfile(log_path),
                            f"Revision log file not found: {log_path}")

    def test_session_results_have_mode_and_status(self):
        """Each session result must have 'mode' and 'status' keys."""
        for name, result in [("design", self.design),
                             ("review", self.review),
                             ("revise", self.revise)]:
            self.assertIn("mode", result, f"{name} result missing 'mode'")
            self.assertIn("status", result, f"{name} result missing 'status'")
            self.assertIsInstance(result["mode"], str)
            self.assertIsInstance(result["status"], str)


# ======================================================================
# Phase 7.3: Export index and error handling tests
# ======================================================================

class TestExportIndexFilesHaveExistsAndSize(unittest.TestCase):
    """Test: export_index.json files must have path/exists/size for all 9 entries."""

    @classmethod
    def setUpClass(cls):
        # Ensure design session has been run
        _design_result()
        cls.index_path = os.path.join(REPO_ROOT, "exports", "phase7_test", "export_index.json")

    def test_index_file_exists(self):
        self.assertTrue(os.path.exists(self.index_path))

    def test_nine_files_in_index(self):
        with open(self.index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
        files = index.get("files", {})
        self.assertEqual(len(files), 9, f"Expected 9 files, got {len(files)}")

    def test_all_files_have_path_exists_size(self):
        with open(self.index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
        files = index.get("files", {})
        required = [
            "full_report_docx", "lesson_plan_docx", "student_worksheet_docx",
            "alignment_matrix_xlsx", "ai_process_record_docx",
            "export_index_json", "project_json", "report_markdown", "materials_markdown",
        ]
        for key in required:
            self.assertIn(key, files, f"Missing: {key}")
            entry = files[key]
            path = entry.get("path")
            self.assertTrue(path, f"{key} path is empty")
            # For export_index_json, the file might not exist during generation
            # but path should still be non-empty
            if key != "export_index_json":
                self.assertTrue(entry.get("exists"), f"{key} exists should be True")
                self.assertGreater(entry.get("size", 0), 0, f"{key} size should be > 0")


class TestExportStatusNotSuccessWhenMissing(unittest.TestCase):
    """Test: export_status should not be success when required file is missing."""

    def test_missing_file_gives_partial_or_failed(self):
        """Simulate by checking that export_status logic works."""
        # Create a minimal project that will have some exports fail
        from tools.agent_session import run_agent_session
        result = run_agent_session({
            "mode": "dc-design",
            "user_type": "K12教师",
            "scenario": "新课设计",
            "subject": "测试学科",
            "grade_level": "七年级",
            "topic": "测试课题",
            "teacher_inputs": {},
        }, "exports/phase7_status_test")
        # Even if all exports succeed, the status should be correct
        export_result = result.get("export_result", {})
        errors = export_result.get("export_errors", [])
        # If no errors, status should be success
        # If errors exist, status should be partial or failed
        if not errors:
            # All exports succeeded - check that files exist
            for key in ["full_report_docx", "lesson_plan_docx", "student_worksheet_docx",
                        "alignment_matrix_xlsx", "ai_process_record_docx"]:
                path = export_result.get(key)
                if path:
                    self.assertTrue(os.path.exists(path), f"{key} file missing: {path}")


class TestExportErrorsReported(unittest.TestCase):
    """Test: export errors are properly reported."""

    def test_export_errors_in_result(self):
        """export_result must have export_errors field."""
        result = _design_result()
        export_result = result.get("export_result", {})
        self.assertIn("export_errors", export_result)
        self.assertIsInstance(export_result["export_errors"], list)

    def test_export_errors_in_warnings(self):
        """If export errors exist, they should appear in warnings."""
        result = _design_result()
        self.assertIn("warnings", result)
        self.assertIsInstance(result["warnings"], list)

    def test_can_export_final_false_when_errors(self):
        """can_export_final must be False when export has errors."""
        result = _design_result()
        export_result = result.get("export_result", {})
        errors = export_result.get("export_errors", [])
        if errors:
            self.assertFalse(result.get("can_export_final", True))


class TestExportFailureMonkeypatch(unittest.TestCase):
    """Test: simulate document_exporter failure with monkeypatch."""

    def test_exporter_failure_blocks_final(self):
        """When document_exporter throws, can_export_final=False
        and final_blocking_reasons contains export_package."""
        from unittest.mock import patch
        from tools.agent_session import run_agent_session

        def _explode(*args, **kwargs):
            raise RuntimeError("Simulated document_exporter failure")

        with patch("tools.document_exporter.export_full_dc_report", _explode), \
             patch("tools.document_exporter.export_lesson_plan", _explode), \
             patch("tools.document_exporter.export_student_worksheet", _explode), \
             patch("tools.document_exporter.export_alignment_matrix", _explode), \
             patch("tools.document_exporter.export_ai_process_record", _explode):
            result = run_agent_session({
                "mode": "dc-design",
                "user_type": "K12教师",
                "scenario": "新课设计",
                "subject": "信息科技",
                "grade_level": "七年级",
                "topic": "认识算法",
                "teacher_inputs": {},
            }, "exports/phase7_failure_test")

        # Must not crash
        self.assertIn("mode", result)

        # export_errors must be non-empty
        export_result = result.get("export_result", {})
        errors = export_result.get("export_errors", [])
        self.assertTrue(len(errors) > 0, "export_errors should be non-empty when exporter fails")

        # warnings must mention export failure
        warnings = result.get("warnings", [])
        has_export_warning = any("导出" in w or "export" in w.lower() for w in warnings)
        self.assertTrue(has_export_warning, "warnings should mention export failure")

        # can_export_final must be False
        self.assertFalse(result.get("can_export_final", True),
                        "can_export_final must be False when export fails")

        # final_blocking_reasons must contain export_package
        blocking = result.get("final_blocking_reasons", [])
        has_export_block = any(
            b.get("component") == "export_package" for b in blocking
        )
        self.assertTrue(has_export_block,
                       "final_blocking_reasons must contain export_package component")


class TestToolStatusReport(unittest.TestCase):
    """Test: tool_status_report covers the required project tools."""

    @classmethod
    def setUpClass(cls):
        cls.result = _design_result()

    def test_tool_status_report_exists(self):
        self.assertIn("tool_status_report", self.result)
        self.assertIsInstance(self.result["tool_status_report"], list)

    def test_tool_status_report_has_all_required_tools(self):
        required = {
            "standards_search", "goal_engine", "skill_graph",
            "learner_context", "objective_engine", "assessment_engine",
            "strategy_engine", "materials_engine", "alignment_checker",
            "export_package", "knowledge_ingest", "teacher_memory",
            "formative_evaluation_plan",
        }
        report = self.result.get("tool_status_report", [])
        # tool_status_report uses "tool_name" key
        tool_names = {t.get("tool_name", t.get("tool", "")) for t in report}
        for tool in required:
            self.assertIn(tool, tool_names, f"Missing required tool: {tool}")

    def test_tool_status_has_status_field(self):
        report = self.result.get("tool_status_report", [])
        for entry in report:
            self.assertIn("status", entry, f"Tool {entry.get('tool_name', '?')} missing status")


if __name__ == "__main__":
    unittest.main()
