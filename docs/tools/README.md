# Tools 相关知识点

本主题位于协议与接口层，解释模型如何调用工具、MCP 如何标准化能力接入、Skill 如何组织知识、Agent 如何跨系统通信，以及传输与网关如何落地。

## 子模块

1. [Function Calling（第 1–3、7 章）](01-function-calling/README.md)
2. [MCP（第 4–6、12、15 章）](02-mcp/README.md)
3. [Skills（第 8–10 章）](03-skills/README.md)
4. [Agent 通信（第 11 章）](04-agent-communication/README.md)
5. [传输与网关（第 13–14 章）](05-transport-gateway/README.md)

## 模块关系

```mermaid
flowchart TB
    FC[Function Calling] --> MCP[MCP]
    FC --> SK[Skills]
    MCP --> SK
    MCP --> A2A[Agent 通信]
    FC --> TG[传输与网关]
    MCP --> TG
    A2A --> TG
```

## 阅读建议

- **工具调用入门**：Function Calling → MCP；
- **Agent 能力封装**：Function Calling → Skills → MCP；
- **跨系统协作**：MCP → Agent 通信；
- **生产治理**：MCP → 传输与网关。

返回[文档主题索引](../README.md)。
