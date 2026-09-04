"""
dc-designer-mcp Server
Dick & Carey 教学系统设计插件的 MCP Server

暴露 4 个核心工具：dc_design_session, dc_review_session, dc_revise_session, dc_export_package
"""

from mcp.server import Server
from mcp.types import Tool, TextContent
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

server = Server("dc-designer-mcp")

# Required export file keys for success/partial/failed judgment
_REQUIRED_EXPORT_KEYS = ["dc_report", "lesson_plan", "student_worksheet",
                         "alignment_matrix", "ai_process_record"]


def _is_v1_request(args: dict) -> bool:
    """Opt into the v1 local core without breaking historical MCP callers."""
    return bool(
        args.get("v1")
        or args.get("education_scope") == "k12_info_technology"
    )


def _is_v3_request(args: dict) -> bool:
    """Opt into the explicit nine-subject v3 contract."""
    if args.get("v3") or args.get("education_scope") == "k12_nine_subjects":
        return True
    project = args.get("existing_design_project") or args.get("project")
    if isinstance(project, dict) and project.get("education_scope") == "k12_nine_subjects":
        return True
    try:
        from core.subject_registry import is_v3_subject

        subject = args.get("subject_id") or args.get("subject")
        # A grade such as "八年级" is not a stage label.  Passing it to the
        # registry would raise before a valid subject can opt into v3.
        stage = args.get("stage") or args.get("education_stage")
        return bool(subject) and is_v3_subject(subject, stage)
    except Exception:
        return False


def _normalize_v3_export_result(raw: dict) -> dict:
    """Normalize the v3 exporter result for the MCP response contract."""
    files = {}
    for key, info in (raw.get("files", {}) if isinstance(raw, dict) else {}).items():
        if not isinstance(info, dict):
            continue
        path = info.get("path", "")
        exists = bool(path) and os.path.isfile(path)
        files[key] = {
            "path": path,
            "exists": exists,
            "size": info.get("size", os.path.getsize(path) if exists else 0),
        }
    errors = list(raw.get("errors", []) if isinstance(raw, dict) else [])
    has_files = any(item.get("exists") and item.get("size", 0) > 0 for item in files.values())
    status = "completed" if raw.get("status") == "success" and not errors else ("completed_with_warnings" if has_files else "failed")
    return {
        "status": status,
        "export_status": "success" if status == "completed" else ("partial" if has_files else "failed"),
        "export_index_json": files.get("export_index_json", {}).get("path", ""),
        "warnings": errors,
        "export_errors": errors,
        "errors": errors,
        "files": files,
    }


def _v1_file_entry(path: str) -> dict:
    exists = bool(path) and os.path.isfile(path)
    return {
        "path": path,
        "exists": exists,
        "size": os.path.getsize(path) if exists else 0,
    }


def _normalize_v1_export_result(raw: dict) -> dict:
    """Normalize the v1 exporter index for the MCP response contract."""
    index = raw.get("files", {}) if isinstance(raw, dict) else {}
    files = {}
    for key, value in index.items():
        if isinstance(value, str):
            files[key] = _v1_file_entry(value)
    legacy = raw.get("legacy_exports", {}) or index.get("legacy_exports", {})
    if isinstance(legacy, dict):
        for key, value in legacy.get("files", {}).items():
            if isinstance(value, dict):
                path = value.get("path", "")
                files.setdefault(key, _v1_file_entry(path))
    required = ["project_json", "report_markdown", "drawio_workbook"]
    required_ok = all(files.get(key, {}).get("exists") and files.get(key, {}).get("size", 0) > 0 for key in required)
    has_any = any(item.get("exists") and item.get("size", 0) > 0 for item in files.values())
    export_status = "success" if required_ok else ("partial" if has_any else "failed")
    warnings = [] if export_status == "success" else ["v1 导出包仍有文件未生成，不能标记为最终包"]
    return {
        "status": "completed" if export_status == "success" else ("completed_with_warnings" if export_status == "partial" else "failed"),
        "export_status": export_status,
        "export_index_json": raw.get("export_index_json", ""),
        "warnings": warnings,
        "export_errors": raw.get("errors", []),
        "errors": raw.get("errors", []),
        "files": files,
    }


def _normalize_export_result(raw: dict) -> dict:
    """Normalize export_all result into stable output contract."""
    all_warnings = []
    all_errors = []
    files_out = {}

    for key, info in raw.get("files", {}).items():
        fpath = info.get("path", "")
        entry = {
            "path": fpath,
            "exists": os.path.exists(fpath) if fpath else False,
            "size": info.get("size", 0),
        }
        if info.get("warnings"):
            all_warnings.extend(info["warnings"])
        if info.get("error"):
            all_errors.append(info["error"])
        files_out[key] = entry

    # Determine export_status based on required files
    required_ok = sum(
        1 for k in _REQUIRED_EXPORT_KEYS
        if files_out.get(k, {}).get("exists", False)
        and files_out.get(k, {}).get("size", 0) > 0
    )
    if required_ok == len(_REQUIRED_EXPORT_KEYS):
        exp_status = "success"
    elif required_ok > 0:
        missing = [k for k in _REQUIRED_EXPORT_KEYS
                   if not files_out.get(k, {}).get("exists", False)
                   or files_out.get(k, {}).get("size", 0) == 0]
        exp_status = "partial"
        all_warnings.append(f"部分必需导出文件缺失: {', '.join(missing)}")
    else:
        exp_status = "failed"

    return {
        "status": "completed" if exp_status == "success"
                  else ("completed_with_warnings" if exp_status == "partial" else "failed"),
        "export_status": exp_status,
        "export_index_json": raw.get("index_path", ""),
        "warnings": all_warnings,
        "export_errors": all_errors,
        "errors": all_errors,
        "files": files_out,
    }

TOOLS = [
    {
        "name": "dc_design_session",
        "description": "启动 Dick & Carey 教学系统设计完整流程（dc-design 模式）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_type": {"type": "string", "description": "用户类型：K12教师/高校教师/职教教师/企业培训师"},
                "scenario": {"type": "string", "description": "教学场景：新课设计/单元设计/课程设计/培训项目设计"},
                "subject": {"type": "string", "description": "学科"},
                "grade_level": {"type": "string", "description": "年级"},
                "topic": {"type": "string", "description": "课题"},
                "teacher_inputs": {"type": "object", "description": "教师提供的学情、媒体、设备等信息"},
                "source_documents": {"type": "array", "items": {"type": "string"}, "description": "教师上传的课标/教材/教研资料路径"},
                "education_scope": {"type": "string", "enum": ["k12_info_technology", "k12_nine_subjects"], "description": "教学范围：历史 v1 信息科技，或 v3 中国 K12 九学科"},
                "v1": {"type": "boolean", "description": "使用本地 v1 信息科技核心；未提供时保留历史 MCP 兼容行为"},
                "v3": {"type": "boolean", "description": "使用 v3 中国 K12 九学科核心；支持语文、数学、英语、物理、化学、生物、历史、地理、政治"},
                "subject_id": {"type": "string", "description": "v3 学科 ID：chinese、mathematics、english、physics、chemistry、biology、history、geography、politics"},
                "mode": {"type": "string", "enum": ["standard_fast", "collaborative"], "description": "课标约束快速设计或完整协同设计"},
                "stage": {"type": "string", "description": "小学、初中或普通高中"},
                "textbook_version": {"type": "string", "description": "教材版本，商业教材全文只在教师本机使用"},
                "unit": {"type": "string", "description": "教材单元/章节位置"},
                "periods": {"type": ["string", "number"], "description": "课时数"},
                "class_profile": {"type": "object", "description": "匿名班级共性学情，不得包含学生身份信息"},
                "equipment": {"type": "string", "description": "设备和软件环境"},
                "workspace": {"type": "string", "description": "教师本机私有工作区"},
                "output_dir": {"type": "string", "description": "输出目录，默认 exports/phase8"}
            },
            "required": ["grade_level", "topic"],
            "anyOf": [
                {"required": ["subject"]},
                {"required": ["subject_id"]}
            ]
        }
    },
    {
        "name": "dc_review_session",
        "description": "评审已有教学设计（dc-review 模式），输出发现和建议，不修改原项目",
        "inputSchema": {
            "type": "object",
            "properties": {
                "existing_design_project_path": {"type": "string", "description": "已有设计项目 JSON 文件路径（与 existing_design_project 二选一）"},
                "existing_design_project": {"type": "object", "description": "已有设计项目数据对象（与 existing_design_project_path 二选一）"},
                "education_scope": {"type": "string", "enum": ["k12_info_technology", "k12_nine_subjects"], "description": "教学范围：历史 v1 信息科技，或 v3 中国 K12 九学科"},
                "v1": {"type": "boolean", "description": "使用本地 v1 评审核心"},
                "v3": {"type": "boolean", "description": "使用 v3 九学科评审核心"},
                "workspace": {"type": "string", "description": "教师本机私有工作区"},
                "output_dir": {"type": "string", "description": "输出目录，默认 exports/phase8"}
            },
            "anyOf": [
                {"required": ["existing_design_project_path"]},
                {"required": ["existing_design_project"]}
            ]
        }
    },
    {
        "name": "dc_revise_session",
        "description": "根据反馈修改教学设计（dc-revise 模式），先影响分析再修改再重检一致性",
        "inputSchema": {
            "type": "object",
            "properties": {
                "existing_design_project_path": {"type": "string", "description": "已有设计项目 JSON 文件路径（与 existing_design_project 二选一）"},
                "existing_design_project": {"type": "object", "description": "已有设计项目数据对象（与 existing_design_project_path 二选一）"},
                "feedback_or_revision_data": {"type": "object", "description": "教师反馈或修改数据，必须包含 feedback_type 和 items"},
                "education_scope": {"type": "string", "enum": ["k12_info_technology", "k12_nine_subjects"], "description": "教学范围：历史 v1 信息科技，或 v3 中国 K12 九学科"},
                "v1": {"type": "boolean", "description": "使用本地 v1 修改核心"},
                "v3": {"type": "boolean", "description": "使用 v3 九学科修改核心"},
                "workspace": {"type": "string", "description": "教师本机私有工作区"},
                "output_dir": {"type": "string", "description": "输出目录，默认 exports/phase8"}
            },
            "required": ["feedback_or_revision_data"],
            "anyOf": [
                {"required": ["existing_design_project_path"]},
                {"required": ["existing_design_project"]}
            ]
        }
    },
    {
        "name": "dc_export_package",
        "description": "导出教学系统设计包为 Word/Excel/JSON/Markdown 文件。必须提供 project_path（JSON 文件路径）或 project（项目数据对象）之一。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {"type": "string", "description": "项目 JSON 文件的完整路径（与 project 二选一）"},
                "project": {"type": "object", "description": "项目数据对象（与 project_path 二选一）"},
                "education_scope": {"type": "string", "enum": ["k12_info_technology", "k12_nine_subjects"], "description": "教学范围：历史 v1 信息科技，或 v3 中国 K12 九学科"},
                "v1": {"type": "boolean", "description": "使用本地 v1 导出核心"},
                "v3": {"type": "boolean", "description": "使用 v3 九学科导出核心"},
                "workspace": {"type": "string", "description": "教师本机私有工作区"},
                "output_dir": {"type": "string", "description": "输出目录，默认 exports/phase8"}
            },
            "anyOf": [
                {"required": ["project_path"]},
                {"required": ["project"]}
            ]
        }
    }
]


@server.list_tools()
async def list_tools():
    return [Tool(**tool) for tool in TOOLS]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """调用工具 - 真实调用 agent_session"""
    # Copy arguments to avoid mutating the caller's dict
    args = dict(arguments or {})

    try:
        if name == "dc_design_session":
            output_dir = args.pop("output_dir", "exports/phase8")
            if _is_v1_request(args):
                from tools.v1_orchestrator import run_v1_design
                workspace = args.pop("workspace", None)
                args.pop("v1", None)
                result = run_v1_design(args, output_dir, workspace)
            elif _is_v3_request(args):
                from tools.v3_orchestrator import run_v3_design
                workspace = args.pop("workspace", None)
                args.pop("v3", None)
                result = run_v3_design(args, output_dir, workspace)
            else:
                from tools.agent_session import run_agent_session
                args["mode"] = "dc-design"
                result = run_agent_session(args, output_dir)

        elif name == "dc_review_session":
            output_dir = args.pop("output_dir", "exports/phase8")
            if _is_v1_request(args):
                from tools.v1_orchestrator import run_v1_review
                workspace = args.pop("workspace", None)
                args.pop("v1", None)
                source = args.pop("existing_design_project_path", None) or args.pop("existing_design_project", None)
                result = run_v1_review(source, output_dir, workspace)
            elif _is_v3_request(args):
                from tools.v3_orchestrator import run_v3_review
                workspace = args.pop("workspace", None)
                args.pop("v3", None)
                source = args.pop("existing_design_project_path", None) or args.pop("existing_design_project", None)
                result = run_v3_review(source, output_dir, workspace)
            else:
                from tools.agent_session import run_agent_session
                args["mode"] = "dc-review"
                result = run_agent_session(args, output_dir)

        elif name == "dc_revise_session":
            output_dir = args.pop("output_dir", "exports/phase8")
            if _is_v1_request(args):
                from tools.v1_orchestrator import run_v1_revise
                workspace = args.pop("workspace", None)
                args.pop("v1", None)
                source = args.pop("existing_design_project_path", None) or args.pop("existing_design_project", None)
                feedback = args.pop("feedback_or_revision_data", {})
                result = run_v1_revise(source, feedback, output_dir, workspace)
            elif _is_v3_request(args):
                from tools.v3_orchestrator import run_v3_revise
                workspace = args.pop("workspace", None)
                args.pop("v3", None)
                source = args.pop("existing_design_project_path", None) or args.pop("existing_design_project", None)
                feedback = args.pop("feedback_or_revision_data", {})
                result = run_v3_revise(source, feedback, output_dir, workspace)
            else:
                from tools.agent_session import run_agent_session
                args["mode"] = "dc-revise"
                result = run_agent_session(args, output_dir)

        elif name == "dc_export_package":
            from tools.document_exporter import export_all
            project_path = args.get("project_path")
            project_obj = args.get("project")
            output_dir = args.get("output_dir", "exports/phase8")
            use_v1 = _is_v1_request(args) or (isinstance(project_obj, dict) and project_obj.get("education_scope") == "k12_info_technology")
            use_v3 = _is_v3_request(args) or (isinstance(project_obj, dict) and project_obj.get("education_scope") == "k12_nine_subjects")

            # Must have project_path or project
            if not project_path and not project_obj:
                result = {
                    "status": "error",
                    "export_status": "failed",
                    "errors": ["必须提供 project_path 或 project 参数"],
                    "export_errors": ["必须提供 project_path 或 project 参数"],
                    "warnings": [],
                    "files": {},
                }
            elif project_path:
                # Load project from file
                if not os.path.exists(project_path):
                    result = {
                        "status": "error",
                        "export_status": "failed",
                        "errors": [f"project_path 文件不存在: {project_path}"],
                        "export_errors": [f"project_path 文件不存在: {project_path}"],
                        "warnings": [],
                        "files": {},
                    }
                else:
                    try:
                        with open(project_path, "r", encoding="utf-8") as f:
                            project_obj = json.load(f)
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        result = {
                            "status": "error",
                            "export_status": "failed",
                            "errors": [f"project_path JSON 解析失败: {str(e)}"],
                            "export_errors": [f"project_path JSON 解析失败: {str(e)}"],
                            "warnings": [],
                            "files": {},
                        }
                    else:
                        os.makedirs(output_dir, exist_ok=True)
                        use_v1 = use_v1 or (isinstance(project_obj, dict) and project_obj.get("education_scope") == "k12_info_technology")
                        use_v3 = use_v3 or (isinstance(project_obj, dict) and project_obj.get("education_scope") == "k12_nine_subjects")
                        if use_v1:
                            from tools.v1_orchestrator import _export_v1
                            result = _normalize_v1_export_result(_export_v1(project_obj, output_dir, args.get("workspace")))
                        elif use_v3:
                            from tools.v3_orchestrator import _export_v3_project
                            result = _normalize_v3_export_result(_export_v3_project(project_obj, output_dir, include_documents=True))
                        else:
                            raw = export_all(project_obj, output_dir)
                            result = _normalize_export_result(raw)
            else:
                os.makedirs(output_dir, exist_ok=True)
                if use_v1:
                    from tools.v1_orchestrator import _export_v1
                    result = _normalize_v1_export_result(_export_v1(project_obj, output_dir, args.get("workspace")))
                elif use_v3:
                    from tools.v3_orchestrator import _export_v3_project
                    result = _normalize_v3_export_result(_export_v3_project(project_obj, output_dir, include_documents=True))
                else:
                    raw = export_all(project_obj, output_dir)
                    result = _normalize_export_result(raw)

        else:
            result = {"error": f"Unknown tool: {name}"}

        # Serialize result (remove non-serializable items)
        serializable = json.loads(json.dumps(result, default=str))

        return [TextContent(
            type="text",
            text=json.dumps(serializable, ensure_ascii=False, indent=2)
        )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "tool": name,
                "status": "error",
                "error": str(e),
                "input": arguments
            }, ensure_ascii=False, indent=2)
        )]


if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(main())
