"""
Phase 5.1: 教学材料生成测试（严格版 v2）
"""
import sys
import os
import json
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mcp-server'))

SEED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'examples', 'mvp_algorithm_seed_with_context.json')


def _make_project():
    """Create a minimal project for unit testing."""
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
            "class_duration": 45, "class_size": 48,
            "prior_knowledge": "能描述做事步骤",
            "entry_skills": ["阅读文本"],
            "common_difficulties": ["步骤笼统"],
            "available_media": ["黑板", "投影", "学习单"],
            "devices": "不保证一人一机",
            "motivation": "较高",
        },
        "instructional_strategy": {"lesson_flow": [], "components": {}},
        "context_analysis": {"strategy_implications": []},
    }


class TestMaterialsEngine(unittest.TestCase):
    """materials_engine 单元测试"""

    def test_generates_nine_materials(self):
        from tools.materials_engine import generate_instructional_materials
        result = generate_instructional_materials(_make_project())
        for key in ['teacher_guide', 'student_worksheet', 'entry_test_sheet',
                    'pretest_sheet', 'group_task_sheet', 'peer_review_checklist',
                    'posttest_sheet', 'board_design', 'simple_lesson_plan']:
            self.assertIn(key, result)

    def test_materials_have_metadata(self):
        from tools.materials_engine import generate_instructional_materials
        result = generate_instructional_materials(_make_project())
        for key, mat in result.items():
            for field in ['material_id', 'title', 'material_type', 'content', 'status']:
                self.assertIn(field, mat, f"{key} 缺少 {field}")

    def test_objectives_no_raw_dict(self):
        """教学目标不应该是 Python dict 原样输出"""
        from tools.materials_engine import _get_objectives_text
        project = _make_project()
        result = _get_objectives_text(project)
        for text in result:
            self.assertNotIn("{'objective_id'", text, f"目标包含原始 dict: {text[:50]}")
            self.assertTrue(len(text) > 5, f"目标文本过短: {text}")

    def test_student_worksheet_has_six_tasks(self):
        from tools.materials_engine import generate_student_worksheet
        result = generate_student_worksheet(_make_project())
        content = result.get("content", result)
        # Count task-like keys
        task_keys = [k for k in content.keys() if "任务" in str(k)]
        self.assertGreaterEqual(len(task_keys), 6, f"只有 {len(task_keys)} 个任务，需要至少 6 个")
        # Check for fill-in areas
        text = json.dumps(content, ensure_ascii=False)
        self.assertTrue("我的步骤" in text or "填写" in text or "1." in text)

    def test_posttest_has_rubric(self):
        from tools.materials_engine import generate_posttest_sheet
        result = generate_posttest_sheet(_make_project())
        content = result.get("content", result)
        text = json.dumps(content, ensure_ascii=False)
        self.assertTrue("评分" in text or "维度" in text or "得分" in text)

    def test_board_design_has_features(self):
        from tools.materials_engine import generate_board_design
        result = generate_board_design(_make_project())
        content = result.get("content", result)
        text = json.dumps(content, ensure_ascii=False)
        self.assertTrue("明确" in text and "有限" in text and "有序" in text)


class TestPipelineWithMaterials(unittest.TestCase):
    """流水线集成测试（严格版）"""

    def test_file_names_correct(self):
        from tools.pipeline import run_mvp_pipeline_with_materials
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_materials(SEED_PATH, tmpdir)
            self.assertTrue(result["project_path"].endswith("mvp_algorithm_project_with_materials_full.json"))
            self.assertTrue(result["report_path"].endswith("mvp_algorithm_report_with_materials.md"))
            self.assertTrue(result["materials_path"].endswith("mvp_algorithm_materials.md"))

    def test_full_json_has_nine_materials(self):
        from tools.pipeline import run_mvp_pipeline_with_materials
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_materials(SEED_PATH, tmpdir)
            with open(result["project_path"], 'r', encoding='utf-8') as f:
                project = json.load(f)
            mats = project.get("instructional_materials", {})
            self.assertGreaterEqual(len(mats), 9)
            for key in ['teacher_guide', 'student_worksheet', 'entry_test_sheet',
                        'pretest_sheet', 'group_task_sheet', 'peer_review_checklist',
                        'posttest_sheet', 'board_design', 'simple_lesson_plan']:
                self.assertIn(key, mats)

    def test_material_alignment_coverage(self):
        from tools.pipeline import run_mvp_pipeline_with_materials
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_materials(SEED_PATH, tmpdir)
            with open(result["project_path"], 'r', encoding='utf-8') as f:
                project = json.load(f)
            ma = project.get("material_alignment", {})
            self.assertGreaterEqual(ma.get("coverage_rate", 0), 0.99)
            self.assertEqual(len(ma.get("missing_assessment_materials", [])), 0)

    def test_report_strict_checks(self):
        """Report must contain real material content, not just titles."""
        import re
        from tools.pipeline import run_mvp_pipeline_with_materials
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_materials(SEED_PATH, tmpdir)
            with open(result["report_path"], 'r', encoding='utf-8') as f:
                md = f.read()

            # Content checks
            self.assertIn("教学材料包", md)
            self.assertIn("学生学习单", md)
            self.assertIn("任务一", md)
            self.assertIn("任务六", md)
            self.assertIn("我的步骤", md)
            self.assertIn("互评检查表", md)
            self.assertIn("后测任务单", md)
            self.assertIn("评分标准", md)
            self.assertIn("板书设计", md)
            self.assertIn("明确", md)
            self.assertIn("有限", md)
            self.assertIn("有序", md)
            self.assertIn("材料一致性检查", md)

            # No raw dict output
            dict_matches = re.findall(r"\{'[a-z_]+':", md)
            self.assertEqual(len(dict_matches), 0, f"Found {len(dict_matches)} raw dict outputs")

            # No empty bullets
            self.assertNotIn("- :", md)
            self.assertNotIn("- \n", md)

    def test_materials_md_strict_checks(self):
        """Materials MD must contain real copyable content."""
        import re
        from tools.pipeline import run_mvp_pipeline_with_materials
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_mvp_pipeline_with_materials(SEED_PATH, tmpdir)
            self.assertTrue(os.path.exists(result["materials_path"]))
            size = os.path.getsize(result["materials_path"])
            self.assertGreater(size, 10000, f"materials.md too small: {size} bytes")

            with open(result["materials_path"], 'r', encoding='utf-8') as f:
                md = f.read()

            # Content checks
            self.assertIn("任务一", md)
            self.assertIn("任务六", md)
            self.assertIn("我的步骤", md)
            self.assertIn("互评检查表", md)
            self.assertIn("评分标准", md)
            self.assertIn("板书设计", md)
            self.assertIn("算法", md)
            self.assertIn("明确", md)
            self.assertIn("有限", md)
            self.assertIn("有序", md)

            # No raw dict output
            dict_matches = re.findall(r"\{'[a-z_]+':", md)
            self.assertEqual(len(dict_matches), 0, f"Found {len(dict_matches)} raw dict outputs in materials MD")

            # No empty bullets
            self.assertNotIn("- :", md)

            # Must have real task content (not just metadata)
            task_content_lines = [l for l in md.split('\n') if '步骤' in l or '填写' in l or '检查' in l]
            self.assertGreater(len(task_content_lines), 5, "Materials MD lacks real task content")


if __name__ == "__main__":
    unittest.main()
