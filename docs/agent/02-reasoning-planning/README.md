---
description: 区分模型推理、推理时搜索、任务调度与反馈修订，理解 ReAct、CoT、ToT 和 Reflexion 的机制及适用边界。
---

# Agent · 推理、规划与反思

覆盖设计范式、搜索推理、任务拆分、显式规划与反思闭环。

阅读时注意四个不同的变化对象：训练更新模型参数；CoT、采样与搜索改变一次求解的计算过程；规划与调度管理行动和状态；反思利用反馈修改候选或经验记忆。增加调用次数、写入记忆和获得测试反馈，都不等于模型发生了参数学习。

第四章先看控制循环，第五章比较推理方法，第六章处理依赖与恢复，第十一、十二章分别深入规划和纠错。文中经典实验用于说明机制，不代表当前模型或业务场景的固定收益；选型需比较相同预算下的任务完成率、延迟与副作用。

## 章节

1. [第四章：Agent 设计范式](04-agent-design-patterns.md)
2. [第五章：Agent 的模型推理与搜索方法](05-agent-reasoning-methods.md)
3. [第六章：复杂任务拆分与调度](06-task-decomposition.md)
4. [第十一章：如何赋予 LLM 与 Agent 规划能力](11-llm-agent-planning.md)
5. [第十二章：Agent 的反思、验证与自我改进](12-agent-reflection.md)

返回 [Agent 相关知识点](../README.md)。

本模块原创文档与示意图：Polo Li，采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)；引用研究归原作者所有。
