import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).resolve().parents[1] / "check_docs.py"
TOPICS = {
    "llm": "LLM", "multimodal": "多模态 AI", "tools": "Tools",
    "agent": "Agent", "rag": "RAG", "frameworks": "框架与编排",
    "engineering": "AI Engineering", "safety": "AI 安全与治理", "fde": "FDE",
}
CHAPTER = "docs/llm/01-foundations/01-example.md"


class ReviewCoverageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        root_rows, docs_rows, nav = [], [], ["README.md"]
        for topic, name in TOPICS.items():
            count = int(topic == "llm")
            root_rows.append(f"| [Topic](docs/{topic}/README.md) | {count} chapters |")
            docs_rows.append(f"| [Topic]({topic}/README.md) | {count} |")
            self.write(f"docs/{topic}/README.md", f"# {topic.title()}\n")
            nav.append(f"{topic}/README.md")
        self.write("README.md", "# Handbook\n\n" + "\n".join(root_rows))
        self.write("docs/README.md", "# Contents\n\n" + "\n".join(docs_rows))
        self.write("CONTRIBUTING.md", "# Contributing\n")
        self.write("docs/llm/README.md", "# LLM\n\n1. [Foundations](01-foundations/README.md)\n")
        self.write("docs/llm/01-foundations/README.md", "# Foundations\n\n[Example](01-example.md)\n")
        self.write(CHAPTER, "# Chapter 1: Example\n\n## 1.1 What does it explain?\n\nAnswer.\n")
        nav.extend(["llm/01-foundations/README.md", "llm/01-foundations/01-example.md"])
        self.write("mkdocs.yml", "nav:\n" + "\n".join(f"  - {path}" for path in nav))
        for path in list(self.root.rglob("*.md")):
            name = path.relative_to(self.root).as_posix()
            text = path.read_text(encoding="utf-8").replace(".md)", ".zh.md)")
            text = text.replace("chapters", "章").replace("# Handbook", "# 手册")
            text += "\n中文配对内容。\n"
            self.write(name[:-3] + ".zh.md", text)
        self.write(CHAPTER[:-3] + ".zh.md", "# 第一章：示例\n\n## 1.1 示例说明什么？\n\n回答。\n")
        self.write("book/i18n/config.json", json.dumps({
            "version": 1, "source_language": "en", "translation_language": "zh-CN",
            "translation_suffix": ".zh.md", "reader_roots": ["docs"],
            "extra_pages": ["README.md", "CONTRIBUTING.md"],
            "expected_reader_pages": 12, "expected_chapters": 1,
            "sync_file": "book/i18n/sync.json",
        }))
        self.write("book/zh-CN/manifest.json", "{}")

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def review(self, entries):
        self.write("book/reviews/example.json", json.dumps({"chapters": entries}))

    def entry(self, **changes):
        return {
            "path": CHAPTER, "disposition": "retained",
            "summary": "Example explanation is complete.",
            "technical_checks": ["Checked the example's assumptions."],
            **changes,
        }

    def run_check(self):
        return subprocess.run(
            [sys.executable, str(CHECKER)], cwd=self.root,
            capture_output=True, text=True, check=False,
        )

    def test_complete_review_passes(self):
        self.review([self.entry()])
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("chapters=1 per_language=1", result.stdout)

    def test_missing_review_directory_fails(self):
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires chapter review records", result.stdout)

    def test_omitted_chapter_fails(self):
        self.review([])
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing chapter review record", result.stdout)

    def test_duplicate_chapter_fails(self):
        self.review([self.entry(), self.entry()])
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate chapter review", result.stdout)

    def test_unknown_chapter_fails(self):
        self.review([self.entry(), self.entry(path="docs/llm/missing.md")])
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown chapter", result.stdout)

    def test_invalid_review_fields_fail(self):
        self.review([self.entry(disposition="unchecked", summary="", technical_checks=[])])
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid review disposition", result.stdout)
        self.assertIn("missing review rationale", result.stdout)
        self.assertIn("missing technical review notes", result.stdout)

    def test_invalid_json_reports_file(self):
        self.write("book/reviews/example.json", "{")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot read chapter review", result.stdout)

    def test_missing_translation_fails(self):
        self.review([self.entry()])
        (self.root / (CHAPTER[:-3] + ".zh.md")).unlink()
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing Chinese companion", result.stdout)

    def test_cross_language_link_fails(self):
        self.review([self.entry()])
        self.write("docs/llm/01-foundations/README.zh.md", "# 基础\n\n[示例](01-example.md)\n")
        result = self.run_check()
        self.assertIn("cross-language internal link", result.stdout)
        self.assertNotEqual(result.returncode, 0)

    def test_explicit_language_switches_only_to_current_companion_pass(self):
        self.review([self.entry()])
        for name in ("README.md", "CONTRIBUTING.md", CHAPTER):
            chinese = name[:-3] + ".zh.md"
            self.write(name, (self.root / name).read_text() +
                       f"\n[简体中文](./{Path(chinese).name})\n")
            self.write(chinese, (self.root / chinese).read_text() +
                       f"\n[English](./{Path(name).name})\n")
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_language_label_does_not_allow_other_pages_or_wrong_direction(self):
        self.review([self.entry()])
        original = (self.root / "README.md").read_text()
        for link in (
            "[简体中文](CONTRIBUTING.zh.md)",
            "[English](README.zh.md)",
            "[Read this](README.zh.md)",
            "![简体中文](README.zh.md)",
            "[简体中文](README.zh.md)\n[Read this](README.zh.md)",
        ):
            with self.subTest(link=link):
                self.write("README.md", original + "\n" + link + "\n")
                result = self.run_check()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("cross-language internal link", result.stdout)
        self.write("README.md", original)
        name = "README.zh.md"
        self.write(name, (self.root / name).read_text() + "\n[English](CONTRIBUTING.md)\n")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cross-language internal link", result.stdout)

    def test_each_language_needs_an_index_link(self):
        self.review([self.entry()])
        self.write("docs/llm/01-foundations/README.zh.md", "# 基础\n\n中文目录缺章。\n")
        result = self.run_check()
        self.assertIn("missing chapter link", result.stdout)
        self.assertNotEqual(result.returncode, 0)

    def test_navigation_only_needs_logical_source_paths(self):
        self.review([self.entry()])
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout)
        text = (self.root / "mkdocs.yml").read_text().replace("  - llm/01-foundations/01-example.md", "")
        self.write("mkdocs.yml", text)
        result = self.run_check()
        self.assertIn("missing page from navigation: llm/01-foundations/01-example.md", result.stdout)

    def test_math_and_fences_checked_in_chinese_too(self):
        self.review([self.entry()])
        name = CHAPTER[:-3] + ".zh.md"
        self.write(name, (self.root / name).read_text() + "\n公式 $\\boxed{x}$。\n")
        self.assertIn("unsupported LaTeX macro", self.run_check().stdout)
        self.write(name, (self.root / name).read_text() + "\n~~~~\nUnclosed\n")
        self.assertIn("unclosed code fence", self.run_check().stdout)

    def test_fake_links_inside_examples_are_ignored(self):
        self.review([self.entry()])
        self.write(CHAPTER, (self.root / CHAPTER).read_text() +
                   "\n````md\n[Example](missing.md)\n```\n````\n\n`[Inline](missing.md)`\n")
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_non_contiguous_h2_and_orphan_h3_fail(self):
        self.review([self.entry()])
        self.write(CHAPTER, "# Chapter 1: Example\n\n## 1.2 Skipped\n\n### 1.1.1 Orphan\n")
        result = self.run_check()
        self.assertIn("non-contiguous H2", result.stdout)
        self.assertIn("H3 has no H2 parent", result.stdout)

    def test_encoded_and_escaped_links_resolve_like_the_localizer(self):
        self.review([self.entry()])
        self.write("notes(example).md", "# Maintenance\n")
        self.write(CHAPTER, (self.root / CHAPTER).read_text() +
                   '\n[Escaped](/notes\\(example\\).md)\n'
                   '[Encoded](/notes%28example%29.md)\n'
                   '<a href="/notes(example)&#46;md">Maintenance</a>\n')
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
