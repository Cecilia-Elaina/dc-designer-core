# v1 Codex 插件合同

## 公开入口

- `dc-info-tech-design`：新建教学系统设计，提供课标约束快速设计和完整协同设计两种模式。
- `dc-info-tech-review`：评审已有项目，只读原项目并输出可执行 findings。
- `dc-info-tech-revise`：基于反馈和形成性评价输入做影响分析、修改和一致性重检。

## 范围

`education_scope` 固定为 `k12_info_technology`。小学、初中使用“信息科技”课程标准，高中使用“信息技术”课程标准。高校、职教、企业和其他学科请求返回 `unsupported_scope`。

## 数据边界

内置库只保存官方文件的来源元数据、官方链接和用于检索的结构化条款候选。教师上传的教材全文、教案、试卷和学校资料保存到本机 `.dc-designer/knowledge/`，不进入插件包；教师资料来源等级为 `C1`，不能单独成为正式教学目的依据。

## 证据状态

`no_source → document_found → clause_candidate → clause_aligned → teacher_confirmed → final_verified`。只有最后两个状态允许正式教学目的通过证据门禁。

## 图形合同

每个项目至少有“目的操作流程图”和“从属技能与入门技能图”两个独立视图；编程分支/循环课题额外生成程序控制流程图。所有页面均写入可在 diagrams.net 打开的多页 Draw.io XML，节点文本完整可编辑，决策分支带“是/否”标签。
