"""Docs-stack tests: python -B scripts/tests/bilingual_site_integration.py."""

import copy
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import urljoin, urlsplit

import yaml


ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "https://example.test/awesome-ai-roadmap/"
CHAPTER = "frameworks/01-langchain/01-foundations/01-agent-frameworks.md"
CHAPTER_URL = CHAPTER[:-3] + "/"


class Document(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.tags = []
        self.schemas = []
        self.schema_text = None
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.schema_text = ""

    def handle_data(self, data):
        if self.schema_text is not None:
            self.schema_text += data

    def handle_endtag(self, tag):
        if tag == "script" and self.schema_text is not None:
            self.schemas.append(json.loads(self.schema_text))
            self.schema_text = None

    def find(self, tag, **attrs):
        return [
            values for name, values in self.tags
            if name == tag and all(values.get(key) == value for key, value in attrs.items())
        ]


def nav_subset(items, paths):
    result = []
    for item in items:
        if isinstance(item, str):
            if item in paths:
                result.append(item)
        else:
            for title, children in item.items():
                selected = nav_subset(children, paths)
                if selected:
                    result.append({title: selected})
    return result


class BilingualSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix=".bilingual-site-", dir=ROOT)
        cls.addClassCleanup(cls.directory.cleanup)
        cls.root = Path(cls.directory.name)
        cls.docs = cls.root / "docs"
        cls.site = cls.root / "site"
        # The repository's trusted YAML includes the existing SuperFences callable.
        cls.original = yaml.load((ROOT / "mkdocs.yml").read_text(), Loader=yaml.Loader)
        cls.config = copy.deepcopy(cls.original)
        cls.redirects = next(
            plugin["redirects"]["redirect_maps"]
            for plugin in cls.config["plugins"] if "redirects" in plugin
        )
        paths = set(cls.redirects.values()) | {
            "README.md", "frameworks/README.md", "about.md", "book/README.md",
        }
        for index, path in enumerate(sorted(paths)):
            cls.write(
                path,
                f"# English fixture {index}\n\n"
                "This English fixture explains a small example for a bilingual website.\n",
            )
            cls.write(
                path[:-3] + ".zh.md",
                f"# 中文示例 {index}\n\n"
                "这个中文示例用于验证双语网站，正文和英文版本分别生成，不能互相替代。\n",
            )
        cls.write(
            "README.md", "# English home\n\n[Read the chapter](" + CHAPTER + ")\n\n"
            "[Old Chinese bookmark](" + CHAPTER + "#11)\n",
        )
        cls.write(
            "README.zh.md", "# 中文首页\n\n[阅读章节](" + CHAPTER[:-3] + ".zh.md)\n"
        )
        cls.write("frameworks/README.md", "# Framework index\n\nAn English collection.\n")
        cls.write("frameworks/README.zh.md", "# 框架目录\n\n中文主题目录。\n")
        cls.write("about.md", "# About this project\n\nAbout the English website.\n")
        cls.write("about.zh.md", "# 关于本项目\n\n关于中文网站。\n")
        cls.write(CHAPTER, """---
description: 'English description with "quotes" & examples.'
git_creation_date_localized_raw_iso_date: '2024-01-02'
git_revision_date_localized_raw_iso_date: '2025-03-04'
---
# Chapter 1: Agent frameworks

English chapter body: orchestration fixture.

## 1.1 Tools and tasks

An English explanation of the example.

## 1.2 Shared boundaries

<span id="12">Reserved anchor</span>

## 1.3 Duplicate

Ambiguous numbering must not create aliases.

## 1.4 Inline `code`

![Diagram](../../../assets/diagram.svg)

```markdown
## 9.9 Not a heading
```

## 1.5 Frequently asked questions

### Why keep the pair?

Both pages must exist and contain their own language.

Back to [module](README.md).

[Home](../../../README.md)
""")
        cls.write(CHAPTER[:-3] + ".zh.md", """---
description: '中文描述，包含“引号”与示例。'
git_creation_date_localized_raw_iso_date: '2024-01-02'
git_revision_date_localized_raw_iso_date: '2025-03-04'
---
# 第一章：框架示例

中文章节正文：编排示例。

## 1.1 工具与任务

这是例子的中文解释。

## 1.2 共享边界

一个已有英文锚点不能被重复定义。

## 1.3 重复

编号重复时不推测对应关系。

## 1.3 重复

重复编号的另一个小节。

## 1.4 行内 `代码`

![示意图](../../../assets/diagram.svg)

```markdown
## 9.9 不是标题
```

## 1.5 常见问题

### 为什么保留双语？

两个页面必须存在，并包含各自语言的正文。

返回[模块](README.zh.md)。

[首页](../../../README.zh.md)

[普通路径也应留在中文](README.md)
""")
        cls.write("assets/diagram.svg", '<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        cls.write("stylesheets/extra.css", "body { color: inherit; }\n")
        cls.write("javascripts/mathjax.js", "// Shared fixture asset.\n")
        cls.config.update({
            "docs_dir": str(cls.docs),
            "site_dir": str(cls.site),
            "site_url": BASE_URL,
            "hooks": [str(ROOT / "scripts/mkdocs_hooks.py")],
            "nav": nav_subset(cls.original["nav"], paths),
            "validation": {"links": {"anchors": "warn"}},
        })
        cls.config["theme"]["custom_dir"] = str(ROOT / "overrides")
        for plugin in cls.config["plugins"]:
            if "git-revision-date-localized" in plugin:
                # Fixture sources are deliberately untracked; raw date metadata
                # still exercises the existing schema and update-date handling.
                plugin["git-revision-date-localized"]["enabled"] = False
        cls.config_path = cls.root / "mkdocs.yml"
        cls.save_config(cls.config)
        result = cls.build_site()
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    @classmethod
    def write(cls, name, text):
        path = cls.docs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    @classmethod
    def save_config(cls, config):
        cls.config_path.write_text(yaml.dump(config, allow_unicode=True), encoding="utf-8")

    @classmethod
    def build_site(cls):
        return subprocess.run(
            [sys.executable, "-m", "mkdocs", "build", "--strict", "-f", str(cls.config_path)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )

    def read_page(self, path):
        content = (self.site / path / "index.html").read_text(encoding="utf-8")
        return content, Document(content)

    def assert_local_target_exists(self, current_url, href):
        resolved = urlsplit(urljoin(current_url, href))
        self.assertEqual(resolved.netloc, "example.test")
        self.assertTrue(resolved.path.startswith("/awesome-ai-roadmap/"), resolved.path)
        relative = resolved.path.removeprefix("/awesome-ai-roadmap/")
        target = self.site / relative
        if resolved.path.endswith("/"):
            target /= "index.html"
        self.assertTrue(target.is_file(), str(target))
        return resolved

    def test_real_navigation_contract(self):
        i18n = next(plugin["i18n"] for plugin in self.original["plugins"] if "i18n" in plugin)
        self.assertFalse(i18n["fallback_to_default"])
        self.assertEqual(i18n["docs_structure"], "suffix")
        self.assertEqual(i18n["languages"][0]["locale"], "en")
        self.assertTrue(i18n["languages"][0]["default"])
        translated = i18n["languages"][1]["nav_translations"]

        def check(items):
            for item in items:
                if isinstance(item, str):
                    self.assertTrue(item.endswith(".md"))
                    self.assertNotIn(".zh.md", item)
                    self.assertTrue((ROOT / "docs" / item).is_file(), item)
                else:
                    for title, children in item.items():
                        self.assertNotRegex(title, r"[\u3400-\u9fff]")
                        self.assertIn(title, translated)
                        check(children)
        check(self.original["nav"])
        self.assertEqual(len(self.redirects), 19)

    def test_language_body_navigation_and_theme(self):
        for prefix, language, body, absent, name, palette, search in [
            ("", "en", "English chapter body", "中文章节正文",
             "Awesome AI Roadmap", "Switch to dark mode", "Search"),
            ("zh/", "zh", "中文章节正文", "English chapter body",
             "AI 工程学习路线", "切换到深色模式", "搜索"),
        ]:
            with self.subTest(language=language):
                content, document = self.read_page(prefix + CHAPTER_URL)
                self.assertEqual(document.find("html")[0]["lang"], language)
                self.assertIn(body, content)
                self.assertNotIn(absent, content)
                self.assertIn(name, content)
                self.assertIn(palette, content)
                self.assertTrue(document.find("input", placeholder=search))
                self.assertIn(
                    "Frameworks and orchestration" if language == "en" else "框架与编排",
                    content,
                )
                self.assertIn(
                    "Chapter 1: Agent frameworks" if language == "en" else "第一章：框架示例",
                    content,
                )
                self.assertNotIn(
                    "第一章：框架示例" if language == "en" else "Chapter 1: Agent frameworks",
                    content,
                )

    def test_seo_schema_faq_and_dates(self):
        for prefix, language, og_locale, question, answer in [
            ("", "en", "en_US", "Why keep the pair?",
             "Both pages must exist and contain their own language."),
            ("zh/", "zh-CN", "zh_CN", "为什么保留双语？",
             "两个页面必须存在，并包含各自语言的正文。"),
        ]:
            with self.subTest(language=language):
                _, document = self.read_page(prefix + CHAPTER_URL)
                canonical = BASE_URL + prefix + CHAPTER_URL
                self.assertEqual(document.find("link", rel="canonical"), [
                    {"rel": "canonical", "href": canonical}
                ])
                self.assertEqual(document.find("meta", property="og:locale")[0]["content"], og_locale)
                self.assertEqual(document.find("meta", property="og:url")[0]["content"], canonical)
                alternate_links = [
                    tag for tag in document.find("link", rel="alternate")
                    if "hreflang" in tag
                ]
                self.assertCountEqual(
                    [tag["hreflang"] for tag in alternate_links], ["en", "zh-CN", "x-default"]
                )
                alternatives = {tag["hreflang"]: tag["href"] for tag in alternate_links}
                self.assertEqual(alternatives, {
                    "en": BASE_URL + CHAPTER_URL,
                    "zh-CN": BASE_URL + "zh/" + CHAPTER_URL,
                    "x-default": BASE_URL + CHAPTER_URL,
                })
                schemas = {schema["@type"]: schema for schema in document.schemas}
                article = schemas["Article"]
                self.assertEqual(article["inLanguage"], language)
                self.assertEqual(article["url"], canonical)
                self.assertEqual(article["isPartOf"]["url"], BASE_URL + prefix)
                self.assertEqual(article["datePublished"], "2024-01-02")
                self.assertEqual(article["dateModified"], "2025-03-04")
                self.assertEqual(schemas["BreadcrumbList"]["itemListElement"][0]["item"], BASE_URL + prefix)
                faq = schemas["FAQPage"]
                self.assertEqual(faq["inLanguage"], language)
                self.assertEqual(faq["mainEntity"][0]["name"], question)
                self.assertEqual(faq["mainEntity"][0]["acceptedAnswer"]["text"], answer)
        _, english = self.read_page(CHAPTER_URL)
        self.assertEqual(
            english.find("meta", name="description")[0]["content"],
            'English description with "quotes" & examples.',
        )

    def test_home_index_and_about_types(self):
        for prefix in ["", "zh/"]:
            for path, expected in [
                ("", "WebSite"), ("frameworks/", "CollectionPage"),
                ("book/", "CollectionPage"), ("about/", "AboutPage"),
            ]:
                with self.subTest(prefix=prefix, path=path):
                    _, document = self.read_page(prefix + path)
                    self.assertEqual(document.schemas[0]["@type"], expected)
                    self.assertEqual(document.schemas[0]["url"], BASE_URL + prefix + path)
                    self.assertEqual(
                        document.schemas[0]["inLanguage"], "zh-CN" if prefix else "en"
                    )

    def test_switch_links_assets_and_suffixed_backlinks(self):
        for prefix in ["", "zh/"]:
            for path in ["", CHAPTER_URL]:
                content, document = self.read_page(prefix + path)
                current_url = BASE_URL + prefix + path
                switches = document.find("a", **{"class": "md-select__link"})
                self.assertEqual(len(switches), 2)
                for link in switches:
                    destination = self.assert_local_target_exists(current_url, link["href"])
                    expected_prefix = "zh/" if link["hreflang"] == "zh" else ""
                    self.assertEqual(
                        destination.path, "/awesome-ai-roadmap/" + expected_prefix + path
                    )
                for tag in document.find("link", rel="stylesheet"):
                    if not tag["href"].startswith("http"):
                        self.assert_local_target_exists(current_url, tag["href"])
                for tag in document.find("script") + document.find("img"):
                    source = tag.get("src")
                    if source and not source.startswith("http"):
                        self.assert_local_target_exists(current_url, source)
                for link in document.find("a"):
                    if not link.get("href", "").startswith("http"):
                        self.assertNotIn(".zh.md", link.get("href", ""))
        content, chinese = self.read_page("zh/" + CHAPTER_URL)
        self.assertIn("普通路径也应留在中文", content)
        links = {urljoin(BASE_URL + "zh/" + CHAPTER_URL, tag["href"])
                 for tag in chinese.find("a") if "href" in tag}
        self.assertIn(BASE_URL + "zh/", links)
        self.assertIn(BASE_URL + "zh/frameworks/01-langchain/01-foundations/", links)

    def test_aliases_are_matched_numbered_and_collision_safe(self):
        content, english = self.read_page(CHAPTER_URL)
        ids = [attrs["id"] for _, attrs in english.tags if "id" in attrs]
        self.assertEqual(len(ids), len(set(ids)))
        aliases = {tag["id"] for tag in english.find("span", **{"class": "legacy-heading-anchor"})}
        self.assertEqual(aliases, {"_1", "11", "14", "15"})
        self.assertIn(
            '<h2 id="11-tools-and-tasks"><span id="11" class="legacy-heading-anchor"',
            content,
        )
        self.assertNotIn("12", aliases)
        self.assertNotIn("13", aliases)
        self.assertNotIn("13_1", aliases)
        self.assertNotIn("99", aliases)
        _, chinese = self.read_page("zh/" + CHAPTER_URL)
        self.assertFalse(chinese.find("span", **{"class": "legacy-heading-anchor"}))

    def test_all_legacy_redirects_remain_in_their_language(self):
        for source, target in self.redirects.items():
            for prefix in ["", "zh/"]:
                source_url = source.replace("README.md", "").replace(".md", "/")
                target_url = target.replace("README.md", "").replace(".md", "/")
                with self.subTest(source=source, prefix=prefix):
                    content, document = self.read_page(prefix + source_url)
                    current = BASE_URL + prefix + source_url
                    destination = BASE_URL + prefix + target_url
                    self.assertEqual(
                        document.find("link", rel="canonical")[0]["href"], destination
                    )
                    self.assertEqual(document.find("html")[0]["lang"], "zh" if prefix else "en")
                    refresh = document.find("meta", **{"http-equiv": "refresh"})[0]["content"]
                    self.assertEqual(urljoin(current, refresh.split("url=", 1)[1]), destination)
                    self.assert_local_target_exists(current, document.find("a")[0]["href"])
                    self.assertIn("window.location.hash", content)

    def test_search_indexes_both_languages_at_their_real_urls(self):
        search = json.loads((self.site / "search/search_index.json").read_text())
        self.assertEqual(set(search["config"]["lang"]), {"en", "zh"})
        entries = {entry["location"]: entry for entry in search["docs"]}
        self.assertIn("English chapter body", entries[CHAPTER_URL]["text"])
        self.assertIn("中文章节正文", entries["zh/" + CHAPTER_URL]["text"])
        self.assertNotIn("中文章节正文", entries[CHAPTER_URL]["text"])
        self.assertEqual(len(entries), len(search["docs"]))
        for location in entries:
            self.assert_local_target_exists(BASE_URL, location)

    def test_missing_pairs_fail_even_outside_navigation(self):
        for path, partner in [("orphan.md", "orphan.zh.md"), ("orphan.zh.md", "orphan.md")]:
            with self.subTest(path=path):
                self.write(path, "# Unpaired fixture\n")
                try:
                    result = self.build_site()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("Unpaired bilingual reader pages", result.stdout + result.stderr)
                    self.assertIn(f"{path} requires {partner}", result.stdout + result.stderr)
                finally:
                    (self.docs / path).unlink()

    def test_fallback_cannot_be_enabled(self):
        config = copy.deepcopy(self.config)
        next(p["i18n"] for p in config["plugins"] if "i18n" in p)["fallback_to_default"] = True
        self.save_config(config)
        try:
            result = self.build_site()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("fallback_to_default: false", result.stdout + result.stderr)
        finally:
            self.save_config(self.config)

    def test_repeated_builds_reset_i18n_state(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "from mkdocs.config import load_config; "
             "from mkdocs.commands.build import build; "
             "import sys; "
             "config = load_config(config_file=sys.argv[1], strict=True); "
             "build(config); build(config)", str(self.config_path)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.test_all_legacy_redirects_remain_in_their_language()
        self.test_search_indexes_both_languages_at_their_real_urls()
        self.test_language_body_navigation_and_theme()


class MetadataExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "bilingual_metadata_hooks", ROOT / "scripts/mkdocs_hooks.py"
        )
        cls.hooks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.hooks)

    def test_ignore_fenced_headlines_and_faq(self):
        for fence in ["```", "~~~", "````", "~~~~"]:
            with self.subTest(fence=fence):
                example = (
                    f"{fence}markdown\n# Example title\n\n## FAQ\n\n"
                    "### Example question?\n\nExample answer.\n" + fence + "\n\n"
                )
                self.assertEqual(self.hooks._extract_headline(example), "")
                self.assertEqual(self.hooks._extract_faq(example), [])
                visible = example + (
                    "# Visible `client_id`\n\n## Frequently asked questions\n\n"
                    "### Which `client_id`?\n\nUse `request_id` for the lookup.\n"
                )
                self.assertEqual(self.hooks._extract_headline(visible), "Visible client_id")
                self.assertEqual(self.hooks._extract_faq(visible), [{
                    "question": "Which client_id?",
                    "answer": "Use request_id for the lookup.",
                }])

    def test_fake_headings_do_not_split_visible_faq(self):
        for section in ["FAQ", "常见问题"]:
            for fence in ["```", "~~~"]:
                with self.subTest(section=section, fence=fence):
                    markdown = (
                        f"## {section}\n\n### Real question?\n\nKeep `before_value`.\n\n"
                        f"{fence}markdown\n## Fake section\n### Fake question?\n\n"
                        f"Fake answer.\n{fence}\n\nKeep `after_value` too.\n"
                    )
                    self.assertEqual(self.hooks._extract_faq(markdown), [{
                        "question": "Real question?",
                        "answer": "Keep before_value. Keep after_value too.",
                    }])

    def test_closing_fence_must_match(self):
        for marker, other in [("`", "~"), ("~", "`")]:
            with self.subTest(marker=marker):
                markdown = (
                    f"   {marker * 4}markdown\n{marker * 3}\n"
                    f"{other * 4}\n{marker * 4} not a closing fence\n"
                    "# Still code\n\n## FAQ\n### Fake?\nFake answer.\n"
                    f"   {marker * 5}\t\n\n# Actual heading\n"
                )
                self.assertEqual(self.hooks._extract_headline(markdown), "Actual heading")
                self.assertEqual(self.hooks._extract_faq(markdown), [])

    def test_inline_code_keeps_its_content(self):
        markdown = (
            "## FAQ\n\n### How does `foo_bar` work?\n\n"
            "Use `foo_bar > 0`, `<Type>`, `a|b`, ``a ` tick``, "
            "```literal_value```, and `&amp;` exactly.\n"
        )
        self.assertEqual(self.hooks._extract_faq(markdown), [{
            "question": "How does foo_bar work?",
            "answer": (
                "Use foo_bar > 0, <Type>, a|b, a ` tick, "
                "literal_value, and &amp; exactly."
            ),
        }])

    def test_description_ignores_fences(self):
        for fence in ["```", "~~~"]:
            with self.subTest(fence=fence):
                description = "This visible description retains the `request_id` identifier."
                markdown = (
                    f"{fence}text\nThis code sample must never become the page description.\n"
                    f"{fence}\n\n# Actual title\n\n{description}\n"
                )
                self.assertEqual(
                    self.hooks._extract_description(markdown),
                    "This visible description retains the request_id identifier.",
                )

    def test_unclosed_fence_does_not_invent_metadata(self):
        for fence in ["```", "~~~"]:
            with self.subTest(fence=fence):
                markdown = f"{fence}markdown\n# Example\n\n## FAQ\n### Fake?\nFake answer."
                self.assertEqual(self.hooks._extract_headline(markdown), "")
                self.assertEqual(self.hooks._extract_faq(markdown), [])


if __name__ == "__main__":
    unittest.main()
