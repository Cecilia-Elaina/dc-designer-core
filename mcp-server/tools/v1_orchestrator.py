"""v1 local orchestrator for the China K12 information-technology plugin.

This module is intentionally deterministic. Codex supplies the conversational
reasoning and teacher confirmations; the local core validates scope, retrieves
evidence, builds the design object, renders graphs and exports artifacts.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

_THIS_DIR = Path(__file__).resolve().parent
_PKG_ROOT = _THIS_DIR.parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from core.evidence_store import search_official_evidence
from core.local_knowledge import ingest_private_document, search_private_knowledge
from core.product_config import (
    EDUCATION_SCOPE,
    initialize_project,
    normalize_stage,
    now_iso,
    validate_scope,
)
from core.runtime_paths import ensure_workspace


TOPIC_PATTERNS = {
    "branch": ("分支", "if", "elif", "else", "条件判断"),
    "loop": ("循环", "for", "while", "迭代", "重复"),
    "algorithm": ("算法", "问题解决", "流程图"),
}


def _contains(text: str, tokens: tuple[str, ...]) -> bool:
    text = str(text or "").lower()
    return any(token.lower() in text for token in tokens)


def _topic_kind(topic: str) -> str:
    for kind, tokens in TOPIC_PATTERNS.items():
        if _contains(topic, tokens):
            return kind
    return "general"


def _topic_analysis(topic: str, grade: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Return stable, domain-specific main steps, subskills and entries."""
    kind = _topic_kind(topic)
    if kind == "branch":
        steps = [
            "识别任务中的判断规则与条件关系",
            "书写基本分支框架",
            "编写条件表达式实现多分支判断逻辑",
            "测试与调试分支逻辑",
        ]
        subs = [
            ("理解条件概念", 0, "intellectual_skill"),
            ("提取判断标准", 0, "intellectual_skill"),
            ("梳理互斥条件与边界关系", 0, "intellectual_skill"),
            ("绘制条件—输出对应表", 0, "cognitive_strategy"),
            ("陈述 if、elif、else 语法规则", 1, "verbal_information"),
            ("书写代码块结构", 1, "psychomotor_skill"),
            ("组装 if-elif-else 基本框架", 1, "psychomotor_skill"),
            ("运用比较运算符", 2, "intellectual_skill"),
            ("运用逻辑运算符", 2, "intellectual_skill"),
            ("将判断标准转化为条件表达式", 2, "intellectual_skill"),
            ("嵌入条件与执行语句", 2, "psychomotor_skill"),
            ("校验条件顺序与覆盖范围", 2, "cognitive_strategy"),
            ("设计覆盖各分支与边界值的测试数据", 3, "intellectual_skill"),
            ("运行程序并观察输出", 3, "psychomotor_skill"),
            ("比较实际输出与预期结果", 3, "intellectual_skill"),
            ("定位语法错误或逻辑错误", 3, "intellectual_skill"),
            ("修改代码并重新测试", 3, "psychomotor_skill"),
        ]
        entries = [
            "能阅读七年级水平的问题描述并找出关键信息",
            "能使用比较符号表达简单数量关系",
            "能在 Python/VSCode 中运行最基本的顺序程序",
        ]
    elif kind == "loop":
        steps = [
            "识别任务中的重复模式与可迭代对象",
            "书写基本循环框架",
            "编写循环体逻辑实现遍历、跳过或退出",
            "测试与调试循环逻辑",
        ]
        subs = [
            ("阅读任务描述并找出重复操作", 0, "intellectual_skill"),
            ("确定循环次数或遍历范围", 0, "intellectual_skill"),
            ("识别可迭代对象与循环变量", 0, "intellectual_skill"),
            ("写出 for/while 循环语法结构", 1, "verbal_information"),
            ("设置循环变量和更新方式", 1, "psychomotor_skill"),
            ("组装基本循环框架", 1, "psychomotor_skill"),
            ("编写循环体中的处理语句", 2, "psychomotor_skill"),
            ("实现 continue 跳过条件", 2, "intellectual_skill"),
            ("实现 break 退出条件", 2, "intellectual_skill"),
            ("检查循环终止条件", 2, "cognitive_strategy"),
            ("设计覆盖边界和次数的测试数据", 3, "intellectual_skill"),
            ("观察输出并与预期结果比较", 3, "intellectual_skill"),
            ("定位循环次数或缩进错误", 3, "intellectual_skill"),
            ("修改代码并重新运行验证", 3, "psychomotor_skill"),
        ]
        entries = [
            "能阅读任务描述并指出重复出现的操作",
            "能使用变量保存数据并完成赋值",
            "能在 Python/VSCode 中运行顺序程序并查看输出",
        ]
    elif kind == "algorithm":
        steps = [
            "读懂问题情境并说出要解决的问题",
            "识别问题中的已知条件、目标和限制",
            "按先后顺序列出解决问题的操作步骤",
            "检查步骤是否完整、明确、有限",
            "用自然语言或流程图表达算法过程",
        ]
        subs = [
            ("从生活情境中找出问题目标", 0, "intellectual_skill"),
            ("区分已知条件和要完成的任务", 1, "intellectual_skill"),
            ("判断步骤之间的先后顺序", 2, "intellectual_skill"),
            ("使用顺序词（先、再、然后、最后）", 2, "verbal_information"),
            ("判断步骤是否缺漏、重复或顺序错误", 3, "cognitive_strategy"),
            ("按模板绘制简单流程图", 4, "psychomotor_skill"),
        ]
        entries = [
            f"能阅读{grade or '本学段'}水平的生活问题文本",
            "能用日常语言描述做事步骤",
            "能识别先、再、然后、最后等顺序词",
        ]
    else:
        steps = [
            "分析任务情境并明确问题目标",
            "建立问题的算法或信息处理模型",
            "选择工具并完成实现",
            "运行、测试并解释结果",
            "根据证据调试和改进作品",
        ]
        subs = [
            ("提取输入、处理和输出信息", 0, "intellectual_skill"),
            ("使用学科概念描述解决思路", 1, "verbal_information"),
            ("选择合适的数字化工具", 2, "intellectual_skill"),
            ("按照规范完成基本操作", 2, "psychomotor_skill"),
            ("设计测试数据并记录结果", 3, "cognitive_strategy"),
            ("根据错误证据定位并修正问题", 4, "intellectual_skill"),
        ]
        entries = [
            "能阅读并理解任务文本",
            "能使用基本数字化工具完成文件或代码操作",
            "能用文字或表格记录观察结果",
        ]
    main_steps = [
        {"step_id": f"S-{index:02d}", "order": index, "description": description, "learning_type": "intellectual_skill", "status": "candidate", "source": "v1_topic_analysis"}
        for index, description in enumerate(steps, 1)
    ]
    subordinate = []
    for index, (description, parent_index, learning_type) in enumerate(subs, 1):
        subordinate.append({
            "skill_id": f"SK-{parent_index + 1:02d}-{index:02d}",
            "name": description,
            "description": description,
            "learning_type": learning_type,
            "linked_step_id": f"S-{parent_index + 1:02d}",
            "parent_step_id": f"S-{parent_index + 1:02d}",
            "skill_type": "subordinate",
            "priority": index,
            "source": "v1_topic_analysis",
            "status": "candidate",
        })
    entry_records = [
        {
            "entry_id": f"E-01-{index:02d}",
            "name": description,
            "description": description,
            "learning_type": "verbal_information",
            "supports_skill_ids": [subordinate[index - 1]["skill_id"]] if subordinate else [],
            "source": "v1_entry_skill_boundary",
            "status": "candidate",
        }
        for index, description in enumerate(entries, 1)
    ]
    return main_steps, subordinate, entry_records


def _confirmation_map(request: dict) -> dict:
    raw = request.get("confirmations", {})
    if isinstance(raw, dict):
        return {str(key): bool(value) for key, value in raw.items()}
    if isinstance(raw, list):
        return {str(value): True for value in raw}
    return {}


def _source_documents(request: dict, workspace: str | None, warnings: list[str]) -> list[dict]:
    records: list[dict] = []
    refs = request.get("source_documents", [])
    if isinstance(refs, str):
        refs = [refs]
    for item in refs or []:
        path = item.get("path") if isinstance(item, dict) else item
        metadata = item.get("metadata", {}) if isinstance(item, dict) else {}
        if not path:
            continue
        if os.path.isfile(str(path)):
            result = ingest_private_document(str(path), metadata, workspace=workspace)
            if result.get("source_record"):
                records.append(result["source_record"])
            warnings.extend(result.get("warnings", []))
            if result.get("status") == "blocked_privacy":
                warnings.append(f"私有资料未入库：{path}")
        else:
            records.append({
                "source_id": f"teacher-input-{len(records) + 1:03d}",
                "source_name": str(path),
                "source_category": "teacher_private",
                "source_level": "C1",
                "can_be_goal_basis": "limited",
                "retrieval_status": "user_provided",
                "provenance_type": "TEACHER_INPUT",
                "distribution_allowed": False,
                "copyright_scope": "teacher_uploaded_private",
                "notes": "仅收到路径/名称，文件尚未被本地解析",
            })
            warnings.append(f"教师资料路径未找到，已作为待确认来源记录：{path}")
    return records


def _build_needs_analysis(request: dict) -> dict:
    performance = request.get("performance_context") or request.get("teacher_inputs", {}).get("performance_context") or {}
    has_evidence = bool(performance.get("evidence") or performance.get("current_performance") or performance.get("gap"))
    if has_evidence:
        return {
            "problem_type": "performance_gap",
            "expected_performance": performance.get("expected_performance", []),
            "current_performance": performance.get("current_performance", []),
            "evidence": performance.get("evidence", []),
            "gap": performance.get("gap", []),
            "instruction_is_appropriate": performance.get("instruction_is_appropriate", True),
            "non_instructional_factors": performance.get("non_instructional_factors", []),
            "numeric_claims_status": "teacher_provided_only",
        }
    return {
        "problem_type": "curriculum_driven",
        "expected_performance": ["课程标准要求的相关信息科技能力"],
        "current_performance": ["尚未提供实施前的班级测量数据"],
        "evidence": [],
        "gap": ["需要通过教学与形成性评价建立能力表现"],
        "instruction_is_appropriate": True,
        "non_instructional_factors": [],
        "numeric_claims_status": "no_invented_percentages",
    }


def _display_evidence(value: Any, default: str) -> str:
    """Render teacher-provided evidence without leaking Python containers."""
    if value is None or value == "":
        return default
    if isinstance(value, list):
        items = [_display_evidence(item, "") for item in value]
        return "；".join(item for item in items if item) or default
    if isinstance(value, dict):
        for key in ("description", "summary", "text", "value"):
            if value.get(key):
                return _display_evidence(value[key], default)
        return default
    return str(value)


def _build_performance_analysis(request: dict, needs: dict, goal: dict) -> dict:
    """Create a transparent needs/performance section for the Word report."""
    behavior = _display_evidence(goal.get("behavior"), "完成本课题的核心学习行为")
    expected_default = f"依据已检索课程标准，学习者能够{behavior}"
    performance_context = request.get("performance_context") or request.get("teacher_inputs", {}).get("performance_context") or {}
    explicit_expected = request.get("expected_performance")
    if isinstance(performance_context, dict):
        explicit_expected = explicit_expected or performance_context.get("expected_performance")
    expected = _display_evidence(explicit_expected, expected_default)
    explicit_current = request.get("current_performance")
    if isinstance(performance_context, dict):
        explicit_current = explicit_current or performance_context.get("current_performance")
    current = _display_evidence(
        explicit_current,
        "尚未提供实施前班级测量数据；当前仅能标注为待验证",
    )
    gap = _display_evidence(
        needs.get("gap"),
        "需要通过教学实施与形成性评价建立可观察的能力表现证据",
    )
    non_instructional = _display_evidence(needs.get("non_instructional_factors"), "")
    if needs.get("problem_type") == "performance_gap":
        problem = "已记录教师提供的绩效差距证据；正式比例、样本和测量方法仍以教师资料为准。"
    else:
        problem = "本项目由课程标准驱动；实施前班级绩效数据尚未提供，以下绩效差距属于待验证设计假设。"
    instructional_problem = (
        f"需要围绕“{behavior}”设计教学、练习和评价，使学习者能够在真实或模拟任务中完成并解释该行为。"
    )
    if non_instructional:
        instructional_problem += f" 已知的非教学因素：{non_instructional}；需要在教师确认后分别处理。"
    return {
        "performance_problem": problem,
        "instructional_problem": instructional_problem,
        "expected_performance": expected,
        "current_performance": current,
        "performance_gap": gap,
        "instructionally_solvable": "候选判断：主要部分可通过教学与形成性评价直接作用；非教学因素待确认",
        "evidence_status": "teacher_provided" if needs.get("problem_type") == "performance_gap" else "待实施/待验证",
        "numeric_claims_status": needs.get("numeric_claims_status", "no_invented_percentages"),
    }


def _make_goal(request: dict, sources: list[dict], stage: str) -> dict:
    from tools.goal_engine import generate_goal_draft

    topic = request.get("topic", "信息科技课题")
    grade = request.get("grade_level") or request.get("grade", "")
    behavior = request.get("goal_behavior") or request.get("behavior")
    if not behavior:
        kind = _topic_kind(topic)
        behavior = {
            "branch": "分析问题中的条件关系，编写并调试能够覆盖多种情况的 Python 分支程序",
            "loop": "识别任务中的重复模式，编写并调试能够正确遍历和控制迭代的 Python 循环程序",
            "algorithm": "分析简单问题并用自然语言或流程图描述完整、明确、有序的算法步骤",
        }.get(kind, "分析信息科技任务，选择适切工具完成实现、测试和改进")
    goal = generate_goal_draft({
        "learner": f"中国 K12 {grade or stage}学生",
        "behavior": behavior,
        "context": request.get("application_context") or "后续课堂上机任务、单元项目或真实数字化问题",
        "tools": request.get("equipment") or request.get("teacher_inputs", {}).get("equipment") or "学校计算机和适用的信息科技工具",
        "scene_type": "k12",
        "sources": sources,
    })
    goal["goal_id"] = "G-01"
    goal["condition"] = request.get("goal_condition") or (
        f"给定{topic}问题情境，并使用{request.get('equipment') or request.get('teacher_inputs', {}).get('equipment') or '学校计算机环境'}"
    )
    kind = _topic_kind(topic)
    if kind == "branch":
        criterion = "程序能够运行且结构、缩进和条件表达式正确；测试覆盖正常、边界及至少一种异常情况；能根据实际输出定位并修正错误"
    elif kind == "loop":
        criterion = "程序能够运行且循环变量、范围、缩进和终止条件正确；测试覆盖零次、一次和边界次数；能根据执行结果定位并修正错误"
    elif kind == "algorithm":
        criterion = "步骤完整、有序、无明显遗漏或重复，并能用自然语言或流程图说明设计依据"
    else:
        criterion = "结果正确、步骤完整，能够说明关键决策依据并提交可核验的过程证据"
    goal["criterion"] = request.get("goal_criterion") or criterion
    goal["performance_standard"] = goal["criterion"]
    goal["generated_full_statement"] = (
        f"{goal.get('learner', '学习者')}在{goal['condition']}时，"
        f"{goal.get('behavior', behavior)}；达到标准：{goal['criterion']}。"
    )
    goal["full_statement"] = goal["generated_full_statement"]
    goal["provenance_type"] = "AI_SUGGESTION"
    goal["evidence_status"] = "clause_candidate" if sources else "no_source"
    goal["teacher_confirmation_required"] = True
    return goal


def _make_objectives(graph: dict, request: dict) -> list[dict]:
    from tools.objective_engine import write_performance_objectives

    generated = write_performance_objectives(graph, {"stage": request.get("stage"), "subject": request.get("subject")})
    objectives = generated.get("objectives", [])
    for index, objective in enumerate(objectives, 1):
        objective["objective_id"] = f"PO-{index:02d}"
        # The legacy strategy engine uses ``id`` while the v1 contract uses
        # ``objective_id``. Keep both stable references in the project object.
        objective["id"] = objective["objective_id"]
        objective["CN"] = objective.get("condition", "给定任务情境和必要工具")
        objective["B"] = objective.get("behavior", "完成相关学习任务")
        objective["CR"] = objective.get("criterion", "结果正确、步骤完整并能说明依据")
        objective["provenance_type"] = "AI_SUGGESTION"
        if _contains(request.get("topic", ""), ("分支", "循环", "编程", "Python")):
            if "测试" in objective["B"] or "调试" in objective["B"]:
                objective["CR"] = "测试数据覆盖主要分支和边界情况，能根据输出定位并修正错误"
            elif "编写" in objective["B"] or "书写" in objective["B"]:
                objective["CR"] = "程序能够运行，结构和缩进正确，输出符合任务要求"
            objective["criterion"] = objective["CR"]
    return objectives


def _material(material_id: str, title: str, content: dict, objective_ids: list[str]) -> dict:
    return {
        "material_id": material_id,
        "title": title,
        "material_type": material_id,
        "target_users": ["teacher" if "教师" in title or "教案" in title or "板书" in title else "student"],
        "related_objective_ids": objective_ids,
        "content": content,
        "status": "candidate",
        "provenance_type": "AI_SUGGESTION",
        "usage_notes": ["由教师结合本校教材版本、设备和班级学情复核后使用"],
    }


def _make_programming_materials(project: dict, objectives: list[dict], kind: str) -> dict:
    """Concrete, topic-specific materials for Python branch/loop units."""
    title = "Python 分支结构" if kind == "branch" else "Python 循环结构"
    obj_ids = [item.get("objective_id", "") for item in objectives]
    if kind == "branch":
        guide_flow = [
            {"时间": "0-8分钟", "教学环节": "任务导入与需求分析", "教师行动": "呈现成绩等级/票价分类任务，引导学生填写条件—输出表，追问条件是否互斥、边界是否覆盖。", "学生活动": "圈出条件，写出不同输入对应的输出。", "反馈": "发现学生把自然语言条件直接写成代码时，先回到表格核对。"},
            {"时间": "8-20分钟", "教学环节": "框架示范", "教师行动": "用逐行演示说明 if、elif、else、冒号、缩进和执行路径。", "学生活动": "在学习单补全框架，预测每个输入的执行分支。", "反馈": "优先检查缩进和分支顺序，不直接替学生改完整代码。"},
            {"时间": "20-35分钟", "教学环节": "条件表达式与代码实现", "教师行动": "示范比较运算符和逻辑运算符，把条件表翻译成表达式。", "学生活动": "完成分支程序并在 VSCode 运行。", "反馈": "要求学生解释‘这个条件为什么放在这里’，防止只凭试错。"},
            {"时间": "35-45分钟", "教学环节": "测试、调试与迁移", "教师行动": "组织正常值、边界值和异常值测试，示范根据输出定位逻辑错误。", "学生活动": "记录实际/预期输出，修改代码并提交测试证据。", "反馈": "检查测试是否覆盖每个分支和边界值。"},
        ]
        worksheet = {
            "标题": "七年级信息科技——Python 分支结构学习任务单",
            "使用说明": "先做表格建模，再写代码；每次修改都保留测试输入、预期输出和实际输出。",
            "任务一：从情境中提取条件": {
                "情境": "根据输入的成绩 score 输出 A/B/C/D 四个等级。",
                "条件—输出表": [
                    {"条件": "score >= 90", "输出": "A", "边界测试": "90"},
                    {"条件": "80 <= score < 90", "输出": "B", "边界测试": "80、89"},
                    {"条件": "60 <= score < 80", "输出": "C", "边界测试": "60、79"},
                    {"条件": "score < 60", "输出": "D", "边界测试": "59"}
                ],
                "我发现的覆盖/冲突问题": "________________________________________"
            },
            "任务二：补全基本分支框架": {
                "代码模板": "score = int(input('请输入成绩：'))\nif __________:\n    level = 'A'\nelif __________:\n    level = 'B'\nelif __________:\n    level = 'C'\nelse:\n    level = 'D'\nprint(level)",
                "缩进检查": ["每个条件后有冒号", "执行语句统一缩进", "elif 与 if 对齐", "else 与 if 对齐"]
            },
            "任务三：把判断规则改写成条件表达式": {
                "规则": "温度低于 10 提示‘注意保暖’，10—25 提示‘适宜’，高于 25 提示‘注意防暑’。",
                "我的条件表达式": ["条件1：________________", "条件2：________________", "条件3：________________"],
                "为什么这样排序": "________________________________________"
            },
            "任务四：小组编程任务": {
                "任务选择": ["根据年龄输出票价类别", "根据体重和身高判断运动建议", "根据电量显示设备使用建议"],
                "输入/条件/输出": "________________________________________",
                "代码区": "________________________________________\n________________________________________\n________________________________________",
                "组内解释": "我们把哪个条件放在第一层？为什么？________________"
            },
            "任务五：测试与调试记录": {
                "测试记录": [
                    {"输入": "正常值", "预期输出": "________", "实际输出": "________", "是否一致": "□是 □否"},
                    {"输入": "边界值", "预期输出": "________", "实际输出": "________", "是否一致": "□是 □否"},
                    {"输入": "异常/极端值", "预期输出": "________", "实际输出": "________", "是否一致": "□是 □否"}
                ],
                "错误定位": "错误发生在哪个条件/分支？________________",
                "修改理由": "________________________________________"
            },
            "任务六：独立迁移": {
                "题目": "输入一个整数，判断它是正数、负数还是零，并输出判断结果。",
                "代码区": "________________________________________\n________________________________________\n________________________________________",
                "至少三组测试数据": "________________________________________"
            }
        }
        entry = {"标题": "Python 分支结构入门技能测试", "题目": ["阅读简单问题并提取条件", "在顺序程序中完成变量赋值和输出", "用比较符号判断两个数的关系"], "作答区": "________________________________________", "评分说明": "能正确完成 2/3 项后进入本课；未通过者使用条件—输出表和代码框架支架。"}
        pre = {"标题": "Python 分支结构前测", "任务": "阅读‘根据年龄计算票价’的要求，写出条件—输出表，不要求完整代码。", "证据": "条件是否覆盖全部情况，是否出现重叠或遗漏。", "评分": [{"维度": "条件提取", "分值": 2}, {"维度": "边界判断", "分值": 2}, {"维度": "表达清晰", "分值": 1}]}
        group = {"标题": "小组任务卡：把分类规则写成程序", "步骤": ["阅读任务", "画条件—输出表", "写分支框架", "补全表达式", "运行测试", "互相解释和修改"], "提交物": ["代码", "三组测试记录", "一段修改理由"]}
        peer = {"标题": "Python 分支程序互评检查表", "检查项": ["输入和输出是否明确", "条件是否互斥且覆盖", "if/elif/else 结构和缩进是否正确", "条件表达式是否与表格一致", "测试是否包含分支和边界值", "实际输出是否与预期一致", "修改理由是否能对应错误证据"], "等级": "每项 0/1 分，至少 6 分且无关键结构错误。"}
        post = {"标题": "Python 分支结构后测", "真实性任务": "输入一个整数 n：n<0 输出‘负数’，n=0 输出‘零’，0<n<10 输出‘个位正数’，n>=10 输出‘两位及以上正数’。", "要求": ["先写条件—输出表", "独立编写 Python 程序", "设计至少 5 组含边界值的测试数据", "提交一条错误定位和修改记录"], "评分量规": [{"维度": "任务分析", "优秀": "条件完整、互斥、边界正确", "分值": 4}, {"维度": "代码实现", "优秀": "结构、缩进和表达式正确并可运行", "分值": 4}, {"维度": "测试调试", "优秀": "覆盖分支/边界且能根据证据修改", "分值": 4}], "总分": 12}
        board = {"标题": title, "核心板书": ["任务：条件 → 判断 → 输出", "基本结构：if / elif / else", "表达式：比较运算符 + 逻辑运算符", "测试：正常值、边界值、异常值", "调试：实际输出 ≠ 预期输出 → 定位条件/顺序/缩进"]}
    else:
        guide_flow = [
            {"时间": "0-8分钟", "教学环节": "重复任务建模", "教师行动": "呈现批量处理任务，圈出重复操作、循环变量、范围和终止条件。", "学生活动": "用执行轨迹表描述每一轮变化。", "反馈": "区分重复操作和重复数据，避免见到多个数据就机械套循环。"},
            {"时间": "8-20分钟", "教学环节": "for/while 框架示范", "教师行动": "演示循环变量、范围、缩进和执行顺序。", "学生活动": "补全框架，预测输出。", "反馈": "先追问循环何时结束，再检查语法。"},
            {"时间": "20-35分钟", "教学环节": "循环体与控制语句", "教师行动": "对比 continue、break 和自然结束，演示执行轨迹。", "学生活动": "修改循环体，观察跳过和退出效果。", "反馈": "要求说明控制语句改变了哪一条执行路径。"},
            {"时间": "35-45分钟", "教学环节": "测试与调试", "教师行动": "组织零次、一次、边界次数和较大次数测试。", "学生活动": "根据输出定位循环次数、缩进或终止条件错误。", "反馈": "把无限循环风险作为必须检查项。"},
        ]
        worksheet = {
            "标题": "七年级信息科技——Python 循环结构学习任务单",
            "使用说明": "先画执行轨迹，再写循环；测试必须包含零次、一次和边界次数。",
            "任务一：识别重复模式": {"情境": "输出 1 到 10 的数字并计算总和。", "重复操作": "____________", "循环变量": "____________", "范围/终止条件": "____________"},
            "任务二：补全循环框架": {"代码模板": "total = 0\nfor i in range(1, ____):\n    total = total + ____\nprint(total)", "执行轨迹": [{"轮次": "第1轮", "i": "____", "total": "____"}, {"轮次": "最后一轮", "i": "____", "total": "____"}]},
            "任务三：编写循环体": {"题目": "输出 1 到 20 中的偶数。", "代码区": "________________________________________", "选择": "使用 for 的理由：________________"},
            "任务四：控制语句任务": {"任务": "遍历 1 到 20，跳过 5 的倍数，遇到 17 时退出。", "代码区": "________________________________________", "continue 的作用": "____________", "break 的作用": "____________"},
            "任务五：测试与调试": {"测试记录": [{"次数": "0 次", "预期": "____", "实际": "____"}, {"次数": "1 次", "预期": "____", "实际": "____"}, {"次数": "边界次数", "预期": "____", "实际": "____"}], "错误定位": "____________", "修改理由": "____________"},
            "任务六：独立迁移": {"题目": "输入 n，计算 1 到 n 中所有 3 的倍数之和。", "循环设计": "____________", "代码区": "________________________________________", "测试数据": "____________"}
        }
        entry = {"标题": "Python 循环结构入门技能测试", "题目": ["阅读重复任务并指出重复操作", "完成变量赋值和输出", "按顺序执行三条简单语句"], "评分说明": "能正确完成 2/3 项后进入本课；未通过者使用执行轨迹表支架。"}
        pre = {"标题": "Python 循环结构前测", "任务": "不用写完整代码，说明如何输出 1 到 5，并画出前两轮执行轨迹。", "证据": "能否说清循环变量、范围、循环体和结束条件。", "评分": [{"维度": "重复模式", "分值": 2}, {"维度": "执行顺序", "分值": 2}, {"维度": "终止条件", "分值": 1}]}
        group = {"标题": "小组任务卡：批量处理程序", "步骤": ["识别重复模式", "选择 for 或 while", "画执行轨迹", "完成循环体", "测试边界", "解释修改"], "提交物": ["代码", "执行轨迹表", "四组测试记录"]}
        peer = {"标题": "Python 循环程序互评检查表", "检查项": ["循环变量和范围是否明确", "循环体缩进是否正确", "循环是否能终止", "continue/break 是否放在正确位置", "是否测试零次、一次、边界次数", "输出是否与预期一致", "是否能解释一轮执行"], "等级": "每项 0/1 分，至少 6 分且无无限循环。"}
        post = {"标题": "Python 循环结构后测", "真实性任务": "输入正整数 n，输出 1 到 n 中 3 的倍数并计算总和。", "要求": ["选择并说明 for/while", "编写可运行程序", "测试 n=1、n=3、n=10 等边界", "说明循环何时结束"], "评分量规": [{"维度": "任务分析", "优秀": "识别变量、范围和终止条件", "分值": 4}, {"维度": "代码实现", "优秀": "循环体、缩进和输出正确", "分值": 4}, {"维度": "测试调试", "优秀": "边界覆盖并能解释结果", "分值": 4}], "总分": 12}
        board = {"标题": title, "核心板书": ["重复操作 → 循环变量 → 范围/终止条件 → 循环体", "for：遍历确定范围；while：条件满足时重复", "continue：跳过本轮；break：退出循环", "测试：零次、一次、边界次数、终止"]}
    return {
        "teacher_guide": _material("MAT-01", f"{title}教师教学指南", {"教学流程": guide_flow, "常见追问": ["这条规则/重复操作来自题目哪句话？", "你如何证明覆盖了边界？", "实际输出与预期不一致时先检查哪里？"]}, obj_ids),
        "student_worksheet": _material("MAT-02", worksheet["标题"], worksheet, obj_ids),
        "entry_test_sheet": _material("MAT-03", entry["标题"], entry, obj_ids[:2]),
        "pretest_sheet": _material("MAT-04", pre["标题"], pre, obj_ids[:3]),
        "group_task_sheet": _material("MAT-05", group["标题"], group, obj_ids),
        "peer_review_checklist": _material("MAT-06", peer["标题"], peer, obj_ids),
        "posttest_sheet": _material("MAT-07", post["标题"], post, obj_ids),
        "board_design": _material("MAT-08", board["标题"], board, obj_ids),
        "simple_lesson_plan": _material("MAT-09", f"{title}简版课堂教案", {"课时": project.get("project", {}).get("periods", "待确认"), "教学重点": "从任务建模到可运行程序，再到测试调试证据", "教学难点": "条件/循环逻辑、边界覆盖和错误定位", "流程": guide_flow}, obj_ids),
    }


def _make_programming_assessment(objectives: list[dict], kind: str) -> dict:
    focus = "分支条件、分支覆盖和边界测试" if kind == "branch" else "循环变量、终止条件和执行轨迹"
    evidence = []
    for objective in objectives:
        evidence.append({
            "evidence_id": f"AS-{objective.get('objective_id', 'PO')}",
            "linked_objective_id": objective.get("objective_id", ""),
            "evidence_type": "authentic_programming_task",
            "task_prompt": f"围绕{focus}完成代码、运行、测试或调试任务：{objective.get('B', objective.get('behavior', '完成目标'))}",
            "required_artifact": "可运行代码 + 测试输入/预期输出/实际输出 + 修改说明",
            "scoring_criteria": [
                {"criterion": "代码结构", "description": "分支/循环结构、缩进和表达式正确", "max_score": 2},
                {"criterion": "运行结果", "description": "程序能够运行且输出符合任务要求", "max_score": 2},
                {"criterion": "测试覆盖", "description": "测试覆盖关键情况和边界", "max_score": 2},
                {"criterion": "调试解释", "description": "能根据证据解释或修正错误", "max_score": 2},
            ],
        })
    return {
        "entry_behavior_test": {"title": "入门技能测试", "items": [
            {"task_prompt": "阅读简单任务并圈出输入、处理和输出", "expected_evidence": "能指出任务要素", "max_score": 1},
            {"task_prompt": "完成变量赋值和 print 输出", "expected_evidence": "代码语法基本正确", "max_score": 1},
            {"task_prompt": "按顺序写出三条程序执行语句", "expected_evidence": "顺序和缩进意识基本正确", "max_score": 1},
        ], "mastery_standard": "至少 2/3 项完成"},
        "pretest": {"title": "前测", "task": f"用表格/执行轨迹说明{focus}，暂不要求完整代码", "items": [{"task_prompt": f"用表格/执行轨迹说明{focus}", "expected_evidence": "能解释建模依据", "max_score": 5}]},
        "practice_evidence": {"title": "课堂练习证据", "items": evidence[: max(1, len(evidence) // 2)]},
        "posttest": {"title": "后测真实性任务", "task": "独立完成可运行程序，提交测试和调试记录", "rubric": ["任务分析", "代码实现", "运行测试", "调试解释"], "items": evidence},
        "authentic_task": {"title": "真实性编程任务", "focus": focus, "evidence_requirements": ["源代码", "运行截图或输出记录", "边界测试", "错误修订说明"]},
        "rubric": [{"dimension": "任务建模", "score": 4}, {"dimension": "代码实现", "score": 4}, {"dimension": "测试与调试", "score": 4}],
        "rubrics": [{"name": "真实性编程任务量规", "criteria": [{"dimension": "任务建模", "description": "条件/重复模式、边界或终止条件分析正确", "max_score": 4}, {"dimension": "代码实现", "description": "代码结构、缩进、表达式和输出正确", "max_score": 4}, {"dimension": "测试与调试", "description": "覆盖关键情况并能根据证据修改", "max_score": 4}]}],
        "evidence": evidence,
        "alignment": {"coverage_rate": 1.0, "uncovered_objectives": []},
    }


def _build_formative_plan(materials: dict, request: dict) -> dict:
    from tools.formative_evaluation import design_field_trial, design_one_on_one_evaluation, design_small_group_evaluation

    learners = [{"level": "较低", "code": "L-A"}, {"level": "中等", "code": "L-B"}, {"level": "较高", "code": "L-C"}]
    plan = {
        "one_on_one": design_one_on_one_evaluation(materials, learners),
        "small_group": design_small_group_evaluation(materials, 12),
        "field_trial": design_field_trial(materials, request.get("learning_context", {})),
        "data_status": "待实施",
        "data_gap": ["任务完成率", "用时", "错误类型", "材料理解度", "教师反思"],
        "recommendations": [
            {"description": "根据真实错误类型修订示范、支架和练习梯度", "target": "教学策略/材料", "priority": "高", "source": "AI推断，待形成性评价验证"},
            {"description": "核对技能图中的入门技能边界是否符合不同层次学生", "target": "教学分析", "priority": "中", "source": "AI推断，待形成性评价验证"},
        ],
    }
    return plan


def _build_ai_process_log(request: dict, sources: list[dict]) -> dict:
    stages = [
        ("1", "项目初始化", "校验中国 K12 信息科技范围与输入字段"),
        ("2", "标准检索", f"检索到 {len(sources)} 个官方/教师来源候选"),
        ("3", "需求与绩效分析", "区分课程驱动与问题驱动，不生成未经提供的比例"),
        ("4", "教学目的", "生成含学习者、行为、条件、标准和应用情境的候选"),
        ("5", "教学分析", "生成目的操作流程、技能层级和入门技能边界"),
        ("6", "学习者与环境", "根据教师提供信息生成学情与设备条件草案"),
        ("7", "绩效目标", "为技能节点生成 CN/B/CR 目标"),
        ("8", "评价方案", "生成入门、前测、练习、后测和真实性任务"),
        ("9", "教学策略与材料", "从目标和评价反推流程、示范、练习和材料"),
        ("10", "门禁与导出", "检查来源、图逻辑、一致性并生成可编辑项目包"),
    ]
    return {
        "record_status": "actual_local_pipeline_record",
        "iteration_log": [
            {
                "iteration": number,
                "model_step": step,
                "original_draft_or_diagnosis": "由当前项目输入和前一模块输出产生",
                "structured_prompt": f"执行 {step}；仅使用已标注来源；缺失信息标为待确认。",
                "ai_core_output_summary": summary,
                "human_evaluation_and_revision": "待教师复核；系统自检已执行",
                "dick_carey_alignment": step,
            }
            for number, step, summary in stages
        ],
        "model_version": "Codex local orchestration contract",
        "integrity_statement": "本表记录本次本地确定性流程调用，不代表教师已经确认全部设计决策。",
        "ethics_statement": "未将教师私有资料标为官方依据；未写入学生姓名、学号或个人成绩。",
        "reviews": [],
    }


def _safe_file_name(text: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "_", str(text or "项目")).strip(" .")
    return value or "信息科技教学设计"


def _write_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return str(path)


def _export_v1(project: dict, output_dir: str | None, workspace: str | None) -> dict:
    from tools.document_exporter import export_all
    from tools.drawio_exporter import export_skill_graph_view, export_skill_graph_workbook
    from tools.export_package import render_markdown_report
    from core.visual_qa import run_visual_qa

    dirs = ensure_workspace(workspace)
    destination = Path(output_dir).expanduser().resolve() if output_dir else dirs["exports"] / _safe_file_name(project["project"]["title"])
    destination.mkdir(parents=True, exist_ok=True)
    legacy_result = export_all(project, str(destination))
    diagrams = destination / "diagrams"
    diagrams.mkdir(exist_ok=True)
    graph_path = diagrams / "技能流图_多页面.drawio"
    graph_result = export_skill_graph_workbook(project.get("skill_graph", {}), str(graph_path))
    operation_path = diagrams / "目的操作流程.drawio"
    hierarchy_path = diagrams / "技能层级图.drawio"
    operation_result = export_skill_graph_view(project.get("skill_graph", {}), "goal_operation_flow", str(operation_path))
    hierarchy_result = export_skill_graph_view(project.get("skill_graph", {}), "skill_hierarchy", str(hierarchy_path))
    control_result = None
    from tools.document_exporter import _create_v1_graph_image
    for view_name, file_name in (
        ("goal_operation_flow", "目的操作流程.png"),
        ("skill_hierarchy", "技能层级图.png"),
        ("control_flow", "程序控制流程图.png"),
    ):
        image = _create_v1_graph_image(project, view_name)
        if image:
            image_path = diagrams / file_name
            image_path.write_bytes(image.getvalue())
            if view_name == "control_flow":
                control_result = str(image_path)

    # Give the teacher stable, readable filenames while retaining the legacy
    # exporter outputs for migration and regression compatibility.
    legacy_files = legacy_result.get("files", {}) if isinstance(legacy_result, dict) else {}
    stable_aliases = {
        "dc_report": "教学系统设计报告.docx",
        "lesson_plan": "教师教学指南.docx",
        "student_worksheet": "学生学习单.docx",
        "alignment_matrix": "一致性矩阵.xlsx",
        "ai_process_record": "AI过程记录.docx",
    }
    alias_paths = {}
    for source_key, alias_name in stable_aliases.items():
        source_info = legacy_files.get(source_key, {})
        source_path = source_info.get("path", "") if isinstance(source_info, dict) else ""
        alias_path = destination / alias_name
        if source_path and os.path.isfile(source_path):
            shutil.copy2(source_path, alias_path)
            alias_paths[source_key] = str(alias_path)
    project_json = _write_json(destination / "project.json", project)
    report_md = destination / "教学系统设计报告.md"
    report_md.write_text(render_markdown_report(project), encoding="utf-8")
    source_md = destination / "证据与来源清单.md"
    source_lines = ["# 证据与来源清单", "", "所有条款在教师确认前均为候选证据。", ""]
    source_category_labels = {
        "official_authority": "官方依据",
        "teacher_private": "教师私有资料",
        "professional_authority": "专业权威资料",
        "ai_generated": "AI生成内容",
    }
    evidence_status_labels = {
        "clause_candidate": "条款候选（待教师核对）",
        "teacher_confirmed": "教师已确认",
        "final_verified": "最终已验证",
        "no_source": "未找到依据",
    }
    for source in project.get("sources", []):
        source_lines.append(f"## {source.get('source_name', source.get('title', '未命名来源'))}")
        source_lines.append(f"- 来源等级：{source.get('source_level', '')}")
        source_lines.append(f"- 来源类别：{source_category_labels.get(source.get('source_category', ''), '待分类')}")
        source_lines.append(f"- 版本：{source.get('source_version', '')}")
        source_lines.append(f"- 发布日期：{source.get('publication_date', source.get('source_date', '未提供'))}")
        source_lines.append(f"- 链接：{source.get('source_url', '本地教师资料，不公开分发')}")
        for clause in source.get("specific_clauses", []):
            location = clause.get("page_number") or clause.get("anchor") or "位置待补充"
            excerpt = clause.get("excerpt") or clause.get("clause_text", "")
            summary = clause.get("normalized_summary") or clause.get("clause_text", "")
            status = evidence_status_labels.get(clause.get("evidence_status", "clause_candidate"), "条款候选（待教师核对）")
            source_lines.append(f"- 条款编号：{clause.get('clause_id', '')}")
            source_lines.append(f"- 条款位置：{location}")
            source_lines.append(f"- 短引文：{excerpt}")
            source_lines.append(f"- 条款摘要：{summary}")
            source_lines.append(f"- 证据状态：{status}")
        source_lines.append("")
    source_md.write_text("\n".join(source_lines), encoding="utf-8")
    align_md = destination / "一致性检查报告.md"
    align_md.write_text(json.dumps(project.get("alignment_report", {}), ensure_ascii=False, indent=2), encoding="utf-8")
    decision_md = destination / "设计决策记录.md"
    decision_md.write_text(json.dumps(project.get("decision_log", []), ensure_ascii=False, indent=2), encoding="utf-8")
    file_paths = {
        key: value.get("path", "")
        for key, value in legacy_files.items()
        if isinstance(value, dict) and value.get("path")
    }
    file_paths.update(alias_paths)
    file_paths.update({
        "project_json": project_json,
        "report_markdown": str(report_md),
        "source_trace_markdown": str(source_md),
        "alignment_markdown": str(align_md),
        "decision_log": str(decision_md),
        "drawio_workbook": graph_result.get("path", str(graph_path)),
        "goal_operation_drawio": operation_result.get("path", str(operation_path)),
        "skill_hierarchy_drawio": hierarchy_result.get("path", str(hierarchy_path)),
        "goal_operation_png": str(diagrams / "目的操作流程.png") if (diagrams / "目的操作流程.png").exists() else "",
        "skill_hierarchy_png": str(diagrams / "技能层级图.png") if (diagrams / "技能层级图.png").exists() else "",
        "control_flow_png": control_result or "",
        "export_index_json": str(destination / "export_index.json"),
    })
    visual_files = {
        "dc_report": alias_paths.get("dc_report", file_paths.get("dc_report", "")),
        "lesson_plan": alias_paths.get("lesson_plan", file_paths.get("lesson_plan", "")),
        "student_worksheet": alias_paths.get("student_worksheet", file_paths.get("student_worksheet", "")),
        "ai_process_record": alias_paths.get("ai_process_record", file_paths.get("ai_process_record", "")),
        "drawio_workbook": file_paths.get("drawio_workbook", ""),
        "goal_operation_drawio": file_paths.get("goal_operation_drawio", ""),
        "skill_hierarchy_drawio": file_paths.get("skill_hierarchy_drawio", ""),
    }
    visual_qa = run_visual_qa(visual_files, destination / "visual_qa")
    file_paths["visual_qa_report"] = visual_qa.get("report_path", "")
    project.setdefault("quality", {})["visual_check"] = visual_qa
    index = {
        "schema_version": "1.0.0",
        "export_status": "pending_validation",
        "project_json": project_json,
        "report_markdown": str(report_md),
        "source_trace_markdown": str(source_md),
        "alignment_markdown": str(align_md),
        "decision_log": str(decision_md),
        "drawio_workbook": graph_result.get("path", str(graph_path)),
        "files": file_paths,
        "legacy_exports": legacy_result,
        "visual_qa": visual_qa,
    }
    index_path = _write_json(destination / "export_index.json", index)
    required_paths = [
        file_paths.get("project_json"),
        file_paths.get("report_markdown"),
        file_paths.get("drawio_workbook"),
        alias_paths.get("dc_report"),
        alias_paths.get("lesson_plan"),
        alias_paths.get("student_worksheet"),
        alias_paths.get("alignment_matrix"),
        alias_paths.get("ai_process_record"),
        file_paths.get("goal_operation_png"),
        file_paths.get("skill_hierarchy_png"),
    ]
    if project.get("skill_graph", {}).get("include_control_flow"):
        required_paths.append(file_paths.get("control_flow_png"))
    export_status = "success" if all(path and os.path.isfile(path) and os.path.getsize(path) > 0 for path in required_paths) else "partial"
    index["export_status"] = export_status
    _write_json(Path(index_path), index)
    project["exports"] = {"output_dir": str(destination), "index": index_path, **index}
    _write_json(Path(project_json), project)
    return {
        "status": "success" if export_status == "success" else "completed_with_warnings",
        "export_status": export_status,
        "output_dir": str(destination),
        "export_index_json": index_path,
        "files": file_paths,
        "legacy_exports": legacy_result,
        "visual_qa": visual_qa,
    }


def run_v1_design(request: dict, output_dir: str | None = None, workspace: str | None = None) -> dict:
    check = validate_scope(request)
    if not check["valid"]:
        return {
            "status": "unsupported_scope",
            "education_scope": EDUCATION_SCOPE,
            "errors": check["errors"],
            "warnings": check["warnings"],
            "can_export_final": False,
            "required_confirmations": [],
        }
    warnings = list(check["warnings"])
    project = initialize_project(request)
    project["project"]["title"] = request.get("title") or request.get("topic") or project["project"]["title"]
    project["metadata"] = {
        "project_name": project["project"]["title"],
        "subject": project["project"]["subject"],
        "grade": project["project"]["grade"],
        "stage": project["project"]["stage"],
        "topic": project["project"]["topic"],
    }
    # Legacy engines are still being migrated; keep flat aliases in addition
    # to the v1 nested project object.
    project["topic"] = project["project"]["topic"]
    project["topic_name"] = project["project"]["topic"]
    project["grade"] = project["project"]["grade"]
    project["subject"] = project["project"]["subject"]
    stage = check["stage"]
    topic = request.get("topic", "")
    evidence = search_official_evidence({"stage": stage, "grade": project["project"]["grade"], "subject": project["project"]["subject"], "topic": topic}, workspace)
    official_sources = evidence.get("sources", [])
    private_sources = _source_documents(request, workspace, warnings)
    sources = official_sources + private_sources
    project["sources"] = sources
    project["source_snapshot"] = {
        "snapshot_id": evidence.get("snapshot_id", ""),
        "catalog_hash": evidence.get("catalog_hash", ""),
        "retrieved_at": evidence.get("retrieved_at", ""),
        "offline_fallback": False,
    }
    project["evidence_claims"] = [
        {
            "claim_id": f"CLM-{index:03d}",
            "text": clause.get("clause_text", ""),
            "provenance": [{"type": "OFFICIAL_STANDARD", "source_id": clause.get("source_id", ""), "clause_id": clause.get("clause_id", "")}],
            "status": "clause_candidate",
        }
        for index, clause in enumerate(evidence.get("matches", []), 1)
    ]
    project["needs_analysis"] = _build_needs_analysis(request)
    goal = _make_goal(request, sources, stage)
    performance_analysis = _build_performance_analysis(request, project["needs_analysis"], goal)
    goal["performance_analysis"] = performance_analysis
    goal["instructional_problem"] = performance_analysis["instructional_problem"]
    project["performance_analysis"] = performance_analysis
    project["performance_context"] = performance_analysis
    confirmations = _confirmation_map(request)
    if confirmations.get("curriculum_standard") and confirmations.get("instructional_goal"):
        goal["evidence_status"] = "teacher_confirmed"
        goal["status"] = "teacher_confirmed"
        goal["provenance_type"] = "TEACHER_INPUT"
        project["quality"]["evidence_status"] = "teacher_confirmed"
    elif official_sources:
        project["quality"]["evidence_status"] = "clause_candidate"
    else:
        project["quality"]["evidence_status"] = "no_source"
        warnings.append("没有条款级官方候选证据，教学目的只能作为待确认草案。")
    project["instructional_goal"] = goal
    project["goal"] = goal

    from tools.skill_graph import build_skill_graph, build_skill_graph_views, validate_skill_graph_views, classify_goal_type
    main_steps, subskills, entries = _topic_analysis(topic, project["project"]["grade"])
    graph = build_skill_graph(goal, main_steps, subskills, entries)
    # Keep both spellings while the historical engines are being migrated.
    graph["entry_behaviors"] = list(entries)
    graph["topic"] = topic
    graph["analysis_method"] = "程序分析 + 层次分析"
    graph["include_control_flow"] = _topic_kind(topic) in {"branch", "loop"}
    classification = classify_goal_type(goal)
    graph["goal_type"] = classification.get("goal_type", "mixed")
    graph["classification_rationale"] = classification.get("rationale", "")
    graph["view_validation"] = validate_skill_graph_views(build_skill_graph_views(graph))
    project["skill_graph"] = graph
    project["goal_analysis"] = {
        "analysis_method": graph["analysis_method"],
        "operation_flow": build_skill_graph_views(graph)["goal_operation_flow"],
        "skill_hierarchy": build_skill_graph_views(graph)["skill_hierarchy"],
        "teacher_confirmation_required": True,
    }
    project["skill_graphs"] = {"goal_operation_flow": project["goal_analysis"]["operation_flow"], "skill_hierarchy": project["goal_analysis"]["skill_hierarchy"], "raw": graph}

    from tools.learner_context import analyze_learner_profile
    class_profile = request.get("class_profile") or request.get("teacher_inputs", {}).get("class_profile") or {}
    learner_input = {
        "grade_level": project["project"]["grade"],
        "entry_skills": entries,
        "prior_knowledge": class_profile.get("prior_knowledge", "") if isinstance(class_profile, dict) else "",
        "motivation": class_profile.get("motivation", "") if isinstance(class_profile, dict) else "",
        "common_difficulties": class_profile.get("common_difficulties", request.get("common_difficulties", [])) if isinstance(class_profile, dict) else request.get("common_difficulties", []),
        "class_size": class_profile.get("class_size", "") if isinstance(class_profile, dict) else "",
        "ability_level": class_profile.get("ability_level", "") if isinstance(class_profile, dict) else "",
        "learning_preferences": class_profile.get("learning_preferences", []) if isinstance(class_profile, dict) else [],
    }
    learner_profile = analyze_learner_profile(learner_input)
    project["learner_context_input"] = learner_input
    project["learner_analysis"] = learner_profile
    project["context_analysis"] = {"learner": learner_profile, "learning_environment": request.get("learning_context", {}), "application_environment": request.get("application_context", "后续上机任务、单元项目或真实数字化问题")}

    objectives = _make_objectives(graph, request)
    project["performance_objectives"] = objectives
    project["objectives"] = objectives
    from tools.assessment_engine import generate_assessment_plan, validate_assessment_alignment
    assessment = generate_assessment_plan(objectives, project["context_analysis"])
    assessment["alignment"] = validate_assessment_alignment(objectives, assessment)
    topic_kind = _topic_kind(topic)
    if topic_kind in {"branch", "loop"}:
        assessment = _make_programming_assessment(objectives, topic_kind)
    project["assessments"] = assessment
    project["assessment_plan"] = assessment

    from tools.strategy_engine import generate_instructional_strategy
    strategy = generate_instructional_strategy(project)
    project["instructional_strategy"] = strategy
    project["instructional_sequence"] = strategy.get("lesson_flow", [])
    from tools.materials_engine import generate_instructional_materials
    materials = generate_instructional_materials(project)
    if topic_kind in {"branch", "loop"}:
        materials = _make_programming_materials(project, objectives, topic_kind)
    project["instructional_materials"] = materials
    project["materials"] = materials
    project["formative_evaluation"] = _build_formative_plan(materials, request)
    project["revision_plan"] = {"status": "待实施", "data_fields": project["formative_evaluation"]["data_gap"]}

    from tools.alignment_checker import check_full_alignment
    try:
        alignment = check_full_alignment(project)
    except Exception as exc:
        alignment = {"overall_status": "warning", "errors": [str(exc)]}
    # Keep the generic checker as migration diagnostics, then replace the
    # public v1 alignment report with scope-specific gates below.
    project["legacy_alignment_report"] = alignment
    project["quality"]["graph_validation"] = graph["view_validation"]
    project["quality"]["alignment_status"] = alignment.get("overall_status", "warning")
    project["decision_log"] = [{"decision_id": "DEC-001", "decision": "v1范围与模式已初始化", "status": "system_recorded", "source": "TEACHER_INPUT"}]
    project["ai_process"] = _build_ai_process_log(request, sources)

    required_keys = ["curriculum_standard", "textbook_unit", "instructional_goal", "entry_skills", "learner_context", "periods_equipment", "instructional_strategy"]
    required_confirmations = [
        {"confirmation_id": key, "question": {
            "curriculum_standard": "请确认当前检索到的课程标准和条款候选适用于本课题。",
            "textbook_unit": "请确认教材版本、单元位置以及商业教材内容只在本机使用。",
            "instructional_goal": "请确认教学目的候选及其应用情境。",
            "entry_skills": "请确认技能层级图中的入门技能边界。",
            "learner_context": "请确认班级共性学情和差异化需求。",
            "periods_equipment": "请确认课时、设备和软件环境。",
            "instructional_strategy": "请确认教学顺序、练习、分组和反馈策略。",
        }[key], "status": "confirmed" if confirmations.get(key) else "pending"}
        for key in required_keys
    ]
    project["required_confirmations"] = required_confirmations
    pending = [item for item in required_confirmations if item["status"] != "confirmed"]
    final_reasons = []
    if pending:
        final_reasons.append("仍有教师关键决策未确认")
    if project["quality"]["evidence_status"] not in {"teacher_confirmed", "final_verified"}:
        final_reasons.append("教学目的所用条款尚未完成教师确认")
    if graph["view_validation"]["status"] != "pass":
        final_reasons.append("技能图逻辑门禁未通过")
    from core.v1_quality import check_v1_alignment
    v1_alignment = check_v1_alignment(project)
    project["alignment_report"] = v1_alignment
    project["alignment_matrix"] = v1_alignment.get("alignment_matrix", [])
    project["quality"]["alignment_status"] = v1_alignment.get("overall_status", "warning")
    if v1_alignment.get("critical_issues"):
        final_reasons.extend(item.get("description", "v1 质量门禁未通过") for item in v1_alignment["critical_issues"])
    project["quality"]["draft_status"] = "final_ready" if not final_reasons else "draft_pending_confirmation"
    project["quality"]["can_export_final"] = not final_reasons
    project["quality"]["final_blocking_reasons"] = list(dict.fromkeys(final_reasons))
    export = _export_v1(project, output_dir, workspace)
    project["exports"] = {**project.get("exports", {}), **export}
    if export.get("export_status") != "success":
        final_reasons.append("导出包未通过完整文件门禁，不能标记为 final_ready")
        project["quality"]["can_export_final"] = False
        project["quality"]["draft_status"] = "draft_pending_confirmation"
        project["quality"]["final_blocking_reasons"] = list(dict.fromkeys(final_reasons))
    visual_status = export.get("visual_qa", {}).get("status", "unverified")
    project["quality"]["visual_status"] = visual_status
    if visual_status != "pass":
        final_reasons.append("Word/Draw.io 视觉质量门禁尚未通过，当前不能标记为 final_ready")
        project["quality"]["can_export_final"] = False
        project["quality"]["draft_status"] = "draft_pending_confirmation"
        project["quality"]["final_blocking_reasons"] = list(dict.fromkeys(final_reasons))
    project_path = project.get("exports", {}).get("project_json", "")
    if project_path:
        _write_json(Path(project_path), project)
    return {
        "status": "completed" if not final_reasons else "completed_with_warnings",
        "education_scope": EDUCATION_SCOPE,
        "mode": project["mode"],
        "project": project,
        "project_json": project_path,
        "sources": sources,
        "evidence_status": project["quality"]["evidence_status"],
        "required_confirmations": required_confirmations,
        "can_export_final": not final_reasons,
        "final_blocking_reasons": final_reasons,
        "warnings": warnings,
        "export_status": export.get("export_status"),
        "export": export,
        "export_result": export,
    }


def _load_project(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    path = Path(str(value or ""))
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def validate_v1_project(project: dict) -> dict:
    from tools.skill_graph import build_skill_graph_views, validate_skill_graph_views
    from core.v1_quality import check_v1_alignment
    errors: list[dict] = []
    if project.get("education_scope") != EDUCATION_SCOPE:
        errors.append({"type": "scope", "severity": "critical", "description": "项目不是 v1 K12 信息科技范围"})
    graph = project.get("skill_graph", {})
    graph_check = validate_skill_graph_views(build_skill_graph_views(graph))
    for message in graph_check.get("errors", []):
        errors.append({"type": "structural", "severity": "high", "description": message})
    if not project.get("instructional_goal") and not project.get("goal"):
        errors.append({"type": "completeness", "severity": "critical", "description": "缺少教学目的"})
    if not project.get("performance_objectives") and not project.get("objectives"):
        errors.append({"type": "completeness", "severity": "high", "description": "缺少绩效目标"})
    if not project.get("assessments") and not project.get("assessment_plan"):
        errors.append({"type": "completeness", "severity": "high", "description": "缺少评价方案"})
    quality_report = check_v1_alignment(project)
    for issue in quality_report.get("critical_issues", []):
        errors.append({
            "type": issue.get("gate", "quality"),
            "severity": issue.get("severity", "critical"),
            "description": issue.get("description", "v1 质量门禁未通过"),
            "evidence": issue.get("evidence", ""),
        })
    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "graph": graph_check,
        "quality": quality_report,
    }


def run_v1_review(project_or_path: Any, output_dir: str | None = None, workspace: str | None = None) -> dict:
    project = _load_project(project_or_path)
    validation = validate_v1_project(project)
    findings = []
    for index, error in enumerate(validation["errors"], 1):
        findings.append({
            "finding_id": f"F-{index:03d}",
            "type": error["type"],
            "severity": error["severity"],
            "description": error["description"],
            "evidence": "v1 project object and graph validator",
            "suggested_fix": "补齐或修正对应模块后重新运行 dc-info-tech-review",
            "affected_modules": ["project"],
            "related_quality_gate": "v1_content_and_graph_gate",
        })
    for issue in validation.get("quality", {}).get("warnings", []):
        findings.append({
            "finding_id": f"F-{len(findings) + 1:03d}",
            "type": issue.get("gate", "quality"),
            "severity": issue.get("severity", "warning"),
            "description": issue.get("description", "需要教师复核"),
            "evidence": issue.get("evidence", ""),
            "suggested_fix": "根据证据和教师实际情境补充、确认或修改对应模块",
            "affected_modules": [issue.get("gate", "project")],
            "related_quality_gate": issue.get("gate", "v1_quality_gate"),
        })
    export = _export_v1(project, output_dir, workspace) if output_dir else {"status": "not_requested"}
    return {"status": "completed_with_warnings" if findings else "completed", "findings": findings, "validation": validation, "export": export, "project_json": project.get("exports", {}).get("project_json", "")}


def run_v1_revise(project_or_path: Any, feedback: dict, output_dir: str | None = None, workspace: str | None = None) -> dict:
    project = _load_project(project_or_path)
    pre = validate_v1_project(project)
    feedback = feedback if isinstance(feedback, dict) else {"text": str(feedback)}
    items = feedback.get("items", [])
    if not isinstance(items, list):
        items = [items]
    impact_modules = set()
    proposed_changes = []
    applied_changes = []
    for item in items:
        if isinstance(item, str):
            item = {"description": item}
        if not isinstance(item, dict):
            continue
        module = str(item.get("module", item.get("affected_module", "project")))
        impact_modules.add(module)
        proposed_changes.append({"module": module, "description": item.get("description", item.get("change", ""))})
        # A change is applied only when the teacher explicitly marks it as
        # accepted. Plain feedback remains a proposal for the next turn.
        if not item.get("accepted") and not item.get("approved"):
            continue
        if module in {"instructional_goal", "goal"} and isinstance(item.get("patch"), dict):
            goal = project.setdefault("instructional_goal", project.get("goal", {}))
            for field in ("behavior", "context", "criterion", "tools"):
                if field in item["patch"]:
                    goal[field] = item["patch"][field]
            project["goal"] = goal
            applied_changes.append({"module": module, "patch": item["patch"]})
        elif module == "learner_context" and isinstance(item.get("patch"), dict):
            project.setdefault("learner_analysis", {}).update(item["patch"])
            applied_changes.append({"module": module, "patch": item["patch"]})
        elif module in {"instructional_strategy", "strategy"} and isinstance(item.get("patch"), dict):
            project.setdefault("instructional_strategy", {}).update(item["patch"])
            applied_changes.append({"module": module, "patch": item["patch"]})
        elif module in {"instructional_materials", "materials"} and isinstance(item.get("patch"), dict):
            project.setdefault("instructional_materials", {}).update(item["patch"])
            project["materials"] = project["instructional_materials"]
            applied_changes.append({"module": module, "patch": item["patch"]})
    entry = {
        "revision_id": f"REV-{len(project.get('decision_log', [])) + 1:03d}",
        "timestamp": now_iso(),
        "trigger": feedback.get("feedback_type", "teacher_feedback"),
        "feedback": feedback.get("items", feedback.get("text", feedback)),
        "impact_analysis": {
            "affected_modules": sorted(impact_modules),
            "pre_revision_alignment_status": pre.get("quality", {}).get("overall_status", "unknown"),
            "proposed_changes": proposed_changes,
        },
        "applied_changes": applied_changes,
        "action_status": "applied_with_recheck" if applied_changes else "proposed",
        "status": "applied_with_recheck" if applied_changes else "proposed",
        "requires_teacher_confirmation": not bool(applied_changes),
    }
    project.setdefault("decision_log", []).append(entry)
    project.setdefault("revision_plan", {})["latest_feedback"] = feedback
    project["quality"]["draft_status"] = "draft_pending_confirmation"
    post = validate_v1_project(project)
    project.setdefault("revision_log", []).append(entry)
    export = _export_v1(project, output_dir, workspace) if output_dir else {"status": "not_requested"}
    return {
        "status": "completed_with_warnings",
        "pre_revision_validation": pre,
        "post_revision_validation": post,
        "pre_revision_alignment": pre.get("quality", {}),
        "post_revision_alignment": post.get("quality", {}),
        "revision_record": entry,
        "unresolved_items": [] if applied_changes else ["教师尚未确认本轮修改是否采纳"],
        "requires_teacher_confirmation": not bool(applied_changes),
        "export": export,
    }
