"""Markdown 报告渲染器"""
import json
from datetime import datetime


_LEARNING_TYPE_LABELS = {
    "verbal_information": "言语信息",
    "intellectual_skill": "智慧技能",
    "psychomotor_skill": "心智运动技能",
    "cognitive_strategy": "认知策略",
    "attitude": "态度",
    "mixed": "混合类型",
}
_STATUS_LABELS = {
    "candidate": "候选（待教师确认）",
    "clause_candidate": "条款候选（待教师核对）",
    "teacher_confirmed": "教师已确认",
    "final_verified": "最终已验证",
    "verified": "已验证",
    "pass": "通过",
    "warning": "存在警告",
    "sufficient": "基本具备",
    "insufficient": "尚需补充",
    "unknown_candidate": "尚未分类",
}
_VALUE_LABELS = {
    "A1": "国家级正式依据",
    "B1": "地方教育依据",
    "C1": "教师私有资料",
    "D1": "AI推断或建议",
    "official_authority": "官方依据",
    "teacher_private": "教师私有资料",
    "OFFICIAL_STANDARD": "官方课程标准",
    "TEACHER_INPUT": "教师提供",
    "AI_INFERENCE": "AI推断（待教师验证）",
    "AI_SUGGESTION": "AI建议（待教师确认）",
    "authentic_programming_task": "真实编程任务",
    "highest": "最高可信度",
    "high": "较高可信度",
    "limited": "有限支持",
    "yes": "可以作为目标依据",
    "no": "不能直接作为目标依据",
    "current": "现行记录",
    "metadata_snapshot_only": "内置元数据快照（未下载全文）",
    "retrieved": "已获取并记录文件校验值",
}


def _label(value: object, default: str = "未提供") -> str:
    if value is None or value == "":
        return default
    if isinstance(value, dict):
        for key in ("description", "summary", "text", "value", "name"):
            if value.get(key):
                return _label(value[key], default)
        return default
    if isinstance(value, list):
        return "；".join(_label(item, "") for item in value if item) or default
    text = str(value)
    return _STATUS_LABELS.get(text, _VALUE_LABELS.get(text, text))


def _teacher_text(value: object, default: str = "未提供") -> str:
    """Render nested model values as readable teacher-facing text."""
    if value is None or value == "":
        return default
    if isinstance(value, dict):
        for key in ("description", "summary", "text", "value", "name", "difficulty", "details", "grouping", "implication", "activity"):
            if value.get(key):
                return _teacher_text(value[key], default)
        return default
    if isinstance(value, list):
        rendered = [_teacher_text(item, "") for item in value]
        return "；".join(item for item in rendered if item) or default
    return _label(value, default)


def _learning_type(value: object) -> str:
    text = str(value or "")
    return _LEARNING_TYPE_LABELS.get(text, _label(value, "尚未分类"))


def render_markdown_report(project: dict) -> str:
    """
    将项目数据渲染为 Markdown 完整报告。
    """
    sections = []

    # 报告头部警告
    quality = project.get("quality_check", {})
    can_final = quality.get("can_export_as_final", False)
    if not can_final:
        sections.append(
            '> ⚠️ 当前报告为"待验证草案"，不能作为最终优秀教学系统设计使用。\n'
        )

    # 1. 项目摘要
    sections.append(_render_section_1_summary(project))

    # 2. 用户类型与教学场景
    sections.append(_render_section_2_context(project))

    # 3. 来源依据与可靠性说明
    sections.append(_render_section_3_sources(project))

    # 4. 需求评估与教学目的
    sections.append(_render_section_4_goal(project))

    # 5. 教学目的类型判断
    sections.append(_render_section_5_goal_type(project))

    # 6. 教学分析与技能流图数据
    sections.append(_render_section_6_skill_graph(project))

    # 7. 入门技能
    sections.append(_render_section_7_entry_behaviors(project))

    # 8. 学习者与环境分析
    sections.append(_render_section_learner_context(project))

    # 9. 教学策略
    sections.append(_render_section_instructional_strategy(project))

    # 10. 绩效目标表
    sections.append(_render_section_10_objectives(project))

    # 11. 评价方案表
    sections.append(_render_section_11_assessment(project))

    # 12. 一致性检查报告
    sections.append(_render_section_12_alignment(project))

    # 14. 教学材料包
    materials_section = _render_section_materials(project)
    if materials_section:
        sections.append(materials_section)

    # 13. 教师确认事项
    sections.append(_render_section_13_confirmation(project))

    return "\n\n".join(sections)


def render_source_trace(sources: list) -> str:
    """渲染来源追溯表。"""
    if not sources:
        return "暂无来源记录。\n"

    lines = ["| 来源名称 | 发布信息 | 等级 | 来源类别/状态 | 作为目标依据 | 条款位置与摘要 |"]
    lines.append("|---------|---------|------|--------------|------------|----------------|")
    for s in sources:
        name = s.get("source_name", s.get("title", "未知"))
        level = _label(s.get("source_level"), "等级待确认")
        cred = _label(s.get("credibility"), "可信度待确认")
        status = _label(s.get("evidence_status", s.get("retrieval_status", "?")), "待确认")
        basis = _label(s.get("can_be_goal_basis", "?"), "待确认")
        category = _label(s.get("source_category", ""), "待分类")
        info = (
            f"{_label(s.get('issuer'), '发布机构待核对')}；"
            f"版本：{s.get('source_version', s.get('version', '版本待核对'))}；"
            f"发布日期：{s.get('publication_date', '日期待核对')}；"
            f"生效日期：{s.get('effective_date', '待核对')}"
        )
        clauses = s.get("specific_clauses", s.get("clauses", [])) or []
        citation_parts = []
        for clause in clauses[:3]:
            section = " / ".join(str(item) for item in clause.get("section_path", []) if item) or "章节待补充"
            location = clause.get("page_number") or clause.get("anchor") or "位置待补充"
            excerpt = clause.get("excerpt") or clause.get("clause_text", "")
            summary = clause.get("normalized_summary") or clause.get("clause_text", "")
            citation_parts.append(f"{section}；{location}；引文：{excerpt}；摘要：{summary}")
        citation = "；".join(citation_parts) or "尚未定位具体条款"
        lines.append(f"| {name} | {info} | {level}（{cred}） | {category}；{status} | {basis} | {citation} |")
    return "\n".join(lines)


def render_quality_summary(alignment_report: dict) -> str:
    """渲染质量总结。"""
    status = alignment_report.get("overall_status", "unknown")
    score = alignment_report.get("score", 0)
    critical = alignment_report.get("critical_issues", [])
    warnings = alignment_report.get("warnings", [])
    can_final = alignment_report.get("can_export_as_final", False)
    can_draft = alignment_report.get("can_export_as_draft", True)
    blocking = alignment_report.get("blocking_reasons", [])

    lines = [
        f"**总体状态：** {status}",
        f"**质量分数：** {score}/100",
        f"**可导出为最终版本：** {'是' if can_final else '否'}",
        f"**可导出为待验证草案：** {'是' if can_draft else '否'}",
    ]

    if blocking:
        lines.append("\n**阻断最终导出的原因：**")
        for i, reason in enumerate(blocking, 1):
            lines.append(f"- {reason}")

    if critical:
        lines.append("\n**严重问题：**")
        for i, issue in enumerate(critical, 1):
            lines.append(f"{i}. {issue}")

    if warnings:
        lines.append("\n**警告：**")
        for i, w in enumerate(warnings, 1):
            lines.append(f"{i}. {w}")

    return "\n".join(lines)


def _render_section_1_summary(project: dict) -> str:
    meta = project.get("metadata", {})
    return f"""# 教学系统设计报告

> 基于 Dick & Carey 教学系统化设计模型

## 1. 项目摘要

| 项目 | 内容 |
|------|------|
| 项目名称 | {meta.get('project_name', '未命名')} |
| 用户类型 | {meta.get('user_type', '未指定')} |
| 教学场景 | {meta.get('scene_type', '未指定')} |
| 学科/领域 | {meta.get('subject', '未指定')} |
| 年级/层次 | {meta.get('grade_level', '未指定')} |
| 课时安排 | {meta.get('session_info', '未指定')} |
| 设计日期 | {project.get('created_at', datetime.now().isoformat())} |"""


def _render_section_2_context(project: dict) -> str:
    meta = project.get("metadata", {})
    return f"""## 2. 用户类型与教学场景

- **用户类型：** {meta.get('user_type', '未指定')}
- **教学场景：** {meta.get('scene_type', '未指定')}
- **学科：** {meta.get('subject', '未指定')}
- **年级：** {meta.get('grade_level', '未指定')}
- **教材版本：** {meta.get('textbook', '未指定')}"""


def _render_section_3_sources(project: dict) -> str:
    sources = project.get("sources", [])
    table = render_source_trace(sources)

    # 3.1 课程标准依据表
    curriculum_section = _render_curriculum_alignment(project)

    return f"""## 3. 来源依据与可靠性说明

{table}

{curriculum_section}"""


def _render_curriculum_alignment(project: dict) -> str:
    """渲染课程标准/教材/考试要求对齐表。"""
    sources = project.get("sources", [])

    # Separate sources by type
    curriculum_sources = []
    material_sources = []
    exam_sources = []

    for s in sources:
        name = s.get("source_name", s.get("title", ""))
        level = s.get("source_level", "")
        category = s.get("source_category", "")

        if any(kw in name for kw in ["课程标准", "课程方案", "课标"]):
            curriculum_sources.append(s)
        elif any(kw in name for kw in ["教材", "教参", "教学参考"]):
            material_sources.append(s)
        elif any(kw in name for kw in ["考试", "中考", "高考", "真题"]):
            exam_sources.append(s)

    lines = ["### 3.1 课程标准依据表"]

    if curriculum_sources:
        lines.append("\n| 来源名称 | 等级 | 匹配层级 | 适用学段 | 可作为目标依据 |")
        lines.append("|---------|------|---------|---------|--------------|")
        for s in curriculum_sources:
            can_basis = s.get("can_be_goal_basis", "?")
            clauses = s.get("specific_clauses", [])
            has_clauses = len(clauses) > 0
            is_test = s.get("is_test_fixture", False)

            # Determine match level
            if is_test:
                match_level = "🧪 测试"
                basis_label = "🧪 仅测试"
            elif has_clauses:
                match_level = "条款级"
                clause_ids = [c.get("clause_id", "") for c in clauses[:2]]
                basis_label = "✅ 可以" if can_basis in ("yes",) else "⚠️ 有限"
            else:
                match_level = "文件级"
                basis_label = "📋 文件级来源：待条款确认"

            grades = ', '.join(s.get('applicable_grades', s.get('grade_levels', s.get('applicable_scenes', ['待确认']))))
            lines.append(
                f"| {s.get('source_name', s.get('title', '?'))} "
                f"| {_label(s.get('source_level'), '待确认')} "
                f"| {match_level} "
                f"| {grades} "
                f"| {basis_label} |"
            )

        # Show clause details if any
        all_clauses = []
        for s in curriculum_sources:
            for c in s.get("specific_clauses", []):
                all_clauses.append(c)
        if all_clauses:
            lines.append("\n**已定位的课标条款：**")
            for c in all_clauses[:5]:
                lines.append(f"- {c.get('clause_id', '?')}: {c.get('clause_text', '?')[:60]}...")
    else:
        lines.append("\n⚠️ 未找到可验证官方课程标准依据。")
        lines.append("请教师上传课程标准、教材章节、教学进度表或教研组资料。")

    if material_sources:
        lines.append("\n### 3.2 教师资料依据表\n")
        lines.append("| 资料名称 | 等级 | 版权范围 | 使用范围 |")
        lines.append("|---------|------|---------|---------|")
        for s in material_sources:
            copyright = s.get("copyright_scope", "?")
            use = ", ".join(s.get("use_scope", []))
            lines.append(
                f"| {s.get('source_name', '?')} "
                f"| {s.get('source_level', '?')} "
                f"| {copyright} "
                f"| {use} |"
            )

    return "\n".join(lines)


def _render_section_4_goal(project: dict) -> str:
    goal = project.get("goal", {})
    if not goal:
        return "## 4. 教学目的\n\n⚠️ 教学目的尚未确定。"

    # 三段式状态显示
    structure_status = goal.get("structure_status", "unknown")
    source_status = goal.get("source_status", "unknown")
    verification_status = goal.get("verification_status", "unknown")

    structure_label = {"pass": "✅ 通过", "fail": "❌ 未通过"}.get(structure_status, _label(structure_status, "未评估"))
    source_label = {
        "sufficient": "✅ 充分",
        "partial": "⚠️ 部分（仅有教师资料）",
        "insufficient": "❌ 不足",
        "unknown": "❓ 未评估",
    }.get(source_status, _label(source_status, "未评估"))
    verification_label = {
        "verified": "✅ 已验证",
        "final_verified": "✅ 最终确认",
        "standard_clause_aligned": "✅ 条款级对齐（待教师确认）",
        "source_found_pending_clause_alignment": "⚠️ 已找到文件，待条款对齐",
        "draft_pending_verification": "⚠️ 待验证草案（仅有教师资料）",
        "draft_unverified": "❌ 未验证草案",
        "unverified": "❓ 未评估",
    }.get(verification_status, _label(verification_status, "未评估"))

    can_final = goal.get("can_use_as_final_goal", False)

    # Additional note for file-level sources
    extra_note = ""
    if verification_status == "source_found_pending_clause_alignment":
        extra_note = (
            "\n\n> 已找到官方课程标准文件，但尚未定位到具体条款或内容要求。"
            "当前报告仍不能作为最终优秀教学系统设计使用。"
            "请上传/确认对应课标条款、教材章节或教研组资料。"
        )

    return f"""## 4. 需求评估与教学目的

**结构完整性：** {structure_label}
**来源充分性：** {source_label}
**当前状态：** {verification_label}
**可用作最终目标：** {"是" if can_final else "否（仅可作为草案使用）"}
{extra_note}

**教学目的陈述：**

> {goal.get('full_statement', '未生成')}

| 要素 | 内容 |
|------|------|
| 学习者 | {goal.get('learner', '未指定')} |
| 最终行为 | {goal.get('behavior', '未指定')} |
| 应用环境 | {goal.get('context', '未指定')} |
| 工具/条件 | {goal.get('tools', '未指定')} |

**来源依据：**
{render_source_trace(goal.get('sources', []))}

**可行性检查：**
{json.dumps(goal.get('feasibility', {}), ensure_ascii=False, indent=2) if goal.get('feasibility') else '未执行'}"""


def _render_section_5_goal_type(project: dict) -> str:
    skill_graph = project.get("skill_graph", {})
    goal_type = skill_graph.get("goal_type", "未分类")
    type_names = {
        "verbal_information": "言语信息",
        "intellectual_skill": "智慧技能",
        "psychomotor_skill": "心智运动技能",
        "attitude": "态度",
        "mixed": "混合类型",
    }
    return f"""## 5. 教学目的类型判断

**分类结果：** {type_names.get(goal_type, _learning_type(goal_type))}

**判断依据：** {skill_graph.get('classification_rationale', '基于教学目的行为动词和内容分析')}"""


def _render_section_6_skill_graph(project: dict) -> str:
    sg = project.get("skill_graph", {})
    steps = sg.get("goal_steps", [])
    subskills = sg.get("subordinate_skills", [])

    lines = ["## 6. 教学分析与技能流图数据"]

    if steps:
        lines.append("\n### 主要步骤\n")
        lines.append("| 步骤编号 | 描述 | 学习类型 | 状态 |")
        lines.append("|---------|------|---------|------|")
        for s in steps:
            lt = _learning_type(s.get('learning_type', 'unknown_candidate'))
            status = _label(s.get('status', 'candidate'))
            lines.append(f"| {s.get('step_id', '')} | {s.get('description', '')} | {lt} | {status} |")

    if subskills:
        lines.append("\n### 从属技能\n")
        lines.append("| 技能编号 | 描述 | 学习类型 | 父步骤 | 状态 |")
        lines.append("|---------|------|---------|--------|------|")
        for sk in subskills:
            lt = _learning_type(sk.get('learning_type', 'unknown_candidate'))
            parent = sk.get('parent_step_id', sk.get('linked_step_id', ''))
            status = _label(sk.get('status', 'candidate'))
            lines.append(f"| {sk.get('skill_id', '')} | {sk.get('description', '')} | {lt} | {parent} | {status} |")

    return "\n".join(lines)


def _render_section_7_entry_behaviors(project: dict) -> str:
    sg = project.get("skill_graph", {})
    entries = sg.get("entry_behaviors", [])

    lines = ["## 7. 入门技能"]
    if entries:
        lines.append("\n| 技能编号 | 描述 | 学习类型 | 支持技能 | 状态 |")
        lines.append("|---------|------|---------|---------|------|")
        for e in entries:
            lt = _learning_type(e.get('learning_type', 'unknown_candidate'))
            supports = e.get('supports_skill_ids', [])
            supports_str = ", ".join(supports[:2]) if supports else e.get('related_skill_id', '')
            status = _label(e.get('status', 'candidate'))
            name = e.get('name', e.get('description', ''))
            entry_id = e.get('entry_id', e.get('skill_id', ''))
            lines.append(f"| {entry_id} | {name} | {lt} | {supports_str} | {status} |")
    else:
        lines.append("\n暂无入门技能记录。")

    return "\n".join(lines)


def _render_section_learner_context(project: dict) -> str:
    """Render learner and environment analysis section.

    Handles the nested format produced by ``tools.learner_context``
    (via ``pipeline.normalize_context_analysis``) as well as older flat
    structures.
    """
    context = project.get("context_analysis", project.get("learner_context", {}))

    lines = ["## 8. 学习者与环境分析"]

    if not context or context.get("data_completeness") == "missing":
        lines.append("\n暂无学习者与环境分析数据。")
        return "\n".join(lines)

    # --- 8.1 Learner profile -------------------------------------------
    lines.append("\n### 8.1 学习者特征")
    learner = context.get("learner_profile", context.get("learner", {}))
    if learner:
        # entry_skills may be a list of strings or a nested dict
        entry = learner.get("entry_skills", [])
        if isinstance(entry, dict):
            entry = entry.get("items", entry.get("level", []))
        if entry:
            if isinstance(entry, list):
                lines.append(f"\n**入门技能：** {_teacher_text(entry)}")
            else:
                lines.append(f"\n**入门技能：** {_teacher_text(entry)}")

        pk = learner.get("prior_knowledge", "")
        pk = _teacher_text(pk, "")
        if pk:
            lines.append(f"**先前知识：** {pk}")

        mot = learner.get("motivation", "")
        mot = _teacher_text(mot, "")
        if mot:
            lines.append(f"**学习动机：** {mot}")

        prefs = learner.get("learning_preferences", [])
        if isinstance(prefs, dict):
            prefs = prefs.get("preferences", [])
        if prefs:
            lines.append(f"**学习偏好：** {_teacher_text(prefs)}")

        diffs = learner.get("common_difficulties", [])
        if diffs:
            lines.append("**常见困难：**")
            for d in diffs:
                if isinstance(d, dict):
                    lines.append(f"- {d.get('difficulty', d.get('description', str(d)))}")
                else:
                    lines.append(f"- {d}")

        gc = learner.get("group_characteristics", "")
        if isinstance(gc, dict):
            gc = gc.get("details", gc.get("grouping", ""))
        gc = _teacher_text(gc, "")
        if gc:
            lines.append(f"**群体特征：** {gc}")

        # attitude fields
        for key, label in [
            ("attitude_toward_content", "对内容的态度"),
            ("attitude_toward_delivery", "对教学方式的态度"),
            ("ability_level", "能力水平"),
        ]:
            val = learner.get(key, "")
            if isinstance(val, dict):
                val = val.get("description", "")
            if val:
                lines.append(f"**{label}：** {val}")

        # Flat-format fallback keys
        for key, label in [
            ("age", "年龄/年级"),
            ("learning_style", "学习风格"),
            ("special_needs", "特殊需求"),
        ]:
            val = learner.get(key, "")
            if val:
                lines.append(f"**{label}：** {val}")
    else:
        lines.append("\n暂无学习者特征数据。")

    # --- 8.2 Learning context ------------------------------------------
    lines.append("\n### 8.2 学习环境分析")
    lctx = context.get("learning_context", context.get("environment", context.get("environment_analysis", {})))
    if lctx:
        for key, label in [
            ("class_duration", "课时"),
            ("class_size", "班额"),
            ("devices", "设备条件"),
            ("network", "网络条件"),
            ("classroom_layout", "教室布局"),
            ("physical_space", "教学场地"),
            ("device_constraints", "设备条件"),
            ("network_availability", "网络条件"),
        ]:
            val = lctx.get(key, "")
            if isinstance(val, dict):
                val = val.get("description", json.dumps(val, ensure_ascii=False))
            if val:
                lines.append(f"- **{label}：** {val}")

        media = lctx.get("available_media", [])
        if media:
            if isinstance(media, list):
                lines.append(f"- **媒体资源：** {', '.join(str(m) for m in media)}")
            else:
                lines.append(f"- **媒体资源：** {media}")

        constraints = lctx.get("constraints", [])
        if constraints:
            if isinstance(constraints, list):
                lines.append(f"- **约束：** {'; '.join(str(c) for c in constraints)}")
            else:
                lines.append(f"- **约束：** {constraints}")
    else:
        lines.append("\n暂无环境分析数据。")

    # --- 8.3 Performance / transfer context ----------------------------
    pctx = context.get("performance_context", {})
    if pctx:
        lines.append("\n### 8.3 应用环境分析")
        tasks = pctx.get("real_world_tasks", [])
        if tasks:
            if isinstance(tasks, list):
                lines.append(f"- **真实任务：** {', '.join(str(t) for t in tasks)}")
            else:
                lines.append(f"- **真实任务：** {tasks}")

        risks = pctx.get("transfer_risks", [])
        if risks:
            if isinstance(risks, list):
                lines.append(f"- **迁移风险：** {'; '.join(str(r) for r in risks)}")
            else:
                lines.append(f"- **迁移风险：** {risks}")

        sim = pctx.get("similarity_to_learning_context", "")
        if sim:
            lines.append(f"- **环境相似度：** {sim}")

        env = pctx.get("use_environment", "")
        if env:
            lines.append(f"- **应用环境：** {env}")

        transfer = pctx.get("expected_transfer", "")
        if transfer:
            lines.append(f"- **预期迁移：** {transfer}")
    else:
        # Fallback: old "8.3 学习困难预估" section
        lines.append("\n### 8.3 学习困难预估")
        diffs_key = "common_difficulties"
        difficulties = context.get(diffs_key, context.get("anticipated_difficulties", []))
        if not difficulties:
            difficulties = context.get("learner_profile", {}).get("common_difficulties", [])
        if difficulties:
            if isinstance(difficulties, list):
                for d in difficulties:
                    if isinstance(d, dict):
                        lines.append(f"- {d.get('difficulty', d.get('description', str(d)))}")
                    else:
                        lines.append(f"- {d}")
            else:
                lines.append(f"- {difficulties}")
        else:
            lines.append("\n暂无学习困难预估。")

    # --- 8.4 Strategy implications -------------------------------------
    lines.append("\n### 8.4 设计启示")
    imps = context.get("strategy_implications", context.get("implications", context.get("design_implications", [])))
    if imps:
        for i, imp in enumerate(imps[:8], 1):
            if isinstance(imp, dict):
                lines.append(f"{i}. {imp.get('implication', imp.get('description', str(imp)))}")
            else:
                lines.append(f"{i}. {imp}")
    else:
        lines.append("暂无设计启示。")

    return "\n".join(lines)


def _render_section_instructional_strategy(project: dict) -> str:
    """Render instructional strategy section with 5 components and lesson flow.

    Handles both the normalized format produced by ``pipeline.py`` and
    the raw format directly from ``strategy_engine``.
    """
    strategy = project.get("instructional_strategy", {})

    lines = ["## 9. 教学策略"]

    if not strategy:
        lines.append("\n暂无教学策略数据。")
        return "\n".join(lines)

    # --- 9.1 Overview ---------------------------------------------------
    lines.append("\n### 9.1 策略概述")
    overview = strategy.get("overview", strategy.get("summary", strategy.get("description", "")))
    if overview:
        lines.append(f"\n{overview}")
    else:
        lines.append("\n暂无策略概述。")

    # --- 9.2-9.6 Five learning components -------------------------------
    # Ordered section titles for the five Dick-Carey components
    section_map = {
        "pre_instructional": "9.2 教学前活动",
        "content_presentation": "9.3 内容呈现",
        "learner_participation": "9.4 学习者参与",
        "assessment": "9.5 评估",
        "follow_through": "9.6 总结与迁移",
    }

    learning_components = strategy.get("learning_components", [])

    # Fallback: if learning_components is empty, build from raw components dict
    if not learning_components:
        learning_components = _build_components_fallback(strategy)

    rendered_types: set[str] = set()
    for comp in learning_components:
        comp_type = comp.get("type", "")
        rendered_types.add(comp_type)
        section_title = section_map.get(comp_type, f"9.x {comp.get('name', comp_type)}")

        lines.append(f"\n### {section_title}")
        desc = comp.get("description", comp.get("activity", "暂无"))
        if desc:
            lines.append(f"\n**活动描述：** {desc}")

        duration = comp.get("duration", "")
        if duration:
            lines.append(f"**时间分配：** {duration}")

        linked_objs = comp.get("linked_objectives", [])
        if linked_objs:
            lines.append(f"**对应目标：** {', '.join(str(o) for o in linked_objs)}")

        media = comp.get("media", comp.get("media_used", []))
        if media:
            if isinstance(media, list):
                lines.append(f"**使用媒体：** {', '.join(str(m) for m in media)}")
            else:
                lines.append(f"**使用媒体：** {media}")

        teacher_activity = comp.get("teacher_activity", comp.get("teacher做什么", ""))
        if teacher_activity:
            lines.append(f"**教师活动：** {teacher_activity}")

        learner_activity = comp.get("learner_activity", comp.get("learner做什么", ""))
        if learner_activity:
            lines.append(f"**学习者活动：** {learner_activity}")

    # --- 9.7 Lesson flow table ------------------------------------------
    lines.append("\n### 9.7 教学活动流程表")
    lesson_flow = strategy.get("lesson_flow", strategy.get("activity_flow", []))
    if lesson_flow:
        lines.append("\n| 时间段 | 活动 | 对应目标 | 学习成分 | 备注 |")
        lines.append("|--------|------|----------|----------|------|")
        for step in lesson_flow:
            # Try renderer keys first, then engine keys, then English keys
            time_slot = step.get(
                "时间",
                step.get("时间段", step.get("time", step.get("time_slot", ""))),
            )
            # If time_slot is a number, format it
            if isinstance(time_slot, (int, float)):
                time_slot = f"{time_slot}分钟"

            activity = step.get(
                "活动",
                step.get("具体活动", step.get("activity", step.get("description", ""))),
            )

            obj_ref = step.get(
                "objective_ids",
                step.get("对应目标", step.get("linked_objectives", step.get("objectives", ""))),
            )
            if isinstance(obj_ref, list):
                obj_ref = ", ".join(str(o) for o in obj_ref if o)

            comp_type = step.get(
                "学习成分",
                step.get("教学环节", step.get("component", step.get("learning_component", ""))),
            )

            notes = step.get(
                "备注",
                step.get("notes", step.get("评估方式", step.get("remark", ""))),
            )

            lines.append(f"| {time_slot} | {activity} | {obj_ref} | {comp_type} | {notes} |")
    else:
        lines.append("\n暂无教学活动流程表。")

    # --- 9.8 Media plan -------------------------------------------------
    lines.append("\n### 9.8 媒体方案")
    media_plan = strategy.get("media_plan", {})
    if media_plan:
        devices = media_plan.get("devices", [])
        if devices:
            if isinstance(devices, list):
                for d in devices:
                    if isinstance(d, dict):
                        name = d.get("name", d.get("type", "?"))
                        desc = d.get("description", "")
                        lines.append(f"- {name}: {desc}" if desc else f"- {name}")
                    else:
                        lines.append(f"- {d}")
            else:
                lines.append(f"- {devices}")
        resources = media_plan.get("resources", [])
        if resources:
            lines.append("\n**教学资源：**")
            for r in resources:
                if isinstance(r, dict):
                    lines.append(f"- {r.get('name', '?')}: {r.get('description', '')}")
                else:
                    lines.append(f"- {r}")
    else:
        lines.append("\n暂无媒体方案。")

    return "\n".join(lines)


def _build_components_fallback(strategy: dict) -> list:
    """Build learning_components list from raw strategy_engine format.

    When the normalized ``learning_components`` key is absent (e.g. the
    project was not run through ``pipeline.py``), this function builds
    the list from the raw ``components`` dict.
    """
    components = strategy.get("components", {})
    lesson_segments = strategy.get("lesson_segments", {})
    segments = lesson_segments.get("segments", []) if isinstance(lesson_segments, dict) else []

    comp_list: list[dict] = []

    # Pre-instructional
    pre = components.get("pre_instructional", {})
    pre_parts: list[str] = []
    motivation = pre.get("motivation", {})
    if isinstance(motivation, dict):
        for s in motivation.get("strategies", []):
            if isinstance(s, dict) and s.get("activity"):
                pre_parts.append(s["activity"])
    obj = pre.get("objectives_overview", {})
    if isinstance(obj, dict) and obj.get("activity"):
        pre_parts.append(obj["activity"])
    entry = pre.get("entry_skill_activation", {})
    if isinstance(entry, dict) and entry.get("activity"):
        pre_parts.append(entry["activity"])

    comp_list.append({
        "type": "pre_instructional",
        "name": "教学前活动",
        "description": "；".join(pre_parts) if pre_parts else "动机激发、目标呈现、入门技能检测",
        "linked_objectives": [],
        "duration": f"{pre.get('total_duration_minutes', 5)}分钟",
        "teacher_activity": "提问、引导、展示目标",
        "learner_activity": "思考、回答、了解学习目标",
    })

    # Content presentation
    pres = components.get("content_presentation", {})
    pres_phases = pres.get("phases", [])
    pres_desc = "；".join(f"{p.get('phase', '')}: {p.get('activity', '')}" for p in pres_phases)
    pres_dur = sum(p.get("duration_minutes", 0) for p in pres_phases)
    pres_objs = _fallback_segment_ids(segments, "content_presentation")
    comp_list.append({
        "type": "content_presentation",
        "name": "内容呈现",
        "description": pres_desc or "概念讲解与范例演示",
        "linked_objectives": pres_objs,
        "duration": f"{pres_dur}分钟",
        "teacher_activity": "讲解、演示、引导",
        "learner_activity": "观察、思考、记录",
    })

    # Learner participation
    part = components.get("learner_participation", {})
    part_phases = part.get("phases", [])
    part_desc = "；".join(f"{p.get('phase', '')}: {p.get('activity', '')}" for p in part_phases)
    part_dur = sum(p.get("duration_minutes", 0) for p in part_phases)
    part_objs = _fallback_segment_ids(segments, "learner_participation")
    comp_list.append({
        "type": "learner_participation",
        "name": "学习者参与",
        "description": part_desc or "练习与反馈",
        "linked_objectives": part_objs,
        "duration": f"{part_dur}分钟",
        "teacher_activity": "巡视、指导、收集反馈",
        "learner_activity": "练习、讨论、合作",
    })

    # Assessment
    assess = components.get("assessment", {})
    assess_items = assess.get("assessments", [])
    assess_desc = "；".join(
        f"{a.get('type', '')}: {a.get('activity', '')}" for a in assess_items
    )
    comp_list.append({
        "type": "assessment",
        "name": "评估",
        "description": assess_desc or "入门测试、前测、形成性评价、后测",
        "linked_objectives": [],
        "duration": f"{assess.get('total_assessment_minutes', 7)}分钟",
        "teacher_activity": "组织测试、收集作品、给予反馈",
        "learner_activity": "完成测试、提交作品",
        "embedded_assessments": [a.get("type", "") for a in assess_items],
    })

    # Follow-through
    follow = components.get("follow_through", {})
    follow_parts = follow.get("memory_support", []) + follow.get("transfer_tasks", [])
    follow_desc = "；".join(str(a) for a in follow_parts[:3])
    comp_list.append({
        "type": "follow_through",
        "name": "总结与迁移",
        "description": follow_desc or "记忆支持与迁移任务",
        "linked_objectives": [],
        "duration": f"{follow.get('total_duration_minutes', 4)}分钟",
        "teacher_activity": "总结要点、布置任务",
        "learner_activity": "回顾总结、记录作业",
    })

    return comp_list


def _fallback_segment_ids(segments: list, name: str) -> list[str]:
    """Extract objective IDs from a named segment (fallback helper)."""
    ids: list[str] = []
    for seg in segments:
        if seg.get("name") == name:
            for obj in seg.get("objectives", []):
                if isinstance(obj, dict):
                    oid = obj.get("objective_id", obj.get("id", ""))
                    if oid:
                        ids.append(oid)
                elif isinstance(obj, str) and obj:
                    ids.append(obj)
    return ids


def _render_section_10_objectives(project: dict) -> str:
    objectives = project.get("objectives", [])

    lines = ["## 10. 绩效目标表"]
    if objectives:
        lines.append("\n| 目标编号 | 关联技能 | 条件 | 行为 | 标准 | 状态 |")
        lines.append("|---------|---------|------|------|------|------|")
        for o in objectives:
            status = "✅" if o.get("status") == "pass" else "⚠️"
            lines.append(
                f"| {o.get('objective_id', '?')} "
                f"| {o.get('related_skill_id', '?')} "
                f"| {o.get('condition', '?')} "
                f"| {o.get('behavior', '?')} "
                f"| {o.get('criterion', '?')} "
                f"| {status} |"
            )
    else:
        lines.append("\n暂无绩效目标。")

    return "\n".join(lines)


def _render_section_11_assessment(project: dict) -> str:
    assessment = project.get("assessment_plan", {})

    lines = ["## 11. 评价方案"]

    # 11.1 入门技能测试
    entry_test = assessment.get("entry_behavior_test", {})
    lines.append("\n### 11.1 入门技能测试")
    if entry_test:
        lines.append(f"**目的：** {entry_test.get('purpose', '')}")
        for item in entry_test.get("items", []):
            lines.append(f"\n**任务：** {item.get('task_prompt', item.get('question', ''))}")
            if item.get("expected_evidence"):
                lines.append(f"\n**预期证据：** {item['expected_evidence']}")
            if item.get("scoring_criteria"):
                lines.append("\n**评分标准：**")
                for c in item["scoring_criteria"]:
                    lines.append(f"- {c.get('criterion', '')}：{c.get('description', '')}（{c.get('max_score', '')}分）")
    else:
        lines.append("\n暂无入门技能测试。")

    # 11.2 前测
    pretest = assessment.get("pretest", {})
    lines.append("\n### 11.2 前测")
    if pretest:
        lines.append(f"**目的：** {pretest.get('purpose', '')}")
        for item in pretest.get("items", []):
            lines.append(f"\n**任务：** {item.get('task_prompt', item.get('question', ''))}")
            if item.get("expected_evidence"):
                lines.append(f"\n**预期证据：** {item['expected_evidence']}")
            if item.get("scoring_criteria"):
                lines.append("\n**评分标准：**")
                for c in item["scoring_criteria"]:
                    lines.append(f"- {c.get('criterion', '')}：{c.get('description', '')}（{c.get('max_score', '')}分）")
    else:
        lines.append("\n暂无前测。")

    # 11.3 练习/模拟测试
    practice = assessment.get("practice_evidence", {})
    lines.append("\n### 11.3 练习/模拟测试")
    if practice:
        lines.append(f"**目的：** {practice.get('purpose', '')}")
        for item in practice.get("items", []):
            lines.append(f"\n**任务：** {item.get('task_prompt', item.get('task_description', ''))}")
            if item.get("expected_evidence"):
                lines.append(f"\n**预期证据：** {item['expected_evidence']}")
            if item.get("scoring_criteria"):
                lines.append("\n**评分标准：**")
                for c in item["scoring_criteria"]:
                    lines.append(f"- {c.get('criterion', '')}：{c.get('description', '')}（{c.get('max_score', '')}分）")
    else:
        lines.append("\n暂无练习/模拟测试。")

    # 11.4 后测
    posttest = assessment.get("posttest", {})
    lines.append("\n### 11.4 后测")
    if posttest:
        lines.append(f"**目的：** {posttest.get('purpose', '')}")
        for item in posttest.get("items", []):
            lines.append(f"\n**任务：** {item.get('task_prompt', item.get('question', ''))}")
            if item.get("expected_evidence"):
                lines.append(f"\n**预期证据：** {item['expected_evidence']}")
            if item.get("scoring_criteria"):
                lines.append("\n**评分标准：**")
                for c in item["scoring_criteria"]:
                    lines.append(f"- {c.get('criterion', '')}：{c.get('description', '')}（{c.get('max_score', '')}分）")
    else:
        lines.append("\n暂无后测。")

    # 11.5 目标-评价证据对应表
    evidence = assessment.get("evidence", [])
    lines.append("\n### 11.5 目标-评价证据对应表")
    if evidence:
        lines.append("\n| 目标编号 | 证据类型 | 任务提示 | 状态 |")
        lines.append("|---------|---------|---------|------|")
        for e in evidence:
            lines.append(
                f"| {e.get('linked_objective_id', '?')} "
                f"| {_label(e.get('evidence_type_name', e.get('evidence_type')), '评价任务证据')} "
                f"| {e.get('task_prompt', e.get('description', '?'))[:40]}... "
                f"| {_label(e.get('status'), '待确认')} |"
            )
    else:
        lines.append("\n暂无评价证据对应关系。")

    return "\n".join(lines)


def _render_section_12_alignment(project: dict) -> str:
    ac = project.get("quality_check", {})
    return f"""## 12. 一致性检查报告

{render_quality_summary(ac)}"""


def _render_section_13_confirmation(project: dict) -> str:
    sg = project.get("skill_graph", {})
    goals = project.get("goal", {})

    items = []
    if goals.get("status") != "pass":
        items.append("- [ ] 确认教学目的陈述是否准确")
    if sg.get("requires_teacher_confirmation"):
        items.append("- [ ] 确认教学分析流图是否正确")
    for o in project.get("objectives", []):
        if o.get("status") != "pass":
            items.append(f"- [ ] 确认绩效目标 {o.get('objective_id', '?')} 是否合理")
    if not items:
        items.append("- ✅ 所有内容已通过质量检查，无需额外确认")

    return f"""## 13. 教师确认事项

{chr(10).join(items)}"""


def _render_material_content(content: dict, indent: int = 0) -> list[str]:
    """
    Recursively render a material's content dict into markdown lines.
    Handles: str, list, dict, nested dicts, objective dicts.
    """
    lines = []
    if not isinstance(content, dict):
        if isinstance(content, str) and content.strip():
            lines.append(content)
        return lines

    for key, val in content.items():
        if not key:
            continue

        prefix = "  " * indent

        if isinstance(val, str) and val.strip():
            # Simple string value
            lines.append(f"{prefix}**{key}：**")
            lines.append(f"{prefix}{val}")

        elif isinstance(val, list) and val:
            lines.append(f"{prefix}**{key}：**")
            for item in val:
                if isinstance(item, str) and item.strip():
                    lines.append(f"{prefix}- {item}")
                elif isinstance(item, dict):
                    # Render dict items recursively
                    sub_lines = _render_dict_item(item, indent + 1)
                    lines.extend(sub_lines)

        elif isinstance(val, dict) and val:
            # Nested dict - render as subsection
            lines.append(f"{prefix}**{key}：**")
            sub_lines = _render_material_content(val, indent + 1)
            lines.extend(sub_lines)

    return lines


def _render_dict_item(item: dict, indent: int = 0) -> list[str]:
    """Render a single dict item from a list into readable markdown lines."""
    lines = []
    prefix = "  " * indent

    # Check if it's an objective dict
    if "behavior" in item and ("objective_id" in item or "related_skill_id" in item):
        behavior = item.get("behavior", "")
        condition = item.get("condition", "")
        criterion = item.get("criterion", "")
        if behavior:
            line = f"{prefix}- {behavior}"
            if condition:
                short_cond = condition[:50] + "..." if len(condition) > 50 else condition
                line += f"（条件：{short_cond}）"
            if criterion:
                short_crit = criterion[:40] + "..." if len(criterion) > 40 else criterion
                line += f"【标准：{short_crit}】"
            lines.append(line)
        return lines

    # Check if it's a flow step dict
    if "环节" in item or "教师行动" in item:
        parts = []
        for k in ["环节", "时间", "教师行动", "教师话术", "追问与反馈", "时间控制"]:
            if k in item and item[k]:
                val_str = str(item[k])
                if len(val_str) > 60:
                    val_str = val_str[:60] + "..."
                parts.append(f"{k}: {val_str}")
        if parts:
            lines.append(f"{prefix}- {' | '.join(parts)}")
        return lines

    # Check if it's a scoring criteria dict
    if "维度" in item or ("标准" in item and "分值" in item):
        dim = item.get("维度", item.get("标准", ""))
        score = item.get("分值", item.get("score", ""))
        desc = item.get("描述", item.get("说明", ""))
        line = f"{prefix}- {dim}"
        if score:
            line += f"（{score}分）"
        if desc:
            line += f"：{desc}"
        lines.append(line)
        return lines

    # Check if it's a peer review item
    if "检查项" in item or "check" in item:
        check = item.get("检查项", item.get("check", ""))
        scale = item.get("评分", item.get("scale", ""))
        lines.append(f"{prefix}- {check}" + (f"（{scale}）" if scale else ""))
        return lines

    # Check if it's a step dict with sub-keys
    if "步骤" in item or "第" in str(list(item.keys())):
        for k2, v2 in item.items():
            if isinstance(v2, str) and v2.strip():
                lines.append(f"{prefix}- {k2}: {v2}")
            elif isinstance(v2, dict):
                lines.append(f"{prefix}- {k2}:")
                sub = _render_material_content(v2, indent + 1)
                lines.extend(sub)
        return lines

    # Check if it's a scoring rubric dict
    if "项目" in item and "评分维度" in item:
        lines.append(f"{prefix}- {item.get('项目', '')}：{item.get('评分维度', '')}")
        if "得分等级" in item:
            lines.append(f"{prefix}  得分：{item['得分等级']}")
        return lines

    # Generic dict fallback - render all string values
    parts = []
    for k2, v2 in item.items():
        if isinstance(v2, str) and v2.strip():
            parts.append(f"{k2}: {v2}")
    if parts:
        lines.append(f"{prefix}- {' | '.join(parts)}")
    return lines


def _render_section_materials(project: dict) -> str:
    """
    Render instructional materials section (Section 14).
    Shows real content from each material, not just metadata.
    """
    materials = project.get("instructional_materials", {})
    if not materials:
        return ""

    lines = ["## 14. 教学材料包"]

    # Define section mapping: material_key -> (section_number, section_title)
    section_map = [
        ("teacher_guide", "14.1 教师授课手册"),
        ("student_worksheet", "14.2 学生学习单"),
        ("entry_test_sheet", "14.3 入门技能测试单"),
        ("pretest_sheet", "14.4 前测任务单"),
        ("group_task_sheet", "14.5 小组任务单"),
        ("peer_review_checklist", "14.6 互评检查表"),
        ("posttest_sheet", "14.7 后测任务单"),
        ("board_design", "14.8 板书设计"),
        ("simple_lesson_plan", "14.9 简版课堂教案"),
    ]

    for mat_key, section_title in section_map:
        mat = materials.get(mat_key, {})
        if not mat:
            continue

        lines.append(f"\n### {section_title}")

        # Extract content - materials are wrapped with "content" key
        content = mat.get("content", mat)

        # Render the content
        content_lines = _render_material_content(content)
        if content_lines:
            lines.extend(content_lines)
        else:
            lines.append("\n（材料内容待补充）")

    # 14.10 Material alignment
    alignment = project.get("material_alignment", {})
    if alignment:
        lines.append("\n### 14.10 材料一致性检查")
        status = alignment.get("overall_status", "unknown")
        coverage = alignment.get("coverage_rate", 0)
        lines.append(f"\n- **总体状态：** {status}")
        lines.append(f"- **目标覆盖率：** {coverage}")
        missing = alignment.get("missing_objectives", [])
        if missing:
            lines.append(f"- **未覆盖目标：** {', '.join(str(m) for m in missing[:5])}")
        else:
            lines.append("- **未覆盖目标：** 无")
        missing_assess = alignment.get("missing_assessment_materials", [])
        if missing_assess:
            lines.append(f"- **缺少评价材料：** {', '.join(str(m) for m in missing_assess[:5])}")
        else:
            lines.append("- **评价材料覆盖：** 完整")
        warnings = alignment.get("context_fit_warnings", [])
        if warnings:
            lines.append(f"- **环境适配警告：** {'; '.join(str(w) for w in warnings[:3])}")
        else:
            lines.append("- **环境适配：** 通过")
        recs = alignment.get("recommendations", [])
        if recs:
            lines.append("- **建议：**")
            for r in recs[:3]:
                lines.append(f"  - {r}")

    return "\n".join(lines)
