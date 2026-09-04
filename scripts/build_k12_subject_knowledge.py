"""Build public metadata for the China K-12 nine-subject knowledge base.

Original PDFs remain in the private .dc-designer workspace. The public package
contains official metadata, hashes, short clause candidates, and normalized
subject-pack guidance only.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
STANDARDS_ROOT = REPO_ROOT / "data" / "standards"
K12_ROOT = STANDARDS_ROOT / "k12"
HIGH_ROOT = STANDARDS_ROOT / "high_school"

COMPULSORY_NOTICE_URL = (
    "https://www.moe.gov.cn/srcsite/A26/s8001/202204/"
    "t20220420_619921.html"
)
SENIOR_NOTICE_URL = (
    "https://www.moe.gov.cn/srcsite/A26/s8001/202006/"
    "t20200603_462199.html"
)
SENIOR_BUNDLE_URL = (
    "https://www.moe.gov.cn/srcsite/A26/s8001/202006/"
    "W020200603315372317586.zip"
)


COMMON = {
    "observable_verbs": [
        "识别",
        "描述",
        "解释",
        "比较",
        "分析",
        "评价",
        "设计",
        "修正",
        "反思",
    ],
    "common_misconceptions": [
        "把知识点记忆或最终答案当成完整学习证据",
        "把抽象的态度口号直接写成课堂绩效目标",
        "忽视任务条件、证据边界和学习者差异",
    ],
    "assessment_evidence_patterns": [
        "过程记录、口头表达、书面作品或操作结果",
        "基于资料、数据、文本或现象的解释与论证",
        "反馈后的二次修订及修订理由",
    ],
    "strategy_patterns": [
        "从真实或适龄的学科问题情境进入",
        "显性示范概念、方法、证据和检查过程",
        "安排形成性任务，让证据回流到策略和目标修订",
    ],
    "material_patterns": [
        "有来源说明的适龄文本、数据、图像或实验材料",
        "任务单、过程记录单和表现评价量表",
        "可编辑的课堂材料与教师确认记录",
    ],
    "formative_feedback_patterns": [
        "指出表现、证据和目标之间的具体差距",
        "把问题拆成概念、方法、表达和条件边界",
        "要求用二次作品或二次表达呈现反馈后的变化",
    ],
    "validation_rules": [
        "目标必须包含学科对象、可观察行为、条件和达成证据",
        "评价证据应与目标行为对应，不能只检查记忆或表态",
        "形成性评价结果必须能回流到教学策略、材料或目标修订",
    ],
}


SUBJECTS: dict[str, dict[str, Any]] = {
    "chinese": {
        "source_key": "chinese",
        "display_name": "语文",
        "compulsory_subject": "语文",
        "senior_subject": "语文",
        "aliases": ["语文", "中文"],
        "focus": "语言文字运用、阅读与鉴赏、表达与交流、梳理与探究",
        "core": ["语言运用", "思维能力", "审美创造", "文化自信"],
        "areas": [
            ["语言文字实践", "在真实语境中理解、表达、交流并修改。", ["阅读", "写作", "口语交际"]],
            ["文本理解与阐释", "依据文本证据形成有依据的理解、判断和阐释。", ["文本", "证据", "理解", "鉴赏"]],
            ["文化传承与表达", "在语言实践中理解文化意义并进行恰当表达。", ["文化", "传承", "表达"]],
        ],
        "verbs": ["朗读", "概括", "解释", "比较", "分析", "鉴赏", "表达", "修改", "评价"],
        "ethics": ["尊重文本版权，公开材料只使用必要短片段或官方链接。", "涉及个人经历和作品时避免公开学生身份信息。"],
        "compulsory_file": "chinese_compulsory_2022.pdf",
        "compulsory_file_name": "义务教育语文课程标准（2022年版）.pdf",
        "compulsory_url": "https://www.moe.gov.cn/srcsite/A26/s8001/202204/W020220420582344386456.pdf",
        "compulsory_sha256": "3ef0ec8a30b5a950211202658df07d99f5427f750f8ba0c3cfda12736b7bd71a",
        "senior_file_name": "普通高中语文课程标准（2017年版2020年修订）.pdf",
        "senior_sha256": "7a187079f1fffe8ae834fdeff25bac9dd0e7de6b979db40fd875786dc0365977",
    },
    "mathematics": {
        "source_key": "math",
        "display_name": "数学",
        "compulsory_subject": "数学",
        "senior_subject": "数学",
        "aliases": ["数学"],
        "focus": "数与代数、图形与几何、统计与概率、综合与实践",
        "core": ["抽象能力", "推理能力", "建模能力", "运算能力", "几何直观", "空间观念", "数据意识", "创新意识"],
        "areas": [
            ["概念与关系", "从数量、图形或数据情境中抽象出概念并解释关系。", ["概念", "关系", "表示"]],
            ["推理与论证", "用定义、性质、条件和过程支持结论。", ["推理", "证明", "条件", "结论"]],
            ["模型与问题解决", "把情境转化为数学模型，检验结果并解释边界。", ["建模", "问题解决", "检验", "解释"]],
            ["数据与图形表示", "选择恰当的图表、表示或运算工具表达信息。", ["数据", "统计", "图形", "表示"]],
        ],
        "verbs": ["识别", "表示", "计算", "估算", "推理", "证明", "建模", "解释", "检验", "比较", "反思"],
        "ethics": ["涉及真实数据时说明来源、范围和匿名化处理。", "工具输出应服务于解释，不把软件结果直接当作证明。"],
        "compulsory_file": "mathematics_compulsory_2022.pdf",
        "compulsory_file_name": "义务教育数学课程标准（2022年版）.pdf",
        "compulsory_url": "https://www.moe.gov.cn/srcsite/A26/s8001/202204/W020220510531636118932.pdf",
        "compulsory_sha256": "1183b95c58a65eaac4c456f2d2b329bbe42f65a6482993edb537e3eaf8baa144",
        "senior_file_name": "普通高中数学课程标准（2017年版2020年修订）.pdf",
        "senior_sha256": "cc4d3a20daa09f5185037e93fbacd58f7df1147392e3dae4bf261c3700ba4195",
    },
    "english": {
        "source_key": "english",
        "display_name": "英语",
        "compulsory_subject": "英语",
        "senior_subject": "英语",
        "aliases": ["英语", "英文"],
        "focus": "主题语境、语篇、语言知识、语言技能、跨文化沟通",
        "core": ["语言能力", "文化意识", "思维品质", "学习能力"],
        "areas": [
            ["主题与语篇", "围绕主题理解语篇结构、意义和表达目的。", ["主题", "语篇", "结构", "意义"]],
            ["语言知识与技能", "在语境中综合运用词汇、语法、语音和听说读写技能。", ["词汇", "语法", "语音", "听说读写"]],
            ["跨文化沟通", "理解文化差异并作出得体、负责任的交流表达。", ["文化", "沟通", "得体", "差异"]],
        ],
        "verbs": ["identify", "understand", "infer", "summarize", "compare", "interact", "describe", "write", "revise", "reflect"],
        "ethics": ["音视频和文本须确认授权范围。", "涉及人物、文化和身份时避免刻板化表述。"],
        "compulsory_file": "english_compulsory_2022.pdf",
        "compulsory_file_name": "义务教育英语课程标准（2022年版）.pdf",
        "compulsory_url": "https://www.moe.gov.cn/srcsite/A26/s8001/202204/W020220420582349487953.pdf",
        "compulsory_sha256": "59ec3971e0dbd6ca487c4e4972cbc80effaf2fd62418d07e5f62c6698fa222fb",
        "senior_file_name": "普通高中英语课程标准（2017年版2020年修订）.pdf",
        "senior_sha256": "8ebd6bb12e9eb1c58e422ee01b540a4a71d2e681a4c4a764a36ee3a34b21c1be",
    },
    "physics": {
        "source_key": "physics",
        "display_name": "物理",
        "compulsory_subject": "物理",
        "senior_subject": "物理",
        "aliases": ["物理"],
        "focus": "物质、运动与相互作用、能量、实验探究与模型",
        "core": ["物理观念", "科学思维", "科学探究", "科学态度与责任"],
        "areas": [
            ["现象与规律", "从可观察现象抽象出物理量、规律和适用条件。", ["现象", "规律", "物理量", "条件"]],
            ["模型与解释", "用模型、图像或方程解释现象并说明边界。", ["模型", "图像", "解释", "边界"]],
            ["实验与证据", "设计观察或实验，处理数据并依据证据修正结论。", ["实验", "变量", "数据", "证据"]],
        ],
        "verbs": ["观察", "测量", "描述", "建模", "预测", "实验", "记录", "处理", "解释", "论证", "修正"],
        "ethics": ["实验前明确器材、用电、热源和运动风险。", "不得用未经审查的高风险演示替代安全实验。"],
        "compulsory_file": "physics_compulsory_2022.pdf",
        "compulsory_file_name": "义务教育物理课程标准（2022年版）.pdf",
        "compulsory_url": "https://www.moe.gov.cn/srcsite/A26/s8001/202204/W020220420582357585169.pdf",
        "compulsory_sha256": "884069da6c924acb27b966ea20b9c7a4d8f0d6dfc828c80cd252aa72bf990340",
        "senior_file_name": "普通高中物理课程标准（2017年版2020年修订）.pdf",
        "senior_sha256": "a64204bc3b5532b44fbc82b560945d3df3c0bb081aa1d69df028a7591bb983f5",
    },
    "chemistry": {
        "source_key": "chemistry",
        "display_name": "化学",
        "compulsory_subject": "化学",
        "senior_subject": "化学",
        "aliases": ["化学"],
        "focus": "物质组成与结构、性质与变化、实验探究、化学与社会",
        "core": ["化学观念", "科学思维", "科学探究与实践", "科学态度与责任"],
        "areas": [
            ["组成、结构与性质", "联系微观结构、宏观性质和符号表示解释物质。", ["组成", "结构", "性质", "符号"]],
            ["变化与证据", "识别化学变化，依据现象和数据解释反应及其条件。", ["变化", "反应", "现象", "证据"]],
            ["实验与社会责任", "安全开展探究并联系资源、环境和生活问题作出判断。", ["实验", "安全", "环境", "责任"]],
        ],
        "verbs": ["辨认", "表示", "预测", "设计", "实验", "观察", "比较", "解释", "计算", "评价", "改进"],
        "ethics": ["实验方案必须经过教师安全审查。", "不得让学生自行尝试危险反应、未知混合物或不明来源试剂。"],
        "compulsory_file": "chemistry_compulsory_2022.pdf",
        "compulsory_file_name": "义务教育化学课程标准（2022年版）.pdf",
        "compulsory_url": "https://www.moe.gov.cn/srcsite/A26/s8001/202204/W020230605524874315398.pdf",
        "compulsory_sha256": "1ecd0cc391376ce76fb61a705f90ef804f746426c99f4813cc8367c0496851c6",
        "senior_file_name": "普通高中化学课程标准（2017年版2020年修订）.pdf",
        "senior_sha256": "589b296ef47fb3b221a08e616dcb8f19546ed9cf770bd5b5b991ba1d2008274f",
    },
    "biology": {
        "source_key": "biology",
        "display_name": "生物学",
        "compulsory_subject": "生物学",
        "senior_subject": "生物学",
        "aliases": ["生物", "生物学"],
        "focus": "生命结构与功能、遗传与进化、稳态与调节、生态系统、技术实践",
        "core": ["生命观念", "科学思维", "科学探究", "社会责任"],
        "areas": [
            ["结构与功能", "联系生物体结构层次与功能解释生命现象。", ["结构", "功能", "层次", "生命"]],
            ["生命活动与稳态", "解释生命活动、调节和健康之间的关系。", ["生命活动", "稳态", "调节", "健康"]],
            ["遗传、进化与多样性", "用证据认识遗传变异、进化和生物多样性。", ["遗传", "变异", "进化", "多样性"]],
            ["生态与责任", "分析生物与环境关系并提出可行的保护行动。", ["生态", "环境", "保护", "责任"]],
        ],
        "verbs": ["观察", "识别", "描述", "比较", "解释", "建模", "探究", "分析", "预测", "评价", "提出方案"],
        "ethics": ["涉及人体、动物、微生物和野外活动时遵守学校安全与伦理要求。", "不收集或公开可识别的健康和个人生物信息。"],
        "compulsory_file": "biology_compulsory_2022.pdf",
        "compulsory_file_name": "义务教育生物学课程标准（2022年版）.pdf",
        "compulsory_url": "https://www.moe.gov.cn/srcsite/A26/s8001/202204/W020220420582359998122.pdf",
        "compulsory_sha256": "95993bea87c30104631fa10f2f20f11b98d0718d69c4aeeac46c53a387f43c00",
        "senior_file_name": "普通高中生物学课程标准（2017年版2020年修订）.pdf",
        "senior_sha256": "8408986334a8826e6c7e1486c1ef1430cf47ad9e10174fd08f65d590f4d302a4",
    },
    "history": {
        "source_key": "history",
        "display_name": "历史",
        "compulsory_subject": "历史",
        "senior_subject": "历史",
        "aliases": ["历史"],
        "focus": "时序与空间、史料实证、历史解释、历史发展与现实联系",
        "core": ["唯物史观", "时空观念", "史料实证", "历史解释", "家国情怀"],
        "areas": [
            ["时空与变迁", "把历史事件放入时间、空间和发展过程理解。", ["时间", "空间", "变迁", "阶段"]],
            ["史料与证据", "辨析史料来源、内容和局限，形成有证据的判断。", ["史料", "证据", "来源", "局限"]],
            ["解释与比较", "从多种角度解释历史现象并比较异同与影响。", ["解释", "比较", "原因", "影响"]],
        ],
        "verbs": ["定位", "排序", "辨析", "提取", "比较", "解释", "论证", "评价", "联系", "反思"],
        "ethics": ["涉及战争、灾难、民族和身份议题时保持历史语境与尊重。", "公开案例避免个人隐私与未经核实的敏感叙述。"],
        "compulsory_file": "history_compulsory_2022.pdf",
        "compulsory_file_name": "义务教育历史课程标准（2022年版）.pdf",
        "compulsory_url": "https://www.moe.gov.cn/srcsite/A26/s8001/202204/W020220420582345700037.pdf",
        "compulsory_sha256": "c807b9162d7f7a652c9acedc187c39b28d29b73edfa9e6964045f9a8672a90ef",
        "senior_file_name": "普通高中历史课程标准（2017年版2020年修订）.pdf",
        "senior_sha256": "5906e55a4758c4446640db126564f535c845ba76df170714e739d97db6f36b97",
    },
    "geography": {
        "source_key": "geography",
        "display_name": "地理",
        "compulsory_subject": "地理",
        "senior_subject": "地理",
        "aliases": ["地理"],
        "focus": "地球与地图、自然环境、人文活动、区域发展、资源与环境",
        "core": ["人地协调观", "综合思维", "区域认知", "地理实践力"],
        "areas": [
            ["空间与尺度", "用地图、空间位置和尺度关系表达地理现象。", ["空间", "地图", "尺度", "位置"]],
            ["区域与联系", "在区域背景中分析自然、人文要素及其联系。", ["区域", "要素", "联系", "差异"]],
            ["资源环境与发展", "基于数据和情境判断资源、环境与发展方案。", ["资源", "环境", "发展", "可持续"]],
        ],
        "verbs": ["定位", "判读", "绘制", "描述", "比较", "分析", "解释", "评价", "调查", "提出方案"],
        "ethics": ["野外或实地调查须遵守学校审批、交通和环境安全要求。", "位置数据、影像和调查对象信息须脱敏。"],
        "compulsory_file": "geography_compulsory_2022.pdf",
        "compulsory_file_name": "义务教育地理课程标准（2022年版）.pdf",
        "compulsory_url": "https://www.moe.gov.cn/srcsite/A26/s8001/202204/W020220420582354066450.pdf",
        "compulsory_sha256": "5aade5cb5cfa103c48277c8ff663783df69cafb0fec2411f4aad1924d75c67b8",
        "senior_file_name": "普通高中地理课程标准（2017年版2020年修订）.pdf",
        "senior_sha256": "32ea1c9f794109cd729351fdba387c63f812f4f6131182a2370a0f5958fe7a3b",
    },
    "politics": {
        "source_key": "politics",
        "display_name": "道德与法治 / 思想政治",
        "compulsory_subject": "道德与法治",
        "senior_subject": "思想政治",
        "aliases": ["政治", "思想政治", "道德与法治"],
        "focus": "个人成长、道德与法律、社会参与、国家与公共生活",
        "core": ["政治认同", "科学精神", "法治意识", "公共参与"],
        "areas": [
            ["道德与法治生活", "在个人、家庭、学校和社会情境中理解规则、责任与权利。", ["道德", "法律", "规则", "责任", "权利"]],
            ["公共问题与判断", "基于事实、规则和价值边界分析公共生活问题。", ["公共问题", "事实", "判断", "价值"]],
            ["参与与行动", "把理解和判断转化为有边界、可实施的公共参与方案。", ["参与", "行动", "方案", "责任"]],
        ],
        "verbs": ["识别", "说明", "区分", "分析", "论证", "判断", "评价", "协商", "提出方案", "反思"],
        "ethics": ["政治、法律和价值议题须由教师核验表述与适龄性。", "不得收集或公开学生政治观点、家庭信息等敏感个人数据。"],
        "compulsory_file": "politics_compulsory_2022.pdf",
        "compulsory_file_name": "义务教育道德与法治课程标准（2022年版）.pdf",
        "compulsory_url": "https://www.moe.gov.cn/srcsite/A26/s8001/202204/W020220420582343475848.pdf",
        "compulsory_sha256": "16c0a291b522ce5b0afe3b1a28e696d8cca0d4d63cc01ff552a1d6ce06506cf0",
        "senior_file_name": "普通高中思想政治课程标准（2017年版2020年修订）.pdf",
        "senior_sha256": "28533adf1e2193c9b5de3056a6a031598209c2bfca00e65ff89458ecc4481f7b",
    },
}


SOURCE_IDS = {
    "compulsory": {
        subject_id: f"std_compulsory_2022_{subject['source_key']}"
        for subject_id, subject in SUBJECTS.items()
    },
    "senior_secondary": {
        subject_id: f"std_senior_2017_2020_{subject['source_key']}"
        for subject_id, subject in SUBJECTS.items()
    },
}


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _stage_meta(stage: str) -> dict[str, Any]:
    if stage == "compulsory":
        return {
            "label": "义务教育",
            "stage_labels": ["小学", "初中"],
            "grade_levels": ["小学1—6年级", "初中7—9年级"],
            "publication_date": "2022-04-20",
            "effective_date": "2022年秋季学期",
            "version": "2022",
        }
    return {
        "label": "普通高中",
        "stage_labels": ["普通高中"],
        "grade_levels": ["高中10—12年级"],
        "publication_date": "2020-06-03",
        "effective_date": "2020-06-03",
        "version": "2017年版2020年修订",
    }


def _source_id(subject: dict[str, Any], stage: str) -> str:
    prefix = "std_compulsory_2022_" if stage == "compulsory" else "std_senior_2017_2020_"
    return prefix + subject["source_key"]


def _subject_name(subject: dict[str, Any], stage: str) -> str:
    return subject["compulsory_subject"] if stage == "compulsory" else subject["senior_subject"]


def _source_name(subject: dict[str, Any], stage: str) -> str:
    meta = _stage_meta(stage)
    return f"{meta['label']}{_subject_name(subject, stage)}课程标准（{meta['version']}年版）" if stage == "compulsory" else f"{meta['label']}{_subject_name(subject, stage)}课程标准（{meta['version']}）"


def _source_file_name(subject: dict[str, Any], stage: str) -> str:
    return subject["compulsory_file_name"] if stage == "compulsory" else subject["senior_file_name"]


def _source_url(subject: dict[str, Any], stage: str) -> str:
    return subject["compulsory_url"] if stage == "compulsory" else SENIOR_BUNDLE_URL


def _source_hash(subject: dict[str, Any], stage: str) -> str:
    return subject["compulsory_sha256"] if stage == "compulsory" else subject["senior_sha256"]


def _private_reference(subject: dict[str, Any], stage: str) -> str:
    if stage == "compulsory":
        return f"private://official/v3/sources/{subject['compulsory_file']}"
    return f"private://official/v3/sources/senior_secondary_2017_2020_bundle.zip#{subject['senior_file_name']}"


def _clauses(subject_id: str, subject: dict[str, Any], stage: str) -> list[dict[str, Any]]:
    source_id = _source_id(subject, stage)
    version = _stage_meta(stage)["version"]
    rows = [
        ("课程性质与课程理念", "课程定位", f"明确{subject['display_name']}课程的育人价值、课程定位和设计方向。", ["课程性质", "课程理念", subject["display_name"]], ["needs_analysis", "instructional_goal", "strategy_design"]),
        ("课程目标与核心素养", "目标与核心素养", "把学科核心素养转化为可观察的学习表现候选，仍需结合课题、学情和教师确认。", subject["core"][:5], ["instructional_goal", "instructional_analysis", "assessment_generation"]),
        ("课程内容与结构", subject["focus"], f"以{subject['focus']}组织内容分析，并作为绩效目标、策略和材料的前置输入。", subject["focus"].split("、"), ["instructional_analysis", "strategy_design", "material_design"]),
        ("学业质量或学习质量", "质量表现", "将学习质量表述为证据要求，不直接替代单节课的教学目标。", ["学业质量", "学习表现", "证据"], ["instructional_goal", "assessment_generation", "formative_evaluation"]),
        ("教学实施与评价建议", "教学与评价", "提示教学、评价与资源协同，形成性证据应回流到后续修订。", ["教学", "评价", "形成性评价", "反馈"], ["strategy_design", "material_design", "formative_evaluation", "revision"]),
        ("学科重点校验", subject["focus"], f"围绕{subject['focus']}检查课堂任务、证据和交付物是否保持学科一致性。", subject["focus"].split("、"), ["instructional_analysis", "assessment_generation", "quality_ethics"]),
    ]
    result = []
    for number, (section, anchor, summary, keywords, modules) in enumerate(rows, start=1):
        result.append({
            "clause_id": f"{source_id.upper()}_{number:02d}",
            "section_path": [section],
            "page_number": "PDF 前置章节（OCR核验，需打开官方原文复核）",
            "anchor": anchor,
            "excerpt": anchor,
            "normalized_summary": summary,
            "keywords": list(dict.fromkeys(keywords)),
            "applicable_topics": ["all"],
            "supports_modules": modules,
            "evidence_status": "clause_candidate",
            "source_version": version,
            "source_id": source_id,
        })
    return result


def _record(subject_id: str, stage: str, retrieved_at: str) -> dict[str, Any]:
    subject = SUBJECTS[subject_id]
    meta = _stage_meta(stage)
    subject_name = _subject_name(subject, stage)
    source_id = _source_id(subject, stage)
    clauses = _clauses(subject_id, subject, stage)
    profile = copy.deepcopy(COMMON)
    profile["observable_verbs"] = subject["verbs"]
    profile["safety_or_ethics_rules"] = subject["ethics"]
    profile["concept_and_skill_patterns"] = [
        {"name": name, "summary": summary, "keywords": keywords}
        for name, summary, keywords in subject["areas"]
    ]
    keywords = list(dict.fromkeys(subject["aliases"] + subject["core"] + subject["focus"].split("、") + ["课程标准", "学业质量", "形成性评价", "Dick-Carey"]))
    record: dict[str, Any] = {
        "standard_id": source_id,
        "source_id": source_id,
        "knowledge_base_version": "3.0.0",
        "title": _source_name(subject, stage),
        "source_name": _source_name(subject, stage),
        "source_description": f"{meta['label']}{subject_name}课程标准的公开官方来源元数据和结构化设计候选。",
        "document_type": "curriculum_standard",
        "issuer": "中华人民共和国教育部",
        "publisher": "教育部",
        "authority": "中华人民共和国教育部",
        "publication_date": meta["publication_date"],
        "effective_date": meta["effective_date"],
        "version": meta["version"],
        "source_version": meta["version"],
        "status": "current",
        "stage": stage,
        "stage_labels": meta["stage_labels"],
        "grade_levels": meta["grade_levels"],
        "applicable_grades": meta["grade_levels"],
        "subject_id": subject_id,
        "subject": subject_name,
        "aliases": subject["aliases"],
        "source_level": "A1",
        "level": "A1",
        "source_category": "official_authority",
        "category": "curriculum_standard",
        "credibility": "highest",
        "can_be_goal_basis": "yes",
        "copyright_scope": "official_public_reference",
        "use_scope": ["goal_basis", "content_reference", "assessment_generation", "strategy_design"],
        "applicable_scenes": ["k12"],
        "source_url": _source_url(subject, stage),
        "source_file_name": _source_file_name(subject, stage),
        "source_bundle_url": SENIOR_BUNDLE_URL if stage == "senior_secondary" else "",
        "private_snapshot_reference": _private_reference(subject, stage),
        "content_sha256": _source_hash(subject, stage),
        "content_hash_status": "local_original_verified_not_packaged",
        "retrieved_at": retrieved_at,
        "metadata_snapshot_at": retrieved_at,
        "keywords": keywords,
        "core_competencies": subject["core"],
        "content_areas": [
            {
                "area_id": f"{subject_id}-{number:02d}",
                "name": name,
                "summary": summary,
                "keywords": area_keywords,
                "stage": stage,
            }
            for number, (name, summary, area_keywords) in enumerate(
                [("课程内容与任务", subject["focus"], subject["focus"].split("、"))] + subject["areas"],
                start=1,
            )
        ],
        "academic_quality_standards": [
            "学习表现应能通过任务、作品、表达、推理、实验、证据或行动观察。",
            "质量判断需要结合课题、学段、学情和课堂证据，不把学科标签直接当作目标。",
            "形成性评价结果应回流到教学策略、材料和目标修订。",
        ],
        **profile,
        "clauses": clauses,
        "specific_clauses": clauses,
        "extraction_evidence": {
            "method": "official_pdf_metadata_plus_intro_ocr",
            "verified_sections": ["封面与版本信息", "课程性质或基本理念", "课程目标与核心素养", "课程结构或内容框架", "学业质量或实施评价入口"],
            "verification_status": "metadata_and_section_structure_verified",
            "semantic_status": "clause_candidate_requires_teacher_confirmation",
            "note": "OCR 仅用于定位前置章节；生成具体课时目标前必须打开官方原文核对。",
        },
        "verification_status": "official_source_candidate",
        "verified_by_teacher": False,
        "teacher_confirmation_required": True,
        "is_test_fixture": False,
        "fallback_required": False,
        "notes": "原始 PDF 保存在本机私有知识库；公开包只发布元数据、哈希和结构化候选。",
    }
    record["source_record_sha256"] = _canonical_hash(record)
    return record


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _build_source_registry(records: list[dict[str, Any]], retrieved_at: str) -> dict[str, Any]:
    current = _load_json(STANDARDS_ROOT / "source_registry.json", {})
    existing = current.get("sources", []) if isinstance(current, dict) else []
    generated_ids = {record["source_id"] for record in records}
    legacy = []
    for item in existing:
        if not isinstance(item, dict) or item.get("source_id") in generated_ids:
            continue
        item = copy.deepcopy(item)
        file_path = str(item.get("file_path", ""))
        if re.match(r"^[A-Za-z]:[\\\\/]", file_path):
            item["file_path"] = ""
            item["source_status"] = "remote_metadata_only"
        item.setdefault("is_test_fixture", False)
        legacy.append(item)
    generated = []
    for record in records:
        generated.append({
            "source_id": record["source_id"],
            "title": record["title"],
            "level": record["source_level"],
            "category": "curriculum_standard",
            "stage": record["stage"],
            "version": record["version"],
            "subject": record["subject"],
            "file_path": "",
            "private_snapshot_reference": record["private_snapshot_reference"],
            "source_url": record["source_url"],
            "publisher": record["publisher"],
            "description": record["source_description"],
            "applicable_grades": record["grade_levels"],
            "copyright_scope": "official_public_reference",
            "use_scope": record["use_scope"],
            "content_sha256": record["content_sha256"],
            "content_hash_status": record["content_hash_status"],
            "retrieved_at": retrieved_at,
            "is_test_fixture": False,
        })
    return {
        "registry_version": "3.0",
        "last_updated": retrieved_at[:10],
        "scope": "中国 K-12 九学科（小学、初中、普通高中；不含职高和高等教育）",
        "source_policy": "官方教育部来源优先；公开包不复制完整课标，教师确认前条款只作为候选。",
        "sources": legacy + generated,
    }


def _build_subject_registry(records: list[dict[str, Any]], retrieved_at: str) -> dict[str, Any]:
    by_id = {record["source_id"]: record for record in records}
    subjects = []
    for subject_id, subject in SUBJECTS.items():
        compulsory = by_id[SOURCE_IDS["compulsory"][subject_id]]
        senior = by_id[SOURCE_IDS["senior_secondary"][subject_id]]
        adapter = copy.deepcopy(COMMON)
        adapter["observable_verbs"] = subject["verbs"]
        adapter["safety_or_ethics_rules"] = subject["ethics"]
        adapter["concept_and_skill_patterns"] = [
            {"name": name, "summary": summary, "keywords": keywords}
            for name, summary, keywords in subject["areas"]
        ]
        adapter.update({
            "subject_id": subject_id,
            "display_name": subject["display_name"],
            "terminology_aliases": subject["aliases"],
            "stage_rules": {
                "compulsory": {
                    "display_name": subject["compulsory_subject"],
                    "labels": ["小学", "初中"],
                    "grade_levels": _stage_meta("compulsory")["grade_levels"],
                    "source_id": compulsory["source_id"],
                },
                "senior_secondary": {
                    "display_name": subject["senior_subject"],
                    "labels": ["普通高中"],
                    "grade_levels": _stage_meta("senior_secondary")["grade_levels"],
                    "source_id": senior["source_id"],
                },
            },
            "official_source_ids": {
                "compulsory": compulsory["source_id"],
                "senior_secondary": senior["source_id"],
            },
            "source_boundary": {
                "national_baseline": True,
                "local_sources_optional": True,
                "textbook_full_text_public": False,
                "teacher_confirmation_required": True,
            },
            "generated_at": retrieved_at,
        })
        subjects.append(adapter)
    return {
        "registry_version": "3.0.0",
        "generated_at": retrieved_at,
        "scope": {
            "education": "中国 K-12",
            "stages": ["小学", "初中", "普通高中"],
            "subjects": list(SUBJECTS),
            "excluded": ["职高", "中等职业教育", "高等教育"],
        },
        "contract": [
            "subject_id",
            "stage_rules",
            "official_source_ids",
            "core_competencies",
            "concept_and_skill_patterns",
            "observable_verbs",
            "common_misconceptions",
            "assessment_evidence_patterns",
            "strategy_patterns",
            "material_patterns",
            "formative_feedback_patterns",
            "safety_or_ethics_rules",
            "terminology_aliases",
            "validation_rules",
        ],
        "subjects": subjects,
    }


def _update_official_snapshot(records: list[dict[str, Any]], retrieved_at: str) -> None:
    path = K12_ROOT / "official_snapshot.json"
    snapshot = _load_json(path, {})
    existing = snapshot.get("sources", []) if isinstance(snapshot, dict) else []
    generated_ids = {record["source_id"] for record in records}
    preserved = []
    for item in existing:
        if not isinstance(item, dict) or item.get("source_id") in generated_ids:
            continue
        item = copy.deepcopy(item)
        file_path = str(item.get("file_path", ""))
        if re.match(r"^[A-Za-z]:[\\\\/]", file_path):
            item["file_path"] = ""
            item["source_status"] = "remote_metadata_only"
        preserved.append(item)
    _write_json(path, {
        "snapshot_id": "k12-multisubject-official-2026-09",
        "snapshot_version": "3.0.0",
        "generated_at": retrieved_at,
        "content_hash_policy": "公开包只保存官方来源元数据、内容哈希和短条款候选；原始 PDF 保存在本机私有知识库，教师确认前不升级为最终证据。",
        "source_record_fields": [
            "source_id", "title", "issuer", "document_type", "publication_date",
            "effective_date", "version", "source_url", "stage", "subject",
            "source_level", "source_category", "copyright_scope", "use_scope",
            "clauses", "content_hash_status", "content_sha256",
            "source_record_sha256", "grade_levels", "retrieved_at",
            "metadata_snapshot_at",
        ],
        "description": "中国 K-12 九学科官方课程标准元数据快照，覆盖小学、初中和普通高中。不复制完整课标、商业教材、教师私有资料或学生数据。",
        "sources": preserved + records,
    })


def build(retrieved_at: str) -> dict[str, Any]:
    records = [
        _record(subject_id, stage, retrieved_at)
        for stage in ("compulsory", "senior_secondary")
        for subject_id in SUBJECTS
    ]
    for record in records:
        root = K12_ROOT if record["stage"] == "compulsory" else HIGH_ROOT
        filename = (
            f"{record['subject_id']}_compulsory_2022.json"
            if record["stage"] == "compulsory"
            else f"{record['subject_id']}_2017_2020.json"
        )
        _write_json(root / filename, record)
    _write_json(STANDARDS_ROOT / "source_registry.json", _build_source_registry(records, retrieved_at))
    _write_json(STANDARDS_ROOT / "subject_registry_v3.json", _build_subject_registry(records, retrieved_at))
    _update_official_snapshot(records, retrieved_at)
    return {
        "generated_at": retrieved_at,
        "subject_count": len(SUBJECTS),
        "record_count": len(records),
        "source_registry": str(STANDARDS_ROOT / "source_registry.json"),
        "subject_registry": str(STANDARDS_ROOT / "subject_registry_v3.json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 K-12 九学科课标知识库元数据")
    parser.add_argument("--date", default="2026-09-04", help="快照日期 YYYY-MM-DD")
    args = parser.parse_args()
    date.fromisoformat(args.date)
    print(json.dumps(build(args.date), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
