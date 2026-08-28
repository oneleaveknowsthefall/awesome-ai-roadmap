# Repository Instructions

## Documentation format

- Write chapters in GitHub-Flavored Markdown under `docs/`.
- Use Mermaid for diagrams and LaTeX only for actual mathematical expressions.
- Keep conceptual relationships and Chinese prose in Markdown instead of wrapping them in LaTeX.
- Use backticks or Unicode symbols for inline variable examples when that reads more clearly than inline math.

## GitHub math compatibility

- Do not use unsupported macros such as `\operatorname`, `\boxed`, or `\text`.
- Do not place raw `<` or `>` characters inside math expressions. Write an explicit range such as `y_1,\ldots,y_{t-1}` instead of `y_{<t}`.
- Keep display formulas between standalone `$$` delimiters.
- Check braces, math delimiters, and fenced code blocks before publishing.
- Review the rendered GitHub page after adding or changing formulas.

## Publishing

- Update the root `README.md` table of contents when adding a chapter.
- Commit completed documentation directly and push it to the remote `main` branch.
- Do not create a pull request unless the user explicitly asks for one.
