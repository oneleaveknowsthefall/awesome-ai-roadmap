# Agent 相关知识点

本主题位于应用架构层，覆盖 Agent 基础架构、运行时 Harness、推理规划、记忆上下文、多智能体协作，以及生产评估与安全。

## 子模块

1. [基础与架构（第 1–3 章）](01-foundations/README.md)
2. [Runtime 与 Harness（第 16–23 章）](02-runtime-harness/README.md)
3. [推理、规划与反思（第 4–6、11–12 章）](02-reasoning-planning/README.md)
4. [记忆与上下文（第 7–8、10 章）](03-memory-context/README.md)
5. [多智能体系统（第 9、13 章）](04-multi-agent/README.md)
6. [评估与安全（第 14–15 章）](05-production/README.md)

## 模块关系

```mermaid
flowchart TB
    F[基础与架构] --> H[Runtime 与 Harness]
    F --> R[推理、规划与反思]
    F --> M[记忆与上下文]
    H --> R
    H --> M
    R --> A[多智能体系统]
    M --> A
    H --> P[评估与安全]
    R --> P
    M --> P
    A --> P
```

协议细节不在本主题重复展开：工具接入见 [Tools · MCP](../tools/02-mcp/README.md)，跨 Agent 互操作见 [Tools · Agent 通信](../tools/04-agent-communication/README.md)。

## 阅读建议

- **Agent 入门**：基础与架构 → 推理、规划与反思；
- **有状态 Agent**：基础与架构 → 记忆与上下文；
- **多 Agent 系统**：基础与架构 → 推理规划 → 多智能体系统；
- **工程落地 / Harness 开发**：基础与架构 → Runtime 与 Harness；
- **生产上线**：完成目标模块后阅读评估与安全。

返回[文档主题索引](../README.md)。
