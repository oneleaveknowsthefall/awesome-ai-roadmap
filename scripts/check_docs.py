#!/usr/bin/env python3

import glob
import json
import os
import re
import string
import sys
from collections import defaultdict


issues: list[str] = []
chapter_files = sorted(glob.glob("docs/**/[0-9][0-9]-*.md", recursive=True))


def report(path: str, message: str) -> None:
    issues.append(f"{path}: {message}")


def prose_without_code(text: str) -> str:
    lines: list[str] = []
    in_code = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code:
            lines.append(line)
    return "\n".join(lines)


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
        # GitHub parses Markdown escapes before passing this TeX to its renderer.
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


for path in chapter_files:
    text = open(path, encoding="utf-8").read()
    prose = prose_without_code(text)
    headings = [line for line in prose.splitlines() if line.startswith("# ")]
    if len(headings) != 1:
        report(path, f"expected one H1, found {len(headings)}")
    if text.count("```") % 2:
        report(path, "unpaired fenced code block")
    if prose.count("$$") % 2:
        report(path, "unpaired display-math delimiter")
    for macro in re.findall(r"\\(operatorname|boxed|text)\b", prose):
        report(path, f"unsupported LaTeX macro: \\{macro}")

    chapter = int(os.path.basename(path).split("-", 1)[0])
    h2 = [
        line for line in prose.splitlines()
        if re.match(r"^## \d+\.\d+ ", line)
    ]
    section_numbers = [
        int(re.match(r"^## \d+\.(\d+) ", line).group(1)) for line in h2
    ]
    if section_numbers != list(range(1, len(section_numbers) + 1)):
        report(path, f"non-contiguous H2 sections: {section_numbers}")
    for line in h2:
        if not line.startswith(f"## {chapter}."):
            report(path, f"H2 chapter number mismatch: {line}")

    h3_by_parent: dict[int, list[int]] = defaultdict(list)
    for line in prose.splitlines():
        match = re.match(r"^### (\d+)\.(\d+)\.(\d+) ", line)
        if not match:
            continue
        h3_chapter, parent, subsection = map(int, match.groups())
        if h3_chapter != chapter:
            report(path, f"H3 chapter number mismatch: {line}")
        h3_by_parent[parent].append(subsection)
    for parent, subsections in h3_by_parent.items():
        expected = list(range(1, len(subsections) + 1))
        if subsections != expected:
            report(path, f"non-contiguous H3 sections under {chapter}.{parent}: {subsections}")


markdown_files = ["README.md", "CONTRIBUTING.md"] + glob.glob(
    "docs/**/*.md", recursive=True
)
link_pattern = re.compile(r"\]\(([^)#]+\.md)(?:#[^)]+)?\)")
for path in markdown_files:
    text = open(path, encoding="utf-8").read()
    check_math(path, prose_without_code(text))
    for target in link_pattern.findall(text):
        if "://" in target:
            continue
        resolved = os.path.normpath(os.path.join(os.path.dirname(path), target))
        if not os.path.exists(resolved):
            report(path, f"missing internal link target: {target}")


root_readme = open("README.md", encoding="utf-8").read()
docs_readme = open("docs/README.md", encoding="utf-8").read()
topic_names = {
    "llm": "LLM",
    "multimodal": "多模态 AI",
    "tools": "Tools",
    "agent": "Agent",
    "rag": "RAG",
    "frameworks": "框架与编排",
    "engineering": "AI Engineering",
    "safety": "AI 安全与治理",
    "fde": "FDE",
}
for topic, display_name in topic_names.items():
    count = len(glob.glob(
        f"docs/{topic}/**/[0-9][0-9]-*.md", recursive=True
    ))
    topic_readme = open(f"docs/{topic}/README.md", encoding="utf-8").read()
    top_module_dirs = sorted(
        path for path in glob.glob(f"docs/{topic}/[0-9][0-9]-*")
        if os.path.isdir(path)
    )
    listed_modules = len(re.findall(
        r"^\d+\. \[[^\]]+\]\(\d{2}-[^/]+/README\.md\)",
        topic_readme,
        re.MULTILINE,
    ))
    if listed_modules != len(top_module_dirs):
        report(
            f"docs/{topic}/README.md",
            f"lists {listed_modules} modules but directory has {len(top_module_dirs)}",
        )
    module_dirs = sorted(
        path for path in glob.glob(
            f"docs/{topic}/**/[0-9][0-9]-*", recursive=True
        )
        if os.path.isdir(path)
    )
    for module in module_dirs:
        module_readme_path = os.path.join(module, "README.md")
        if not os.path.exists(module_readme_path):
            report(module, "missing module README.md")
            continue
        module_readme = open(module_readme_path, encoding="utf-8").read()
        parent_readme_path = os.path.join(os.path.dirname(module), "README.md")
        parent_readme = open(parent_readme_path, encoding="utf-8").read()
        module_link = f"({os.path.basename(module)}/README.md)"
        if module_link not in parent_readme:
            report(parent_readme_path, f"missing module link: {module_link}")
        for chapter_path in glob.glob(os.path.join(module, "[0-9][0-9]-*.md")):
            chapter_link = f"({os.path.basename(chapter_path)})"
            if chapter_link not in module_readme:
                report(module_readme_path, f"missing chapter link: {chapter_link}")
    if not re.search(rf"docs/{topic}/.*\|\s*{count} 章\s*\|", root_readme):
        report("README.md", f"{topic} chapter count is not {count}")
    if not re.search(rf"\|\s*{display_name}.*\|\s*{count}\s*\|", docs_readme):
        report("docs/README.md", f"{topic} chapter count is not {count}")

mkdocs_config = open("mkdocs.yml", encoding="utf-8").read()
for path in glob.glob("docs/**/*.md", recursive=True):
    nav_path = os.path.relpath(path, "docs")
    if nav_path not in mkdocs_config:
        report("mkdocs.yml", f"missing page from navigation: {nav_path}")

review_files = sorted(glob.glob("book/reviews/*.json"))
if os.path.exists("book/zh-CN/manifest.json") and not review_files:
    report("book/reviews", "book manuscript requires chapter review records")
if review_files:
    reviewed: dict[str, str] = {}
    chapter_set = set(chapter_files)
    for path in review_files:
        try:
            with open(path, encoding="utf-8") as source:
                review = json.load(source)
        except (OSError, json.JSONDecodeError) as error:
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
            if not isinstance(checks, list) or not checks:
                report(path, f"missing technical review notes: {chapter_path}")
    for chapter_path in sorted(chapter_set - reviewed.keys()):
        report(chapter_path, "missing chapter review record")


if issues:
    print("\n".join(issues))
    print(f"\nchapters={len(chapter_files)} issues={len(issues)}")
    sys.exit(1)

print(f"chapters={len(chapter_files)} issues=0")
