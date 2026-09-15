---
description: 比较单、多 Agent 的选型条件，梳理并行调度、交接协议、共享状态一致性与失败恢复。
---

# Agent · 多智能体系统

先判断任务是否值得拆成独立决策循环，再讨论怎样交接、调度和验收。重点区分 Agent 的语义协作与存储系统的强一致提交，避免把多角色投票当成分布式共识。

## 章节

1. [第九章：Single-Agent 与 Multi-Agent 系统](09-single-vs-multi-agent.md)
2. [第十三章：Multi-Agent 协作、路由与动态切换](13-multi-agent-coordination.md)

第九章适合比较上下文隔离、任务耦合、成本与评测基线；第十三章进一步讨论消息语义、并发写入、租约、预算和故障恢复。

返回 [Agent 相关知识点](../README.md)。
