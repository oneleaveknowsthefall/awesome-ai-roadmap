---
description: Connect multimodal data and deployment validation, covering filtering bias, factual alignment, benchmark leakage, content provenance, and reuse conditions for media features and language caches.
---

# Multimodal · Training Data, Evaluation, and Serving

This module covers collecting and aligning multimodal training data, along with issues requiring dedicated validation before production: benchmark contamination, image- and generated-content-specific safety risks, and inference-serving architecture.

## Chapters

1. [Chapter 9: Multimodal Training Data and Alignment](09-multimodal-data-alignment.md)
2. [Chapter 10: Multimodal Evaluation, Safety, and Inference Serving](10-evaluation-safety-serving.md)

## Connections within the module

```mermaid
flowchart LR
    D[Multimodal Training Data<br/>and Alignment] --> E[Multimodal Evaluation,<br/>Safety, and Inference Serving]
```

Chapter 9 examines how data supplies or omits training signals; Chapter 10 asks how to verify capabilities, risks, and serving costs. These are not finishing touches added after training: splits, decontamination, permissions, and resource budgets must be determined during data collection and system design.

Important distinctions include: similarity is not pair correctness, a release date does not establish freedom from contamination, content credentials do not establish factual truth, and media-feature caching does not permit arbitrary-context KV reuse. For the general framework, see [LLM · Multimodal Models](../../llm/06-multimodal/23-multimodal-models.md).

Return to [Multimodal Topics](../README.md).
