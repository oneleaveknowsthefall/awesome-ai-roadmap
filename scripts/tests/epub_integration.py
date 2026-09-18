"""Explicit EPUB-only integration suite; never discovered by the website workflow."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_epub as epub
import test_build_book as fixtures


class EpubIntegration(unittest.TestCase):
    def test_real_pandoc_renderer_package_links_and_failure_preservation(self):
        self.assertTrue(epub.PANDOC.is_file(), "install EPUB tools before running this explicit suite")
        fixture = fixtures.BookTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        diagram = ('```mermaid\nflowchart LR\n A["中文检索"] --> B["生成答案"]'
                   ' --> C["核对事实与来源"] --> D["人工审阅与交付"] --> E["复盘与更新"]\n```\n')
        fixture.write(fixture.first, "# 第一章：模型\n\n## 1.1 中文机制\n\n"
                      "[跨章中文标题](../02-second/02-second.md#21-机制) "
                      "[目录](../../README.md)\n\n"
                      '`$not_math$` 和 `` `$$` ``。\n\n'
                      "    $indented_code$\n\n"
                      '````markdown\n```mermaid\nnot a real diagram\n```\n$x$\n````\n\n'
                      "$x_i^2$。\n\n$$\n\\frac{1}{2}\n$$\n\n" + diagram)
        fixture.write(fixture.third, "# 第一章：智能体\n\n## 1.1 机制\n\n" + diagram)
        original = {path: path.read_bytes() for path in fixture.root.rglob("*.md")}
        output = fixture.root / "book/zh-CN/generated/epub"
        real_run = epub.run

        def run(command, **kwargs):
            if list(command) == ["git", "rev-parse", "HEAD"]:
                return "integration-fixture\n"
            return real_run(command, **kwargs)

        def build():
            with patch.object(epub, "Book", lambda **_: fixture.book()), \
                    patch.object(epub, "ROOT", fixture.root), patch.object(epub, "run", run):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as errors:
                    result = epub.main(["--output", str(output)])
                return result, errors.getvalue()

        result, errors = build()
        self.assertEqual(result, 0, errors)
        self.assertEqual({path: path.read_bytes() for path in original}, original)
        report = json.loads((output / "build.json").read_text(encoding="utf-8"))
        self.assertEqual(report["occurrences"], {"inline": 1, "display": 1, "mermaid": 2})
        self.assertEqual(report["unique_rendered"]["mermaid"], 1)
        self.assertEqual(report["nonlinear_figure_documents"], 2)
        self.assertNotIn("diagram-detail", report["image_occurrences"])
        self.assertGreater(report["supplemental_image_occurrences"]["diagram-detail"], 0)
        filename = output / (epub.BOOK_NAME + ".epub")
        previous = filename.read_bytes()
        with zipfile.ZipFile(filename) as archive:
            trees = {name: ET.fromstring(archive.read(name)) for name in archive.namelist()
                     if name.endswith(".xhtml")}
        origin = {}
        for name, tree in trees.items():
            for node in tree.iter():
                if node.get("id", "").startswith("figure-"):
                    origin[node.get("id")] = name
            if "/text/" in name:
                self.assertFalse(tree.findall(".//h:img[@class='diagram-detail']", epub.NS))
        return_targets = []
        for name, tree in trees.items():
            if "/figures/" in name:
                link = tree.find(".//h:a", epub.NS)
                target, fragment = epub.package_target(name, link.get("href"))
                self.assertEqual(origin[fragment], target)
                return_targets.append(target)
        self.assertEqual(len(set(return_targets)), 2, "shared PNG must return to the right chapter")
        code = "\n".join(node.text or "" for tree in trees.values()
                         for node in tree.findall(".//h:code", epub.NS))
        self.assertIn("$not_math$", code)
        self.assertIn("$indented_code$", code)
        self.assertIn("not a real diagram", code)
        fixture.write(fixture.first, "# 第一章：模型\n\n$\\notARealCommand{x}$\n")
        result, errors = build()
        self.assertEqual(result, 1)
        self.assertIn("Undefined control sequence", errors)
        self.assertEqual(filename.read_bytes(), previous, "a failed rebuild must preserve last valid EPUB")
        fixture.write(fixture.first, "# 第一章：模型\n\n![远程图](https://example.org/image.png)\n")
        result, errors = build()
        self.assertEqual(result, 1)
        self.assertIn("cannot embed remote", errors)
        self.assertEqual(filename.read_bytes(), previous)


if __name__ == "__main__":
    unittest.main()
