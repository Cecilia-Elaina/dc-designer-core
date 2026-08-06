"""
Material alignment checks for dc-designer-core.
Verifies that materials support objectives, strategy, assessment, and context.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def check_material_objective_alignment(materials: dict, objectives: list) -> dict:
    """
    Check that each key objective has material support.
    Returns: {aligned, missing_objectives, coverage_rate, recommendations}
    """
    if not objectives:
        return {
            "aligned": False,
            "missing_objectives": [],
            "coverage_rate": 0.0,
            "recommendations": ["未提供教学目标，无法对齐检查"]
        }

    # Build a set of all objective keywords present in material content
    objective_keywords_map = {}
    all_material_text = _collect_all_material_text(materials)

    for obj in objectives:
        # Use the objective text itself as search anchor
        obj_text = obj if isinstance(obj, str) else str(obj)
        objective_keywords_map[obj_text] = False

    # Check if each objective is addressed in any material
    for obj_text in objective_keywords_map:
        keywords = _extract_keywords(obj_text)
        for keyword in keywords:
            if keyword in all_material_text:
                objective_keywords_map[obj_text] = True
                break

    missing = [obj for obj, covered in objective_keywords_map.items() if not covered]
    covered_count = sum(1 for v in objective_keywords_map.values() if v)
    total = len(objectives)
    coverage_rate = round(covered_count / total, 2) if total > 0 else 0.0

    recommendations = []
    if missing:
        for obj_text in missing:
            recommendations.append(f"目标 \"{obj_text}\" 在材料中未找到对应内容，请补充支持该目标的教学活动或材料")

    return {
        "aligned": coverage_rate >= 0.8,
        "missing_objectives": missing,
        "coverage_rate": coverage_rate,
        "recommendations": recommendations
    }


def check_material_strategy_alignment(materials: dict, instructional_strategy: dict) -> dict:
    """
    Check that materials support key strategy segments.
    Returns: {aligned, unsupported_segments, recommendations}
    """
    if not instructional_strategy:
        return {
            "aligned": False,
            "unsupported_segments": [],
            "recommendations": ["未提供教学策略，无法对齐检查"]
        }

    lesson_flow = instructional_strategy.get("lesson_flow", [])
    if not lesson_flow:
        return {
            "aligned": False,
            "unsupported_segments": [],
            "recommendations": ["教学策略中未包含 lesson_flow"]
        }

    all_material_text = _collect_all_material_text(materials)
    unsupported = []

    for segment in lesson_flow:
        if isinstance(segment, str):
            segment_name = segment
            segment_keywords = _extract_keywords(segment_name)
        elif isinstance(segment, dict):
            segment_name = segment.get("name", segment.get("环节", str(segment)))
            segment_keywords = _extract_keywords(segment_name)
            # Also check segment objectives/activities if present
            for key in ("activities", "activities_cn", "objectives"):
                for item in segment.get(key, []):
                    segment_keywords.extend(_extract_keywords(str(item)))
        else:
            segment_name = str(segment)
            segment_keywords = _extract_keywords(segment_name)

        found = False
        for kw in segment_keywords:
            if len(kw) >= 2 and kw in all_material_text:
                found = True
                break

        if not found:
            unsupported.append(segment_name)

    recommendations = []
    if unsupported:
        for seg in unsupported:
            recommendations.append(f"教学环节 \"{seg}\" 在材料中缺少对应支持，请补充相关材料")

    return {
        "aligned": len(unsupported) == 0,
        "unsupported_segments": unsupported,
        "recommendations": recommendations
    }


def check_material_assessment_alignment(materials: dict, assessment_plan: dict) -> dict:
    """
    Check that materials cover all 4 assessment types.
    Returns: {aligned, missing_assessment_materials, recommendations}
    """
    required_assessment_types = [
        ("entry_test", "入口测验", "entry_test_sheet"),
        ("pretest", "前测", "pretest_sheet"),
        ("mid_check", "中段检查", "group_task_sheet"),
        ("posttest", "后测", "posttest_sheet"),
    ]

    missing = []
    for type_key, type_name, material_key in required_assessment_types:
        # Check if the assessment type exists in the plan
        type_exists = False
        if assessment_plan:
            if type_key in assessment_plan:
                type_exists = True
            # Also check alternative key names
            for alt_key in (type_name, type_key.replace("_test", "_assessment")):
                if alt_key in assessment_plan:
                    type_exists = True
                    break

        # Check if the corresponding material exists and is non-empty
        material_exists = False
        if material_key in materials:
            mat = materials[material_key]
            if isinstance(mat, dict) and mat:
                material_exists = True
            elif isinstance(mat, str) and mat.strip():
                material_exists = True
            elif isinstance(mat, list) and mat:
                material_exists = True

        if not material_exists:
            missing.append({
                "assessment_type": type_name,
                "expected_material": material_key,
                "issue": "缺少对应的评估材料"
            })

    # Also check for peer review material
    peer_review_found = "peer_review_checklist" in materials and materials["peer_review_checklist"]
    if not peer_review_found:
        missing.append({
            "assessment_type": "互评",
            "expected_material": "peer_review_checklist",
            "issue": "缺少互评检查清单"
        })

    recommendations = []
    if missing:
        for item in missing:
            recommendations.append(
                f"评估类型 \"{item['assessment_type']}\" 缺少材料 \"{item['expected_material']}\"，请补充"
            )

    return {
        "aligned": len(missing) == 0,
        "missing_assessment_materials": missing,
        "recommendations": recommendations
    }


def check_material_context_fit(materials: dict, context_analysis: dict) -> dict:
    """
    Check materials fit class size, devices, network, preferences, difficulties.
    Returns: {fits, context_fit_warnings, recommendations}
    """
    warnings = []
    recommendations = []

    if not context_analysis:
        return {
            "fits": True,
            "context_fit_warnings": [],
            "recommendations": ["未提供环境分析数据，跳过环境适配检查"]
        }

    # Check device availability
    device_info = context_analysis.get("devices", context_analysis.get("设备情况", ""))
    if isinstance(device_info, str):
        device_lower = device_info.lower()
        no_devices = any(term in device_lower for term in ["没有设备", "无设备", "设备不足", "no device"])
    else:
        no_devices = False

    # Check network stability
    network_info = context_analysis.get("network", context_analysis.get("网络情况", ""))
    if isinstance(network_info, str):
        network_lower = network_info.lower()
        unstable_network = any(term in network_lower for term in ["不稳定", "不稳定", "断网", "limited", "unstable"])
    else:
        unstable_network = False

    # Check class size
    class_size = context_analysis.get("class_size", context_analysis.get("班级人数", 0))
    if isinstance(class_size, str):
        try:
            class_size = int(class_size)
        except ValueError:
            class_size = 0

    large_class = isinstance(class_size, int) and class_size > 45

    # Check time constraints
    time_info = context_analysis.get("time_constraints", context_analysis.get("时间限制", ""))
    if isinstance(time_info, str):
        limited_time = any(term in time_info for term in ["时间紧", "课时短", "不够时间", "limited"])
    else:
        limited_time = False

    all_material_text = _collect_all_material_text(materials)

    # Device-related checks
    if no_devices:
        online_terms = ["在线", "网络", "电脑", "平板", "手机", "online", "digital", "电子"]
        for term in online_terms:
            if term in all_material_text:
                warnings.append(f"环境无设备但材料中包含与设备相关的内容（\"{term}\"）")
                recommendations.append(f"请将与设备相关的内容替换为纸质学习单或板书形式")
                break

    # Network-related checks
    if unstable_network:
        online_resource_terms = ["网址", "链接", "网站", "在线资源", "网络资源", "URL", "http"]
        for term in online_resource_terms:
            if term in all_material_text:
                warnings.append(f"网络不稳定但材料中包含在线资源引用（\"{term}\"）")
                recommendations.append("请将在线资源替换为本地可用的纸质或离线材料")
                break

    # Time-related checks
    if limited_time:
        extended_terms = ["拓展活动", "探究活动", "研究性学习", "项目式", "extended", "深入探究"]
        for term in extended_terms:
            if term in all_material_text:
                warnings.append(f"课时有限但材料中包含耗时活动（\"{term}\"）")
                recommendations.append("建议精简或删减耗时活动，聚焦核心教学环节")
                break

    # Class size checks
    if large_class:
        group_terms = ["小组讨论", "分组", "小组合作", "角色扮演"]
        group_mentioned = any(term in all_material_text for term in group_terms)
        if group_mentioned:
            warnings.append(f"班级人数较多（{class_size}人），小组活动组织可能有困难")
            recommendations.append("建议控制小组规模为4-5人，安排明确的小组长和分工")

    # Student difficulty checks
    difficulties = context_analysis.get("difficulties", context_analysis.get("学情困难", []))
    if isinstance(difficulties, list):
        for diff in difficulties:
            diff_text = str(diff)
            if "抽象" in diff_text or "概念" in diff_text:
                if "具体例子" not in all_material_text and "实例" not in all_material_text:
                    warnings.append("学生存在抽象概念理解困难，但材料中缺少具体例子")
                    recommendations.append("请在材料中增加贴近生活的具体实例帮助理解")

    return {
        "fits": len(warnings) == 0,
        "context_fit_warnings": warnings,
        "recommendations": recommendations
    }


def check_full_material_alignment(project: dict) -> dict:
    """
    Aggregate all material alignment checks.
    Returns: {overall_status, coverage_rate, missing_objectives,
              unsupported_strategy_segments, missing_assessment_materials,
              context_fit_warnings, recommendations}
    """
    materials = project.get("instructional_materials", {})
    objectives = project.get("objectives", project.get("learning_objectives", []))
    strategy = project.get("instructional_strategy", {})
    assessment = project.get("assessment_plan", {})
    context = project.get("context_analysis", {})

    obj_result = check_material_objective_alignment(materials, objectives)
    strat_result = check_material_strategy_alignment(materials, strategy)
    assess_result = check_material_assessment_alignment(materials, assessment)
    context_result = check_material_context_fit(materials, context)

    all_recommendations = (
        obj_result.get("recommendations", [])
        + strat_result.get("recommendations", [])
        + assess_result.get("recommendations", [])
        + context_result.get("recommendations", [])
    )

    # Determine overall status
    checks = [
        obj_result.get("aligned", False),
        strat_result.get("aligned", False),
        assess_result.get("aligned", False),
        context_result.get("fits", False),
    ]

    passed = sum(checks)
    if passed == 4:
        overall_status = "fully_aligned"
    elif passed >= 2:
        overall_status = "partially_aligned"
    else:
        overall_status = "misaligned"

    return {
        "overall_status": overall_status,
        "coverage_rate": obj_result.get("coverage_rate", 0.0),
        "missing_objectives": obj_result.get("missing_objectives", []),
        "unsupported_strategy_segments": strat_result.get("unsupported_segments", []),
        "missing_assessment_materials": assess_result.get("missing_assessment_materials", []),
        "context_fit_warnings": context_result.get("context_fit_warnings", []),
        "recommendations": all_recommendations
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _collect_all_material_text(materials: dict) -> str:
    """Recursively collect all text content from a materials dict into one string."""
    parts = []
    _recursive_text_collect(materials, parts)
    return "\n".join(parts)


def _recursive_text_collect(obj, parts: list):
    """Recursively extract string values from nested dicts/lists."""
    if isinstance(obj, dict):
        for value in obj.values():
            _recursive_text_collect(value, parts)
    elif isinstance(obj, list):
        for item in obj:
            _recursive_text_collect(item, parts)
    elif isinstance(obj, str):
        parts.append(obj)
    elif isinstance(obj, (int, float)):
        parts.append(str(obj))


def _extract_keywords(text: str) -> list:
    """
    Extract meaningful keywords from Chinese/English text.
    Splits on common delimiters and filters short tokens.
    """
    import re
    # Split on punctuation, whitespace, and common separators
    tokens = re.split(r'[\s,.。，；、！？《》()（）\[\]【】]+', text)
    keywords = []
    for token in tokens:
        token = token.strip()
        if len(token) >= 2:
            keywords.append(token)
            # Also add substrings for Chinese text (2-char n-grams)
            if len(token) > 4:
                for i in range(len(token) - 1):
                    bigram = token[i:i+2]
                    if len(bigram) == 2:
                        keywords.append(bigram)
    return keywords
