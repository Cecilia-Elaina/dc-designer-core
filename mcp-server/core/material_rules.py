"""
Material rules for dc-designer-core.
Defines what materials are needed, formats, and topic-specific content.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Material types that should be generated
MATERIAL_TYPES = [
    "teacher_guide",
    "student_worksheet",
    "entry_test_sheet",
    "pretest_sheet",
    "group_task_sheet",
    "peer_review_checklist",
    "posttest_sheet",
    "board_design",
    "simple_lesson_plan",
]

# Format rules based on environment constraints
FORMAT_RULES = {
    "no_devices": {
        "preferred": ["paper_worksheet", "blackboard", "projector"],
        "avoid": ["online_quiz", "computer_activity", "tablet_worksheet"],
        "note": "设备不足时优先使用纸质学习单和板书"
    },
    "unstable_network": {
        "preferred": ["paper_worksheet", "blackboard"],
        "avoid": ["online_resource", "web_based_activity"],
        "note": "网络不稳定时避免依赖在线资源"
    },
    "limited_time": {
        "preferred": ["compact_worksheet", "quick_check"],
        "avoid": ["extended_project", "research_activity"],
        "note": "课时较短时使用紧凑型材料"
    },
}

# Topic-specific content templates
TOPIC_MATERIALS = {
    "algorithm": {
        "teacher_guide_sections": [
            "教学目的与目标",
            "学情提醒",
            "45分钟教学流程",
            "每个环节教师行动与话术",
            "提问点与反馈点",
            "时间控制提醒",
            "常见问题与应对"
        ],
        "student_worksheet_tasks": [
            {"task": "我会按顺序描述生活任务", "type": "导入"},
            {"task": "比较两组步骤，判断哪组更清晰", "type": "前测"},
            {"task": "认识算法的三个特征：明确、有限、有序", "type": "概念学习"},
            {"task": "小组合作写一个校园生活问题的算法步骤", "type": "小组任务"},
            {"task": "用检查清单修改算法步骤", "type": "互评修改"},
            {"task": "独立完成一个新情境的算法描述", "type": "后测"},
        ],
        "peer_review_items": [
            "问题目标是否明确",
            "步骤是否按顺序排列",
            "每一步是否具体明确",
            "是否有遗漏步骤",
            "是否有重复步骤",
            "是否能在有限步骤内完成",
            "能否用自然语言清晰表达",
        ],
        "board_design_structure": [
            {"section": "标题", "content": "认识算法"},
            {"section": "定义", "content": "解决问题的一组明确、有限、有序的步骤"},
            {"section": "三个特点", "content": "1.明确：每一步说清楚\n2.有限：能在有限步骤内完成\n3.有序：步骤先后合理"},
            {"section": "描述模板", "content": "先……\n再……\n然后……\n最后……"},
            {"section": "检查清单", "content": "目标清楚了吗？\n步骤完整吗？\n顺序合理吗？\n有没有遗漏或重复？"},
        ],
    }
    ,"branch": {
        "teacher_guide_sections": ["课标与目的依据", "条件—输出建模", "if-elif-else 示范", "测试与调试流程", "分层支持与反馈"],
        "student_worksheet_tasks": [
            {"task": "从任务描述中提取条件、输出和边界值", "type": "任务分析"},
            {"task": "把条件—输出表翻译成 if-elif-else 框架", "type": "框架练习"},
            {"task": "用比较运算符和逻辑运算符编写条件表达式", "type": "表达式练习"},
            {"task": "运行程序并使用正常值、边界值测试各分支", "type": "测试任务"},
            {"task": "根据错误输出定位、修改并重新测试代码", "type": "调试任务"},
            {"task": "独立完成一个新的多路分类程序", "type": "迁移任务"}
        ],
        "peer_review_items": ["条件是否覆盖题目要求", "分支顺序是否合理", "比较和逻辑运算符是否准确", "缩进和语法是否正确", "是否测试各分支和边界值", "实际输出是否符合预期", "是否能说明修改理由"],
        "board_design_structure": [
            {"section": "标题", "content": "Python 分支结构：条件判断、多路选择、条件筛选"},
            {"section": "任务分析", "content": "条件 → 判断 → 输出；先列条件—输出表，再写代码"},
            {"section": "基本框架", "content": "if 条件:\n    执行语句\nelif 条件:\n    执行语句\nelse:\n    执行语句"},
            {"section": "测试清单", "content": "每个分支？边界值？异常值？实际输出与预期一致？"}
        ]
    },
    "loop": {
        "teacher_guide_sections": ["重复任务建模", "for/while 框架示范", "循环体与控制语句", "执行轨迹和测试", "调试反馈"],
        "student_worksheet_tasks": [
            {"task": "圈出任务中的重复操作并确定循环变量", "type": "任务分析"},
            {"task": "根据执行轨迹表补全 for/while 循环框架", "type": "框架练习"},
            {"task": "编写循环体并观察每一轮状态变化", "type": "循环体练习"},
            {"task": "使用 continue 或 break 实现跳过和退出", "type": "控制语句"},
            {"task": "用边界次数和终止条件测试程序", "type": "测试调试"},
            {"task": "独立完成一个批量处理任务", "type": "迁移任务"}
        ],
        "peer_review_items": ["重复模式识别是否准确", "循环变量和范围是否明确", "循环体缩进是否正确", "终止条件是否有效", "是否测试零次/一次/边界次数", "是否避免无限循环", "能否解释控制语句"],
        "board_design_structure": [
            {"section": "标题", "content": "Python 循环结构：筛选、跳过、退出"},
            {"section": "任务分析", "content": "重复操作 → 循环变量 → 范围/终止条件 → 循环体"},
            {"section": "控制语句", "content": "continue：跳过本轮；break：退出循环；自然结束：条件不再满足"},
            {"section": "测试清单", "content": "零次？一次？边界次数？终止？输出与预期一致？"}
        ]
    }
}
