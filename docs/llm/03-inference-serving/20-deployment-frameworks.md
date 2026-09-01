# 第二十章：部署框架选型

## 20.1 部署框架到底解决什么问题

先看「直接用 transformers 的 `model.generate()`」会有什么问题——能跑起来，但效率很糟糕。

### 20.1.1 三大痛点

| 痛点 | 表现 |
|---|---|
| **① KV Cache 显存碎片严重** | 朴素实现可能为请求预留接近最大长度的连续空间，而实际长度短得多，导致可用并发下降 |
| **② 批量推理调度低效** | Static batching 是「凑齐 N 个请求一起跑、一起结束」。但生成长度差异大（有的 50 token 有的 1000 token），**短请求等长请求，GPU 大量时间跑了一半在等** |
| **③ 重复计算** | 所有用户共用同一段 1000 token 的 System Prompt，**每次都要重新算它的 KV Cache** |

**因此常见优化方向是**：内存高效（缓解碎片）+ 批量调度（提高利用率）+ 缓存复用（避免重复计算）。各框架的覆盖与实现随版本变化。

## 20.2 vLLM：PagedAttention + Continuous Batching

### 20.2.1 PagedAttention 的灵感来自操作系统虚拟内存

**操作系统怎么管内存**？不是给每个进程预分配大块连续物理内存（那会有大量碎片），而是把物理内存切成固定大小的「页」，进程拿到「逻辑地址」，通过页表映射到真实物理页。

**PagedAttention 把这个思路搬到 KV Cache 上**：

```mermaid
flowchart LR
    subgraph L["请求的逻辑 KV 序列"]
        A1["块 0"] --> A2["块 1"] --> A3["块 2"]
    end
    L --> BT["Block Table<br/>逻辑 → 物理映射"]
    BT --> P["物理显存<br/>固定大小 Block（典型 16 token）<br/>用完即释放，可任意分布"]

    style BT fill:#e8f0fe
```

一个请求实际用了 200 token 就只占 13 个 Block（$200/16$），避免了为该请求保留整段 4096-token 连续空间的常见浪费。

> 实际收益取决于请求长度分布、block 大小、模型、并发限制和 KV-cache 预算；应使用生产形态的 trace 压测，而非套用固定百分比。

### 20.2.2 第二个杀手锏：Continuous Batching

**Static batching**：凑齐 N 个请求一起跑、跑完一起结束。

**Continuous Batching**：请求**异步加入和退出**，每个 token 步骤动态组 batch。

```
t1: 请求 A、B、C 同时在跑
t5: A 生成完退出 → 新请求 D 立刻加入
t8: B 生成完退出 → 新请求 E 加入
```

它可减少由长度不均造成的空槽时间；吞吐增益取决于到达率、输出长度和调度策略。

> **vLLM = PagedAttention（显存高效）+ Continuous Batching（吞吐高效）**，是当前生产环境部署 LLM API 的常见默认选择。

## 20.3 SGLang：RadixAttention 攻共享前缀

SGLang 更适合前缀复用率高的场景，尤其是**多请求共享前缀**。

### 20.3.1 哪些场景前缀重复率高

- **System Prompt 共享**：所有用户调同一个 API，System Prompt 完全一样；
- **Few-shot 示例共享**：Prompt 里有 5–10 个固定示例；
- **多轮对话历史**：每轮都包含前 N 轮的完整历史；
- **Agent 工作流**：Agent 多次调用 LLM，每次上下文都从同一个 System Prompt 开始。

vLLM 不只有 PagedAttention，也提供 **Automatic Prefix Caching（APC）**，可复用相同 token 前缀的 KV block。是否开启、命中和收益依版本、配置及缓存压力而定；不能把「跨请求前缀复用」说成 SGLang 独有。

### 20.3.2 RadixAttention：用基数树组织 KV Cache

```mermaid
flowchart TB
    ROOT["根节点（空）"] --> SP["共享的 System Prompt<br/>1000 token —— 只存一份"]
    SP --> U1["用户 A 的问题"]
    SP --> U2["用户 B 的问题"]
    SP --> U3["用户 C 的问题"]

    style SP fill:#e6f4ea
```

**多个请求开头 N 个 token 一样，就共享根节点到第 N 层的同一条路径**，第 N+1 层才分叉。

> 前缀树可让共享部分只保留一份；实际节省由前缀重合、驱逐策略和并发共同决定。

### 20.3.3 更妙的一点：自动复用历史请求

若相同前缀的 KV block 尚未被逐出，后来的请求可复用它们；缓存驻留时长和首 token 延迟收益都由部署配置与负载决定。

SGLang 的 RadixAttention 对高前缀复用工作负载尤其值得评估；vLLM APC、SGLang 与其他运行时都应在同一模型、硬件、并发和 trace 下比较。

> **但要注意：纯单请求、无前缀共享的场景下，SGLang 相对 vLLM 优势不明显。两者是互补关系，不是替代关系。**

## 20.4 TGI：处于维护模式的 HuggingFace 服务方案

Hugging Face 已声明 TGI 进入**维护模式**：接受小型修复、文档和轻量维护工作，并推荐新部署评估 vLLM、SGLang 或本地兼容运行时。现有 TGI 用户仍应按自身版本的支持矩阵维护部署。

| 维度 | 说明 |
|---|---|
| **生态集成** | 直接读 HF Hub 模型 ID 自动下载部署，不用手动转格式；支持 safetensors / quantization 配置；兼容 HF tokenizer 和 chat template |
| **企业级特性** | HTTP / gRPC 双协议、鉴权（API Key / JWT）、Prometheus metrics、健康检查、优雅重启、SSE 流式响应 |
| **能力** | 提供连续批处理、量化和 SSE 流式输出；新项目需将维护状态和目标模型支持纳入选型 |

**适合**：公司本来就用 HuggingFace 全套；需要快速 POC 不想折腾推理框架；模型在 HF Hub 上有现成的；需要企业级可观测性。

## 20.5 llama.cpp：CPU / 边缘设备的常用方案

**核心思路与服务端 GPU 运行时不同**：用 C/C++ 实现轻量推理栈，面向 CPU、Apple Silicon 与边缘场景。

**为什么这么做**——绝大多数个人设备没有独立 GPU：Mac（统一内存架构）、集显笔记本、树莓派 / Jetson、手机。

### 20.5.1 三个关键技术

**① GGUF 文件格式**

把模型权重 + 量化方案 + 元数据打包到一个文件。常见量化档位：

| 档位 | 说明 |
|---|---|
| Q8_0 | 8-bit，通常比更低比特格式保留更多质量 |
| Q5_K_M | 5-bit，精度和体积平衡 |
| **Q4_K_M** | 4-bit，常见的体积与质量折中 |
| Q3_K_S | 3-bit，极端压缩，精度有损 |

> **再强调一次：GGUF 是文件格式不是量化算法**（见 [第十五章](15-quantization.md)）。

**② SIMD 优化**

针对 AVX2、AVX512、ARM NEON 等指令集提供优化 kernel。CPU 与 GPU 的速度比较高度依赖模型、量化、内存带宽和批量大小，不应使用固定比例。

**③ Metal 后端（Apple Silicon）**

**苹果 M 系列的统一内存架构特别适合它**——大内存的 M 系列机器能跑 70B 模型，速度可观。这让 llama.cpp 在 Mac 用户中极其流行。

### 20.5.2 适用边界

| 适合 | 不适合 |
|---|---|
| 个人本地玩模型 | **高并发生产 API**（CPU 吞吐上不去） |
| Mac 用户充分利用 M 系列芯片 | **需要 batch 处理**（批量支持较弱） |
| 边缘 / 嵌入式部署 | **多卡 GPU 集群**（不是设计目标） |
| 离线场景、隐私敏感场景（数据不出设备） | |

## 20.6 TensorRT-LLM：NVIDIA 官方极致优化

**定位很特殊：针对 NVIDIA GPU 做极致优化，不考虑跨平台。**

| 特点 | 代价 |
|---|---|
| 对每个具体 GPU 型号做硬件级调优 | **工程门槛高**，需要先编译 engine |
| 集成 NVIDIA 自家内核库 | **只支持 NVIDIA GPU** |
| 支持 FP8、INT4 等所有硬件支持的精度 | 文档生态不如开源框架活跃 |
| 性能需针对具体 GPU、模型、编译配置和服务负载进行基准测试 | |

**适合**：有 NVIDIA 大集群的大厂、追求极致 GPU 利用率、愿意承担额外工程复杂度。

## 20.7 选型决策矩阵

| 框架 | 核心创新 | 最佳场景 | 性能 | 生态 |
|---|---|---|---|---|
| **vLLM** | PagedAttention、Continuous Batching、APC | 高吞吐 LLM API 与重复前缀工作负载 | 需实测 | 开源活跃 |
| **SGLang** | RadixAttention（共享前缀） | Agent / 多轮 / Few-shot | 高前缀复用时值得评估 | 快速演进 |
| **TGI** | HF 服务生态 | 既有 TGI 部署 | 已进入维护模式 | HF 生态 |
| **llama.cpp** | C/C++ 推理 + GGUF | CPU / Mac / 边缘 | 需按设备实测 | 个人 / 边缘 |
| **TensorRT-LLM** | NVIDIA 运行时优化 | NVIDIA 集群 | 需按 engine 与负载实测 | NVIDIA 官方开源 |

### 20.7.1 四个常见误用

| 误用 | 后果 | 正确做法 |
|---|---|---|
| **认为 vLLM 没有前缀复用** | 忽略 APC，导致错误的架构判断 | 查目标版本 APC 配置，并用真实 trace 比较 vLLM 与 SGLang |
| **用 llama.cpp 做高并发服务** | 批量调度弱，并发上去后吞吐瓶颈 | 生产 API 用 GPU + vLLM |
| **用 TGI 追求绝对性能** | 瓶颈是 GPU 吞吐时它通常不是第一选择 | 优先评估 vLLM / SGLang / TensorRT-LLM。**具体差距随模型、硬件、量化和 batch 策略变化，别死记固定百分比** |
| **用 TensorRT-LLM 做快速 POC** | 每个模型 / GPU 组合都要编译 engine | 模型经常换的场景不适合 |

## 20.8 三大隐藏陷阱

### 20.8.1 显存碎片在长上下文场景还是会出现

PagedAttention **可大幅缓解但不能保证消除**碎片。当请求长度极不均匀时，仍会有尾块、调度和预留空间等开销。

**应对**：监控 GPU 显存、KV-cache 命中率和排队延迟，再结合 trace 调整 `max-model-len`、并发与交换策略。

### 20.8.2 KV Cache 量化的支持差异大

权重量化很多框架都支持，**但 KV Cache 量化的支持差异很大，而且版本迭代很快**。

> **如果你的瓶颈是长上下文 KV Cache 显存，选型前一定要查当前版本文档，别只听别人说「支持」。**

### 20.8.3 MoE 模型的部署支持差异

MoE 部署比 Dense 复杂得多（需要专家并行、All-to-All 通信优化，见 [第十九章](19-moe.md)）：

- vLLM 和 SGLang 都支持但配置复杂；
- llama.cpp 通过 GGUF 支持但性能一般；
- TensorRT-LLM 支持最好但工程门槛高。

**要部署 MoE 建议先在测试环境跑通再上生产。**

## 20.9 常见错误

### 20.9.1 只会背框架名字，说不出它们解决什么问题

**先讲三大痛点**（显存碎片、批量调度低效、共享前缀重复计算），再讲每个框架攻击哪个维度。

### 20.9.2 说不清 PagedAttention 的灵感来源

**操作系统虚拟内存的分页机制**——Block Table 就是页表。

### 20.9.3 把 SGLang 说成 vLLM 的替代品

**无前缀共享的单请求场景下优势不明显，两者是互补关系。**

### 20.9.4 在 Agent 场景无脑用 vLLM

Agent 前缀重复率极高，SGLang 的 RadixAttention 正是为此而生。

### 20.9.5 用 llama.cpp 做高并发生产服务

批量调度弱，是本地和边缘部署的工具。

### 20.9.6 认为 PagedAttention 彻底消除了显存碎片

长度极不均匀时仍会有尾块、调度和预留空间等开销。

### 20.9.7 假设所有框架的 KV Cache 量化支持一致

差异很大且版本迭代快，必须查当前版本文档。

### 20.9.8 用固定百分比描述框架间的性能差距

差距随模型、硬件、量化方式和 batch 策略变化。

## 20.10 本章总结

1. **部署框架解决三大痛点**：KV Cache 显存碎片、批量调度低效、共享前缀重复计算；
2. **vLLM 的 PagedAttention 借鉴操作系统虚拟内存**，Block Table 映射逻辑到物理；APC 可自动复用匹配前缀的 KV block；
3. **Continuous Batching 让请求异步进出**，可改善长度不均工作负载的利用率；
4. **SGLang 的 RadixAttention 用基数树共享前缀**，高前缀复用时可减少缓存和 prefill 重算；
5. **vLLM APC 与 SGLang 都应按实际 trace 评估**，不存在脱离版本与负载的固定胜负；
6. **TGI 已进入维护模式**；新项目需优先检查目标模型与运行时的当前支持；
7. **llama.cpp 纯 C++ 实现 + GGUF**，是 CPU / Mac / 边缘的常用方案；高并发和多卡能力应按目标版本实测；
8. **TensorRT-LLM 针对 NVIDIA 硬件深度优化**，代价是 engine 构建与平台绑定；是否领先取决于模型、硬件、精度与请求负载；
9. **三大隐藏陷阱**：长上下文仍有碎片与调度开销、KV Cache 量化支持差异大、MoE 部署复杂度通常高于 Dense。


## 参考资料

- [Efficient Memory Management for Large Language Model Serving with PagedAttention（vLLM）](https://arxiv.org/abs/2309.06180)
- [SGLang: Efficient Execution of Structured Language Model Programs（RadixAttention）](https://arxiv.org/abs/2312.07104)
- [Orca: A Distributed Serving System for Transformer-Based Generative Models（Continuous Batching）](https://www.usenix.org/conference/osdi22/presentation/yu)
- [vLLM 文档](https://docs.vllm.ai/)
- [vLLM: Automatic Prefix Caching](https://docs.vllm.ai/en/stable/features/automatic_prefix_caching/)
- [SGLang 仓库](https://github.com/sgl-project/sglang)
- [Text Generation Inference 仓库](https://github.com/huggingface/text-generation-inference)
- [TGI 官方文档（维护模式说明）](https://huggingface.co/docs/text-generation-inference/main/en/index)
- [llama.cpp 仓库](https://github.com/ggml-org/llama.cpp)
- [TensorRT-LLM 仓库](https://github.com/NVIDIA/TensorRT-LLM)
