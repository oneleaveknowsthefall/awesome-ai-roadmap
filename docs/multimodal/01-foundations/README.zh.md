---
description: 从连续特征拼接、交叉注意力和离散图文序列比较多模态融合，区分检索表征、生成目标与推理成本。
---

# 多模态 · 基础与架构

梳理连续特征拼接、交叉注意力读取与离散 Token 联合生成，区分统一 Embedding 空间和生成分布。Early/Late Fusion 在不同文献中定义不一，应比较实际计算路径，不能把输入层拼接误判成浅层交互。

重点追问：视觉表示是否占用语言序列位置？压缩了多少信息？冻结哪些参数？能理解图片是否意味着能生成图片？这些问题比记住模型归类更能检验架构理解。

## 章节

1. [第一章：多模态表征与融合架构](01-multimodal-fusion-architecture.md)

## 与其他模块的关系

本模块只覆盖"如何接入"的架构问题；训练数据配比与对齐见 [训练数据与对齐](../05-data-training-evaluation/README.md)，具体模态的能力细节见 [视觉与文档智能](../02-vision-document/README.md)、[语音与音频](../03-speech-audio/README.md)、[多模态生成](../04-generation/README.md)。多模态模型的整体训练/推理/评测/安全概览见 [LLM · 多模态模型](../../llm/06-multimodal/23-multimodal-models.md)。

返回 [多模态相关知识点](../README.md)。
