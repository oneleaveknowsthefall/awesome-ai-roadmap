# AI 知识图谱

本仓库用于系统梳理 LLM、RAG、Agent 和应用框架等 AI 知识，并采用便于 DeepWiki 索引的分层文档结构。

## 总体策略图

本仓库按「抽象层次」组织知识，五个主题自下而上构成一条完整的栈。

```mermaid
flowchart TB
    subgraph L1["第一层 · 模型底层原理"]
        LLM["LLM · 22 章<br/>Transformer / 训练 / 推理 / 部署"]
    end

    subgraph L2["第二层 · 协议与接口"]
        TOOLS["Tools · 14 章<br/>Function Calling / MCP / Skill / A2A"]
    end

    subgraph L3["第三层 · 应用架构"]
        AGENT["Agent · 15 章<br/>规划 / 记忆 / 反思 / 多智能体"]
        RAG["RAG · 20 章<br/>索引 / 检索 / 重排 / 生成"]
    end

    subgraph L4["第四层 · 框架实现"]
        LC["LangChain · 12 章<br/>编排 / 状态 / 持久化"]
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
| 底层原理 | LLM 相关知识点 | [`docs/llm/`](docs/llm/README.md) | 已完成 22 章 |
| 协议接口 | Tools 相关知识点 | [`docs/tools/`](docs/tools/README.md) | 已完成 14 章 |
| 应用架构 | Agent 相关知识点 | [`docs/agent/`](docs/agent/README.md) | 已完成 15 章 |
| 应用架构 | RAG 相关知识点 | [`docs/rag/`](docs/rag/README.md) | 已完成 20 章 |
| 框架实现 | LangChain 相关知识点 | [`docs/langchain/`](docs/langchain/README.md) | 规划 12 章，撰写中 |

完整文档索引与主题间交叉引用约定见 [`docs/README.md`](docs/README.md)。

## Agent 相关知识点

1. [从大模型到 AI Agent](docs/agent/01-agent-foundations.md)
2. [Agent 的现代系统架构](docs/agent/02-agent-architecture.md)
3. [Tools、Skills、Agents、Workflows 与 AGENTS.md](docs/agent/03-agentic-building-blocks.md)
4. [Agent 设计范式](docs/agent/04-agent-design-patterns.md)
5. [Agent 的模型推理与搜索方法](docs/agent/05-agent-reasoning-methods.md)
6. [复杂任务拆分与调度](docs/agent/06-task-decomposition.md)
7. [AI Agent 的记忆机制](docs/agent/07-agent-memory.md)
8. [Agent 长短期记忆系统的工程实现](docs/agent/08-agent-memory-implementation.md)
9. [Single-Agent 与 Multi-Agent 系统](docs/agent/09-single-vs-multi-agent.md)
10. [Agent 记忆与上下文压缩](docs/agent/10-agent-memory-compression.md)
11. [如何赋予 LLM 与 Agent 规划能力](docs/agent/11-llm-agent-planning.md)
12. [Agent 的反思、验证与自我改进](docs/agent/12-agent-reflection.md)
13. [Multi-Agent 协作、路由与动态切换](docs/agent/13-multi-agent-coordination.md)
14. [Agent 评估与 Benchmark](docs/agent/14-agent-evaluation.md)
15. [Agent 安全与 Prompt Injection](docs/agent/15-agent-security.md)

## Agent 知识图谱

```mermaid
flowchart TB
    LLM[大语言模型] --> FOUNDATION[01 Agent 基础]
    FOUNDATION --> ARCH[02 现代系统架构]

    ARCH --> BUILD[03 构建单元]
    BUILD --> TOOLS[Tools 与 Skills]
    BUILD --> WORKFLOW[Workflows]
    BUILD --> MCP[MCP]

    ARCH --> PATTERN[04 Agent 设计范式]
    PATTERN --> REACT[ReAct]
    PATTERN --> PLANEXEC[Plan-and-Execute]
    PATTERN --> REFLECT[Reflection]

    PATTERN --> REASON[05 推理与搜索方法]
    REASON --> PLAN[11 规划能力]
    PLAN --> DECOMP[06 复杂任务拆分]
    REFLECT --> REFMECH[12 反思与验证]

    ARCH --> MEMORY[07 记忆机制]
    MEMORY --> MEMIMPL[08 长短期记忆实现]
    MEMIMPL --> COMPRESS[10 记忆与上下文压缩]

    DECOMP --> MULTI[09 Single-Agent 与 Multi-Agent]
    MULTI --> COORD[13 协作、路由与动态切换]
    COORD --> A2A[A2A]

    MCP --> EXTERNAL[外部工具与数据]
    A2A --> REMOTE[跨系统 Agent 协作]
    WORKFLOW --> MULTI

    COORD --> EVAL[14 评估与 Benchmark]
    REFMECH --> EVAL
    EVAL --> SEC[15 安全与 Prompt Injection]
    TOOLS --> SEC
    MEMORY --> SEC
    EXTERNAL --> SEC
```

## RAG 相关知识点

1. [RAG 是什么，解决什么问题](docs/rag/01-what-is-rag.md)
2. [RAG、微调与长上下文的三方取舍](docs/rag/02-rag-finetune-longcontext.md)
3. [文档解析与预处理](docs/rag/03-document-parsing.md)
4. [Chunking 策略与粒度选择](docs/rag/04-chunking-strategy.md)
5. [语义被切断怎么办](docs/rag/05-semantic-truncation.md)
6. [Embedding 原理与技术演进](docs/rag/06-embedding-principles.md)
7. [Embedding 模型选型与评估](docs/rag/07-embedding-selection.md)
8. [向量数据库与 ANN 索引](docs/rag/08-vector-database.md)
9. [向量库生产实践与性能调优](docs/rag/09-vectordb-production.md)
10. [RAG 在线链路全流程](docs/rag/10-online-pipeline.md)
11. [检索范式：稀疏、稠密与后期交互](docs/rag/11-retrieval-paradigms.md)
12. [Query 理解与改写](docs/rag/12-query-rewriting.md)
13. [多路召回、RRF 融合与 Rerank](docs/rag/13-hybrid-retrieval-rerank.md)
14. [检索优化的四层框架](docs/rag/14-retrieval-optimization.md)
15. [高级 RAG 范式](docs/rag/15-advanced-rag-paradigms.md)
16. [GraphRAG 与图检索](docs/rag/16-graphrag.md)
17. [生成、Grounding 与幻觉规避](docs/rag/17-generation-hallucination.md)
18. [RAG 评估体系](docs/rag/18-rag-evaluation.md)
19. [知识库的动态更新与增量索引](docs/rag/19-dynamic-update.md)
20. [RAG 落地难点与安全](docs/rag/20-rag-challenges-security.md)

## RAG 知识图谱

```mermaid
flowchart TB
    R1[01 RAG 是什么] --> R2[02 微调 长上下文 三方取舍]
    R1 --> OFF[离线链路]
    R1 --> ON[在线链路]

    OFF --> R3[03 文档解析与预处理]
    R3 --> R4[04 Chunking 策略与粒度]
    R4 --> R5[05 语义切断的解法]
    R5 --> R6[06 Embedding 原理与演进]
    R6 --> R7[07 Embedding 选型与评估]
    R7 --> R8[08 向量库与 ANN 索引]
    R8 --> R9[09 生产实践与调优]

    ON --> R10[10 在线链路全流程]
    R10 --> R12[12 Query 理解与改写]
    R12 --> R11[11 检索范式]
    R11 --> R13[13 多路召回 RRF 与 Rerank]
    R13 --> R17[17 生成 Grounding 与幻觉]

    R9 --> R11
    R13 --> R14[14 检索优化四层框架]
    R14 --> R15[15 高级 RAG 范式]
    R15 --> R16[16 GraphRAG 与图检索]

    R17 --> R18[18 RAG 评估体系]
    R14 --> R18
    R18 --> R19[19 动态更新与增量索引]
    R19 --> R20[20 落地难点与安全]
    R17 --> R20
```

## Tools 相关知识点

1. [Function Calling 是什么，原理是什么](docs/tools/01-function-calling.md)
2. [LLM 如何学会调用工具](docs/tools/02-tool-learning.md)
3. [工具定义与 Schema 工程](docs/tools/03-tool-schema-design.md)
4. [MCP 模型上下文协议的核心内容](docs/tools/04-what-is-mcp.md)
5. [MCP 的三层组成](docs/tools/05-mcp-components.md)
6. [MCP 与 Function Calling 的区别与选型](docs/tools/06-mcp-vs-function-calling.md)
7. [为什么有些推理模型不支持 MCP](docs/tools/07-reasoning-models-and-tools.md)
8. [Skill 是什么](docs/tools/08-what-is-skill.md)
9. [Skill 与 MCP 的区别](docs/tools/09-skill-vs-mcp.md)
10. [Function Calling、Skill、MCP 三者关系](docs/tools/10-fc-skill-mcp.md)
11. [A2A 协议与 Agent 间通信](docs/tools/11-a2a-protocol.md)
12. [MCP 的传输方式](docs/tools/12-mcp-transport.md)
13. [SSE、WebSocket 与 WebRTC](docs/tools/13-sse-websocket-webrtc.md)
14. [LLM 网关](docs/tools/14-llm-gateway.md)

## Tools 知识图谱

```mermaid
flowchart TB
    MODEL[大语言模型] --> T1[01 Function Calling 原理]

    T1 --> T2[02 模型如何学会调工具]
    T1 --> T3[03 工具定义与 Schema 工程]
    T2 --> T7[07 推理模型与工具调用]

    T1 --> T4[04 MCP 核心内容]
    T4 --> T5[05 MCP 三层组成]
    T4 --> T6[06 MCP vs Function Calling]

    T3 --> T8[08 Skill 是什么]
    T8 --> T9[09 Skill vs MCP]
    T4 --> T9
    T6 --> T10[10 三者关系总览]
    T9 --> T10

    T4 --> T11[11 A2A 协议]
    T5 --> T12[12 MCP 传输方式]
    T12 --> T13[13 SSE / WebSocket / WebRTC]

    T10 --> T14[14 LLM 网关]
    T13 --> T14
    T11 --> T14
```

## LLM 相关知识点

1. [大语言模型与传统 NLP 的本质区别](docs/llm/01-what-is-llm.md)
2. [Transformer 架构原理](docs/llm/02-transformer-architecture.md)
3. [MHA 的局限与 MQA、GQA、Flash Attention](docs/llm/03-attention-variants.md)
4. [位置编码：sin/cos、RoPE 与 ALiBi](docs/llm/04-position-encoding.md)
5. [Tokenizer 分词器原理](docs/llm/05-tokenizer.md)
6. [大模型的三阶段训练流程](docs/llm/06-llm-training.md)
7. [Scaling Law 与涌现能力](docs/llm/07-scaling-law-emergence.md)
8. [微调方案全景](docs/llm/08-finetuning.md)
9. [LoRA 技术详解](docs/llm/09-lora.md)
10. [Post-Training：RLHF、DPO、GRPO 与拒绝采样](docs/llm/10-post-training.md)
11. [DPO 与 PPO 的区别](docs/llm/11-dpo-vs-ppo.md)
12. [解码策略：贪心、Beam Search 与采样](docs/llm/12-decoding-strategies.md)
13. [Temperature、Top-P 与 Top-K](docs/llm/13-temperature-top-p-top-k.md)
14. [KV Cache 与 Prompt Caching](docs/llm/14-kv-cache.md)
15. [模型量化：INT8、INT4、GPTQ 与 AWQ](docs/llm/15-quantization.md)
16. [Prompt 工程实践](docs/llm/16-prompt-engineering.md)
17. [CoT 思维链的原理与局限](docs/llm/17-cot.md)
18. [大模型幻觉的根因与缓解](docs/llm/18-hallucination.md)
19. [MoE 混合专家模型](docs/llm/19-moe.md)
20. [部署方案：vLLM、SGLang、TGI 与 llama.cpp](docs/llm/20-deployment-frameworks.md)
21. [大模型能力评测指标](docs/llm/21-evaluation-metrics.md)
22. [主流大模型对比与选型](docs/llm/22-model-selection.md)

## LLM 知识图谱

```mermaid
flowchart TB
    L1[01 LLM 与传统 NLP] --> L2[02 Transformer 架构]

    L2 --> L3[03 注意力变体与优化]
    L2 --> L4[04 位置编码]
    L1 --> L5[05 Tokenizer]

    L2 --> L6[06 三阶段训练流程]
    L6 --> L7[07 Scaling Law 与涌现]
    L6 --> L8[08 微调方案全景]
    L8 --> L9[09 LoRA]
    L6 --> L10[10 Post-Training]
    L10 --> L11[11 DPO vs PPO]

    L2 --> L12[12 解码策略]
    L12 --> L13[13 采样参数调参]
    L3 --> L14[14 KV Cache 与 Prompt Caching]
    L9 --> L15[15 模型量化]
    L14 --> L15

    L13 --> L16[16 Prompt 工程]
    L16 --> L17[17 CoT 思维链]
    L17 --> L18[18 幻觉根因与缓解]
    L10 --> L18

    L2 --> L19[19 MoE 混合专家]
    L14 --> L20[20 部署框架选型]
    L15 --> L20
    L19 --> L20

    L7 --> L21[21 能力评测指标]
    L18 --> L21
    L21 --> L22[22 模型对比与选型]
    L20 --> L22
```
