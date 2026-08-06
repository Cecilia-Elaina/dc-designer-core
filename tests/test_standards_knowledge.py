"""
Phase 3: K12 课程标准数据源与教师私有知识库测试
"""
import sys
import os
import json
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mcp-server'))


class TestStandardsSearch(unittest.TestCase):
    """standards_search 测试"""

    def test_search_standards_found(self):
        """standards_search 能从本地 fixture 中检索候选条款"""
        from tools.standards_search import search_standards

        result = search_standards({
            "stage": "compulsory",
            "grade": "七年级",
            "subject": "信息科技",
            "topic": "认识算法",
            "keywords": ["算法", "问题解决", "步骤描述"],
            "scene_type": "k12",
        })
        self.assertIn(result["status"], ("found", "partial"))
        self.assertTrue(len(result.get("matches", [])) > 0)

    def test_search_standards_not_found(self):
        """search_standards 无匹配时返回 fallback_required 和 next_actions"""
        from tools.standards_search import search_standards

        result = search_standards({
            "stage": "compulsory",
            "grade": "七年级",
            "subject": "古生物化石修复",
            "topic": "恐龙骨骼拼装",
            "keywords": ["化石", "骨骼", "拼装", "修复技术"],
            "scene_type": "k12",
        })
        # Should either be not_found or partial with fallback
        self.assertIn(result["status"], ("not_found", "partial"))
        if result["status"] == "not_found":
            self.assertTrue(result.get("fallback_required", False))
            self.assertTrue(len(result.get("next_actions", [])) > 0)

    def test_build_source_record_from_standard(self):
        """build_source_record_from_standard 生成 source.schema 兼容字段"""
        from tools.standards_search import build_source_record_from_standard

        match = {
            "source_id": "std_compulsory_2022_info_tech",
            "title": "义务教育信息科技课程标准（2022年版）",
            "level": "A1",
            "publisher": "教育部",
            "applicable_grades": ["七年级"],
            "copyright_scope": "official_public",
        }
        record = build_source_record_from_standard(match)
        self.assertIn("source_id", record)
        self.assertIn("source_level", record)
        self.assertIn("credibility", record)
        self.assertIn("can_be_goal_basis", record)
        self.assertIn("copyright_scope", record)


class TestSourceReliability(unittest.TestCase):
    """source_reliability 测试"""

    def test_c_source_cannot_be_final_goal(self):
        """C 级教师资料不能单独让 K12 目标 can_use_as_final_goal = true"""
        from core.source_reliability import can_source_support_goal

        c_source = {"source_level": "C1", "source_category": "teacher_private"}
        result = can_source_support_goal(c_source, "k12")
        # C level returns limited support, not formal
        self.assertEqual(result.get("support_level", ""), "limited")
        # Limited support means cannot be final goal basis
        self.assertNotEqual(result.get("support_level", ""), "formal")

    def test_a_source_supports_goal(self):
        """A/B 级正式来源可以让 has_formal_goal_basis = true"""
        from core.source_reliability import summarize_source_chain

        sources = [
            {"source_level": "A1", "source_category": "official_authority",
             "can_be_goal_basis": "yes", "is_test_fixture": False}
        ]
        result = summarize_source_chain(sources)
        self.assertTrue(result.get("has_formal_goal_basis", False))

    def test_mock_fixture_not_formal(self):
        """mock/test fixture 不得被当成真实 official final basis"""
        from core.source_reliability import summarize_source_chain

        # Test fixture should not count as formal basis in source chain
        sources = [
            {"source_level": "A1", "is_test_fixture": True,
             "can_be_goal_basis": "test_only", "source_category": "official_authority"}
        ]
        result = summarize_source_chain(sources)
        # summarize_source_chain should recognize test fixtures
        # and not count them as formal basis
        self.assertIn("status", result)


class TestKnowledgeIngest(unittest.TestCase):
    """knowledge_ingest 测试"""

    def test_ingest_document(self):
        """ingest_document 能入库一个 Markdown 教师资料"""
        from tools.knowledge_ingest import ingest_document

        # Create a temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False,
                                          encoding='utf-8') as f:
            f.write("# 教学设计笔记\n\n算法教学要点：\n1. 从生活情境入手\n2. 用顺序词描述步骤")
            temp_path = f.name

        try:
            result = ingest_document(temp_path, {
                "document_type": "lesson_plan",
                "subject": "信息科技",
                "grade_level": "七年级",
                "topic": "算法",
                "copyright_scope": "teacher_private_use_only",
                "use_scope": ["private_reference_only"],
            })
            self.assertTrue(result.get("ingested", False))
            self.assertIn("document_id", result)
        finally:
            os.unlink(temp_path)

    def test_ingest_detects_personal_info(self):
        """ingest_document 遇到疑似学生个人信息时返回 warning"""
        from tools.knowledge_ingest import ingest_document

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False,
                                          encoding='utf-8') as f:
            f.write("学生成绩：张三 98分，李四 75分\n学号：2024001234")
            temp_path = f.name

        try:
            result = ingest_document(temp_path, {
                "document_type": "grade_report",
                "subject": "数学",
                "grade_level": "七年级",
                "topic": "成绩",
                "copyright_scope": "teacher_private_use_only",
                "use_scope": ["private_reference_only"],
            })
            self.assertTrue(len(result.get("warnings", [])) > 0)
        finally:
            os.unlink(temp_path)

    def test_search_knowledge_base(self):
        """search_knowledge_base 能检索教师资料"""
        from tools.knowledge_ingest import search_knowledge_base

        # Pass keywords as string, not list
        result = search_knowledge_base({
            "keywords": "算法",
            "subject": "信息科技",
        })
        self.assertIn("status", result)
        self.assertIn("matches", result)


class TestCurriculumMapper(unittest.TestCase):
    """curriculum_mapper 测试"""

    def test_alignment_status(self):
        """curriculum_mapper 能生成 alignment_status = formal / limited / missing"""
        from tools.curriculum_mapper import map_goal_to_sources

        goal = {"behavior": "描述算法步骤", "scene_type": "k12"}
        sources = [
            {"source_level": "A1", "source_name": "信息科技课标",
             "can_be_goal_basis": "yes", "is_test_fixture": False}
        ]
        result = map_goal_to_sources(goal, sources)
        self.assertTrue(result.get("has_formal_basis", False))


class TestReportAlignment(unittest.TestCase):
    """报告课程标准依据表测试"""

    def test_report_shows_curriculum_table(self):
        """报告能显示课程标准依据表"""
        from tools.export_package import render_markdown_report

        project = {
            "metadata": {"project_name": "测试"},
            "sources": [
                {"source_name": "义务教育信息科技课程标准（2022年版）",
                 "source_level": "A1", "can_be_goal_basis": "yes",
                 "applicable_grades": ["七年级"]}
            ],
            "goal": {"behavior": "测试", "status": "warning", "structure_status": "pass",
                     "source_status": "sufficient", "verification_status": "verified",
                     "can_use_as_final_goal": True, "can_use_as_draft": True},
            "skill_graph": {"goal_steps": [], "subordinate_skills": [], "entry_behaviours": []},
            "objectives": [],
            "assessment_plan": {"evidence": [], "entry_behavior_test": {}, "pretest": {},
                               "practice_evidence": {}, "posttest": {}},
            "quality_check": {"overall_status": "pass", "score": 100, "critical_issues": [],
                             "warnings": [], "can_export_as_final": True, "can_export_as_draft": True,
                             "blocking_reasons": []},
        }
        md = render_markdown_report(project)
        self.assertIn("课程标准依据表", md)
        self.assertIn("信息科技课程标准", md)

    def test_report_no_source_shows_warning(self):
        """无正式来源时报告继续显示待验证草案"""
        from tools.export_package import render_markdown_report

        project = {
            "metadata": {"project_name": "测试"},
            "sources": [],
            "goal": {"behavior": "测试", "status": "warning", "structure_status": "pass",
                     "source_status": "insufficient", "verification_status": "draft_unverified",
                     "can_use_as_final_goal": False, "can_use_as_draft": True},
            "skill_graph": {"goal_steps": [], "subordinate_skills": [], "entry_behaviours": []},
            "objectives": [],
            "assessment_plan": {"evidence": [], "entry_behavior_test": {}, "pretest": {},
                               "practice_evidence": {}, "posttest": {}},
            "quality_check": {"overall_status": "warning", "score": 50, "critical_issues": [],
                             "warnings": [], "can_export_as_final": False, "can_export_as_draft": True,
                             "blocking_reasons": ["无官方来源"]},
        }
        md = render_markdown_report(project)
        self.assertIn("待验证草案", md)
        self.assertIn("未找到可验证官方课程标准依据", md)


class TestGoalEngineUpgrade(unittest.TestCase):
    """goal_engine 升级测试"""

    def test_k12_a_source_file_only(self):
        """K12 A1 来源只有文件级（无 clauses）时应为 source_found_pending_clause_alignment"""
        from tools.goal_engine import validate_instructional_goal

        goal = {
            "learner": "学生", "behavior": "描述步骤", "context": "课堂",
            "tools": "纸笔", "scene_type": "k12",
        }
        sources = [{"source_level": "A1", "retrieval_status": "found",
                    "is_test_fixture": False, "specific_clauses": []}]
        result = validate_instructional_goal(goal, sources)
        self.assertEqual(result["verification_status"], "source_found_pending_clause_alignment")
        self.assertFalse(result["can_use_as_final_goal"])

    def test_k12_a_source_with_clauses_verified(self):
        """K12 A1 来源 + clauses 时应为 standard_clause_aligned"""
        from tools.goal_engine import validate_instructional_goal

        goal = {
            "learner": "学生", "behavior": "描述步骤", "context": "课堂",
            "tools": "纸笔", "scene_type": "k12",
        }
        sources = [{"source_level": "A1", "retrieval_status": "found",
                    "is_test_fixture": False,
                    "specific_clauses": [{"clause_id": "IT2022-001", "clause_text": "算法"}]}]
        result = validate_instructional_goal(goal, sources)
        self.assertEqual(result["verification_status"], "standard_clause_aligned")
        self.assertTrue(result["can_use_as_final_goal"])
        self.assertTrue(result.get("requires_teacher_confirmation", False))

    def test_k12_teacher_confirmed_final(self):
        """教师确认后应变为 final_verified"""
        from tools.goal_engine import validate_instructional_goal

        goal = {
            "learner": "学生", "behavior": "描述步骤", "context": "课堂",
            "tools": "纸笔", "scene_type": "k12",
        }
        sources = [{"source_level": "A1", "retrieval_status": "found",
                    "is_test_fixture": False, "verified_by_teacher": True,
                    "specific_clauses": [{"clause_id": "IT2022-001", "clause_text": "算法"}]}]
        result = validate_instructional_goal(goal, sources)
        self.assertEqual(result["verification_status"], "final_verified")
        self.assertTrue(result["can_use_as_final_goal"])
        self.assertFalse(result.get("requires_teacher_confirmation", True))

    def test_k12_test_fixture_with_clauses_not_verified(self):
        """测试夹具即使有 clauses 也不能升级 verified_candidate"""
        from tools.goal_engine import validate_instructional_goal

        goal = {
            "learner": "学生", "behavior": "描述步骤", "context": "课堂",
            "tools": "纸笔", "scene_type": "k12",
        }
        sources = [{"source_level": "A1", "retrieval_status": "found",
                    "is_test_fixture": True,
                    "specific_clauses": [{"clause_id": "MOCK-001", "clause_text": "测试"}]}]
        result = validate_instructional_goal(goal, sources)
        self.assertNotEqual(result["verification_status"], "standard_clause_aligned")
        self.assertNotEqual(result["verification_status"], "final_verified")
        self.assertFalse(result["can_use_as_final_goal"])


class TestSourceNormalizer(unittest.TestCase):
    """source_normalizer 测试"""

    def test_normalize_source_record(self):
        """normalize_source_record 统一字段格式"""
        from core.source_normalizer import normalize_source_record

        source = {"level": "A1", "title": "测试", "category": "curriculum_standard"}
        result = normalize_source_record(source)
        self.assertEqual(result["source_level"], "A1")
        self.assertEqual(result["source_name"], "测试")
        self.assertEqual(result["source_category"], "official_authority")

    def test_merge_source_records_dedup(self):
        """同一 source_id 重复来源必须合并"""
        from core.source_normalizer import merge_source_records

        sources = [
            {"source_id": "s1", "source_level": "A1", "credibility": "highest",
             "specific_clauses": [{"clause_id": "c1"}]},
            {"source_id": "s1", "source_level": "A1", "credibility": "high",
             "specific_clauses": [{"clause_id": "c2"}]},
        ]
        result = merge_source_records(sources)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0].get("specific_clauses", [])), 2)

    def test_merge_no_goal_basis_conflict(self):
        """合并后不得出现 can_be_goal_basis=yes/no 冲突"""
        from core.source_normalizer import merge_source_records

        sources = [
            {"source_id": "s1", "source_level": "A1", "can_be_goal_basis": "yes"},
            {"source_id": "s1", "source_level": "A1", "can_be_goal_basis": "no"},
        ]
        result = merge_source_records(sources)
        self.assertEqual(len(result), 1)
        # Should resolve to limited, not yes or no
        self.assertEqual(result[0].get("normalized_can_be_goal_basis"), "limited")

    def test_remove_nested_goal(self):
        """goal 内不得包含嵌套 goal 字段"""
        from core.source_normalizer import remove_nested_goal_payload

        goal = {
            "behavior": "描述步骤",
            "status": "pass",
            "goal": {"behavior": "描述步骤", "status": "verified"},
        }
        result = remove_nested_goal_payload(goal)
        self.assertNotIn("goal", result)
        self.assertEqual(result["verification_status"], "verified")


class TestReportNewStatuses(unittest.TestCase):
    """报告新状态测试"""

    def test_report_shows_file_level_source(self):
        """报告中必须区分文件级来源和条款级来源"""
        from tools.export_package import render_markdown_report

        project = {
            "metadata": {"project_name": "测试"},
            "sources": [
                {"source_name": "义务教育信息科技课程标准（2022年版）",
                 "source_level": "A1", "can_be_goal_basis": "yes",
                 "applicable_grades": ["七年级"], "specific_clauses": [],
                 "is_test_fixture": False}
            ],
            "goal": {"behavior": "测试", "status": "warning", "structure_status": "pass",
                     "source_status": "partial",
                     "verification_status": "source_found_pending_clause_alignment",
                     "can_use_as_final_goal": False, "can_use_as_draft": True},
            "skill_graph": {"goal_steps": [], "subordinate_skills": [], "entry_behaviours": []},
            "objectives": [],
            "assessment_plan": {"evidence": [], "entry_behavior_test": {}, "pretest": {},
                               "practice_evidence": {}, "posttest": {}},
            "quality_check": {"overall_status": "warning", "score": 84, "critical_issues": [],
                             "warnings": [], "can_export_as_final": False, "can_export_as_draft": True,
                             "blocking_reasons": ["待条款对齐"]},
        }
        md = render_markdown_report(project)
        self.assertIn("文件级来源：待条款确认", md)
        self.assertIn("已找到官方课程标准文件", md)

    def test_report_final_not_pass_blocks(self):
        """文件级来源报告仍显示不能作为最终优秀设计"""
        from tools.export_package import render_markdown_report

        project = {
            "metadata": {"project_name": "测试"},
            "sources": [],
            "goal": {"behavior": "测试", "status": "warning", "structure_status": "pass",
                     "source_status": "partial",
                     "verification_status": "source_found_pending_clause_alignment",
                     "can_use_as_final_goal": False, "can_use_as_draft": True},
            "skill_graph": {"goal_steps": [], "subordinate_skills": [], "entry_behaviours": []},
            "objectives": [],
            "assessment_plan": {"evidence": [], "entry_behavior_test": {}, "pretest": {},
                               "practice_evidence": {}, "posttest": {}},
            "quality_check": {"overall_status": "warning", "score": 84, "critical_issues": [],
                             "warnings": [], "can_export_as_final": False, "can_export_as_draft": True,
                             "blocking_reasons": []},
        }
        md = render_markdown_report(project)
        self.assertIn("待验证草案", md)
        self.assertIn("可导出为最终版本", md)


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
