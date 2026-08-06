"""项目数据存储工具（本地 JSON 文件）"""
import json
import os
from datetime import datetime


DEFAULT_EXPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..",
    "exports",
)


def save_project(project: dict, output_path: str | None = None) -> dict:
    """
    保存项目数据为 JSON 文件。

    Args:
        project: 项目数据字典
        output_path: 输出路径，None 则自动命名

    Returns:
        {"saved": bool, "path": str}
    """
    if output_path is None:
        os.makedirs(DEFAULT_EXPORTS_DIR, exist_ok=True)
        proj_id = project.get("project_id", "unknown")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(DEFAULT_EXPORTS_DIR, f"{proj_id}_{ts}.json")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(project, f, ensure_ascii=False, indent=2)

    return {"saved": True, "path": output_path}


def load_project(path: str) -> dict:
    """加载项目数据。"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_empty_project(user_type: str = "", scene_type: str = "") -> dict:
    """创建空项目骨架。"""
    from core.ids import gen_project_id

    return {
        "project_id": gen_project_id(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "metadata": {
            "user_type": user_type,
            "scene_type": scene_type,
            "project_name": "",
            "subject": "",
            "grade_level": "",
            "textbook": "",
            "session_info": "",
        },
        "sources": [],
        "goal": {},
        "skill_graph": {},
        "objectives": [],
        "assessment_plan": {},
        "quality_check": {},
    }
