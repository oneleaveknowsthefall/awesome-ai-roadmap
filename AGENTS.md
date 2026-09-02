# Repository Instructions

## Documentation format

- Group chapters by topic and module under lowercase English directory names, using `docs/<topic>/<NN-module>/NN-chapter.md`.
- Give every topic and module directory a `README.md` index with a Chinese display title.
- Write chapters in GitHub-Flavored Markdown inside the matching topic directory.
- Use Mermaid for diagrams and LaTeX only for actual mathematical expressions.
- Keep conceptual relationships and Chinese prose in Markdown instead of wrapping them in LaTeX.
- Use backticks or Unicode symbols for inline variable examples when that reads more clearly than inline math.

## GitHub math compatibility

- Do not use unsupported macros such as `\operatorname`, `\boxed`, or `\text`.
- Do not place raw `<` or `>` characters inside math expressions. Write an explicit range such as `y_1,\ldots,y_{t-1}` instead of `y_{<t}`.
- Keep display formulas between standalone `$$` delimiters.
- Check braces, math delimiters, and fenced code blocks before publishing.
- Review the rendered GitHub page after adding or changing formulas.

## Page metadata and discoverability

- Add a specific front matter `description` to important chapters and topic indexes.
- Keep descriptions factual and readable; do not repeat keyword variants.
- Add FAQ sections only for recurring reader questions, and keep every marked-up answer visible on the page.
- Use `scripts/mkdocs_hooks.py` and `overrides/main.html` for site-wide metadata and structured data instead of copying HTML into chapters.
- Attribute original documentation and diagrams to Polo Li under CC BY 4.0.

## Publishing

- Update the module `README.md`, topic `README.md`, root indexes, and `mkdocs.yml` navigation when adding, moving, or removing a chapter.
- Run `python3 scripts/check_docs.py`, `npm run check:mermaid`, and `.venv/bin/mkdocs build --strict` before publishing.
- Commit completed documentation directly and push it to the remote `main` branch.
- Do not create a pull request unless the user explicitly asks for one.
