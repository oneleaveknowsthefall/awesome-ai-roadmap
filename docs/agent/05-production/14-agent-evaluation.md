---
description: 说明如何评估 Agent 的任务成功率、轨迹质量、工具使用、成本和安全性，并比较离线 Benchmark 与线上评测。
---

# 第十四章：Agent 评估与 Benchmark

## 14.1 为什么 Agent 评估是独立问题

评估普通 LLM 和评估 Agent 是两件事。

评估 LLM 时，输入是一段 Prompt，输出是一段文本，可以直接和参考答案比较。评估 Agent 时，输入是一个目标，输出是**一整条执行轨迹**：调用了哪些 Tool、传了什么参数、读到了什么结果、中途改了几次方向、最后改动了哪些外部状态。

这让单轮文本评估中的一些困难更突出，并增加外部状态与副作用的验收问题。

**第一，没有唯一正确路径。** 同一个任务可以先搜索再读文件，也可以先读文件再搜索，两条路径都对。因此不能用「轨迹是否匹配参考轨迹」来打分。

**第二，结果不只是文本。** Agent 可能改了数据库、提交了代码、发了邮件。正确性必须在**环境状态**上验证，而不是在输出文本上验证。

**第三，行为不确定。** 同一个任务跑两次可能走不同路径、得到不同结果。单次运行可以发现失败，但无法估计同一任务的重复可靠性；重复试验与任务覆盖是两个不同维度。

**第四，失败有多种形态。** 任务失败、工具调用格式错误、无限循环、超预算、越权操作，这些是不同的失败，不能合并成一个「错误率」。

```mermaid
flowchart TB
    LLM[LLM 评估] --> L1[输入: Prompt]
    LLM --> L2[输出: 文本]
    LLM --> L3[比较: 与参考答案]

    AG[Agent 评估] --> A1[输入: 目标 + 环境]
    AG --> A2[输出: 轨迹 + 环境状态变化]
    AG --> A3[比较: 状态断言 + 多次采样]
```

## 14.2 评估的四个层次

一个完整的 Agent 评估体系应该覆盖四层，从下到上分别是：

```mermaid
flowchart BT
    L1[L1 组件层<br/>单个 Tool / Prompt / 检索] --> L2[L2 轨迹层<br/>决策序列是否合理]
    L2 --> L3[L3 任务层<br/>端到端是否达成目标]
    L3 --> L4[L4 系统层<br/>成本 / 延迟 / 稳定性 / 安全]
```

| 层次 | 评估对象 | 典型指标 | 何时用 |
|---|---|---|---|
| L1 组件层 | 单个 Tool、单条 Prompt、检索模块 | 参数正确率、召回率、Schema 合规率 | 改动某个组件时的回归 |
| L2 轨迹层 | 决策序列 | 步数、冗余调用比例、路径合理性 | 定位「结果对但过程差」的问题 |
| L3 任务层 | 端到端结果 | 任务成功率、pass@k、pass^k | 版本发布前的主指标 |
| L4 系统层 | 整体运行特性 | Token 成本、P95 延迟、越权率、循环率 | 上线后的持续监控 |

工程里很容易只盯 L3 端到端成功率。这样做的问题是：成功时说不清为什么成功，失败时也难定位卡在哪一步。L1 和 L2 的价值就在于**归因**，能把一个「任务失败」继续拆到「第 3 步检索没召回」或「第 5 步工具参数填错」。

## 14.3 主流 Agent Benchmark 全景

理解学术基准的价值不在于刷分，而在于它们各自**定义了一类能力**，可以借鉴其评测设计思路来构造自己的业务评测集。

```mermaid
flowchart TB
    B[Agent Benchmark] --> CODE[代码工程]
    B --> WEB[网页与检索]
    B --> GUI[操作系统与 GUI]
    B --> TOOL[工具与对话]
    B --> GEN[通用助手]

    CODE --> SWE[SWE-bench / SWE-Lancer / Terminal-Bench]
    WEB --> WA[WebArena / BrowseComp]
    GUI --> OS[OSWorld]
    TOOL --> TAU[tau-bench / tau2-bench]
    GEN --> GA[GAIA / AgentBench]
    B -.补充知识评测.-> HLE[HLE：非 Agent 专用]
```

### 14.3.1 代码工程类

**SWE-bench** 从真实 GitHub 仓库抽取 Issue 与修复，要求在指定基线仓库中提交补丁。评测使用测试补丁和既有测试，检查应从失败转成功的测试（FAIL_TO_PASS）及应保持通过的测试（PASS_TO_PASS），不是只运行 Agent 修改后恰好已有的测试。

它的设计有两个关键点值得借鉴：

1. **用可执行测试而非文本相似度做判定**，减少主观评分，但测试仍可能遗漏需求、脆弱或被投机满足；
2. **提供完整仓库而非孤立文件**，迫使 Agent 具备检索与导航能力。

由于原始数据集中存在部分描述不充分或测试不可靠的样例，后续出现了人工筛选过的 **SWE-bench Verified** 子集（500 题）。OpenAI 指出该基准存在测试设计缺陷和训练数据污染问题，已停止报告其分数，并建议改报 SWE-bench Pro，见 [Why SWE-bench Verified no longer measures frontier coding capabilities](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)。**引用分数时必须说明是哪个子集**，Full、Lite、Verified 的分数不可直接比较；引用 Verified 成绩时应注意这些局限。

**SWE-Lancer** 使用真实自由职业市场的软件任务，包含独立贡献者任务与管理者选择方案任务。按任务历史报酬聚合的金额是该基准下的价值代理，不是 Agent 实际收入，也不能直接推算生产 ROI。

**Terminal-Bench** 关注纯终端环境中的任务完成能力，覆盖编译、调试、系统配置等场景。

### 14.3.2 网页与检索类

**WebArena** 构建了可复现的自托管网站环境（电商、论坛、代码托管等），任务用程序化的状态断言判定，而不是看模型说了什么。

**BrowseComp** 走向另一个方向：题目答案简短且易于验证，但需要在网络上进行**深度、多跳的检索**才能找到，专门用来测量「持续搜索并交叉验证」的能力。

### 14.3.3 操作系统与 GUI 类

**OSWorld** 在真实操作系统中评测多模态 Agent，任务涉及跨应用操作，判定基于最终文件与系统状态。它增加了视觉定位、动作执行和异步界面的困难，但不能跨不同模型与任务集断言一定比所有纯文本基准难。

### 14.3.4 工具与对话类

**tau-bench** 模拟客服场景，特点是引入了三方交互：Agent、用户模拟器、以及一份必须遵守的**领域政策**。它同时考察三件事：能否正确调用工具、能否与用户澄清信息、以及**能否在用户提出不合规要求时拒绝**。

**tau²-bench** 是其后继，引入「双向控制」：用户侧也能执行动作，Agent 需要指导用户完成操作，更贴近真实的技术支持场景。

### 14.3.5 通用助手类

**GAIA** 的设计理念是「对人类简单、对 AI 困难」。题目需要组合网页浏览、多模态理解、文件处理与推理，但答案是唯一确定的短字符串，便于自动判定。

**AgentBench** 覆盖操作系统、数据库、知识图谱、游戏等八类环境，用于横向比较不同模型的 Agent 能力。

**Humanity's Last Exam (HLE)** 不是 Agent 基准，而是极高难度的学科知识基准，常被用来配合工具使用能力做联合评测。

### 14.3.6 基准对比表

| 基准 | 领域 | 判定方式 | 主要考察 |
|---|---|---|---|
| SWE-bench | 代码修复 | 单元测试 | 仓库导航 + 代码修改 |
| SWE-Lancer | 软件任务 | 测试 + 经济价值 | 端到端交付能力 |
| Terminal-Bench | 终端操作 | 状态断言 | 命令行与系统能力 |
| WebArena | 网页操作 | 状态断言 | 多步网页交互 |
| BrowseComp | 深度检索 | 依据参考短答案判分，官方实现使用模型裁判 | 难检索信息定位与证据核实 |
| OSWorld | 桌面 GUI | 文件/系统状态 | 跨应用长程操作 |
| tau-bench | 客服对话 | 数据库状态 + 政策 | 工具 + 澄清 + 合规拒绝 |
| tau²-bench | 双向对话 | 状态断言 | 指导用户执行动作 |
| GAIA | 通用助手 | 精确答案匹配 | 多模态 + 多工具组合 |
| AgentDojo | 安全 | 任务成功 + 攻击成功 | 抗 Prompt Injection |

### 14.3.7 学术基准的局限

必须清楚学术基准**不能替代业务评测集**，原因有四个：

1. **数据污染**：公开基准的题目和答案可能已进入模型训练语料，分数被高估；
2. **分布不匹配**：你的业务任务分布与基准分布几乎必然不同；
3. **过拟合风险**：针对某个基准做的 Scaffold 优化不一定能迁移；
4. **口径混乱**：不同报告使用不同子集、不同尝试次数、不同工具集，分数不可比。

**正确的用法是：用学术基准的评测设计思路，构造自己的业务评测集。** 具体借鉴点包括「用可执行断言代替主观打分」「在真实环境状态上验证」「把安全违规单独计分」。

## 14.4 核心指标定义

### 14.4.1 任务成功率

最基础的指标。设评测集有 $N$ 个任务，第 $i$ 个任务的判定函数为 $s_i \in \lbrace 0, 1 \rbrace$，则：

$$
\mathrm{SuccessRate} = \frac{1}{N}\sum_{i=1}^{N} s_i
$$

关键是预先定义可复现的判分标准。数据库状态和代码任务优先用可执行断言；报告质量等开放任务可用经校准的模型或人工 Rubric。程序断言覆盖不全时，也不能把“测试通过”直接等同于用户目标完成。

### 14.4.2 pass@k：至少一次做对的机会

从同一任务的 $n$ 次独立运行中，若有 $c_i$ 次成功，则从其中任选 $k$ 次时“至少一次成功”的无偏估计为：

$$
\mathrm{pass@}k = \frac{1}{N}\sum_{i=1}^{N}\left(1 - \frac{\binom{n-c_i}{k}}{\binom{n}{k}}\right), \quad n \geq k
$$

它估计的是允许多次尝试并任选一个成功结果时的成功概率，衡量**能力上界**。适用于有人工审核或可安全挑选候选的场景，例如工程师从多个补丁中选择一个。

### 14.4.3 pass^k：连续运行的一致性

令 $p_i$ 为任务 $i$ 的单次成功概率， $\mathrm{pass}^{k}$ 的定义是同一任务独立运行 $k$ 次都成功的平均概率：

$$
\mathrm{pass}^{k} = \frac{1}{N}\sum_{i=1}^{N}p_i^k
$$

用同一任务的 $n$ 次观测估计时， $c_i$ 次成功给出的无偏有限样本估计为：

$$
\widehat{\mathrm{pass}^{k}} = \frac{1}{N}\sum_{i=1}^{N}\frac{\binom{c_i}{k}}{\binom{n}{k}}, \quad n \geq k
$$

这不是 $\mathrm{pass@}k$，也不写成含糊的 “pass hat k”。对于无人值守生产 Agent， $\mathrm{pass}^{k}$ 才衡量连续可依赖性。tau-bench 的实验揭示： $\mathrm{pass@}1$ 看起来不错时， $k$ 增大， $\mathrm{pass}^{k}$ 仍可能急剧下降，说明行为一致性低于单次能力上限。

```mermaid
flowchart LR
    P1["pass@k<br/>k 次中至少一次成功"] --> U1[衡量能力上界]
    U1 --> S1[适用: 有人工审核的场景]

    P2["pass^k<br/>k 次全部成功"] --> U2[衡量行为一致性]
    U2 --> S2[适用: 无人值守自动化]
```

长链路为何脆弱？在“每步独立、正确率相同、任一步失败都不可恢复”的教学假设下， $m$ 步成功率为 $p^m$； $p = 0.95$、 $m = 20$ 时约为 $0.36$。真实 Agent 存在相关错误、重试和验证，不能直接套用此式，更不能由它推出“降低方差一定比提高能力重要”。此外，即便只有单步任务， $p_i^k$ 也会随重复次数衰减。

报告 pass@k 时还要说明怎样从候选中选出成功结果；若生产没有可靠验收器，离线“至少有一个成功”不代表实际能交付它。比较 pass^k 时应重置环境、固定预算，并区分重复同一任务与连续执行不同任务的可靠性。

### 14.4.4 轨迹层指标

| 指标 | 定义 | 诊断什么 |
|---|---|---|
| 平均步数 | 完成任务的平均循环轮次 | 是否绕路 |
| 冗余调用率 | 重复或无效的 Tool 调用占比 | 是否在原地打转 |
| 工具选择准确率 | 选对工具的步数占比 | Tool 描述是否清晰 |
| 参数合规率 | 参数通过 Schema 校验的比例 | Schema 设计与模型能力 |
| 循环终止率 | 因触达最大轮次而终止的比例 | 停止条件是否失效 |
| 恢复率 | 出错后成功自我纠正的比例 | 错误处理是否有效 |

### 14.4.5 Agentic trajectory：正确、合规且可恢复

最终状态通过不代表轨迹一定可接受。对有副作用的 Agent，评估用例还应断言：

| 维度 | 例子 |
|---|---|
| **证据与授权链** | 每次高风险调用能关联用户目标、允许来源和审批记录 |
| **策略合规** | 未越权、未调用禁用工具，审批发生在执行前 |
| **状态转移正确性** | 中间写入满足不变量；失败后没有留下半完成或重复副作用 |
| **恢复与幂等** | 超时/重试后能恢复，重复执行不重复扣款、发信或删除 |
| **最小充分性** | 在完成任务前提下避免冗余调用、无关数据读取和多余权限 |

轨迹不应与单一“黄金步骤序列”逐字比对；应通过这些可执行约束判断不同合法路径。含检索与引用的 Agent 还应复用 [RAG 评估](../../rag/05-generation-evaluation/18-rag-evaluation.md) 的 Citation、时效和鲁棒性用例。

### 14.4.6 成本与延迟

$$
\mathrm{CostPerTask} = \frac{\sum_{i=1}^{N}\left(c_{\mathrm{in}} \cdot T_{\mathrm{in}}^{(i)} + c_{\mathrm{out}} \cdot T_{\mathrm{out}}^{(i)}\right)}{N}
$$

其中 $c_{\mathrm{in}}$、 $c_{\mathrm{out}}$ 是输入输出单价， $T^{(i)}$ 是任务 $i$ 的 Token 消耗。

**成本必须和成功率一起报告。** 只报成功率会鼓励无限增加反思轮次和搜索宽度。实践中常用的联合指标是「单位成功任务的成本」：

$$
\mathrm{CostPerSuccess} = \frac{\mathrm{CostPerTask}}{\mathrm{SuccessRate}}
$$

即把总成本摊到成功任务上，成功率为零时该比值没有有限定义。教学示例中，90%/0.5 美元方案约为每成功任务 0.56 美元，95%/2 美元方案约为 2.11 美元；前者只在此成本口径上更低，若失败损失或 SLA 不同，不能直接宣布更优。完整成本还要计入失败尝试、工具、计算与人工处理。延迟至少同时报告 P50、P95 和超时率。

## 14.5 判定方式：如何决定一次运行算不算成功

这是构建评测集时最关键的设计决策。

```mermaid
flowchart TB
    J[判定方式] --> E[程序化断言]
    J --> L[LLM-as-Judge]
    J --> H[人工评估]

    E --> E1[可重复 依赖断言覆盖]
    L --> L1[覆盖主观任务 需校准]
    H --> H1[领域判断 需一致性校准]
```

### 14.5.1 程序化断言（首选）

用代码检查最终状态是否满足条件：

- 单元测试是否通过；
- 数据库中是否存在预期记录；
- 生成的文件是否包含指定字段；
- 是否**没有**调用禁止的工具。

**优先级最高。** 只要任务能定义出可执行的断言，就不要用 LLM 打分。断言可靠、便宜、可重复，而且不会随模型版本漂移。

一个实用技巧是**同时写正向断言和负向断言**：正向检查「做到了什么」，负向检查「没有做不该做的事」（如没有删除其他数据、没有越权调用）。

### 14.5.2 LLM-as-Judge（次选）

对于报告质量、回答有用性等任务，可以结合人工与模型评分。模型裁判需处理以下偏差，换成另一家模型也不保证偏差消失：

| 偏差 | 表现 | 缓解手段 |
|---|---|---|
| 位置偏差 | 偏好排在前面的候选 | 交换顺序各评一次取平均 |
| 长度偏差 | 偏好更长的回答 | 在 Rubric 中显式声明长度不加分 |
| 自我偏好 | 偏好同族模型的输出 | 用与被测模型不同的裁判模型 |
| 尺度漂移 | 不同批次分数不可比 | 用固定锚点样例校准 |

先在覆盖主要类别与边界的样本上校准，样本量由误差容忍度、类别稀疏程度和标注预算决定，没有通用的“100 条足够”。除总体一致率与适用时的 Cohen's Kappa，还要检查各类误判、裁判间分歧和标签基率。固定 Rubric、模型版本与锚点样例，防止优化成讨好裁判。

另外，**尽量让 Judge 做二元判定或少档位判定，而不是打 1–10 分**。模型在「是否满足这条具体标准」上远比在连续打分上可靠。

### 14.5.3 人工评估

作为金标准，用于校准 Judge、抽查线上样本、以及处理争议样例。不应作为主要的回归手段。

## 14.6 评测集的构建

### 14.6.1 分层设计

评测集可以分层。下面数量与频率是教学示例，不是行业标准；实际按风险覆盖、统计精度与运行成本调整：

```mermaid
flowchart LR
    S[Smoke 10-20 条] --> R[Regression 100-300 条]
    R --> F[Full 1000+ 条]

    S --> S1[每次提交]
    R --> R1[每次发布]
    F --> F1[每周 / 重大变更]
```

| 层次 | 规模 | 频率 | 用途 |
|---|---|---|---|
| Smoke | 10–20 | 每次代码提交 | 快速发现明显崩溃 |
| Regression | 100–300 | 每次发布 | 防止已修复问题回归 |
| Full | 1000+ | 每周或重大变更 | 全面评估与横向对比 |

### 14.6.2 样例来源

优先级从高到低：

1. **线上真实失败样例**（价值最高，直接反映生产分布）；
2. 线上真实成功样例（用于防回归）；
3. 领域专家构造的边界样例；
4. 模型合成的样例（用于扩充覆盖，需人工抽检）。

**每修复一个线上 Bug，就把对应场景固化成一条回归用例。** 这是评测集最健康的增长方式。

### 14.6.3 每条用例应包含什么

```json
{
  "id": "refund-001",
  "goal": "为订单 A123 办理退款并通知用户",
  "initial_state": {
    "orders": [ { "id": "A123", "status": "shipped", "return_confirmed": true } ]
  },
  "assertions": [
    { "type": "db", "check": "orders.A123.status == 'refunded'" },
    { "type": "event_count", "event": "refund_committed", "order_id": "A123", "equals": 1 },
    { "type": "event_order", "before": "return_confirmed", "after": "refund_committed" },
    { "type": "event_order", "before": "refund_committed", "after": "email_sent" },
    { "type": "email", "order_id": "A123", "recipient": "order_owner", "delivered": true },
    { "type": "tool_not_called", "name": "delete_order" }
  ],
  "policy": ["已发货订单退款需先确认用户已退货"],
  "budget": { "max_steps": 15, "max_tokens": 60000 },
  "tags": ["refund", "policy-check"]
}
```

这是示意用例格式，断言需由评测器实现。关键字段是初始状态、正负向断言及预算；`return_confirmed` 事件须由环境夹具提供，而不能凭 Agent 声明。若未确认退货，应另设“先澄清、不得退款”的用例，不能同时要求无条件退款成功。

### 14.6.4 环境隔离与可复现

评测环境必须与生产环境隔离，且每条用例运行前重置到确定的初始状态。常见做法是用容器快照或数据库事务回滚。**如果两次运行同一条用例的初始状态不同，这条用例的分数就没有意义。**

## 14.7 在线评估与可观测性

离线评测集覆盖不了所有真实情况，必须配合线上监控。

### 14.7.1 必须落库的字段

每次 Agent 运行应记录完整轨迹：

| 字段 | 用途 |
|---|---|
| trace_id / span_id | 关联完整调用链 |
| 每步的 Action、Observation、结构化决策理由/状态摘要 | 复盘可审计决策过程；理由必须是显式生成且允许记录的摘要 |
| Tool 名称、参数、返回、耗时、是否报错 | 定位组件级问题；按敏感级别脱敏与访问控制 |
| 输入输出 Token 数与模型版本 | 成本归因与版本对比 |
| 终止原因 | 区分正常完成 / 超轮次 / 超时 / 报错 |
| 用户反馈信号 | 隐式（是否重问、是否采纳）与显式（点赞点踩） |

**不得保存或要求模型暴露隐藏 Thought / 私有 CoT。** 它既不是可靠解释，也可能包含敏感上下文；用工具调用、可见观察、状态变化和专门生成的简短理由摘要完成审计。终止原因同样不能遗漏，否则「失败率 8%」无法进一步拆解。

### 14.7.2 线上核心监控指标

- 任务完成率与用户重问率；
- P50 / P95 延迟；
- 单任务成本；
- 循环终止率（触达最大轮次的比例）；
- 工具错误率（按工具分组）；
- 安全拦截率与越权尝试次数。

### 14.7.3 灰度与 A/B

Agent 的改动（换模型、改 Prompt、加工具）应通过灰度发布验证。由于 Agent 输出方差大，A/B 实验需要比传统功能更大的样本量才能达到统计显著。**改动前先估算所需样本量，否则容易被噪声误导。**

### 14.7.4 追踪标准

OpenTelemetry 的 GenAI 语义约定覆盖模型、Agent 和工具属性，但截至 2026-09-08 官方仍标记 **Development**。采用时固定约定与 SDK 版本，验证后端字段映射，并对内容脱敏；不能假定所有平台无需适配即可完整消费。

## 14.8 评估驱动开发

把评估放在开发流程的前面，而不是后面。

```mermaid
flowchart LR
    A[发现问题场景] --> B[写成评测用例]
    B --> C[确认当前失败]
    C --> D[修改 Prompt/Tool/流程]
    D --> E[跑评测集]
    E --> F{通过且无回归?}
    F -->|否| D
    F -->|是| G[灰度发布]
    G --> H[线上监控]
    H --> A
```

对于修复用例，先确认它能复现目标失败，再比较修复前后；随机失败可能需要多次试验。已经通过的用例仍可保护现有能力和安全不变量，不能因为“初始通过”就拒绝加入回归集。

## 14.9 常见错误

### 14.9.1 只报单次运行结果

单次运行能发现具体失败，但不足以估计重复可靠性。运行次数应由目标误差和成本决定；3–5 次可作初筛，不能当作统计充分的固定门槛。版本比较尽量对同一批任务做配对分析，报告任务数、每题尝试数、置信区间及失败分布；重复同一题不能替代新增业务覆盖。

### 14.9.2 只看端到端成功率

无法归因。需要同时看轨迹层指标才能知道问题出在哪一步。

### 14.9.3 只报成功率不报成本

会导致不断增加反思轮次和搜索宽度来刷分，上线后成本失控。

### 14.9.4 用 LLM-as-Judge 但不做校准

未经校准的 Judge 分数可能与人工判断严重不一致，此时优化的是「讨好裁判」而非真实质量。

### 14.9.5 评测集被污染

用同一批数据既做 Prompt 调优又做最终评估，等于用训练集测分数。**必须保留一个从不用于调优的 Holdout 集。**

### 14.9.6 直接引用学术基准分数作为业务能力承诺

基准分数与业务表现之间没有可靠的映射关系。

### 14.9.7 忽略安全指标

一个成功率 95% 但偶尔会执行越权删除的 Agent，比成功率 85% 但从不越权的 Agent 危险得多。**安全违规应该是独立的、一票否决的指标**，不能被平均进成功率里。

## 14.10 本章总结

Agent 评估与 LLM 评估的根本区别在于：前者看的不是一段文本，而是**整条轨迹和环境状态**。

工程上更实用的做法，是把评估拆成四层：组件层负责归因，轨迹层看过程质量，任务层给端到端结论，系统层持续盯成本、延迟和安全。判定顺序也尽量固定：能用程序化断言就别交给模型打分，必须用 LLM-as-Judge 时先做校准；人工评估更适合做抽查和校准基线。

无人值守场景别只看 $\mathrm{pass@}k$，还要看 $\mathrm{pass}^{k}$、单位成功成本、P95 延迟，以及轨迹里的授权、状态转移和恢复是否站得住。评测集也要分层运行：Smoke、Regression、Full 各跑各的频率，线上失败样例持续回流。上线后还要把完整轨迹和终止原因落库，并把越权、违规这类安全问题单独计分，不和成功率平均。

学术基准更适合借鉴评测设计，真正做版本决策还得靠自己的业务评测集。

## 参考资料

- [SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://arxiv.org/abs/2310.06770)
- [OpenAI: Why SWE-bench Verified no longer measures frontier coding capabilities](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)
- [SWE-Lancer: Can Frontier LLMs Earn $1 Million from Real-World Freelance Software Engineering?](https://arxiv.org/abs/2502.12115)
- [GAIA: a benchmark for General AI Assistants](https://arxiv.org/abs/2311.12983)
- [tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](https://arxiv.org/abs/2406.12045)
- [tau^2-Bench: Evaluating Conversational Agents in a Dual-Control Environment](https://arxiv.org/abs/2506.07982)
- [OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments](https://arxiv.org/abs/2404.07972)
- [WebArena: A Realistic Web Environment for Building Autonomous Agents](https://arxiv.org/abs/2307.13854)
- [BrowseComp: A Simple Yet Challenging Benchmark for Browsing Agents](https://arxiv.org/abs/2504.12516)
- [AgentBench: Evaluating LLMs as Agents](https://arxiv.org/abs/2308.03688)
- [MLE-bench: Evaluating Machine Learning Agents on Machine Learning Engineering](https://arxiv.org/abs/2410.07095)
- [Humanity's Last Exam](https://arxiv.org/abs/2501.14249)
- [AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents](https://arxiv.org/abs/2406.13352)
- [OpenTelemetry: Generative AI Semantic Conventions](https://github.com/open-telemetry/semantic-conventions-genai)
- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [SWE-bench: Evaluation harness](https://www.swebench.com/SWE-bench/guides/evaluation/)
- [OpenAI: BrowseComp reference implementation](https://github.com/openai/simple-evals/blob/main/browsecomp_eval.py)
- [Anthropic: How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
