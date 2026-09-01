# 第五章：MCP 的三层组成

## 5.1 用三层把概念理清

第一次接触 MCP，最劝退的是名词密度：Host、Client、Server、Tools、Resources、Prompts、JSON-RPC、stdio、Streamable HTTP、sampling、elicitation、roots……

把它拆成三层来看，会清楚很多，而且这三层在设计上本来就是解耦的：

```mermaid
flowchart TB
    subgraph L1["第一层 · 角色架构：谁和谁在通信"]
        A["Host ── Client ── Server"]
    end

    subgraph L2["第二层 · 能力类型：Server 能提供什么"]
        B["Tools / Resources / Prompts<br/>+ Client input capabilities"]
    end

    subgraph L3["第三层 · 传输协议：消息怎么传"]
        C["JSON-RPC 2.0 消息格式<br/>+ stdio / Streamable HTTP 传输方式"]
    end

    L1 --> L2 --> L3
```

解耦的意思是：传输可替换而不改变核心能力语义；能力扩展也不必重写角色模型。

## 5.2 第一层：角色架构

### 5.2.1 三个角色各自做什么

| 角色 | 是什么 | 核心职责 |
|---|---|---|
| **Host** | AI 应用本身（Claude Desktop、Cursor、你的 Agent） | 启动和管理所有 Client、决定连哪些 Server、执行安全策略、处理用户授权、协调 LLM 调用 |
| **Client** | Host 内部的连接模块 | 通信、能力发现和转发请求/结果；通常对应一个 Server 连接 |
| **Server** | 工具提供方的独立进程 | 暴露 Tools / Resources / Prompts，不关心上游是谁 |

用一个公司的类比：Host 是公司，决定和哪些供应商合作；Client 是派驻到每个供应商的联络员，一人对接一家；Server 是供应商，只管按标准交付，不关心客户是谁。

### 5.2.2 一对一连接便于隔离，但不是安全保证

Host 常为每个 Server 建立独立 Client/连接，便于管理生命周期、认证与故障；规范不会因此自动隔离 Server 的文件、网络或进程权限。

```mermaid
flowchart TB
    subgraph GOOD["独立 Client / 连接"]
        H1[Host] --> C1[Client 1] --> S1[财务数据 Server]
        H1 --> C2[Client 2] --> S2[第三方工具 Server]
        NOTE1["便于分别管理<br/>版本、认证、故障与生命周期"]
    end

    subgraph BOUNDARY["真正的安全边界"]
        P["Host 策略"] --> R["进程 / 容器权限"]
        P --> N["网络出口与数据过滤"]
        P --> A["用户授权与审计"]
    end

    style GOOD fill:#e6f4ea
    style BOUNDARY fill:#fff3cd
```

面对第三方 Server，Host 还应使用最小权限、进程/容器隔离、网络出口控制和参数过滤。只有这些运行时策略才能限制一个 Server 能读取和执行的范围。

### 5.2.3 Host 是唯一的权限把关者

Host 和 Client 经常被混在一起。Client 负责通信和转发，授权与策略决定仍在 Host。

具体来说，这些决策全在 Host：

- 用户是否授权某次工具调用；
- 哪些 Server 的工具可以暴露给模型；
- 敏感操作是否需要二次确认；
- 多个 Server 的上下文怎么聚合进 Prompt。

Server 无权决定自己的工具会不会被调用，Client 也无权替用户同意。这条边界在讨论 MCP 安全时是核心。

## 5.3 第二层：能力类型

### 5.3.1 Server 提供的三类能力

区分它们的关键是**默认控制路径**，而不是「读还是写」或是否有副作用：

| 能力 | 控制权 | 有副作用 | 典型场景 |
|---|---|---|---|
| **Tools** | 模型或 Host 工作流可选择，Host 最终放行 | 可读、可写或有副作用 | 搜索、创建 Issue、发消息、写文件 |
| **Resources** | Client/Host 决定何时读取/注入 | 通常是可读取上下文；不构成安全承诺 | 读日志、读文档、读数据库记录 |
| **Prompts** | 用户或 Host 取得 | 返回模板/消息 | 代码审查模板、周报生成模板 |

> **Tools 是可执行能力，Resources 是可加载上下文，Prompts 是可取得的模板；每一项实际权限都由 Host 的策略决定。**

对应的 JSON-RPC 方法：

```json
{"method": "tools/list"}          // 发现有哪些工具
{"method": "tools/call"}          // 调用某个工具
{"method": "resources/list"}      // 列出可用资源
{"method": "resources/read"}      // 读取某个资源
{"method": "prompts/list"}        // 列出提示模板
{"method": "prompts/get"}         // 展开某个模板
```

`*/list` 这组方法就是「自动发现」的实现。应用不需要硬编码工具清单，连上就问一句。

### 5.3.2 容易被漏掉的第四类：Server 需要 Client 输入

上面三类是 Server **提供**给 Client 的。执行过程中，Server 有时还需要模型推理或用户补充信息。2026-07-28 规范不再让 Server 反向发起 JSON-RPC request，而是在当前响应中返回 `InputRequiredResult`；Client 处理后带输入重发原请求。

| 能力 | Server 想要什么 | 用途 |
|---|---|---|
| **Sampling** | 让 Host 一侧的模型完成受控推理 | Server 需要模型能力，但不应持有 Host 的模型密钥 |
| **Elicitation** | 向用户索取结构化补充信息 | 参数不全时补充；不能替代高风险动作的独立审批 |

Sampling 让 Server 不必持有 Host 的模型 API Key。Host 仍要审查模型、预算、可见上下文与返回范围，防止远端 Server 滥用推理资源或诱导数据外带。

### 5.3.3 InputRequiredResult 的往返模式

当前消息方向仍是 Client request → Server response。需要 Client 输入时，Server 暂停当前处理并返回输入需求：

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    rect rgb(230, 244, 234)
    Note over C,S: Server 需要模型输入
    C->>S: tools/call
    S-->>C: InputRequiredResult(sampling)
    C->>C: Host 审查并执行模型调用
    C->>S: 重发 tools/call + input
    S-->>C: 工具结果
    end
```

并非每个 Server 都使用这些能力。Host 应逐请求声明允许的 Client capabilities，并把用户交互、模型访问、预算和数据边界纳入授权策略。

## 5.4 第三层：传输协议

### 5.4.1 消息格式与传输方式是解耦的

这一层的设计点，就是把消息格式和传输方式分开：

```mermaid
flowchart TB
    MSG["JSON-RPC 2.0<br/>消息格式（不变）"]
    MSG --> T1["stdio<br/>本地子进程"]
    MSG --> T2["Streamable HTTP<br/>远程服务"]
    MSG --> T3["自定义传输<br/>规范允许扩展"]
```

同一套 JSON-RPC 消息可以跑在任意传输层上。**切换传输方式不影响上层的工具调用逻辑**——同一个 Server 实现，改几行配置就能从本地子进程变成远程 HTTP 服务。

### 5.4.2 两种主要传输方式

| | stdio | Streamable HTTP |
|---|---|---|
| Server 形态 | 本地子进程 | 独立 HTTP 服务 |
| 通信通道 | 操作系统管道（stdin/stdout） | HTTP POST |
| 延迟 | 极低 | 有网络开销 |
| 多 Client 共享 | 不支持，每个 Host 起一份 | 支持 |
| 认证 | 靠进程隔离和环境变量 | 需要完整的 OAuth 授权 |
| 典型用途 | 文件系统、本地 Git、本地数据库 | 团队共享服务、SaaS 工具 |

一个实用细节：stdio 模式下 **stdout 只能走协议消息**，任何 `print` 调试输出都会污染消息流导致解析失败。日志必须写 stderr——这是新手写 MCP Server 最常踩的坑。

传输层的完整细节，包括 HTTP+SSE 到 Streamable HTTP 的演进，见 [第十二章](12-mcp-transport.md)。

## 5.5 三层拼起来：一次完整调用

```mermaid
sequenceDiagram
    participant U as 用户
    participant H as Host
    participant C as Client
    participant S as Server
    participant M as LLM

    Note over H,S: 可选发现阶段
    H->>C: 创建 Client 连接 GitHub Server
    C->>S: server/discover
    S-->>C: 支持的版本与能力
    C->>S: tools/list
    S-->>C: [create_issue, search_repos, ...]
    C->>H: 汇总工具清单

    Note over H,M: 运行阶段
    U->>H: 帮我提个 bug issue
    H->>M: messages + 所有 Server 的工具 Schema
    M-->>H: tool_calls: create_issue(...)
    H->>U: 请确认：将创建 Issue
    U->>H: 同意
    H->>C: 转发调用
    C->>S: tools/call
    S-->>C: {"issue_url": "..."}
    C->>H: 结果
    H->>M: role=tool 消息
    M-->>H: 已创建 Issue，链接是……
    H->>U: 最终答案
```

这次完整调用里，有三点最值得注意：

1. **若 Host 使用模型 Function Calling**，可将 MCP Tool 转为该模型的 schema；也可由规则、结构化输出或人工操作调用 MCP。MCP 对模型接口没有强制要求；
2. **用户授权发生在 Host 层**，在调用真正发出去之前；
3. **能力可提前发现，但协商是逐请求的**；每个请求仍携带版本与 Client capabilities，不能只信启动时缓存。

## 5.6 常见错误

### 5.6.1 把三层混在一起讲

面试时把 Host/Client/Server 和 Tools/Resources/Prompts 和 stdio/HTTP 混着说，听起来像在背名词。分成三层，每层回答一个问题（谁在通信、提供什么、怎么传），结构立刻清晰。

### 5.6.2 把连接映射误作安全沙箱

独立 Client/连接有助于管理；但安全边界要靠 Host 的授权、运行时隔离和网络策略，不能只靠对象关系。

### 5.6.3 把 Host 的职责安到 Client 上

授权、安全策略、生命周期管理都在 Host。Client 只是管道。

### 5.6.4 只知道三类 Server 能力，不知道输入需求

Sampling 与 Elicitation 让 Server 在执行中请求 Host 提供模型或用户输入。当前规范通过 `InputRequiredResult` 完成往返，不应继续照抄旧版 Server→Client request 流程。

### 5.6.5 忽略 stdout 污染问题

stdio 模式下往 stdout 打日志会直接破坏协议消息流，而且报错信息通常是难懂的 JSON 解析失败。日志一律写 stderr。

### 5.6.6 忽略逐请求能力协商

每个请求都要携带版本与 Client capabilities；不要只在启动时发现一次后永久相信缓存，也不要假定任意 Host 都允许 sampling 或 elicitation。

## 5.7 本章总结

1. **三层拆解**：角色架构解决「谁和谁通信」，能力类型解决「提供什么」，传输协议解决「怎么传」；
2. **三层尽量解耦**，传输和能力可分别演进；
3. **Host 是决策者，Client 是连接器，Server 是提供者**；独立连接不替代运行时安全隔离；
4. **三类正向能力按默认控制路径区分**：Tools 可由模型/工作流选择，Resources 由 Client 加载，Prompts 由用户/Host 取得；
5. **输入需求容易被漏**：Sampling 让 Server 受控借用 Host 模型，Elicitation 补充用户信息；
6. **当前规范用 `InputRequiredResult` 而非 Server 反向 request**，Client capabilities 随每个请求声明并由 Host 策略控制；
7. **消息格式与传输方式解耦**，同一个 Server 换配置就能在本地和远程之间切换；
8. **stdio 下 stdout 是协议专用通道**，日志必须走 stderr。


## 参考资料

- [MCP 架构说明](https://modelcontextprotocol.io/specification/2026-07-28/architecture)
- [MCP 规范 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28)
- [MCP Server 能力：Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [MCP Client 输入模式](https://modelcontextprotocol.io/specification/2026-07-28/client)
- [MCP 传输层规范](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)
- [JSON-RPC 2.0 规范](https://www.jsonrpc.org/specification)
