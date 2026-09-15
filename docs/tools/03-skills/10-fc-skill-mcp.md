---
description: 从模型输出、任务知识和外部能力连接三个层次比较 Function Calling、Skill 与 MCP，并说明三者如何组合。
---

# 第十章：Function Calling、MCP、Skill 三者关系

## 10.1 为什么会有三个概念

最典型的误解是把这三个当成「不同厂商在不同时期推出的竞争方案，选一个用就行」。

它们是**可组合的三种接口与内容机制**，不是必须逐层依赖的技术栈。

可以先看**每句话的主语是谁**：

| | 谁在说话 | 说什么 |
|---|---|---|
| **Function Calling** | 模型 | 「我要调这个函数，参数是这些」 |
| **MCP** | 工具服务 | 「我能提供这些函数」 |
| **Skill** | 操作手册 | 「用这些工具，按这个流程做」 |

主语不同、对话对象不同、粒度不同——这就是三者的本质差异。

### 10.1.1 代表性发布节点不等于依赖关系

```mermaid
timeline
    title 三种机制的代表性发布时间
    2023 : Function Calling : 问题「模型只会生成文本<br/>怎么让它触发外部调用」
    2024 : MCP : 问题「每个应用都在重复<br/>写对接各种工具的代码」
    2025 : Agent Skill : 问题「工具有了<br/>但 Agent 不知道该按什么流程用」
```

这条时间线指 OpenAI Function Calling、MCP 和 Anthropic Agent Skills 的发布节点，不是工具调用、接口标准化或流程复用思想的起源。三者分别处理：

- Function Calling 解决**调用协议**问题：模型和程序之间需要一套结构化的表达方式；
- MCP 处理重复对接的问题，把工具、资源和提示模板的接入**标准化**，让兼容的应用复用服务端能力；
- Skill 处理任务步骤和标准的重复维护，组织**知识与流程复用**，并不要求工具先通过 MCP 接入。

## 10.2 从「谁和谁通信」定位三者

```mermaid
flowchart TB
    subgraph L3["第三层 · Skill"]
        direction LR
        AGENT[Agent] <-->|"扫描 / 加载"| KM["知识模块<br/>SKILL.md + 脚本 + 模板"]
    end

    subgraph L2["第二层 · MCP"]
        direction LR
        CLIENT[MCP Client] <-->|"JSON-RPC<br/>tools/list · tools/call"| SERVER[MCP Server]
    end

    subgraph L1["第一层 · Function Calling"]
        direction LR
        MODEL[模型] <-->|"tool_calls JSON<br/>tool 消息回填"| HOST[宿主程序]
    end

    L3 -.->|"可选：流程中使用 MCP"| L2
    L2 -.->|"可选：Host 转成 FC 格式<br/>并回传结果"| L1

    style L3 fill:#e6f4ea
    style L2 fill:#e8f0fe
    style L1 fill:#fef7e0
```

| 层次 | 发生在哪两个角色之间 | 本质 | 粒度 |
|---|---|---|---|
| Function Calling | 模型 ↔ 宿主程序 | 单次调用的格式规范 | 一次函数调用 |
| MCP | MCP Client ↔ MCP Server | 工具的标准化封装与发现 | 一个工具 / 一组工具 |
| Skill | Agent ↔ 知识模块 | 流程与标准的可复用封装 | 一类完整任务 |

注意粒度的跨度：「查询订单表」是一个 **MCP 工具**，「代码审查」「数据分析报告」是一个 **Skill**——一个 Skill 内部可能有好几个步骤，每步可调用多个 MCP 工具；由 LLM 驱动时，常以 Function Calling 或结构化输出表达调用意图。

## 10.3 组合关系不是强制依赖

可以用反例检查是否混淆了职责：

```mermaid
flowchart TB
    S["Skill<br/>定义流程"] --> H["Host / Agent<br/>选择与执行"]
    H --> M["MCP Client<br/>调用 Server"]
    H --> LOCAL["本地函数 / CLI / API"]
    F["Function Calling<br/>模型提出调用"] --> H
    RULE["规则工作流 / 人工操作"] --> H

    style S fill:#e6f4ea
    style M fill:#e8f0fe
    style F fill:#fef7e0
```

这些路径都能成立：

- **没有原生 Function Calling**，Host 仍可用结构化文本、规则或人工选择触发工具；区别在可靠性和适配成本；
- **MCP 可与 Function Calling 配合**：许多 Host 会把 MCP Tool 转成模型 schema，但 MCP 不强制这条适配路径。[第六章](../02-mcp/06-mcp-vs-function-calling.md) 详细拆过这条时序链；
- **需要外部操作的 Skill 依赖宿主提供相应能力，而非特定协议**：执行中可使用 MCP、内嵌函数或其他受控集成。

仅有 Function Calling 加执行器就能工作；确定性程序也能单独用 MCP；纯写作 Skill 可以不调任何外部工具。三者都不是另外两者成立的必要条件。

## 10.4 三种边界，三种不同的失败

| | 边界 | 典型失败 |
|---|---|---|
| **Function Calling** | 模型提议 → 应用执行 | 工具选错、参数语义错、未授权调用 |
| **MCP** | Client → Server | 版本不兼容、认证失败、超时后结果未知 |
| **Skill** | 可复用知识 → 当前任务上下文 | 错误触发、过时指令、脚本依赖缺失 |

“参数是合法 JSON”“Server 能连接”“Skill 已加载”分别只证明一个环节通过，不能证明整个任务完成。

## 10.5 一个完整场景串起三层

用户说：**「帮我分析最近三个月的销售数据，找出下滑的产品线，给改进建议。」**

```mermaid
sequenceDiagram
    participant U as 用户
    participant A as Agent
    participant SK as Skill 层
    participant MC as MCP Client
    participant MS as MCP Servers
    participant M as 模型

    U->>A: 分析销售数据并给建议
    A->>SK: 扫描 Skill 元数据
    SK-->>A: 匹配到「数据分析报告」Skill
    A->>SK: 加载 SKILL.md 正文
    SK-->>A: 流程：取数 → 趋势分析 → 按模板成文

    Note over A,MS: 第一步：取数
    A->>M: 任务 + 流程 + 可用工具定义
    M-->>A: tool_calls: query_database(sql=...)
    A->>A: 校验查询范围、参数与用户权限
    A->>MC: 路由调用
    MC->>MS: tools/call → 数据库 Server
    MS-->>MC: 查询结果
    MC-->>A: 结果
    A->>M: tool 消息回填

    Note over A,MS: 第二步：趋势分析
    M-->>A: tool_calls: run_python(code=...)
    A->>A: 检查执行权限、隔离与资源预算
    A->>MC: 路由调用
    MC->>MS: tools/call → Python 执行器 Server
    MS-->>MC: 分析结果
    MC-->>A: 结果
    A->>M: tool 消息回填

    Note over A,SK: 第三步：按 Skill 模板成文
    M-->>A: 结构化分析报告
    A-->>U: 返回报告
```

放到这个流程里看，三层分工分别是：

- **Skill 指导流程**——说明先取数、再分析、最后按模板成文。业务告警阈值需声明由谁制定，不能把任意百分比叫作统计显著；
- **MCP 提供能力发现与调用接口**——Client 从已知 Server 取得工具列表，Host 再按权限和任务筛选，不是连接建立后所有工具自动进入模型上下文；
- **Function Calling 做模型与工具的通信**——每一次 `tool_calls` 输出和 `tool` 消息回填。

Host 还需验证用户可访问的销售范围、限制 SQL、隔离 Python 执行器，并保留数据时间与来源。MCP 2026-07-28、Agent Skills 文件格式和模型工具 API 的版本分别管理；任何一层升级都要回归这条完整链路。

图中展示成功路径。查询失败时不能继续生成销售结论；数据只覆盖部分日期时要明确范围，分析脚本失败则保留已取得的数据并报告缺失步骤。销量下滑不直接证明原因，改进建议还要区分数据支持的判断与待验证假设。

## 10.6 常见错误

### 10.6.1 当成三个竞争方案

它们可以共同出现，也可以单独使用；先明确要解决的是模型输出、能力接入还是流程复用。

### 10.6.2 说不清依赖方向

更准确的关系是：Host 按 Skill 指令编排能力；MCP 标准化一部分能力接入；Function Calling 是模型选择工具时常见的表达层。三者可组合，不构成强制的单向依赖。

### 10.6.3 认为三者缺一不可

任何一项缺失都可有其他实现路径。小项目也可能需要标准化或流程复用，不能只按项目大小决定。

### 10.6.4 混淆粒度

一个 Skill 不等于一个工具。它可描述整类任务，也可只组织写作标准；是否调用工具、调用几次不是格式规定。

### 10.6.5 把 MCP 说成「Anthropic 版的 Function Calling」

MCP 不是 FC 的替代实现，也不建立在 FC 之上。同一个 MCP Server 可以服务不同 Host；当 Host 使用模型工具接口时，可将工具定义翻译成各家的 FC schema，也可采用其他调用路径。

### 10.6.6 只背概念不讲协作

如果要向别人解释这三者，拿一个具体场景把三层串起来，通常比分别背三段定义更能说明问题。

## 10.7 本章总结

1. **三者是可组合机制，不是强制依赖栈**；
2. **主语法可以快速区分**：模型说「我要调」、服务说「我能提供」、手册说「按这个流程做」；
3. **发布时间不证明依赖**，这几类问题和方法在具体产品发布前已经存在；
4. **Host 可按 Skill 编排 MCP 或其他能力**；MCP Tool 可由模型提议或确定性流程触发，执行前仍需校验；
5. **粒度跨度大**：一次调用 / 一个工具 / 一类完整任务；
6. **不是缺一不可**：FC 配合执行器就能工作，是否引入 MCP 或 Skill 取决于接口和流程的复用需求，而非项目规模门槛；
7. **完整调用链要包含授权、失败恢复与结果证据**，不能只画成功路径。

## 参考资料

- [OpenAI: Function Calling 指南](https://platform.openai.com/docs/guides/function-calling)
- [Model Context Protocol 官方文档](https://modelcontextprotocol.io/docs/getting-started/intro)
- [MCP 规范 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28)
- [Anthropic: Introducing Agent Skills](https://www.anthropic.com/news/skills)
- [Agent Skills 规范](https://agentskills.io/specification)
- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
