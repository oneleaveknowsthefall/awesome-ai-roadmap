import contextlib
import io
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPTS = Path(__file__).absolute().parents[1]
sys.path.insert(0, str(SCRIPTS))

import localize_zh_links as localize
from markdown_links import (
    MarkdownLinkError, is_language_switch, labeled_link_destinations,
    link_destinations, rewrite_links,
)


class MarkdownLinksTests(unittest.TestCase):
    def test_language_switch_labels_are_per_inline_link_not_per_url(self):
        text = (
            "[English](README.md)\n[正文](README.md)\n"
            "![English](README.md)\n[English]: README.md\n"
            '<a href="README.md">English</a>\n'
            "`[English](README.md)`\n"
        )
        links = labeled_link_destinations(text, "README.zh.md")
        self.assertEqual(links, [
            ("README.md", "English"), ("README.md", "正文"),
            ("README.md", None), ("README.md", None), ("README.md", None),
        ])
        self.assertEqual(
            [is_language_switch("README.zh.md", target, label) for target, label in links],
            [True, False, False, False, False],
        )
        self.assertTrue(is_language_switch("README.md", "README.zh.md", "简体中文"))
        self.assertFalse(is_language_switch("README.md", "CONTRIBUTING.zh.md", "简体中文"))
        self.assertFalse(is_language_switch("README.zh.md", "CONTRIBUTING.md", "English"))
        self.assertFalse(is_language_switch("README.md", "README.zh.md", "English"))

    def test_code_labels_keep_real_links_but_code_examples_are_protected(self):
        text = (
            "[`docs/topic/`](docs/topic/README.md)\n"
            "[`README.md`](README.md#目录 \"title\")\n"
            "`[example](missing.md)`\n"
            "``[`docs/topic/`](missing.md)``\n"
        )
        self.assertEqual(link_destinations(text, "README.zh.md"),
                         ["docs/topic/README.md", "README.md#目录"])
        self.assertEqual(
            rewrite_links(text, "README.zh.md", lambda url: url.replace(".md", ".zh.md")),
            "[`docs/topic/`](docs/topic/README.zh.md)\n"
            "[`README.md`](README.zh.md#目录 \"title\")\n"
            "`[example](missing.md)`\n"
            "``[`docs/topic/`](missing.md)``\n",
        )

    def test_only_destinations_change(self):
        text = (
            '[中文 `标签` $x$](  ../target.md?x=1#中文 "保留 target.md")\r\n'
            "[嵌套 [文字]](<target (one).md#小节> 'title')\r\n"
            "![图](image.svg)\r\n"
            '[ref]: target.md "Reference title"\r\n\r\n'
            "[引用][ref]\r\n"
            '<a class="x" href = \'target.md?x=1&amp;y=2#中文\' title="a > b">中文</a>\r\n'
        )
        destinations = [
            "../target.md?x=1#中文", "target (one).md#小节", "image.svg",
            "target.md", "target.md?x=1&amp;y=2#中文",
        ]
        self.assertEqual(link_destinations(text, "chapter.md"), destinations)
        changed = rewrite_links(text, "chapter.md", lambda url: url.replace(".md", ".zh.md"))
        expected = text
        for before, after in [
            ("../target.md?x", "../target.zh.md?x"),
            ("<target (one).md#", "<target (one).zh.md#"),
            ('[ref]: target.md "', '[ref]: target.zh.md "'),
            ("href = 'target.md?", "href = 'target.zh.md?"),
        ]:
            expected = expected.replace(before, after)
        self.assertEqual(changed, expected)
        self.assertEqual(rewrite_links(text, "chapter.md", lambda url: url), text)

    def test_protected_examples_are_not_urls(self):
        text = (
            "\ufeff---\r\n"
            'description: "[yaml](fake.md)"\r\n'
            "example: |\r\n  [yaml](fake.md)\r\n---\r\n"
            "<!-- [comment](fake.md)\r\n<a href='fake.md'> -->\r\n"
            "`[inline](fake.md)` and ``code `[inline](fake.md)` ``\r\n"
            "$[math](fake.md)$ and $$[display](fake.md)$$\r\n"
            "\\([math](fake.md)\\) and \\[[math](fake.md)\\]\r\n"
            "\r\n$$\r\n[display](fake.md)\r\n$$\r\n"
            "\r\n    [indented](fake.md)\r\n\t<a href='fake.md'>\r\n"
            "\r\n````markdown\r\n```python\r\n[fence](fake.md)\r\n```\r\n````\r\n"
            "~~~~~markdown\r\n~~~\r\n[fence](fake.md)\r\n~~~~\r\n~~~~~\r\n"
            "<pre>[pre](fake.md)</pre>\r\n"
            "<code>[code](fake.md)</code>\r\n"
            '<span title="[attribute](fake.md)">plain</span>\r\n'
            "[actual](real.md)\r\n"
        )
        self.assertEqual(link_destinations(text, "chapter.md"), ["real.md"])
        self.assertEqual(rewrite_links(text, "chapter.md", lambda _: "real.zh.md"),
                         text.replace("[actual](real.md)", "[actual](real.zh.md)"))

    def test_container_fences_and_indented_code(self):
        text = (
            "> ````md\n> [fake](fake.md)\n> ```\n> ````\n\n"
            "- item\n\n"
            "  ~~~~md\n  [fake](fake.md)\n  ~~~\n  ~~~~\n\n"
            "      [fake](fake.md)\n\n"
            "  [real](one.md)\n\n"
            "> - ```md\n>   [fake](fake.md)\n>   ```\n\n"
            "[real](two.md)\n"
        )
        self.assertEqual(link_destinations(text, "chapter.md"), ["one.md", "two.md"])

    def test_nested_inline_images_and_escaped_labels(self):
        text = (
            r"[label \] \[ ![image](image.svg) `x[y](fake.md)`](target.md)" "\n"
            r"\[not a link](fake.md)" "\n"
            r"[escaped](target\(one\).md)" "\n"
            r"[balanced](target(one(two)).md)" "\n"
        )
        self.assertEqual(link_destinations(text, "chapter.md"),
                         ["image.svg", "target.md", r"target\(one\).md", "target(one(two)).md"])

    def test_references_and_multiline_links(self):
        text = (
            "[first]:\n  <one.md#中文>\n  'title'\n\n"
            "[second]: two.md\n\n"
            "[third]: three.md (title)\n"
            "[one][first] [two][] [second]\n"
            "[multiline](\n  four.md\n  \"title\"\n)\n"
            "[empty]() [empty](<> 'title') [empty]( \"title\")\n"
            "[^footnote]: ordinary text, not a URL\n"
        )
        self.assertEqual(link_destinations(text, "chapter.md"),
                         ["one.md#中文", "two.md", "three.md", "four.md", "", "", ""])

    def test_html_anchors_and_autolinks(self):
        text = (
            '<A HREF=one.md class=x>one</A>\n'
            '<a\nhref = "two.md?x=1&amp;y=2" data-href="fake.md">two</a>\n'
            "<https://example.org/three.md> <reader@example.org>\n"
        )
        self.assertEqual(link_destinations(text, "chapter.md"),
                         ["one.md", "two.md?x=1&amp;y=2",
                          "https://example.org/three.md", "reader@example.org"])

    def test_unmatched_backticks_do_not_hide_later_paragraphs(self):
        text = (
            "Literal unmatched ` [one](one.md)\n\n"
            "`[example](fake.md)` [two](two.md)\n"
            "\nLiteral unmatched ` [three](three.md)\n"
            "~~~md\n`[example](fake.md)`\n~~~\n"
            "[four](four.md)\n"
        )
        self.assertEqual(link_destinations(text, "chapter.md"),
                         ["one.md", "two.md", "three.md", "four.md"])

    def test_malformed_input_fails_before_callbacks(self):
        cases = [
            "[x](a.md", "[x](<a.md)", '[x](a.md "unclosed)',
            "[x](a(one.md)", "[ref]:\n\n", '[ref]: a.md "title" extra',
            "[x](a.md\n\n)", "<!-- unclosed", "```\n[x](a.md)\n",
            "~~~\n[x](a.md)\n",
            "$$\n[x](a.md)\n", "<a href='a.md>", "<a href>",
            "<pre>[x](a.md)", "\x00",
        ]
        for malformed in cases:
            with self.subTest(malformed=malformed):
                callback = mock.Mock(side_effect=lambda url: url)
                with self.assertRaises(MarkdownLinkError) as raised:
                    rewrite_links("[valid](real.md)\n\n" + malformed, "bad.md", callback)
                self.assertIn("bad.md:", str(raised.exception))
                callback.assert_not_called()

    def test_unclosed_front_matter_is_an_error(self):
        with self.assertRaisesRegex(MarkdownLinkError, "front matter"):
            link_destinations("---\nexample: '[x](a.md)'\n", "bad.md")


class LocalizeTests(unittest.TestCase):
    def setUp(self):
        # Keep every fixture and atomic sibling inside the repository, never /tmp.
        self.directory = tempfile.TemporaryDirectory(prefix=".link-tests-", dir=SCRIPTS.parent)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.pair("README.md")
        self.pair("CONTRIBUTING.md")
        self.pair("book/README.md")
        self.pair("docs/README.md")
        self.pair("docs/topic/source.md")
        self.pair("docs/topic/target.md")

    def write(self, relative, content=b"# Fixture\n"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        return path

    def pair(self, normal, content=b"# Fixture\n"):
        self.write(normal)
        return self.write(normal[:-3] + ".zh.md", content)

    def run_main(self, *arguments):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = localize.main(["--root", str(self.root), *arguments])
        return code, out.getvalue(), err.getvalue()

    def assert_clean_siblings(self):
        self.assertEqual(list(self.root.rglob("*.localize-*")), [])

    def test_check_only_then_write_then_idempotence(self):
        source = self.write("docs/topic/source.zh.md", "[章节](target.md#中文标题)\n")
        code, out, err = self.run_main()
        self.assertEqual(code, 1, out + err)
        self.assertIn("docs/topic/source.zh.md", out)
        self.assertIn("1 destination(s)", out)
        self.assertEqual(source.read_text(), "[章节](target.md#中文标题)\n")
        code, out, err = self.run_main("--write")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(source.read_text(), "[章节](target.zh.md#中文标题)\n")
        before = source.stat()
        code, out, err = self.run_main("--write")
        self.assertEqual(code, 0, out + err)
        self.assertIn("Wrote 0 file(s)", out)
        self.assertEqual(source.stat().st_ino, before.st_ino)
        self.assertEqual(source.stat().st_mtime_ns, before.st_mtime_ns)
        self.assert_clean_siblings()

    def test_explicit_english_switch_is_preserved_but_same_url_prose_is_localized(self):
        raw = (
            "[English](./source.md?raw=1#overview)\r\n"
            "[正文](./source.md?raw=1#overview)\r\n"
            "[章节](target.md)\r\n"
            "`[English](source.md)`\r\n"
        )
        source = self.write("docs/topic/source.zh.md", raw)
        before = source.read_bytes()
        code, out, err = self.run_main()
        self.assertEqual(code, 1, out + err)
        self.assertEqual(source.read_bytes(), before)
        code, out, err = self.run_main("--write")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(source.read_bytes(), (
            "[English](./source.md?raw=1#overview)\r\n"
            "[正文](./source.zh.md?raw=1#overview)\r\n"
            "[章节](target.zh.md)\r\n"
            "`[English](source.md)`\r\n"
        ).encode("utf-8"))
        self.assertEqual(self.run_main()[0], 0)

    def test_root_and_maintenance_english_switches_stay_read_only(self):
        for normal in ("README.md", "CONTRIBUTING.md", "book/README.md"):
            self.write(normal[:-3] + ".zh.md", f"[English](./{Path(normal).name})\n")
        before = {path: path.read_bytes() for path in self.root.rglob("*.md")}
        code, out, err = self.run_main()
        self.assertEqual(code, 0, out + err)
        self.assertEqual(before, {path: path.read_bytes() for path in self.root.rglob("*.md")})

    def test_language_label_never_exempts_a_different_page(self):
        source = self.write("docs/topic/source.zh.md", "[English](target.md)\n")
        code, out, err = self.run_main("--write")
        self.assertEqual(code, 1, out + err)
        self.assertIn("exact companion", err)
        self.assertEqual(source.read_text(), "[English](target.md)\n")

    def test_explicit_paths_leave_other_translations_untouched(self):
        first = self.write("docs/topic/source.zh.md", "[x](target.md)")
        second = self.write("README.zh.md", "[x](docs/README.md)")
        code, out, err = self.run_main("--write", "docs/topic/source.zh.md")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(first.read_text(), "[x](target.zh.md)")
        self.assertEqual(second.read_text(), "[x](docs/README.md)")

    def test_default_scan_includes_book_readme(self):
        source = self.write("book/README.zh.md", "[章节](../docs/topic/target.md#中文)\n")
        code, out, err = self.run_main()
        self.assertEqual(code, 1, out + err)
        self.assertIn("book/README.zh.md", out)
        self.assertEqual(source.read_text(), "[章节](../docs/topic/target.md#中文)\n")
        code, out, err = self.run_main("--write")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(source.read_text(), "[章节](../docs/topic/target.zh.md#中文)\n")
        code, out, err = self.run_main()
        self.assertEqual(code, 0, out + err)

    def test_crlf_bom_mode_and_suffixes_are_preserved(self):
        raw = (
            '\ufeff---\r\ndescription: "[example](missing.md)"\r\n---\r\n'
            '[中文](./target.md?mode=raw#中文标题 "title target.md")\r\n'
            '<a href="./target.md?x=1&amp;y=2#中文">中文</a>\r\n'
            "<!-- [example](missing.md) -->\r\n"
        ).encode("utf-8")
        path = self.write("docs/topic/source.zh.md", raw)
        path.chmod(0o640)
        code, out, err = self.run_main("--write")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(path.read_bytes(), raw.replace(b"./target.md?", b"./target.zh.md?"))
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)

    def test_root_and_relative_and_already_localized_links(self):
        source = self.write(
            "docs/topic/source.zh.md",
            "[root](/README.md#中文) [contrib](../../CONTRIBUTING.md)\n"
            "[book](../../book/README.md#中文)\n"
            "[index](../README.md) [done](target.zh.md#same)\n",
        )
        code, out, err = self.run_main("--write")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(
            source.read_text(),
            "[root](/README.zh.md#中文) [contrib](../../CONTRIBUTING.zh.md)\n"
            "[book](../../book/README.zh.md#中文)\n"
            "[index](../README.zh.md) [done](target.zh.md#same)\n",
        )

    def test_external_assets_and_english_only_maintenance_stay_unchanged(self):
        self.write("maintenance.md")
        self.write("book/maintenance.md")
        self.write("docs/topic/figure.svg")
        self.write("docs/topic/data.json")
        raw = (
            "[web](https://example.org/missing.md?x=1#x)\n"
            "[web](//example.org/missing.md) [mail](mailto:reader@example.org)\n"
            "<reader@example.org> <https://example.org/missing.md>\n"
            "[asset](figure.svg) ![asset](figure.svg)\n"
            "[data](data.json) [maintenance](../../maintenance.md)\n"
            "[book maintenance](../../book/maintenance.md)\n"
            "[anchor](#中文) [query](?view=raw) [empty]()\n"
        )
        path = self.write("docs/topic/source.zh.md", raw)
        code, out, err = self.run_main("--write")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(path.read_text(), raw)

    def test_encoded_spelling_and_escaped_parentheses(self):
        self.pair("docs/topic/with space.md")
        self.pair("docs/topic/with(paren).md")
        raw = (
            "[percent](with%20space%2emd?x=1#原样)\n"
            "[escaped](with\\(paren\\).md)\n"
            '<a href="target&#46;md&#35;中文">entity</a>\n'
            "[extension](target.%6d%64)\n"
        )
        source = self.write("docs/topic/source.zh.md", raw)
        code, out, err = self.run_main("--write")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(
            source.read_text(),
            "[percent](with%20space.zh%2emd?x=1#原样)\n"
            "[escaped](with\\(paren\\).zh.md)\n"
            '<a href="target.zh&#46;md&#35;中文">entity</a>\n'
            "[extension](target.zh.%6d%64)\n",
        )

    def test_references_html_and_code_examples(self):
        raw = (
            "[ref]: target.md 'title'\n\n"
            "[reference][ref]\n<a href='target.md#same'>anchor</a>\n"
            "`[fake](missing.md)`\n\n~~~md\n[fake](missing.md)\n~~~\n"
            "\n    [fake](missing.md)\n\n$[fake](missing.md)$\n"
        )
        source = self.write("docs/topic/source.zh.md", raw)
        code, out, err = self.run_main("--write")
        self.assertEqual(code, 0, out + err)
        self.assertEqual(source.read_text(), raw.replace("target.md", "target.zh.md"))

    def test_missing_reader_companion_aborts_entire_batch(self):
        first = self.write("README.zh.md", "[x](docs/README.md)")
        second = self.write("docs/topic/source.zh.md", "[x](target.md)")
        (self.root / "docs/topic/target.zh.md").unlink()
        before = first.read_bytes(), second.read_bytes()
        code, out, err = self.run_main("--write")
        self.assertEqual(code, 1, out + err)
        self.assertIn("missing required Chinese companion", err)
        self.assertIn("No files written", err)
        self.assertEqual((first.read_bytes(), second.read_bytes()), before)
        self.assert_clean_siblings()

    def test_required_companion_cannot_be_maintenance(self):
        for normal in ("README.md", "CONTRIBUTING.md", "book/README.md"):
            with self.subTest(normal=normal):
                companion = self.root / (normal[:-3] + ".zh.md")
                original = companion.read_bytes()
                companion.unlink()
                source = self.write("docs/topic/source.zh.md", f"[x](../../{normal})")
                before = source.read_bytes()
                code, out, err = self.run_main("--write", "docs/topic/source.zh.md")
                self.assertEqual(code, 1, out + err)
                self.assertIn("missing required Chinese companion", err)
                self.assertIn(companion.relative_to(self.root).as_posix(), err)
                self.assertEqual(source.read_bytes(), before)
                companion.write_bytes(original)

    def test_default_scan_requires_all_three_extra_pages(self):
        for normal in ("README.md", "CONTRIBUTING.md", "book/README.md"):
            with self.subTest(normal=normal):
                companion = self.root / (normal[:-3] + ".zh.md")
                original = companion.read_bytes()
                companion.unlink()
                code, out, err = self.run_main("--write")
                self.assertEqual(code, 1, out + err)
                self.assertIn("missing required Chinese companion", err)
                self.assertIn(companion.relative_to(self.root).as_posix(), err)
                companion.write_bytes(original)

    def test_english_only_branch_reports_missing_translations(self):
        for path in self.root.rglob("*.zh.md"):
            path.unlink()
        code, out, err = self.run_main()
        self.assertEqual(code, 1, out + err)
        self.assertIn("missing required Chinese companion", err)

    def test_already_localized_target_requires_normal_pair(self):
        self.write("docs/topic/source.zh.md", "[x](target.zh.md)")
        (self.root / "docs/topic/target.md").unlink()
        code, out, err = self.run_main("--write", "docs/topic/source.zh.md")
        self.assertEqual(code, 1, out + err)
        self.assertIn("missing target: docs/topic/target.md", err)

    def test_source_requires_normal_pair(self):
        (self.root / "docs/topic/source.md").unlink()
        code, out, err = self.run_main("--write", "docs/topic/source.zh.md")
        self.assertEqual(code, 1, out + err)
        self.assertIn("missing target: docs/topic/source.md", err)

    def test_invalid_local_links_abort(self):
        for url in ["missing.md", "missing.zh.md", "missing.svg", "target%QZ.md",
                    "target%ff.md", "target%00.md", "target%5c.md"]:
            with self.subTest(url=url):
                source = self.write("docs/topic/source.zh.md", f"[x]({url})")
                original = source.read_bytes()
                code, out, err = self.run_main("--write", "docs/topic/source.zh.md")
                self.assertEqual(code, 1, out + err)
                self.assertIn("ERROR", err)
                self.assertEqual(source.read_bytes(), original)

    def test_malformed_later_file_prevents_any_write(self):
        first = self.write("README.zh.md", "[x](docs/README.md)")
        self.write("docs/topic/source.zh.md", "[x](target.md")
        before = first.read_bytes()
        code, out, err = self.run_main("--write")
        self.assertEqual(code, 1, out + err)
        self.assertIn("unclosed inline link", err)
        self.assertEqual(first.read_bytes(), before)
        self.assert_clean_siblings()

    def test_later_replace_failure_restores_both_files_bytes_and_modes(self):
        first = self.write("README.zh.md", b"[x](docs/README.md)\r\n")
        second = self.write("docs/topic/source.zh.md", b"[x](target.md)\r\n")
        first.chmod(0o640)
        second.chmod(0o600)
        originals = {path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) for path in (first, second)}
        replace = os.replace
        calls = []

        def fail_second(source, destination):
            calls.append((source, destination))
            if len(calls) == 2:
                raise OSError("injected later write failure")
            return replace(source, destination)

        with mock.patch.object(localize.os, "replace", side_effect=fail_second):
            code, out, err = self.run_main("--write", "README.zh.md", "docs/topic/source.zh.md")
        self.assertEqual(code, 1, out + err)
        self.assertIn("all original bytes restored", err)
        self.assertGreaterEqual(len(calls), 4)
        for path, original in originals.items():
            self.assertEqual((path.read_bytes(), stat.S_IMODE(path.stat().st_mode)), original)
        self.assert_clean_siblings()

    def test_error_after_replacement_also_rolls_back(self):
        first = self.write("README.zh.md", "[x](docs/README.md)")
        second = self.write("docs/topic/source.zh.md", "[x](target.md)")
        originals = first.read_bytes(), second.read_bytes()
        replace = os.replace
        calls = 0

        def fail_after_second(source, destination):
            nonlocal calls
            calls += 1
            replace(source, destination)
            if calls == 2:
                raise OSError("injected error after replacement")

        with mock.patch.object(localize.os, "replace", side_effect=fail_after_second):
            code, out, err = self.run_main("--write", "README.zh.md", "docs/topic/source.zh.md")
        self.assertEqual(code, 1, out + err)
        self.assertEqual((first.read_bytes(), second.read_bytes()), originals)
        self.assert_clean_siblings()

    def test_staging_failure_leaves_originals_untouched(self):
        first = self.write("README.zh.md", "[x](docs/README.md)")
        second = self.write("docs/topic/source.zh.md", "[x](target.md)")
        originals = first.read_bytes(), second.read_bytes()
        stage = localize._stage
        calls = 0

        def fail_later(*arguments):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("injected staging failure")
            return stage(*arguments)

        with mock.patch.object(localize, "_stage", side_effect=fail_later):
            code, out, err = self.run_main("--write", "README.zh.md", "docs/topic/source.zh.md")
        self.assertEqual(code, 1, out + err)
        self.assertEqual((first.read_bytes(), second.read_bytes()), originals)
        self.assert_clean_siblings()

    def test_input_traversal_and_outside_absolute_paths_refused(self):
        paths = ["../README.zh.md", "docs/topic/../topic/source.zh.md",
                 str(self.root.parent / "outside.zh.md"), "docs/topic/source.md"]
        for path in paths:
            with self.subTest(path=path):
                code, out, err = self.run_main("--write", path)
                self.assertEqual(code, 1, out + err)
                self.assertIn("ERROR", err)

    def test_link_traversal_refused_but_internal_parent_links_work(self):
        for url in ["../../../outside.md", "%2e%2e/%2e%2e/%2e%2e/outside.md",
                    "/../outside.md"]:
            with self.subTest(url=url):
                self.write("docs/topic/source.zh.md", f"[x]({url})")
                code, out, err = self.run_main("--write", "docs/topic/source.zh.md")
                self.assertEqual(code, 1, out + err)
                self.assertIn("escapes repository root", err)

    def test_symlink_source_and_target_refused(self):
        outside = self.write("outside/sentinel.md", "[outside](unchanged.md)")
        for relative in ["docs/topic/source.zh.md", "docs/topic/target.md",
                         "docs/topic/target.zh.md"]:
            with self.subTest(relative=relative):
                source = self.write("docs/topic/source.zh.md", "[x](target.md)")
                target = self.root / relative
                original = target.read_bytes()
                target.unlink()
                target.symlink_to(outside)
                code, out, err = self.run_main("--write", "docs/topic/source.zh.md")
                self.assertEqual(code, 1, out + err)
                self.assertIn("symlink", err)
                self.assertEqual(outside.read_text(), "[outside](unchanged.md)")
                target.unlink()
                self.write(relative, original)
                self.assert_clean_siblings()

    def test_broken_companion_symlink_is_not_optional(self):
        self.write("maintenance.md")
        (self.root / "maintenance.zh.md").symlink_to(self.root / "absent.md")
        self.write("docs/topic/source.zh.md", "[x](../../maintenance.md)")
        code, out, err = self.run_main("--write", "docs/topic/source.zh.md")
        self.assertEqual(code, 1, out + err)
        self.assertIn("symlink", err)

    def test_symlink_directory_scan_and_source_parent_refused(self):
        self.write("outside/source.md")
        sentinel = self.write("outside/source.zh.md", "[outside](unchanged.md)")
        (self.root / "docs/linked").symlink_to(self.root / "outside", target_is_directory=True)
        for paths in [(), ("docs/linked/source.zh.md",)]:
            code, out, err = self.run_main("--write", *paths)
            self.assertEqual(code, 1, out + err)
            self.assertIn("symlink", err)
            self.assertEqual(sentinel.read_text(), "[outside](unchanged.md)")

    def test_symlink_root_refused(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root / "docs", target_is_directory=True)
        code, out, err = self.run_main("--root", str(alias), "--write")
        self.assertEqual(code, 1, out + err)
        self.assertIn("symlink", err)

    def test_symlink_cannot_modify_anything_outside_selected_root(self):
        selected_root = self.root / "repository"
        self.write("repository/docs/source.md")
        source = self.write("repository/docs/source.zh.md", "[x](target.md)")
        sentinel = self.write("outside.md", b"outside bytes\r\n")
        target = selected_root / "docs/target.md"
        target.symlink_to(sentinel)
        before = source.read_bytes(), sentinel.read_bytes()
        code, out, err = self.run_main(
            "--root", str(selected_root), "--write", "docs/source.zh.md",
        )
        self.assertEqual(code, 1, out + err)
        self.assertIn("symlink", err)
        self.assertEqual((source.read_bytes(), sentinel.read_bytes()), before)

    def test_subprocess_help_and_check_exit_status(self):
        help_result = subprocess.run(
            [sys.executable, str(SCRIPTS / "localize_zh_links.py"), "--help"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("check", help_result.stdout.lower())
        self.assertIn("--write", help_result.stdout)
        self.write("docs/topic/source.zh.md", "[x](target.md)")
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "localize_zh_links.py"), "--root", str(self.root)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Check only", result.stdout)


if __name__ == "__main__":
    unittest.main()
