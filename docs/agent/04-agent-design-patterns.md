# 第四章：Agent 设计范式

## 4.1 什么是 Agent 设计范式

Agent 设计范式描述的是：

> **Agent 如何组织推理、规划、行动、观察、验证与重试。**

它不是某个特定框架，也不只是一个 Prompt 模板，而是一种运行时控制策略。

目前最常见的三类基础范式是：

1. **ReAct**：一边观察、一边决定下一步；
2. **Plan-and-Execute**：先建立全局计划，再执行和动态重规划；
3. **Reflection / Reflexion**：通过评估、反馈和经验总结改进下一次尝试。

三者并不互斥。生产系统通常采用分层组合：

```mermaid
flowchart TB
    G[用户目标] --> WF[Workflow / 安全边界]
    WF --> P[Planner / 全局计划]
    P --> E[Executor]
    E --> R[局部 ReAct 循环]
    R --> V[Verifier / Evaluator]
    V -->|通过| DONE[完成]
    V -->|局部失败| R
    V -->|计划失效| P
    V -->|需要人工判断| H[Human-in-the-loop]
```

## 4.2 ReAct：推理与行动交替

ReAct（Reasoning and Acting）将推理与外部行动结合起来。经典表达是：

> **Thought → Action → Observation → Thought**

```mermaid
flowchart LR
    T[Thought / Decide] --> A[Action]
    A --> O[Observation]
    O --> T
    T --> F[Final Answer]
```

### 4.2.1 一轮 ReAct 如何运行

#### Thought

模型分析当前目标、状态和观察结果，并决定下一步策略。

#### Action

模型生成结构化动作，例如调用搜索工具：

```json
{
  "tool_call": {
    "name": "search_web",
    "arguments": {
      "query": "竞品 A 最新产品更新"
    }
  }
}
```

#### Observation

Runtime 执行 Tool，并将真实结果或错误返回给模型。模型基于新证据进入下一轮决策。

### 4.2.2 现代实现不应暴露完整 Thought

早期 ReAct 示例会让模型显式输出 Thought。现代系统通常不依赖向用户展示完整思维链，而是保留：

- 当前目标；
- 结构化计划；
- Tool Call；
- Observation；
- 状态变化；
- 简洁且可验证的行动理由。

因此，工程实现中更合适的表达是：

> **Observe → Decide → Act → Observe**

模型可以在内部完成推理，但系统应通过工具轨迹、证据和验证结果保证可解释性，而不是依赖展示全部隐藏推理。

### 4.2.3 ReAct 的决策形式

设当前目标为 $g$、状态为 $s_t$、观察为 $o_t$、可用上下文为 $c_t$，下一步动作可表示为：

$$
a_t \sim \pi_{\theta}(a\mid g,s_t,o_t,c_t)
$$

Runtime 执行动作后得到新的观察：

$$
o_{t+1}=Env(a_t)
$$

Agent 随后更新状态：

$$
s_{t+1}=Update(s_t,a_t,o_{t+1})
$$

### 4.2.4 ReAct 的优势

- 实现简单；
- 能及时利用最新环境反馈；
- 适合无法预先获得完整信息的任务；
- 工具失败后可以立即调整；
- 对短任务和探索性任务非常有效。

### 4.2.5 ReAct 的局限

ReAct 常被概括为“走一步看一步”，其主要风险包括：

- 缺少全局任务结构；
- 每次 Tool Call 通常都需要再次调用模型；
- 容易重复搜索或调用相同工具；
- 长任务中目标和约束可能被上下文噪音稀释；
- 局部合理的动作未必形成全局最优路径；
- 完成条件模糊时容易过早停止或持续循环。

这里的“局部最优”是一个直观类比，不是严格的优化保证。模型选择的动作甚至不一定是当前局部最优，只是根据当前上下文生成的候选动作。

### 4.2.6 改进 ReAct

生产系统通常加入：

- 始终可见的目标和验收条件；
- 结构化任务状态；
- Todo 或阶段检查点；
- Tool Call 去重；
- 无进展检测；
- 最大步骤、时间和费用预算；
- 周期性全局目标复核；
- 关键步骤的外部验证。

```mermaid
flowchart TB
    O[Observation] --> D[Decide]
    D --> C{动作是否重复或越权?}
    C -->|是| RP[重新规划或停止]
    C -->|否| A[Action]
    A --> U[更新结构化状态]
    U --> G{仍符合全局目标?}
    G -->|是| O
    G -->|否| RP
```

## 4.3 Plan-and-Execute：规划与执行解耦

Plan-and-Execute 将全局规划与局部执行分开。成熟实现通常包含三个角色：

1. **Planner**：生成带依赖关系的计划；
2. **Executor**：执行一个或多个计划步骤；
3. **Replanner**：根据结果更新剩余计划或结束任务。

Planner、Executor 和 Replanner 可以使用不同模型，也可以由同一个模型在不同上下文中承担。

```mermaid
flowchart TB
    G[目标] --> P[Planner]
    P --> PLAN[计划 / DAG]
    PLAN --> E[Executor]
    E --> O[执行结果]
    O --> V{计划仍然有效?}
    V -->|是| N{还有步骤?}
    N -->|是| E
    N -->|否| DONE[完成]
    V -->|否| RP[Replanner]
    RP --> PLAN
```

### 4.3.1 计划不应只是自然语言列表

一个可靠的计划步骤最好包含：

- 唯一 ID；
- 目标；
- 依赖步骤；
- 所需输入；
- 推荐 Tool 或执行器；
- 预期输出；
- 验收条件；
- 风险等级；
- 失败和回退策略。

```json
{
  "id": "compare-products",
  "goal": "比较竞品 A 与竞品 B 的核心能力",
  "depends_on": ["research-a", "research-b"],
  "inputs": ["artifact://research-a", "artifact://research-b"],
  "success_criteria": [
    "至少覆盖功能、定价和目标用户",
    "每项关键结论包含来源"
  ]
}
```

结构化计划比自由文本列表更容易调度、验证和恢复。

### 4.3.2 动态重规划

Plan-and-Execute 不等于“计划一次，然后机械执行”。每个关键步骤完成后，Replanner 应判断：

- 执行结果是否达到验收条件；
- 关键假设是否仍然成立；
- 后续步骤是否仍有必要；
- 是否需要插入、删除或重排步骤；
- 是否可以并行执行；
- 是否需要人工确认。

设当前计划为 $P_t$，新观察为 $o_{t+1}$，重规划可以表示为：

$$
P_{t+1}=R(P_t,o_{t+1},g,s_t)
$$

其中 $R$ 表示 Replanner。

### 4.3.3 动态插入步骤示例

原始计划：

```text
1. 搜索竞品 A
2. 搜索竞品 B
3. 对比分析
```

执行第一步后发现竞品 A 刚发布重大版本，计划更新为：

```text
1. 搜索竞品 A
2. 调研竞品 A 的重大版本更新
3. 搜索竞品 B
4. 对比分析
```

此时计划仍提供全局方向，但可以根据环境反馈演化。

### 4.3.4 Plan-and-Execute 的优势

- 对复杂任务具有更强的全局视野；
- 可以显式表达步骤依赖；
- 计划可以在执行前由人工审核；
- 容易分配不同模型和工具；
- 可以将独立步骤并行化；
- 更适合 checkpoint 和故障恢复。

### 4.3.5 Plan-and-Execute 的局限

- 规划和重规划增加延迟与成本；
- 初始计划可能建立在错误假设上；
- 规划器可能生成不可执行或过度细化的步骤；
- 频繁重规划可能退化成高成本 ReAct；
- Planner 与 Executor 之间可能出现语义偏差；
- 长计划可能在环境变化后迅速失效。

因此，计划粒度应与任务稳定性匹配：环境变化越快，计划越应保持高层和短周期。

## 4.4 更先进的规划执行变体

### 4.4.1 ReWOO

ReWOO（Reasoning Without Observation）让 Planner 预先生成带变量引用的计划，执行器可以将前一步结果绑定到变量，并在后续步骤中复用。

```text
E1 = Search["本年度决赛队伍"]
E2 = LLM["从 E1 中提取第一支队伍"]
E3 = Search["E2 的核心球员数据"]
```

它的目标之一是减少每个 Tool 执行之间都调用大型规划模型的需要。

### 4.4.2 DAG Planning

当计划包含明确依赖时，可以将其表示为有向无环图：

```mermaid
flowchart LR
    A[调研竞品 A] --> D[对比分析]
    B[调研竞品 B] --> D
    C[收集行业趋势] --> E[趋势影响分析]
    D --> F[生成报告]
    E --> F
```

没有依赖的步骤可以并行执行，从而降低总延迟。

### 4.4.3 LLMCompiler

LLMCompiler 类架构通常包含：

- Planner：生成或流式输出任务 DAG；
- Task Fetching Unit：依赖满足后立即调度任务；
- Joiner：汇总结果，并决定结束还是重新规划。

这类设计关注的不只是规划质量，也关注执行并行度、模型调用次数和总体延迟。

## 4.5 Reflection：通过反馈改进结果

Reflection 在生成或执行之后加入评估环节：

```mermaid
flowchart LR
    G[Generate / Execute] --> E[Evaluate]
    E --> D{达到标准?}
    D -->|是| DONE[完成]
    D -->|否| FB[生成反馈]
    FB --> G
```

评估可以发生在：

- 单个步骤完成后；
- 一个里程碑完成后；
- 整个任务完成后；
- 只有高风险或低置信度时。

### 4.5.1 验证器的优先级

Reflection 不应默认等于“让同一个 LLM 再看一遍”。能够使用确定性或外部验证时，应优先使用：

1. 编译器、单元测试和静态分析；
2. Schema、规则和约束检查；
3. 数据库或 API 返回的真实状态；
4. 人工审核；
5. 独立模型或 LLM-as-a-Judge；
6. 同一模型的自我评价。

越靠前的信号通常越接近可验证的客观反馈。

### 4.5.2 Reflection 的适用场景

- 代码生成与修复；
- 文案和报告优化；
- 翻译；
- 需要来源完整性的研究；
- 具有明确评分规则的结构化输出；
- 可以通过模拟器或测试环境验证的任务。

### 4.5.3 Reflection 的风险

- 评估模型可能与生成模型共享相同盲点；
- 没有明确标准时，反思可能只是改写；
- 多轮优化可能出现质量退化；
- 反思文本可能污染后续上下文；
- Agent 可能针对评分规则“投机”而非真正完成目标；
- 成本和延迟随轮数增加。

因此，需要最大反思轮数、最低改进阈值和清晰的成功标准。

## 4.6 Reflexion：带经验记忆的反思

Reflexion 是 Reflection 的一种具体范式。它不更新模型权重，而是把任务反馈转化为自然语言经验，并将其保存在情景记忆中供下一次尝试使用。

其经典结构包含：

- **Actor**：执行任务；
- **Evaluator**：评价轨迹或结果；
- **Self-Reflection**：将失败信号总结为可操作经验；
- **Episodic Memory**：在后续尝试中提供这些经验。

```mermaid
flowchart TB
    A[Actor] --> ENV[环境 / 工具]
    ENV --> TRAJ[执行轨迹与结果]
    TRAJ --> E[Evaluator]
    E --> PASS{成功?}
    PASS -->|是| DONE[结束]
    PASS -->|否| SR[Self-Reflection]
    SR --> MEM[情景记忆]
    MEM --> A
```

### 4.6.1 “错题本”类比

普通重试可能只是再次生成；Reflexion 会先总结：

- 哪个假设错误；
- 哪一步行动无效；
- 哪个反馈被忽略；
- 下一次应该采用什么不同策略。

这些经验作为额外上下文加入下一次尝试，因此类似“做错题、分析原因、带着经验重做”。

### 4.6.2 HumanEval 结果应如何解读

Reflexion 论文报告：在其 2023 年的实验设置中，基于 GPT-4 的 Reflexion 在 HumanEval 上达到 **91% pass@1**，论文引用的 GPT-4 基线为 **80%**。

这个数字说明反思与执行反馈在特定实验中具有价值，但不能直接推导为：

- 所有模型都能从 80% 提升到 91%；
- 所有代码任务都能获得相同提升；
- 生产项目中的仓库级任务也有相同效果；
- 增加反思轮次一定持续提高质量。

模型版本、Prompt、测试生成方式、任务分布和基准污染都会影响结果。生产系统应以自己的评估集和成本指标为准。

### 4.6.3 记忆污染问题

模型生成的反思不一定正确。如果未经验证就写入长期记忆，错误经验可能影响未来任务。

更安全的策略是：

1. 默认将反思保留在当前任务的临时记忆中；
2. 使用测试、环境反馈或人工审核验证；
3. 只有稳定、可复用的经验才晋升为长期记忆、Skill 或规则；
4. 为长期经验记录来源、版本和适用范围。

## 4.7 三种范式如何组合

一种常见的分层架构是：

```mermaid
flowchart TB
    G[目标] --> P[Plan-and-Execute<br/>生成全局里程碑]
    P --> S1[步骤 1]
    P --> S2[步骤 2]
    P --> S3[步骤 N]

    S1 --> R1[ReAct<br/>局部探索与工具调用]
    S2 --> R2[ReAct<br/>局部探索与工具调用]
    S3 --> R3[ReAct<br/>局部探索与工具调用]

    R1 --> V[Reflection / Verifier]
    R2 --> V
    R3 --> V

    V -->|局部失败| RETRY[局部重试]
    V -->|计划失效| P
    V -->|通过| DONE[完成]
```

职责划分为：

- **Plan-and-Execute**：保持全局方向；
- **ReAct**：处理局部未知和工具反馈；
- **Reflection**：检查质量并产生改进反馈；
- **Workflow**：限制整体路径、权限和预算。

## 4.8 Agentic Workflow：生产环境的默认思路

Agentic Workflow 用确定性流程包围概率性决策：

```mermaid
flowchart LR
    IN[输入] --> V[校验]
    V --> ROUTE[固定路由]
    ROUTE --> AG[受限 Agent 节点]
    AG --> CHECK[确定性验证]
    CHECK -->|通过| OUT[输出]
    CHECK -->|可修复| AG
    CHECK -->|高风险| HUMAN[人工审核]
```

以客服系统为例：

- 意图识别、权限检查和输出审核由 Workflow 控制；
- 知识检索节点可以使用 ReAct 动态决定查询方式；
- 复杂问题使用 Plan-and-Execute 拆分；
- 最终答案使用引用检查或 Reflection；
- 退款、改价等操作必须经过确定性规则和人工确认。

这种方式将自主性限制在真正需要灵活性的局部范围内。

## 4.9 如何选择范式

| 任务特征 | 推荐范式 |
|---|---|
| 步骤少、信息需要边做边获取 | ReAct |
| 步骤多、依赖复杂、需要全局视野 | Plan-and-Execute |
| 子任务存在明确依赖且可并行 | DAG Planning |
| 每次工具调用都咨询大模型成本过高 | ReWOO 或分层执行 |
| 输出质量要求高且存在验收标准 | Reflection |
| 希望从失败经验中改进下一次尝试 | Reflexion |
| 主流程稳定、局部存在未知 | Agentic Workflow |
| 高风险、强合规、路径完全已知 | 确定性 Workflow |

还可以从两个基础维度判断：

```mermaid
quadrantChart
    title Task complexity and quality requirements
    x-axis Low complexity --> High complexity
    y-axis Low quality requirement --> High quality requirement
    quadrant-1 Plan-and-Execute plus Reflection
    quadrant-2 ReAct plus Reflection
    quadrant-3 Simple workflow
    quadrant-4 Plan-and-Execute
    ReAct: [0.30, 0.40]
    Plan-and-Execute: [0.78, 0.48]
    Reflection: [0.40, 0.82]
    Hybrid Agent: [0.82, 0.85]
```

二维图只是帮助理解。实际选择还需考虑风险、延迟、成本、可验证性和环境变化速度。

## 4.10 停止、预算与无进展检测

所有范式都必须具有停止条件：

- 达到明确成功标准；
- 达到最大步骤数；
- 达到 Token 或费用预算；
- 超过运行时间；
- 连续多轮没有产生新信息；
- 重复相同 Tool Call；
- 反思后评分不再改善；
- 触发安全策略；
- 需要人工判断；
- 用户主动取消。

可以定义一个受限执行预算：

$$
B=(N_{max},T_{max},C_{max},R_{max})
$$

其中：

- $N_{max}$：最大步骤数；
- $T_{max}$：最大运行时间；
- $C_{max}$：最大费用或 Token；
- $R_{max}$：最大重试或反思次数。

当预算耗尽时，系统应明确报告未完成状态和已有结果，而不是伪装成成功。

## 4.11 生产级设计检查表

### ReAct

- 是否持续保留目标和成功标准？
- 是否检测重复动作和无进展循环？
- Observation 是否来自真实工具结果？
- Tool 错误是否以结构化形式返回？

### Plan-and-Execute

- 计划是否具有依赖、输入和验收条件？
- 是否存在 Replanner？
- 什么事件会触发重规划？
- 能否只重规划受影响的局部步骤？

### Reflection / Reflexion

- 是否有客观验证器？
- 评价标准是否明确？
- 最大优化轮数是多少？
- 反思是否可能污染长期记忆？
- 改进是否值得额外延迟和成本？

### Agentic Workflow

- 哪些节点必须确定执行？
- 哪些节点确实需要 Agent 自主性？
- 高风险动作是否经过审批？
- 是否保留完整 Trace、状态和审计记录？

## 4.12 Anthropic 原则的准确理解

“能用 Workflow 解决，就不要用 Agent”是对 Anthropic 工程建议的通俗概括，但不是原文中的绝对规则。

更准确的原则是：

> **从能够满足需求的最简单方案开始，只有在更高复杂度能够带来可测量收益时，才升级为多步 Workflow 或自主 Agent。**

Anthropic 的区分是：

- 路径明确、需要一致性和可预测性时，优先使用 Workflow；
- 路径无法预先确定、需要模型动态决策时，才使用 Agent；
- 很多问题通过单次 LLM 调用、检索和示例优化就能解决。

复杂度本身不是能力。只有当任务成功率、质量或可扩展性得到可验证提升时，增加 Agent 自主性才有价值。

## 4.13 本章总结

ReAct、Plan-and-Execute 与 Reflection 分别解决三个不同问题：

1. **ReAct**：如何根据最新环境反馈选择下一步；
2. **Plan-and-Execute**：如何维持复杂任务的全局结构；
3. **Reflection / Reflexion**：如何利用验证和失败经验提升质量。

生产级 Agent 通常将它们组合在受控 Workflow 中：

> **Workflow 控制边界，Planner 保持方向，ReAct 处理局部未知，Verifier 提供客观反馈，Reflection 负责有限优化。**

## 参考资料

- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366)
- [LangChain: Planning Agents](https://www.langchain.com/blog/planning-agents)
- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
