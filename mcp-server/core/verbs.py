"""行为动词可观测性检查"""

# 不可观测动词（禁止使用或需替换）
UNOBSERVABLE_VERBS = {
    "知道", "了解", "理解", "掌握", "熟悉", "认识", "体会", "感受",
    "领会", "鉴赏", "欣赏", "内化", "领悟",
}

# 推荐替换映射
VERB_SUGGESTIONS = {
    "知道": ["说出", "列举", "写出", "指出", "识别"],
    "了解": ["描述", "复述", "列举", "指出", "说明"],
    "理解": ["解释", "阐述", "区分", "举例说明", "比较"],
    "掌握": ["运用", "操作", "完成", "解决", "设计"],
    "熟悉": ["描述", "列举", "区分", "识别"],
    "认识": ["识别", "区分", "指出", "命名"],
    "体会": ["描述", "举例说明", "在情境中表现"],
    "感受": ["描述", "表达", "在情境中选择"],
    "领会": ["解释", "举例说明", "在新情境中运用"],
    "鉴赏": ["评价", "比较", "判断", "分析"],
    "欣赏": ["评价", "描述", "表达偏好"],
    "内化": ["在新情境中运用", "自主应用"],
    "领悟": ["解释", "在新情境中运用"],
}

# 可观测动词（按学习类型分组）
OBSERVABLE_VERBS = {
    "verbal_information": [
        "说出", "列举", "写出", "描述", "复述", "指出", "命名",
        "背诵", "陈述", "报告", "说明", "转述",
    ],
    "intellectual_skill": [
        "识别", "区分", "分类", "比较", "解释", "举例说明",
        "演示", "计算", "设计", "生成", "解决", "分析",
        "评价", "修改", "预测", "推断", "论证", "建构",
    ],
    "psychomotor_skill": [
        "操作", "执行", "完成", "演示", "安装", "拆卸",
        "绘制", "编写", "搭建", "修复", "测量", "搬运",
    ],
    "attitude": [
        "选择", "倾向于", "主动", "在情境中表现",
        "在...情况下选择", "表现出",
    ],
}


def check_observable_verb(behavior: str) -> dict:
    """
    检查行为描述中的动词是否可观测。

    Args:
        behavior: 行为描述字符串

    Returns:
        {
            "is_observable": bool,
            "found_verbs": list[str],
            "unobservable_verbs": list[str],
            "suggestions": dict[str, list[str]],
            "recommendation": str
        }
    """
    found_unobservable = []
    found_suggestions = {}

    for verb in UNOBSERVABLE_VERBS:
        if verb in behavior:
            found_unobservable.append(verb)
            if verb in VERB_SUGGESTIONS:
                found_suggestions[verb] = VERB_SUGGESTIONS[verb]

    is_observable = len(found_unobservable) == 0

    if is_observable:
        recommendation = "行为动词可观测，无需修改"
    else:
        parts = []
        for v, s in found_suggestions.items():
            parts.append(f'"{v}" → 可替换为: {", ".join(s[:3])}')
        recommendation = f"发现不可观测动词: {'; '.join(parts)}"

    return {
        "is_observable": is_observable,
        "found_verbs": found_unobservable,
        "unobservable_verbs": found_unobservable,
        "suggestions": found_suggestions,
        "recommendation": recommendation,
    }


def suggest_observable_behavior(weak_behavior: str, goal_type: str) -> dict:
    """
    根据学习结果类型推荐可观测行为表达。

    Args:
        weak_behavior: 含糊的行为描述
        goal_type: 学习结果类型

    Returns:
        {
            "original": str,
            "goal_type": str,
            "suggested_verbs": list[str],
            "suggested_behaviors": list[str]
        }
    """
    verbs = OBSERVABLE_VERBS.get(goal_type, OBSERVABLE_VERBS["intellectual_skill"])

    # 提取行为描述中的核心内容（去掉动词部分）
    core = weak_behavior
    for v in UNOBSERVABLE_VERBS:
        core = core.replace(v, "").strip()

    suggestions = []
    for v in verbs[:5]:
        if core:
            suggestions.append(f"{v}{core}")
        else:
            suggestions.append(v)

    return {
        "original": weak_behavior,
        "goal_type": goal_type,
        "suggested_verbs": verbs[:8],
        "suggested_behaviors": suggestions,
    }
