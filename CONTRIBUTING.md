# 贡献指南

## 目录与命名

- 章节放在对应的 `docs/<topic>/<module>/` 目录，文件名使用 `NN-lowercase-slug.md`。
- 每个主题 README 维护子模块目录与模块关系；每个子模块 README 维护章节目录；根 README 仅维护主题级入口。
- 新概念应先确认其「详解归属地」。其他主题只解释本层视角，并链接到主章节，避免复制整段内容。

## 章节结构

1. 使用唯一一级标题：`# 第N章：标题`。
2. 二级标题按 `## N.1`、`## N.2` 连续编号。
3. 使用 Mermaid 表达流程和关系；LaTeX 只用于数学表达。
4. 章节末尾包含“常见错误”“本章总结”和一手参考资料。
5. 涉及版本、性能或模型能力时，注明核验日期、版本和适用条件，避免使用“永远”“唯一”“必然”等无边界结论。

## 数学与链接

- 不使用 GitHub 不支持的 `\operatorname`、`\boxed`、`\text`。
- 数学环境中不写裸 `<` 或 `>`。
- 优先引用规范、官方文档、原论文和可复现的工程报告。
- 相对链接应指向概念的详解归属章节，不重复维护同一内容。

## 提交前检查

```bash
python3 scripts/check_docs.py
npm install
npm run check:mermaid
python3 -m venv .venv
.venv/bin/pip install -r requirements-docs.txt
.venv/bin/mkdocs build --strict
```

新增章节后同步更新子模块 `README.md`、主题 `README.md` 中的章节范围，以及 `docs/README.md` 的主题计数。
新增、删除或移动页面时，还需同步更新 `mkdocs.yml` 中的 Wiki 导航。
