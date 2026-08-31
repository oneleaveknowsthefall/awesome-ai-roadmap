# AI 知识图谱

本仓库系统梳理 LLM、Tools、Agent、RAG 与应用框架等 AI 知识。文档采用主题目录、主题索引和章节交叉链接构成的分层结构，便于 GitHub 阅读与 DeepWiki 建立知识关联。

> **内容基线：2026-08-31。** 高时效性章节应结合文中链接的官方文档和实际版本再次核验。

## 总体策略图

本仓库按「抽象层次」组织知识，五个主题自下而上构成一条完整的技术栈。

```mermaid
flowchart TB
    subgraph L1["第一层 · 模型底层原理"]
        LLM["LLM · 23 章<br/>Transformer / 训练 / 多模态 / 推理 / 部署"]
    end

    subgraph L2["第二层 · 协议与接口"]
        TOOLS["Tools · 15 章<br/>Function Calling / MCP / Skill / A2A / 安全"]
    end

    subgraph L3["第三层 · 应用架构"]
        AGENT["Agent · 15 章<br/>规划 / 记忆 / 反思 / 多智能体"]
        RAG["RAG · 21 章<br/>索引 / 检索 / 多模态 / 生成"]
    end

    subgraph L4["第四层 · 框架实现"]
        LC["LangChain · 13 章<br/>编排 / 状态 / 持久化 / 评测"]
    end

    LLM --> TOOLS
    TOOLS --> AGENT
    LLM --> RAG
    AGENT --> LC
    RAG --> LC
    RAG -.知识增强.-> AGENT
```

## 主题目录

| 层次 | 主题 | 目录 | 状态 |
|---|---|---|---|
| 底层原理 | LLM 相关知识点 | [`docs/llm/`](docs/llm/README.md) | 23 章 |
| 协议接口 | Tools 相关知识点 | [`docs/tools/`](docs/tools/README.md) | 15 章 |
| 应用架构 | Agent 相关知识点 | [`docs/agent/`](docs/agent/README.md) | 15 章 |
| 应用架构 | RAG 相关知识点 | [`docs/rag/`](docs/rag/README.md) | 21 章 |
| 框架实现 | LangChain 相关知识点 | [`docs/langchain/`](docs/langchain/README.md) | 13 章 |

完整章节目录、跨主题归属约定与推荐阅读路径见 [`docs/README.md`](docs/README.md)。每个主题的 `README.md` 是该主题章节导航与知识图谱的唯一维护入口。

## 文档质量

仓库提供 `scripts/check_docs.py` 与 `scripts/check_mermaid.mjs`，用于检查章节编号、标题、代码与数学围栏、禁用 LaTeX 宏、内部链接、导航计数和 Mermaid 语法。写作与贡献约定见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。
