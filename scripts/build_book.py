#!/usr/bin/env python3
"""Assemble the repository's Markdown subset; never modify chapter sources."""

import argparse
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
from urllib.parse import quote, unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = "book/zh-CN/manifest.json"
INDEX_PATH = "docs/book/README.md"
CHAPTER = re.compile(r"^(\d{2})-.+\.md$")
HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$", re.M)
ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
SPECIAL = re.compile(
    r"(?P<fence>^ {0,3}(?P<ticks>`{3,}|~{3,})[^\n]*(?:\n|$))"
    r"|(?P<display>^\$\$[ \t]*(?:\n|$))"
    r"|(?P<comment><!--)"
    r"|(?P<code>`+)"
    r"|(?P<math>(?<!\\)\$(?!\$))"
    r"|(?P<indent>^(?: {4}|\t)[^\n]*(?:\n|$))",
    re.M,
)
ATTRIBUTION = re.compile(
    r"(?:本文原创讲解与示意图|原文与图示|原创文档与图示|原创文档与图"
    r"|原创中文说明、案例、示例与图示|原创文字与图示)：Polo Li，"
    r"(?:(?:按|采用) )?(?:\[CC BY 4\.0\]\(https://creativecommons\.org/licenses/by/4\.0/\)"
    r"|CC BY 4\.0)(?: 授权| 许可)?[。；]"
    r"(?:(?:外部案例出处见上方链接|第三方资料与代码遵循各自项目的许可"
    r"|引用资料归原作者所有|引用资料的权利与许可归原作者|引用资料的权利归原作者)。)?"
)
RETURN_LINK = re.compile(r"^返回 \[[^\n]+\]\([^\n]+/README\.md\)。[ \t]*$|"
                         r"^返回 \[[^\n]+\]\(README\.md\)。[ \t]*$", re.M)
REFERENCE = re.compile(r"^ {0,3}\[([^\]\n]+)\]:[ \t]*(.*)$", re.M)


class BookError(ValueError):
    """An input cannot be assembled without losing its meaning."""


def require(condition, message):
    if not condition:
        raise BookError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def chinese(number):
    require(0 < number < 100, f"unsupported Chinese number: {number}")
    digits = "零一二三四五六七八九"
    if number < 10:
        return digits[number]
    tens, units = divmod(number, 10)
    return (digits[tens] if tens > 1 else "") + "十" + (digits[units] if units else "")


def slug(text):
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]*>", "", text).lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def segments(text, path):
    """Protect fences, inline code, math and indented code; discard comments."""
    position = 0
    while match := SPECIAL.search(text, position):
        yield False, text[position:match.start()]
        start, end = match.span()
        if match.group("fence"):
            ticks = match.group("ticks")
            closing = re.compile(r"^ {0,3}" + re.escape(ticks[0]) +
                                 "{" + str(len(ticks)) + r",}[ \t]*(?:\n|$)", re.M)
            stop = closing.search(text, end)
            require(stop is not None, f"{path}: unclosed code fence")
            end = stop.end()
        elif match.group("display"):
            stop = re.search(r"^\$\$[ \t]*(?:\n|$)", text[end:], re.M)
            require(stop is not None, f"{path}: unclosed display math")
            end += stop.end()
        elif match.group("comment"):
            end = text.find("-->", end)
            require(end != -1, f"{path}: unclosed HTML comment")
            position = end + 3
            continue
        elif match.group("code"):
            stop = re.search(r"(?<!`)" + re.escape(match.group()) + r"(?!`)", text[end:])
            require(stop is not None, f"{path}: unclosed inline code")
            end += stop.end()
        elif match.group("math"):
            stop = re.search(r"(?<!\\)\$(?!\$)", text[end:].split("\n", 1)[0])
            if stop is None:
                yield False, text[start:end]
                position = end
                continue
            end += stop.end()
        yield True, text[start:end]
        position = end
    yield False, text[position:]


def inside(root, path):
    return path == root or root in path.parents


def visible_headings(text, chunks):
    mask = "".join(re.sub(r"[^\n]", " ", content) if protected else content
                   for protected, content in chunks)
    return [match for match in HEADING.finditer(text) if mask[match.start()] == "#"]


def source_path(root, value):
    require(isinstance(value, str), "source path must be a string")
    path = PurePosixPath(value)
    require(not path.is_absolute() and "\\" not in value and
            ".." not in path.parts and str(path) == value,
            f"non-canonical source path: {value}")
    result = (root / value).resolve()
    require(inside(root, result), f"source escapes repository: {value}")
    require(result.is_file(), f"missing source: {value}")
    require(result == root / value, f"symlink source is not allowed: {value}")
    return result


def object_keys(value, keys, label):
    require(isinstance(value, dict), f"{label}: expected object")
    require(set(value) == set(keys), f"{label}: expected fields {', '.join(keys)}")


def nonempty(value, label):
    require(isinstance(value, str) and value.strip() and "\n" not in value,
            f"{label}: expected nonempty single-line string")


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


@dataclass
class Document:
    id: str
    path: str
    number: int = 0
    part_number: int = 0
    title: str = ""
    chunks: list = field(default_factory=list)
    headings: dict = field(default_factory=dict)
    aliases: dict = field(default_factory=dict)
    references: dict = field(default_factory=dict)

    @property
    def label(self):
        if self.number:
            return f"第{chinese(self.part_number)}篇 第{self.number}章：{self.title}"
        return self.title


class Book:
    def __init__(self, root=ROOT, manifest=DEFAULT_MANIFEST):
        self.root = Path(root).resolve()
        self.manifest_path = source_path(self.root, manifest)
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"),
                                   object_pairs_hook=no_duplicate_keys)
        self.documents = {}
        self.parts = []
        self.assets = {}
        self.hashes = {}
        self.anchors = {"contents"}
        self.validate_manifest()
        for document in self.documents.values():
            self.read_document(document)
        require(self.front[0].title == self.manifest["title"],
                "manifest title differs from title-page H1")

    def add_anchor(self, anchor):
        require(anchor not in self.anchors, f"duplicate book anchor: {anchor}")
        self.anchors.add(anchor)
        return anchor

    def entries(self, entries, part_number=0, topic=None):
        require(isinstance(entries, list) and entries, "entries must be a nonempty list")
        result = []
        for number, entry in enumerate(entries, 1):
            object_keys(entry, ("id", "path"), "entry")
            require(isinstance(entry["id"], str) and ID.fullmatch(entry["id"]),
                    f"invalid stable ID: {entry['id']}")
            path = source_path(self.root, entry["path"])
            require(path.suffix == ".md", f"expected Markdown source: {entry['path']}")
            require(entry["path"] not in self.documents, f"duplicate source: {entry['path']}")
            self.add_anchor(entry["id"])
            if topic:
                require(PurePosixPath(entry["path"]).parts[:2] == ("docs", topic),
                        f"chapter outside topic {topic}: {entry['path']}")
                filename = CHAPTER.fullmatch(path.name)
                require(filename and int(filename[1]) == number,
                        f"{topic}: chapters must be in original numeric order 1..N: {path.name}")
            else:
                require(PurePosixPath(entry["path"]).parent == PurePosixPath("docs/book"),
                        f"front/back matter must be in docs/book: {entry['path']}")
                require(path.name != "README.md", "website index is not book matter")
            document = Document(entry["id"], entry["path"], number if topic else 0, part_number)
            self.documents[document.path] = document
            result.append(document)
        return result

    def validate_manifest(self):
        data = self.manifest
        object_keys(data, ("schema_version", "language", "edition", "title", "chapter_count",
                           "source_url", "front_matter", "parts", "back_matter"), "manifest")
        require(type(data["schema_version"]) is int and data["schema_version"] == 1,
                "unsupported schema_version")
        require(data["language"] == "zh-CN", "this builder currently supports zh-CN only")
        for key in ("edition", "title", "source_url"):
            nonempty(data[key], key)
        source_url = urlsplit(data["source_url"])
        require(source_url.scheme == "https" and source_url.netloc and
                not source_url.query and not source_url.fragment and
                data["source_url"].endswith("/"),
                "source_url must be an HTTPS directory URL")
        require(type(data["chapter_count"]) is int and data["chapter_count"] > 0,
                "chapter_count must be a positive integer")
        self.front = self.entries(data["front_matter"])
        require(self.front[0].id == "title-page", "front matter must start with title-page")
        require(isinstance(data["parts"], list) and data["parts"], "parts must be a nonempty list")
        topics = set()
        for number, part in enumerate(data["parts"], 1):
            object_keys(part, ("id", "title", "chapters"), "part")
            require(isinstance(part["id"], str) and ID.fullmatch(part["id"]), "invalid topic ID")
            require(part["id"] not in topics, f"duplicate topic: {part['id']}")
            topics.add(part["id"])
            nonempty(part["title"], "part title")
            self.add_anchor("part-" + part["id"])
            self.parts.append((part, self.entries(part["chapters"], number, part["id"])))
        self.back = self.entries(data["back_matter"])
        require(self.back[-1].id == "colophon", "back matter must end with colophon")
        discovered = {p.relative_to(self.root).as_posix()
                      for p in (self.root / "docs").rglob("[0-9][0-9]-*.md")}
        included = {d.path for d in self.documents.values() if d.number}
        require(discovered == included,
                f"chapter coverage mismatch; missing={sorted(discovered - included)}, "
                f"unexpected={sorted(included - discovered)}")
        require(len(included) == data["chapter_count"],
                f"chapter_count={data['chapter_count']}, actual={len(included)}")

    def read_document(self, document):
        raw = (self.root / document.path).read_bytes()
        self.hashes[document.path] = digest(raw)
        text = raw.decode("utf-8").replace("\r\n", "\n")
        if text.startswith("---\n"):
            end = re.search(r"^---[ \t]*$", text[4:], re.M)
            require(end is not None, f"{document.path}: unclosed YAML front matter")
            text = text[4 + end.end():].lstrip("\n")
        chunks = []
        for protected, content in segments(text, document.path):
            if not protected and document.number:
                content = RETURN_LINK.sub("", ATTRIBUTION.sub("", content))
                require("Polo Li" not in content,
                        f"{document.path}: unrecognized author notice; centralize in colophon")
            chunks.append((protected, content))
        text = "".join(content for _, content in chunks).rstrip()
        text = re.sub(r"\n---[ \t]*$", "", text).rstrip() + "\n"
        # Re-tokenizing after removing comments also restores adjacent prose spans.
        document.chunks = list(segments(text, document.path))
        prose = "".join(re.sub(r"[^\n]", " ", content) if protected else content
                        for protected, content in document.chunks)
        source_headings = visible_headings(text, document.chunks)
        h1 = [m for m in source_headings if len(m[1]) == 1]
        require(len(h1) == 1, f"{document.path}: expected exactly one H1")
        require(text[:h1[0].start()].strip() == "", f"{document.path}: content precedes H1")
        document.title = h1[0][2]
        if document.number:
            prefix = re.match(r"^第([一二三四五六七八九十百零\d]+)章[：:]\s*(.+)$",
                              document.title)
            require(prefix and prefix[1] in (str(document.number), chinese(document.number)),
                    f"{document.path}: H1 chapter number does not match filename")
            document.title = prefix[2]
        occurrences = {}
        extra = 0
        for match in source_headings:
            level, heading = len(match[1]), match[2]
            require(not document.number or level < 6,
                    f"{document.path}: H6 cannot be demoted; revise heading hierarchy")
            source_slug = slug(heading)
            count = occurrences.get(source_slug, 0)
            occurrences[source_slug] = count + 1
            alias = source_slug + (f"-{count}" if count else "")
            if level == 1:
                anchor = document.id
            elif number := re.match(r"(\d+(?:\.\d+)+)\s", heading):
                anchor = self.add_anchor(document.id + "-s" + number[1].replace(".", "-"))
            else:
                extra += 1
                anchor = self.add_anchor(f"{document.id}-extra-{extra:02}")
            document.headings[match.start()] = anchor
            document.aliases[alias] = anchor
            document.aliases[anchor] = anchor
        for ref in REFERENCE.finditer(prose):
            key = " ".join(ref[1].lower().split())
            require(not key.startswith("^"), f"{document.path}: footnotes are not supported")
            require(key not in document.references, f"{document.path}: duplicate reference: {key}")
            document.references[key] = f"{document.id}-ref-{digest(key.encode())[:12]}"
        require(not re.search(r"<[A-Za-z][^>]*\b(?:id|name)\s*=", prose),
                f"{document.path}: source HTML anchors need explicit conversion")

    def rewrite_url(self, url, document):
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc:
            require(parsed.scheme in ("http", "https", "mailto") or
                    (not parsed.scheme and parsed.netloc),
                    f"{document.path}: unsupported URL scheme: {url}")
            return url
        require(not parsed.query, f"{document.path}: local link has query: {url}")
        require(not parsed.path.startswith("/") and "\\" not in parsed.path,
                f"{document.path}: invalid local link: {url}")
        target = ((self.root / document.path).parent / unquote(parsed.path)).resolve()
        if not parsed.path:
            target = self.root / document.path
        require(inside(self.root, target), f"{document.path}: link escapes repository: {url}")
        require(target.is_file(), f"{document.path}: missing link or asset: {url}")
        relative = target.relative_to(self.root).as_posix()
        fragment = unquote(parsed.fragment)
        if relative in self.documents:
            destination = self.documents[relative]
            if not fragment:
                return "#" + destination.id
            require(fragment in destination.aliases,
                    f"{document.path}: missing heading fragment: {url}")
            return "#" + destination.aliases[fragment]
        if relative in ("README.md", "docs/README.md", INDEX_PATH) and not fragment:
            return "#contents"
        for part, _ in self.parts:
            if relative == f"docs/{part['id']}/README.md" and not fragment:
                return "#part-" + part["id"]
        if target.suffix == ".md":
            # Module indexes are not chapters. Keep their precise online meaning.
            if fragment:
                aliases = set()
                counts = {}
                text = target.read_text(encoding="utf-8")
                chunks = list(segments(text, relative))
                for heading in visible_headings(text, chunks):
                    name = slug(heading[2])
                    count = counts.get(name, 0)
                    aliases.add(name + (f"-{count}" if count else ""))
                    counts[name] = count + 1
                require(fragment in aliases, f"{document.path}: missing index fragment: {url}")
            return (self.manifest["source_url"] + quote(relative, safe="/") +
                    ("#" + quote(fragment) if fragment else ""))
        self.assets[relative] = target
        return "assets/" + quote(relative, safe="/") + ("#" + quote(fragment) if fragment else "")

    def rewrite_destinations(self, content, document):
        # Only the destination is replaced; labels and optional titles remain intact.
        pattern = re.compile(r"(?<!\\)\]\([ \t]*|^ {0,3}\[[^\]\n]+\]:[ \t]*", re.M)
        pieces, position = [], 0
        for match in pattern.finditer(content):
            if match.end() < position:
                continue
            start = match.end()
            angle = content[start:start + 1] == "<"
            begin = start + int(angle)
            end, depth = begin, 0
            while end < len(content):
                char = content[end]
                if char == "\\":
                    end += 2
                    continue
                if angle and char == ">":
                    break
                if not angle:
                    if (char.isspace() or char == ")") and depth == 0:
                        break
                    if char == "(":
                        depth += 1
                    elif char == ")":
                        depth -= 1
                end += 1
            require(end < len(content) and depth == 0,
                    f"{document.path}: malformed Markdown link near {content[start:start + 80]!r}")
            if angle:
                require(content[end] == ">", f"{document.path}: unclosed link destination")
            tail = content[end + int(angle):]
            title = r"""(?:"[^"\n]*"|'[^'\n]*'|\([^()\n]*\))"""
            if match[0].lstrip().startswith("]("):
                require(re.match(r"[ \t]*(?:" + title + r"[ \t]*)?\)", tail),
                        f"{document.path}: malformed inline link suffix: {tail[:80]!r}")
            else:
                require(re.match(r"[ \t]*(?:" + title + r"[ \t]*)?(?:\n|$)", tail),
                        f"{document.path}: malformed reference definition")
            raw_url = content[begin:end]
            url = re.sub(r"\\([()])", r"\1", raw_url)
            replacement = self.rewrite_url(url, document)
            pieces.extend((content[position:begin], replacement))
            position = end
        pieces.append(content[position:])
        return "".join(pieces)

    def rewrite_prose(self, content, document):
        require(not re.search(r"\[\^[^\]]+\]", content),
                f"{document.path}: footnotes need an explicit book conversion")
        content = self.rewrite_destinations(content, document)

        def reference(match):
            label, explicit = match[1], match[2]
            key = " ".join((explicit or label).lower().split())
            if explicit is not None:
                require(key in document.references,
                        f"{document.path}: undefined link reference: {key}")
            if key in document.references:
                return f"[{label}][{document.references[key]}]"
            return match[0]

        lines = []
        for line in content.splitlines(keepends=True):
            definition = REFERENCE.match(line)
            if definition:
                key = " ".join(definition[1].lower().split())
                line = line.replace("[" + definition[1] + "]:",
                                    "[" + document.references[key] + "]:", 1)
            else:
                line = re.sub(r"(?<!\\)\[([^\[\]\n]+)\](?:\[([^\]\n]*)\])?(?![(:])",
                              reference, line)
            lines.append(line)
        content = "".join(lines)

        def html_tag(match):
            tag = match[0]
            generated = re.fullmatch(r'<a id="([a-z0-9-]+)">', tag)
            if generated and generated[1] in self.anchors:
                return tag
            require(not re.search(r"\b(?:id|name|srcset)\s*=", tag, re.I),
                    f"{document.path}: source HTML anchors/srcset need explicit conversion")
            attributes = re.compile(r"""\b(href|src)\s*=\s*(["'])(.*?)\2""", re.I)
            require(len(attributes.findall(tag)) == len(re.findall(r"\b(?:href|src)\s*=", tag, re.I)),
                    f"{document.path}: HTML URLs must be quoted")
            return attributes.sub(lambda m: m[1] + "=" + m[2] +
                                  self.rewrite_url(m[3], document) + m[2], tag)

        return re.sub(r"<[A-Za-z][^>]*>", html_tag, content)

    def render_document(self, document):
        def heading(match):
            if match.start() not in document.headings:
                return match[0]
            anchor = document.headings[match.start()]
            level = len(match[1]) + int(bool(document.number))
            title = document.label if len(match[1]) == 1 else match[2]
            return f'<a id="{anchor}"></a>\n\n{"#" * level} {title}'

        text = "".join(content for _, content in document.chunks)
        text = HEADING.sub(heading, text)
        result = [content if protected else self.rewrite_prose(content, document)
                  for protected, content in segments(text, document.path)]
        return "".join(result).strip()

    def contents(self, website=False):
        link = (lambda d: os.path.relpath(self.root / d.path, self.root / "docs/book")) \
            if website else (lambda d: "#" + d.id)
        lines = []
        for document in self.front:
            lines.append(f"- [{document.title}]({link(document)})")
        for number, (part, documents) in enumerate(self.parts, 1):
            lines.extend(("", f"## 第{chinese(number)}篇：{part['title']}（{len(documents)}章）", ""))
            for document in documents:
                lines.append(f"- [{document.label}]({link(document)})")
        lines.extend(("", "## 后记与许可", ""))
        for document in self.back:
            lines.append(f"- [{document.title}]({link(document)})")
        return "\n".join(lines)

    def index(self):
        return (
            "---\n"
            "description: 按九篇、篇内原章号排列的中文简体书稿完整阅读目录，"
            "从模型原理读到生产系统与现场交付。\n---\n\n"
            "# 中文书稿：线性阅读目录\n\n"
            "从[扉页](title-page.md)开始，依次阅读前言、读法、九篇正文和后附页。"
            "**每篇章号重新开始**；下列顺序以篇内原章号为准，不按网站模块目录排序。"
            "这里链接同一份章节正文，不另存一套副本。\n\n"
            "<!-- Generated by scripts/build_book.py --write-index; do not edit the list. -->\n\n"
            + self.contents(website=True) + "\n"
        )

    def assemble(self):
        pages = [self.render_document(self.front[0]),
                 '<a id="contents"></a>\n\n# 目录\n\n' + self.contents()]
        pages.extend(self.render_document(d) for d in self.front[1:])
        for number, (part, documents) in enumerate(self.parts, 1):
            pages.append(f'<a id="part-{part["id"]}"></a>\n\n'
                         f'# 第{chinese(number)}篇：{part["title"]}')
            pages.extend(self.render_document(d) for d in documents)
        pages.extend(self.render_document(d) for d in self.back)
        return "\n\n".join(pages) + "\n"

    def write(self, output, manuscript):
        output = Path(output).resolve()
        default_dir = self.root / "book/zh-CN/generated"
        require(output.suffix == ".md", "output must have .md extension")
        require(not inside(self.root, output) or inside(default_dir, output),
                "repository output must stay under book/zh-CN/generated; sources are read-only")
        require(output not in self.assets.values(), "output would overwrite an input asset")
        receipt_path = output.with_suffix(".build.json")
        require(receipt_path.resolve() == receipt_path, "build receipt must not be a symlink")
        destinations = []
        for relative, source in self.assets.items():
            destination = output.parent / "assets" / relative
            require(destination.resolve() == destination, "asset output must not be a symlink")
            require(destination != source, "asset output would overwrite source")
            destinations.append((source, destination))
        output.parent.mkdir(parents=True, exist_ok=True)
        for source, destination in destinations:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        output.write_text(manuscript, encoding="utf-8")
        receipt = {
            "edition": self.manifest["edition"],
            "language": self.manifest["language"],
            "manifest_sha256": digest(self.manifest_path.read_bytes()),
            "source_sha256": self.hashes,
            "asset_sha256": {p: digest(source.read_bytes()) for p, source in self.assets.items()},
            "manuscript_sha256": digest(manuscript.encode("utf-8")),
        }
        receipt_path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST, help="repository-relative JSON path")
    parser.add_argument("--check", action="store_true", help="validate without generating manuscript")
    indexes = parser.add_mutually_exclusive_group()
    indexes.add_argument("--write-index", action="store_true", help="regenerate docs/book/README.md")
    indexes.add_argument("--check-index", action="store_true", help="fail if reader index is stale")
    parser.add_argument("--output", type=Path, help="Markdown destination; defaults to ignored generated/")
    args = parser.parse_args(argv)
    try:
        require(not args.check or args.output is None, "--check cannot be combined with --output")
        book = Book(root=ROOT, manifest=args.manifest)
        manuscript = book.assemble()
        index = ROOT / INDEX_PATH
        if args.check_index:
            require(index.is_file() and index.read_text(encoding="utf-8") == book.index(),
                    "reader index is stale; run python3 scripts/build_book.py --write-index")
        if args.write_index:
            index.parent.mkdir(parents=True, exist_ok=True)
            index.write_text(book.index(), encoding="utf-8")
        if not args.check and (not args.write_index or args.output):
            output = args.output or ROOT / "book/zh-CN/generated/manuscript.md"
            book.write(output, manuscript)
            print(f"Markdown draft: {output}")
        print(f"chapters={book.manifest['chapter_count']} parts={len(book.parts)} "
              f"assets={len(book.assets)}")
        return 0
    except (BookError, OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"book: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
