# 第三章：OCR 与 Document AI

> RAG 场景下"文档解析该选 OCR 管线还是页面截图检索"的工程决策见 [RAG · 文档解析 第 3.5 节](../../rag/02-ingestion-indexing/03-document-parsing.md)；本章聚焦 OCR/Document AI **模型本身**的架构演进、坐标输出方式与评测指标，两章互为补充，不重复展开对方的内容。

## 3.1 从"识别文字"到"理解文档结构"

传统 OCR 分两步：**文字检测**（在图像中定位文字区域，输出框）和**文字识别**（把框内像素转成字符串）。这对扫描页面已经足够，但真实文档（发票、合同、表单、财报）的价值往往不在"文字本身"，而在文字之间的**结构关系**：哪一行是标题、哪一列是金额、哪个字段对应哪个标签。这类任务统称 Document AI 或文档智能，输出目标从"一串文字"变成"结构化的键值对、表格或版面树"。

## 3.2 版面感知模型：LayoutLM 系列

LayoutLM 系列的核心思路是让模型同时看到**文字内容、二维坐标和视觉特征**三种信号，而不仅是文字序列本身。LayoutLM 在 BERT 式预训练里加入了 2D 位置嵌入，把每个文字 token 的边界框坐标当作额外输入；LayoutLMv3 进一步统一了文字和图像 patch 的处理方式，用同一个 Transformer 同时接收文字 token 和图像 patch，并设计了跨模态对齐的预训练目标（如判断某个文字 token 对应的图像 patch 是否被遮盖）。

这类模型解决的关键问题是**阅读顺序**：扫描件或复杂排版下，文字的物理阅读顺序（从左到右、从上到下、多栏交错）和 OCR 引擎输出顺序经常不一致，纯文本模型难以还原真实语义结构，而版面感知模型把坐标作为一等公民输入，能显著改善多栏、表单类文档的结构还原。

## 3.3 OCR-free 端到端文档理解

上述路线仍然依赖一个独立的 OCR 引擎先产出文字和坐标，误差会逐级传递（OCR 错一个字，下游结构化提取也跟着错）。Donut（Document Understanding Transformer）提出完全跳过显式 OCR 步骤：用一个视觉编码器直接处理文档图像，解码器直接生成目标结构化输出（如 JSON），整个过程不产生中间的 OCR 文字层，训练时用合成文档图像配合目标结构做端到端监督。

OCR-free 路线的收益是避免了 OCR 错误的级联传播，且不需要为每种版式单独设计规则；代价是可解释性降低——模型内部"看到了什么文字"不再有显式的中间表示可供审计，出错时更难定位是感知问题还是结构推理问题。

## 3.4 表格与图表：结构比文字更重要

表格和图表是文档智能里最容易被低估难度的子任务，因为正确率不能只看"文字有没有认对"，还要看**结构有没有还原**。

- **表格结构识别（Table Structure Recognition）**：目标是还原行、列、跨行跨列单元格的拓扑关系，而不只是识别单元格内文字。Table Transformer（TATR）把表格结构识别建模为目标检测问题，用 DETR 架构分别检测表格整体区域、行、列和跨单元格结构；PubTables-1M 是配套发布的大规模标注数据集。评测常用 **TEDS（Tree-Edit-Distance-based Similarity）**，把表格表示为树结构后计算编辑距离相似度，而不是简单的逐单元格文字匹配。
- **图表理解（Chart Understanding）**：图表（柱状图、折线图）的"文字"往往只是坐标轴标签和图例，真正的信息藏在视觉编码（柱高、线的斜率、颜色分组）里。ChartQA 一类基准要求模型结合视觉编码和图上文字共同回答数值型问题（"哪一年增长最快"），这类任务的失败模式和纯 OCR 任务完全不同：模型可能正确识别了所有坐标轴文字，但读错了柱子的相对高度。

## 3.5 坐标输出与版面框的表示

无论是版面分析、表格还是通用 VQA 场景下的定位，Document AI 模型的坐标输出方式与 [第二章](02-vlm-grounding.md) 描述的两条路径（坐标文本化 / 检测头）完全一致：一部分模型把版面框编码为文本 token 直接生成，另一部分保留独立检测头输出结构化坐标。区别在于 Document AI 场景的框往往带有层级关系（页 → 段落 → 行 → 词），需要额外的层级结构表示，而不仅是独立的边界框列表。

## 3.6 工程化服务：不是所有场景都要自建模型

生产环境中，通用文档抽取需求（发票、身份证件、合同关键字段）通常优先使用云厂商的 Document AI 服务而非自建模型，因为这类服务已经针对常见证件和票据格式做了大量场景化优化，并提供版本化的准确率保证：

| 服务 | 定位 |
|---|---|
| Azure AI Document Intelligence | 提供预置模型（发票、收据、身份证件）与可训练的自定义抽取模型 |
| Google Document AI | 提供表单解析器、发票解析器等专用处理器（Processor） |
| Amazon Textract | 提供文字检测、表单键值对提取、表格提取的独立 API |

选择自建模型还是云服务，取决于文档类型是否属于通用票据/证件（更适合云服务）还是高度定制化的内部表单（更可能需要微调专用模型），以及数据合规是否允许调用外部 API。

## 3.7 评测：分层次衡量，不要只看一个总分

| 层次 | 指标 | 说明 |
|---|---|---|
| 字符/词识别 | CER（字符错误率）、WER（词错误率） | 衡量纯文字识别准确度，不涉及结构 |
| 版面结构 | 阅读顺序准确率、区域分类 F1 | 衡量段落、标题、页眉页脚等区域划分是否正确 |
| 表格结构 | TEDS | 衡量行列拓扑与跨单元格结构的还原程度 |
| 键值抽取 | 字段级 Precision/Recall/F1 | 衡量"发票金额""开票日期"等字段是否抽对且抽全 |
| 端到端文档问答 | DocVQA 一类基准的 ANLS | 衡量结合版面、文字、视觉的综合问答能力 |

CER/WER 低不代表下游任务可用：一个字符准确率 99% 的 OCR 结果，如果恰好错在金额的一位数字上，对财务场景是灾难性错误。字段级指标必须单独评测，不能用整体识别率替代。

## 3.8 常见错误

### 3.8.1 用整体 OCR 准确率代表文档理解能力

字符识别准确率高不代表版面结构、表格拓扑或关键字段抽取正确，必须按 3.7 节分层评测。

### 3.8.2 把表格"拍平"成纯文本再抽取

将表格逐行转成一段连续文本会丢失跨行跨列关系；涉及数值比较、条件过滤的问题应保留结构化表示（见 [RAG · 多模态 RAG 第 21.3 节](../../rag/04-advanced/21-multimodal-rag.md)对表格证据的处理原则）。

### 3.8.3 忽视扫描质量、旋转和多语言对识别率的影响

生产文档常见倾斜、低分辨率扫描、印章遮挡和多语言混排，基准测试集的高分不能直接迁移到这些场景，上线前应用真实分布的样本单独核验。

## 3.9 本章总结

1. Document AI 的目标是结构化理解而非单纯文字识别，版面、表格、键值关系是评测和架构设计的核心对象；
2. LayoutLM 系列通过融合文字、坐标与视觉特征解决阅读顺序和版面结构问题；
3. Donut 一类 OCR-free 模型端到端生成结构化输出，避免了独立 OCR 阶段的错误级联，但降低了可解释性；
4. 表格结构识别（TATR/TEDS）和图表理解（ChartQA）的失败模式与纯文字识别不同，需要专门评测；
5. 生产场景应先评估是否可用云厂商预置 Document AI 服务，再决定是否自建/微调模型。

> Document AI 往往输在结构还原：字认对了，不代表阅读顺序、表格拓扑和字段关系也对了。

## 参考资料

- [LayoutLM: Pre-training of Text and Layout for Document Image Understanding](https://arxiv.org/abs/1912.13318)
- [LayoutLMv3: Pre-training for Document AI with Unified Text and Image Masking](https://arxiv.org/abs/2204.08387)
- [OCR-free Document Understanding Transformer (Donut)](https://arxiv.org/abs/2111.15664)
- [PubTables-1M: Towards Comprehensive Table Extraction From Unstructured Documents](https://arxiv.org/abs/2110.00061)
- [Image-based table recognition: data, model, and evaluation (PubTabNet / TEDS)](https://arxiv.org/abs/1911.10683)
- [ChartQA: A Benchmark for Question Answering about Charts](https://arxiv.org/abs/2203.10244)
- [DocVQA: A Dataset for VQA on Document Images](https://arxiv.org/abs/2007.00398)
- [Azure AI Document Intelligence 官方文档](https://learn.microsoft.com/azure/ai-services/document-intelligence/overview)
- [Google Cloud Document AI 官方文档](https://cloud.google.com/document-ai/docs/overview)
- [Amazon Textract 官方文档](https://docs.aws.amazon.com/textract/latest/dg/what-is.html)
