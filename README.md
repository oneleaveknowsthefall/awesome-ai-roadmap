# AI 知识图谱

本仓库系统梳理从模型原理到生产治理的 AI 技术栈。文档采用“主题 → 子模块 → 章节”的知识图谱结构，并通过 MkDocs Material 发布为可搜索的 Wiki。

**在线 Wiki：** <https://zongyangbigpolo.github.io/awesome-ai-roadmap/>

> **内容基线：2026-08-31。** 高时效性章节应结合文中链接的官方文档和实际版本再次核验。

## 总体策略图

九个主题按“模型能力 → 协议接口 → 应用架构 → 框架实现 → 生产治理 → 现场交付”组织，共 139 章。

```mermaid
flowchart TB
    subgraph L1["第一层 · 模型与多模态能力"]
        LLM["LLM · 23 章<br/>Transformer / 训练 / 推理 / 部署"]
        MM["多模态 AI · 10 章<br/>视觉 / 语音 / 图像与视频生成"]
    end

    subgraph L2["第二层 · 协议与接口"]
        TOOLS["Tools · 15 章<br/>Function Calling / MCP / Skill / A2A / 安全"]
    end

    subgraph L3["第三层 · 应用架构"]
        AGENT["Agent · 23 章<br/>Harness / 规划 / 记忆 / 多智能体"]
        RAG["RAG · 21 章<br/>索引 / 检索 / 多模态 / 生成"]
    end

    subgraph L4["第四层 · 框架实现"]
        FW["框架与编排 · 23 章<br/>LangChain / LlamaIndex / DSPy / Semantic Kernel"]
    end

    subgraph L5["第五层 · 生产与治理"]
        ENG["AI Engineering · 13 章<br/>评测 / 可观测性 / 发布 / SLO / 成本"]
        SAFE["AI 安全与治理 · 10 章<br/>威胁 / 隔离 / 红队 / 审计"]
    end

    subgraph L6["第六层 · 现场交付"]
        FDE["FDE · 1 章<br/>发现 / 验收 / 集成 / 交付 / 复用"]
    end

    LLM --> MM
    LLM --> TOOLS
    TOOLS --> AGENT
    LLM --> RAG
    MM --> AGENT
    MM --> RAG
    AGENT --> FW
    RAG --> FW
    FW --> ENG
    ENG --> SAFE
    ENG --> FDE
    SAFE --> FDE
    FDE -.现场反馈.-> FW
    AGENT -.风险输入.-> SAFE
    RAG -.风险输入.-> SAFE
    RAG -.知识增强.-> AGENT
```

## 主题目录

| 层次 | 主题 | 目录 | 状态 |
|---|---|---|---|
| 底层原理 | LLM 相关知识点 | [`docs/llm/`](docs/llm/README.md) | 23 章 |
| 模型能力 | 多模态 AI | [`docs/multimodal/`](docs/multimodal/README.md) | 10 章 |
| 协议接口 | Tools 相关知识点 | [`docs/tools/`](docs/tools/README.md) | 15 章 |
| 应用架构 | Agent 相关知识点 | [`docs/agent/`](docs/agent/README.md) | 23 章 |
| 应用架构 | RAG 相关知识点 | [`docs/rag/`](docs/rag/README.md) | 21 章 |
| 框架实现 | AI 框架与编排 | [`docs/frameworks/`](docs/frameworks/README.md) | 23 章 |
| 生产工程 | AI Engineering / LLMOps | [`docs/engineering/`](docs/engineering/README.md) | 13 章 |
| 安全治理 | AI 安全与治理 | [`docs/safety/`](docs/safety/README.md) | 10 章 |
| 现场交付 | FDE | [`docs/fde/`](docs/fde/README.md) | 1 章 |

完整目录、跨主题归属约定与推荐阅读路径见 [`docs/README.md`](docs/README.md)。每个主题 README 维护子模块入口与模块关系，每个子模块 README 维护具体章节顺序。

## 文档质量

仓库提供 `scripts/check_docs.py` 与 `scripts/check_mermaid.mjs`，用于检查章节编号、标题、代码与数学围栏、禁用 LaTeX 宏、内部链接、导航计数和 Mermaid 语法。写作与贡献约定见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。
