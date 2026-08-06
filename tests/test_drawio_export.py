"""
Draw.io Skill Graph Exporter Tests

Tests the .drawio XML generation from skill graph data.
"""
import sys
import os
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mcp-server'))

SEED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '..', 'examples', 'mvp_algorithm_seed_with_context.json')


def _get_skill_graph():
    """Get a real skill_graph from the MVP pipeline."""
    from tools.pipeline import run_mvp_pipeline_with_materials
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_mvp_pipeline_with_materials(SEED_PATH, tmpdir)
        project = result['project']
        return project.get('skill_graph', {})


def _make_minimal_skill_graph():
    """Create a minimal skill_graph for edge-case testing."""
    return {
        "goal_node": {
            "node_id": "goal_test",
            "node_type": "goal",
            "label": "测试教学目标",
        },
        "goal_steps": [
            {"step_id": "step_1", "description": "第一步：理解概念", "order": 1,
             "learning_type": "intellectual_skill", "status": "candidate"},
            {"step_id": "step_2", "description": "第二步：应用方法", "order": 2,
             "learning_type": "intellectual_skill", "status": "candidate"},
        ],
        "subordinate_skills": [
            {"skill_id": "sub_1", "name": "识别关键信息", "description": "从材料中识别关键信息",
             "learning_type": "intellectual_skill", "linked_step_id": "step_1",
             "parent_step_id": "step_1", "status": "candidate"},
            {"skill_id": "sub_2", "name": "选择策略方法", "description": "根据问题选择合适策略",
             "learning_type": "intellectual_skill", "linked_step_id": "step_2",
             "parent_step_id": "step_2", "status": "candidate"},
        ],
        "entry_behaviours": [
            {"entry_id": "entry_1", "name": "基本阅读能力",
             "description": "能阅读理解材料内容", "learning_type": "verbal_information",
             "supports_skill_ids": ["sub_1"], "status": "candidate"},
        ],
        "nodes": [],
        "edges": [
            {"from": "goal_test", "to": "step_1", "edge_type": "goal_to_step"},
            {"from": "step_1", "to": "step_2", "edge_type": "step_sequence"},
            {"from": "step_1", "to": "sub_1", "edge_type": "step_requires_skill"},
            {"from": "step_2", "to": "sub_2", "edge_type": "step_requires_skill"},
            {"from": "entry_1", "to": "sub_1", "edge_type": "entry_prerequisite"},
        ],
        "metadata": {
            "node_count": 6,
            "edge_count": 5,
            "goal_type": "intellectual_skill",
        },
    }


class TestDrawioExportMinimal(unittest.TestCase):
    """Tests using a minimal hand-crafted skill_graph."""

    def setUp(self):
        self.sg = _make_minimal_skill_graph()

    def test_drawio_valid_xml(self):
        """XML is well-formed and has correct structure."""
        from tools.drawio_exporter import generate_drawio_xml
        xml_str = generate_drawio_xml(self.sg)

        # Basic structure checks
        self.assertTrue(xml_str.startswith('<?xml version="1.0"'))
        self.assertIn('<mxfile', xml_str)
        self.assertIn('<mxGraphModel', xml_str)
        self.assertIn('<root>', xml_str)
        self.assertIn('</mxfile>', xml_str)

        # Parse to verify well-formedness (strip XML declaration)
        body = xml_str.split('?>', 1)[1]
        root = ET.fromstring(body)
        self.assertIsNotNone(root)

    def test_drawio_contains_all_nodes(self):
        """XML contains vertex cells for all nodes."""
        from tools.drawio_exporter import generate_drawio_xml
        xml_str = generate_drawio_xml(self.sg)

        # Count vertex cells
        vertex_count = xml_str.count('vertex="1"')
        expected = 1 + len(self.sg["goal_steps"]) + len(self.sg["subordinate_skills"]) + len(self.sg["entry_behaviours"])
        self.assertEqual(vertex_count, expected,
                         f"Expected {expected} vertices, got {vertex_count}")

    def test_drawio_contains_all_edges(self):
        """XML contains edge cells for all edges."""
        from tools.drawio_exporter import generate_drawio_xml
        xml_str = generate_drawio_xml(self.sg)

        edge_count = xml_str.count('edge="1"')
        self.assertEqual(edge_count, len(self.sg["edges"]),
                         f"Expected {len(self.sg['edges'])} edges, got {edge_count}")

    def test_drawio_node_ids_match(self):
        """Node IDs in XML match skill_graph node_ids with n_ prefix."""
        from tools.drawio_exporter import generate_drawio_xml
        xml_str = generate_drawio_xml(self.sg)

        # Check goal node
        self.assertIn('id="n_goal_test"', xml_str)
        # Check step nodes
        self.assertIn('id="n_step_1"', xml_str)
        self.assertIn('id="n_step_2"', xml_str)
        # Check subskill nodes
        self.assertIn('id="n_sub_1"', xml_str)
        self.assertIn('id="n_sub_2"', xml_str)
        # Check entry nodes
        self.assertIn('id="n_entry_1"', xml_str)

    def test_drawio_edge_connections(self):
        """Edges in XML have correct source/target with n_ prefix."""
        from tools.drawio_exporter import generate_drawio_xml
        xml_str = generate_drawio_xml(self.sg)

        # Check a specific edge: goal -> step_1
        self.assertIn('source="n_goal_test"', xml_str)
        self.assertIn('target="n_step_1"', xml_str)
        # Check entry -> subskill edge
        self.assertIn('source="n_entry_1"', xml_str)
        self.assertIn('target="n_sub_1"', xml_str)

    def test_drawio_color_coding(self):
        """Node styles contain expected colors."""
        from tools.drawio_exporter import generate_drawio_xml
        xml_str = generate_drawio_xml(self.sg)

        # Goal: dark blue
        self.assertIn('#1B4F72', xml_str)
        # Steps: light blue
        self.assertIn('#5DADE2', xml_str)
        # Subordinate skills: green
        self.assertIn('#82E0AA', xml_str)
        # Entry behaviours: yellow
        self.assertIn('#F9E79F', xml_str)

    def test_drawio_file_write(self):
        """export_skill_graph_drawio writes a valid file."""
        from tools.drawio_exporter import export_skill_graph_drawio
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_skill_graph.drawio")
            result = export_skill_graph_drawio(self.sg, path)

            self.assertTrue(result["exported"])
            self.assertEqual(result["path"], path)
            self.assertGreater(result["size"], 0)
            self.assertTrue(os.path.exists(path))

            # Verify file content is valid XML
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            body = content.split('?>', 1)[1]
            ET.fromstring(body)

    def test_drawio_empty_graph(self):
        """Empty skill_graph produces valid XML with only goal node."""
        from tools.drawio_exporter import generate_drawio_xml
        empty_sg = {
            "goal_node": {"node_id": "g1", "label": "空目标"},
            "goal_steps": [],
            "subordinate_skills": [],
            "entry_behaviours": [],
            "edges": [],
        }
        xml_str = generate_drawio_xml(empty_sg)

        self.assertIn('<mxfile', xml_str)
        self.assertIn('vertex="1"', xml_str)
        self.assertEqual(xml_str.count('edge="1"'), 0)

    def test_drawio_chinese_text_escaping(self):
        """Chinese text with special chars is properly escaped."""
        from tools.drawio_exporter import generate_drawio_xml
        sg = dict(self.sg)
        sg["goal_node"] = {
            "node_id": "g_cn",
            "label": '目标包含&特殊<字符>"引号',
        }
        xml_str = generate_drawio_xml(sg)

        # Should not contain raw special chars in attribute values
        # The escaped forms should be present
        self.assertIn('&amp;', xml_str)
        self.assertIn('&lt;', xml_str)
        self.assertIn('&gt;', xml_str)

    def test_drawio_layout_no_overlap(self):
        """Nodes in the same tier do not overlap horizontally."""
        from tools.drawio_exporter import generate_drawio_xml
        xml_str = generate_drawio_xml(self.sg)

        # Parse and extract all vertex geometries
        body = xml_str.split('?>', 1)[1]
        root = ET.fromstring(body)

        # Collect geometries by inferring tier from style color
        geometries = []
        for cell in root.iter('mxCell'):
            if cell.get('vertex') == '1':
                geom = cell.find('mxGeometry')
                if geom is not None:
                    x = float(geom.get('x', 0))
                    w = float(geom.get('width', 0))
                    y = float(geom.get('y', 0))
                    geometries.append((x, w, y))

        # Check that no two nodes at the same Y level overlap
        # Group by approximate Y (within 30 units)
        y_groups = {}
        for x, w, y in geometries:
            matched = False
            for gy in y_groups:
                if abs(y - gy) < 30:
                    y_groups[gy].append((x, w))
                    matched = True
                    break
            if not matched:
                y_groups[y] = [(x, w)]

        for y_level, nodes in y_groups.items():
            nodes.sort()
            for i in range(len(nodes) - 1):
                x1, w1 = nodes[i]
                x2, _ = nodes[i + 1]
                self.assertGreaterEqual(x2, x1 + w1 - 1,
                    f"Overlap at y~{y_level}: node ending at {x1+w1} overlaps next at {x2}")


class TestDrawioExportReal(unittest.TestCase):
    """Tests using a real skill_graph from the MVP pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.sg = _get_skill_graph()

    def test_drawio_valid_xml(self):
        """Real skill_graph produces valid XML."""
        from tools.drawio_exporter import generate_drawio_xml
        xml_str = generate_drawio_xml(self.sg)

        self.assertTrue(xml_str.startswith('<?xml'))
        self.assertIn('<mxfile', xml_str)
        body = xml_str.split('?>', 1)[1]
        root = ET.fromstring(body)
        self.assertIsNotNone(root)

    def test_drawio_has_nodes(self):
        """Real skill_graph produces vertex cells."""
        from tools.drawio_exporter import generate_drawio_xml
        xml_str = generate_drawio_xml(self.sg)

        vertex_count = xml_str.count('vertex="1"')
        self.assertGreater(vertex_count, 0, "No vertex cells generated")

    def test_drawio_has_edges(self):
        """Real skill_graph produces edge cells."""
        from tools.drawio_exporter import generate_drawio_xml
        xml_str = generate_drawio_xml(self.sg)

        edge_count = xml_str.count('edge="1"')
        self.assertGreater(edge_count, 0, "No edge cells generated")

    def test_drawio_file_export(self):
        """Real skill_graph exports to a .drawio file."""
        from tools.drawio_exporter import export_skill_graph_drawio
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "real_skill_graph.drawio")
            result = export_skill_graph_drawio(self.sg, path)

            self.assertTrue(result["exported"])
            self.assertGreater(result["size"], 500)


if __name__ == "__main__":
    unittest.main()
