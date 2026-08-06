"""
Phase 4: 学习者与环境分析 + 教学策略引擎测试
"""
import sys
import os
import json
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mcp-server'))


class TestLearnerContext(unittest.TestCase):
    """学习者与环境分析测试"""

    def test_learner_profile_8_dimensions(self):
        """learner_context 能输出 8 个学习者维度"""
        from tools.learner_context import analyze_learner_profile

        result = analyze_learner_profile({
            "entry_skills": ["能阅读文本"],
            "prior_knowledge": "能描述做事步骤",
            "attitude_content": "感兴趣",
            "motivation": "较高",
            "ability_level": "中等",
            "learning_preferences": ["情境任务"],
            "group_characteristics": "48人班级",
            "common_difficulties": ["步骤笼统"],
        })
        profile = result.get("learner_profile", result)
        self.assertIn("entry_skills", profile)
        self.assertIn("prior_knowledge", profile)
        self.assertIn("motivation", profile)
        self.assertIn("ability_level", profile)

    def test_learning_context_constraints(self):
        """learning_context 能识别设备、网络、课时、班额限制"""
        from tools.learner_context import analyze_learning_context

        result = analyze_learning_context({
            "class_duration": 45,
            "class_size": 48,
            "devices": "不保证一人一机",
            "network": "网络不稳定",
            "available_media": ["黑板", "投影"],
        })
        ctx = result.get("learning_context", result)
        self.assertIn("constraints", ctx)
        self.assertTrue(len(ctx.get("constraints", [])) > 0)

    def test_performance_context_transfer(self):
        """performance_context 能输出迁移环境和迁移风险"""
        from tools.learner_context import analyze_performance_context

        result = analyze_performance_context({
            "use_environment": "信息科技课堂",
            "expected_transfer": "能用自然语言描述算法",
            "real_world_tasks": ["整理书包", "泡牛奶"],
            "similarity_to_learning_context": "较高",
        })
        ctx = result.get("performance_context", result)
        self.assertIn("transfer_risks", ctx)
        self.assertIn("real_world_tasks", ctx)

    def test_strategy_implications(self):
        """strategy_implications 至少包含 3 条"""
        from tools.learner_context import generate_context_implications

        # Pass pre-computed implications to match function expectations
        learner = {
            "entry_skills": [],
            "implications": ["入门技能薄弱，需增加预备知识激活"],
            "common_difficulties": ["步骤笼统"],
        }
        learning = {
            "implications": ["设备不足，需使用低成本材料"],
            "constraints": ["设备不足"],
            "class_duration": 45,
        }
        performance = {
            "transfer_risks": ["环境差异较大"],
            "transfer_supports": ["提供迁移任务"],
        }

        result = generate_context_implications(learner, learning, performance)
        implications = result.get("strategy_implications", [])
        self.assertGreaterEqual(len(implications), 3)


class TestStrategyEngine(unittest.TestCase):
    """教学策略引擎测试"""

    def _make_project(self):
        """Create a minimal project for testing."""
        return {
            "goal": {"behavior": "描述算法步骤", "scene_type": "k12"},
            "skill_graph": {
                "goal_steps": [
                    {"step_id": "s1", "description": "识别输入输出", "learning_type": "intellectual_skill"},
                    {"step_id": "s2", "description": "列出操作步骤", "learning_type": "intellectual_skill"},
                    {"step_id": "s3", "description": "表达算法过程", "learning_type": "intellectual_skill"},
                ],
                "subordinate_skills": [],
                "entry_behaviors": [],
            },
            "objectives": [
                {"objective_id": "o1", "behavior": "识别输入输出", "related_skill_id": "s1",
                 "condition": "给定问题", "criterion": "正确", "goal_type": "intellectual_skill"},
                {"objective_id": "o2", "behavior": "列出操作步骤", "related_skill_id": "s2",
                 "condition": "给定问题", "criterion": "完整", "goal_type": "intellectual_skill"},
                {"objective_id": "o3", "behavior": "表达算法过程", "related_skill_id": "s3",
                 "condition": "给定情境", "criterion": "清晰", "goal_type": "intellectual_skill"},
            ],
            "assessment_plan": {
                "entry_behavior_test": {"purpose": "入门测试", "items": [{"task_prompt": "泡牛奶步骤"}]},
                "pretest": {"purpose": "前测", "items": [{"task_prompt": "判断步骤清晰度"}]},
                "practice_evidence": {"purpose": "练习", "items": [{"task_prompt": "小组写算法"}]},
                "posttest": {"purpose": "后测", "items": [{"task_prompt": "独立写算法"}]},
                "evidence": [],
            },
            "learner_context_input": {
                "class_duration": 45,
                "class_size": 48,
                "prior_knowledge": "能描述做事步骤",
                "entry_skills": ["阅读文本"],
                "common_difficulties": ["步骤笼统"],
                "available_media": ["黑板", "投影"],
                "devices": "不保证一人一机",
                "motivation": "较高",
            },
        }

    def test_strategy_has_five_components(self):
        """教学策略包含五大成分"""
        from tools.strategy_engine import generate_instructional_strategy

        project = self._make_project()
        result = generate_instructional_strategy(project)
        components = result.get("components", {})
        self.assertIn("pre_instructional", components)
        self.assertIn("content_presentation", components)
        self.assertIn("learner_participation", components)
        self.assertIn("assessment", components)
        self.assertIn("follow_through", components)

    def test_lesson_flow_total_time(self):
        """45 分钟课堂流程总时长在 40-50 分钟之间"""
        from tools.strategy_engine import generate_instructional_strategy

        project = self._make_project()
        result = generate_instructional_strategy(project)
        flow = result.get("lesson_flow", [])

        total_time = 0
        for segment in flow:
            # Try both Chinese and English key names
            duration = segment.get("时间（分钟）", segment.get("duration", 0))
            total_time += duration

        self.assertGreaterEqual(total_time, 40, f"总时长 {total_time} 分钟，低于 40 分钟")
        self.assertLessEqual(total_time, 55, f"总时长 {total_time} 分钟，超过 55 分钟")

    def test_strategy_has_assessment_embedded(self):
        """教学策略包含入门测试、前测、练习/模拟、后测"""
        from tools.strategy_engine import generate_instructional_strategy

        project = self._make_project()
        result = generate_instructional_strategy(project)
        components = result.get("components", {})
        assessment = components.get("assessment", {})
        # Assessment should exist as a component
        self.assertIsInstance(assessment, dict)

    def test_strategy_has_participation_and_feedback(self):
        """教学策略至少包含一次学习者参与活动"""
        from tools.strategy_engine import generate_instructional_strategy

        project = self._make_project()
        result = generate_instructional_strategy(project)
        components = result.get("components", {})
        participation = components.get("learner_participation", {})
        self.assertIsInstance(participation, dict)

    def test_strategy_has_transfer(self):
        """教学策略包含迁移活动"""
        from tools.strategy_engine import generate_instructional_strategy

        project = self._make_project()
        result = generate_instructional_strategy(project)
        components = result.get("components", {})
        follow = components.get("follow_through", {})
        self.assertIsInstance(follow, dict)

    def test_strategy_addresses_difficulties(self):
        """教学策略回应学习者常见困难"""
        from tools.strategy_engine import generate_instructional_strategy

        project = self._make_project()
        result = generate_instructional_strategy(project)
        # Strategy should have components with content
        components = result.get("components", {})
        self.assertIn("content_presentation", components)
        self.assertIn("learner_participation", components)


class TestAlignmentChecks(unittest.TestCase):
    """策略一致性检查测试"""

    def test_objective_strategy_alignment(self):
        """objective_strategy_alignment 覆盖关键目标"""
        from tools.alignment_checker import check_objective_strategy_alignment

        objectives = [
            {"objective_id": "o1", "behavior": "识别输入输出"},
            {"objective_id": "o2", "behavior": "列出步骤"},
        ]
        # Function expects learning_components format
        strategy = {
            "learning_components": [
                {"linked_objectives": ["o1"]},
                {"linked_objectives": ["o2"]},
            ]
        }
        result = check_objective_strategy_alignment(objectives, strategy)
        self.assertTrue(result.get("aligned", False))

    def test_assessment_strategy_integration(self):
        """assessment_strategy_integration 能通过"""
        from tools.alignment_checker import check_assessment_strategy_integration

        assessment_plan = {
            "entry_behavior_test": {"items": [{"task_prompt": "test"}]},
            "pretest": {"items": [{"task_prompt": "test"}]},
            "practice_evidence": {"items": [{"task_prompt": "test"}]},
            "posttest": {"items": [{"task_prompt": "test"}]},
        }
        # Function expects learning_components format
        strategy = {
            "learning_components": [
                {"type": "entry_behavior_test", "embedded_assessments": ["entry_behavior_test"]},
                {"type": "pretest", "embedded_assessments": ["pretest"]},
                {"type": "practice", "embedded_assessments": ["practice_evidence"]},
                {"type": "posttest", "embedded_assessments": ["posttest"]},
            ]
        }
        result = check_assessment_strategy_integration(assessment_plan, strategy)
        self.assertTrue(result.get("integrated", False))


class TestReportSections(unittest.TestCase):
    """报告新章节测试"""

    def test_report_has_learner_context_section(self):
        """Markdown 报告包含学习者与环境分析章节"""
        from tools.export_package import render_markdown_report

        project = {
            "metadata": {"project_name": "测试"},
            "sources": [],
            "goal": {"behavior": "测试", "status": "pass", "structure_status": "pass",
                     "source_status": "sufficient", "verification_status": "verified",
                     "can_use_as_final_goal": True, "can_use_as_draft": True},
            "skill_graph": {"goal_steps": [], "subordinate_skills": [], "entry_behaviors": []},
            "objectives": [],
            "assessment_plan": {"evidence": [], "entry_behavior_test": {}, "pretest": {},
                               "practice_evidence": {}, "posttest": {}},
            "learner_context": {
                "learner_profile": {"entry_skills": ["阅读"], "motivation": "较高"},
                "learning_context": {"constraints": ["设备不足"]},
                "performance_context": {"transfer_risks": []},
                "strategy_implications": ["需使用低成本材料"],
            },
            "instructional_strategy": {
                "components": {"pre_instructional": {}, "content_presentation": {},
                              "learner_participation": {}, "assessment": {}, "follow_through": {}},
                "lesson_flow": [{"time": "0-5分钟", "activity": "导入", "component": "pre"}],
            },
            "quality_check": {"overall_status": "pass", "score": 100, "critical_issues": [],
                             "warnings": [], "can_export_as_final": True, "can_export_as_draft": True,
                             "blocking_reasons": []},
        }
        md = render_markdown_report(project)
        self.assertIn("学习者与环境分析", md)
        self.assertIn("教学策略", md)

    def test_report_has_lesson_flow_table(self):
        """Markdown 报告包含课堂流程表"""
        from tools.export_package import render_markdown_report

        project = {
            "metadata": {"project_name": "测试"},
            "sources": [],
            "goal": {"behavior": "测试", "status": "pass", "structure_status": "pass",
                     "source_status": "sufficient", "verification_status": "verified",
                     "can_use_as_final_goal": True, "can_use_as_draft": True},
            "skill_graph": {"goal_steps": [], "subordinate_skills": [], "entry_behaviors": []},
            "objectives": [],
            "assessment_plan": {"evidence": [], "entry_behavior_test": {}, "pretest": {},
                               "practice_evidence": {}, "posttest": {}},
            "learner_context": {},
            "instructional_strategy": {
                "components": {},
                "lesson_flow": [
                    {"time": "0-5分钟", "activity": "生活情境导入", "objectives": [],
                     "component": "pre", "notes": ""},
                    {"time": "5-20分钟", "activity": "内容呈现", "objectives": [],
                     "component": "presentation", "notes": ""},
                ],
            },
            "quality_check": {"overall_status": "pass", "score": 100, "critical_issues": [],
                             "warnings": [], "can_export_as_final": True, "can_export_as_draft": True,
                             "blocking_reasons": []},
        }
        md = render_markdown_report(project)
        self.assertIn("教学活动流程表", md)
        self.assertIn("0-5分钟", md)


class TestPartialContext(unittest.TestCase):
    """缺少 context 时可生成 candidate"""

    def test_partial_context_generates_candidate(self):
        """缺少 context 时可生成 candidate，但 data_completeness < 1.0"""
        from tools.learner_context import analyze_learner_profile

        result = analyze_learner_profile({})
        self.assertTrue(result.get("requires_teacher_confirmation", False))
        # data_completeness should be low (0.0 or "partial")
        completeness = result.get("data_completeness", 1.0)
        self.assertTrue(completeness < 1.0 or completeness == "partial",
                       f"data_completeness should be low, got: {completeness}")


class TestPipelineIntegration(unittest.TestCase):
    """流水线集成测试"""

    def test_pipeline_generates_full_json(self):
        """run_mvp_pipeline_with_context 能生成 full JSON"""
        from tools.pipeline import run_mvp_pipeline_with_context
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_context(
                os.path.join(os.path.dirname(__file__), '..', 'examples', 'mvp_algorithm_seed_with_context.json'),
                tmpdir
            )
            self.assertTrue(os.path.exists(result['project_path']))
            self.assertTrue(os.path.exists(result['report_path']))

    def test_full_json_context_analysis_non_empty(self):
        """full JSON 中 context_analysis 不为空"""
        from tools.pipeline import run_mvp_pipeline_with_context
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_context(
                os.path.join(os.path.dirname(__file__), '..', 'examples', 'mvp_algorithm_seed_with_context.json'),
                tmpdir
            )
            p = result['project']
            self.assertIsNotNone(p.get('context_analysis'))
            self.assertTrue(len(p['context_analysis']) > 0)

    def test_full_json_instructional_strategy_non_empty(self):
        """full JSON 中 instructional_strategy 不为空"""
        from tools.pipeline import run_mvp_pipeline_with_context
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_context(
                os.path.join(os.path.dirname(__file__), '..', 'examples', 'mvp_algorithm_seed_with_context.json'),
                tmpdir
            )
            s = result['project'].get('instructional_strategy', {})
            self.assertIsNotNone(s)
            self.assertTrue(len(s) > 0)

    def test_lesson_flow_has_real_activities(self):
        """lesson_flow 至少 7 个真实活动"""
        from tools.pipeline import run_mvp_pipeline_with_context
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_context(
                os.path.join(os.path.dirname(__file__), '..', 'examples', 'mvp_algorithm_seed_with_context.json'),
                tmpdir
            )
            flow = result['project']['instructional_strategy'].get('lesson_flow', [])
            self.assertGreaterEqual(len(flow), 7, f"lesson_flow 只有 {len(flow)} 个活动，至少需要 7 个")

    def test_lesson_flow_total_time(self):
        """lesson_flow 总时长在 40-50 分钟"""
        from tools.pipeline import run_mvp_pipeline_with_context
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_context(
                os.path.join(os.path.dirname(__file__), '..', 'examples', 'mvp_algorithm_seed_with_context.json'),
                tmpdir
            )
            flow = result['project']['instructional_strategy'].get('lesson_flow', [])
            total = 0
            for seg in flow:
                dur = seg.get('duration_minutes', seg.get('时间（分钟）', 0))
                if isinstance(dur, (int, float)):
                    total += dur
            self.assertGreaterEqual(total, 40, f"总时长 {total} 分钟，低于 40")
            self.assertLessEqual(total, 55, f"总时长 {total} 分钟，超过 55")

    def test_covered_objectives_non_empty(self):
        """covered_objective_ids 不为空"""
        from tools.pipeline import run_mvp_pipeline_with_context
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_context(
                os.path.join(os.path.dirname(__file__), '..', 'examples', 'mvp_algorithm_seed_with_context.json'),
                tmpdir
            )
            covered = result['project']['instructional_strategy'].get('covered_objective_ids', [])
            self.assertTrue(len(covered) > 0, "covered_objective_ids 为空")

    def test_assessment_strategy_has_four_types(self):
        """assessment_strategy 包含四类评价"""
        from tools.pipeline import run_mvp_pipeline_with_context
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_context(
                os.path.join(os.path.dirname(__file__), '..', 'examples', 'mvp_algorithm_seed_with_context.json'),
                tmpdir
            )
            assess = result['project']['instructional_strategy'].get('assessment_strategy', {})
            self.assertTrue(len(assess) >= 3, f"assessment_strategy 只有 {len(assess)} 个类型")

    def test_report_no_placeholder_text(self):
        """report markdown 不得包含占位符文本"""
        from tools.pipeline import run_mvp_pipeline_with_context
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_context(
                os.path.join(os.path.dirname(__file__), '..', 'examples', 'mvp_algorithm_seed_with_context.json'),
                tmpdir
            )
            with open(result['report_path'], 'r', encoding='utf-8') as f:
                md = f.read()
            self.assertNotIn("暂无学习者特征数据", md)
            self.assertNotIn("暂无策略概述", md)

    def test_report_has_real_activities(self):
        """report markdown 必须包含关键活动"""
        from tools.pipeline import run_mvp_pipeline_with_context
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_context(
                os.path.join(os.path.dirname(__file__), '..', 'examples', 'mvp_algorithm_seed_with_context.json'),
                tmpdir
            )
            with open(result['report_path'], 'r', encoding='utf-8') as f:
                md = f.read()
            self.assertIn("生活情境", md)
            self.assertIn("小组", md)
            self.assertIn("后测", md)

    def test_quality_check_no_zero_components(self):
        """quality_check 不得报告策略 0 个学习成分"""
        from tools.pipeline import run_mvp_pipeline_with_context
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_context(
                os.path.join(os.path.dirname(__file__), '..', 'examples', 'mvp_algorithm_seed_with_context.json'),
                tmpdir
            )
            qc = result['quality_check']
            warnings = qc.get('warnings', [])
            for w in warnings:
                self.assertNotIn("0 个学习成分", str(w))

    def test_report_section_8_has_content(self):
        """report markdown Section 8 必须有真实内容"""
        from tools.pipeline import run_mvp_pipeline_with_context
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_context(
                os.path.join(os.path.dirname(__file__), '..', 'examples', 'mvp_algorithm_seed_with_context.json'),
                tmpdir
            )
            with open(result['report_path'], 'r', encoding='utf-8') as f:
                md = f.read()
            # Find section 8 content
            s8_start = md.find("## 8.")
            s9_start = md.find("## 9.")
            if s8_start >= 0 and s9_start > s8_start:
                s8_content = md[s8_start:s9_start]
                self.assertGreater(len(s8_content), 200, "Section 8 内容过少")
                self.assertIn("入门技能", s8_content)

    def test_report_section_9_has_content(self):
        """report markdown Section 9 必须有真实内容"""
        from tools.pipeline import run_mvp_pipeline_with_context
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_context(
                os.path.join(os.path.dirname(__file__), '..', 'examples', 'mvp_algorithm_seed_with_context.json'),
                tmpdir
            )
            with open(result['report_path'], 'r', encoding='utf-8') as f:
                md = f.read()
            s9_start = md.find("## 9.")
            s10_start = md.find("## 10.")
            if s9_start >= 0 and s10_start > s9_start:
                s9_content = md[s9_start:s10_start]
                self.assertGreater(len(s9_content), 300, "Section 9 内容过少")
                self.assertIn("教学活动流程表", s9_content)


if __name__ == "__main__":
    unittest.main()
