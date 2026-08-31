# Repository Instructions

## Documentation format

- Group chapters by topic under lowercase English directory names in `docs/`, such as `docs/agent/`, `docs/llm/`, `docs/rag/`, and `docs/langchain/`.
- Give every topic directory a `README.md` index with a Chinese display title.
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

## Publishing

- Update the topic `README.md`, `docs/README.md`, and root `README.md` navigation when adding a topic or chapter.
- Commit completed documentation directly and push it to the remote `main` branch.
- Do not create a pull request unless the user explicitly asks for one.
