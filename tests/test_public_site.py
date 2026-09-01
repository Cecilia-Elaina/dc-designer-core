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
