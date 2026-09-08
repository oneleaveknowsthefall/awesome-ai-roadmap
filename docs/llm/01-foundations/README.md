---
description: 学习语言模型目标、Transformer 数据流、注意力开销、位置编码与分词，并用计算和反例解释它们的适用边界。
---

# LLM · 基础原理

先区分训练目标和模型结构，再沿一次请求的 Tokenizer → Transformer → 输出分布追踪数据。基础题不能只记名称：需要能算出张量形状和 KV Cache 大小，解释因果掩码、位置外推及分词边界。

## 章节

1. [第一章：大语言模型与传统 NLP 的本质区别](01-what-is-llm.md)
2. [第二章：Transformer 架构原理](02-transformer-architecture.md)
3. [第三章：MHA 的局限与 MQA、GQA、Flash Attention](03-attention-variants.md)
4. [第四章：位置编码](04-position-encoding.md)
5. [第五章：Tokenizer 分词器](05-tokenizer.md)

返回 [LLM 相关知识点](../README.md)。
