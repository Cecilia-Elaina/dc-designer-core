"""Contract tests for the static DC Designer product website."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class TestPublicSiteAssets(unittest.TestCase):
    def test_required_site_assets_exist(self):
        for name in ("index.html", "styles.css", "site.js", "favicon.svg"):
            path = SITE / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 100, name)

    def test_html_uses_relative_assets_and_has_core_sections(self):
        html = (SITE / "index.html").read_text(encoding="utf-8")
        self.assertIn('<html lang="zh-CN">', html)
        self.assertIn('href="styles.css"', html)
        self.assertIn('src="site.js"', html)
        self.assertEqual(len(re.findall(r"<h1\b", html)), 1)
        for marker in ("DC DESIGNER CORE", "Dick–Carey", "STANDARD FAST", "COLLABORATIVE", "#install", "复制给 Codex"):
            self.assertIn(marker, html)

    def test_hero_copy_matches_requested_lines(self):
        html = (SITE / "index.html").read_text(encoding="utf-8")
        self.assertIn("<h1><span>从课标到课堂</span><em>让教学设计真正可执行</em></h1>", html)
        hero_text = re.search(r"<h1>(.*?)</h1>", html, re.S).group(1)
        self.assertNotRegex(hero_text, r"[，。！？、；：,.!?]")
        self.assertIn("DICK–CAREY 模型", html)
        self.assertNotIn("DICK–CAREY / 中国 K–12 信息科技", html)

    def test_hero_preview_has_separated_title_and_equal_flow_nodes(self):
        html = (SITE / "index.html").read_text(encoding="utf-8")
        css = (SITE / "styles.css").read_text(encoding="utf-8")
        self.assertIn('<div class="report-title"><span>Python</span><em>循环程序设计</em></div>', html)
        self.assertEqual(html.count('class="report-node"'), 4)
        self.assertIn(".report-flow {", css)
        self.assertIn("grid-template-columns: repeat(4, minmax(0, 1fr))", css)
        self.assertNotIn("position: absolute", css[css.index(".report-flow {"):css.index(".report-flow-line {")])

    def test_hero_index_uses_requested_labels(self):
        html = (SITE / "index.html").read_text(encoding="utf-8")
        for label in ("01", "系统化", "可追溯", "向下阅读"):
            self.assertIn(f">{label}<", html)
        self.assertNotIn(">本地优先<", html)

    def test_information_architecture_is_merged_and_graphical(self):
        html = (SITE / "index.html").read_text(encoding="utf-8")
        for obsolete_heading in ("WHY A SYSTEM", "TWO WAYS IN", "SOURCE WITH CONTEXT", "QUESTIONS"):
            self.assertNotIn(obsolete_heading, html)
        for section_id in ("approach", "workflow", "evidence", "outputs", "install"):
            self.assertIn(f'id="{section_id}"', html)
        self.assertEqual(len(re.findall(r'<article class="flow-stage[^\"]*" tabindex="0">', html)), 10)
        self.assertEqual(html.count('class="stage-note"'), 10)
        self.assertIn('textbook-flow-map', html)
        self.assertIn('class="flow-routes"', html)
        self.assertIn('route-revise-bus', html)
        self.assertNotIn('这一步做什么', html)
        self.assertNotIn('class="implementation-rail"', html)
        self.assertIn('class="plugin-architecture"', html)
        self.assertIn('class="architecture-center"', html)
        self.assertIn('class="architecture-routes"', html)
        self.assertIn('data-principle-visual', html)
        self.assertIn('data-work-mode', html)
        self.assertEqual(html.count('data-disclosure-button'), 2)
        self.assertNotIn('principle-toggle', html)
        self.assertNotIn('work-mode-toggle', html)
        self.assertIn('id="principle-map"', html)
        self.assertIn('id="work-mode-options"', html)
        self.assertIn('class="evidence-chain"', html)
        self.assertEqual(html.count('class="evidence-node'), 4)
        for evidence_class in ("evidence-node-official", "evidence-node-teacher", "evidence-node-context", "evidence-node-confirm"):
            self.assertIn(evidence_class, html)
        self.assertIn('class="evidence-gate"', html)
        self.assertIn('class="gate-route"', html)
        self.assertNotIn('class="gate-line"', html)
        self.assertNotIn('class="evidence-status"', html)
        self.assertEqual(html.count('class="graph-link '), 3)
        self.assertIn('branch-a">', html)
        self.assertIn('branch-b">', html)
        self.assertIn('branch-c">', html)
        self.assertNotIn('graph-connector', html)
        self.assertIn('class="copy-explainer"', html)
        self.assertIn("grid-template-columns: repeat(6, minmax(0, 1fr))", (SITE / "styles.css").read_text(encoding="utf-8"))
        self.assertNotIn("↗", html)
        self.assertIn('class="report-showcase-card', html)
        self.assertNotIn('INSTALL PROMPT', html)
        self.assertIn('class="github-icon"', html)
        self.assertNotIn("GitHub ↗", html)

    def test_model_and_evidence_copy_are_teacher_facing(self):
        html = (SITE / "index.html").read_text(encoding="utf-8")
        self.assertIn("一份教学设计，不应只是几页文字。它需要说明教学决策从何而来、课堂如何展开，也要用清晰的评价证据判断学生是否达成学习目标。", html)
        self.assertIn("Dick–Carey 模型", html)
        self.assertIn("如何被插件带进课堂", html)
        self.assertIn("智能体协作", html)
        self.assertIn("真实课堂", html)
        self.assertIn("来源有边界，教师有确认权", html)

    def test_method_interactions_use_hover_and_architecture_layout(self):
        css = (SITE / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".work-mode-visual:hover .work-mode-options", css)
        self.assertIn(".work-mode-core { position: absolute", css)
        self.assertIn(".textbook-flow-map {", css)
        self.assertIn("grid-template-columns: repeat(5, minmax(0, 1fr))", css)
        self.assertIn(".architecture-map {", css)

    def test_site_does_not_expose_old_workbench_or_internal_enums(self):
        content = "\n".join(path.read_text(encoding="utf-8") for path in SITE.iterdir() if path.is_file())
        for forbidden in ("新建设计项目", "教师工作台", "candidate", "sufficient", "cognitive_strategy", "authentic_programming_task"):
            self.assertNotIn(forbidden, content)

    def test_editorial_constraints_are_present(self):
        css = (SITE / "styles.css").read_text(encoding="utf-8")
        self.assertIn("#f9f8f6", css.lower())
        self.assertIn("#1c1c1c", css.lower())
        self.assertNotIn("linear-gradient", css.lower())
        self.assertNotIn("box-shadow", css.lower())
        self.assertNotIn("border-radius", css.lower())
        self.assertIn("prefers-reduced-motion", css)

    def test_install_prompt_is_consistent_and_actionable(self):
        js = (SITE / "site.js").read_text(encoding="utf-8")
        match = re.search(r'const INSTALL_PROMPT = "(.+?)";', js)
        self.assertIsNotNone(match)
        prompt = match.group(1)
        self.assertIn("Plugins", prompt)
        self.assertIn("https://github.com/Cecilia-Elaina/dc-designer-core", prompt)
        self.assertIn("导入 marketplace", prompt)
        self.assertIn("dc-info-tech-design", prompt)
        self.assertIn("若当前账户无权限", prompt)

    def test_marketplace_manifest_points_to_plugin_repository_root(self):
        manifest = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "dc-designer-marketplace")
        self.assertEqual(len(manifest["plugins"]), 1)
        plugin = manifest["plugins"][0]
        self.assertEqual(plugin["name"], "dc-designer-core")
        self.assertEqual(plugin["source"]["source"], "url")
        self.assertEqual(plugin["source"]["url"], "https://github.com/Cecilia-Elaina/dc-designer-core.git")

    def test_pages_workflow_publishes_site(self):
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        self.assertIn("actions/upload-pages-artifact@v3", workflow)
        self.assertIn("path: site", workflow)
        self.assertIn("actions/deploy-pages@v4", workflow)


class TestOldWorkBenchRemoval(unittest.TestCase):
    def test_old_workbench_files_are_removed(self):
        for relative in ("web/index.html", "web/styles.css", "web/app.js", "scripts/dc_web.py", "scripts/web_smoke.py"):
            self.assertFalse((ROOT / relative).exists(), relative)


if __name__ == "__main__":
    unittest.main()
