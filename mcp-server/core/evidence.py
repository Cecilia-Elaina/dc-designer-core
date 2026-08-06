"""评价证据生成工具"""

# 评价证据类型与学习类型的映射
EVIDENCE_BY_GOAL_TYPE = {
    "verbal_information": [
        "objective_item",       # 客观题（简答、填空、选择）
        "constructed_response", # 主观题（论述、简答）
    ],
    "intellectual_skill": [
        "constructed_response", # 情境题、问题解决
        "performance_task",     # 表现性任务
        "product",              # 作品
    ],
    "psychomotor_skill": [
        "performance_task",     # 操作表现
        "observation",          # 观察量表
        "rubric",               # 评分规准
    ],
    "attitude": [
        "attitude_scale",       # 态度量表
        "observation",          # 行为观察
        "constructed_response", # 情境选择/反思
    ],
}

EVIDENCE_TYPE_NAMES = {
    "objective_item": "客观题（选择、填空、匹配）",
    "constructed_response": "主观题（简答、论述、情境分析）",
    "performance_task": "表现性任务（操作、演示、角色扮演）",
    "product": "作品（报告、设计、项目、编程作品）",
    "observation": "观察记录（课堂观察、行为观察）",
    "rubric": "评分规准（核查表、等级量表）",
    "attitude_scale": "态度量表（兴趣问卷、自评量表）",
    "workplace_task": "工作现场任务（岗位实操、项目验收）",
}


def suggest_evidence_type(goal_type: str) -> list[str]:
    """根据目标类型推荐评价证据类型。"""
    return EVIDENCE_BY_GOAL_TYPE.get(
        goal_type, EVIDENCE_BY_GOAL_TYPE["intellectual_skill"]
    )


def generate_evidence_for_objective(objective: dict) -> dict:
    """
    为单个绩效目标生成评价证据草案。

    Args:
        objective: 绩效目标字典，需包含 objective_id, behavior, goal_type

    Returns:
        评价证据字典
    """
    from core.ids import gen_assessment_id

    goal_type = objective.get("goal_type", "intellectual_skill")
    suggested_types = suggest_evidence_type(goal_type)
    primary_type = suggested_types[0] if suggested_types else "constructed_response"

    # 根据目标类型生成具体的评价描述
    behavior = objective.get("behavior", "")
    condition = objective.get("condition", "")
    criterion = objective.get("criterion", "")

    evidence_desc = _generate_evidence_description(
        objective.get("objective_id", ""),
        behavior,
        condition,
        criterion,
        primary_type,
        goal_type,
    )

    # Generate specific task_prompt, expected_evidence, scoring_criteria
    task_prompt = _generate_task_prompt(behavior, condition, primary_type, goal_type)
    expected_evidence = _generate_expected_evidence(behavior, criterion, primary_type)
    scoring_criteria = _generate_scoring_criteria(behavior, criterion, primary_type, goal_type)

    return {
        "evidence_id": gen_assessment_id(),
        "linked_objective_id": objective.get("objective_id", ""),
        "evidence_type": primary_type,
        "evidence_type_name": EVIDENCE_TYPE_NAMES.get(primary_type, primary_type),
        "description": evidence_desc,
        "task_prompt": task_prompt,
        "expected_evidence": expected_evidence,
        "scoring_criteria": scoring_criteria,
        "suggested_types": suggested_types,
        "goal_type": goal_type,
        "status": "candidate",
    }


def _generate_task_prompt(
    behavior: str, condition: str, evidence_type: str, goal_type: str
) -> str:
    """生成具体的评价任务提示。"""
    if evidence_type == "performance_task":
        return f"给定情境：{condition}，要求学习者完成以下任务：{behavior}"
    elif evidence_type == "constructed_response":
        return f"阅读材料后，{behavior}。条件：{condition}"
    elif evidence_type == "product":
        return f"根据要求，提交一份作品，体现以下能力：{behavior}"
    elif evidence_type == "observation":
        return f"观察学习者在以下情境中的行为表现：{behavior}"
    elif evidence_type == "rubric":
        return f"使用评分规准评价学习者的表现：{behavior}"
    else:
        return f"完成以下任务：{behavior}（条件：{condition}）"


def _generate_expected_evidence(
    behavior: str, criterion: str, evidence_type: str
) -> str:
    """生成预期证据描述。"""
    return f"学习者能{behavior}，达到标准：{criterion}"


def _generate_scoring_criteria(
    behavior: str, criterion: str, evidence_type: str, goal_type: str
) -> list:
    """生成评分标准。"""
    if goal_type == "verbal_information":
        return [
            {"criterion": "正确性", "description": "信息表述正确", "max_score": 2},
            {"criterion": "完整性", "description": "覆盖所有要点", "max_score": 2},
        ]
    elif goal_type == "psychomotor_skill":
        return [
            {"criterion": "操作规范", "description": "按步骤规范操作", "max_score": 2},
            {"criterion": "结果达标", "description": "完成任务且结果正确", "max_score": 2},
        ]
    elif goal_type == "attitude":
        return [
            {"criterion": "选择合理性", "description": "在情境中做出合理选择", "max_score": 2},
            {"criterion": "一致性", "description": "行为与态度一致", "max_score": 2},
        ]
    else:
        return [
            {"criterion": "任务完成度", "description": "完成规定任务", "max_score": 2},
            {"criterion": "正确性", "description": "结果正确、步骤合理", "max_score": 2},
        ]


def _generate_evidence_description(
    obj_id: str,
    behavior: str,
    condition: str,
    criterion: str,
    evidence_type: str,
    goal_type: str,
) -> str:
    """根据目标和证据类型生成评价描述。"""
    if evidence_type == "objective_item":
        return f"针对目标 {obj_id}，设计客观题（选择/填空/匹配），测量：{behavior}"
    elif evidence_type == "constructed_response":
        return f"针对目标 {obj_id}，设计情境题或问题解决任务，条件：{condition}，行为：{behavior}，标准：{criterion}"
    elif evidence_type == "performance_task":
        return f"针对目标 {obj_id}，设计表现性任务，要求学习者在模拟情境中完成：{behavior}，标准：{criterion}"
    elif evidence_type == "product":
        return f"针对目标 {obj_id}，要求学习者提交作品（报告/设计/代码），评价标准：{criterion}"
    elif evidence_type == "observation":
        return f"针对目标 {obj_id}，使用观察量表记录学习者行为表现，观察点：{behavior}"
    elif evidence_type == "rubric":
        return f"针对目标 {obj_id}，开发评分规准（核查表/等级量表），评价维度：{behavior}，等级标准：{criterion}"
    elif evidence_type == "attitude_scale":
        return f"针对目标 {obj_id}，设计态度量表或情境选择题，测量学习者的倾向性选择"
    else:
        return f"针对目标 {obj_id}，设计评价证据，行为：{behavior}"
