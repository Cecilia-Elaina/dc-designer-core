# Phase 8: Plugin Contract

## 1. Goals

Phase 8 verifies that dc-designer-core works as an **MCP plugin** that Claude (or any MCP client) can invoke through standard tool-call semantics. The three objectives are:

1. **Plugin manifest integrity** -- `manifest.json`, `.claude-plugin/plugin.json`, and `.mcp.json` exist, are internally consistent, and declare the correct tool count.
2. **MCP tool discovery** -- `server.list_tools()` returns exactly 4 `Tool` objects with `name`, `description`, and `inputSchema`.
3. **MCP call_tool dispatch** -- `server.call_tool(name, arguments)` returns `[TextContent(type="text", text=json_str)]` for every tool, and the JSON payload matches the per-tool contract below.

Phase 8 builds on Phase 7 (agent contract). Phase 7 proved that `run_agent_session()` produces correct structured results. Phase 8 proves the **MCP entry layer** on top of it works: tool registration, argument routing, and response serialization.

---

## 2. Architecture

```
MCP Client (Claude / VS Code / custom)
  |
  v
server.py  (MCP Server, mcp.server.Server)
  |
  |-- list_tools()  --> returns [Tool, Tool, Tool, Tool]
  |
  |-- call_tool(name, arguments)
        |
        |-- "dc_design_session"   --> agent_session.run_agent_session(mode="dc-design", ...)
        |-- "dc_review_session"   --> agent_session.run_agent_session(mode="dc-review", ...)
        |-- "dc_revise_session"   --> agent_session.run_agent_session(mode="dc-revise", ...)
        |-- "dc_export_package"   --> document_exporter.export_all(project, output_dir)
        |
        v
      [TextContent(type="text", text=json.dumps(result))]
```

All four tools follow the same call convention:

```python
result = await server.call_tool(tool_name, arguments_dict)
# result is a list: [TextContent(type="text", text="<json string>")]
parsed = json.loads(result[0].text)
```

---

## 3. The Four Public MCP Tools

### 3.1 dc_design_session

**Purpose**: Start a full Dick & Carey instructional design pipeline (dc-design mode).

**Input Schema** (required fields marked with `*`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_type` | string | | User persona: K12教师 / 高校教师 / 职教教师 / 企业培训师 |
| `scenario` | string | | Teaching scenario: 新课设计 / 单元设计 / 课程设计 / 培训项目设计 |
| `subject` | string | * | Subject area |
| `grade_level` | string | * | Grade level |
| `topic` | string | * | Topic / lesson title |
| `teacher_inputs` | object | | Teacher-provided context (prior knowledge, media, devices) |
| `source_documents` | array[string] | | Paths to curriculum standards / textbook materials |
| `output_dir` | string | | Output directory (default: `exports/phase8`) |

**Output Contract** (JSON inside TextContent):

```json
{
  "mode": "dc-design",
  "status": "completed" | "completed_with_warnings" | "error",
  "tool_call_plan": [{"step": 1, "engine": "...", "function": "...", ...}],
  "warnings": ["..."],
  "required_confirmations": [{"module": "...", "reason": "...", ...}],
  "can_export_final": false,
  "final_blocking_reasons": [{"component": "...", "reason": "...", ...}],
  "draft_status": "draft_pending_confirmation" | "blocked" | "final_ready",
  "tool_status_report": [{"tool_name": "...", "status": "called"|"not_called", ...}],
  "export_result": {
    "project_json": "path/to/project.json",
    "full_report_docx": "path/to/report.docx",
    "lesson_plan_docx": "path/to/lesson.docx",
    "student_worksheet_docx": "path/to/worksheet.docx",
    "alignment_matrix_xlsx": "path/to/matrix.xlsx",
    "ai_process_record_docx": "path/to/record.docx",
    "export_index_json": "path/to/index.json",
    "export_errors": []
  },
  "alignment_summary": {...}
}
```

**Key invariant**: For K12 users without clause-level source documents, `can_export_final` must be `false` and `draft_status` must not be `final_ready`.

---

### 3.2 dc_review_session

**Purpose**: Audit an existing design project for alignment and quality issues. Read-only; does not modify the original project.

**Input Schema**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `existing_design_project_path` | string | | Path to project JSON file (mutually exclusive with `existing_design_project`) |
| `existing_design_project` | object | | Project data object (mutually exclusive with `existing_design_project_path`) |
| `output_dir` | string | | Output directory (default: `exports/phase8`) |

**Output Contract**:

```json
{
  "mode": "dc-review",
  "status": "completed" | "completed_with_warnings",
  "findings": [
    {
      "finding_id": "fnd_1",
      "severity": "high" | "medium" | "low",
      "description": "...",
      "suggested_fix": "...",
      "affected_modules": ["..."],
      "related_quality_gate": "..."
    }
  ],
  "review_report": {...},
  "alignment_summary": {...}
}
```

**Key invariant**: Findings list is non-empty when issues exist. Every finding has `finding_id`, `severity`, `description`, `suggested_fix`, and `affected_modules`.

---

### 3.3 dc_revise_session

**Purpose**: Apply teacher feedback to an existing design project and re-verify alignment. Performs impact analysis before modification, then runs post-revision consistency checks.

**Input Schema**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `existing_design_project_path` | string | | Path to project JSON file |
| `existing_design_project` | object | | Project data object (alternative to path) |
| `feedback_or_revision_data` | object | * | Must contain `feedback_type` and `items` |
| `output_dir` | string | | Output directory (default: `exports/phase8`) |

**Output Contract**:

```json
{
  "mode": "dc-revise",
  "status": "completed" | "completed_with_warnings",
  "revision_log": [
    {
      "module": "...",
      "action": "...",
      "action_status": "applied" | "skipped" | "failed",
      ...
    }
  ],
  "revision_record": {...},
  "pre_revision_alignment": {"overall_status": "...", ...},
  "post_revision_alignment": {"overall_status": "...", ...},
  "revised_project_path": "path/to/revised.json"
}
```

**Key invariant**: `pre_revision_alignment` and `post_revision_alignment` must both be present. If post-revision status is not `pass`, the overall revise status must be `completed_with_warnings`.

---

### 3.4 dc_export_package

**Purpose**: Export a design project to Word (.docx), Excel (.xlsx), JSON, and Markdown files. Must be provided either `project_path` (file path) or `project` (in-memory object).

**Input Schema**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_path` | string | | Path to project JSON file (mutually exclusive with `project`) |
| `project` | object | | Project data object (mutually exclusive with `project_path`) |
| `output_dir` | string | | Output directory (default: `exports/phase8`) |

**Output Contract (success)**:

```json
{
  "status": "ok",
  "export_status": "success",
  "export_index_json": "path/to/export_index.json",
  "warnings": [],
  "errors": [],
  "files": {
    "dc_report": {"path": "...", "exists": true, "size": 153805},
    "lesson_plan": {"path": "...", "exists": true, "size": 38034},
    "student_worksheet": {"path": "...", "exists": true, "size": 38139},
    "alignment_matrix": {"path": "...", "exists": true, "size": 6339},
    "ai_process_record": {"path": "...", "exists": true, "size": 39382}
  }
}
```

**Output Contract (error)**:

```json
{
  "status": "error",
  "export_status": "failed",
  "errors": ["必须提供 project_path 或 project 参数"],
  "warnings": [],
  "files": {}
}
```

**Key invariant**: Every entry in `files` must have `path`, `exists` (boolean), and `size` (integer). When neither `project_path` nor `project` is provided, `status` must be `"error"` and `errors` must be non-empty. When `project_path` does not exist on disk, `status` must be `"error"`.

---

## 4. Tool Boundaries

Each tool operates in a strict mode boundary. No tool mixes responsibilities.

| Tool | Mode | Reads | Writes | Modifies Original |
|------|------|-------|--------|-------------------|
| `dc_design_session` | dc-design | Standards DB, teacher inputs | Project JSON, 5 export files, export index | N/A (creates new) |
| `dc_review_session` | dc-review | Project JSON | Review report JSON | No |
| `dc_revise_session` | dc-revise | Project JSON, feedback data | Revised project JSON, revision log | Yes (creates revision) |
| `dc_export_package` | dc-export | Project JSON | 5 export files, export index | No |

**Critical rule**: `dc_review_session` must never modify the input project. It is a pure audit tool.

---

## 5. AGENTS.md Constraints

The following constraints from AGENTS.md apply to all tool outputs:

1. **No fake finals**: K12 designs without clause-level source documents cannot return `can_export_final: true` or `draft_status: "final_ready"`. The system must block final export and list `final_blocking_reasons`.

2. **Source traceability**: Every design must record where curriculum standard matches came from. The `source_trace.goal_basis.sources` array must be present.

3. **Confirmation before export**: When alignment issues or source verification gaps exist, the system must list `required_confirmations` and must not auto-export a final document.

4. **Review is read-only**: `dc_review_session` must not write to the project file. It outputs findings and a review report only.

5. **Revision requires impact analysis**: `dc_revise_session` must run `pre_revision_alignment` before modifications and `post_revision_alignment` after. The revision log must record every action's `action_status`.

6. **Deterministic engines only**: All pipeline calls go through real deterministic functions (goal_engine, skill_graph, objective_engine, assessment_engine, strategy_engine, materials_engine, alignment_checker, standards_search). No AI calls, no stubs.

---

## 6. Error Handling Rules

### 6.1 Server-level error wrapping

`server.py` wraps all exceptions in a consistent error response:

```python
{
    "tool": "<tool_name>",
    "status": "error",
    "error": "<exception message>",
    "input": <arguments dict>
}
```

This is returned as `[TextContent(type="text", text=json_str)]`.

### 6.2 Tool-level error responses

Each tool returns structured errors (not exceptions) when inputs are invalid:

- **dc_design_session**: Returns `{"status": "error", "warnings": ["Missing required fields: ..."]}` when required fields are missing.
- **dc_review_session**: Returns `{"status": "error", "warnings": ["No project path provided"]}` when no path is given, or `{"status": "error", "warnings": ["Project file not found: ..."]}` when the file does not exist.
- **dc_revise_session**: Returns `{"status": "error", ...}` when the project cannot be loaded or feedback data is missing.
- **dc_export_package**: Returns `{"status": "error", "export_status": "failed", "errors": [...]}` when project is missing, path is invalid, or JSON parsing fails.

### 6.3 JSON serialization safety

All results pass through `json.loads(json.dumps(result, default=str))` before being wrapped in `TextContent`. This ensures non-serializable objects (datetime, Path, etc.) are converted to strings rather than causing serialization failures.

---

## 7. Verification Test Checklist

The following tests are implemented in `tests/test_phase8_mcp_real.py`:

| # | Test Class | What It Verifies |
|---|-----------|------------------|
| 1 | `TestMCPListToolsExposesFourPublicTools` | `list_tools()` returns exactly 4 Tool objects with name, description, inputSchema |
| 2 | `TestMCPDesignCallTool` | `call_tool("dc_design_session", ...)` returns mode="dc-design", status exists, can_export_final=false for K12 without sources |
| 3 | `TestMCPReviewCallTool` | `call_tool("dc_review_session", ...)` returns mode="dc-review", non-empty findings with required fields |
| 4 | `TestMCPReviseCallTool` | `call_tool("dc_revise_session", ...)` returns mode="dc-revise", revision_log or revision_record exists, alignment status present |
| 5 | `TestMCPExportPackageLoadsProjectPath` | `call_tool("dc_export_package", {project_path: ...})` loads real project, returns files with path/exists/size |
| 6 | `TestMCPExportPackageRejectsMissing` | `call_tool("dc_export_package", {})` returns error status with non-empty errors list |
| 7 | `TestMCPExportPackageResult` | Export result has status, export_status, files, export_index_json, warnings or errors |

**Total: 24 test methods across 7 test classes.**

All tests call `server.call_tool()` or `server.list_tools()` directly -- they do not call `agent_session.run_agent_session()` or any lower-level engine function. This proves the MCP plugin entry layer is functional end-to-end.

---

## 8. File Locations

| File | Purpose |
|------|---------|
| `mcp-server/server.py` | MCP server with `list_tools()` and `call_tool()` decorators |
| `mcp-server/tools/agent_session.py` | Agent session orchestrator (Phase 7) |
| `mcp-server/tools/document_exporter.py` | Document export engine (Phase 6.2) |
| `tests/test_phase8_mcp_real.py` | Real MCP layer tests (Phase 8.2) |
| `tests/test_phase8_plugin_contract.py` | Plugin manifest + agent contract tests (Phase 8.1) |
| `.mcp.json` | MCP server configuration for Claude |
| `.claude-plugin/plugin.json` | Plugin manifest for Claude plugin system |
| `manifest.json` | Package manifest |
