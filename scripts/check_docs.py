#!/usr/bin/env python3
"""Validate both editions while counting each logical knowledge chapter once."""

import argparse
import json
from pathlib import Path
import re
import string
import sys
from collections import defaultdict
from urllib.parse import unquote, urlsplit

from build_book import BookError, segments
from check_translations import (
    CONFIG, TranslationError, content_problems, headings, inventory, load_config,
    source_name, translation_name,
)
from markdown_links import MarkdownLinkError, is_language_switch, labeled_link_destinations, markup_url


issues: list[str] = []
TOPICS = ("llm", "multimodal", "tools", "agent", "rag", "frameworks", "engineering", "safety", "fde")


def report(path: str, message: str) -> None:
    issues.append(f"{path}: {message}")


def prose_without_code(text: str, path="<markdown>") -> str:
    return "".join(
        content if not protected or re.match(r"^ {0,3}\$", content) else
        re.sub(r"[^\n]", " ", content)
        for protected, content in segments(text, path)
    )


def check_math(path: str, prose: str) -> None:
    prose = re.sub(r"`+[^`\n]*`+", "", prose)
    display_pattern = re.compile(r"^\$\$[ \t]*\n(.*?)^\$\$[ \t]*$", re.M | re.S)
    display = display_pattern.findall(prose)
    remaining = display_pattern.sub("", prose)
    if "$$" in remaining:
        report(path, "display math requires paired, standalone $$ delimiters")
    inline_matches = list(re.finditer(
        r"(?<![\\$])\$(?!\$)([^\n$]+)(?<!\\)\$(?!\$)", remaining
    ))
    inline = [match.group(1) for match in inline_matches]
    for match in inline_matches:
        previous = remaining[match.start() - 1] if match.start() else ""
        if previous and not previous.isascii() and not previous.isspace():
            report(path, "inline math needs a space after Chinese text or punctuation")
    for expression in display:
        if re.search(r"^[ \t]*[-=+*]+[ \t]*$", expression, re.M):
            report(path, "standalone math operator can become a Markdown heading or list")
        if re.search(r"\n[ \t]*\n", expression):
            report(path, "blank line can split a display-math block in GitHub Markdown")
    for expression in display + inline:
        for macro in re.findall(r"\\(operatorname|boxed|text)\b", expression):
            report(path, f"unsupported LaTeX macro: \\{macro}")
        for escaped in sorted(set(re.findall(r"\\([^A-Za-z0-9\s])", expression))):
            if escaped in string.punctuation:
                report(path, f"Markdown-sensitive math escape: \\{escaped}; use a letter command")
        if "<" in expression or ">" in expression:
            report(path, "raw angle bracket in math; use a LaTeX comparison command")
        depth = 0
        for char in expression:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            if depth < 0:
                break
        if depth != 0:
            report(path, "unbalanced braces in math")


def check_chapter(path, text):
    chapter = int(Path(path).name.split("-", 1)[0])
    items = headings(text, path)
    h2 = [title for level, title in items if level == 2 and re.match(r"^\d+\.\d+ ", title)]
    section_numbers = [int(re.match(r"^\d+\.(\d+) ", title)[1]) for title in h2]
    if section_numbers != list(range(1, len(section_numbers) + 1)):
        report(path, f"non-contiguous H2 sections: {section_numbers}")
    for title in h2:
        if not title.startswith(f"{chapter}."):
            report(path, f"H2 chapter number mismatch: {title}")
    h3_by_parent = defaultdict(list)
    for level, title in items:
        match = re.match(r"^(\d+)\.(\d+)\.(\d+) ", title) if level == 3 else None
        if not match:
            continue
        h3_chapter, parent, subsection = map(int, match.groups())
        if h3_chapter != chapter:
            report(path, f"H3 chapter number mismatch: {title}")
        if parent not in section_numbers:
            report(path, f"H3 has no H2 parent: {title}")
        h3_by_parent[parent].append(subsection)
    for parent, subsections in h3_by_parent.items():
        if subsections != list(range(1, len(subsections) + 1)):
            report(path, f"non-contiguous H3 sections under {chapter}.{parent}: {subsections}")


def check_links(root, path, text, sources):
    targets = set()
    for url, label in labeled_link_destinations(text, path):
        decoded_url, _ = markup_url(url)
        parsed = urlsplit(decoded_url)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        decoded = unquote(parsed.path)
        if not decoded.endswith(".md"):
            continue
        base = root if decoded.startswith("/") else (root / path).parent
        target = (base / decoded.lstrip("/")).resolve()
        if not target.is_relative_to(root):
            report(path, f"internal link escapes repository: {url}")
            continue
        logical = target.relative_to(root).as_posix()
        targets.add(logical)
        if not target.is_file():
            report(path, f"missing internal link target: {url}")
        if source_name(logical) in sources:
            if (path.endswith(".zh.md") != logical.endswith(".zh.md") and
                    not is_language_switch(path, logical, label)):
                report(path, f"cross-language internal link: {url}")
    return targets


def check_indexes(root, texts, links, chapters):
    for chinese_edition in (False, True):
        localized = translation_name if chinese_edition else lambda value: value
        root_name, docs_name = localized("README.md"), localized("docs/README.md")
        for topic in TOPICS:
            topic_path = root / "docs" / topic
            if not topic_path.is_dir():
                report(f"docs/{topic}", "missing topic directory")
                continue
            count = sum(name.startswith(f"docs/{topic}/") for name in chapters)
            topic_name = localized(f"docs/{topic}/README.md")
            if topic_name not in texts:
                report(topic_name, "missing topic README")
            top_modules = sorted(p for p in topic_path.glob("[0-9][0-9]-*") if p.is_dir())
            listed_modules = re.findall(
                r"^\d+\. \[[^\]]+\]\((\d{2}-[^/]+/README(?:\.zh)?\.md)\)",
                texts.get(topic_name, ""), re.M,
            )
            expected_modules = {
                localized(f"{module.name}/README.md") for module in top_modules
            }
            if set(listed_modules) != expected_modules or len(listed_modules) != len(expected_modules):
                report(topic_name, f"module list differs from directories: expected {len(expected_modules)} modules")
            for module in sorted(p for p in topic_path.rglob("[0-9][0-9]-*") if p.is_dir()):
                module_path = module.relative_to(root).as_posix()
                module_name = localized(f"{module_path}/README.md")
                parent_name = localized(f"{module.parent.relative_to(root).as_posix()}/README.md")
                if module_name not in texts:
                    report(module_name, "missing module README")
                if module_name not in links.get(parent_name, set()):
                    report(parent_name, f"missing module link: {module_name}")
                for chapter in chapters:
                    if Path(chapter).parent.as_posix() == module_path:
                        if localized(chapter) not in links.get(module_name, set()):
                            report(module_name, f"missing chapter link: {localized(chapter)}")
            for index, target in (
                (root_name, localized(f"docs/{topic}/README.md")),
                (docs_name, localized(f"{topic}/README.md")),
            ):
                rows = [line for line in texts.get(index, "").splitlines()
                        if line.startswith("|") and f"]({target})" in line]
                if len(rows) != 1 or not re.search(
                    rf"\|\s*{count}(?:\s*(?:章|chapters?))?\s*\|", rows[0], re.I
                ):
                    report(index, f"{topic} chapter count is not {count}")


def valid_review_note(note):
    if isinstance(note, str):
        return bool(note.strip())
    if not isinstance(note, dict) or not isinstance(note.get("check"), str) or not note["check"].strip():
        return False
    if "result" in note and not isinstance(note["result"], str):
        return False
    if "source_urls" in note and (
        not isinstance(note["source_urls"], list) or
        not all(isinstance(url, str) and url.strip() for url in note["source_urls"])
    ):
        return False
    return True


def check_historical_reviews(root, chapters):
    """Review paths are logical IDs of the original Chinese manuscript, not English reviews."""
    files = sorted((root / "book/reviews").glob("*.json"))
    if (root / "book/zh-CN/manifest.json").exists() and not files:
        report("book/reviews", "book manuscript requires chapter review records")
    if not files:
        return
    reviewed = {}
    chapter_set = set(chapters)
    for file in files:
        path = file.relative_to(root).as_posix()
        try:
            review = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            report(path, f"cannot read chapter review: {error}")
            continue
        if not isinstance(review, dict) or not isinstance(review.get("chapters"), list):
            report(path, "review requires a chapters array")
            continue
        for entry in review["chapters"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                report(path, "review entry requires a chapter path")
                continue
            chapter_path = entry["path"]
            if chapter_path not in chapter_set:
                report(path, f"review refers to an unknown chapter: {chapter_path}")
            if chapter_path in reviewed:
                report(path, f"duplicate chapter review: {chapter_path}")
            reviewed[chapter_path] = path
            if entry.get("disposition") not in ("revised", "retained"):
                report(path, f"invalid review disposition: {chapter_path}")
            if not isinstance(entry.get("summary"), str) or not entry["summary"].strip():
                report(path, f"missing review rationale: {chapter_path}")
            checks = entry.get("technical_checks")
            if not isinstance(checks, list) or not checks or not all(
                valid_review_note(note) for note in checks
            ):
                report(path, f"missing technical review notes: {chapter_path}")
    for chapter_path in sorted(chapter_set - reviewed.keys()):
        report(chapter_path, "missing chapter review record (historical Chinese manuscript)")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", default=CONFIG)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    issues.clear()
    try:
        config = load_config(root, args.config)
        sources, chapters, problems = inventory(root, config)
        issues.extend(problems)
        issues.extend(content_problems(root, sources))
        texts, links = {}, {}
        for source in sources:
            for name in (source, translation_name(source)):
                if not (root / name).is_file():
                    continue
                try:
                    text = (root / name).read_text(encoding="utf-8")
                    texts[name] = text
                    check_math(name, prose_without_code(text, name))
                    links[name] = check_links(root, name, text, set(sources))
                    if source in chapters:
                        check_chapter(name, text)
                except (OSError, UnicodeError, ValueError) as error:
                    report(name, str(error))
        check_indexes(root, texts, links, chapters)
        mkdocs = (root / "mkdocs.yml").read_text(encoding="utf-8")
        nav = re.split(r"^nav:\s*$", mkdocs, maxsplit=1, flags=re.M)
        if len(nav) != 2:
            report("mkdocs.yml", "missing navigation")
        else:
            for source in sources:
                if not source.startswith("docs/"):
                    continue
                path = source.removeprefix("docs/")
                if not re.search(r"(?:^|\s)[\"']?" + re.escape(path) +
                                 r"[\"']?\s*(?:#.*)?$", nav[1], re.M):
                    report("mkdocs.yml", f"missing page from navigation: {path}")
        check_historical_reviews(root, chapters)
    except (TranslationError, BookError, MarkdownLinkError, OSError, UnicodeError) as error:
        report("documentation", str(error))
        chapters = []
    if issues:
        print("\n".join(issues))
    print(f"chapters={len(chapters)} per_language={len(chapters)} languages=en,zh-CN issues={len(issues)}")
    return int(bool(issues))


if __name__ == "__main__":
    sys.exit(main())
