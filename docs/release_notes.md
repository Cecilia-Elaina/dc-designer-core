# v1.1.0 发布说明

## 发布边界

本版本面向中国大陆小学、初中和普通高中信息科技/信息技术教师，采用 Dick–Carey 教学系统设计模型。高校、职业教育、企业培训和其他学科不在本版本范围内。

## 关键能力

- 内置官方来源元数据快照：文件名称、发布机构、发布日期、生效日期、版本、链接、适用学段、学科、条款编号、定位、短引文和规范化摘要。
- 来源分层：国家/官方来源、教师本机资料、教材或学校资料、AI 推断分开显示；教师私有资料只写入本机工作区。
- 在线官方更新先进入待审核区；教师补齐来源元数据并明确确认后才替换活动来源，旧版本写入历史记录。
- 可恢复会话：查看阶段、确认或修改决策、暂停后继续、回退版本、复制项目和比较版本。
- 真实导出：完整 Word 报告、教师授课手册、学生学习单、AI 过程记录、Excel 一致性矩阵、PNG 图和 Draw.io XML。
- 发布门禁：LibreOffice 逐页渲染、空白页与页面边界检查、字体/字号/长表格/图片指标、内部枚举泄漏检查和 Draw.io 结构检查。

## 尚未承诺的能力

- 形成性评价目前只有方案、数据字段和待实施标记，不生成虚构学生效果数据。
- 内置快照不复制官方文件全文；`content_hash_status=metadata_snapshot_only` 表示只记录元数据和候选条款。联网更新成功并经教师确认后，才记录下载内容的 SHA-256。
- 插件平台的最终上架仍需要发布者账号、仓库地址和平台审核流程；本地包可以先完成安装与验收。

## 发布前命令

```text
python scripts/doctor.py
python scripts/release_check.py
python scripts/acceptance_cases.py
python scripts/package_release.py
python scripts/clean_install_smoke.py --archive dist/dc-designer-core-v1.1.0.zip
```

要生成范例报告视觉基线，可执行：

```text
python scripts/visual_qa.py --docx <导出的报告.docx> --output-dir <qa目录> --reference-docx <标准报告一.docx> --reference-docx <标准报告二.docx>
```
