# DEPRECATION_PLAN

## 立即停止作为 v1 入口

- `.claude-plugin/plugin.json`：保留作历史兼容，不再作为 Codex 发布清单。
- `skills/dc-higher-ed/SKILL.md` 和 `skills/dc-corporate-training/SKILL.md`：保留文件以避免破坏旧测试，但从 Codex manifest 和产品入口移除。
- `manifest.json` 中的高校、职教、企业场景：改为历史兼容信息，不再暴露为可触发能力。
- 远程 MCP 配置：保留用于旧阶段回归，v1 Skill 不依赖它。

## 迁移顺序

1. 建立 `.codex-plugin/plugin.json`，公开 `dc-info-tech-design`、`dc-info-tech-review`、`dc-info-tech-revise`。
2. 新增统一 `k12_info_technology` 范围、模式、来源和项目 schema。
3. 将标准检索和教师资料索引迁移到本机 `.dc-designer` 工作区。
4. 重写技能图 schema、图逻辑校验和多页 Draw.io 导出。
5. 让 Word/Markdown/JSON/Draw.io/PDF 从同一项目对象导出。
6. 增加高校、企业、其他学科和隐私违规的负向测试。
7. 最后再决定是否删除旧 MCP；在 v1 发布前保持兼容但不让它成为安装前置。

## 删除条件

只有同时满足以下条件后，才可以删除历史入口：

- Codex manifest 已通过插件校验；
- 三个公开 Skills 可在干净工作区完成端到端设计、评审和修改；
- 本地知识库可重建且不依赖仓库内用户资料；
- 两张核心技能图均可在 diagrams.net 打开且通过逻辑门禁；
- Word、PDF、JSON、Markdown 和 Draw.io 的编号与链接一致；
- 正向和负向验收用例全部通过。

