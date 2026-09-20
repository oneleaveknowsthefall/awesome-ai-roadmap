---
description: 区分 SSE 事件格式、WebSocket 双向消息与 WebRTC 媒体栈，并分析模型网关的重试、缓存和治理边界。
---

# Tools · 传输与网关

比较流式和实时传输，并讨论 LLM Gateway 的生产治理。

先区分事件格式、浏览器 API 和底层传输，再讨论断线恢复、取消与副作用。网关的接口兼容不等于模型能力兼容；语义缓存命中率和额外延迟都应在具体工作负载下测量。

## 章节

1. [第十三章：SSE、WebSocket 与 WebRTC](13-sse-websocket-webrtc.md)
2. [第十四章：LLM 网关](14-llm-gateway.md)

返回 [Tools 相关知识点](../README.md)。
