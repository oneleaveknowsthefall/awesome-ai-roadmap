"""Book compilation tests use tiny repositories, not a second copy of the book."""

import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "build_book.py"
SPEC = importlib.util.spec_from_file_location("build_book", SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


class BookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.first = "docs/llm/01-foundations/01-first.md"
        self.second = "docs/llm/02-second/02-second.md"
        self.third = "docs/agent/01-foundations/01-agent.md"
        self.manifest = {
            "schema_version": 1, "language": "zh-CN", "edition": "draft-test",
            "title": "测试书稿", "chapter_count": 3,
            "source_url": "https://example.org/repository/blob/main/",
            "front_matter": [
                {"id": "title-page", "path": "docs/book/title-page.md"},
                {"id": "preface", "path": "docs/book/preface.md"},
            ],
            "parts": [
                {"id": "llm", "title": "大语言模型", "chapters": [
                    {"id": "llm-01", "path": self.first},
                    {"id": "llm-02", "path": self.second},
                ]},
                {"id": "agent", "title": "智能体", "chapters": [
                    {"id": "agent-01", "path": self.third},
                ]},
            ],
            "back_matter": [
                {"id": "acknowledgments", "path": "docs/book/acknowledgments.md"},
                {"id": "colophon", "path": "docs/book/colophon.md"},
            ],
        }
        self.write("docs/book/title-page.md", "---\ndescription: 扉页\n---\n\n# 测试书稿\n")
        self.write("docs/book/preface.md", "# 前言\n\n[作者说明](colophon.md)\n")
        self.write("docs/book/acknowledgments.md", "# 致谢\n\n谢谢读者。\n<!-- 待作者填真实姓名 -->\n")
        self.write("docs/book/colophon.md", "# 作者与许可\n\nPolo Li，CC BY 4.0。\n")
        self.write(self.first, "# 第一章：模型\n\n## 1.1 机制\n\n正文。\n")
        self.write(self.second, "# 第二章：推理\n\n## 2.1 机制\n\n正文。\n")
        self.write(self.third, "# 第一章：智能体\n\n## 1.1 机制\n\n正文。\n")
        self.write("docs/llm/README.md", "# 语言模型\n\n网站目录，不是正文。\n")
        self.write("docs/llm/01-foundations/README.md", "# 基础\n\n网站模块。\n")
        self.write("docs/README.md", "# 网站目录\n")
        self.save_manifest()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def save_manifest(self):
        self.write(builder.DEFAULT_MANIFEST, json.dumps(self.manifest, ensure_ascii=False))

    def book(self):
        return builder.Book(self.root)

    def test_order_numbering_toc_and_no_duplicate_body(self):
        text = self.book().assemble()
        labels = re.findall(r"^## (第.+篇 第\d+章：.+)$", text, re.M)
        self.assertEqual(labels, ["第一篇 第1章：模型", "第一篇 第2章：推理", "第二篇 第1章：智能体"])
        self.assertEqual(text.count("\n正文。"), 3)
        self.assertIn("[第一篇 第2章：推理](#llm-02)", text)
        self.assertLess(text.index("# 测试书稿"), text.index("# 目录"))
        self.assertLess(text.index("# 目录"), text.index("# 前言"))
        self.assertLess(text.index("# 致谢"), text.index("# 作者与许可"))
        self.assertNotIn("description:", text)
        self.assertNotIn("待作者填真实姓名", text)
        self.assertNotIn("网站目录，不是正文", text)
        self.assertEqual(text.count("Polo Li"), 1)
        anchors = re.findall(r'<a id="([^"]+)"></a>', text)
        self.assertEqual(len(anchors), len(set(anchors)))
        links = re.findall(r"\]\(#([^)]+)\)", text)
        self.assertFalse(set(links) - set(anchors))

    def test_cross_chapter_same_chapter_index_and_front_back_links(self):
        self.write(self.first, "# 第一章：模型\n\n## 1.1 机制\n\n"
                   "[本节](#11-机制) [本章](#第一章模型)\n"
                   "[下一章](../02-second/02-second.md#21-机制)\n"
                   "[另一篇](../../agent/01-foundations/01-agent.md)\n"
                   "[全书](../../README.md) [本篇](../README.md)\n"
                   "[模块](README.md) [后附页](../../book/colophon.md)\n")
        text = self.book().assemble()
        for expected in ("[本节](#llm-01-s1-1)", "[本章](#llm-01)",
                         "[下一章](#llm-02-s2-1)", "[另一篇](#agent-01)",
                         "[全书](#contents)", "[本篇](#part-llm)",
                         "[后附页](#colophon)", "[作者说明](#colophon)"):
            self.assertIn(expected, text)
        self.assertIn("https://example.org/repository/blob/main/docs/llm/01-foundations/README.md", text)

    def test_inline_code_in_headings_keeps_spacing_and_complete_fragment(self):
        self.write(self.first, "# 第一章：`LLM` 模型\n\n## 1.1 `KV Cache` 与缓存\n\n"
                   "[本节](#11-kv-cache-与缓存)\n")
        text = self.book().assemble()
        self.assertIn("## 第一篇 第1章：`LLM` 模型", text)
        self.assertIn("### 1.1 `KV Cache` 与缓存", text)
        self.assertIn("[本节](#llm-01-s1-1)", text)

    def test_repeated_headings_get_unique_anchors_and_source_aliases(self):
        self.write(self.first, "# 第一章：模型\n\n## 参考资料\n\nA\n\n## 参考资料\n\n"
                   "[第二处](#参考资料-1)\n")
        text = self.book().assemble()
        self.assertIn('[第二处](#llm-01-extra-02)', text)

    def test_fences_inline_code_math_and_comments_are_not_rewritten(self):
        protected = (
            "````markdown\n# 假标题\n```python\n[坏路径](missing.md)\n```\n"
            "<!-- 代码里的注释必须保留 -->\n````\n\n"
            "~~~text\n[另一个](missing.md)\n~~~\n\n"
            "`[内联](missing.md)` 和 `` `[代码](missing.md)` ``。\n\n"
            "$$\nA[x](y) = B\n$$\n\n"
            "公式 $A[x](y)$ 不应变成链接。\n\n"
            "    [缩进代码](missing.md)\n"
        )
        self.write(self.first, "# 第一章：模型\n\n" + protected + "\n<!-- 不应出现\n注释结束 -->\n")
        text = self.book().assemble()
        self.assertIn(protected.strip(), text)
        self.assertNotIn("不应出现", text)

    def test_reference_links_are_namespaced_and_destinations_rewritten(self):
        self.write(self.first, "# 第一章：模型\n\n[第二章][ref] [ref] [ref][]\n\n"
                   '[ref]: ../02-second/02-second.md "标题"\n')
        self.write(self.second, "# 第二章：推理\n\n[ref]\n\n[ref]: https://example.org/other\n")
        text = self.book().assemble()
        definitions = re.findall(r"^\[([^]]+)\]: (.+)$", text, re.M)
        self.assertEqual(len(definitions), 2)
        self.assertNotEqual(definitions[0][0], definitions[1][0])
        self.assertEqual(definitions[0][1], '#llm-02 "标题"')
        self.assertIn(f"[第二章][{definitions[0][0]}]", text)
        self.assertEqual(text.count(f"[ref][{definitions[0][0]}]"), 2)

    def test_assets_titles_encoded_paths_and_html(self):
        self.write("docs/assets/图 (1).svg", "<svg>asset</svg>")
        self.write(self.first, '# 第一章：模型\n\n'
                   '![图](<../../assets/图 (1).svg> "图标题")\n'
                   '[下载](../../assets/%E5%9B%BE%20%281%29.svg)\n'
                   '<img src="../../assets/%E5%9B%BE%20%281%29.svg" alt="图">\n'
                   '<a href="../02-second/02-second.md">下一章</a>\n'
                   '[外链](https://example.org/a_(b)?q=x#z "标题")\n')
        book = self.book()
        text = book.assemble()
        encoded = "assets/docs/assets/%E5%9B%BE%20%281%29.svg"
        self.assertIn(f'![图](<{encoded}> "图标题")', text)
        self.assertIn(f'<img src="{encoded}" alt="图">', text)
        self.assertIn('<a href="#llm-02">下一章</a>', text)
        self.assertIn('[外链](https://example.org/a_(b)?q=x#z "标题")', text)
        output = self.root / "book/zh-CN/generated/manuscript.md"
        book.write(output, text)
        self.assertEqual((output.parent / "assets/docs/assets/图 (1).svg").read_text(), "<svg>asset</svg>")
        receipt = json.loads(output.with_suffix(".build.json").read_text())
        self.assertEqual(receipt["manuscript_sha256"], builder.digest(text.encode()))
        self.assertIn("docs/assets/图 (1).svg", receipt["asset_sha256"])
        before = output.with_suffix(".build.json").read_bytes()
        book.write(output, text)
        self.assertEqual(output.with_suffix(".build.json").read_bytes(), before)

    def test_narrow_footer_removal_keeps_citations_and_access_notes(self):
        self.write(self.first, "# 第一章：模型\n\n## 参考资料\n\n"
                   "- [第三方论文](https://example.org/paper)\n\n"
                   "审校口径：截至 2026-09-08；价格仍需核对。原创文字与图示：Polo Li，CC BY 4.0。\n\n"
                   "返回 [FDE 模块目录](README.md)。\n")
        text = self.book().assemble()
        self.assertIn("价格仍需核对。", text)
        self.assertIn("[第三方论文](https://example.org/paper)", text)
        self.assertNotIn("返回 [FDE", text)
        self.assertEqual(text.count("Polo Li"), 1)

    def test_malformed_manifests(self):
        mutations = (
            lambda m: m.update(schema_version=2),
            lambda m: m.update(schema_version=True),
            lambda m: m.update(language="en"),
            lambda m: m.update(chapter_count=4),
            lambda m: m.update(unexpected=True),
            lambda m: m.update(parts=None),
            lambda m: m["parts"][0].update(chapters=[]),
            lambda m: m["parts"][0]["chapters"].reverse(),
            lambda m: m["parts"][0]["chapters"].pop(),
            lambda m: m["parts"][0]["chapters"].append(m["parts"][0]["chapters"][0]),
            lambda m: m["parts"][0]["chapters"][1].update(id="llm-01"),
            lambda m: m["parts"][0]["chapters"][1].update(path=self.third),
            lambda m: m["parts"][0]["chapters"][0].update(path="../outside.md"),
            lambda m: m["parts"][0]["chapters"][0].update(path="/etc/passwd"),
            lambda m: m["parts"][0]["chapters"][0].update(path="./" + self.first),
            lambda m: m["parts"][0]["chapters"][0].update(path="docs\\bad.md"),
            lambda m: m["parts"][0]["chapters"][0].update(path="docs/missing.md"),
            lambda m: m["parts"][0]["chapters"][0].update(id="contains space"),
            lambda m: m["parts"][0]["chapters"][0].update(id="part-llm"),
            lambda m: m.update(title="wrong book"),
        )
        original = json.dumps(self.manifest)
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.manifest = json.loads(original)
                mutation(self.manifest)
                self.save_manifest()
                with self.assertRaises(builder.BookError):
                    self.book()

    def test_new_unlisted_topic_is_not_silently_omitted(self):
        self.write("docs/unlisted/01-module/01-new.md", "# 第一章：新主题\n")
        with self.assertRaisesRegex(builder.BookError, "coverage mismatch"):
            self.book()

    def test_duplicate_json_keys_are_rejected(self):
        self.write(builder.DEFAULT_MANIFEST, '{"schema_version": 1, "schema_version": 2}')
        with self.assertRaisesRegex(builder.BookError, "duplicate JSON key"):
            self.book()

    def test_bad_source_paths_and_local_links(self):
        bodies = (
            "[坏链接](missing.md)", "[坏锚点](#does-not-exist)",
            "[坏跨章](../02-second/02-second.md#does-not-exist)",
            "[越界](../../../../outside.md)", "[根路径](/etc/passwd)",
            "[查询](../README.md?query=x)", "[协议](file:///etc/passwd)",
            "[坏链接](../README.md", "[坏链接](<../README.md)",
            "[坏引用][missing]", "[^footnote]", '<img src=missing.svg>',
            '<img srcset="a.svg 1x, b.svg 2x">', '<a id="source-anchor"></a>',
            "Copyright Polo Li, all rights reserved.",
            "```python\n未闭合", "$$\n未闭合", "`未闭合",
            "<!-- 未闭合", "## 1.1 A\n\n## 1.1 B\n",
        )
        for body in bodies:
            with self.subTest(body=body):
                self.write(self.first, "# 第一章：模型\n\n" + body + "\n")
                with self.assertRaises(builder.BookError):
                    self.book().assemble()
        self.write(self.first, "---\ndescription: 未闭合\n# 第一章：模型\n")
        with self.assertRaisesRegex(builder.BookError, "YAML"):
            self.book()

    def test_source_symlink_and_output_overwrite_are_rejected(self):
        (self.root / self.first).unlink()
        (self.root / self.first).symlink_to(self.root / self.second)
        with self.assertRaisesRegex(builder.BookError, "symlink"):
            self.book()
        (self.root / self.first).unlink()
        self.write(self.first, "# 第一章：模型\n")
        book = self.book()
        text = book.assemble()
        with self.assertRaisesRegex(builder.BookError, "read-only"):
            book.write(self.root / self.first, text)
        output = self.root / "book/zh-CN/generated/manuscript.md"
        output.parent.mkdir(parents=True)
        output.with_suffix(".build.json").symlink_to(self.root / self.first)
        with self.assertRaisesRegex(builder.BookError, "receipt"):
            book.write(output, text)
        self.assertFalse(output.exists())

    def test_cli_check_index_regeneration_and_determinism(self):
        with patch.object(builder, "ROOT", self.root), patch("sys.stdout"), patch("sys.stderr"):
            self.assertEqual(builder.main(["--check"]), 0)
            self.assertFalse((self.root / "book/zh-CN/generated").exists())
            self.assertEqual(builder.main(["--check", "--check-index"]), 1)
            self.assertEqual(builder.main(["--write-index"]), 0)
            self.assertEqual(builder.main(["--check", "--check-index"]), 0)
            self.assertEqual(builder.main(["--check", "--output", "not-written.md"]), 1)
            index_before = (self.root / builder.INDEX_PATH).read_bytes()
            self.write(self.first, "# 第一章：模型新标题\n")
            self.assertEqual(builder.main(["--check", "--check-index"]), 1)
            self.assertEqual(builder.main(["--write-index"]), 0)
            self.assertNotEqual((self.root / builder.INDEX_PATH).read_bytes(), index_before)
            self.assertEqual(builder.main([]), 0)
            output = self.root / "book/zh-CN/generated/manuscript.md"
            before = output.read_bytes()
            self.assertEqual(builder.main([]), 0)
            self.assertEqual(output.read_bytes(), before)

class RepositoryBookTests(unittest.TestCase):
    def test_real_manifest_covers_nine_topics_and_143_chapters(self):
        book = builder.Book()
        self.assertEqual([part["id"] for part, _ in book.parts],
                         ["llm", "multimodal", "tools", "rag", "agent", "frameworks",
                          "engineering", "safety", "fde"])
        self.assertEqual([len(documents) for _, documents in book.parts],
                         [23, 10, 15, 22, 25, 23, 13, 10, 2])
        manuscript = book.assemble()
        self.assertEqual(len(re.findall(r"^## 第.+篇 第\d+章：", manuscript, re.M)), 143)
        self.assertEqual(manuscript.count("Polo Li"), 1)
        anchors = re.findall(r'<a id="([^"]+)"></a>', manuscript)
        self.assertEqual(len(anchors), len(set(anchors)))
        self.assertFalse(set(re.findall(r"\]\(#([^)]+)\)", manuscript)) - set(anchors))
        for document in book.documents.values():
            with self.subTest(path=document.path):
                source_code_math = [content for protected, content in document.chunks if protected]
                assembled_code_math = [content for protected, content in
                                       builder.segments(book.render_document(document), document.path)
                                       if protected]
                self.assertEqual(assembled_code_math, source_code_math)


if __name__ == "__main__":
    unittest.main()
