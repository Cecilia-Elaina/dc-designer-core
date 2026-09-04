# 义务教育九学科元数据

本目录包含教育部《义务教育课程方案和课程标准（2022 年版）》覆盖的九个 v3 学科记录：

- 语文、数学、英语
- 物理、化学、生物学
- 历史、地理、道德与法治

文件名使用 <subject>_compulsory_2022.json。official_snapshot.json 是内置官方来源快照，保留旧版信息科技来源以兼容 v2，并加入九学科来源记录。

每个学科 JSON 使用统一的 subject_id、stage、core_competencies、content_areas、academic_quality_standards、clauses 和 extraction_evidence 字段。条款候选来自官方文件前置章节的元数据与 OCR 定位，生成课时级内容时必须由教师打开官方原文复核。

来源主索引见上级目录的 source_registry.json，九学科适配器见 subject_registry_v3.json。原始 PDF 不随仓库发布。
