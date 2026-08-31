# 第七章：扩散模型、Flow Matching 与图像生成

> 本章聚焦图像生成模型背后的**生成式建模范式**（Diffusion、Flow Matching）及其在文本到图像任务中的具体应用；视频生成在时序一致性上引入的额外问题见 [第八章](08-video-generation.md)。这里讨论的是"如何从噪声生成数据"，与 [第一章](../01-foundations/01-multimodal-fusion-architecture.md)讨论的"如何把多模态输入接入语言模型做理解"是不同方向的问题。

## 7.1 生成式建模的核心问题

图像生成模型要学习的是数据分布 $p(x)$ 本身，使得可以从中采样出新的、逼真的样本，而不仅是判断"这张图像是否属于某类"。当前主流的两类范式——扩散模型（Diffusion）和 Flow Matching——都把这个问题转化为**学习一个把简单分布（如高斯噪声）逐步变换为目标数据分布的连续过程**，区别在于这个过程的数学表述和训练目标。

## 7.2 扩散模型：加噪与去噪

DDPM（Denoising Diffusion Probabilistic Models）定义了一个固定的**前向加噪过程**：从真实数据 $x_0$ 出发，经过 $T$ 步逐渐加入高斯噪声，最终得到近似纯噪声的 $x_T$：

$$
q(x_t\mid x_{t-1})=\mathcal{N}\!\left(x_t;\sqrt{1-\beta_t}\,x_{t-1},\ \beta_t I\right)
$$

其中 $\beta_t$ 是每一步的噪声调度系数。模型要学习的是**反向去噪过程**：给定 $x_t$，预测出噪声更小的 $x_{t-1}$，训练目标可以简化为让一个神经网络 $\epsilon_\theta$ 预测每一步加入的噪声：

$$
\mathcal{L}=\mathbb{E}_{x_0,\epsilon,t}\left[\lVert \epsilon-\epsilon_\theta(x_t,t)\rVert^2\right]
$$

推理时从纯噪声 $x_T$ 出发，反复调用 $\epsilon_\theta$ 逐步去噪，最终得到一张符合训练数据分布的图像。这个视角也等价于 Score-Based 生成模型：预测噪声等价于估计数据分布的对数密度梯度（score function），两条理论路线殊途同归，最终都指向同一类训练目标。

## 7.3 Latent Diffusion：把扩散过程搬到隐空间

直接在像素空间做上百步去噪计算成本极高。Latent Diffusion（Stable Diffusion 的核心架构）先用一个自编码器（VAE）把图像压缩到一个远小于像素空间的隐空间，扩散过程完全在这个隐空间里进行，只有最后一步用 VAE 解码器把去噪结果还原为像素图像。文本条件通过交叉注意力注入到去噪网络的每一层——这与 [第一章 1.3 节](../01-foundations/01-multimodal-fusion-architecture.md)描述的交叉注意力融合思路一致，只不过这里查询方是图像隐变量、被查询方是文本编码，方向与理解类模型相反。这一设计把训练和推理成本降低到可在消费级硬件运行的程度，是文本到图像生成走向大规模开源应用的关键工程突破。

## 7.4 采样加速与可控性

原始 DDPM 需要数百到上千步迭代才能生成一张图像，工程上代价过高，两类技术显著缓解了这个问题：

- **确定性采样（DDIM）**：把随机的马尔可夫链去噪过程改写为等价的确定性常微分方程（ODE）求解，允许跳过中间步骤、用远少于训练步数的采样步数生成同等质量的图像；
- **无分类器引导（Classifier-Free Guidance）**：训练时随机丢弃条件（文本）信息，让模型同时学会有条件和无条件生成，推理时按权重外推两者的预测差异，增强生成结果与文本条件的一致性，代价是引导强度过高会牺牲多样性和真实感，需要按任务调节引导系数。

## 7.5 Flow Matching：换一种数学表述，同样的目标

Flow Matching 提出了一条不同的理论路径：不再显式定义"加噪—去噪"的随机过程，而是直接学习一个**连续常微分方程的速度场**，使得沿这个速度场从噪声分布积分演化到数据分布：

$$
\frac{dx_t}{dt}=v_\theta(x_t,t)
$$

训练目标是让模型预测的速度场 $v_\theta$ 匹配一条预先指定的、连接噪声与数据的路径（如直线插值路径，即 Rectified Flow）上的真实速度。这种表述的训练目标更简单，且直线路径本身在推理时天然支持更少步数的采样，不需要额外的蒸馏或近似技巧。Stable Diffusion 3 采用了 Flow Matching 结合 Diffusion Transformer（用 Transformer 替代此前扩散模型常用的 U-Net 骨干）的组合，是这条路线从研究走向大规模生产系统的代表性节点。

Diffusion 与 Flow Matching 并非互斥的两套体系——在特定路径假设下，两者的训练目标可以相互推导，实践中的差异更多体现在噪声调度、路径设计和工程实现的选择上，而非根本不同的生成原理。

## 7.6 主流系统的架构定位

| 系统 | 骨干架构 | 关键设计 |
|---|---|---|
| Stable Diffusion（1/2 版本） | U-Net + 隐空间扩散 | 开源权重，社区生态最成熟 |
| Stable Diffusion 3 | Diffusion Transformer + Flow Matching | 用 Transformer 替代 U-Net，结合 Rectified Flow 训练 |
| DALL·E 3 | 隐空间扩散 + 强调训练数据的描述质量 | 技术报告强调用模型重新生成更详细的图像描述以提升文本遵循度 |
| Imagen | 像素空间级联扩散（基础分辨率 + 超分辨率级联） | 依赖大规模纯文本预训练语言模型作为文本编码器 |

不同系统在骨干网络、隐空间还是像素空间操作、文本编码器选择上各有取舍，但都可以归入 7.2–7.5 节描述的扩散/流匹配框架下理解，不存在脱离该框架的"全新原理"。

## 7.7 评测：自动指标与人工评估缺一不可

| 维度 | 指标 | 局限 |
|---|---|---|
| 图像质量/多样性 | FID（Fréchet Inception Distance） | 衡量生成分布与真实分布的统计距离，对局部细节缺陷不敏感 |
| 文本-图像一致性 | CLIPScore | 依赖 CLIP 的图文对齐能力，可能与人类对"是否遵循提示词"的判断不完全一致 |
| 整体偏好 | 人工两两比较（Human Preference） | 更贴近实际使用体验，但成本高、结果受评审人群影响 |

FID 和 CLIPScore 分数改善不等于人类偏好改善，两者在评测中经常出现不一致的排名，生产系统的模型选型应结合人工评估，不能只依赖单一自动指标。

## 7.8 常见错误

### 7.8.1 把"步数越多越好"当成普适规则

DDIM、Flow Matching 等技术已经能用个位数到几十步生成高质量图像，盲目增加采样步数只会增加延迟，收益在超过某个步数后迅速趋于平缓，应针对具体模型和调度器实测收益拐点。

### 7.8.2 无分类器引导系数"一律调高"

引导系数越高，生成结果越贴合文本描述，但过高会导致图像饱和度异常、细节失真、多样性下降，应结合具体任务和评测反馈调节，而非默认设为固定的最大值。

### 7.8.3 用 FID 分数直接排名不同分辨率或数据集下训练的模型

FID 对图像分辨率、参考数据集选择和特征提取网络版本敏感，跨论文、跨设置直接比较分数具有误导性，必须在相同评测协议下复现比较。

## 7.9 本章总结

1. 扩散模型和 Flow Matching 都把生成建模转化为"学习从噪声到数据的连续变换"，训练目标可以相互推导；
2. Latent Diffusion 把扩散过程搬到 VAE 压缩后的隐空间，是文本到图像生成走向大规模可用的关键工程突破；
3. DDIM 与无分类器引导分别解决采样步数和文本一致性问题，是提升生成效率与可控性的核心技术；
4. Flow Matching 用连续 ODE 速度场替代显式加噪/去噪过程，训练目标更简单、天然支持更少采样步数；
5. FID、CLIPScore 等自动指标各有局限，生产系统的模型选型应结合人工偏好评估。

> **一句话概括：图像生成的核心技术脉络是把"从噪声生成数据"表述为一个可学习的连续变换过程，Diffusion 与 Flow Matching 是这一思想的两种数学实现，采样加速和引导技术决定了它能否在实际产品中低成本落地。**

## 参考资料

- [Denoising Diffusion Probabilistic Models (DDPM)](https://arxiv.org/abs/2006.11239)
- [Denoising Diffusion Implicit Models (DDIM)](https://arxiv.org/abs/2010.02502)
- [Score-Based Generative Modeling through Stochastic Differential Equations](https://arxiv.org/abs/2011.13456)
- [High-Resolution Image Synthesis with Latent Diffusion Models (Stable Diffusion)](https://arxiv.org/abs/2112.10752)
- [Classifier-Free Diffusion Guidance](https://arxiv.org/abs/2207.12598)
- [Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747)
- [Flow Straight and Fast: Learning to Generate and Transfer Data with Rectified Flow](https://arxiv.org/abs/2209.03003)
- [Scaling Rectified Flow Transformers for High-Resolution Image Synthesis (Stable Diffusion 3)](https://arxiv.org/abs/2403.03206)
- [Photorealistic Text-to-Image Diffusion Models with Deep Language Understanding (Imagen)](https://arxiv.org/abs/2205.11487)
- [OpenAI DALL·E 3: Improving Image Generation with Better Captions](https://cdn.openai.com/papers/dall-e-3.pdf)
- [GANs Trained by a Two Time-Scale Update Rule Converge to a Local Nash Equilibrium (FID)](https://arxiv.org/abs/1706.08500)
- [CLIPScore: A Reference-free Evaluation Metric for Image Captioning](https://arxiv.org/abs/2104.08718)
