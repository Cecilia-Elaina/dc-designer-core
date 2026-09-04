# 发布前清单

## 产品与范围

- [ ] `.codex-plugin/plugin.json`、`.claude-plugin/plugin.json` 和 `gemini-extension.json` 版本、名称和说明一致。
- [ ] `GEMINI.md`、`commands/`、`prompts/` 和 [跨智能体接入说明](agent-compatibility.md) 与共享 Skill 保持一致。
- [ ] 官网复制按钮提供通用启动提示词，不把产品描述成 Codex 专属。
- [ ] `.agents/plugins/marketplace.json` 指向正确的 GitHub 插件仓库根目录。
- [ ] v3 支持中国大陆小学、初中和普通高中九学科；高校、职教、企业培训和九学科之外的学科明确返回不支持。
- [ ] README、快速开始、隐私和依赖说明完整。

## 证据与隐私

- [ ] 内置官方来源具有快照编号、链接、日期、版本和条款定位。
- [ ] 教师资料标记为 `C1/teacher_private`，不进入插件发布包。
- [ ] 待审核的官方在线更新不会自动激活。
- [ ] 项目和教师资料位于本机 `.dc-designer`，学生身份信息被拒绝保存。

## 真实输出

- [ ] 端到端生成完整报告、教师指南、学生学习单、AI 过程记录和 Excel 矩阵。
- [ ] 分别生成目的操作流程图、技能层级图和程序控制流程图。
- [ ] Draw.io 单页图和多页工作簿可以解析，页面内节点 ID 不重复。
- [ ] LibreOffice 逐页转换成功，没有空白页，Word 没有内部枚举泄漏。

## 发布包

- [ ] `python scripts/doctor.py` 通过核心检查。
- [ ] `python scripts/release_check.py` 通过。
- [ ] `python scripts/package_release.py` 生成版本压缩包、SHA256 和清单。
- [ ] 解压到干净目录后仍能运行 `scripts/dc_designer.py`；历史 `scripts/dc_info_tech.py` 兼容入口仍可运行；官网静态文件可独立预览。
- [ ] GitHub Pages 工作流能够从 `site/` 生成公开站点。
- [ ] `python scripts/compatibility_check.py` 通过，确认原生适配清单、MCP 路径和通用提示词一致。
- [ ] 未把 `exports/`、参考报告、测试缓存或教师资料打入压缩包。

## 干净环境与三案例

- [ ] `python scripts/acceptance_cases.py` 的初中分支、高中循环、小学算法三个案例均导出成功并通过视觉门禁。
- [ ] `python scripts/clean_install_smoke.py --archive <release.zip>` 在解压后的目录中通过来源检索和最小设计导出。
- [ ] 用两份标准报告生成 `reference_profile.json`，记录页数、表格数、图形数、页面方向、字体和最小字号，作为后续回归基线。
- [ ] 发布说明明确说明形成性评价数据仍为“待实施/待验证”，没有真实学生数据闭环。
