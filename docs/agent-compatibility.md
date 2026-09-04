# 智能体兼容说明

DC Designer v3 把九学科教学设计核心、宿主适配和通用启动提示词分开。不同智能体的插件格式并不相同，但它们可以共享同一组 Skill、MCP 工具、项目数据合同和质量边界。

## 共享核心

- `skills/`：设计、评审、修订三个教学设计 Skill；
- `.mcp.json`：标准 MCP 配置，提供设计、评审、修订和导出工具；
- `scripts/dc_designer.py`：没有原生插件入口时使用的九学科 v3 本地命令；
- `scripts/dc_info_tech.py`：历史信息科技 v1 兼容命令；
- `schemas/`、`canon/`、`data/standards/` 和 `templates/`：模型、来源、数据和输出合同；
- `prompts/dc-designer-core.md`：可以粘贴给任意能读项目文件的智能体的启动提示词。

## 宿主入口

| 智能体 | 原生适配 | 使用入口 |
| --- | --- | --- |
| Codex | `.codex-plugin/plugin.json`、Skills、MCP | 在 Plugins 中导入仓库的 marketplace，然后使用 `/dc-designer-core:dc-info-tech-design` 并提供学科与学段 |
| Claude Code | `.claude-plugin/plugin.json`、`skills/`、`.mcp.json` | 在仓库根目录运行 `claude --plugin-dir .`，然后使用 `/dc-designer-core:dc-info-tech-design` 并提供学科与学段 |
| Gemini CLI | `gemini-extension.json`、`GEMINI.md`、`commands/`、MCP | 使用 `gemini extensions install https://github.com/xiajiadi/dc-designer-core`，重启后使用 `/dc-info-tech-design` 并提供学科与学段 |
| 其他 MCP 智能体 | 标准 `.mcp.json` | 将 `dc-designer-mcp` 配置为 `python mcp-server/server.py`，或直接使用本地脚本 |
| 其他智能体 | 通用提示词 | 从官网复制启动提示词，粘贴到当前智能体；它会先判断可用的接入方式 |

## 通用接入规则

1. 优先使用当前智能体的项目级插件、扩展、Skill 或 MCP 配置；
2. 没有用户明确授权时，不写入用户全局配置，不上传教师资料，不把 `.dc-designer/` 当作公开内容；
3. 如果宿主要求用户确认安装、登录或启用权限，必须明确说明尚未完成，不能把“已读到仓库”说成“已安装”；
4. 接入完成后，先读取对应 Skill 和 `DESIGN.md`，再开始 v3 设计；只有历史 v1 信息科技项目才读取 `docs/v1_plugin_contract.md`；
5. 设计阶段保持教师确认、来源分层、隐私边界和“待实施 / 待验证”状态，不因宿主不同而降低门禁。

## 不能混淆的边界

“支持所有智能体”指同一套 DC Designer v3 九学科工作流可以通过原生适配、MCP 或通用提示词接入不同宿主，不代表每个宿主都提供相同的插件安装命令。宿主没有原生插件系统时，智能体仍可以读取项目文件并运行 `python scripts/dc_designer.py`，但它不会自动获得宿主专属的 Skill 菜单或命令命名空间。
