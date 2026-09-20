---
description: Compare multimodal fusion through continuous feature concatenation, cross-attention, and discrete image–text sequences, distinguishing retrieval representations, generation objectives, and inference costs.
---

# Multimodal · Foundations and Architectures

This module covers continuous feature concatenation, cross-attention access, and joint generation with discrete tokens, distinguishing shared embedding spaces from generative distributions. Early/Late Fusion has different definitions across the literature; compare actual computation paths rather than mistaking input-level concatenation for shallow interaction.

Useful follow-up questions include: do visual representations occupy language sequence positions? How much information is compressed? Which parameters are frozen? Does understanding images imply the ability to generate them? These questions test architectural understanding better than memorizing model categories.

## Chapters

1. [Chapter 1: Multimodal Representations and Fusion Architectures](01-multimodal-fusion-architecture.md)

## Connections to other modules

This module covers only the architecture of integrating modalities. For training mixtures and alignment, see [Training Data and Alignment](../05-data-training-evaluation/README.md). For modality-specific capabilities, see [Vision and Document Intelligence](../02-vision-document/README.md), [Speech and Audio](../03-speech-audio/README.md), and [Multimodal Generation](../04-generation/README.md). For an overview of multimodal training, inference, evaluation, and safety, see [LLM · Multimodal Models](../../llm/06-multimodal/23-multimodal-models.md).

Return to [Multimodal Topics](../README.md).
