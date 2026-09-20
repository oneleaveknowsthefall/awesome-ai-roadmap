---
description: Examines MCP roles, capabilities, per-request negotiation, transports, and authorization against version 2026-07-28, distinguishing legacy compatibility paths.
---

# Tools · Model Context Protocol

MCP architecture, capabilities, transports, technology selection, and protocol identity and security boundaries.

The baseline is the [2026-07-28 Current specification](https://modelcontextprotocol.io/specification/versioning). Its core semantics have no initialization handshake and must not be mixed with the session model of 2025-11-25 and earlier. Sampling, Roots, and Logging are deprecated but not yet removed; Tasks have moved to an optional extension. SDK version numbers are not protocol versions.

## Chapters

1. [Chapter 4: The Core of the Model Context Protocol](04-what-is-mcp.md)
2. [Chapter 5: The Three Layers of MCP](05-mcp-components.md)
3. [Chapter 6: MCP and Function Calling—Differences and Tradeoffs](06-mcp-vs-function-calling.md)
4. [Chapter 12: MCP Transports](12-mcp-transport.md)
5. [Chapter 15: Tool Protocol Security](15-tool-protocol-security.md)

Back to [Tools topics](../README.md).
