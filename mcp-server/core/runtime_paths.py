"""Local storage paths for the v1 teacher workspace.

The plugin package is read-only product code. Teacher documents, profiles,
indexes, projects and exports live in a separate local workspace so an update
of the plugin cannot overwrite them.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def workspace_root(explicit: str | os.PathLike[str] | None = None) -> Path:
    """Return the local ``.dc-designer`` workspace, without creating it."""
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
    elif os.environ.get("DC_DESIGNER_HOME"):
        candidate = Path(os.environ["DC_DESIGNER_HOME"]).expanduser().resolve()
    elif os.environ.get("DC_TEACHER_WORKSPACE"):
        candidate = (Path(os.environ["DC_TEACHER_WORKSPACE"]).expanduser() / ".dc-designer").resolve()
    else:
        candidate = (Path.home() / ".dc-designer").resolve()

    # An explicit path is allowed for tests and advanced users. The default
    # path must never silently resolve inside the installed plugin directory.
    if candidate == PACKAGE_ROOT or PACKAGE_ROOT in candidate.parents:
        if not explicit and not os.environ.get("DC_DESIGNER_HOME"):
            return (Path.home() / ".dc-designer").resolve()
    return candidate


def workspace_dirs(explicit: str | os.PathLike[str] | None = None) -> dict[str, Path]:
    root = workspace_root(explicit)
    return {
        "root": root,
        "profile": root / "profile",
        "knowledge": root / "knowledge",
        "knowledge_documents": root / "knowledge" / "documents",
        "indexes": root / "indexes",
        "projects": root / "projects",
        "exports": root / "exports",
    }


def ensure_workspace(explicit: str | os.PathLike[str] | None = None) -> dict[str, Path]:
    dirs = workspace_dirs(explicit)
    try:
        for path in dirs.values():
            path.mkdir(parents=True, exist_ok=True)
        probe = dirs["root"] / f".write-probe-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return dirs
    except OSError:
        # Some managed Windows runtimes expose the user's home directory as
        # read-only to sandboxed processes. A real user-specified workspace
        # must still fail loudly; only the implicit default gets a local temp
        # fallback so read-only diagnostics and tests remain usable.
        if explicit or os.environ.get("DC_DESIGNER_HOME") or os.environ.get("DC_TEACHER_WORKSPACE"):
            raise
        fallback = Path(tempfile.gettempdir()) / "dc-designer"
        fallback_dirs = workspace_dirs(fallback)
        for path in fallback_dirs.values():
            path.mkdir(parents=True, exist_ok=True)
        return fallback_dirs
