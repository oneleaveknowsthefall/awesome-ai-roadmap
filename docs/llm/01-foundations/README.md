---
description: Study language-model objectives, Transformer data flow, attention costs, positional encoding, and tokenization, using calculations and counterexamples to explain their limits.
---

# LLM · Foundations

First distinguish training objectives from model architecture, then trace a request through Tokenizer → Transformer → output distribution. Knowing the names is not enough: you need to calculate tensor shapes and KV cache size, and explain causal masks, positional extrapolation, and tokenization boundaries.

## Chapters

1. [Chapter 1: How Large Language Models Differ from Traditional NLP](01-what-is-llm.md)
2. [Chapter 2: Transformer Architecture](02-transformer-architecture.md)
3. [Chapter 3: MHA Limitations, MQA, GQA, and FlashAttention](03-attention-variants.md)
4. [Chapter 4: Positional Encoding](04-position-encoding.md)
5. [Chapter 5: Tokenizers](05-tokenizer.md)

Return to [LLM Topics](../README.md).
