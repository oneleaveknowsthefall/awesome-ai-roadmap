# 多模态 · 基础与架构

梳理多模态模型在架构层面如何把图像、音频等信号接入语言模型：融合发生的位置（Late Fusion / Cross-Attention / Early Fusion）、统一 Token 化与统一 Embedding 空间的区别。这是本主题其余模块的公共基础。

## 章节

1. [第一章：多模态表征与融合架构](01-multimodal-fusion-architecture.md)

## 与其他模块的关系

本模块只覆盖"如何接入"的架构问题；训练数据配比与对齐见 [训练数据与对齐](../05-data-training-evaluation/README.md)，具体模态的能力细节见 [视觉与文档智能](../02-vision-document/README.md)、[语音与音频](../03-speech-audio/README.md)、[多模态生成](../04-generation/README.md)。多模态模型的整体训练/推理/评测/安全概览见 [LLM · 多模态模型](../../llm/06-multimodal/23-multimodal-models.md)。

返回 [多模态相关知识点](../README.md)。
