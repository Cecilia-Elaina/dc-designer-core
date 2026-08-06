"""
Export Package Tools

Provides functions for exporting completed Dick & Carey instructional design
projects into Markdown reports and JSON data files. All rendering is delegated
to core.report_renderer; file I/O is handled here.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from datetime import datetime
from core.report_renderer import (
    render_markdown_report as _core_render_markdown_report,
    render_source_trace as _core_render_source_trace,
    render_quality_summary as _core_render_quality_summary,
)
from core.project_store import save_project


# ---------------------------------------------------------------------------
# Directory for auto-generated exports
# ---------------------------------------------------------------------------

_DEFAULT_EXPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "exports",
)


# ---------------------------------------------------------------------------
# Thin delegates to core.report_renderer
# ---------------------------------------------------------------------------

def render_markdown_report(project: dict) -> str:
    """Delegate to core.report_renderer.render_markdown_report.

    Args:
        project: Complete project state dictionary.

    Returns:
        str containing the full Markdown report.
    """
    return _core_render_markdown_report(project)


def render_source_trace(sources: list) -> str:
    """Delegate to core.report_renderer.render_source_trace.

    Args:
        sources: List of source dictionaries to render as a traceability
            table.

    Returns:
        str containing a Markdown table of source traces.
    """
    return _core_render_source_trace(sources)


def render_quality_summary(alignment_report: dict) -> str:
    """Delegate to core.report_renderer.render_quality_summary.

    Args:
        alignment_report: Quality / alignment report dictionary.

    Returns:
        str containing a Markdown quality summary.
    """
    return _core_render_quality_summary(alignment_report)


# ---------------------------------------------------------------------------
# File-oriented export helpers
# ---------------------------------------------------------------------------

def export_markdown_report(project: dict, output_path: str | None = None) -> dict:
    """Export the project as a Markdown file.

    When *output_path* is ``None`` the file is written into the exports
    directory with an auto-generated name based on the project id and
    current timestamp.

    Args:
        project: Complete project state dictionary.
        output_path: Optional explicit file path.  When provided the parent
            directories are created if they do not already exist.

    Returns:
        dict with keys ``exported`` (bool), ``path`` (str), and
        ``content_length`` (int, character count of the written Markdown).
    """
    content = render_markdown_report(project)

    if output_path is None:
        os.makedirs(_DEFAULT_EXPORTS_DIR, exist_ok=True)
        proj_id = project.get("project_id", "unknown")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(_DEFAULT_EXPORTS_DIR, f"{proj_id}_{ts}.md")

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(content)

    return {
        "exported": True,
        "path": output_path,
        "content_length": len(content),
    }


def export_full_project(project: dict, output_dir: str | None = None) -> dict:
    """Export both JSON project data and Markdown report.

    Writes two files into *output_dir* (defaulting to the exports
    directory): a ``.json`` file via :func:`core.project_store.save_project`
    and a ``.md`` file via :func:`export_markdown_report`.

    Args:
        project: Complete project state dictionary.
        output_dir: Optional directory for output files.  Created
            automatically when it does not exist.

    Returns:
        dict with keys ``json_path`` (str) and ``markdown_path`` (str).
    """
    if output_dir is None:
        output_dir = _DEFAULT_EXPORTS_DIR

    os.makedirs(output_dir, exist_ok=True)

    proj_id = project.get("project_id", "unknown")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- JSON export -------------------------------------------------------
    json_path = os.path.join(output_dir, f"{proj_id}_{ts}.json")
    json_result = save_project(project, output_path=json_path)

    # --- Markdown export ---------------------------------------------------
    md_path = os.path.join(output_dir, f"{proj_id}_{ts}.md")
    md_result = export_markdown_report(project, output_path=md_path)

    return {
        "json_path": json_result["path"],
        "markdown_path": md_result["path"],
    }
