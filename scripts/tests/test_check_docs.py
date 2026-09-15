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
            root_rows.append(f"| docs/{topic}/ | {count} 章 |")
            docs_rows.append(f"| {name} | {count} |")
            self.write(f"docs/{topic}/README.md", f"# {name}\n")
            nav.append(f"{topic}/README.md")
        self.write("README.md", "\n".join(root_rows))
        self.write("docs/README.md", "\n".join(docs_rows))
        self.write("CONTRIBUTING.md", "# Contributing\n")
        self.write("docs/llm/README.md", "# LLM\n\n1. [基础](01-foundations/README.md)\n")
        self.write("docs/llm/01-foundations/README.md", "# 基础\n\n[示例](01-example.md)\n")
        self.write(CHAPTER, "# 第一章：示例\n\n## 1.1 示例说明什么？\n\n回答。\n")
        nav.extend(["llm/01-foundations/README.md", "llm/01-foundations/01-example.md"])
        self.write("mkdocs.yml", "\n".join(nav))
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


if __name__ == "__main__":
    unittest.main()
