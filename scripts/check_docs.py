#!/usr/bin/env python3

import glob
import os
import re
import sys
from collections import defaultdict


issues: list[str] = []
chapter_files = sorted(glob.glob("docs/*/[0-9][0-9]-*.md"))


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
    "tools": "Tools",
    "agent": "Agent",
    "rag": "RAG",
    "langchain": "LangChain",
}
for topic, display_name in topic_names.items():
    count = len(glob.glob(f"docs/{topic}/[0-9][0-9]-*.md"))
    topic_readme = open(f"docs/{topic}/README.md", encoding="utf-8").read()
    listed = len(re.findall(rf"^\d+\. \[[^\]]+\]\(\d{{2}}-[^)]+\.md\)$", topic_readme, re.MULTILINE))
    if listed != count:
        report(f"docs/{topic}/README.md", f"lists {listed} chapters but directory has {count}")
    if not re.search(rf"docs/{topic}/.*\|\s*{count} 章\s*\|", root_readme):
        report("README.md", f"{topic} chapter count is not {count}")
    if not re.search(rf"\|\s*{display_name}.*\|\s*{count}\s*\|", docs_readme):
        report("docs/README.md", f"{topic} chapter count is not {count}")


if issues:
    print("\n".join(issues))
    print(f"\nchapters={len(chapter_files)} issues={len(issues)}")
    sys.exit(1)

print(f"chapters={len(chapter_files)} issues=0")
