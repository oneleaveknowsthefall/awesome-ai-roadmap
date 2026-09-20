# Repository Instructions

## Audience and interview preparation

- This knowledge base is primarily for AI engineering interview preparation. Explain mechanisms, assumptions, tradeoffs, failure cases, and how to evaluate a proposed solution.
- Write natural, professional English as the primary manuscript, with a complete and idiomatic Simplified Chinese companion. Keep technical depth available for follow-up questions; do not replace explanations with memorization slogans.
- Avoid generic AI narration, exaggerated claims, "high-scoring answer" language, and identical answer templates across chapters. Add concrete questions only when they clarify a real distinction.
- Preserve useful foundational material even when newer approaches exist. Verify time-sensitive claims against primary sources and distinguish stable specifications, drafts, historical APIs, and vendor-specific behavior.
- Introduce a fictional case once, in a short note that covers its setting and example numbers. Do not repeat the disclaimer in every subsection, index, or footer. Keep targets distinct from results without interrupting the story.
- Explain projects through people, events, mistakes, and decisions. Prefer concrete verbs to stacks of abstract nouns; use terminology that is precise in the language being edited.
- Keep source-access notes in the references. Retain qualifications that change a technical conclusion, but do not turn the main text into an audit log.
- Never present fictional projects as the author's experience or suggest that readers claim them as real work.

## Book manuscript

- Maintain an English-first AI engineering interview handbook and its complete Simplified Chinese companion. Normal `.md` files are English; their `.zh.md` counterparts are Chinese. English is the default website and book language. Do not relabel or convert Chinese to another language without an explicit request.
- Treat the existing Chinese manuscript and cited primary papers, specifications, and official documentation as the highest-priority evidence during migration. Verify conflicts against the relevant source version, make justified corrections in both languages, and record access limitations honestly.
- Organize explanations around meaningful questions, followed by a direct answer, reasoning, examples, and relevant limitations. Keep the sequence readable from beginning to end; do not mechanically turn every heading into a question.
- Preserve passages that already read naturally. Change them only for a factual error, a real structural problem, or a concrete reading obstacle; do not expand the scope into AI infrastructure.
- Keep chapter paths and stable identifiers independent of localized titles. The book manifest defines reading order; topic and module indexes remain useful for the website.
- Change English first and synchronize the corresponding Chinese text in the same PR. An English-only wording change may leave Chinese text unchanged only after explicitly reviewing that the translation still applies. Never refresh synchronization hashes merely to hide stale translations.
- Use `book/i18n/README.md` and `book/i18n/glossary.json` for bilingual conventions. Preserve code identifiers, protocol values, data, units, time zones, and mathematical meaning; translate explanatory text, comments, and diagram labels. Do not replace complete chapters with summaries.
- Keep technical chapters free of repeated author signatures and copyright or license boilerplate. Centralize original attribution and rights information in the book's closing matter and repository license. Preserve source citations and required third-party notices.
- Do not invent acknowledgments, endorsements, ISBNs, publication history, or contributors. Keep author-facing placeholders out of the assembled reader manuscript.
- Retain Mermaid and LaTeX as source formats, with prose that explains their meaning. The EPUB exporter creates local static figures and formulas; format checks do not replace Kindle Previewer or publication review.
- Verify KDP's current language and content requirements before release. Do not label Simplified Chinese as another language or describe AI-generated text, images, or translations as merely AI-assisted.

## Documentation format

- Group chapters by topic and module under lowercase English directory names, using `docs/<topic>/<NN-module>/NN-chapter.md`.
- Give every topic and module directory paired `README.md` and `README.zh.md` indexes, with titles and navigation text in their respective languages.
- Write chapters in GitHub-Flavored Markdown inside the matching topic directory.
- Use Mermaid for diagrams and LaTeX only for actual mathematical expressions.
- Keep conceptual relationships and prose in Markdown instead of wrapping them in LaTeX.
- Use backticks or Unicode symbols for inline variable examples when that reads more clearly than inline math.

## GitHub math compatibility

- Do not use unsupported macros such as `\operatorname`, `\boxed`, or `\text`.
- Do not place raw `<` or `>` characters inside math expressions. Write an explicit range such as `y_1,\ldots,y_{t-1}` instead of `y_{<t}`.
- Keep display formulas between standalone `$$` delimiters.
- Separate inline `$...$` from preceding Chinese text or punctuation with a space; otherwise GitHub may leave it as raw TeX.
- Keep operators on the same line as an operand; a lone `-` or `=` can turn a formula into a Markdown heading. Do not put blank lines inside a display block.
- Avoid backslash-punctuation commands in math: GitHub Markdown can strip their backslashes. Use `\Vert`, `\lbrace` / `\rbrace`, and `\quad` where needed; use `\cr` for matrix row breaks instead of `\\`. Put percentages in prose or use decimals.
- Check braces, math delimiters, and fenced code blocks before publishing.
- Review the rendered GitHub and Wiki pages after adding or changing formulas; a successful local build does not prove browser math rendering works.

## Page metadata and discoverability

- Add a specific front matter `description` to important chapters and topic indexes.
- Keep descriptions factual and readable; do not repeat keyword variants.
- Add FAQ sections only for recurring reader questions, and keep every marked-up answer visible on the page.
- Use `scripts/mkdocs_hooks.py` and `overrides/main.html` for site-wide metadata and structured data instead of copying HTML into chapters.
- Attribute original documentation and diagrams to Polo Li under CC BY 4.0 in centralized project and book notices, not repeated chapter footers.

## Publishing

- Update the module `README.md`, topic `README.md`, root indexes, and `mkdocs.yml` navigation when adding, moving, or removing a chapter.
- Update both language editions, their manifests, paired indexes, and synchronization records when changing the chapter inventory. Do not publish missing translations through a fallback language.
- Run the documentation, translation synchronization, Chinese-link, Mermaid, and strict site checks before publication. Check and assemble both book languages; changes to export behavior also require the EPUB regression and format checks.
- Submit manuscript revisions as a pull request for the user to merge. Do not push these changes to `main`, merge the PR, or publish the book on the user's behalf.
- Only use direct publication when the user explicitly requests it.
