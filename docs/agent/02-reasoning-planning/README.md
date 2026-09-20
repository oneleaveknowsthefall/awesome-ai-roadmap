---
description: Distinguish model reasoning, inference-time search, task scheduling, and feedback-driven revision, and understand the mechanisms and limits of ReAct, CoT, ToT, and Reflexion.
---

# Agents · Reasoning, Planning, and Reflection

Covers design patterns, reasoning with search, task decomposition, explicit planning, and reflection loops.

As you read, distinguish four different things that can change: training updates model parameters; CoT, sampling, and search change the computation used to solve a problem; planning and scheduling manage actions and state; reflection uses feedback to revise candidates or experiential memory. More calls, writes to memory, and test feedback do not, by themselves, mean that the model has learned through parameter updates.

Chapter 4 begins with the control loop, Chapter 5 compares reasoning methods, and Chapter 6 addresses dependencies and recovery. Chapters 11 and 12 examine planning and error correction in greater depth. The classic experiments illustrate mechanisms, not fixed gains for current models or business settings. Compare task completion rates, latency, and side effects under equal budgets when selecting an approach.

## Chapters

1. [Chapter 4: Agent Design Patterns](04-agent-design-patterns.md)
2. [Chapter 5: Model Reasoning and Search Methods for Agents](05-agent-reasoning-methods.md)
3. [Chapter 6: Complex Task Decomposition and Scheduling](06-task-decomposition.md)
4. [Chapter 11: Giving LLMs and Agents the Ability to Plan](11-llm-agent-planning.md)
5. [Chapter 12: Agent Reflection, Verification, and Self-improvement](12-agent-reflection.md)

Back to [Agent Topics](../README.md).
