"""Lightweight EPUB regressions: no Pandoc, Java, Node or browser prerequisite."""

import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_epub as epub


def header(level, identifier, title):
    return {"t": "Header", "c": [level, [identifier, [], []], [epub.string(title)]]}


class EpubTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def test_anchors_and_code_math_boundaries(self):
        protected = (
            '````markdown\n<a id="fake"></a>\n\n# 假标题\n```mermaid\nA-->B\n```\n````\n\n'
            '`$code$` `` `$$` ``\n\n    $indented$\n\n'
        )
        source = '<a id="real"></a>\n\n## 中文 `KV` 标题\n\n' + protected + "$x$\n\n$$\ny\n$$\n"
        result = epub.prepare_markdown(source)
        self.assertIn("## 中文 `KV` 标题 {#real}", result)
        self.assertIn(protected, result)
        self.assertEqual(epub.source_counts(source), {"inline": 1, "display": 1})

    def test_actual_mermaid_not_nested_example(self):
        source = "```mermaid\nA-->B\n```\n\n````markdown\n```mermaid\nC-->D\n```\n````\n"
        self.assertEqual(epub.source_counts(source), {"mermaid": 1})

    def test_ast_preserves_examples_removes_manual_contents_and_matter_split(self):
        manifest = self.root / "manifest.json"
        manifest.write_text("{}", encoding="utf-8")
        book = SimpleNamespace(
            anchors={"title-page", "contents", "preface", "preface-extra", "part-one", "one-01"},
            front=[SimpleNamespace(id="title-page"), SimpleNamespace(id="preface")], back=[],
            manifest={"title": "测试", "language": "zh-CN"}, manifest_path=manifest,
        )
        code = {"t": "CodeBlock", "c": [["", ["python"], []], 'print("$x$")\n```mermaid\n']}
        ast = {"blocks": [
            header(1, "title-page", "测试"), header(1, "contents", "目录"),
            {"t": "Para", "c": [epub.string("人工目录正文")]},
            header(1, "preface", "前言"), header(2, "preface-extra", "读法"),
            header(1, "part-one", "第一篇"), header(2, "one-01", "第一篇 第1章"),
            code,
            {"t": "Math", "c": [{"t": "InlineMath"}, "x_i"]},
            {"t": "Math", "c": [{"t": "InlineMath"}, "x_i"]},
        ]}
        jobs, count = epub.prepare_ast(ast, book, self.root)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(count, {"inline": 2})
        self.assertNotIn("人工目录正文", json.dumps(ast, ensure_ascii=False))
        self.assertEqual(ast["blocks"][2]["c"][0], 3)
        self.assertIn(code, ast["blocks"])
        rendered = {"results": [{"key": jobs[0]["key"], "kind": "inline", "file": "formula.png",
                                 "width": 40, "height": 20, "tiles": []}]}
        result = epub.apply_images(ast, rendered)
        self.assertIn(code, result["blocks"])
        self.assertEqual(sum(node["t"] == "Image" for node in epub.walk(result)), 2)
        self.assertNotIn("_render", json.dumps(result))
        self.assertIn("width:2.00em", json.dumps(result))

    def test_local_non_ascii_asset_and_missing_remote_fail(self):
        asset = self.root / "图片.png"
        asset.write_bytes(b"png")
        self.assertEqual(epub.local_resource("%E5%9B%BE%E7%89%87.png", self.root), asset)
        for url in ("missing.png", "../outside.png", "https://example.com/image.png", "//example.com/a"):
            with self.subTest(url=url), self.assertRaises(epub.BookError):
                epub.local_resource(url, self.root)

    def test_raw_html_rejects_active_or_remote_resources(self):
        for html in ('<script>alert(1)</script>', '<img src="https://example.com/x.png">',
                     '<div onclick="x()">', '<img srcset="x 2x">', '<svg></svg>'):
            with self.subTest(html=html), self.assertRaises(epub.BookError):
                epub.HTMLResources(self.root).feed(html)
        epub.HTMLResources(self.root).feed('<br/><a href="https://example.com">参考</a>')

    def test_output_must_not_replace_sources_or_unowned_directory(self):
        source = self.root / "docs/source.md"
        source.parent.mkdir()
        source.write_text("正文", encoding="utf-8")
        with self.assertRaisesRegex(epub.BookError, "read-only"):
            epub.output_path(source, self.root)
        owned = self.root / "book/zh-CN/generated/epub"
        owned.mkdir(parents=True)
        with self.assertRaisesRegex(epub.BookError, "not an EPUB"):
            epub.output_path(owned, self.root)
        (owned / "build.json").write_text('{"builder":"build_epub.py"}', encoding="utf-8")
        self.assertEqual(epub.output_path(owned, self.root), owned)
        linked = owned.parent / "linked"
        linked.symlink_to(owned, target_is_directory=True)
        with self.assertRaisesRegex(epub.BookError, "symlinks"):
            epub.output_path(linked, self.root)
        self.assertEqual(source.read_text(encoding="utf-8"), "正文")

    def test_failed_publication_restores_previous_build(self):
        target = self.root / "epub"
        target.mkdir()
        (target / "old.epub").write_bytes(b"previous")
        staging = self.root / "stage"
        staging.mkdir()
        original = Path.rename

        def fail_new(path, destination):
            if path == staging:
                raise OSError("disk failure")
            return original(path, destination)

        with patch.object(Path, "rename", fail_new), self.assertRaisesRegex(OSError, "disk failure"):
            epub.publish_directory(staging, target)
        self.assertEqual((target / "old.epub").read_bytes(), b"previous")

    def test_failed_command_is_not_success_shaped(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("missing")):
            with self.assertRaisesRegex(epub.BookError, "missing tool"):
                epub.run(["pandoc"])

    def make_package(self):
        book = SimpleNamespace(
            manifest={"language": "zh-CN", "title": "测试", "chapter_count": 2},
            front=[SimpleNamespace(id="title-page")],
            parts=[({"id": "one"}, [SimpleNamespace(id="one-01"), SimpleNamespace(id="one-02")])],
            back=[SimpleNamespace(id="colophon")],
            anchors={"title-page", "contents", "part-one", "one-01", "one-02", "中文节", "colophon"},
        )
        order = epub.reading_order(book)
        entries = {"mimetype": b"application/epub+zip",
                   "META-INF/container.xml": b'<container><rootfiles><rootfile full-path="EPUB/content.opf"/></rootfiles></container>'}
        items, spine = [], []
        for number, identifier in enumerate(order):
            name = f"text/ch{number}.xhtml"
            body = f'<h1 id="{identifier}">{identifier}</h1>'
            if identifier == "one-01":
                body += '<a href="#%E4%B8%AD%E6%96%87%E8%8A%82">跨章非ASCII</a><a href="#contents">目录</a>'
            if identifier == "one-02":
                body += '<h2 id="中文节">中文节</h2>'
            if identifier == "contents":
                body = '<nav epub:type="toc" id="toc"><ol>' + "".join(
                    f'<li><a href="ch{i}.xhtml#{key}">{key}</a></li>'
                    for i, key in enumerate(order) if key != "contents") + '</ol></nav>'
            entries["EPUB/" + name] = (
                f'<html xmlns="{epub.XHTML}" xmlns:epub="http://www.idpf.org/2007/ops">'
                f'<head><title>测试</title></head><body>{body}</body></html>').encode()
            items.append(f'<item id="i{number}" href="{name}" media-type="application/xhtml+xml"/>')
            spine.append(f'<itemref idref="i{number}"/>')
        entries["EPUB/content.opf"] = (
            f'<package xmlns="{epub.OPF}" xmlns:dc="{epub.DC}" version="3.0">'
            '<metadata><dc:title>测试</dc:title><dc:language>zh-CN</dc:language></metadata>'
            '<manifest>' + "".join(items) + '</manifest><spine>' + "".join(spine)
            + '</spine></package>').encode()
        output = self.root / "fixture.epub"
        self.write_package(output, entries)
        return output, book

    def write_package(self, output, entries):
        with zipfile.ZipFile(output, "w") as archive:
            for name, data in entries.items():
                archive.writestr(name, data)

    def test_cross_file_unicode_fragments_native_toc_and_order(self):
        output, book = self.make_package()
        self.assertEqual(epub.repair_links(output, book=book), 2)
        report = epub.audit_epub(output, book, {})
        self.assertEqual(report["chapters"], 2)
        self.assertEqual(report["spine_documents"], 6)
        with zipfile.ZipFile(output) as archive:
            chapter = archive.read("EPUB/text/ch3.xhtml").decode()
        self.assertIn('href="ch4.xhtml#中文节"', chapter)
        self.assertIn('href="ch1.xhtml#contents"', chapter)

    def test_missing_fragments_and_bad_language_fail(self):
        output, book = self.make_package()
        epub.repair_links(output, book=book)
        entries = epub.read_package(output)
        entries["EPUB/text/ch3.xhtml"] = entries["EPUB/text/ch3.xhtml"].replace(
            "ch4.xhtml#中文节".encode(), b"ch4.xhtml#missing")
        self.write_package(output, entries)
        with self.assertRaisesRegex(epub.BookError, "missing EPUB fragment"):
            epub.audit_epub(output, book)
        output, book = self.make_package()
        epub.repair_links(output, book=book)
        book.manifest["language"] = "en"
        with self.assertRaisesRegex(epub.BookError, "incorrect book language"):
            epub.audit_epub(output, book)

    def test_missing_resource_script_and_formula_coverage_fail(self):
        for injection, expected in (
            ('<img src="missing.png" alt="图片"/>', "missing EPUB link/resource"),
            ('<script>1</script>', "non-static XHTML"),
            ('<img src="https://example.com/a.png" alt="图片"/>', "remote/active resource"),
        ):
            output, book = self.make_package()
            epub.repair_links(output, book=book)
            entries = epub.read_package(output)
            entries["EPUB/text/ch3.xhtml"] = entries["EPUB/text/ch3.xhtml"].replace(
                b"</body>", injection.encode() + b"</body>")
            self.write_package(output, entries)
            with self.subTest(injection=injection), self.assertRaisesRegex(epub.BookError, expected):
                epub.audit_epub(output, book)
        output, book = self.make_package()
        epub.repair_links(output, book=book)
        with self.assertRaisesRegex(epub.BookError, "coverage mismatch"):
            epub.audit_epub(output, book, {"inline": 1})

    def test_bad_mimetype_fails(self):
        output, _ = self.make_package()
        entries = epub.read_package(output)
        entries["mimetype"] = b"text/plain"
        self.write_package(output, entries)
        with self.assertRaisesRegex(epub.BookError, "mimetype"):
            epub.read_package(output)


if __name__ == "__main__":
    unittest.main()
