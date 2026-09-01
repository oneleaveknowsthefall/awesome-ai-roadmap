# 第二章：视觉语言模型与视觉 Grounding

> 本章的“Grounding”特指**视觉定位**：把语言指代（“左上角的红色按钮”）映射到图像中的具体坐标或区域。这与 RAG 领域"Grounding = 答案落回可验证证据"是同一个词的不同含义，后者见 [RAG · 多模态 RAG 第 21.5 节](../../rag/04-advanced/21-multimodal-rag.md)。多模态模型的通用架构与训练流程见 [第一章](../01-foundations/01-multimodal-fusion-architecture.md)与 [LLM · 多模态模型](../../llm/06-multimodal/23-multimodal-models.md)，本章只展开视觉理解与定位这条能力线。

## 2.1 VLM 的能力谱系

视觉语言模型（Vision-Language Model, VLM）对外呈现为"看图回答问题"，但内部能力可以拆成一条由粗到细的谱系：

| 能力 | 输出形式 | 代表任务 |
|---|---|---|
| 图像描述（Captioning） | 自然语言 | 生成一句话描述整张图 |
| 视觉问答（VQA） | 自然语言 | 回答关于图像内容的开放式问题 |
| 指代表达理解（Referring Expression Comprehension） | 坐标/区域 | 给定"图中戴帽子的人"，定位对应区域 |
| 开放词表检测（Open-Vocabulary Detection） | 多组坐标 + 类别 | 不局限于固定类别表，检测任意文本描述的物体 |
| 像素级定位（Grounded Segmentation） | 分割掩码 | 定位到像素而非矩形框 |

越靠表格下方，模型需要输出的不再是自由文本，而是**可被程序消费的结构化坐标**，这正是 Grounding 与普通 VQA 的分界线：VQA 只要求答案在语义上正确，Grounding 额外要求答案在空间上可验证。

## 2.2 坐标怎么被语言模型"说"出来

自回归语言模型本身只会生成 token 序列，要让它输出边界框，通常有两条路径：

1. **坐标文本化**：把边界框 $(x_1,y_1,x_2,y_2)$ 归一化到 $[0,1000)$ 或 $[0,1)$ 区间后，转成一段文本（如 `<box>(102,304),(560,812)</box>`），模型像生成普通文本一样"写出"坐标。Qwen-VL 和 PaliGemma 都采用了这一思路，坐标 token 与普通文本 token 共享同一个词表和生成过程。
2. **检测头 + 语言解耦**：视觉分支保留传统目标检测的回归/分类头，语言模型只负责决定"要找什么"（文本查询），检测头负责"在哪里"。Grounding DINO 是这一路线的代表：把 DETR 式检测器与语言编码器结合，语言特征引导检测器的候选框筛选与分类。

坐标文本化的好处是复用了语言模型现成的生成能力和上下文推理能力（可以在一次对话里既描述又定位）；检测头路线的好处是保留了成熟检测架构的精度和效率，但语言与视觉分支的耦合更弱，通常难以做复杂的多轮指代消解。

归一化坐标的评测标准是 **IoU（Intersection over Union）**：

$$
\mathrm{IoU}(B_{\mathrm{pred}},B_{\mathrm{gt}})=\frac{\lvert B_{\mathrm{pred}}\cap B_{\mathrm{gt}}\rvert}{\lvert B_{\mathrm{pred}}\cup B_{\mathrm{gt}}\rvert}
$$

RefCOCO 系列基准通常以 $\mathrm{IoU}>0.5$ 作为判定"定位正确"的阈值，但阈值本身会随任务对精度的要求而调整（例如 GUI 点击场景常直接用"点是否落在目标元素内"而非 IoU，见 [第四章](04-computer-use.md)）。

## 2.3 开放词表检测：跳出固定类别表

传统目标检测模型（如 Faster R-CNN、YOLO 系列）只能识别训练时见过的固定类别集合。GLIP 把检测重新表述为一个"图像区域—文本短语"匹配问题：将类别名称拼接成一句话提示（prompt），用对比学习让区域特征与对应短语的文本特征对齐，检测器就能识别提示词中出现的任意名词短语，而不局限于预定义类别表。OWL-ViT 走了另一条更"轻量"的路线：直接复用 CLIP 式的图文对比预训练权重，在其基础上添加检测头做微调，同样具备开放词表能力。

开放词表检测与前一节的"坐标文本化"路线可以结合：先用开放词表检测器产出候选区域，再交给语言模型做筛选、排序或多轮追问，兼顾检测精度和语言推理的灵活性。

## 2.4 训练数据：指代表达与像素级标注

Grounding 能力高度依赖专门标注的数据集，通用图文对（如网页爬取的 alt-text）几乎不包含精确坐标：

- **RefCOCO / RefCOCO+ / RefCOCOg**：在 COCO 图像上标注"指代表达—目标框"配对，三者的区别在于指代表达是否包含绝对位置词（如"左边的"）以及表达长度；
- **Visual Genome**：为图像中的每个区域标注短语描述和关系三元组，是训练区域级描述和关系定位的常用数据源；
- **像素级标注**：分割式 Grounding 需要掩码级标注，通常成本远高于框级标注，一部分工作采用检测框加分割模型（如 SAM）自动生成掩码再人工核验的半自动流程降低成本。

## 2.5 评测：不能只看整体 VQA 分数

Grounding 能力需要独立评测，原因是它和普通 VQA 分数经常不同步：一个模型可能"知道图里有什么"但"说不准在哪里"。常见评测维度：

| 维度 | 指标 | 说明 |
|---|---|---|
| 单目标定位 | RefCOCO/+/g 的 Acc@IoU>0.5 | 单个指代表达对应单个目标框 |
| 多目标/计数 | 检测式 mAP | 需要同时找全所有满足条件的目标 |
| 细粒度/小目标 | 分辨率敏感的定位准确率 | 高分辨率切图或动态分辨率策略下的表现差异 |
| 幻觉定位 | 目标不存在时是否正确拒绝 | 防止模型在图中不存在目标时仍"编造"一个框 |

“幻觉定位”尤其容易被忽视：评测集如果只包含目标确实存在的样本，无法区分"模型真的定位准确"还是"模型倾向于给任何提示都返回一个框"。

## 2.6 常见错误

### 2.6.1 把 VQA 能力等同于 Grounding 能力

模型能正确回答"图里有几只猫"不代表它能准确框出每一只猫的位置。两者依赖的表示粒度不同，必须分别评测，见 2.5 节。

### 2.6.2 固定阈值直接跨任务比较 IoU

$\mathrm{IoU}>0.5$ 是 RefCOCO 类基准的常见约定，不是普适标准。小目标、密集场景或需要像素级精度的任务（如医学影像、GUI 元素点击）应使用该任务自己的容错标准，而不是套用同一个阈值下结论。

### 2.6.3 忽视坐标系统与分辨率归一化的差异

不同模型对坐标的归一化方式（$[0,1)$、$[0,1000)$、绝对像素）和参考分辨率不一致，直接比较原始输出坐标而不做归一化换算会得到错误结论；集成多个 Grounding 模型时必须先统一坐标系统。

## 2.7 本章总结

1. VLM 能力谱系从图像描述、VQA 到指代表达理解、开放词表检测、像素级定位，粒度依次变细；
2. 坐标输出主要有"坐标文本化"（复用语言生成能力）与"检测头 + 语言解耦"（复用检测架构精度）两条路径；
3. 开放词表检测（GLIP、OWL-ViT）通过图文对齐让检测跳出固定类别表；
4. Grounding 训练依赖 RefCOCO、Visual Genome 等专门标注的坐标/区域数据，通用图文对无法替代；
5. 评测必须独立于整体 VQA 分数，并纳入幻觉定位（目标不存在时的拒绝能力）。

> 做视觉 Grounding 时，真正要补的是坐标表示、专门标注数据和独立定位评测；VQA 高分并不能替代这些能力。

## 参考资料

- [Grounding DINO: Marrying DINO with Grounded Pre-Training for Open-Set Object Detection](https://arxiv.org/abs/2303.05499)
- [Grounded Language-Image Pre-training (GLIP)](https://arxiv.org/abs/2112.03857)
- [Simple Open-Vocabulary Object Detection with Vision Transformers (OWL-ViT)](https://arxiv.org/abs/2205.06230)
- [PaliGemma: A versatile 3B VLM for transfer](https://arxiv.org/abs/2407.07726)
- [Qwen-VL: A Versatile Vision-Language Model](https://arxiv.org/abs/2308.12966)
- [Molmo and PixMo: Open Weights and Open Data for State-of-the-Art Multimodal Models](https://arxiv.org/abs/2409.17146)
- [Visual Genome: Connecting Language and Vision Using Crowdsourced Dense Image Annotations](https://arxiv.org/abs/1602.07332)
- [Generation and Comprehension of Unambiguous Object Descriptions (RefCOCO)](https://arxiv.org/abs/1511.02283)
