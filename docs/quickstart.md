# 快速开始

## 1. 检查环境

在项目目录打开 PowerShell：

```text
python scripts/doctor.py
```

至少应满足 Python、python-docx、openpyxl、Pillow 和 LibreOffice 检查。没有 LibreOffice 时仍可生成草案，但视觉质量门禁会保持“待验证”。

## 2. 在 Codex 中使用

安装插件后新建对话，调用：

```text
/dc-designer-core:dc-info-tech-design
```

可以直接描述课题，也可以明确选择两种模式：

- `standard_fast`：提供学段、年级、课题、教材版本、单元、课时、设备和匿名班级共性学情，系统检索课程标准并生成草案；
- `collaborative`：从评价需求和绩效差距开始，逐阶段回答问题并确认候选方案。

系统会先展示官方依据候选和来源层级。教学目的、入门技能、学情、课时设备和教学策略等关键内容必须由教师确认或修改；“条款候选”不等同于最终依据。

## 3. 启动本地工作台

```text
python scripts/dc_web.py --port 8765
```

打开 `http://127.0.0.1:8765/`。项目、版本、导出文件和本机知识库都位于教师工作区，默认是 `%USERPROFILE%\\.dc-designer`。

## 4. 导入教师资料

```text
python scripts/dc_info_tech.py knowledge-ingest --path <文件路径> --metadata-json '{"subject":"信息科技","school_type":"普通高中"}'
```

教师资料会标记为 `C1/teacher_private`，只作为情境和策略参考，不能被伪装成国家课程标准。含学生身份信息或个人成绩的文件会被拒绝。

## 5. 导出与验收

每个项目可以导出完整 Word 报告、教师指南、学生学习单、AI 过程记录、Excel 一致性矩阵、PNG 图和 Draw.io XML。只有来源确认、关键决策、图逻辑、一致性和视觉检查全部通过，才会出现 `final_ready`。

没有真实形成性评价数据时，形成性评价章节保持“待实施/待验证”，不生成虚构的学习效果。
