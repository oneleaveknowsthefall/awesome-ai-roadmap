---
description: Compare single-agent and multi-agent designs, parallel scheduling, handoff contracts, shared-state consistency, and failure recovery.
---

# Agents · Multi-Agent Systems

First decide whether a task warrants separate decision loops, then consider handoffs, scheduling, and acceptance. Distinguish coordination over the meaning of agents' results from strongly consistent commits in a storage system: votes from multiple roles are not distributed consensus.

## Chapters

1. [Chapter 9: Single-Agent and Multi-Agent Systems](09-single-vs-multi-agent.md)
2. [Chapter 13: Multi-Agent Coordination, Routing, and Dynamic Switching](13-multi-agent-coordination.md)

Chapter 9 compares context isolation, task coupling, costs, and evaluation baselines. Chapter 13 goes further into message semantics, concurrent writes, leases, budgets, and failure recovery.

Back to [Agent Topics](../README.md).
