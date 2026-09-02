import html
import json
import re
from urllib.parse import urljoin


def _plain_text(value: str) -> str:
    value = re.sub(r"```.*?```", " ", value, flags=re.DOTALL)
    value = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[`*_>#|]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return html.unescape(value).strip()


def _extract_description(markdown: str) -> str:
    markdown = re.sub(r"```.*?```", " ", markdown, flags=re.DOTALL)
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
    match = re.search(r"^#\s+(.+)$", markdown, flags=re.MULTILINE)
    return _plain_text(match.group(1)) if match else ""


def _extract_faq(markdown: str) -> list[dict[str, str]]:
    section = re.search(
        r"^##\s+(?:\d+\.\d+\s+)?常见问题\s*$([\s\S]*?)(?=^##\s+|\Z)",
        markdown,
        flags=re.MULTILINE,
    )
    if not section:
        return []

    entries: list[dict[str, str]] = []
    parts = re.split(r"^###\s+", section.group(1), flags=re.MULTILINE)
    for part in parts[1:]:
        question, _, answer = part.partition("\n")
        answer = re.split(r"^\s*返回\[", answer, maxsplit=1, flags=re.MULTILINE)[0]
        question_text = _plain_text(question)
        answer_text = _plain_text(answer)
        if question_text and answer_text:
            entries.append({"question": question_text, "answer": answer_text})
    return entries


def on_page_markdown(markdown, page, config, **kwargs):
    headline = _extract_headline(markdown) or page.title
    description = page.meta.get("description") or _extract_description(markdown)
    if not description:
        description = f"{headline}。{config.site_description}"
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
    author = config.extra["author"]
    is_chapter = bool(re.match(r"^\d{2}-", page.file.name))

    if page.file.src_uri == "README.md":
        page_type = "WebSite"
    elif page.file.name == "README":
        page_type = "CollectionPage"
    elif page.file.src_uri == "about.md":
        page_type = "AboutPage"
    else:
        page_type = "Article" if is_chapter else "WebPage"

    page_schema = {
        "@context": "https://schema.org",
        "@type": page_type,
        "name": config.site_name if page_type == "WebSite" else page.meta["seo_headline"],
        "description": page.meta["seo_description"],
        "inLanguage": "zh-CN",
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
            "url": site_url,
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
            "item": site_url,
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
    if canonical_url != site_url:
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
        json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
        for schema in schemas
    ]
    page.meta["seo_page_type"] = "article" if is_chapter else "website"
    page.meta["seo_canonical_url"] = canonical_url
    return context
