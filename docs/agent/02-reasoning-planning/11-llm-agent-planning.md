# 第十一章：如何赋予 LLM 与 Agent 规划能力

## 11.1 规划不等于 CoT

最常见的误区是：

> **CoT = 规划能力**

CoT 只是帮助模型沿一条路径展开中间推理的方法。规划则需要面向未来行动，处理：

- 目标；
- 当前状态；
- 可用动作；
- 依赖关系；
- 资源和权限；
- 动作可能产生的结果；
- 风险和回退；
- 完成条件。

```mermaid
flowchart TB
    R[Reasoning] --> Q[回答：为什么、是什么、能否推出]
    P[Planning] --> A[回答：为了目标，接下来做什么]

    Q --> COT[CoT / ToT / GoT]
    A --> PLAN[Plan / DAG / Policy]
    PLAN --> EXEC[Execution]
    EXEC --> OBS[Observation]
    OBS --> PLAN
```

推理方法可以帮助生成计划，但不能单独构成可靠规划系统。

## 11.2 Reasoning 与 Planning 的区别

| 维度 | Reasoning | Planning |
|---|---|---|
| 核心目标 | 推导结论 | 选择行动序列 |
| 输入 | 问题、事实、规则 | 目标、状态、动作、约束 |
| 输出 | 答案或判断 | 可执行计划或策略 |
| 是否改变环境 | 通常不直接改变 | 计划由执行器作用于环境 |
| 是否需要反馈 | 不一定 | 通常需要 |
| 是否需要重规划 | 较少 | 环境变化时需要 |
| 成功标准 | 推理正确 | 目标在约束内完成 |

例如：

- “为什么 API 调用失败？”是 Reasoning；
- “接下来按什么步骤修复 API？”是 Planning；
- “执行修复并根据测试结果调整”是 Agent Control Loop。

## 11.3 为什么需要显式规划

LLM 可以直接生成答案或动作，但复杂任务容易出现：

- 跳过关键步骤；
- 忽略依赖；
- 工具调用顺序错误；
- 缺少成功标准；
- 过早结束；
- 在局部问题上反复循环；
- 无法估算成本和风险。

显式规划的价值是：

- 将目标转化为可执行步骤；
- 暴露依赖和并行机会；
- 在执行前检查权限与风险；
- 为每一步定义验收条件；
- 支持局部重试和故障恢复；
- 根据真实 Observation 动态调整。

> **规划机制的核心不是让模型“把所有想法写出来”，而是产生可执行、可验证、可更新的控制结构。**

## 11.4 规划能力来自两个层次

### 11.4.1 Model-level Planning

模型层能力包括：

- 理解目标；
- 分解问题；
- 预测动作结果；
- 比较候选方案；
- 生成步骤；
- 识别依赖；
- 根据反馈修订。

这些能力可以通过以下方式增强：

- 预训练和后训练；
- 高质量规划示例；
- Instruction Tuning；
- Tool-use Training；
- Reinforcement Learning；
- Verifiable Rewards；
- 推理时搜索和验证。

### 11.4.2 System-level Planning

系统层负责将模型输出变成可靠计划：

- 计划 Schema；
- Planner；
- Plan Validator；
- Scheduler；
- Executor；
- State Store；
- Verifier；
- Replanner；
- Budget 与 Guardrails。

```mermaid
flowchart TB
    G[Goal + Constraints] --> P[LLM Planner]
    P --> S[Structured Plan]
    S --> V[Plan Validator]
    V -->|不通过| P
    V -->|通过| SCH[Scheduler]
    SCH --> E[Executor]
    E --> O[Observation]
    O --> CHECK{目标或假设变化?}
    CHECK -->|否| SCH
    CHECK -->|是| RP[Replanner]
    RP --> S
```

一个强模型如果缺少 Runtime 和验证，仍可能生成不可执行计划；一个中等模型配合良好 Schema、Tools 和 Verifier，反而可能更可靠。

## 11.5 规划问题的基本元素

可以将一个规划问题抽象为：

- `G`：目标；
- `S₀`：初始状态；
- `A`：可用动作集合；
- `C`：约束；
- `B`：预算；
- `T`：终止条件。

一个动作应声明：

- 前置条件；
- 输入；
- 预期效果；
- 副作用；
- 费用和时间；
- 风险等级；
- 失败方式。

```json
{
  "action": "deploy_service",
  "preconditions": [
    "tests_passed",
    "human_approval_received"
  ],
  "inputs": {
    "service": "payment",
    "version": "v2.4.1"
  },
  "effects": [
    "production_version_updated"
  ],
  "risk_level": "high",
  "timeout_seconds": 600
}
```

如果 Agent 不知道动作前置条件和效果，就很难真正进行可靠规划。

## 11.6 CoT：单路径推理，不是完整规划器

> CoT 的机制、适用任务与解释性局限已在[第五章](05-agent-reasoning-methods.md)详述；这里仅说明它为何不能替代有状态、可验证的规划器。

CoT（Chain of Thought）让模型沿一条中间推理链得到结论：

```mermaid
flowchart LR
    Q[问题] --> S1[步骤 1]
    S1 --> S2[步骤 2]
    S2 --> S3[步骤 N]
    S3 --> A[答案或初步计划]
```

它可以帮助模型：

- 提取约束；
- 分解简单步骤；
- 减少直接跳到答案；
- 生成初步行动列表。

但 CoT 缺少：

- 多路径探索；
- 回溯；
- 真实环境反馈；
- 状态持久化；
- 计划验证；
- 动态重规划；
- 权限和资源调度。

### 11.6.1 工程边界

CoT 会消耗推理预算并占用上下文，但不提供多路径搜索、环境反馈、状态持久化、计划验证或权限调度。规划系统应输出可验证的结构化步骤、依赖、成功标准、工具和风险，而不要求公开隐藏 Thought。其成本与可审计轨迹的记录原则分别见[第五章](05-agent-reasoning-methods.md)和[第十四章](../05-production/14-agent-evaluation.md)。

## 11.7 Task Decomposition：从目标生成子任务

规划的第一步通常是将目标分解为可执行任务。

```mermaid
flowchart TB
    G[复杂目标] --> M1[里程碑 1]
    G --> M2[里程碑 2]
    G --> M3[里程碑 3]
    M1 --> T11[子任务 1.1]
    M1 --> T12[子任务 1.2]
```

高质量子任务应具有：

- 明确目标；
- 独立输入输出；
- 依赖；
- 执行器；
- 验收条件；
- 风险和预算；
- 可重试性。

分解只是产生计划结构，不代表计划正确。还需要验证依赖、可执行性和完整性。

## 11.8 Plan-and-Solve：先形成解题计划

Plan-and-Solve 先生成问题求解计划，再沿计划完成推理。

```text
Plan:
1. 提取目标和约束
2. 识别所需事实
3. 计算中间结果
4. 检查答案是否满足约束
```

它比简单 CoT 更明确地区分：

- Planning；
- Solving。

但它主要仍工作在模型推理层，不一定包含外部 Tool、状态和重规划。

## 11.9 ToT：搜索多个候选方向

ToT（Tree of Thoughts）把中间推理状态组织成树，在每个节点：

1. 生成多个候选；
2. 评价候选；
3. 选择部分候选继续；
4. 必要时回溯。

```mermaid
flowchart TB
    S0[Initial State] --> A[Candidate A]
    S0 --> B[Candidate B]
    S0 --> C[Candidate C]

    A --> A1[Expand A1]
    A --> A2[Expand A2]
    B --> B1[Expand B1]
    B --> B2[Expand B2]

    A1 --> E[Evaluate / Select]
    A2 --> E
    B1 --> E
    B2 --> E
```

ToT 解决的不是“保证纠正错误方向”，而是：

> **允许系统探索多个方向，并在评价函数有效时进行选择和回溯。**

如果候选质量差或 Evaluator 判断错误，ToT 仍可能选择错误路径。

## 11.10 ToT 的成本不能写成固定 3 到 5 倍

ToT 成本取决于：

- 每个节点的分支数 `b`；
- 搜索深度 `d`；
- 保留的 Beam Width `k`；
- 每个节点生成候选的模型调用数；
- Evaluator 调用数；
- 是否批处理；
- 剪枝和提前终止。

完整树节点数为：

$$
N=\sum_{i=0}^{d}b^i
$$

当分支数大于 1 时，节点数可能随深度快速增长。

若使用 Beam Search，每层只保留 `k` 个候选，计算量可以粗略近似为：

$$
N\approx kbd
$$

因此，ToT 可能是 CoT 的数倍，也可能高出一个数量级以上。只有在固定具体分支数、深度、剪枝和模型调用策略后，才能给出倍数。

### 11.10.1 控制 ToT 成本

- 限制搜索深度；
- 限制 Beam Width；
- 批量生成候选；
- 使用小模型初筛；
- 使用规则或程序验证；
- 低分节点提前剪枝；
- 达到置信阈值后停止；
- 只对高风险或高难问题启用。

## 11.11 GoT：合并和复用中间结果

GoT（Graph of Thoughts）允许多个推理路径：

- 分叉；
- 合并；
- 复用；
- 迭代修订；
- 建立依赖。

```mermaid
flowchart LR
    A[Analysis A] --> M[Merge]
    B[Analysis B] --> M
    C[Evidence C] --> M
    M --> R[Refine]
    R --> V[Verify]
    V -->|需要修订| R
    V -->|通过| O[Output]
```

它针对树结构的局限：

- 树中不同分支难以共享中间结果；
- 相同子问题可能被重复计算；
- 多个候选结论无法自然合并。

### 11.11.1 GoT 的生产成熟度

需要区分两个概念：

#### Graph of Thoughts 研究范式

将“Thought”作为图节点，由模型生成、聚合和转换。它仍缺少统一的生产标准和通用实现。

#### Graph-based Agent Orchestration

使用 DAG、状态图、任务图或 Workflow 表示计划，已经广泛用于生产系统。

两者思想相似，但工程系统通常操作的是：

- Task；
- State；
- Artifact；
- Dependency；
- Transition。

而不是不可验证的自由文本 Thought。

> **GoT 研究标签尚未成为统一生产标准，但图结构规划本身已经是成熟工程方法。**

## 11.12 从 Thought Graph 升级为 Task Graph

生产系统更适合把图节点定义为可执行 Task：

```mermaid
flowchart LR
    A[Collect Product Data] --> D[Compare Products]
    B[Collect Pricing Data] --> D
    C[Collect Market Data] --> E[Analyze Market]
    D --> F[Generate Report]
    E --> F
    F --> V[Verify Sources]
```

每个节点应包含：

- 输入；
- 输出；
- 依赖；
- Executor；
- Success Criteria；
- Retry Policy；
- Artifact。

这种图可以被 Scheduler、Verifier 和 Runtime 直接使用。

## 11.13 Planner-Executor-Replanner

赋予 Agent 规划能力最常见的系统架构是：

```mermaid
flowchart TB
    G[Goal] --> P[Planner]
    P --> PLAN[Structured Plan]
    PLAN --> E[Executor]
    E --> O[Observation]
    O --> V{计划仍有效?}
    V -->|是| E
    V -->|否| RP[Replanner]
    RP --> PLAN
    V -->|目标完成| DONE[Finish]
```

### 11.13.1 Planner

负责：

- 理解目标；
- 生成里程碑；
- 拆分任务；
- 建立依赖；
- 指定验收条件；
- 估算风险和资源。

### 11.13.2 Executor

负责：

- 执行当前步骤；
- 调用 Tool；
- 返回真实 Observation；
- 保存 Artifact；
- 报告结构化错误。

### 11.13.3 Replanner

负责判断：

- 结果是否符合预期；
- 哪个假设已经失效；
- 是否需要新增、删除或重排步骤；
- 是否可以提前结束；
- 是否需要人工介入。

## 11.14 动态重规划

原始计划为 `Pₜ`，执行获得新观察 `oₜ₊₁` 后，Replanner 更新计划：

$$
P_{t+1}=R(P_t,o_{t+1},s_t,g)
$$

需要触发重规划的常见事件：

- Tool 返回意外结果；
- 前置假设错误；
- 新约束出现；
- 某个任务失败；
- 预算变化；
- 用户修改目标；
- 外部环境变化；
- Verifier 判断计划无法达到目标。

### 11.14.1 不要每一步都完整重规划

每一步都重写全计划会：

- 增加成本；
- 造成计划漂移；
- 丢失已验证结构；
- 退化为昂贵 ReAct。

更好的方式是：

- 只更新受影响子图；
- 保留已完成节点；
- 对稳定里程碑加锁；
- 记录 Plan Diff；
- 重大假设变化才整体重规划。

## 11.15 Hierarchical Planning

分层规划先确定高层里程碑，再按需展开当前阶段：

```mermaid
flowchart TB
    G[Global Goal] --> M1[Research]
    G --> M2[Implementation]
    G --> M3[Validation]

    M1 --> T11[Search Sources]
    M1 --> T12[Extract Facts]

    M2 --> T21[Design]
    M2 --> T22[Code]

    M3 --> T31[Test]
    M3 --> T32[Review]
```

优势：

- 保留全局方向；
- 避免一次生成过长计划；
- 降低远期计划失效；
- 支持阶段预算；
- 适合长任务。

## 11.16 Rolling Horizon Planning

滚动规划只详细规划近期步骤：

```mermaid
flowchart LR
    S[Current State] --> P[Plan Next Horizon]
    P --> E[Execute Next Step]
    E --> O[Observe]
    O --> U[Update State]
    U --> P
```

适合：

- 环境变化快；
- 远期信息不可靠；
- 工具结果决定后续路径；
- 任务可能随时被用户调整。

它在全局计划和 ReAct 之间提供平衡。

## 11.17 ReAct 在规划中的作用

ReAct 不是完整全局规划器，但适合执行计划中的局部开放任务：

```mermaid
flowchart TB
    P[Global Plan] --> S[Current Step]
    S --> O[Observe]
    O --> D[Decide]
    D --> A[Act]
    A --> O
    D -->|局部完成| NEXT[Next Plan Step]
```

推荐组合：

- Planner 负责全局结构；
- ReAct 负责局部 Tool 选择；
- Replanner 处理计划失效；
- Verifier 检查步骤结果。

## 11.18 Reflection 与规划质量

Reflection 可以在规划前后加入质量检查。

### 11.18.1 Plan Critique

检查：

- 是否遗漏步骤；
- 依赖是否正确；
- 是否可执行；
- 是否存在权限问题；
- 是否定义成功条件；
- 是否存在更低成本路径。

### 11.18.2 Execution Reflection

根据执行结果检查：

- 哪个步骤失败；
- 原因是计划错误还是执行错误；
- 是否需要改变策略；
- 哪些经验可以用于后续规划。

```mermaid
flowchart LR
    P[Plan] --> C[Critic]
    C --> V{Plan Valid?}
    V -->|否| R[Revise]
    R --> P
    V -->|是| E[Execute]
    E --> F[Feedback]
    F --> C
```

Reflection 应优先使用真实工具反馈、规则、测试和人工审核，而不是只让同一个模型自我评价。

## 11.19 Verifier-guided Planning

一个计划只有通过以下检查后才执行：

### 11.19.1 Schema Validation

- 字段完整；
- 类型正确；
- 引用的 Task 存在；
- 输出格式合法。

### 11.19.2 Dependency Validation

- 不存在循环；
- 所需输入有来源；
- 前置条件可满足；
- 并行任务没有写冲突。

### 11.19.3 Capability Validation

- 指定 Tool 存在；
- Agent 拥有所需 Skill；
- 权限足够；
- 参数可以生成。

### 11.19.4 Risk Validation

- 高风险操作是否有审批；
- 是否使用最小权限；
- 是否定义回滚或补偿；
- 是否触及敏感数据。

### 11.19.5 Budget Validation

- Token；
- 时间；
- 费用；
- 最大步骤；
- 并发限制。

```mermaid
flowchart LR
    PLAN[Candidate Plan] --> S[Schema]
    S --> D[Dependencies]
    D --> C[Capabilities]
    C --> R[Risk]
    R --> B[Budget]
    B --> EXEC[Executable Plan]
```

## 11.20 使用外部规划器

并非所有规划都应交给 LLM。

### 11.20.1 Deterministic Workflow

流程已知时直接使用代码、DAG 或状态机。

### 11.20.2 Constraint Solver

适合：

- 排班；
- 资源分配；
- 路径约束；
- 组合优化；
- 满足严格规则的问题。

### 11.20.3 Classical Planner

当动作具有清晰前置条件和效果时，可以使用经典规划算法。

### 11.20.4 LLM + Solver

LLM 负责：

- 理解自然语言目标；
- 提取约束；
- 生成 Solver 输入；
- 解释结果。

Solver 负责：

- 精确搜索；
- 约束满足；
- 最优性判断。

```mermaid
sequenceDiagram
    participant U as User
    participant M as LLM
    participant S as Solver
    participant R as Runtime

    U->>M: 自然语言目标
    M-->>R: 结构化目标与约束
    R->>S: 求解
    S-->>R: 可行计划
    R->>M: 计划与约束结果
    M-->>U: 解释或执行计划
```

> **能由确定性算法可靠解决的规划问题，不应完全依赖语言模型搜索。**

## 11.21 计划的表示方式

### 11.21.1 Natural Language List

简单直观，但难以验证和调度。

### 11.21.2 Structured JSON

适合任务管理和 API 集成：

```json
{
  "plan_id": "plan-42",
  "goal": "发布新版本",
  "tasks": [
    {
      "id": "test",
      "depends_on": [],
      "executor": "test-tool",
      "success_criteria": ["all tests pass"]
    },
    {
      "id": "deploy",
      "depends_on": ["test", "approval"],
      "executor": "deployment-agent",
      "success_criteria": ["health checks pass"]
    }
  ]
}
```

### 11.21.3 DAG

适合依赖和并行调度。

### 11.21.4 State Machine

适合状态有限、转移规则明确的业务流程。

### 11.21.5 Policy

不生成固定步骤，而是根据状态选择下一动作，适合动态环境。

## 11.22 计划粒度

计划过粗：

- 无法执行；
- 无法验证；
- 失败影响范围大。

计划过细：

- 调度成本高；
- 模型调用过多；
- 状态碎片化；
- 容易丢失全局目标。

合理任务单元应：

- 独立执行；
- 独立验证；
- 独立重试；
- 输入输出明确；
- 副作用有边界；
- 产生有意义 Artifact。

## 11.23 Planning Memory

规划需要记住：

- 当前目标；
- 已完成步骤；
- 计划版本；
- 关键假设；
- Observation；
- 失败和重试；
- 未解决问题；
- 预算。

```mermaid
flowchart TB
    PLAN[Plan] --> STATE[Planning State]
    OBS[Observations] --> STATE
    FAIL[Failures] --> STATE
    BUDGET[Budget] --> STATE
    STATE --> RP[Replanner]
```

计划不能只存在于一次 Prompt 中，应保存在结构化 State Store 并支持 Checkpoint。

## 11.24 World Model

规划需要估计动作会如何改变环境。这个预测模型称为 World Model。

LLM 可以隐式预测：

- 调用 Tool 后可能得到什么；
- 某个动作是否满足前置条件；
- 下一步会产生什么副作用。

但高风险场景不应只相信语言模型预测，应使用：

- API Schema；
- 模拟器；
- 测试环境；
- 数字孪生；
- 规则引擎；
- 真实只读查询。

World Model 越准确，计划越可靠。

## 11.25 规划中的不确定性

计划应区分：

- 已知事实；
- 假设；
- 不确定信息；
- 必须通过 Tool 验证的条件。

```json
{
  "assumption": "竞品 A 仍提供免费版本",
  "confidence": 0.6,
  "verification_task": "check-current-pricing",
  "on_failure": "revise-comparison-plan"
}
```

低置信假设应尽早验证，避免后续大量步骤建立在错误基础上。

## 11.26 风险感知规划

不同动作需要不同控制：

| 风险 | 示例 | 规划策略 |
|---|---|---|
| 低 | 搜索公开网页 | 可自动执行 |
| 中 | 修改本地代码 | 保留 Diff 和回滚 |
| 高 | 发邮件、发布内容 | 执行前确认 |
| 极高 | 转账、删库、改权限 | 强认证、审批和最小权限 |

规划器应优先选择：

- 可逆动作；
- 只读探测；
- 最小副作用；
- 可验证中间步骤；
- 明确回滚路径。

## 11.27 规划预算

规划系统需要限制：

$$
B=(N,D,K,T,C)
$$

其中：

- `N`：候选计划数量；
- `D`：搜索深度；
- `K`：重规划次数；
- `T`：最大时间；
- `C`：最大费用。

预算策略可以是：

- 简单任务只生成一个计划；
- 中等任务生成计划并做一次 Critique；
- 高风险任务生成多个候选并使用 Verifier；
- 预算耗尽时返回部分计划和未解决风险。

## 11.28 Adaptive Planning

Adaptive Planner 根据任务难度和风险选择规划强度：

```mermaid
flowchart TB
    G[Goal] --> A[Assess Complexity / Risk]
    A -->|简单| C[CoT / Checklist]
    A -->|路径明确| W[Workflow]
    A -->|复杂但可分解| P[Plan-and-Execute]
    A -->|候选较多| T[ToT / Search]
    A -->|严格约束| S[External Solver]
    A -->|动态环境| R[Rolling Replanning]
```

这比所有任务都运行昂贵搜索更高效。

## 11.29 规划能力的训练方式

### 11.29.1 In-context Examples

提供高质量计划示例，包括依赖、成功标准和失败处理。

### 11.29.2 Supervised Fine-tuning

使用目标到计划、状态到下一动作的轨迹训练模型。

### 11.29.3 Tool-use Training

训练模型理解 Tool Schema、参数和 Observation。

### 11.29.4 Reinforcement Learning

根据任务成功、成本、风险和步骤效率优化策略。

### 11.29.5 Verifiable Rewards

使用测试、模拟器、规则和环境结果提供可验证反馈。

### 11.29.6 Curriculum

从短计划逐步训练到长任务和动态环境。

训练可以增强模型能力，但系统仍需要 Runtime、State、Verifier 和 Guardrails。

## 11.30 规划质量如何评估

| 指标 | 含义 |
|---|---|
| Goal Completion | 最终是否完成目标 |
| Plan Validity | 计划结构是否合法 |
| Executability | 步骤是否可以实际执行 |
| Completeness | 是否覆盖必要步骤 |
| Dependency Accuracy | 依赖是否正确 |
| Replan Rate | 计划失效频率 |
| Step Efficiency | 是否存在冗余步骤 |
| Recovery | 失败后是否能局部恢复 |
| Cost | 规划和执行成本 |
| Safety | 是否遵守权限和风险约束 |

还需要与基线比较：

- 单次 LLM；
- ReAct；
- 固定 Workflow；
- Plan-and-Execute；
- Search-based Planner。

只有当规划提高任务成功率或降低总体成本时，增加复杂度才合理。

## 11.31 常见失败模式

### 11.31.1 计划看起来完整但不可执行

原因：

- Tool 不存在；
- 参数无法获得；
- 权限不足；
- 步骤输出没有被后续消费。

### 11.31.2 计划遗漏隐含依赖

例如部署前忘记测试或审批。

### 11.31.3 Planner 产生过多微任务

调度和通信成本超过收益。

### 11.31.4 初始假设错误

后续所有步骤建立在错误方向上。

### 11.31.5 频繁完整重规划

产生 Plan Drift 和成本膨胀。

### 11.31.6 Planner 与 Executor 语义不一致

Executor 不理解步骤目标或输出格式。

### 11.31.7 自我评价取代真实验证

计划逻辑看似合理，但无法通过环境测试。

### 11.31.8 没有停止条件

不断拆分、搜索和重规划。

## 11.32 推荐的生产架构

```mermaid
flowchart TB
    INPUT[User Goal] --> NORMALIZE[Goal / Constraint Parser]
    NORMALIZE --> ROUTER[Planning Strategy Router]

    ROUTER -->|固定流程| WF[Workflow]
    ROUTER -->|动态任务| PLANNER[LLM Planner]
    ROUTER -->|严格约束| SOLVER[External Solver]

    PLANNER --> PLAN[Structured Plan / DAG]
    SOLVER --> PLAN
    WF --> PLAN

    PLAN --> VALIDATE[Schema + Dependency + Risk Validation]
    VALIDATE -->|不通过| PLANNER
    VALIDATE -->|通过| SCHED[Scheduler]

    SCHED --> EXEC[Executor / ReAct]
    EXEC --> OBS[Observation + Artifact]
    OBS --> VERIFY[Verifier]

    VERIFY -->|步骤通过| SCHED
    VERIFY -->|局部失败| EXEC
    VERIFY -->|计划失效| REPLAN[Replanner]
    REPLAN --> PLAN
    VERIFY -->|高风险| HUMAN[Human Approval]
    VERIFY -->|目标完成| DONE[Final Result]

    PLAN --> STATE[Planning State Store]
    OBS --> STATE
    STATE --> REPLAN
```

## 11.33 实现步骤

### 11.33.1 定义目标与成功标准

不要只传入模糊目标。

### 11.33.2 建立 Action Catalog

为每个动作定义前置条件、效果、风险和成本。

### 11.33.3 定义 Plan Schema

让计划可以被程序验证和调度。

### 11.33.4 添加 Plan Validator

检查依赖、能力、权限和预算。

### 11.33.5 执行并保存 Observation

只使用真实 Tool Result 更新状态。

### 11.33.6 添加 Replanner

定义明确的触发条件和最大重规划次数。

### 11.33.7 添加 Verifier

优先使用测试、规则、模拟器和真实环境。

### 11.33.8 加入 Guardrails

限制步骤、时间、费用、权限和副作用。

### 11.33.9 建立评估集

测量成功率、成本、延迟和恢复能力。

## 11.34 选型表

| 场景 | 推荐方案 |
|---|---|
| 简单线性问题 | Direct / CoT |
| 需要先分解再求解 | Plan-and-Solve |
| 候选方向较多且可评价 | ToT |
| 中间结果需要合并复用 | Task Graph / DAG |
| 长任务且环境变化 | Rolling Replanning |
| 路径固定 | Workflow |
| 严格约束优化 | External Solver |
| 全局计划 + 局部探索 | Planner + ReAct |
| 高质量要求 | Planner + Verifier + Reflection |

## 11.35 本章总结

赋予 LLM 规划能力不能只靠一句“请一步步思考”。

### 11.35.1 模型层

- CoT 提供单路径中间推理；
- Task Decomposition 生成子问题；
- ToT 搜索多个候选方向；
- GoT 允许合并和复用中间结果；
- 训练和 Verifiable Reward 可以增强规划能力。

### 11.35.2 系统层

- 用 Plan Schema 表达可执行任务；
- 用 Validator 检查依赖、能力和风险；
- 用 Scheduler 与 Executor 执行；
- 用 Observation 更新真实状态；
- 用 Replanner 动态修改计划；
- 用 Verifier 和 Guardrails 保证质量与安全。

最重要的原则是：

> **规划不是把思维过程写得更长，而是把目标转化为可执行、可验证、可更新并受预算约束的行动结构。**

## 参考资料

- [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903)
- [Tree of Thoughts: Deliberate Problem Solving with Large Language Models](https://arxiv.org/abs/2305.10601)
- [Graph of Thoughts: Solving Elaborate Problems with Large Language Models](https://arxiv.org/abs/2308.09687)
- [Plan-and-Solve Prompting](https://arxiv.org/abs/2305.04091)
- [LLMCompiler: An LLM Compiler for Parallel Function Calling](https://arxiv.org/abs/2312.04511)
- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
