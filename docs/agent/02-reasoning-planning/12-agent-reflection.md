# 第十二章：Agent 的反思、验证与自我改进

## 12.1 什么是 Agent Reflection

Agent Reflection 更接近一套反馈驱动的控制机制，而不是抽象的“自省”：

> **生成或执行 → 评价 → 定位问题 → 定向修订 → 再验证**

```mermaid
flowchart LR
    G[Generate / Execute] --> E[Evaluate]
    E --> D{满足标准?}
    D -->|是| DONE[Finish]
    D -->|否| F[Structured Feedback]
    F --> R[Refine / Retry / Replan]
    R --> G
```

反思要起作用，前提是系统拿到了新的反馈。反馈可以来自：

- Tool Result；
- 编译器；
- 单元测试；
- Schema；
- 规则；
- 模拟器；
- 权威数据；
- 人工审核；
- Critic Model；
- LLM-as-a-Judge。

如果没有新的证据或评价标准，让同一个模型重复生成可能只会得到另一个同样不可靠的答案。

## 12.2 为什么需要反思

### 12.2.1 发现生成阶段遗漏的问题

模型生成内容时主要关注“完成任务”，不一定同时覆盖：

- 事实正确性；
- 约束完整性；
- 引用一致性；
- 安全要求；
- 输出格式；
- 边界条件。

单独评价阶段可以把注意力集中到这些维度。

### 12.2.2 阻止错误继续传播

在强依赖任务中，早期错误可能成为后续步骤的输入：

```mermaid
flowchart LR
    A[错误搜索词] --> B[错误资料]
    B --> C[错误分析]
    C --> D[错误结论]
```

如果在关键节点验证：

```mermaid
flowchart LR
    A[搜索结果] --> V{来源与相关性通过?}
    V -->|是| B[继续分析]
    V -->|否| R[修改查询并重试]
```

就能降低错误复合。

### 12.2.3 改善一次难以完成的高质量输出

适合：

- 代码生成；
- 研究报告；
- 翻译；
- 法律或商业文本；
- 复杂数据分析；
- 有明确评分标准的内容生成。

### 12.2.4 将失败转化为可复用经验

经过验证的失败原因可以：

- 改善当前重试；
- 更新当前任务计划；
- 形成 Episode；
- 晋升为长期记忆；
- 转化为 Skill、规则或测试。

未经验证的反思不应直接成为长期规则。

## 12.3 Reflection 与 Verification 的区别

| Reflection | Verification |
|---|---|
| 解释哪里可能有问题及如何改 | 判断是否满足明确标准 |
| 通常由模型生成反馈 | 可以由程序、规则、环境或人执行 |
| 可能具有主观性 | 越接近真实环境越客观 |
| 用于指导修订 | 用于接受、拒绝或阻止 |

更稳妥的做法是让 Verification 判断问题是否成立，再由 Reflection 把这些问题转成可执行的修订动作。

例如：

- 单元测试指出函数在空输入时失败；
- Critic 将失败归纳为“缺少空输入分支”；
- Refiner 修改代码；
- 测试再次验证。

## 12.4 Verifier 的优先级

当多种反馈可用时，通常优先：

1. 真实环境结果；
2. 编译器、测试和约束求解器；
3. Schema 与确定性规则；
4. 权威数据源；
5. 人工审核；
6. 专用 Reward Model；
7. 独立 LLM Judge；
8. 同一模型自我评价。

```mermaid
flowchart TB
    RESULT[Candidate Result] --> DET[Deterministic Verifier]
    DET -->|可验证| DECISION[Pass / Fail]
    DET -->|无法完全验证| HUMAN[Human or Domain Review]
    HUMAN -->|仍需辅助| JUDGE[LLM Judge]
```

语言模型评价适合处理难以完全形式化的质量维度，但不应替代可用的客观验证。

## 12.5 反思的四种触发粒度

除了步骤级和任务级，还可以加入里程碑级与跨任务 Consolidation。

```mermaid
flowchart TB
    R[Reflection Granularity] --> S[Step-level]
    R --> M[Milestone-level]
    R --> T[Task-level]
    R --> C[Cross-task Consolidation]
```

## 12.6 Step-level Reflection

Step-level Reflection 在 Tool Call、推理步骤或状态转移后检查结果。

```mermaid
flowchart LR
    S[Execute Step] --> O[Observation]
    O --> V{Step Valid?}
    V -->|是| N[Next Step]
    V -->|否| F[Feedback]
    F --> R[Retry or Replan]
    R --> S
```

### 12.6.1 适用场景

- 步骤之间强依赖；
- 早期错误会影响大量后续工作；
- Tool 结果容易验证；
- 操作具有高风险或副作用；
- 局部重试成本较低。

例如：

- 搜索结果是否与问题相关；
- API 是否返回成功状态；
- 代码是否通过编译；
- 数据是否满足 Schema；
- 高风险操作是否经过审批。

### 12.6.2 优势

- 错误发现早；
- 失败影响范围小；
- 可以局部重试；
- 状态更容易保持正确；
- 适合强依赖任务。

### 12.6.3 代价

- 增加验证延迟；
- 增加模型或 Tool 调用；
- 可能过度检查低风险步骤；
- Critic 可能不断提出非关键修改；
- 任务吞吐下降。

### 12.6.4 不一定每步增加一次 LLM 调用

“十步任务加步骤级反思就需要二十次 LLM 调用”不是必然规律。

步骤验证可以由：

- Tool 自身状态码；
- Schema Validator；
- 单元测试；
- 规则引擎；
- 当前 Agent 的下一轮决策；
- 批量 Critic；
- 只在异常时触发的模型评价。

只有在每个步骤都单独调用 LLM Critic 时，调用次数才可能接近翻倍。

## 12.7 Milestone-level Reflection

Milestone-level Reflection 在一个阶段完成后评价，而不是检查每个微步骤。

```mermaid
flowchart LR
    S1[Stage Steps] --> M[Milestone Artifact]
    M --> V{Milestone Valid?}
    V -->|是| NEXT[Next Milestone]
    V -->|否| FIX[Repair Affected Stage]
```

这种做法的成本低于逐步检查，也比只看最终结果更容易尽早发现偏差。

适合：

- 一个阶段内部步骤较多；
- 阶段能产生独立 Artifact；
- 每步验证过于昂贵；
- 阶段之间依赖明显。

例如：

- 资料收集完成后统一检查来源覆盖；
- 功能实现完成后运行整组测试；
- 报告提纲完成后检查结构。

## 12.8 Task-level Reflection

Task-level Reflection 在完整任务结束后进行整体评价。

```mermaid
flowchart LR
    TASK[Complete Task] --> OUT[Final Candidate]
    OUT --> E[Holistic Evaluation]
    E --> D{Pass?}
    D -->|是| DONE[Deliver]
    D -->|否| R[Revise Result or Replan]
```

### 12.8.1 适用场景

- 步骤相对独立；
- 单步错误影响有限；
- 更关注整体一致性；
- 最终结果容易统一评价；
- 中间验证成本较高。

例如：

- 报告结构和结论是否一致；
- 文案风格是否统一；
- 多章节是否重复或矛盾；
- 最终方案是否满足全部要求。

### 12.8.2 优势

- 额外调用较少；
- 能观察全局一致性；
- 适合发现跨部分问题；
- 实现简单。

### 12.8.3 代价

- 错误发现晚；
- 可能浪费前期执行成本；
- 很难只修复一个局部；
- 根因可能被最终输出掩盖。

## 12.9 Cross-task Consolidation

跨任务反思更像一次复盘，重点是总结：

- 哪种策略有效；
- 哪种错误反复出现；
- 哪些规则值得长期保留；
- 哪些 Tool 或 Prompt 需要改进。

```mermaid
flowchart LR
    T1[Task 1] --> C[Consolidation]
    T2[Task 2] --> C
    T3[Task N] --> C
    C --> M[Validated Memory]
    C --> S[Skill / Workflow Update]
    C --> E[Evaluation Set]
```

跨任务经验必须经过验证、去重和适用范围检查，不能把模型的一次自我评价自动提升为永久规则。

## 12.10 如何选择反思粒度

| 任务特征 | 推荐粒度 |
|---|---|
| 强依赖、错误会层层传播 | Step-level |
| 阶段有独立输出 | Milestone-level |
| 各步骤相对独立，关注整体质量 | Task-level |
| 需要积累重复任务经验 | Cross-task Consolidation |
| 高风险动作 | Step-level + Human Gate |
| 成本敏感 | Triggered Milestone / Task-level |

生产系统通常混合使用：

```mermaid
flowchart TB
    STEP[Low-risk Steps] --> MILESTONE[Milestone Verification]
    RISK[High-risk Step] --> IMMEDIATE[Immediate Verification]
    MILESTONE --> TASK[Task-level Review]
    IMMEDIATE --> TASK
    TASK --> CONS[Optional Consolidation]
```

## 12.11 Adaptive Reflection

不必在每一步都反思。可以根据风险和异常动态触发。

触发信号包括：

- Tool 返回错误；
- 输出不符合 Schema；
- 置信度低；
- 多个来源冲突；
- 重复调用同一 Tool；
- 计划偏离目标；
- 即将执行高风险动作；
- 阶段耗时或成本异常；
- Verifier 分数低。

```mermaid
flowchart LR
    O[Observation] --> R[Risk / Anomaly Detector]
    R -->|正常| NEXT[Continue]
    R -->|异常| REFLECT[Reflect / Verify]
    REFLECT --> FIX[Repair / Replan]
```

相比固定“每一步一次 Critic”，自适应触发通常更容易把成本控制住。

## 12.12 反思系统的基本组件

一个完整实现通常包含：

1. Generator / Executor；
2. Verifier / Critic；
3. Feedback Formatter；
4. Refiner；
5. Stop Controller；
6. Optional Memory Writer。

```mermaid
flowchart TB
    G[Generator / Executor] --> A[Artifact + Trace]
    A --> V[Verifier / Critic]
    V --> F[Structured Feedback]
    F --> R[Refiner]
    R --> G
    V --> S[Stop Controller]
    S -->|Pass| DONE[Finish]
    S -->|Budget Exhausted| PARTIAL[Report Incomplete]
    F --> MW[Optional Memory Writer]
```

## 12.13 Evaluate 与 Refine 必须职责分离

反思至少需要两个逻辑阶段：

### 12.13.1 Evaluate

只负责：

- 对照标准检查；
- 找出具体问题；
- 提供证据；
- 判断严重程度；
- 给出可操作建议。

### 12.13.2 Refine

负责：

- 读取原始任务；
- 读取原始输出；
- 读取结构化反馈；
- 定向修改；
- 保留正确内容；
- 返回可再次验证的结果。

这两个角色可以由：

- 两个不同 Prompt；
- 两次模型调用；
- 不同模型；
- LLM + 确定性验证器；
- 同一 Agent 的不同 Workflow 节点；

实现。

重点是职责和输入输出边界，而不是必须恰好存在两个 Prompt 文件。

## 12.14 Critic Prompt 应包含什么

### 12.14.1 原始任务与成功标准

Critic 必须知道什么才算完成。

### 12.14.2 具体检查维度

例如：

- Correctness；
- Completeness；
- Evidence；
- Consistency；
- Safety；
- Format；
- Efficiency。

### 12.14.3 可验证证据

要求每个 Finding 引用：

- 输出片段；
- Tool Result；
- 测试；
- 来源；
- 明确规则。

### 12.14.4 PASS 出口

如果结果已经满足要求，Critic 必须能够返回 PASS。否则它会为了完成“找问题”的指令不断制造低价值意见。

### 12.14.5 结构化输出

```json
{
  "verdict": "REVISE",
  "score": 0.78,
  "findings": [
    {
      "criterion": "evidence",
      "severity": "high",
      "location": "section-3",
      "problem": "关键市场份额结论没有来源",
      "evidence": "报告第 3 节第 2 段",
      "suggestion": "补充权威来源，或删除该具体数字"
    }
  ],
  "next_action": "revise"
}
```

允许的 Verdict 可以是：

- `PASS`；
- `REVISE`；
- `REPLAN`；
- `BLOCKED`；
- `NEEDS_HUMAN_REVIEW`。

## 12.15 Refiner Prompt 应包含什么

Refiner 需要：

- 原始任务；
- 当前候选；
- Critic Findings；
- 不可改变的约束；
- 允许修改的范围；
- 输出 Schema。

推荐要求：

1. 只处理有效 Finding；
2. 保留已经正确的部分；
3. 不引入无来源新事实；
4. 返回修改后的完整 Artifact 或明确 Patch；
5. 说明哪些 Finding 无法解决。

不要只说“请根据意见优化一下”，否则修改方向不稳定。

## 12.16 Stop Controller

不能依赖模型自己无限反思直到满意。

停止条件包括：

- Verifier 返回 PASS；
- 达到最低分数；
- 达到最大轮数；
- Token 或费用预算耗尽；
- 超时；
- 连续多轮没有显著改善；
- 相同 Finding 重复出现；
- 需要人工判断；
- 用户取消。

设第 `r` 轮评分为 `sᵣ`，改进量为：

$$
\Delta_r=s_r-s_{r-1}
$$

如果连续若干轮满足：

$$
\Delta_r\le\epsilon
$$

可以判定优化已经停滞。

### 12.16.1 最大轮数不是固定 2 到 3

一到三轮是很多低风险文本任务的常见默认范围，但不应写成普适规则。

轮数应根据：

- 单轮成本；
- 任务风险；
- Verifier 可靠性；
- 每轮平均提升；
- 用户延迟目标；
- 是否存在确定性成功条件；

通过评估确定。

高风险操作可能只允许一次修订后转人工；可自动测试的代码修复则可能允许更多受限迭代。

## 12.17 反思成本

若每轮包含 Evaluate、Refine 和 Verify，总成本可表示为：

$$
C_{reflection}=
\sum_{r=1}^{R}
\left(
C_{eval,r}
+
C_{refine,r}
+
C_{verify,r}
\right)
$$

成本还包括：

- Tool 执行；
- 测试；
- Context；
- Critic Agent 通信；
- Artifact 存储；
- 人工审核。

降低成本的方法：

- 只在异常或高风险时触发；
- 使用确定性验证器；
- 用小模型初筛；
- 批量检查多个步骤；
- 在 Milestone 而非每个微步骤反思；
- 达到阈值立即停止；
- 只修复受影响部分。

## 12.18 Self-Reflection

Self-Reflection 使用同一模型或同一 Agent 评价自己的结果。

### 12.18.1 优势

- 实现简单；
- 无需额外 Agent；
- Context 传递成本低；
- 适合低风险初步检查。

### 12.18.2 局限

- Generator 与 Critic 共享模型偏差；
- 容易重复原来的假设；
- 可能偏好自己的表达；
- 缺少真正的新证据；
- 可能产生表面修改。

Self-Reflection 可以作为初筛，但不能当成客观验证。

## 12.19 Critic Agent

Critic Agent 专门检查 Executor 的 Artifact 或轨迹。

```mermaid
sequenceDiagram
    participant E as Executor Agent
    participant C as Critic Agent
    participant V as Verifier

    E->>C: Candidate + Rubric + Evidence
    C-->>E: Structured Findings
    E->>E: Refine
    E->>V: Revised Candidate
    V-->>E: Pass or Fail
```

### 12.19.1 为什么可能更好

- Critic 使用独立 Prompt；
- Critic 不承担生成任务；
- 可以隐藏 Generator 的解释，减少 Anchoring；
- 可以使用不同模型和 Tools；
- 可以只关注某个质量维度；
- 可以访问独立验证数据。

### 12.19.2 为什么不一定更客观

如果 Critic：

- 使用相同模型；
- 看到相同上下文；
- 使用模糊 Rubric；
- 没有外部证据；
- 只被要求“找问题”；

它仍可能与 Generator 共享错误，或为了批评而批评。

> **拆成独立 Critic Agent，不会自动带来独立证据，也不会自动消除共享误差。**

提高独立性的方式：

- 使用不同模型或模型版本；
- 使用不同数据源；
- Blind Review；
- 明确 Rubric；
- 提供测试和事实来源；
- 对 Critic 本身做评估。

## 12.20 Multi-Critic

可以让多个 Critic 分别检查：

- 事实；
- 安全；
- 逻辑；
- 格式；
- 领域合规。

```mermaid
flowchart TB
    OUT[Candidate] --> F[Fact Critic]
    OUT --> S[Safety Critic]
    OUT --> L[Logic Critic]
    OUT --> D[Domain Critic]
    F --> J[Finding Aggregator]
    S --> J
    L --> J
    D --> J
```

优势：

- 每个 Critic 更聚焦；
- 可以并行；
- 权限和数据隔离更清晰。

代价：

- 成本增加；
- Findings 可能冲突；
- 需要聚合和优先级；
- 多个相同模型仍可能共享偏差。

## 12.21 Debate

Debate 让多个 Agent 对候选方案进行对抗式讨论。

```mermaid
flowchart LR
    P[Proposer] --> O[Opponent]
    O --> R[Rebuttal]
    R --> J[Judge / Verifier]
    J --> D{通过?}
    D -->|否| P
    D -->|是| OUT[Final Decision]
```

适合：

- 存在多个合理观点；
- 需要暴露假设；
- 需要风险分析；
- 结论无法完全用确定性规则验证。

### 12.21.1 Debate 的风险

- 更善辩不等于更正确；
- Judge 可能偏好表达方式；
- Agent 可能共享相同知识盲区；
- 讨论可能循环；
- Token 和延迟成本高；
- 对事实问题不应以投票替代数据。

关键商业或法律决策仍需要权威事实、领域专家和明确责任人。

## 12.22 Self-Refine

Self-Refine 的基本流程是：

> **Generate → Feedback → Refine**

```mermaid
flowchart LR
    G[Generate] --> F[Self Feedback]
    F --> R[Refine]
    R --> V{Pass?}
    V -->|否| F
    V -->|是| OUT[Output]
```

它主要优化当前候选，不修改模型权重。

适合：

- 文本质量优化；
- 格式修正；
- 有 Rubric 的生成任务；
- 低风险迭代。

## 12.23 Reflexion

Reflexion 将环境反馈转化为自然语言反思，并保存在 Episodic Memory 中，供后续尝试使用。

经典组件包括：

- Actor；
- Evaluator；
- Self-Reflection；
- Episodic Memory。

```mermaid
flowchart TB
    A[Actor] --> ENV[Environment]
    ENV --> TRAJ[Trajectory + Reward]
    TRAJ --> E[Evaluator]
    E --> D{Success?}
    D -->|是| DONE[Finish]
    D -->|否| SR[Self-Reflection]
    SR --> MEM[Episodic Memory]
    MEM --> A
```

### 12.23.1 原始 Reflexion 的记忆范围

原始方法重点是在同一任务的多次 Trial 之间保留 verbal reflection，从而让下一次尝试避免重复错误。

它不要求：

- 必须使用 Vector DB；
- 必须进行跨任务语义检索；
- 自动把所有经验永久保存。

生产系统可以扩展为跨任务记忆，但需要：

- 经验验证；
- 适用范围；
- 去重；
- 来源；
- 相似任务检索；
- 过期和删除策略。

### 12.23.2 从 Reflection 晋升为 Skill

如果一条经验：

- 多次验证有效；
- 具有跨任务价值；
- 适用范围明确；
- 不包含敏感信息；

可以晋升为：

- Skill；
- Workflow；
- Rule；
- Test；
- Runbook。

## 12.24 LATS

LATS（Language Agent Tree Search）将：

- Tree Search；
- Action；
- Environment Feedback；
- Value Evaluation；
- Reflection；

结合在同一个搜索过程。

```mermaid
flowchart TB
    ROOT[Current State] --> A[Action A]
    ROOT --> B[Action B]
    ROOT --> C[Action C]

    A --> OA[Observation A]
    B --> OB[Observation B]
    C --> OC[Observation C]

    OA --> VA[Value + Reflection]
    OB --> VB[Value + Reflection]
    OC --> VC[Value + Reflection]

    VA --> SELECT[Tree Policy]
    VB --> SELECT
    VC --> SELECT
    SELECT --> EXPAND[Expand Promising Path]
```

### 12.24.1 核心价值

- 同时探索多个行动路径；
- 使用环境反馈评价路径；
- 从失败轨迹中提取反思；
- 将评价用于后续搜索。

### 12.24.2 成本

成本取决于：

- 分支数；
- 搜索深度；
- Rollout 数；
- Value Evaluation；
- Reflection 调用；
- Tool 执行。

它可能远高于线性 ReAct 或简单 Reflection，不能用固定倍数概括。

### 12.24.3 工程定位

LATS 是重要的研究型架构，其思想可以用于：

- 候选方案搜索；
- 代码修复；
- 可模拟环境；
- 高价值决策辅助。

但完整 MCTS + Reflection 通常不是普通生产请求的默认方案。生产系统更常采用受预算限制的 Beam Search、Best-of-N、Verifier 和局部重试。

## 12.25 反思与规划的关系

Reflection 可以作用于不同对象：

```mermaid
flowchart TB
    R[Reflection] --> OUT[Output Reflection]
    R --> STEP[Step Reflection]
    R --> PLAN[Plan Reflection]
    R --> TRACE[Trajectory Reflection]
    R --> MEMORY[Memory Reflection]
```

- Output Reflection：结果是否正确；
- Step Reflection：当前步骤是否有效；
- Plan Reflection：计划是否仍适用；
- Trajectory Reflection：整条执行路径是否合理；
- Memory Reflection：哪些经验值得保留。

Plan-and-Execute 中，反思结果可能触发 Replanner，而不仅是重写当前答案。

## 12.26 反思与 Agentic Workflow

生产系统通常将反思限制在 Workflow 节点中：

```mermaid
flowchart LR
    IN[Input] --> G[Generate]
    G --> DET[Deterministic Checks]
    DET -->|通过| C[Critic]
    DET -->|失败| FIX[Direct Repair]
    C --> D{Verdict}
    D -->|PASS| OUT[Output]
    D -->|REVISE| R[Refiner]
    D -->|REPLAN| P[Planner]
    D -->|HUMAN| H[Human Review]
    R --> DET
    P --> G
```

Workflow 负责：

- 最大轮数；
- 允许的 Verdict；
- 权限；
- 预算；
- 人工审批；
- 最终停止。

LLM 负责：

- 找出难以形式化的问题；
- 生成具体反馈；
- 定向修订。

## 12.27 代码 Agent 示例

目标：

> 修复一个导致空输入崩溃的函数。

```mermaid
flowchart TB
    G[Generate Patch] --> T[Run Tests]
    T --> D{Tests Pass?}
    D -->|是| R[Code Review]
    D -->|否| F[Extract Failure]
    F --> REF[Reflect on Root Cause]
    REF --> G
    R --> Q{Review Pass?}
    Q -->|是| DONE[Finish]
    Q -->|否| G
```

关键点：

- Test 是 Verifier；
- 测试失败提供新证据；
- Reflection 总结根因；
- Refiner 修改 Patch；
- 最大尝试次数由 Runtime 控制；
- 测试通过后仍需 Review 检查未覆盖风险。

## 12.28 研究报告示例

### 12.28.1 Step-level

- 搜索结果是否相关；
- 来源是否可信；
- 关键数字是否来自原文。

### 12.28.2 Milestone-level

- 每个竞品是否覆盖相同维度；
- 是否存在缺失资料；
- Artifact Schema 是否完整。

### 12.28.3 Task-level

- 结论是否前后一致；
- 引用是否支持论点；
- 是否区分事实、推断与建议；
- 报告结构是否完整。

### 12.28.4 Cross-task

- 哪些来源长期可靠；
- 哪种检索策略经常失败；
- 哪些检查规则应加入 Skill。

## 12.29 反思记忆的数据结构

```json
{
  "reflection_id": "ref-42",
  "task_id": "task-101",
  "scope": "step",
  "trigger": "test_failure",
  "evidence": {
    "test": "test_empty_input",
    "error": "IndexError"
  },
  "diagnosis": "函数在访问首元素前没有检查空列表",
  "recommended_action": "增加空输入分支并补充测试",
  "verified": true,
  "applicability": "functions that access the first list element",
  "retention": "task-local"
}
```

关键字段：

- Scope；
- Trigger；
- Evidence；
- Diagnosis；
- Action；
- Verification；
- Applicability；
- Retention。

## 12.30 防止 Reflection Loop

```mermaid
flowchart TB
    R[Reflection Round] --> V[Verify]
    V --> P{Pass?}
    P -->|是| DONE[Finish]
    P -->|否| B{Budget Remaining?}
    B -->|否| STOP[Stop and Report]
    B -->|是| I{Finding Changed?}
    I -->|否| ESC[Escalate / Human]
    I -->|是| FIX[Refine]
    FIX --> R
```

硬性机制包括：

- 最大轮数；
- 最大 Token 和费用；
- 超时；
- Finding 去重；
- 无改进检测；
- 同一错误重复阈值；
- 人工升级；
- 不可修复状态。

停止时应明确报告：

- 已解决问题；
- 未解决 Finding；
- 停止原因；
- 当前 Artifact；
- 下一步建议。

## 12.31 如何评估反思系统

| 指标 | 含义 |
|---|---|
| First-pass Success | 不反思时的成功率 |
| Post-reflection Success | 反思后的成功率 |
| Finding Precision | Critic 提出的问题中真实问题比例 |
| Finding Recall | 已知问题被发现的比例 |
| Fix Success | 反馈是否促成正确修复 |
| Regression Rate | 修订是否破坏正确内容 |
| Average Rounds | 平均反思轮数 |
| Cost per Success | 每个成功任务的总成本 |
| Time to Detect | 错误被发现的时间 |
| Escalation Rate | 需要人工处理的比例 |

评估时更该看反思是否以可接受成本提高最终任务成功率，并减少风险，而不是只统计 Critic 提了多少意见。

## 12.32 A/B 评估

至少比较：

1. 无 Reflection；
2. Self-Reflection；
3. Deterministic Verifier；
4. Critic Agent；
5. Verifier + Critic；
6. Step-level；
7. Milestone-level；
8. Task-level。

观察：

- 质量提升；
- 延迟；
- Token；
- Tool 成本；
- False Positive；
- Regression；
- 用户满意度。

如果 Critic 只增加成本而没有稳定提升，就不应保留。

## 12.33 常见反模式

### 12.33.1 只说“请检查有没有问题”

缺少 Rubric，反馈容易流于表面。

### 12.33.2 Critic 只能返回问题

没有 PASS 出口，会无限挑毛病。

### 12.33.3 Refiner 看不到原始任务

只根据批注修改，可能偏离用户目标。

### 12.33.4 同一个模型反复重写

没有新证据，只产生文本变化。

### 12.33.5 每个步骤都调用大型 Critic

低风险步骤成本过高。

### 12.33.6 Critic Agent 被假设为客观真相

独立角色仍可能共享模型偏差。

### 12.33.7 反思自动写入长期记忆

错误经验会形成 Memory Poisoning。

### 12.33.8 没有最大轮次

形成无限修订。

### 12.33.9 Debate 用于替代事实查询

多个 Agent 讨论不能替代权威数据。

## 12.34 推荐生产架构

```mermaid
flowchart TB
    TASK[Task] --> EXEC[Executor]
    EXEC --> ART[Artifact + Trace]

    ART --> DV[Deterministic Verifiers]
    DV --> RISK{高风险或检查失败?}

    RISK -->|否| NEED{需要主观质量评价?}
    RISK -->|是| CRITIC[Critic]
    NEED -->|否| DONE[Finish]
    NEED -->|是| CRITIC

    CRITIC --> VERDICT{Verdict}
    VERDICT -->|PASS| DONE
    VERDICT -->|REVISE| REFINE[Refiner]
    VERDICT -->|REPLAN| PLAN[Replanner]
    VERDICT -->|BLOCKED| HUMAN[Human Review]

    REFINE --> EXEC
    PLAN --> EXEC

    CRITIC --> STOP[Stop Controller]
    STOP -->|Budget Exhausted| PARTIAL[Report Incomplete]

    DONE --> CONS{经验值得沉淀?}
    CONS -->|否| END[End]
    CONS -->|是| VALIDATE[Validate Reflection]
    VALIDATE --> MEMORY[Memory / Skill Candidate]
```

推荐原则：

1. 先使用确定性 Verifier；
2. 只在必要维度调用 Critic；
3. 使用结构化 Finding；
4. 将 Evaluate 与 Refine 分开；
5. 对高风险和强依赖步骤提前验证；
6. 对整体输出进行 Task-level Review；
7. 硬性限制轮数、预算和时间；
8. 只有经过验证的经验才能进入长期记忆。

## 12.35 本章总结

Agent Reflection 是反馈驱动的质量控制环：

> **执行 → 验证 → 反馈 → 修订或重规划 → 再验证**

触发粒度包括：

- Step-level：尽早阻止错误传播；
- Milestone-level：平衡成本和纠错速度；
- Task-level：检查整体一致性；
- Cross-task：提炼可复用经验。

落地时要看几件事：

- Critic 具有明确 Rubric；
- 输出结构化 Finding；
- 允许 PASS；
- Refiner 保留原始任务和正确内容；
- 优先使用客观 Verifier；
- 设置硬性停止条件；
- 不把未经验证的反思直接写入长期记忆。

Self-Refine、Reflexion、Critic Agent、Debate 和 LATS 提供的是不同深度的反馈机制。它们有用，但都会增加成本，也都不能替代真实环境、测试、权威数据和人工责任。

## 参考资料

- [Self-Refine: Iterative Refinement with Self-Feedback](https://arxiv.org/abs/2303.17651)
- [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366)
- [Language Agent Tree Search Unifies Reasoning, Acting, and Planning](https://arxiv.org/abs/2310.04406)
- [Improving Factuality and Reasoning in Language Models through Multiagent Debate](https://arxiv.org/abs/2305.14325)
- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
