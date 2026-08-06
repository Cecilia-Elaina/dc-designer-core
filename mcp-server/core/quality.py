"""质量门禁检查"""


def check_goal_quality(goal: dict) -> dict:
    """
    检查教学目的质量。

    Returns:
        {
            "passed": bool,
            "issues": list[str],
            "is_draft": bool
        }
    """
    issues = []
    is_draft = False

    # 1. 目的不能为空
    if not goal or not goal.get("behavior"):
        issues.append("教学目的不能为空")

    # 2. 必须包含学习者
    if not goal.get("learner"):
        issues.append("教学目的缺少学习者描述")

    # 3. 必须包含行为
    if not goal.get("behavior"):
        issues.append("教学目的缺少最终行为描述")

    # 4. 必须包含环境或条件
    if not goal.get("context") and not goal.get("condition"):
        issues.append("教学目的缺少应用环境或条件描述")

    # 5. K12 场景来源检查
    scene = goal.get("scene_type", "")
    sources = goal.get("sources", [])
    if scene in ("k12", "K12"):
        has_official = any(
            s.get("source_level", "").startswith(("A", "B"))
            for s in sources
        )
        has_teacher = any(
            s.get("retrieval_status") in ("user_uploaded", "teacher_confirmed")
            for s in sources
        )
        if not has_official and not has_teacher:
            is_draft = True
            issues.append("K12场景：无官方来源(A/B级)且无教师上传资料，教学目的只能标记为待验证草案")

    # 6. 企业培训场景检查
    if scene in ("corporate", "企业"):
        if not goal.get("performance_problem"):
            issues.append("企业培训场景：缺少绩效问题描述")

    passed = len(issues) == 0
    return {
        "passed": passed,
        "issues": issues,
        "is_draft": is_draft,
    }


def check_skill_graph_quality(skill_graph: dict) -> dict:
    """检查技能流图质量。"""
    issues = []

    if not skill_graph.get("goal_node"):
        issues.append("技能流图缺少 goal_node")
    if not skill_graph.get("goal_steps"):
        issues.append("技能流图缺少 goal_steps")
    if not skill_graph.get("subordinate_skills"):
        issues.append("技能流图缺少 subordinate_skills")
    if not skill_graph.get("entry_behaviors"):
        issues.append("技能流图缺少 entry_behaviors")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
    }


def check_objective_quality(objective: dict) -> dict:
    """检查单个绩效目标质量。"""
    issues = []

    if not objective.get("condition"):
        issues.append(f"目标 {objective.get('objective_id', '?')} 缺少条件")
    if not objective.get("behavior"):
        issues.append(f"目标 {objective.get('objective_id', '?')} 缺少行为")
    if not objective.get("criterion"):
        issues.append(f"目标 {objective.get('objective_id', '?')} 缺少标准")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
    }


def check_objectives_quality(objectives: list) -> dict:
    """检查所有绩效目标质量。"""
    all_issues = []
    for obj in objectives:
        result = check_objective_quality(obj)
        all_issues.extend(result["issues"])

    return {
        "passed": len(all_issues) == 0,
        "issues": all_issues,
    }


def check_assessment_quality(objectives: list, assessment_plan: dict) -> dict:
    """检查评价方案质量。"""
    issues = []

    # 检查每个目标是否有评价证据
    covered_ids = set()
    evidence_list = assessment_plan.get("evidence", [])
    for ev in evidence_list:
        linked = ev.get("linked_objective_id", "")
        if linked:
            covered_ids.add(linked)

    for obj in objectives:
        oid = obj.get("objective_id", "")
        if oid and oid not in covered_ids:
            issues.append(f"目标 {oid} 缺少对应评价证据")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
    }
