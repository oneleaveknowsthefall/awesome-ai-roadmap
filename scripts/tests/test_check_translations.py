import contextlib
import io
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_translations as checker


class TranslationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.chapter = "docs/topic/01-module/01-example.md"
        self.chinese = checker.translation_name(self.chapter)
        self.config = {
            "version": 1, "source_language": "en", "translation_language": "zh-CN",
            "translation_suffix": ".zh.md", "reader_roots": ["docs"],
            "extra_pages": ["README.md"], "expected_reader_pages": 2,
            "expected_chapters": 1, "sync_file": "book/i18n/sync.json",
        }
        self.write(checker.CONFIG, json.dumps(self.config))
        self.write(self.chapter, "# Chapter 1: Example\n\n## 1.1 Why?\n\n### 1.1.1 Details\n\nAnswer.\n")
        self.write(self.chinese, "# 第一章：示例\n\n## 1.1 为什么？\n\n### 1.1.1 细节\n\n回答。\n")
        self.write("docs/README.md", "# Contents\n\nRead the handbook.\n")
        self.write("docs/README.zh.md", "# 目录\n\n阅读手册。\n")
        self.write("README.md", "# Handbook\n\nEnglish source.\n")
        self.write("README.zh.md", "# 手册\n\n中文版。\n")

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_check(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = checker.main(["--root", str(self.root), *args])
        return result, output.getvalue()

    def record_all(self):
        result, output = self.run_check("--record-all", "--note", "Compared both editions and cited evidence.")
        self.assertEqual(result, 0, output)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()}

    def test_check_never_initializes_records(self):
        before = self.snapshot()
        result, output = self.run_check()
        self.assertEqual(result, 1)
        self.assertIn("sync.json", output)
        self.assertEqual(before, self.snapshot())

    def test_record_all_and_read_only_api(self):
        self.record_all()
        before = self.snapshot()
        self.assertEqual(checker.validate_translations(self.root), [])
        result, output = self.run_check()
        self.assertEqual(result, 0, output)
        self.assertIn("pairs=3 knowledge chapters=1", output)
        self.assertEqual(before, self.snapshot())
        record = json.loads((self.root / self.config["sync_file"]).read_text())
        self.assertEqual(record["source_language"], "en")
        self.assertEqual(record["pairs"][self.chapter]["translation"], self.chinese)

    def test_read_only_api_is_importable_as_repository_namespace(self):
        self.record_all()
        result = subprocess.run(
            [sys.executable, "-B", "-S", "-c",
             "from scripts.check_translations import validate_translations; "
             "import sys; assert validate_translations(sys.argv[1]) == []",
             str(self.root)],
            cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_both_editions_invalidate_version_pair(self):
        self.record_all()
        for name in (self.chapter, self.chinese):
            with self.subTest(name=name):
                original = (self.root / name).read_text()
                self.write(name, original + "\nWording change.\n")
                before = self.snapshot()
                result, output = self.run_check()
                self.assertEqual(result, 1)
                self.assertIn("stale version pair", output)
                self.assertTrue(any("stale version pair" in p for p in checker.validate_translations(self.root)))
                self.assertEqual(before, self.snapshot())
                self.write(name, original)

    def test_english_wording_can_be_reviewed_without_fake_chinese_diff(self):
        self.record_all()
        old_zh = (self.root / self.chinese).read_bytes()
        self.write(self.chapter, (self.root / self.chapter).read_text() + "\nClarified wording.\n")
        result, output = self.run_check("--record", self.chapter, "--note", "Wording only; Chinese still matches.")
        self.assertEqual(result, 0, output)
        self.assertEqual(old_zh, (self.root / self.chinese).read_bytes())
        self.assertEqual(checker.validate_translations(self.root), [])

    def test_record_selected_does_not_refresh_other_pages(self):
        self.record_all()
        for name in (self.chapter, "README.md"):
            self.write(name, (self.root / name).read_text() + "\nA change.\n")
        result, output = self.run_check("--record", self.chapter, "--note", "Reviewed this pair only.")
        self.assertEqual(result, 0, output)
        problems = checker.validate_translations(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("README.md: stale", problems[0])

    def test_missing_pair_is_not_silently_refreshed(self):
        self.record_all()
        records = json.loads((self.root / self.config["sync_file"]).read_text())
        del records["pairs"][self.chapter]
        self.write(self.config["sync_file"], json.dumps(records))
        before = self.snapshot()
        result, output = self.run_check()
        self.assertEqual(result, 1)
        self.assertIn("missing reviewed version pair", output)
        self.assertEqual(before, self.snapshot())

    def test_removed_page_record_requires_explicit_cleanup(self):
        self.record_all()
        records = json.loads((self.root / self.config["sync_file"]).read_text())
        records["pairs"]["docs/removed.md"] = {
            **records["pairs"][self.chapter], "translation": "docs/removed.zh.md",
        }
        self.write(self.config["sync_file"], json.dumps(records))
        before = self.snapshot()
        self.assertTrue(any("outside reader coverage" in p
                            for p in checker.validate_translations(self.root)))
        result, output = self.run_check("--record-all", "--note", "Do not erase historical records silently.")
        self.assertEqual(result, 1)
        self.assertIn("remove their obsolete entries explicitly", output)
        self.assertEqual(before, self.snapshot())

    def test_note_is_required_nonempty_and_only_for_recording(self):
        for args in (
            ("--record-all",), ("--record-all", "--note", "  "),
            ("--note", "Cannot change check mode"), ("--record", self.chapter),
        ):
            with self.subTest(args=args):
                before = self.snapshot()
                self.assertEqual(self.run_check(*args)[0], 1)
                self.assertEqual(before, self.snapshot())

    def test_record_paths_must_be_english_reader_paths(self):
        for paths in ((self.chinese,), ("AGENTS.md",), ("../outside.md",), (self.chapter, self.chapter)):
            with self.subTest(paths=paths):
                before = self.snapshot()
                self.assertEqual(self.run_check("--record", *paths, "--note", "Reviewed.")[0], 1)
                self.assertEqual(before, self.snapshot())

    def test_missing_companion_cannot_be_recorded(self):
        (self.root / self.chinese).unlink()
        before = self.snapshot()
        result, output = self.run_check("--record-all", "--note", "Must not record missing content.")
        self.assertEqual(result, 1)
        self.assertIn("missing Chinese companion", output)
        self.assertEqual(before, self.snapshot())

    def test_orphan_and_changed_page_count(self):
        self.write("docs/stray.zh.md", "# 孤立页面\n")
        self.write("docs/new.md", "# New page\n")
        problems = checker.validate_translations(self.root)
        self.assertTrue(any("orphaned" in p for p in problems))
        self.assertTrue(any("reader pages=3, expected=2" in p for p in problems))

    def test_maintenance_files_are_not_reader_pages(self):
        self.write("AGENTS.md", "# Agent instructions\n")
        self.write("scripts/README.md", "# Tools\n")
        self.write("book/i18n/README.md", "# Maintenance\n")
        self.record_all()
        self.assertEqual(checker.validate_translations(self.root), [])

    def test_identical_fallback_and_non_english_h1_are_rejected(self):
        self.write(self.chapter, (self.root / self.chinese).read_text())
        problems = checker.validate_translations(self.root)
        self.assertTrue(any("identical editions" in p for p in problems))
        self.assertTrue(any("expected H1 '# Chapter 1:" in p for p in problems))

    def test_numbered_hierarchy_matches_in_order_not_just_count(self):
        self.write(self.chinese, "# 第一章：示例\n\n## 1.1 为什么？\n\n### 1.1.2 细节\n")
        self.assertTrue(any("section numbers differ" in p for p in checker.validate_translations(self.root)))

    def test_zero_chapter_number_is_a_reported_error(self):
        self.write("docs/topic/01-module/00-invalid.md", "# Chapter 0: Invalid\n")
        self.write("docs/topic/01-module/00-invalid.zh.md", "# 第零章：无效\n")
        self.assertTrue(any("chapter numbers start at 1" in p
                            for p in checker.validate_translations(self.root)))

    def test_headings_in_examples_are_not_sections(self):
        for name in (self.chapter, self.chinese):
            self.write(name, (self.root / name).read_text() + "\n````md\n## 9.9 Example\n```\n````\n")
        self.record_all()

    def test_missing_h1_in_either_edition(self):
        self.write("docs/README.zh.md", "目录正文，无标题。\n")
        self.assertTrue(any("expected one H1" in p for p in checker.validate_translations(self.root)))

    def test_duplicate_json_keys_and_invalid_record_are_reported(self):
        self.record_all()
        self.write(self.config["sync_file"], '{"version": 1, "version": 1}')
        self.assertTrue(any("duplicate JSON key" in p for p in checker.validate_translations(self.root)))
        self.write(self.config["sync_file"], "[]")
        self.assertTrue(any("invalid synchronization record fields" in p
                            for p in checker.validate_translations(self.root)))

    def test_bad_hash_note_and_timestamp_are_reported(self):
        self.record_all()
        original = (self.root / self.config["sync_file"]).read_text()
        for key, value in (("source_sha256", "not-a-hash"), ("note", ""), ("reviewed_at", "yesterday")):
            record = json.loads(original)
            record["pairs"][self.chapter][key] = value
            self.write(self.config["sync_file"], json.dumps(record))
            self.assertTrue(checker.validate_translations(self.root))

    def test_atomic_record_failure_preserves_previous_bytes(self):
        self.record_all()
        before = self.snapshot()
        with patch.object(checker.os, "replace", side_effect=OSError("simulated disk error")):
            result, output = self.run_check("--record-all", "--note", "Second review.")
        self.assertEqual(result, 1)
        self.assertIn("simulated disk error", output)
        self.assertEqual(before, self.snapshot())

    def test_symlink_translation_is_rejected(self):
        (self.root / self.chinese).unlink()
        (self.root / self.chinese).symlink_to(self.root / self.chapter)
        self.assertTrue(any("symlink" in p for p in checker.validate_translations(self.root)))


if __name__ == "__main__":
    unittest.main()
