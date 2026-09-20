import html
import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import urljoin

from markdown import Markdown
from mkdocs.exceptions import PluginError
from mkdocs.plugins import CombinedEvent, event_priority
from mkdocs.utils.meta import get_data
from mkdocs_redirects.plugin import get_html_path
from mkdocs_static_i18n.config import RE_LOCALE


@event_priority(100)
def on_config(config, **kwargs):
    i18n = config.plugins.get("i18n")
    if (
        i18n is None
        or i18n.config.docs_structure != "suffix"
        or i18n.config.fallback_to_default
        or i18n.default_language != "en"
        or set(i18n.build_languages) != {"en", "zh"}
    ):
        raise PluginError(
            "The bilingual site requires English at root, Chinese at /zh/, "
            "suffix mode, both languages enabled, and fallback_to_default: false."
        )

    # static-i18n re-enters build() for each locale and retains state during serve.
    if not i18n.building:
        i18n.current_language = "en"
        i18n.search_entries.clear()
        i18n.i18n_files_per_language.clear()

    paths = {p.relative_to(config.docs_dir).as_posix()
             for p in Path(config.docs_dir).rglob("*.md")}
    missing = []
    for path in sorted(paths):
        stem = PurePosixPath(path).stem
        locale = PurePosixPath(stem).suffix.lstrip(".")
        if locale and RE_LOCALE.fullmatch(locale) and locale != "zh":
            raise PluginError(f"Unsupported localized reader page: {path}; use .md / .zh.md.")
        partner = path[:-6] + ".md" if path.endswith(".zh.md") else path[:-3] + ".zh.md"
        if partner not in paths:
            missing.append(f"{path} requires {partner}")
    if missing:
        raise PluginError("Unpaired bilingual reader pages:\n" + "\n".join(missing))
    return config


@event_priority(50)
def _capture_shared_assets(files, config, **kwargs):
    # Disabling content fallback also drops unsuffixed assets in static-i18n.
    config.plugins["i18n"]._shared_assets = [
        file for file in files
        if not file.is_documentation_page()
        and not RE_LOCALE.fullmatch(PurePosixPath(file.name).suffix.lstrip("."))
    ]
    return files


@event_priority(-110)
def _restore_assets_and_redirects(files, config, **kwargs):
    i18n = config.plugins["i18n"]
    present = {file.src_uri for file in files}
    for file in i18n._shared_assets:
        if file.src_uri not in present:
            files.append(file)

    # redirects runs before i18n's nested post-build. Give each pass its own
    # source paths and localized destination Files, never mutate redirect_maps.
    redirects = config.plugins.get("redirects")
    if redirects:
        prefix = "" if i18n.current_language == "en" else "zh/"
        redirects.redirects = {
            prefix + source: target
            for source, target in redirects.config["redirect_maps"].items()
        }
        redirects.doc_pages = {
            file.norm_src_uri: file for file in files.documentation_pages()
        }
    return files


on_files = CombinedEvent(_capture_shared_assets, _restore_assets_and_redirects)


@event_priority(-50)
def on_post_build(config, **kwargs):
    redirects = config.plugins.get("redirects")
    if not redirects:
        return
    language = config.plugins["i18n"].current_language
    for source, target in redirects.redirects.items():
        path = Path(config.site_dir, get_html_path(source, config.use_directory_urls))
        if not path.is_file():
            continue
        target_path, separator, fragment = target.partition("#")
        file = redirects.doc_pages.get(target_path)
        canonical = (
            urljoin(config.site_url, file.url) + separator + fragment
            if file else target
        )
        content = path.read_text(encoding="utf-8")
        content = content.replace('<html lang="en">', f'<html lang="{language}">')
        content = re.sub(
            r'<link rel="canonical" href="[^"]*">',
            lambda _: f'<link rel="canonical" href="{html.escape(canonical, quote=True)}">',
            content,
        )
        if language == "zh":
            content = content.replace("Redirecting...", "正在跳转……").replace(
                "You're being redirected to a ", "正在跳转到"
            ).replace("new destination", "新页面")
        path.write_text(content, encoding="utf-8")


class _Headings(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.headings = []
        self.ids = set()
        self.current = None
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if re.fullmatch(r"h[1-6]", tag):
            self.current = {"level": tag, "id": attrs.get("id"), "text": ""}

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"] += data

    def handle_endtag(self, tag):
        if self.current is not None and tag == self.current["level"]:
            self.headings.append(self.current)
            self.current = None


def _heading_key(heading):
    if heading["level"] == "h1":
        return "h1", "title"
    number = re.match(r"^(\d+(?:\.\d+)*)(?=[\s.:：、])", heading["text"])
    if number:
        return heading["level"], number.group(1)
    return None


def on_page_content(content, page, config, **kwargs):
    if page.file.locale != "en":
        return content
    chinese_file = page.file.alternates["zh"]
    markdown, _ = get_data(Path(chinese_file.abs_src_path).read_text(encoding="utf-8"))
    chinese_html = Markdown(
        extensions=config.markdown_extensions, extension_configs=config.mdx_configs
    ).convert(markdown)
    english = _Headings(content)
    chinese = _Headings(chinese_html)
    old, new = defaultdict(list), defaultdict(list)
    for heading in chinese.headings:
        old[_heading_key(heading)].append(heading)
    for heading in english.headings:
        new[_heading_key(heading)].append(heading)
    aliases = {}
    for key, headings in old.items():
        if key is None or len(headings) != 1 or len(new[key]) != 1:
            continue
        alias, target = headings[0]["id"], new[key][0]["id"]
        # An existing English anchor always wins; ambiguous matches are skipped.
        if alias and target and alias not in english.ids:
            aliases[target] = alias
            english.ids.add(alias)

    def insert_alias(match):
        target = html.unescape(match.group(2))
        if target not in aliases:
            return match.group(0)
        alias = html.escape(aliases[target], quote=True)
        return (
            match.group(0)
            + f'<span id="{alias}" class="legacy-heading-anchor" aria-hidden="true"></span>'
        )

    content = re.sub(r'(<h[1-6]\b[^>]*\bid=")([^"]+)("[^>]*>)', insert_alias, content)
    if page.present_anchor_ids is not None:
        page.present_anchor_ids.update(aliases.values())
    return content


def _without_fenced_code(markdown: str) -> str:
    lines = []
    closing = None
    for line in markdown.splitlines(keepends=True):
        if closing is not None:
            if closing.fullmatch(line.rstrip("\r\n")):
                closing = None
            lines.append("\n" if line.endswith("\n") else "")
            continue
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)", line)
        if opening and not (
            opening[1][0] == "`" and "`" in opening[2]
        ):
            marker = re.escape(opening[1][0])
            closing = re.compile(rf" {{0,3}}{marker}{{{len(opening[1])},}}[ \t]*")
            lines.append("\n" if line.endswith("\n") else "")
        else:
            lines.append(line)
    return "".join(lines)


def _plain_text(value: str) -> str:
    value = _without_fenced_code(value)
    inline_code = []

    def protect_code(match):
        inline_code.append(match[2])
        return f"\x00CODE{len(inline_code) - 1}\x00"

    # Keep literal identifiers, operators and angle brackets inside inline code.
    value = re.sub(
        r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", protect_code, value, flags=re.DOTALL
    )
    value = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[`*_>#|]", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\x00CODE(\d+)\x00", lambda match: inline_code[int(match[1])], value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _extract_description(markdown: str) -> str:
    markdown = _without_fenced_code(markdown)
    markdown = re.sub(r"\$\$.*?\$\$", " ", markdown, flags=re.DOTALL)
    paragraphs = re.split(r"\n\s*\n", markdown)
    for paragraph in paragraphs:
        stripped = paragraph.strip()
        if (
            not stripped
            or stripped.startswith(("#", "```", "$$", "-", "*", "1.", "|", ">"))
        ):
            continue
        description = _plain_text(stripped)
        if len(description) >= 30:
            return description[:157].rstrip("，。；： ") + (
                "…" if len(description) > 157 else ""
            )
    return ""


def _extract_headline(markdown: str) -> str:
    markdown = _without_fenced_code(markdown)
    match = re.search(r"^#\s+(.+)$", markdown, flags=re.MULTILINE)
    return _plain_text(match.group(1)) if match else ""


def _extract_faq(markdown: str) -> list[dict[str, str]]:
    markdown = _without_fenced_code(markdown)
    section = re.search(
        r"^##\s+(?:\d+(?:\.\d+)*[.)]?\s+)?"
        r"(?:常见问题|FAQ|Frequently asked questions)\s*$([\s\S]*?)(?=^##\s+|\Z)",
        markdown,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    if not section:
        return []

    entries: list[dict[str, str]] = []
    parts = re.split(r"^###\s+", section.group(1), flags=re.MULTILINE)
    for part in parts[1:]:
        question, _, answer = part.partition("\n")
        answer = re.split(
            r"^\s*(?:返回\s*\[|Back to\s+\[)", answer, maxsplit=1,
            flags=re.MULTILINE | re.IGNORECASE,
        )[0]
        question_text = _plain_text(question)
        answer_text = _plain_text(answer)
        if question_text and answer_text:
            entries.append({"question": question_text, "answer": answer_text})
    return entries


def on_page_markdown(markdown, page, config, **kwargs):
    headline = _extract_headline(markdown) or page.title
    description = page.meta.get("description") or _extract_description(markdown)
    if not description:
        separator = "。" if page.file.locale == "zh" else ". "
        description = f"{headline}{separator}{config.site_description}"
    page.meta["seo_description"] = description
    page.meta["description"] = html.escape(description, quote=True)
    page.meta.setdefault("author", "Polo Li")
    page.meta["seo_headline"] = headline
    page.meta["seo_faq"] = _extract_faq(markdown)
    revision_date = page.meta.get("git_revision_date_localized_raw_iso_date")
    if revision_date:
        page.update_date = revision_date
    return markdown


def on_page_context(context, page, config, **kwargs):
    site_url = config.site_url.rstrip("/") + "/"
    canonical_url = urljoin(site_url, page.url)
    language = page.file.locale
    locale = "zh-CN" if language == "zh" else "en"
    language_home = urljoin(site_url, "zh/" if language == "zh" else "")
    source = PurePosixPath(page.file.norm_src_uri)
    author = config.extra["author"]
    is_chapter = bool(re.match(r"^\d{2}-", source.stem))

    if source.as_posix() in {"README.md", "index.md"}:
        page_type = "WebSite"
    elif source.stem in {"README", "index"}:
        page_type = "CollectionPage"
    elif source.as_posix() == "about.md":
        page_type = "AboutPage"
    else:
        page_type = "Article" if is_chapter else "WebPage"

    page_schema = {
        "@context": "https://schema.org",
        "@type": page_type,
        "name": config.site_name if page_type == "WebSite" else page.meta["seo_headline"],
        "description": page.meta["seo_description"],
        "inLanguage": locale,
        "url": canonical_url,
        "author": {
            "@type": "Person",
            "name": author["name"],
            "url": author["url"],
        },
    }
    if page_type != "WebSite":
        page_schema["isPartOf"] = {
            "@type": "WebSite",
            "name": config.site_name,
            "url": language_home,
        }
    schemas = [page_schema]

    if is_chapter:
        article = schemas[0]
        article["headline"] = page.meta["seo_headline"]
        article["mainEntityOfPage"] = {
            "@type": "WebPage",
            "@id": canonical_url,
        }
        article["datePublished"] = page.meta.get(
            "git_creation_date_localized_raw_iso_date"
        )
        article["dateModified"] = page.meta.get(
            "git_revision_date_localized_raw_iso_date"
        )

    breadcrumbs = [
        {
            "@type": "ListItem",
            "position": 1,
            "name": config.site_name,
            "item": language_home,
        }
    ]
    ancestors = list(reversed(page.ancestors))
    for ancestor in ancestors:
        ancestor_url = getattr(ancestor, "url", None)
        if ancestor_url:
            breadcrumbs.append(
                {
                    "@type": "ListItem",
                    "position": len(breadcrumbs) + 1,
                    "name": ancestor.title,
                    "item": urljoin(site_url, ancestor_url),
                }
            )
    if canonical_url != language_home:
        breadcrumbs.append(
            {
                "@type": "ListItem",
                "position": len(breadcrumbs) + 1,
                "name": page.title,
                "item": canonical_url,
            }
        )
    if len(breadcrumbs) > 1:
        schemas.append(
            {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": breadcrumbs,
            }
        )

    if page.meta["seo_faq"]:
        schemas.append(
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "inLanguage": locale,
                "url": canonical_url,
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": entry["question"],
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": entry["answer"],
                        },
                    }
                    for entry in page.meta["seo_faq"]
                ],
            }
        )

    page.meta["seo_json_ld"] = [
        json.dumps(schema, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
        for schema in schemas
    ]
    page.meta["seo_page_type"] = "article" if is_chapter else "website"
    page.meta["seo_canonical_url"] = canonical_url
    page.meta["seo_og_locale"] = "zh_CN" if language == "zh" else "en_US"
    page.meta["seo_og_alternate_locale"] = "en_US" if language == "zh" else "zh_CN"
    page.meta["seo_alternates"] = {
        ("zh-CN" if lang == "zh" else lang): urljoin(site_url, file.url)
        for lang, file in page.file.alternates.items()
    }
    page.meta["seo_alternates"]["x-default"] = page.meta["seo_alternates"]["en"]
    return context
