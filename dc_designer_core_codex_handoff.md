# dc-designer-core 项目交接文档：给 Codex 的完整审查与继续开发说明

> 本文用于把当前 ChatGPT 会话中的全部关键上下文交给 Codex。Codex 的任务不是从零理解项目，而是直接进入仓库，读取文件，审查 Claude Code 的产物，判断是否通过阶段验收，并在必要时给出/执行修复。
>
> 当前项目名称：`dc-designer-core`  
> 当前定位：面向智能体的 Dick-Carey 教学系统设计插件内核  
> 当前阶段：Phase 5 已尝试完成，但审查未通过；下一步应执行 Phase 5.1：教学材料包最终导出与测试修复。

---

## 0. Codex 的角色

你现在接手的是一个持续迭代项目。之前的工作方式是：

1. 用户让 Claude Code 按阶段实现功能；
2. Claude Code 输出变更报告和测试结果；
3. ChatGPT 审查实际产物，而不是只相信 Claude Code 的文字报告；
4. 若通过，进入下一阶段；若不通过，给出小阶段修复指令。

你现在要延续这个角色：

- 不要只看 Claude Code 的“完成报告”；
- 必须打开仓库文件和 exports 输出文件审查；
- 必须以最终 JSON、Markdown、测试文件、pipeline 输出为准；
- 如果发现“代码写了但没有进入最终产物”，判定为不通过；
- 如果测试过于宽松，必须指出并修复；
- 不要一次跨太多阶段；
- 每一阶段必须有明确验收条件。

---

## 1. 项目总目标

`dc-designer-core` 是一个专业的 Dick & Carey 教学系统化设计助手/插件内核，不是普通教案生成器。

它要帮助教师或培训设计者按照 Dick-Carey 模型完成完整的教学系统设计，包括：

1. 需求评估与教学目的；
2. 教学目的类型分类；
3. 教学分析/技能流图；
4. 从属技能与入门技能；
5. 学习者与环境分析；
6. 绩效目标；
7. 评价方案；
8. 教学策略；
9. 教学材料；
10. 形成性评价；
11. 修订；
12. 最终导出报告与材料包。

核心理念：

```text
不是“帮老师写一份教案”，
而是“帮助老师完成一套可追溯、可评价、可修订的 Dick-Carey 教学系统设计”。
```

---

## 2. 项目不可违反的原则

以下规则一直作为质量门禁存在：

```text
1. 没有教学目的，不得生成教学策略。
2. 没有绩效目标，不得生成评价方案。
3. 没有学习者和环境分析，不得生成最终教学策略。
4. K12 场景缺少官方/教材/教师来源依据时，只能标记为“待验证草案”。
5. 形成性评价数据必须能反馈到目标、评价、策略、材料的修订。
6. AI 推断不能伪装成官方依据。
7. 教师上传资料只能作为私有分析依据，不得公开再发布版权内容原文。
8. 最终报告必须区分：教师输入、官方来源、教师上传资料、AI 推断。
9. 单元测试通过不等于阶段通过；必须看最终导出 JSON/Markdown。
```

---

## 3. K12 来源依据规则

K12 场景特别严格。来源优先级：

```text
1. 国家课程标准
2. 省级教学指导意见
3. 教材版本与单元内容
4. 高考/中考评价要求
5. 教师已有材料
6. 班级学情
7. 最终教学目的和绩效目标
```

K12 课标版本规则：

```text
小学/初中 → 义务教育课程标准 2022年版
普通高中 → 普通高中课程标准 2017年版2020年修订
高中考试导向课 → 高中课标 + 中国高考评价体系 + 近年真题分析
```

来源等级：

```text
S/A：教育部、教育部考试院、中国教育考试网、省级教育厅/考试院等官方来源
B：官方教材出版社、国家智慧教育平台等
C：教师上传资料、学校材料、教研组材料、教师经验
D/E：普通网页、公号、AI 推断等，只能作为灵感，不能作为 K12 final 目标依据
```

搜索失败时应返回类似：

```json
{
  "status": "not_found",
  "confidence": 0,
  "message": "未检索到可验证的官方课标或政策来源。",
  "next_action": [
    "请教师上传课程标准 PDF",
    "请教师提供教材目录或截图",
    "请教师确认学校使用的课程标准版本",
    "暂时将目标标记为待验证"
  ]
}
```

---

## 4. 当前项目架构概况

目标仓库大致结构：

```text
dc-designer-core/
├── README.md
├── AGENTS.md
├── manifest.json
├── .claude-plugin/plugin.json
├── .mcp.json
├── skills/
│   ├── dc-design/SKILL.md
│   ├── dc-review/SKILL.md
│   ├── dc-revise/SKILL.md
│   ├── dc-k12/SKILL.md
│   ├── dc-higher-ed/SKILL.md
│   └── dc-corporate-training/SKILL.md
├── canon/
│   ├── dick-carey-model-spec.md
│   ├── module-io-spec.md
│   ├── quality-gates.md
│   ├── alignment-rules.md
│   ├── source-reliability-policy.md
│   ├── teacher-memory-policy.md
│   └── anti-patterns.md
├── schemas/
├── mcp-server/
│   ├── core/
│   └── tools/
├── templates/
├── data/
├── examples/
├── exports/
└── tests/
```

重要 MCP/tools 模块已经逐步出现：

```text
mcp-server/tools/goal_engine.py
mcp-server/tools/skill_graph.py
mcp-server/tools/objective_engine.py
mcp-server/tools/assessment_engine.py
mcp-server/tools/standards_search.py
mcp-server/tools/knowledge_ingest.py
mcp-server/tools/curriculum_mapper.py
mcp-server/tools/learner_context.py
mcp-server/tools/strategy_engine.py
mcp-server/tools/materials_engine.py
mcp-server/tools/pipeline.py
mcp-server/tools/alignment_checker.py
mcp-server/tools/export_package.py

mcp-server/core/source_reliability.py
mcp-server/core/source_normalizer.py
mcp-server/core/report_renderer.py
mcp-server/core/context_rules.py
mcp-server/core/strategy_rules.py
mcp-server/core/material_rules.py
mcp-server/core/material_alignment.py
```

---

## 5. 已完成阶段回顾

### Phase 0/1：项目骨架与规范

已建立基础项目结构、canon 文件、schemas、skills、MCP tools 空接口。

审查曾发现并要求修复：

- 补 `.claude-plugin/plugin.json`；
- 补 `.mcp.json`；
- K12 版本规则；
- 来源 schema；
- “评价证据”而不是只说“评价题”；
- 加入形成性评价后的“修改教学”；
- 移除不准确术语。

已通过。

---

### Phase 2：MVP 核心引擎

目标：

```text
输入项目种子
→ 生成教学目的
→ 教学分析/技能流图
→ 绩效目标
→ 评价方案
→ 一致性检查
→ Markdown 报告
```

测试案例：七年级信息科技《认识算法》。

经历 Phase 2.1/2.2 修复后，已解决：

- K12 无官方来源时不能 final；
- 算法主题技能图不能泛化；
- 弱动词“理解/掌握/了解”要被替换或提示；
- 评价方案要有入门测试、前测、练习/模拟、后测；
- 报告不能一边说待验证，一边说可导出最终版；
- 目标-技能匹配警告残留问题。

Phase 2 已通过。

---

### Phase 3：K12 来源依据与教师知识库 MVP

目标：

```text
standards_search
knowledge_ingest
source_reliability
curriculum_mapper
source trace
```

Phase 3 初次完成后发现严重问题：只找到 A1 级课标文件，就把目标升级为 verified/final，但没有具体条款；goal 对象嵌套旧状态；sources 重复冲突。

Phase 3.1 修复后通过：

K12 目标验证状态分为：

```text
no_source → draft_unverified
teacher_limited → draft_pending_verification
standard_file_found → source_found_pending_clause_alignment
standard_clause_aligned → verified_candidate
final_verified → 教师确认后的最终验证
```

要求：

- 只有文件级课标不能 final；
- specific_clauses 为空不能 verified_candidate；
- test fixture 永远不能 final；
- goal 内不能再嵌套旧 goal；
- sources 要去重合并。

Phase 3.1 已通过。

---

### Phase 4：学习者与环境分析 + 教学策略

目标：

```text
context_analysis
instructional_strategy
45分钟教学流程
策略-目标-评价-环境一致性检查
```

Phase 4 初次完成后，报告显示：

- 学习者分析为空；
- 教学策略为空；
- 课堂流程表空白；
- 一致性检查显示 0 个学习成分、11 个目标未覆盖。

判定：模块测试通过，但没有接入主流水线。

Phase 4.1 修复 pipeline 和字段映射后，学习者分析和教学策略进入报告。

Phase 4.2 又修复：

- 策略 quality_check 内外不一致；
- 45分钟流程变成 49分钟；
- 流程表目标列为空；
- 设计启示重复。

Phase 4.2 通过。

当前策略报告已能显示：

- 学习者特征；
- 学习环境；
- 应用环境；
- 设计启示；
- 教学前活动；
- 内容呈现；
- 学习者参与；
- 评估；
- 总结迁移；
- 0-45分钟课堂流程；
- 目标 ID 映射；
- 策略质量 100 分。

注意：当前报告仍然是待验证草案，因为 sources 为空，这是正确的，不影响开发后续模块。

---

## 6. 当前 Phase 5 审查结论：未通过

Claude Code 宣称 Phase 5 完成：新增 `materials_engine.py`、`material_rules.py`、`material_alignment.py`，生成 9 类教学材料，测试 181 OK。

但实际审查发现：**Phase 5 没有通过。**

原因：

### 6.1 最终 full JSON 不是 materials 版本

期望产物：

```text
exports/mvp_algorithm_project_with_materials_full.json
```

实际上传/看到的仍是：

```text
mvp_algorithm_project_with_strategy_full(2).json
```

这个文件主要仍是策略阶段项目。审查时没有可靠看到顶层完整的：

```json
"instructional_materials": {...},
"material_alignment": {...}
```

也就是说，材料生成可能在函数中存在，但未成为 Phase 5 的最终项目产物。

### 6.2 Markdown 报告不是 materials 版本

期望产物：

```text
exports/mvp_algorithm_report_with_materials.md
```

实际上传/看到的仍是：

```text
mvp_algorithm_report_with_strategy(2).md
```

这个报告主要显示来源、目标、学习者分析、教学策略、绩效目标、评价方案等，没有看到它声称的：

```text
Section 14 教学材料包
14.1 教师授课手册
14.2 学生学习单
...
14.10 材料一致性检查
```

### 6.3 pipeline 文件名仍停留在 strategy 阶段

`pipeline.py` 已经加入材料生成：

```python
from tools.materials_engine import generate_instructional_materials
from core.material_alignment import check_full_material_alignment

materials = generate_instructional_materials(project)
project["instructional_materials"] = materials
material_alignment = check_full_material_alignment(project)
project["material_alignment"] = material_alignment
```

但输出文件名仍然是：

```python
mvp_algorithm_project_with_strategy_full.json
mvp_algorithm_report_with_strategy.md
mvp_algorithm_materials.md
```

Phase 5 需要新文件名：

```text
mvp_algorithm_project_with_materials_full.json
mvp_algorithm_report_with_materials.md
mvp_algorithm_materials.md
```

### 6.4 测试过于宽松，可能假通过

发现测试中存在类似：

```python
os.path.exists(materials_path) or os.path.exists(result['report_path'])
```

这会导致即使 `mvp_algorithm_materials.md` 没生成，只要普通报告存在，测试也通过。

还发现“学生学习单至少 6 个任务”的描述，但断言可能只是 `>=3`。这不符合验收标准。

因此 Phase 5 必须进入 Phase 5.1 修复。

---

## 7. 当前应该执行的阶段：Phase 5.1

### 7.1 Phase 5.1 目标

不是重写材料引擎，而是修复最终导出、报告渲染和测试严格性。

目标：

```text
1. 新增 run_mvp_pipeline_with_materials。
2. 生成 materials 命名的最终 JSON 和报告。
3. full JSON 顶层必须包含 instructional_materials 和 material_alignment。
4. Markdown 报告必须包含教学材料包章节。
5. 单独 mvp_algorithm_materials.md 必须真实存在且内容完整。
6. 测试不能再 OR 假通过。
7. 每个材料必须有标准元数据字段。
```

---

## 8. 给 Claude Code / Codex 的 Phase 5.1 修复指令

以下是可以直接交给 Codex 或 Claude Code 的指令：

```text
进入 Phase 5.1：教学材料包最终导出与测试修复。

Phase 5 已经新增 materials_engine、material_rules、material_alignment，并在 pipeline 中尝试接入材料生成。但实际验收发现：

1. 上传的 full JSON 仍然是 mvp_algorithm_project_with_strategy_full.json，顶层没有可靠看到 instructional_materials 和 material_alignment 最终成果；
2. 上传的 Markdown 报告仍然是 mvp_algorithm_report_with_strategy.md，没有看到“教学材料包”章节；
3. pipeline 虽然生成 materials，但主 JSON / 主报告文件名仍停留在 strategy 阶段；
4. 测试过于宽松，例如 materials Markdown 测试使用 materials_path exists OR report_path exists，导致材料包未生成时也能通过；
5. 学生学习单测试声称至少 6 个任务，但实际断言低于要求；
6. 当前不能进入 Phase 6 文件导出。

本轮只修复 Phase 5 的最终导出、报告渲染和测试严格性，不做 Word/PPT/Excel、draw.io、PDF/OCR、联网搜索、教师长期记忆、形成性评价闭环。
```

### 8.1 必须新增/强化 pipeline 函数

```python
def run_mvp_pipeline_with_materials(seed_path: str, output_dir: str = "exports") -> dict:
    """
    运行完整 MVP + 教学材料流水线。
    必须生成：
    - mvp_algorithm_project_with_materials_full.json
    - mvp_algorithm_report_with_materials.md
    - mvp_algorithm_materials.md
    """
```

返回：

```json
{
  "project": {},
  "project_path": "exports/mvp_algorithm_project_with_materials_full.json",
  "report_path": "exports/mvp_algorithm_report_with_materials.md",
  "materials_path": "exports/mvp_algorithm_materials.md",
  "quality_check": {},
  "material_alignment": {}
}
```

要求：

- `run_mvp_pipeline_with_context` 可以保留；
- Phase 5 验收必须使用 `run_mvp_pipeline_with_materials`；
- 不要只输出 `with_strategy` 文件名；
- 旧 strategy 文件可以保留，但不能作为 Phase 5 验收产物。

### 8.2 full JSON 必须包含材料字段

最终文件：

```text
exports/mvp_algorithm_project_with_materials_full.json
```

顶层必须包含：

```json
{
  "instructional_materials": {
    "teacher_guide": {},
    "student_worksheet": {},
    "entry_test_sheet": {},
    "pretest_sheet": {},
    "group_task_sheet": {},
    "peer_review_checklist": {},
    "posttest_sheet": {},
    "board_design": {},
    "simple_lesson_plan": {}
  },
  "material_alignment": {
    "overall_status": "",
    "coverage_rate": 0,
    "missing_objectives": [],
    "unsupported_strategy_segments": [],
    "missing_assessment_materials": [],
    "context_fit_warnings": [],
    "recommendations": []
  }
}
```

验收要求：

```text
instructional_materials 不得为空；
9 类材料都必须存在；
material_alignment.overall_status 必须存在；
material_alignment.coverage_rate 必须为 1.0 或 >=0.99；
material_alignment.missing_assessment_materials 必须为空；
材料字段必须进入最终 JSON，而不是只存在于函数返回值。
```

### 8.3 Markdown 报告必须包含教学材料包章节

最终文件：

```text
exports/mvp_algorithm_report_with_materials.md
```

必须包含：

```text
## 教学材料包
### 教师授课手册
### 学生学习单
### 入门技能测试单
### 前测任务单
### 小组任务单
### 互评检查表
### 后测任务单
### 板书设计
### 简版课堂教案
### 材料一致性检查
```

要求：

```text
章节里必须展示材料真实内容；
不允许只写“已生成”；
学生学习单必须显示至少 6 个任务；
教师授课手册必须显示教师提问、反馈建议、时间控制；
板书设计必须显示算法定义、三个特征、描述模板、检查清单；
材料一致性检查必须显示覆盖率、缺失目标、评价材料覆盖和环境适配结果。
```

### 8.4 单独材料包 Markdown 必须真实生成

最终文件：

```text
exports/mvp_algorithm_materials.md
```

必须存在，并包含：

```text
# 教学材料包
## 教师授课手册
## 学生学习单
## 入门技能测试单
## 前测任务单
## 小组任务单
## 互评检查表
## 后测任务单
## 板书设计
## 简版课堂教案
```

要求：

```text
文件必须存在；
文件大小不能为 0，建议 >1000 bytes；
不得只包含标题；
必须包含可复制使用的任务内容；
必须包含学生可填写区域；
必须包含互评检查表；
必须包含后测评分量规。
```

### 8.5 修复测试，不能再“假通过”

修改 `tests/test_materials_engine.py`。

#### 修复 materials Markdown 测试

不允许：

```python
os.path.exists(materials_path) or os.path.exists(result['report_path'])
```

必须改为：

```python
assert os.path.exists(result["materials_path"])
assert os.path.getsize(result["materials_path"]) > 1000

with open(result["materials_path"], "r", encoding="utf-8") as f:
    md = f.read()

assert "教师授课手册" in md
assert "学生学习单" in md
assert "互评检查表" in md
assert "后测任务单" in md
assert "板书设计" in md
```

#### 修复学生学习单任务数量测试

当前如果只是 `>=3`，必须改成：

```python
assert len(tasks) >= 6
```

并检查：

```python
assert "学习任务一" in text
assert "学习任务六" in text
assert "我的步骤" in text or "填写" in text
```

#### 新增最终报告测试

```python
assert "教学材料包" in report_md
assert "教师授课手册" in report_md
assert "学生学习单" in report_md
assert "材料一致性检查" in report_md
```

#### 新增 full JSON 测试

```python
project = result["project"]
assert "instructional_materials" in project
assert "teacher_guide" in project["instructional_materials"]
assert "student_worksheet" in project["instructional_materials"]
assert "material_alignment" in project
assert project["material_alignment"]["coverage_rate"] >= 0.99
```

#### 新增文件名测试

```python
assert result["project_path"].endswith("mvp_algorithm_project_with_materials_full.json")
assert result["report_path"].endswith("mvp_algorithm_report_with_materials.md")
assert result["materials_path"].endswith("mvp_algorithm_materials.md")
```

### 8.6 修复材料结构

当前材料可能是中文扁平 dict。可以保留中文内容，但每个材料必须同时具备标准元数据字段：

```json
{
  "material_id": "",
  "title": "",
  "material_type": "",
  "target_users": [],
  "related_objective_ids": [],
  "related_strategy_segments": [],
  "related_assessment_ids": [],
  "estimated_time_minutes": 0,
  "content": {},
  "usage_notes": [],
  "status": "candidate"
}
```

允许：

```json
"content": {
  "学习任务一": "...",
  "填写区": ["1.", "2.", "3."]
}
```

不允许只有中文扁平键而没有标准元数据。

### 8.7 完成后输出

Claude Code/Codex 完成后必须输出：

```text
1. 修复了哪些文件；
2. 是否新增 run_mvp_pipeline_with_materials；
3. 是否生成 mvp_algorithm_project_with_materials_full.json；
4. full JSON 中 instructional_materials 是否存在且包含 9 类材料；
5. full JSON 中 material_alignment 是否存在；
6. 是否生成 mvp_algorithm_report_with_materials.md，且包含教学材料包章节；
7. 是否生成 mvp_algorithm_materials.md，且包含可复制材料内容；
8. 学生学习单是否至少 6 个任务；
9. 测试是否已修复，尤其 materials_path 不再用 OR 假通过；
10. 测试结果；
11. 是否建议进入 Phase 6。
```

---

## 9. Phase 5.1 验收标准

Codex 修完后重点审查 4 个文件：

```text
1. exports/mvp_algorithm_project_with_materials_full.json
2. exports/mvp_algorithm_report_with_materials.md
3. exports/mvp_algorithm_materials.md
4. tests/test_materials_engine.py
```

必须同时满足：

```text
1. project_with_materials_full.json 顶层有 instructional_materials；
2. 9 类材料齐全；
3. project 顶层有 material_alignment；
4. material_alignment.coverage_rate >= 0.99；
5. report_with_materials.md 有“教学材料包”章节；
6. materials.md 真有可复制内容，不是空标题；
7. tests/test_materials_engine.py 不再使用 OR 假通过；
8. 学习单任务数量测试至少要求 6 个任务；
9. 材料结构包含标准元数据字段。
```

只有以上全部通过，才能进入 Phase 6。

---

## 10. Phase 6 预告：正式文件导出

Phase 5.1 通过后，下一阶段才是 Phase 6：正式文件导出。

Phase 6 目标可能包括：

```text
Word 教学系统设计报告
Word 简版教案
Word 学生学习单
Excel 目标-评价-策略-材料一致性矩阵
Markdown / JSON 导出稳定化
后续可考虑 draw.io 技能流图、PPT 大纲等
```

但现在不要提前做 Phase 6。

---

## 11. Codex 审查方式建议

请按下面顺序审查：

```text
1. 先运行测试：python -m unittest discover tests -v
2. 再运行 pipeline：run_mvp_pipeline_with_materials(...)
3. 打开 exports/mvp_algorithm_project_with_materials_full.json
4. 检查 instructional_materials 和 material_alignment
5. 打开 exports/mvp_algorithm_report_with_materials.md
6. 搜索“教学材料包”“学生学习单”“互评检查表”“材料一致性检查”
7. 打开 exports/mvp_algorithm_materials.md
8. 确认有可复制内容、填写区、评分量规
9. 打开 tests/test_materials_engine.py
10. 确认测试不是宽松假通过
```

如果某项失败，不要进入 Phase 6。

---

## 12. 用户偏好与交互方式

用户偏好：

```text
- 中文沟通；
- 直接、严格、不要废话；
- 需要复制即可用的 Claude Code/Codex 指令；
- 每个阶段只做明确范围；
- 必须指出不能进入下一阶段的原因；
- 不要被 Claude Code 的“测试 OK”迷惑；
- 审查要以实际文件为准。
```

用户现在希望 Codex 能直接读取文件并审查，所以这份文档要作为 Codex 的完整上下文。

---

## 13. 一句话总结当前状态

```text
当前 dc-designer-core 已完成 Dick-Carey 核心流程、K12 来源门禁、学习者环境分析、教学策略生成；Phase 5 教学材料生成代码方向正确，但最终 materials JSON/Markdown 产物和测试严格性未通过，必须先完成 Phase 5.1：教学材料包最终导出与测试修复，然后才能进入 Phase 6 文件导出。
```
