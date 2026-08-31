# 多模态 · 生成

覆盖图像与视频生成背后的扩散模型、Flow Matching 生成范式，以及视频生成在时序一致性和计算成本上引入的额外问题。

## 章节

1. [第七章：扩散模型、Flow Matching 与图像生成](07-diffusion-flow-matching-image.md)
2. [第八章：视频生成模型](08-video-generation.md)

## 模块内关系

```mermaid
flowchart LR
    D[扩散模型 / Flow Matching<br/>与图像生成] --> V[视频生成模型]
```

视频生成复用图像生成的扩散/流匹配训练目标与 Diffusion Transformer 骨干，只是把空间 patch 扩展为时空 patch；理解第七章的生成原理是理解第八章时序扩展的前提。

返回 [多模态相关知识点](../README.md)。
