---
description: Explore decoding, sampling, KV and prefix caching, quantization, MoE, and inference runtimes through probability mechanisms, memory estimates, and serving metrics.
---

# LLM · Inference and Serving

This module covers decoding, sampling, KV caching, quantization, MoE, and inference serving frameworks.

Keep three questions separate as you read: **Does output selection change the target distribution? How do architecture and precision affect resource requirements? Can serving schedules meet latency and throughput constraints?** Parameter count, bit width, or a framework name alone cannot determine end-to-end performance.

## Chapters

1. [Chapter 12: Decoding Strategies](12-decoding-strategies.md)
2. [Chapter 13: Tuning Temperature, Top-P, and Top-K](13-temperature-top-p-top-k.md)
3. [Chapter 14: KV Cache and Prompt Caching](14-kv-cache.md)
4. [Chapter 15: Model Quantization](15-quantization.md)
5. [Chapter 19: Mixture-of-Experts Models](19-moe.md)
6. [Chapter 20: Choosing a Serving Framework](20-deployment-frameworks.md)

Return to [LLM Topics](../README.md).

Architecture examples retain explicit model versions. API defaults, cache prices, and framework support matrices depend on the official sources cited in each chapter and the deployed version; historical experimental results are not guarantees of current performance.
