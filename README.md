# dc-designer-core

面向中国 K12 信息科技/信息技术教师的 Dick–Carey 教学系统设计 Codex 插件。

## 产品范围

当前 v1 只支持中国大陆小学、初中、普通高中信息科技/信息技术。插件提供两个设计模式：

- `standard_fast`：课标约束快速设计。检索内置官方文件的条款候选，自动形成完整草案，再请教师确认关键决策。
- `collaborative`：完整协同设计。从需求/绩效差距开始，按 Dick–Carey 模块逐步提问、生成候选、记录决策并复核。

高校、职教、企业培训和其他学科在当前版本会被明确拒绝，不会套用泛化模板继续生成。

## Codex 入口

官方清单是 `.codex-plugin/plugin.json`，公开三个 Skills：

```text
/dc-designer-core:dc-info-tech-design
/dc-designer-core:dc-info-tech-review
/dc-designer-core:dc-info-tech-revise
```

Skills 使用本地 `scripts/dc_info_tech.py` 和 `mcp-server/` 核心，不要求远程服务。MCP Server 仍保留为兼容入口；明确传入 `education_scope=k12_info_technology` 或 `v1=true` 时会路由到 v1 核心。

## 知识与隐私边界

- 插件内置的是官方文件元数据、链接和标注为 `normalized_summary` 的条款候选，不复制商业教材全文，也不把摘要冒充逐字引文。
- 教师上传的教材、教案、试卷和校本资料写入教师本机 `.dc-designer/knowledge/`，来源标为 `C1/teacher_private`，不能单独成为正式教学目的依据。
- 教师长期记忆必须显式同意；系统拒绝保存学生姓名、学号、身份证号、电话和个人成绩等身份信息。
- 条款候选必须由教师核对链接、版本、单元和适用范围后，才能进入 `teacher_confirmed` 或 `final_verified`。

## 输出

一次设计从同一项目对象生成：

- Word 完整教学系统设计报告、教师教学指南、学生学习单、AI 过程记录；
- Excel 一致性矩阵、JSON 项目文件、Markdown 证据与质量报告；
- 目的操作流程图、技能层级图和编程课题控制流程图的 PNG；
- 可编辑的单页 Draw.io 图和多页 Draw.io 工作簿。

技能图严格区分目的操作流程与从属技能/入门技能层级；分支、循环课题会生成决策菱形、是/否边和测试/调试反馈回路。

## 本地命令

```text
python scripts/dc_info_tech.py design --request-file examples/v1/smoke_request.json --output-dir exports/v1_smoke
python scripts/dc_info_tech.py review --project <project.json> --output-dir <review-dir>
python scripts/dc_info_tech.py revise --project <project.json> --feedback-file <feedback.json> --output-dir <revise-dir>
python scripts/dc_info_tech.py knowledge-ingest --path <teacher-file> --metadata-json '{"subject":"信息科技"}'
```

## 本地工作台

不使用 Codex 对话时，可以启动本机教师工作台：

```text
python scripts/doctor.py
python scripts/dc_web.py --port 8765
```

浏览器打开 `http://127.0.0.1:8765/`。工作台支持新建设计、阶段进度、确认或修改决策、暂停继续、版本回退、来源查看、官方文件待审核更新以及本机项目删除。服务只绑定回环地址，不上传教师文件，也不要求账号。

## 环境与安装

- Windows 10/11；Python 3.10 或更高版本。
- 生成 Word/Excel 需要 `requirements-core.txt`；MCP 兼容入口再安装 `requirements-mcp.txt`。
- 视觉质量门禁推荐安装 LibreOffice；`scripts/doctor.py` 会检查 LibreOffice 和 `pdftoppm`。
- Draw.io 文件是标准 XML，可用 diagrams.net 打开编辑；本地生成不依赖联网 Draw.io 客户端。
- 运行 `python scripts/package_release.py` 生成不含测试导出物和用户资料的发布压缩包。

## 官方来源与更新

内置库是带快照编号的官方来源元数据和短条款候选，不复制受限全文。每条来源包含发布机构、日期、版本、链接、页码或条款定位、适用学段和用途。教师可通过对话入口或本地工作台获取教育部/政府官方链接；在线文件只会进入 `.dc-designer/knowledge/official/updates.json` 的待审核区，教师确认并补齐元数据后才会进入本机活动目录。

## 隐私与产品边界

插件只支持中国大陆小学、初中、普通高中信息科技/信息技术；高校、职教、企业培训和其他学科会被拒绝。教师资料和项目文件默认保存在本机 `.dc-designer/`，不会被打包进插件。系统拒绝保存学生姓名、学号、身份证号、电话和个人成绩；没有真实形成性评价数据时，报告只写“待实施/待验证”，不编造效果数据。

## 开发验证

```text
python -m pytest -q
python <Codex plugin validator>/validate_plugin.py .
python scripts/release_check.py
```

## 目录

```text
.codex-plugin/       Codex 官方插件清单
skills/              三个公开 Skill
scripts/             本地 Skill 入口
mcp-server/core/     范围、证据、知识库、质量和路径核心
mcp-server/tools/    教学分析、导出与兼容工具
data/standards/      官方来源元数据和条款候选
schemas/             v1 项目与技能图合同
docs/                审计、复用矩阵、插件合同
tests/               回归与 v1 端到端验收
```

## 许可

MIT License

## 发布前验收

发布包生成前建议依次执行：

```text
python scripts/doctor.py
python scripts/acceptance_cases.py
python scripts/package_release.py
python scripts/clean_install_smoke.py --archive dist/dc-designer-core-v1.1.3.zip
```

`acceptance_cases.py` 使用匿名合成请求验证初中分支、高中循环和小学算法三个场景；它不会导入或生成真实学生数据。`clean_install_smoke.py` 会将压缩包解压到临时目录，并在包外建立教师工作区，验证安装包不依赖开发者目录。
