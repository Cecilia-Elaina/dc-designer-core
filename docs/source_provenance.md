# 官方来源与证据追溯

## 内置快照

`data/standards/k12/official_snapshot.json` 是随插件发布的官方来源快照。它保存来源元数据和短条款候选，不复制商业教材或受限文件全文。每条来源至少记录：

- 文件名称、发布机构、发布日期、生效日期和版本；
- 官方链接、文件类型、适用学段、学科和主题；
- 条款编号或章节定位、页码（可获得时）、短原文片段和中文规范化摘要；
- 来源层级、可信度、可作为教学目的依据的范围、适用模块和当前状态。

当前产品只把教育部或政府官方域名作为内置官方证据入口。`normalized_summary` 是检索和生成候选，不是对原文的逐字替代；教师应打开链接核对版本和适用范围。

## 本机更新

```text
历史信息科技 v1 的来源更新仍使用 `scripts/dc_info_tech.py`：

```text
python scripts/dc_info_tech.py source-update --url <官方HTTPS链接>
python scripts/dc_info_tech.py source-approve --update-id <update-id> --teacher-confirmed --source-record-file <元数据JSON>
python scripts/dc_info_tech.py source-rebuild
```

v3 的九学科国家标准基线由 `data/standards/` 中的版本化记录提供；新增在线来源仍先进入本地待审核区，不会自动改变活动快照。
```

第一步只保存文件和哈希到待审核区，不改变活动来源。第二步需要教师确认，并要求补齐或核对来源记录。活动来源保存在 `.dc-designer/knowledge/official/active_sources.json`，内置快照不会被覆盖。

## 来源层级

| 层级 | 含义 | 用途 |
| --- | --- | --- |
| A1 | 国家或政府官方文件 | 课程目标和规范要求的候选依据，须经教师确认 |
| B1 | 教材或公开教学材料 | 内容组织和示例参考，不冒充国家要求 |
| C1 | 教师私有资料 | 校本情境、学情和经验参考，只保存在本机 |
| AI | 系统推断 | 方案候选，不能单独成为正式依据 |

报告中的“来源依据”表会显示来源名称、发布机构、版本、日期、链接、条款定位、原文片段/摘要和确认状态，教师可以沿表格回到原始链接核验。
