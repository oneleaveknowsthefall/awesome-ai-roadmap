---
description: 按 MCP 2026-07-28 核查角色、能力、逐请求协商、传输及授权，并区分旧版本兼容路径。
---

# Tools · 模型上下文协议

覆盖 MCP 架构、能力、传输、选型以及协议身份与安全边界。

以 [2026-07-28 Current 规范](https://modelcontextprotocol.io/specification/versioning)为基准：无初始化握手的核心语义，不可与 2025-11-25 及以前的会话模型混用。Sampling、Roots、Logging 已弃用但尚未移除；Tasks 已迁到可选扩展。SDK 版本号不等于协议版本。

## 章节

1. [第四章：MCP 模型上下文协议的核心内容](04-what-is-mcp.md)
2. [第五章：MCP 的三层组成](05-mcp-components.md)
3. [第六章：MCP 与 Function Calling 的区别与选型](06-mcp-vs-function-calling.md)
4. [第十二章：MCP 的传输层](12-mcp-transport.md)
5. [第十五章：Tool Protocol 安全](15-tool-protocol-security.md)

返回 [Tools 相关知识点](../README.md)。
