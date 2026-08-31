# 第十一章：LangChain 的版本演进

## 11.1 为什么要不断调整架构

**LangChain 早期把模型、向量库、工具、Retriever 和大量预制 Chain 都放在相近的包结构中**，快速验证想法很方便。

**但问题是层层叠加的**：

```mermaid
flowchart TB
    A["第一层：依赖<br/>第三方 SDK 的一次更新<br/>就可能牵动整个依赖树"]
    B["第二层：API 不统一<br/>不同 Chain 的调用和组合方式不一致<br/>开发者要记住越来越多专用 API"]
    C["第三层：执行不可控<br/>复杂 Agent 的执行循环藏在执行器内部<br/>很难插入分支、审批和恢复逻辑"]
    A --> B --> C
    C --> D["功能越加越多<br/>核心职责反而越来越模糊"]

    style D fill:#fff3cd
```

> **大版本演进的重点并不是单纯增加功能，而是重新划分边界**：哪些协议需要保持稳定，哪些集成应该独立更新，哪些流程应该由更底层的运行时管理。

## 11.2 节点一：核心与集成拆开

**模型厂商、向量数据库和外部工具的 SDK 变化很快，而消息、Runnable、Tool 等核心协议应该尽量稳定。**

> **把它们放在同一个包中，会让两种不同的迭代节奏互相影响。**

| 包 | 核心职责 |
|---|---|
| `langchain-core` | 消息、模型、Tool、Runnable 等**基础协议** |
| `langchain` | 面向应用开发的**高层 Agent 能力** |
| `langchain-community` | 大量**社区维护**的第三方集成 |
| `langchain-openai` 等独立包 | **跟随特定厂商 SDK 独立迭代** |

**拆分后的收益**：项目只安装真正需要的集成，也降低了某个模型 SDK 升级对整个框架的影响。

> **不需要背出所有包名，重点是「稳定内核，释放边缘」这一架构思想。**

## 11.3 节点二：Runnable 统一协议

**早期为不同流程提供了大量 Chain 类，调用方式和扩展方式并不完全一致。**

```python
# Prompt、Model 和 Parser 统一遵循 Runnable 协议
chain = prompt | model | output_parser

# 组合后的整体仍然使用统一的 invoke 接口
result = chain.invoke({"question": "什么是 Agent？"})
```

> **这段代码的重要之处不是管道符**，而是**组合后的整体仍然遵循 Runnable 协议**，因此可以使用统一的同步、异步、批处理、流式和追踪接口。

**它代表 LangChain 从「大量预制类」转向「少量标准协议 + 组合」**（详见 [第二章](02-chain-and-lcel.md)）。

> **对于步骤固定的确定性流程，Runnable 和 LCEL 往往比 Agent 更容易测试和控制。**

## 11.4 节点三：转向 LangGraph

**传统 Agent 执行器通常在内部运行「模型判断、调用工具、再次判断」的循环。**

**简单 Agent 使用方便，但一旦加入规划、反思、并行分支、人工审批或故障恢复，隐藏的循环就会变得难以修改。**

### 11.4.1 解决思路：把隐藏循环摊开

| 概念 | 承担 |
|---|---|
| **State** | 保存消息和业务进度 |
| **Node** | 执行模型、工具或**普通业务逻辑** |
| **Edge** | 决定结果接下来流向哪里 |

> **循环和分支不再隐藏在执行器内部**，检查点还能保存运行状态，为暂停恢复、人工介入和长时间执行提供基础（详见 [第十章](10-langgraph-advantages.md)）。

**LangGraph 并不是把 LangChain 完全替换掉**：LangChain 提供模型、Tool、middleware 和 `create_agent` 等高层开发体验，LangGraph 提供底层状态与执行能力。

## 11.5 节点四：v1 重新聚焦 Agent

**从开发者最常接触的入口看起**：

```mermaid
flowchart TB
    A["① 高层入口收敛到 create_agent<br/>提供模型、工具和系统提示词<br/>底层由 LangGraph 运行 Agent loop<br/>因此仍能使用持久化、流式输出和人工介入"]
    A --> B["② middleware 成为主要扩展方式<br/>动态提示词、模型选择、工具筛选<br/>对话摘要、重试、人工审批<br/>插入关键执行阶段而不是复制整套 loop"]
    B --> C["③ 主命名空间顺势精简<br/>旧 Chain、Retriever、Indexing、Hub<br/>主要迁到 langchain-classic"]

    style A fill:#e8f0fe
    style C fill:#e6f4ea
```

> **易用性留在 LangChain，复杂执行能力则由 LangGraph 承接。**

**为什么需要 middleware 这一层**：如果每增加一项能力都重写循环，**高层入口很快又会失去意义**。

### 11.5.1 一个关键澄清

> **不能把 v1 简单理解成「旧 API 全部删除」。**
>
> **更准确的说法是**：新项目使用聚焦后的 Agent API，旧项目通过 `langchain-classic` 保持运行，再根据需要逐步迁移。

## 11.6 Pydantic 2 值得重点背吗

**Python 版本 v0.3 将内部数据模型迁移到 Pydantic 2，并停止使用 Pydantic 1 兼容层。**

**这属于重要的迁移背景**，因为工具 Schema、结构化输出和配置对象都依赖 Pydantic。

> **但面试时不需要展开 Pydantic 的全部版本差异。** 说明它统一了数据模型与校验基线、旧项目升级时需要检查导入路径和模型定义即可。
>
> **相比之下，拆包、Runnable、LangGraph 和 v1 Agent 架构更能体现长期演进方向。**

## 11.7 升级时要注意什么

**跨大版本升级不能只执行一次依赖更新。**

```mermaid
flowchart TB
    S1["① 动手前<br/>锁定当前依赖和可复现环境<br/>阅读目标版本的迁移指南<br/>否则多个包同时变化，很难判断问题从哪开始"]
    S2["② 顺着新的分层检查兼容关系<br/>langchain、LangGraph 和模型集成包各有更新节奏<br/>确认版本组合后再替换废弃导入路径和内部 API<br/>小步修改、小步运行"]
    S3["③ 代码能启动只说明导入问题解决了<br/>工具调用、结构化输出、流式响应、持久化<br/>仍要分别回归"]
    S4["④ 有副作用的路径<br/>付款、发消息先在隔离环境验证幂等<br/>再做小流量发布"]
    S1 --> S2 --> S3 --> S4

    style S3 fill:#fff3cd
    style S4 fill:#fff3cd
```

### 11.7.1 一条容易被忽略的稳定性边界

> **不同包的更新节奏并不完全一致。主包的稳定承诺不能自动覆盖社区集成、合作伙伴包和实验性 API。**

**因此生产项目应该固定依赖版本，并尽量建立在公开稳定接口之上。**

## 11.8 演进方向是什么

**把几次架构变化连起来，主线其实很清楚**：

```mermaid
flowchart LR
    A["langchain-core<br/>稳定基础协议"] --> B["集成拆包<br/>解决核心与外部 SDK<br/>节奏不一致"]
    B --> C["Runnable + LCEL<br/>统一确定性流程的组合方式"]
    C --> D["LangGraph<br/>承接复杂状态和执行流程"]
    D --> E["create_agent + middleware<br/>提供更易用的 Agent 入口"]

    style A fill:#e8f0fe
    style E fill:#e6f4ea
```

> **这套方向让 LangChain 从「封装大量 LLM 功能」，转向「提供清晰分层的 Agent 工程体系」。**
>
> **代价**是旧项目升级需要处理依赖和导入路径；**收益**是核心接口更稳定、复杂流程更可控，也更适合生产环境。

## 11.9 常见错误

### 11.9.1 把演进理解成「不断加功能」

**它是在反复重新划分边界**：哪些稳定、哪些独立、哪些下沉。

### 11.9.2 背诵每个小版本的 API 变化

**抓四个架构节点就够了**，也不建议报当前最新补丁版本。

### 11.9.3 认为 v1 把旧 API 全删了

**它们迁到了 `langchain-classic`**，存量项目可渐进迁移。

### 11.9.4 以为 LangGraph 是来替换 LangChain 的

**高层易用性留在 LangChain，复杂执行能力下沉到 LangGraph。**

### 11.9.5 把 Pydantic 2 迁移当成最重要的变化

它是重要背景，**但拆包、Runnable、LangGraph 和 v1 架构更能体现方向**。

### 11.9.6 升级只更新依赖版本就上线

**必须分别回归工具调用、结构化输出、流式响应和持久化。**

### 11.9.7 一次性改完所有代码再启动

**应该小步修改、小步运行**，否则无法定位问题来源。

### 11.9.8 假设主包稳定承诺覆盖所有包

**社区集成、合作伙伴包和实验性 API 节奏不同**，生产要固定版本。

### 11.9.9 升级后直接放量有副作用的路径

**先在隔离环境验证幂等，再小流量发布。**

## 11.10 本章总结

1. **演进的动因是三层问题叠加**：依赖牵一发动全身、专用 API 不统一、执行循环藏在执行器内部；
2. **节点一「拆包」**：`langchain-core` 稳定协议，集成独立迭代——「稳定内核，释放边缘」；
3. **节点二「Runnable + LCEL」**：从「大量预制类」转向「少量标准协议 + 组合」，组合后仍是 Runnable；
4. **节点三「LangGraph」**：把隐藏循环摊开成 State + Node + Edge，检查点支撑暂停恢复与长时间执行；
5. **节点四「v1 聚焦 Agent」**：`create_agent` 做入口、middleware 做扩展、`langchain-classic` 承接旧能力；
6. **v1 不是删掉旧 API**，而是主命名空间精简 + 渐进迁移；
7. **Pydantic 2 是重要迁移背景**，但不是最能体现方向的变化；
8. **升级四步**：锁环境读指南 → 按分层确认版本组合并小步替换 → 分别回归四类边界能力 → 副作用路径先隔离验证幂等再小流量；
9. **稳定承诺不覆盖社区包和实验性 API**，生产要固定版本；
10. **总方向**：稳定核心、解耦集成、组合确定性流程、图化 Agent 运行时。

> **一句话概括：LangChain 的版本演进不是功能堆叠史，而是一条不断重划边界的路线——先把协议稳下来、把集成放出去，再用 Runnable 统一确定性流程、用 LangGraph 承接复杂执行，最后在高层用 create_agent 和 middleware 把易用性还给开发者。**

## 参考资料

- [LangChain v1 迁移指南](https://docs.langchain.com/oss/python/migrate/langchain-v1)
- [LangChain 官方文档](https://docs.langchain.com/oss/python/langchain/overview)
- [LangChain v1 发布说明](https://docs.langchain.com/oss/python/releases/langchain-v1)
- [LangChain v0.3 版本说明（Pydantic 2 迁移）](https://python.langchain.com/docs/versions/v0_3/)
- [LangChain 官方博客](https://blog.langchain.com/)
- [LangGraph 官方文档](https://docs.langchain.com/oss/python/langgraph/overview)
- [Pydantic 迁移指南](https://docs.pydantic.dev/latest/migration/)
