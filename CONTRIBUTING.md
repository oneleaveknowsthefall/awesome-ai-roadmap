# Contributing

[简体中文](CONTRIBUTING.zh.md)

## Audience and writing style

The handbook is primarily for AI engineering interview preparation. After reading a section, a reader should be able to explain why a mechanism works, the conditions it relies on, and how a changed constraint affects the design, rather than simply name the technique.

Answer the question directly, then develop the necessary reasoning and examples. Retain useful derivations and state the conditions of a comparison. Choose follow-up questions that reveal a real distinction, such as why a retry might duplicate a charge or why higher retrieval recall might worsen an answer.

English is the primary manuscript, with a complete Simplified Chinese companion. A question, direct answer, explanation, and change of conditions are a useful progression, not a mandatory set of headings. Define a concept before relying on it. Cross-references should supply detail, not force repeated detours to understand the current answer. Preserve passages that are already clear and accurate; the migration does not add an AI infrastructure topic.

Do not impose a uniform "standard answer, key insight, one-line summary" template or promise interview success instead of explaining the engineering. Tell project stories through who faced the problem, what they tried, what failed, and why the design changed. Prefer concrete actions over abstract nouns. Write idiomatically in each language rather than mirroring sentence structure word for word.

Introduce a hypothetical case once, with a short note covering its setting and example data. Do not repeat it throughout the chapter or indexes. Keep targets distinct from results and never turn a case into the author's claimed experience. Put source-access limitations in references and review records; keep conditions that affect the conclusion in the explanation itself.

## Directories, languages, and source ownership

- Put English chapters in `docs/<topic>/<module>/NN-lowercase-slug.md`, with Chinese companions at `NN-lowercase-slug.zh.md`.
- Pair each topic and module's `README.md` with `README.zh.md`. Topic indexes explain module relationships; module indexes list chapters; root indexes introduce topics.
- Give each concept a main location for its detailed explanation. Other topics should explain their own perspective and link to it, not duplicate the full text.
- The site supports browsing, while the book manifests define continuous reading order. Both use the same source text for each language; there is no second set of EPUB prose.
- Title pages, prefaces, acknowledgments, and closing matter are not knowledge chapters and do not consume chapter numbers.

Use the existing manuscript to preserve scope and the original cited papers, standards, and official documentation to verify technical meaning. A model's memory is not a substitute. Tie historical claims to their actual versions, and correct a demonstrated error in both languages rather than silently allowing them to disagree.

## Chapter structure

1. Use one H1: `# Chapter N: Title` in English and the existing numbered chapter form in Chinese.
2. Number H2 sections consecutively as `## N.1`, `## N.2`, and so on; keep corresponding section numbers aligned between languages.
3. Use Mermaid for processes and relationships, and LaTeX only for mathematics.
4. Keep useful pitfalls, summaries, and primary references. Do not repeat the body just to fill a template.
5. Attach dates, versions, and conditions to claims about changing APIs, performance, or model capabilities.
6. Give important chapters a specific front matter `description` in the page's own language.
7. Use FAQs only for genuine recurring questions, with every answer visible in the page.
8. Explain diagrams in nearby prose rather than relying only on color, interactive controls, or a reader's screen layout. Keep code and tables readable on narrow screens; do not align text with manual spaces or insert fixed page numbers.

## English-first updates

Edit the English source first, then update the affected Chinese companion in the same PR. Translate headings, explanations, diagram labels, and code comments, but preserve identifiers, protocol fields, data, units, time zones, formulas, and executable behavior. Chinese strings that are themselves example data may remain with an English explanation.

Use the [bilingual editing rules](book/i18n/README.md) and [glossary](book/i18n/glossary.json). Do not upload manuscript content to an external translation service or introduce paid API calls without approval. CI does not translate pages on demand; it checks that complete, reviewed language pairs are present.

After reviewing the pair, record its revisions explicitly:

```bash
python3 scripts/check_translations.py --record docs/topic/module/NN-chapter.md \
  --note "Describe the paired review and any source checks."
```

An English wording-only change may leave the Chinese text unchanged if the reviewer explicitly confirms that it still conveys the same meaning. A matching hash records that decision; it does not prove semantic correctness. Never refresh records merely to make CI pass.

## Mathematics and links

- Avoid the unsupported macros `\operatorname`, `\boxed`, and `\text`.
- Do not put raw `<` or `>` inside math expressions.
- Separate inline `$...$` from preceding Chinese characters or punctuation with a space so GitHub recognizes it.
- Put display math between standalone `$$` lines without internal blank lines. Do not leave operators such as `-` or `=` alone on a line, where Markdown may treat them as headings or lists.
- Avoid backslash-punctuation sequences that GitHub may consume before math rendering. Use `\Vert`, `\lbrace`, `\rbrace`, `\cr`, and `\quad` as appropriate; put percentages in prose and decimals in formulas.
- After changing a formula, inspect the actual GitHub and website rendering as well as the EPUB. A successful build alone does not establish visual correctness.
- Prefer specifications, official documentation, original papers, and reproducible engineering reports.
- English internal Markdown links use normal `.md` paths; Chinese links use the paired `.zh.md` paths. Keep external citations and shared asset paths unchanged.

For a Chinese companion copied from an existing page, the protected link helper supports a dry check and an explicit write:

```bash
python3 scripts/localize_zh_links.py docs/topic/module/NN-chapter.zh.md
python3 scripts/localize_zh_links.py --write docs/topic/module/NN-chapter.zh.md
```

## Checks before submission

```bash
python3 scripts/check_docs.py
python3 scripts/localize_zh_links.py
python3 scripts/check_translations.py
npm run check:mermaid
python3 scripts/build_book.py --language en --check --check-index
python3 scripts/build_book.py --language zh-CN --check --check-index
PYTHONDONTWRITEBYTECODE=1 .venv/bin/mkdocs build --strict
```

Install the repository's locked dependencies when needed. Changes to website or export behavior also need their relevant unit and integration tests, documented in the [maintenance guide](book/README.md).

Adding, removing, or moving a chapter requires both language sources, both book manifests, paired module/topic/root indexes, MkDocs navigation, and updated inventory and synchronization records. After changing titles or manifests, regenerate the two book indexes with `--write-index` before recording the reviewed pairs.

Submit manuscript revisions through a PR for the maintainer to merge. Do not push them directly to `main` or upload a book to KDP automatically.

## Publishing, licenses, and attribution

The two languages use the same stable chapter identities. Each language can be read on the website or exported to an EPUB with local figures, formulas, and navigation. A valid EPUB is not proof of Kindle layout quality or publication eligibility. Review the current platform requirements for language, content, and AI-generated material before release; never mislabel a language to bypass them.

Acknowledgment placeholders are for confirmed contributors, not invented people or endorsements. Keep operational checklists and unfinished editorial tasks out of the reader manuscript.

Original text and diagrams are released under [CC BY 4.0](LICENSE). A contribution must be material you have the right to provide under that license. Preserve original sources and any required third-party notices.

Collect author attribution and general licensing information in the project description and closing matter, not after every chapter or module. Keep technical citations near their claims; a notice required for reproduced third-party code must not be discarded as boilerplate.
