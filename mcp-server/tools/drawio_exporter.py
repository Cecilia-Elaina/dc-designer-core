"""
Draw.io Skill Graph Exporter

Generates .drawio XML files from Dick & Carey skill graph data.
The output can be opened and edited in draw.io / diagrams.net.

All functions are pure / deterministic -- no AI calls.
"""

import os
import sys
from xml.sax.saxutils import escape as _xml_escape

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_THIS_DIR)
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from core.ids import gen_skill_id


# ===================================================================
# Constants
# ===================================================================

# Node type -> draw.io style string
_NODE_STYLES = {
    "goal": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#1B4F72;fontColor=#FFFFFF;"
        "strokeColor=#154360;fontSize=13;fontStyle=1;shadow=1;"
    ),
    "goal_step": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#5DADE2;fontColor=#FFFFFF;"
        "strokeColor=#2E86C1;fontSize=11;"
    ),
    "subordinate_skill": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#82E0AA;fontColor=#1E8449;"
        "strokeColor=#27AE60;fontSize=10;"
    ),
    "entry_behavior": (
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#F9E79F;fontColor=#7D6608;"
        "strokeColor=#D4AC0D;fontSize=10;"
    ),
}

# Edge type -> draw.io style string
_EDGE_STYLES = {
    "goal_to_step": (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
        "jettySize=auto;html=1;strokeColor=#1B4F72;strokeWidth=2;"
        "endArrow=block;endFill=1;"
    ),
    "step_sequence": (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
        "jettySize=auto;html=1;strokeColor=#2E86C1;strokeWidth=1.5;"
        "endArrow=block;endFill=1;"
    ),
    "step_requires_skill": (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
        "jettySize=auto;html=1;strokeColor=#27AE60;strokeWidth=1;"
        "dashed=1;endArrow=block;endFill=1;"
    ),
    "entry_prerequisite": (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
        "jettySize=auto;html=1;strokeColor=#D4AC0D;strokeWidth=1;"
        "dashed=1;endArrow=block;endFill=1;"
    ),
}

# Default style for unknown edge types
_EDGE_STYLE_DEFAULT = (
    "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
    "jettySize=auto;html=1;strokeColor=#666666;strokeWidth=1;"
    "endArrow=block;endFill=1;"
)

# Tier Y positions
_TIER_Y = {
    "goal": 50,
    "goal_step": 220,
    "subordinate_skill": 420,
    "entry_behavior": 600,
}

# Node dimensions (base)
_NODE_DIMS = {
    "goal": (280, 60),
    "goal_step": (210, 50),
    "subordinate_skill": (190, 45),
    "entry_behavior": (190, 40),
}

# Tier ordering for layout
_TIER_ORDER = ["goal", "goal_step", "subordinate_skill", "entry_behavior"]


def _get_node_id(node: dict) -> str:
    """Extract the canonical node ID from any node type.

    Steps use 'step_id', subskills use 'skill_id', entries use 'entry_id',
    goal uses 'node_id'.  Falls back to auto-generated ID.
    """
    return (node.get("node_id")
            or node.get("step_id")
            or node.get("skill_id")
            or node.get("entry_id")
            or gen_skill_id())


# ===================================================================
# Public API
# ===================================================================

def export_skill_graph_drawio(skill_graph: dict, output_path: str) -> dict:
    """Export a skill graph as a .drawio XML file.

    Parameters
    ----------
    skill_graph : dict
        Skill graph data structure as produced by
        ``tools.skill_graph.build_skill_graph``.
    output_path : str
        File path for the output ``.drawio`` file.

    Returns
    -------
    dict with keys: ``exported`` (bool), ``path`` (str), ``size`` (int).
    """
    # The v1 file is a multi-page workbook. ``generate_drawio_xml`` remains
    # available as a backwards-compatible single-page function for old data.
    xml_str = generate_drawio_workbook_xml(skill_graph)

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(xml_str)

    file_size = os.path.getsize(output_path)
    return {
        "exported": True,
        "path": output_path,
        "size": file_size,
    }


def generate_drawio_xml(skill_graph: dict) -> str:
    """Generate a complete .drawio XML string from a skill graph.

    This is a pure function (no I/O) suitable for unit testing.

    Parameters
    ----------
    skill_graph : dict
        Skill graph with keys: goal_node, goal_steps, subordinate_skills,
        entry_behaviours (or entry_behaviors), nodes, edges.

    Returns
    -------
    str containing valid .drawio XML.
    """
    # Normalize entry behaviours key
    entry_key = "entry_behaviours" if "entry_behaviours" in skill_graph else "entry_behaviors"
    entries = skill_graph.get(entry_key, [])

    goal_node = skill_graph.get("goal_node", {})
    goal_steps = skill_graph.get("goal_steps", [])
    subskills = skill_graph.get("subordinate_skills", [])
    edges = skill_graph.get("edges", [])

    # Calculate layout positions
    layout = _calculate_layout(goal_node, goal_steps, subskills, entries)

    # Build XML cells
    cells = []

    # Default draw.io root cells
    cells.append('<mxCell id="0"/>')
    cells.append('<mxCell id="1" parent="0"/>')

    # Vertex cells
    _add_vertex(cells, goal_node, layout)
    for step in goal_steps:
        _add_vertex(cells, step, layout)
    for sk in subskills:
        _add_vertex(cells, sk, layout)
    for eb in entries:
        _add_vertex(cells, eb, layout)

    # Edge cells
    for idx, edge in enumerate(edges):
        _add_edge(cells, edge, idx)

    # Assemble XML
    cells_xml = "\n        ".join(cells)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" type="device">
  <diagram name="教学分析流图" id="dc_skill_graph">
    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="900" math="0" shadow="0">
      <root>
        {cells_xml}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""


# ===================================================================
# Layout algorithm
# ===================================================================

def _calculate_layout(
    goal_node: dict,
    goal_steps: list,
    subskills: list,
    entries: list,
) -> dict:
    """Calculate x, y, width, height for every node.

    Returns a dict mapping node_id -> {"x", "y", "width", "height"}.
    """
    layout = {}

    # Determine which tiers are present
    tiers = [
        ("goal", [goal_node] if goal_node else []),
        ("goal_step", goal_steps),
        ("subordinate_skill", subskills),
        ("entry_behavior", entries),
    ]

    # Filter out empty tiers
    active_tiers = [(name, nodes) for name, nodes in tiers if nodes]

    if not active_tiers:
        return layout

    # Calculate canvas width based on the widest tier
    max_nodes_in_tier = max(len(nodes) for _, nodes in active_tiers)
    canvas_width = max(900, max_nodes_in_tier * 240)

    # Recalculate Y positions for active tiers only
    tier_count = len(active_tiers)
    y_spacing = 550 / max(tier_count - 1, 1) if tier_count > 1 else 0

    for tier_idx, (tier_name, tier_nodes) in enumerate(active_tiers):
        base_y = 50 + tier_idx * y_spacing
        base_w, base_h = _NODE_DIMS.get(tier_name, (180, 40))

        n = len(tier_nodes)
        if n == 0:
            continue

        spacing = canvas_width / (n + 1)

        for i, node in enumerate(tier_nodes):
            node_id = _get_node_id(node)
            label = node.get("label", node.get("description", node.get("name", "")))

            # Adjust width for long labels
            eff_len = _effective_text_length(label)
            extra_w = min(max(0, eff_len - 12) * 5, 140)
            w = base_w + extra_w
            h = base_h

            # Wrap long labels -- increase height
            lines = _count_wrap_lines(label)
            if lines > 1:
                h = base_h + (lines - 1) * 16

            x = spacing * (i + 1) - w / 2

            # Clamp to canvas bounds
            x = max(10, min(x, canvas_width - w - 10))

            layout[node_id] = {
                "x": round(x, 1),
                "y": round(base_y, 1),
                "width": round(w, 1),
                "height": round(h, 1),
            }

    return layout


# ===================================================================
# XML cell builders
# ===================================================================

def _add_vertex(cells: list, node: dict, layout: dict) -> None:
    """Append a vertex mxCell to the cells list."""
    node_id = _get_node_id(node)
    cell_id = f"n_{node_id}"

    # Determine node type
    node_type = node.get("node_type", "")
    if not node_type:
        # Infer from available fields
        if "goal_id" in node or node.get("order") is not None:
            if "order" in node:
                node_type = "goal_step"
            else:
                node_type = "goal"
        elif "skill_id" in node or "linked_step_id" in node:
            node_type = "subordinate_skill"
        elif "entry_id" in node or "supports_skill_ids" in node:
            node_type = "entry_behavior"
        else:
            node_type = "goal_step"

    label = node.get("label", node.get("description", node.get("name", "")))
    wrapped = _wrap_label(label)
    escaped = _escape_xml(wrapped)
    style = _NODE_STYLES.get(node_type, _NODE_STYLES["goal_step"])

    pos = layout.get(node_id, {"x": 100, "y": 100, "width": 180, "height": 45})

    cells.append(
        f'<mxCell id="{cell_id}" value="{escaped}" style="{style}" '
        f'vertex="1" parent="1">'
        f'<mxGeometry x="{pos["x"]}" y="{pos["y"]}" '
        f'width="{pos["width"]}" height="{pos["height"]}" as="geometry"/>'
        f'</mxCell>'
    )


def _add_edge(cells: list, edge: dict, idx: int) -> None:
    """Append an edge mxCell to the cells list."""
    from_id = edge.get("from", "")
    to_id = edge.get("to", "")
    edge_type = edge.get("edge_type", "")

    cell_id = f"e_{idx}"
    source = f"n_{from_id}"
    target = f"n_{to_id}"
    style = _EDGE_STYLES.get(edge_type, _EDGE_STYLE_DEFAULT)

    cells.append(
        f'<mxCell id="{cell_id}" style="{style}" '
        f'edge="1" source="{source}" target="{target}" parent="1">'
        f'<mxGeometry relative="1" as="geometry"/>'
        f'</mxCell>'
    )


# ===================================================================
# Text helpers
# ===================================================================

def _wrap_label(text: str, max_effective: int = 20) -> str:
    """Wrap text for draw.io display using <br> line breaks.

    Chinese characters count as 2 effective width units,
    Latin characters as 1.  Lines are broken at natural punctuation
    when possible, otherwise at the character limit.

    Maximum 4 lines; excess is truncated with '...'.
    """
    if not text:
        return ""

    # Truncate very long text
    if len(text) > 80:
        text = text[:77] + "..."

    lines = []
    current_line = []
    current_eff = 0

    for ch in text:
        ch_eff = 2 if ord(ch) > 127 else 1

        if current_eff + ch_eff > max_effective and current_line:
            lines.append("".join(current_line))
            current_line = [ch]
            current_eff = ch_eff
        else:
            current_line.append(ch)
            current_eff += ch_eff

        # Natural break at punctuation
        if ch in "，。、；：!！?？" and current_eff >= max_effective * 0.6:
            lines.append("".join(current_line))
            current_line = []
            current_eff = 0

    if current_line:
        lines.append("".join(current_line))

    # Limit to 4 lines
    if len(lines) > 4:
        lines = lines[:3]
        lines.append("...")

    return "<br>".join(lines)


def _effective_text_length(text: str) -> int:
    """Calculate effective display width of text (Chinese=2, Latin=1)."""
    if not text:
        return 0
    return sum(2 if ord(ch) > 127 else 1 for ch in text)


def _count_wrap_lines(text: str, max_effective: int = 20) -> int:
    """Count how many lines _wrap_label would produce."""
    if not text:
        return 1
    if len(text) > 80:
        text = text[:77] + "..."

    lines = 1
    current_eff = 0

    for ch in text:
        ch_eff = 2 if ord(ch) > 127 else 1
        if current_eff + ch_eff > max_effective:
            lines += 1
            current_eff = ch_eff
        else:
            current_eff += ch_eff

        if ch in "，。、；：!！?？" and current_eff >= max_effective * 0.6:
            lines += 1
            current_eff = 0

    return min(lines, 4)


def _escape_xml(text: str) -> str:
    """Escape text for safe embedding in XML attribute values."""
    return _xml_escape(text, {'"': "&quot;", "'": "&apos;"})


# ===================================================================
# v1 multi-page workbook exporter
# ===================================================================

_V1_NODE_STYLES = {
    "instructional_goal": "rounded=1;whiteSpace=wrap;html=1;fillColor=#4472C4;fontColor=#FFFFFF;strokeColor=#2F5496;fontStyle=1;fontSize=14;",
    "goal_step": "rounded=1;whiteSpace=wrap;html=1;fillColor=#7565E8;fontColor=#FFFFFF;strokeColor=#5145B8;fontSize=14;",
    "goal_substep": "rounded=1;whiteSpace=wrap;html=1;fillColor=#E5E0FF;fontColor=#2D245F;strokeColor=#7C3AED;fontSize=10;",
    "intellectual_skill": "rounded=1;whiteSpace=wrap;html=1;fillColor=#DDEBF7;fontColor=#1F2937;strokeColor=#5B9BD5;fontSize=10;",
    "verbal_information": "rounded=1;whiteSpace=wrap;html=1;fillColor=#E2F0D9;fontColor=#375623;strokeColor=#70AD47;fontSize=10;",
    "psychomotor_skill": "rounded=1;whiteSpace=wrap;html=1;fillColor=#FCE4D6;fontColor=#843C0C;strokeColor=#ED7D31;fontSize=10;",
    "cognitive_strategy": "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;fontColor=#7F6000;strokeColor=#BF9000;fontSize=10;",
    "attitude": "rounded=1;whiteSpace=wrap;html=1;fillColor=#F4CCCC;fontColor=#660000;strokeColor=#CC0000;fontSize=10;",
    "entry_skill": "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;fontColor=#7F6000;strokeColor=#BF9000;fontSize=10;",
    "entry_boundary": "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;fillOpacity=0;strokeColor=#7F8C8D;dashed=1;fontColor=#566573;fontSize=11;",
    "start": "ellipse;whiteSpace=wrap;html=1;fillColor=#D9EAD3;fontColor=#274E13;strokeColor=#6AA84F;fontSize=11;",
    "end": "ellipse;whiteSpace=wrap;html=1;fillColor=#F4CCCC;fontColor=#660000;strokeColor=#CC0000;fontSize=11;",
    "action": "rounded=1;whiteSpace=wrap;html=1;fillColor=#D9EAF7;fontColor=#1F2937;strokeColor=#5B9BD5;fontSize=11;",
    "decision": "rhombus=1;whiteSpace=wrap;html=1;fillColor=#4472C4;fontColor=#FFFFFF;strokeColor=#2F5496;fontSize=11;",
}

_V1_EDGE_STYLES = {
    "conditional_yes": "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#2E7D32;strokeWidth=1.5;endArrow=block;endFill=1;",
    "conditional_no": "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#C62828;strokeWidth=1.5;endArrow=block;endFill=1;",
    "prerequisite": "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#5B9BD5;dashed=1;endArrow=block;endFill=1;",
    "entry_boundary": "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#BF9000;dashed=1;endArrow=block;endFill=1;",
    "component_of": "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#7C3AED;endArrow=block;endFill=1;",
    "retry": "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#C62828;dashed=1;strokeWidth=1.5;endArrow=block;endFill=1;",
    "feedback": "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#E69138;dashed=1;endArrow=block;endFill=1;",
    "sequence": "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#2F5496;strokeWidth=1.5;endArrow=block;endFill=1;",
}


def _v1_wrap_label(value: object, max_effective: int = 28) -> str:
    """Wrap without truncation; every input character remains in the label."""
    text = str(value or "").strip()
    if not text:
        return "待确认"
    lines: list[str] = []
    current: list[str] = []
    width = 0
    for char in text:
        char_width = 2 if ord(char) > 127 else 1
        if current and width + char_width > max_effective:
            lines.append("".join(current))
            current = []
            width = 0
        current.append(char)
        width += char_width
        if char in "。；：!?！" and width >= max_effective * 0.55:
            lines.append("".join(current))
            current = []
            width = 0
    if current:
        lines.append("".join(current))
    return "<br>".join(lines)


def _v1_node_dimensions(node_type: str, label: str) -> tuple[int, int]:
    line_count = max(1, label.count("<br>") + 1)
    if node_type == "instructional_goal":
        return 460, max(78, 24 * line_count + 30)
    if node_type == "decision":
        return 210, max(110, 25 * line_count + 58)
    if node_type == "entry_boundary":
        return 190, 34
    return 220, max(62, 22 * line_count + 24)


def _v1_layout(view: dict) -> dict[str, dict]:
    nodes = list(view.get("nodes", []))
    view_id = view.get("view_id", "")
    layout: dict[str, dict] = {}
    if not nodes:
        return layout
    by_type: dict[str, list[dict]] = {}
    for node in nodes:
        by_type.setdefault(node.get("node_type", "action"), []).append(node)

    if view_id == "skill_hierarchy":
        steps = by_type.get("goal_step", [])
        column_gap = 390
        column_width = 300
        left = 80
        canvas_width = max(1500, left * 2 + max(1, len(steps)) * column_gap)
        goal = by_type.get("instructional_goal", [])
        if goal:
            node = goal[0]
            label = _v1_wrap_label(node.get("label"), 26)
            w, h = max(520, _v1_node_dimensions(node.get("node_type", ""), label)[0]), _v1_node_dimensions(node.get("node_type", ""), label)[1]
            layout[node["id"]] = {"x": (canvas_width - w) / 2, "y": 68, "width": w, "height": h}
        step_x: dict[str, float] = {}
        for index, node in enumerate(steps):
            label = _v1_wrap_label(node.get("label"), 17)
            w, h = column_width, _v1_node_dimensions(node.get("node_type", ""), label)[1]
            x = left + index * column_gap
            step_x[node["id"]] = x
            layout[node["id"]] = {"x": x, "y": 190, "width": w, "height": h}
        sub_types = {"intellectual_skill", "verbal_information", "psychomotor_skill", "cognitive_strategy", "attitude"}
        sub_by_parent: dict[str, list[dict]] = {}
        for node in nodes:
            if node.get("node_type") in sub_types:
                sub_by_parent.setdefault(node.get("parent_step_id", ""), []).append(node)
        max_subskills = max((len(items) for items in sub_by_parent.values()), default=0)
        for parent, children in sub_by_parent.items():
            base_x = step_x.get(parent, left)
            for index, node in enumerate(children):
                label = _v1_wrap_label(node.get("label"), 17)
                w, h = column_width, _v1_node_dimensions(node.get("node_type", ""), label)[1]
                layout[node["id"]] = {"x": base_x, "y": 330 + index * 108, "width": w, "height": h}
        boundary_y = 350 + max_subskills * 108
        boundary = by_type.get("entry_boundary", [])
        if boundary:
            node = boundary[0]
            layout[node["id"]] = {"x": left - 10, "y": boundary_y, "width": canvas_width - 2 * (left - 10), "height": 32}
        entries = by_type.get("entry_skill", [])
        entry_gap = column_gap
        entry_width = column_width
        for index, node in enumerate(entries):
            label = _v1_wrap_label(node.get("label"), 17)
            w, h = entry_width, _v1_node_dimensions(node.get("node_type", ""), label)[1]
            layout[node["id"]] = {"x": left + index * entry_gap, "y": boundary_y + 75, "width": w, "height": h}
        return layout

    if view_id == "goal_operation_flow":
        steps = by_type.get("goal_step", [])
        gap = 310
        for index, node in enumerate(steps):
            label = _v1_wrap_label(node.get("label"), 20)
            w, h = 280, _v1_node_dimensions(node.get("node_type", ""), label)[1]
            layout[node["id"]] = {"x": 80 + index * gap, "y": 190, "width": w, "height": h}
        goal = by_type.get("instructional_goal", [])
        if goal:
            node = goal[0]
            label = _v1_wrap_label(node.get("label"), 25)
            w, h = 420, _v1_node_dimensions(node.get("node_type", ""), label)[1]
            max_x = max((pos["x"] + pos["width"] for pos in layout.values()), default=1200)
            layout[node["id"]] = {"x": max(100, (max_x - w) / 2), "y": 42, "width": w, "height": h}
        return layout

    if view_id == "control_flow":
        main_actions = sorted(
            [node for node in by_type.get("action", []) if str(node.get("id", "")).startswith("CF-A")],
            key=lambda node: str(node.get("id", "")),
        )
        for index, node in enumerate(main_actions):
            label = _v1_wrap_label(node.get("label"), 17)
            w, h = 260, _v1_node_dimensions("action", label)[1]
            y = 180 if index < 3 else 610 + (index - 3) * 110
            x = 90 + (index if index < 3 else 2) * 330
            layout[node["id"]] = {"x": x, "y": y, "width": w, "height": h}
        starts = by_type.get("start", [])
        if starts:
            node = starts[0]
            layout[node["id"]] = {"x": 90, "y": 55, "width": 180, "height": 62}
        last_main_y = 180 if len(main_actions) <= 3 else 610 + (len(main_actions) - 4) * 110
        test_y = last_main_y + 180
        test_decision_y = test_y + 150
        debug_y = test_decision_y + 150
        decisions = by_type.get("decision", [])
        for index, node in enumerate(decisions):
            label = _v1_wrap_label(node.get("label"), 14)
            w, h = _v1_node_dimensions("decision", label)
            node_id = str(node.get("id", ""))
            if node_id == "CF-TEST-DECISION":
                x, y = 750, test_decision_y
            elif node_id == "CF-LOOP":
                x, y = 1350, 350
            else:
                x, y = 750 + index * 300, 350
            layout[node["id"]] = {"x": x, "y": y, "width": w, "height": h}
        branch_actions = [node for node in by_type.get("action", []) if str(node.get("id", "")) in {"CF-YES", "CF-NO"}]
        for node in branch_actions:
            label = _v1_wrap_label(node.get("label"), 15)
            w, h = 240, _v1_node_dimensions("action", label)[1]
            x = 1050 if node.get("id") == "CF-YES" else 420
            layout[node["id"]] = {"x": x, "y": 470, "width": w, "height": h}
        for node_id, x, y in (("CF-TEST", 750, test_y), ("CF-DEBUG", 420, debug_y)):
            node = next((item for item in by_type.get("action", []) if str(item.get("id")) == node_id), None)
            if node:
                label = _v1_wrap_label(node.get("label"), 15)
                w, h = 260, _v1_node_dimensions("action", label)[1]
                layout[node_id] = {"x": x, "y": y, "width": w, "height": h}
        ends = by_type.get("end", [])
        if ends:
            node = ends[0]
            layout[node["id"]] = {"x": 1050, "y": debug_y, "width": 180, "height": 62}
        return layout

    # Any custom view nodes are placed in a deterministic, non-overlapping row.
    for index, node in enumerate(nodes):
        label = _v1_wrap_label(node.get("label"), 18)
        w, h = _v1_node_dimensions(node.get("node_type", "action"), label)
        layout[node["id"]] = {"x": 100 + index * 300, "y": 200, "width": w, "height": h}
    return layout


def _v1_vertex(cells: list[str], node: dict, layout: dict[str, dict]) -> None:
    node_id = str(node["id"])
    node_type = node.get("node_type", "action")
    label = _v1_wrap_label(node.get("label", ""))
    # XML attributes must keep the line-break tag escaped. diagrams.net
    # decodes it and renders it as HTML because the cell style has html=1.
    escaped = _escape_xml(label)
    style = _V1_NODE_STYLES.get(node_type, _V1_NODE_STYLES["action"])
    pos = layout.get(node_id, {"x": 100, "y": 100, "width": 220, "height": 62})
    cells.append(
        f'<mxCell id="n_{_escape_xml(node_id)}" value="{escaped}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{pos["x"]}" y="{pos["y"]}" width="{pos["width"]}" height="{pos["height"]}" as="geometry"/>'
        f'</mxCell>'
    )


def _v1_edge(cells: list[str], edge: dict, index: int) -> None:
    source = str(edge.get("from", ""))
    target = str(edge.get("to", ""))
    edge_type = edge.get("edge_type", "sequence")
    style = _V1_EDGE_STYLES.get(edge_type, _V1_EDGE_STYLES["sequence"])
    label = _escape_xml(str(edge.get("label", "")))
    cells.append(
        f'<mxCell id="e_{index}" value="{label}" style="{style}" edge="1" source="n_{_escape_xml(source)}" target="n_{_escape_xml(target)}" parent="1">'
        f'<mxGeometry relative="1" as="geometry"/></mxCell>'
    )


def _v1_page_xml(view: dict, page_index: int) -> str:
    layout = _v1_layout(view)
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    for node in view.get("nodes", []):
        _v1_vertex(cells, node, layout)
    for index, edge in enumerate(view.get("edges", [])):
        _v1_edge(cells, edge, index)
    cell_text = "\n        ".join(cells)
    page_id = f"dc_{view.get('view_id', page_index)}"
    return f'''  <diagram name="{_escape_xml(view.get("title", "教学分析图"))}" id="{page_id}">
    <mxGraphModel dx="1600" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1800" pageHeight="1000" math="0" shadow="0">
      <root>
        {cell_text}
      </root>
    </mxGraphModel>
  </diagram>'''


def generate_drawio_workbook_xml(skill_graph: dict) -> str:
    """Generate a multi-page editable Draw.io workbook for v1."""
    from tools.skill_graph import build_skill_graph_views, validate_skill_graph_views

    views = build_skill_graph_views(skill_graph)
    validation = validate_skill_graph_views(views)
    # Preserve the validation result in the graph only when the caller wants
    # to inspect it; the XML itself remains a normal diagrams.net document.
    pages = []
    for index, view in enumerate(views.values(), 1):
        pages.append(_v1_page_xml(view, index))
    return '<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="app.diagrams.net" type="device" modified="2026-07-30T00:00:00.000Z" agent="dc-designer-core" version="24.7.17">\n' + "\n".join(pages) + "\n</mxfile>"


def generate_view_drawio_xml(skill_graph: dict, view_name: str) -> str:
    """Generate a one-page editable Draw.io file for one v1 graph view."""
    from tools.skill_graph import build_skill_graph_views

    view = build_skill_graph_views(skill_graph).get(view_name)
    if not view:
        raise ValueError(f"unknown skill graph view: {view_name}")
    page = _v1_page_xml(view, 1)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="app.diagrams.net" type="device" modified="2026-07-30T00:00:00.000Z" agent="dc-designer-core" version="24.7.17">\n' + page + "\n</mxfile>"


def export_skill_graph_view(skill_graph: dict, view_name: str, output_path: str) -> dict:
    """Write one independent, editable v1 graph page."""
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(generate_view_drawio_xml(skill_graph, view_name))
    return {"exported": True, "path": output_path, "size": os.path.getsize(output_path), "view": view_name}


def export_skill_graph_workbook(skill_graph: dict, output_path: str) -> dict:
    """Explicit v1 alias for callers that want to distinguish a workbook."""
    return export_skill_graph_drawio(skill_graph, output_path)
