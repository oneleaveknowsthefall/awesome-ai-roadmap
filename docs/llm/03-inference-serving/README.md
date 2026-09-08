---
description: 汇集解码、采样、KV 与前缀缓存、量化、MoE 和推理框架章节，按概率机制、内存估算及服务指标梳理部署取舍。
---

# LLM · 推理与部署

覆盖解码、采样、KV Cache、量化、MoE 与推理服务框架。

阅读时区分三个层次：**输出选择是否改变目标分布、模型结构与精度如何影响资源、服务调度能否满足延迟与吞吐约束**。参数量、位宽和框架名称都不能单独推导端到端性能。

## 章节

1. [第十二章：解码策略](12-decoding-strategies.md)
2. [第十三章：Temperature、Top-P、Top-K 调参](13-temperature-top-p-top-k.md)
3. [第十四章：KV Cache 与 Prompt Caching](14-kv-cache.md)
4. [第十五章：模型量化](15-quantization.md)
5. [第十九章：MoE 混合专家模型](19-moe.md)
6. [第二十章：部署框架选型](20-deployment-frameworks.md)

返回 [LLM 相关知识点](../README.md)。

本模块资料核对基准为 2026-09-08。模型架构示例保留明确版本；API 默认值、缓存价格与框架支持矩阵以各章所引官方资料及实际部署版本为准，不将历史实验数值当作当前性能保证。

本文原创编排：Polo Li，采用 CC BY 4.0。
