"""
Context analysis rules and strategy implication templates.
Defines constraint rules, implication templates, topic strategies,
ARCS motivation strategies, and grouping strategies.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Learning context constraint rules
CONSTRAINT_RULES = {
    "short_duration": {
        "threshold": 30,
        "implication": "课时较短，需精简内容，聚焦核心目标",
    },
    "large_class": {
        "threshold": 40,
        "implication": "班级人数较多，需设计全班互动和小组活动",
    },
    "no_individual_devices": {
        "keywords": ["不保证一人一机", "无计算机", "设备不足"],
        "implication": "无法进行个人计算机操作练习，需使用替代活动",
    },
    "unstable_network": {
        "keywords": ["网络不稳定", "无网络"],
        "implication": "不适合在线资源依赖型教学",
    },
}

# Strategy implication templates by context dimension
IMPLICATION_TEMPLATES = {
    "entry_skills_weak": "入门技能薄弱，教学前需增加预备知识激活和复习环节",
    "motivation_low": "学习动机较低，需在教学前活动和内容呈现中加强情境导入和关联性设计",
    "motivation_high": "学习者对主题有兴趣，可利用情境任务和问题驱动维持动机",
    "common_difficulties": "学习者常见困难包括{difficulties}，教学中需针对性设计突破策略",
    "short_class": "课时{duration}分钟，需合理分配时间，每环节不超过{max_minutes}分钟",
    "no_devices": "设备条件有限，优先使用黑板、学习单、纸质流程图等低成本材料",
    "transfer_low_similarity": "学习环境与应用环境差异较大，需加强迁移活动设计",
}

# Topic-specific strategy templates
TOPIC_STRATEGY_TEMPLATES = {
    "algorithm": {
        "pre_instructional": {
            "motivation": "从生活中的做事步骤（如泡牛奶、整理书包）引入，激发学生对“步骤化描述”的兴趣",
            "objectives_overview": "告诉学生本节课将学习用自然语言和流程图描述算法",
            "entry_skill_activation": "让学生回忆日常生活中做事的步骤，用顺序词描述",
        },
        "content_presentation": [
            {
                "phase": "对比导入",
                "duration": 5,
                "activity": "展示两组步骤（清晰vs混乱），让学生判断哪组更好",
            },
            {
                "phase": "概念讲解",
                "duration": 7,
                "activity": "讲解算法的基本特征：明确、有限、有序",
            },
            {
                "phase": "范例演示",
                "duration": 4,
                "activity": "教师示范用自然语言描述一个简单问题的算法",
            },
        ],
        "learner_participation": [
            {
                "phase": "小组任务",
                "duration": 10,
                "activity": "选择校园生活问题，小组合作写出算法步骤",
            },
            {
                "phase": "互评修改",
                "duration": 6,
                "activity": "小组间互评，检查步骤缺漏、重复、顺序错误",
            },
        ],
        "follow_through": {
            "memory_support": [
                "提供算法检查清单（明确、完整、有序）",
                "使用顺序词模板辅助记忆",
            ],
            "transfer_tasks": [
                "课后用算法描述一个家庭生活任务",
                "预习流程图绘制方法",
            ],
        },
    },
    "branch": {
        "pre_instructional": {
            "motivation": "从成绩分级、交通信号或游戏规则等多种情况的判断任务导入，比较人工判断与程序判断。",
            "objectives_overview": "说明本课将把判断规则转化为 if-elif-else 分支程序，并通过测试和调试验证逻辑。",
            "entry_skill_activation": "用条件—结果表复习比较关系、顺序程序和 Python 缩进。",
        },
        "content_presentation": [
            {"phase": "情境建模", "duration": 7, "activity": "将多种输入情况整理为条件—输出对应表，识别边界值和互斥关系。"},
            {"phase": "框架示范", "duration": 8, "activity": "教师逐步示范 if、elif、else 的语法结构、缩进和分支顺序。"},
            {"phase": "条件表达式示范", "duration": 7, "activity": "将自然语言判断规则改写为比较/逻辑表达式，并讨论覆盖范围。"},
        ],
        "learner_participation": [
            {"phase": "代码补全", "duration": 10, "activity": "学生根据条件—输出表补全分支代码并在 VSCode 运行。"},
            {"phase": "测试互查", "duration": 8, "activity": "用正常值、边界值和异常值测试程序，记录实际与预期输出并互相定位错误。"},
        ],
        "follow_through": {
            "memory_support": ["提供 if-elif-else 结构速查卡", "使用条件—表达式—输出三列表格检查逻辑"],
            "transfer_tasks": ["将一个生活分类规则改写为 Python 分支程序", "为程序补充边界值测试并说明理由"],
        },
    },
    "loop": {
        "pre_instructional": {
            "motivation": "从批量处理名单、重复绘图或统计数据的任务导入，体验重复操作的低效。",
            "objectives_overview": "说明本课将识别重复模式，编写循环体，并用测试数据验证循环次数和退出逻辑。",
            "entry_skill_activation": "复习变量、赋值、顺序执行和输出，明确重复操作与一次操作的区别。",
        },
        "content_presentation": [
            {"phase": "重复模式建模", "duration": 7, "activity": "从任务描述中标出重复操作、循环变量、范围和终止条件。"},
            {"phase": "循环框架示范", "duration": 8, "activity": "教师示范 for/while 基本结构、缩进、循环变量更新和执行轨迹。"},
            {"phase": "控制语句示范", "duration": 7, "activity": "比较 continue、break 和正常循环结束，分析各自适用情境。"},
        ],
        "learner_participation": [
            {"phase": "代码补全", "duration": 10, "activity": "学生根据循环轨迹表补全循环程序并运行观察输出。"},
            {"phase": "测试互查", "duration": 8, "activity": "用零次、一次、边界次数和较大次数测试，互查终止条件和缩进。"},
        ],
        "follow_through": {
            "memory_support": ["提供循环框架和循环变量检查清单", "用执行轨迹表辅助解释每一轮状态"],
            "transfer_tasks": ["为一个批量处理任务选择 for 或 while 并说明理由", "设计能暴露无限循环风险的测试数据"],
        },
    },
}

# ARCS motivation strategies
ARCS_STRATEGIES = {
    "attention": ["对比导入", "生活情境", "问题悬念", "多媒体展示"],
    "relevance": ["联系生活实际", "关联已有经验", "展示实用价值"],
    "confidence": ["分层任务", "成功体验", "即时反馈"],
    "satisfaction": ["成果展示", "同伴认可", "自我评价"],
}

# Grouping strategies
GROUPING_STRATEGIES = {
    "individual": "个别学习",
    "pairs": "结对学习",
    "small_group": "小组协作（3-5人）",
    "whole_class": "全班讨论",
    "mixed": "混合分组",
}
