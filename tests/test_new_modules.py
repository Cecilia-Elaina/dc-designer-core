"""Functional tests for standards_search.py and source_reliability.py"""
import sys
import os
import unittest

# Path setup
_MCP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mcp-server")
sys.path.insert(0, _MCP_DIR)

from tools.standards_search import (
    search_standards,
    get_standard_source,
    rank_standard_matches,
    build_source_record_from_standard,
    _fuzzy_subject_match,
    _normalize_grade,
    _grade_matches,
    _keyword_overlap,
    _level_to_credibility,
    _level_to_goal_basis,
)
from core.source_reliability import (
    classify_source_level,
    can_source_support_goal,
    validate_source_usage,
    summarize_source_chain,
)


class TestFuzzySubjectMatch(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(_fuzzy_subject_match("数学", "数学"), 1.0)

    def test_no_match(self):
        self.assertEqual(_fuzzy_subject_match("数学", "物理"), 0.0)

    def test_substring(self):
        self.assertEqual(_fuzzy_subject_match("数学", "数"), 0.8)

    def test_alias(self):
        # 政治 normalizes to 道德与法治
        self.assertEqual(
            _fuzzy_subject_match("道德与法治", "政治"),
            1.0,
        )


class TestNormalizeGrade(unittest.TestCase):
    def test_chinese_number(self):
        self.assertEqual(_normalize_grade("三年级"), ("primary", 3))

    def test_arabic(self):
        self.assertEqual(_normalize_grade("7年级"), ("junior", 7))

    def test_senior(self):
        self.assertEqual(_normalize_grade("高一"), ("senior", 1))

    def test_empty(self):
        self.assertEqual(_normalize_grade(""), ("", 0))

    def test_junior_9(self):
        self.assertEqual(_normalize_grade("九年级"), ("junior", 9))

    def test_senior_12(self):
        self.assertEqual(_normalize_grade("十二年级"), ("senior", 12))


class TestGradeMatches(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(_grade_matches("三年级", "三年级"), 1.0)

    def test_close_grade(self):
        self.assertGreater(_grade_matches("三年级", "四年级"), 0.0)

    def test_different_stage(self):
        self.assertEqual(_grade_matches("三年级", "七年级"), 0.0)

    def test_same_stage_near(self):
        self.assertGreater(_grade_matches("七年级", "八年级"), 0.0)


class TestKeywordOverlap(unittest.TestCase):
    def test_overlap(self):
        self.assertGreater(_keyword_overlap(["算法", "排序"], "算法排序"), 0.0)

    def test_empty_text(self):
        self.assertEqual(_keyword_overlap(["算法"], ""), 0.0)

    def test_empty_keywords(self):
        self.assertEqual(_keyword_overlap([], "算法"), 0.0)


class TestLevelMapping(unittest.TestCase):
    def test_credibility(self):
        self.assertEqual(_level_to_credibility("A1"), "highest")
        self.assertEqual(_level_to_credibility("B1"), "high")
        self.assertEqual(_level_to_credibility("C1"), "medium")
        self.assertEqual(_level_to_credibility("D1"), "medium_low")
        self.assertEqual(_level_to_credibility("E1"), "uncertain")

    def test_goal_basis(self):
        self.assertEqual(_level_to_goal_basis("A1"), "yes")
        self.assertEqual(_level_to_goal_basis("B5"), "limited")
        self.assertEqual(_level_to_goal_basis("C1"), "limited")
        self.assertEqual(_level_to_goal_basis("D1"), "no")
        self.assertEqual(_level_to_goal_basis("E1"), "no")


class TestBuildSourceRecord(unittest.TestCase):
    def test_a1_official(self):
        match = {
            "standard_id": "test-001",
            "source_name": "义务教育数学课程标准",
            "description": "2022年版",
            "subject": "数学",
            "grade": "三年级",
            "source_level": "A1",
            "source_category": "official_authority",
            "applicable_scenes": ["k12"],
            "is_test_fixture": False,
            "data_file": "test.json",
        }
        record = build_source_record_from_standard(match)
        self.assertEqual(record["source_id"], "test-001")
        self.assertEqual(record["source_level"], "A1")
        self.assertEqual(record["credibility"], "highest")
        self.assertEqual(record["can_be_goal_basis"], "yes")
        self.assertEqual(record["copyright_scope"], "official_public")
        self.assertFalse(record["is_test_fixture"])
        self.assertIn("goal_basis", record["use_scope"])

    def test_test_fixture(self):
        match = {
            "standard_id": "fixture-001",
            "source_name": "测试数据",
            "source_level": "A1",
            "source_category": "official_authority",
            "is_test_fixture": True,
        }
        record = build_source_record_from_standard(match)
        self.assertEqual(record["can_be_goal_basis"], "test_only")
        self.assertTrue(record["is_test_fixture"])
        self.assertTrue(len(record.get("warnings", [])) > 0)

    def test_b5_limited(self):
        record = build_source_record_from_standard({
            "standard_id": "test-b5",
            "source_name": "教育心理学著作",
            "source_level": "B5",
            "source_category": "professional_authority",
            "is_test_fixture": False,
        })
        self.assertEqual(record["can_be_goal_basis"], "limited")
        self.assertEqual(record["credibility"], "medium_high")

    def test_c1_teacher_private(self):
        record = build_source_record_from_standard({
            "standard_id": "test-c1",
            "source_name": "教师教案",
            "source_level": "C1",
            "source_category": "teacher_private",
            "is_test_fixture": False,
        })
        self.assertEqual(record["can_be_goal_basis"], "limited")
        self.assertEqual(record["copyright_scope"], "teacher_private_use_only")

    def test_d1_public(self):
        record = build_source_record_from_standard({
            "standard_id": "test-d1",
            "source_name": "教育网站",
            "source_level": "D1",
            "source_category": "public",
            "is_test_fixture": False,
        })
        self.assertEqual(record["can_be_goal_basis"], "no")
        self.assertTrue(record["fallback_required"])

    def test_no_id_generates_source_id(self):
        record = build_source_record_from_standard({
            "source_name": "test",
            "source_level": "A1",
            "source_category": "official_authority",
            "is_test_fixture": False,
        })
        self.assertTrue(record["source_id"].startswith("src_"))


class TestSearchStandards(unittest.TestCase):
    def test_with_data(self):
        """Test search_standards loads data from local files and returns results."""
        result = search_standards({
            "subject": "数学",
            "grade": "三年级",
            "topic": "分数运算",
        })
        # Should find at least the math standard from source_registry
        self.assertIn(result["status"], ("found", "partial", "not_found"))
        self.assertIn("query", result)
        self.assertIsInstance(result["matches"], list)
        self.assertIsInstance(result["next_actions"], list)
        self.assertIsInstance(result["sources"], list)

    def test_keywords_string(self):
        """Test search_standards accepts keywords as a string."""
        result = search_standards({
            "subject": "信息科技",
            "keywords": "算法",
        })
        self.assertIn(result["status"], ("found", "partial", "not_found"))
        self.assertIn("query", result)

    def test_empty_query(self):
        """Test search_standards with empty query still returns valid structure."""
        result = search_standards({})
        self.assertIn(result["status"], ("found", "partial", "not_found"))
        self.assertIn("query", result)
        self.assertIsInstance(result["matches"], list)

    def test_returns_source_records(self):
        """Test that each match has a corresponding source record."""
        result = search_standards({
            "subject": "信息科技",
            "topic": "算法",
        })
        if result["matches"]:
            self.assertTrue(len(result["sources"]) == len(result["matches"]))
            for src in result["sources"]:
                self.assertIn("source_id", src)
                self.assertIn("source_level", src)
                self.assertIn("credibility", src)
                self.assertIn("can_be_goal_basis", src)

    def test_info_tech_search(self):
        """Test searching for information technology standards."""
        result = search_standards({
            "subject": "信息科技",
            "grade": "七年级",
            "topic": "算法与程序设计",
        })
        # Should find the info tech standard
        self.assertTrue(len(result["matches"]) > 0)
        self.assertEqual(result["status"], "found")
        # Verify at least one source has A-level
        a_sources = [s for s in result["sources"] if s["source_level"].startswith("A")]
        self.assertTrue(len(a_sources) > 0, "Should have at least one A-level source")
        # Verify source records have required fields
        for src in result["sources"]:
            self.assertIn("source_id", src)
            self.assertIn("source_level", src)
            self.assertIn("credibility", src)
            self.assertIn("can_be_goal_basis", src)


class TestGetStandardSource(unittest.TestCase):
    def test_not_found(self):
        result = get_standard_source("nonexistent-id")
        self.assertEqual(result["status"], "not_found")

    def test_empty_input(self):
        result = get_standard_source("")
        self.assertEqual(result["status"], "error")

    def test_found_existing(self):
        """Test retrieving an existing standard by ID."""
        result = get_standard_source("std_compulsory_2022_math")
        self.assertEqual(result["status"], "found")
        self.assertIsNotNone(result["source"])
        self.assertEqual(result["source"]["source_id"], "std_compulsory_2022_math")


class TestRankStandardMatches(unittest.TestCase):
    def test_empty(self):
        result = rank_standard_matches([], {"subject": "数学"})
        self.assertEqual(result["ranked_matches"], [])
        self.assertIsNone(result["top_match"])

    def test_ranking_order(self):
        mock_matches = [
            {
                "standard_id": "s1",
                "source_name": "数学课程标准",
                "subject": "数学",
                "grade": "三年级",
                "keywords": ["分数", "运算"],
                "source_level": "A1",
                "source_category": "official_authority",
                "applicable_scenes": ["k12"],
                "is_test_fixture": False,
            },
            {
                "standard_id": "s2",
                "source_name": "物理课程标准",
                "subject": "物理",
                "grade": "七年级",
                "keywords": ["力学", "运动"],
                "source_level": "B1",
                "source_category": "professional_authority",
                "applicable_scenes": ["k12"],
                "is_test_fixture": False,
            },
        ]
        result = rank_standard_matches(mock_matches, {
            "subject": "数学",
            "grade": "三年级",
            "topic": "分数运算",
        })
        self.assertEqual(len(result["ranked_matches"]), 2)
        self.assertEqual(result["top_match"]["standard_id"], "s1")
        self.assertIn("scoring_breakdown", result)
        math_score = result["scoring_breakdown"]["s1"]["weighted_total"]
        physics_score = result["scoring_breakdown"]["s2"]["weighted_total"]
        self.assertGreater(math_score, physics_score)


# ===================================================================
# Source Reliability Tests
# ===================================================================

class TestClassifySourceLevel(unittest.TestCase):
    def test_explicit_a1(self):
        result = classify_source_level({
            "source_level": "A1",
            "source_name": "义务教育数学课程标准(2022)",
        })
        self.assertEqual(result["level"], "A1")
        self.assertEqual(result["credibility"], "highest")
        self.assertEqual(result["can_be_goal_basis"], "yes")

    def test_explicit_b5(self):
        result = classify_source_level({
            "source_level": "B5",
            "source_name": "教育心理学著作",
        })
        self.assertEqual(result["can_be_goal_basis"], "limited")

    def test_from_category(self):
        result = classify_source_level({
            "source_category": "official_authority",
            "source_name": "教育部文件",
        })
        self.assertTrue(result["level"].startswith("A"))

    def test_from_publisher(self):
        result = classify_source_level({
            "publisher": "人民教育出版社",
            "source_name": "数学教材",
        })
        self.assertEqual(result["level"], "A1")

    def test_provincial_publisher(self):
        result = classify_source_level({
            "publisher": "省教育厅",
            "source_name": "省课程实施意见",
        })
        self.assertEqual(result["level"], "A4")

    def test_textbook_publisher(self):
        result = classify_source_level({
            "publisher": "某出版社出版",
            "source_name": "教材",
        })
        self.assertEqual(result["level"], "B1")

    def test_wikipedia(self):
        result = classify_source_level({"publisher": "Wikipedia"})
        self.assertEqual(result["level"], "D2")

    def test_blog(self):
        result = classify_source_level({"publisher": "某公众号"})
        self.assertEqual(result["level"], "D3")

    def test_default(self):
        result = classify_source_level({"source_name": "未知来源"})
        self.assertEqual(result["level"], "D1")

    def test_letter_prefix_only(self):
        result = classify_source_level({"source_level": "C"})
        self.assertEqual(result["level"], "C1")


class TestCanSourceSupportGoal(unittest.TestCase):
    def test_k12_a1_formal(self):
        result = can_source_support_goal({"source_level": "A1"}, "k12")
        self.assertTrue(result["can_support"])
        self.assertEqual(result["support_level"], "formal")

    def test_k12_c1_limited(self):
        result = can_source_support_goal({"source_level": "C1"}, "k12")
        self.assertTrue(result["can_support"])
        self.assertEqual(result["support_level"], "limited")

    def test_k12_d1_not_allowed(self):
        result = can_source_support_goal({"source_level": "D1"}, "k12")
        self.assertFalse(result["can_support"])
        self.assertEqual(result["support_level"], "not_allowed")

    def test_k12_e1_not_allowed(self):
        result = can_source_support_goal({"source_level": "E1"}, "k12")
        self.assertFalse(result["can_support"])

    def test_corporate_c1_formal(self):
        result = can_source_support_goal({"source_level": "C1"}, "corporate")
        self.assertTrue(result["can_support"])
        self.assertEqual(result["support_level"], "formal")

    def test_corporate_b4_formal(self):
        result = can_source_support_goal({"source_level": "B4"}, "corporate")
        self.assertTrue(result["can_support"])
        self.assertEqual(result["support_level"], "formal")

    def test_higher_ed_b5_limited(self):
        result = can_source_support_goal({"source_level": "B5"}, "higher_ed")
        self.assertTrue(result["can_support"])
        self.assertEqual(result["support_level"], "limited")

    def test_vocational_b1_formal(self):
        result = can_source_support_goal({"source_level": "B1"}, "vocational")
        self.assertTrue(result["can_support"])

    def test_general_a1_formal(self):
        result = can_source_support_goal({"source_level": "A1"}, "general")
        self.assertTrue(result["can_support"])

    def test_inferred_level(self):
        result = can_source_support_goal(
            {"source_category": "official_authority", "source_name": "课标"},
            "k12",
        )
        self.assertTrue(result["can_support"])


class TestValidateSourceUsage(unittest.TestCase):
    def test_teacher_private_public_export(self):
        result = validate_source_usage(
            {
                "source_name": "教师教案",
                "copyright_scope": "teacher_private_use_only",
                "use_scope": [],
            },
            "public_export",
        )
        self.assertFalse(result["valid"])
        self.assertTrue(len(result["violations"]) > 0)

    def test_teacher_private_goal_basis(self):
        result = validate_source_usage(
            {
                "source_name": "教师教案",
                "copyright_scope": "teacher_private_use_only",
                "use_scope": [],
            },
            "goal_basis",
        )
        self.assertFalse(result["valid"])

    def test_official_public_content_reference(self):
        result = validate_source_usage(
            {
                "source_name": "课程标准",
                "copyright_scope": "official_public",
                "use_scope": ["goal_basis", "content_reference"],
            },
            "content_reference",
        )
        self.assertTrue(result["valid"])

    def test_not_for_public_export(self):
        result = validate_source_usage(
            {
                "source_name": "未知来源",
                "copyright_scope": "unknown",
                "use_scope": [],
            },
            "public_export",
        )
        self.assertFalse(result["valid"])

    def test_goal_basis_not_in_scope(self):
        result = validate_source_usage(
            {
                "source_name": "来源",
                "copyright_scope": "official_public",
                "use_scope": ["content_reference", "private_reference_only"],
            },
            "goal_basis",
        )
        self.assertFalse(result["valid"])

    def test_d_level_goal_basis(self):
        result = validate_source_usage(
            {
                "source_name": "D级来源",
                "source_level": "D1",
                "copyright_scope": "public_domain",
                "use_scope": ["content_reference"],
            },
            "goal_basis",
        )
        self.assertFalse(result["valid"])

    def test_public_domain_goal_basis(self):
        result = validate_source_usage(
            {
                "source_name": "公共领域",
                "copyright_scope": "public_domain",
                "use_scope": ["goal_basis"],
            },
            "goal_basis",
        )
        self.assertTrue(result["valid"])
        self.assertTrue(len(result["recommendations"]) > 0)


class TestSummarizeSourceChain(unittest.TestCase):
    def test_sufficient(self):
        result = summarize_source_chain([
            {"source_level": "A1", "source_name": "课标", "can_be_goal_basis": "yes"},
            {"source_level": "B1", "source_name": "教材", "can_be_goal_basis": "yes"},
        ])
        self.assertEqual(result["status"], "sufficient")
        self.assertTrue(result["has_formal_goal_basis"])
        self.assertEqual(result["highest_level"], "A1")

    def test_insufficient(self):
        result = summarize_source_chain([
            {"source_level": "D1", "source_name": "网页", "can_be_goal_basis": "no"},
        ])
        self.assertEqual(result["status"], "insufficient")
        self.assertFalse(result["has_formal_goal_basis"])
        self.assertTrue(len(result["blocked_sources"]) > 0)

    def test_empty(self):
        result = summarize_source_chain([])
        self.assertEqual(result["status"], "insufficient")
        self.assertFalse(result["has_formal_goal_basis"])

    def test_limited_only(self):
        result = summarize_source_chain([
            {"source_level": "C1", "source_name": "教师资料", "can_be_goal_basis": "limited"},
        ])
        self.assertEqual(result["status"], "partial")
        self.assertFalse(result["has_formal_goal_basis"])

    def test_test_fixture(self):
        result = summarize_source_chain([
            {"source_level": "A1", "source_name": "fixture", "is_test_fixture": True, "can_be_goal_basis": "yes"},
        ])
        self.assertTrue(len(result["limited_sources"]) > 0)
        self.assertTrue(len(result["recommendations"]) > 0)

    def test_mixed_sources(self):
        result = summarize_source_chain([
            {"source_level": "A1", "source_name": "课标", "can_be_goal_basis": "yes"},
            {"source_level": "D1", "source_name": "网页", "can_be_goal_basis": "no"},
        ])
        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["has_formal_goal_basis"])
        self.assertTrue(len(result["blocked_sources"]) > 0)


if __name__ == "__main__":
    unittest.main()
