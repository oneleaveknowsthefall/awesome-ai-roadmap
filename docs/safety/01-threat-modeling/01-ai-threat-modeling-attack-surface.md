# 第一章：AI 系统威胁建模与攻击面全景

## 1.1 为什么 AI 安全需要单独的威胁模型

传统应用安全假设「代码是可信的执行体，数据是待校验的输入」。LLM 系统打破了这个假设：**模型的输入（Prompt、检索内容、工具返回值、图片）和输出（文本、工具调用参数、代码）共享同一条通道，指令与数据之间没有结构边界**。这不是某个具体漏洞，而是架构性的根问题——第二章到第八章讨论的几乎所有攻击，最终都能追溯到这一点。

```mermaid
flowchart TB
    T[传统应用安全] --> T1[代码路径固定<br/>数据流向可枚举]
    A[AI 系统安全] --> A1[模型行为由权重和上下文共同决定<br/>无法穷举所有输入到输出的映射]
    A --> A2[指令与数据同道传输<br/>见第2章]
    A --> A3[系统包含训练、微调、检索、<br/>工具、多 Agent 协作等新阶段]
```

因此，AI 系统的威胁建模需要在传统的资产、信任边界和攻击者画像之外，额外回答三个问题：**模型从哪里获得了它现在的行为？运行时哪些不可信内容会进入模型的决策链路？模型的输出能触发什么后果？** 本章给出覆盖这三个问题的框架，后续章节都是对具体环节的深入。

## 1.2 AI 系统的资产与信任边界

把一个典型的生产级 LLM 应用拆成资产,才能谈威胁。

| 资产类别 | 具体对象 | 面临的核心风险 |
|---|---|---|
| 模型权重与配置 | 预训练/微调权重、System Prompt、护栏配置 | 窃取、篡改、后门植入（第4、5章） |
| 训练与微调数据 | 预训练语料、SFT/RLHF 数据、RAG 知识库 | 投毒、隐私泄漏（第4、6章） |
| 运行时上下文 | 用户输入、检索片段、工具返回值、多模态内容 | 提示注入、越狱（第2章） |
| 工具与执行环境 | Function/MCP Server、代码解释器、浏览器、Computer Use | 越权调用、沙箱逃逸（第7、8章） |
| 输出与下游系统 | 生成文本、工具调用参数、渲染界面 | 二次注入、密钥外泄（第3章） |
| 身份与凭据 | 用户/Agent/Server 身份、OAuth 令牌、API Key | 冒充、confused deputy（第7章） |
| 治理与审计数据 | 日志、模型卡、评测报告、内容出处 | 篡改、合规缺失（第9、10章） |

信任边界不再是单一的「内网/外网」，而是**每一次内容进入模型上下文、每一次模型输出触发动作**都构成一次边界穿越。这也是「Host/调用方必须是策略执行点」（详见[Tool Protocol 安全](../../tools/02-mcp/15-tool-protocol-security.md) 15.1）这一原则的根源。

## 1.3 三个主流威胁建模框架

生产环境通常需要同时使用三类框架：一类给出攻击者视角的战术知识库，一类给出组织级风险治理流程，一类给出漏洞分类清单。三者互补而非互斥。

### 1.3.1 MITRE ATLAS：攻击者战术与技术知识库

MITRE ATLAS（Adversarial Threat Landscape for Artificial-Intelligence Systems）仿照 ATT&CK 的战术-技术矩阵，记录真实发生过的 AI 攻击案例，覆盖侦察、资源开发、初始访问、ML 供应链攻击、模型逃避、数据投毒、模型窃取、外泄等战术阶段。它的价值在于**用真实案例校准「这个威胁是否值得投入资源防御」**，而不是空想式的攻击树。做威胁建模时，可以按 ATLAS 矩阵逐格检查系统是否暴露对应技术面。

### 1.3.2 NIST AI RMF：治理生命周期

NIST AI Risk Management Framework 定义了 **Govern、Map、Measure、Manage** 四个循环功能：Govern 建立问责与制度，Map 识别场景中的风险来源，Measure 用指标量化风险，Manage 决定缓解、转移或接受。RMF 不关心具体攻击技术，而是回答「谁负责、什么时候评估、评估不通过怎么办」——这是第十章治理章节的直接依据。生成式 AI 场景可结合 NIST 的 Generative AI Profile 补充具体风险清单（如幻觉、内容真实性、CBRN 滥用等）。

### 1.3.3 OWASP Top 10：漏洞分类与速查

OWASP 维护两份互补清单：**LLM Applications Top 10**（面向单模型应用，如 LLM01 Prompt Injection、LLM02 Sensitive Information Disclosure、LLM03 Supply Chain、LLM04 Data and Model Poisoning、LLM05 Improper Output Handling、LLM06 Excessive Agency、LLM07 System Prompt Leakage、LLM08 Vector and Embedding Weaknesses、LLM09 Misinformation、LLM10 Unbounded Consumption）和 **Agentic AI / Multi-Agentic System Top 10**（面向自主 Agent，覆盖工具滥用、身份冒充、级联失控、人机协同失效等）。两份清单的粒度接近 CWE，适合作为代码评审和安全测试的检查项。

三者的关系可以概括为：**ATLAS 告诉你敌人怎么打，RMF 告诉你组织怎么管，OWASP 告诉你代码里该查什么。**

```mermaid
flowchart LR
    ATLAS["MITRE ATLAS<br/>攻击者战术/技术"] -->|校准威胁优先级| MODEL[本组织威胁模型]
    OWASP["OWASP LLM / Agentic Top 10<br/>漏洞分类"] -->|检查项| MODEL
    RMF["NIST AI RMF<br/>Govern/Map/Measure/Manage"] -->|治理流程| MODEL
    MODEL --> DECIDE[决定投入哪些防御<br/>见第2-10章]
```

## 1.4 攻击面总览：沿数据与模型生命周期铺开

按 AI 系统的生命周期阶段梳理攻击面，比按单点漏洞罗列更容易做到不遗漏。

```mermaid
flowchart TB
    subgraph S1["数据与训练阶段"]
        D1[预训练语料] --> D2[微调/RLHF 数据]
        D2 --> D3[模型权重]
    end
    subgraph S2["分发与部署阶段"]
        D3 --> P1[模型仓库/供应链]
        P1 --> P2[推理服务]
    end
    subgraph S3["运行时阶段"]
        P2 --> R1[Prompt/多模态输入]
        R1 --> R2[RAG 检索]
        R2 --> R3[工具/MCP/A2A 调用]
        R3 --> R4[代码执行/浏览器/Computer Use]
    end
    subgraph S4["输出与治理阶段"]
        R4 --> O1[生成输出]
        O1 --> O2[下游系统/用户]
        O2 --> G1[审计与合规]
    end
```

| 阶段 | 典型攻击 | 详解章节 |
|---|---|---|
| 训练/微调数据 | 数据投毒、后门触发器 | 第4章 |
| 模型分发 | 供应链篡改、反序列化 RCE | 第5章 |
| 运行时输入 | 直接/间接 Prompt Injection、越狱 | 第2章、[Agent 安全](../../agent/05-production/15-agent-security.md) |
| RAG 检索 | 语料投毒、间接注入 | [RAG 安全](../../rag/06-operations-security/20-rag-challenges-security.md)、第4章 |
| 工具/协议调用 | 越权、confused deputy | 第7章、[Tool Protocol 安全](../../tools/02-mcp/15-tool-protocol-security.md) |
| 代码/浏览器/Computer Use | 沙箱逃逸、SSRF、剪贴板劫持 | 第8章 |
| 输出 | 二次注入、密钥外泄、不安全渲染 | 第3章 |
| 隐私 | 记忆化抽取、PII 泄漏 | 第6章 |
| 全生命周期 | 评测缺失、治理缺位 | 第9、10章 |

## 1.5 攻击者画像与能力分级

同一威胁在不同攻击者能力下风险等级完全不同，建模时应显式区分。

| 能力等级 | 描述 | 举例 |
|---|---|---|
| L0 匿名用户 | 仅能通过公开接口发送 Prompt | 越狱、间接注入投放 |
| L1 认证用户 | 拥有合法账号和正常权限 | 滥用自身权限做越权探测、差分探测 |
| L2 内容供应方 | 能让内容进入训练语料或知识库 | 数据投毒、后门触发器 |
| L3 供应链角色 | 能发布模型/依赖/工具描述 | 供应链投毒、Tool poisoning |
| L4 内部人员 | 拥有部署、日志或密钥访问权限 | 权限滥用、日志泄漏 |
| L5 具备算力的研究级攻击者 | 可训练影子模型做迁移攻击 | 模型窃取、成员推断 |

多数生产系统的第一优先级应放在 L0-L2（因为攻击面最大、门槛最低），L3-L5 需要结合具体业务的暴露程度决定投入。

## 1.6 本主题的定位与交叉引用约定

本仓库已经在 Agent、Tools、RAG 三个应用主题中，针对具体架构给出了防御细节：

- [Agent 安全](../../agent/05-production/15-agent-security.md)：Prompt Injection 的架构级防御模式（Dual LLM、CaMeL 等）、致命三要素、权限最小化、执行隔离。
- [Tool Protocol 安全](../../tools/02-mcp/15-tool-protocol-security.md)：MCP/A2A 协议层的 OAuth、audience、token passthrough、SSRF 防护。
- [RAG 落地难点与安全](../../rag/06-operations-security/20-rag-challenges-security.md)：语料投毒、检索侧间接注入、权限过滤、差分探测。

`docs/safety/` 不重复展开这些已经讲清楚的架构模式，而是承担三件事：

1. **提供跨层的威胁建模框架和标准映射**（本章），让读者知道任意一个具体攻击落在整体图景的什么位置；
2. **补充这些主题尚未覆盖、但同样关键的环节**：越狱与系统提示泄漏的分类学（第2章）、输出侧处理（第3章）、训练/供应链投毒（第4、5章）、隐私与记忆泄漏（第6章）、跨系统身份治理与 Computer Use 沙箱（第7、8章）；
3. **提供组织级的评测、红队与治理流程**（第9、10章），这是单个应用架构文档不会覆盖的层面。

阅读顺序建议：先读本章建立框架，再按需查阅具体章节；已经读过 Agent/Tools/RAG 安全章节的读者可以直接跳到第2章之后。

## 1.7 常见错误

### 1.7.1 只用一个框架

只套 OWASP Top 10 会漏掉治理流程；只用 NIST RMF 会缺少具体技术清单；只看 ATLAS 案例会忽略尚未被公开报道的新型风险。三者应配合使用。

### 1.7.2 把威胁建模做成一次性文档

模型、Prompt、工具集和依赖库都在持续变化，威胁模型需要随每次架构变更或依赖升级重新评审，而不是上线前写一次就归档。

### 1.7.3 忽略攻击者能力分级

不区分「匿名用户」和「内部人员」会导致防御资源错配——把大量精力投入防内部威胁，却对最容易触发的匿名越狱和间接注入疏于防范。

### 1.7.4 认为威胁模型是安全团队的事

模型行为、Prompt 结构、工具授权范围的决定权在产品和工程团队手里，威胁建模必须让这些团队参与，而不是安全团队闭门产出一份文档。

## 1.8 本章总结

1. AI 系统的威胁建模需要额外回答「模型行为从哪来、运行时什么内容会进入决策链路、输出能触发什么」三个问题；
2. **MITRE ATLAS** 给出攻击者战术技术知识库，**NIST AI RMF** 给出 Govern/Map/Measure/Manage 治理流程，**OWASP LLM/Agentic Top 10** 给出漏洞检查清单，三者互补；
3. 攻击面应沿「训练/微调 → 分发 → 运行时输入/检索/工具调用/执行 → 输出 → 治理」的生命周期铺开，而不是零散罗列；
4. 攻击者能力应分级（匿名用户到内部人员），防御投入应优先覆盖门槛最低、暴露面最大的等级；
5. `docs/safety/` 负责跨层框架、标准映射和第2-10章覆盖的补充环节，Agent/Tools/RAG 已有的架构级防御细节通过交叉引用复用，不重复展开。

> **一句话概括：AI 安全的第一步不是挑一个具体漏洞去修，而是先把资产、生命周期阶段和攻击者能力摆清楚，再用 ATLAS、RMF、OWASP 三张地图对齐威胁优先级。**

## 参考资料

- [MITRE ATLAS](https://atlas.mitre.org/)
- [NIST AI Risk Management Framework (AI RMF 1.0)](https://www.nist.gov/itl/ai-risk-management-framework)
- [NIST Generative AI Profile (NIST AI 600-1)](https://www.nist.gov/publications/generative-ai-profile)
- [OWASP Top 10 for Large Language Model Applications](https://genai.owasp.org/llm-top-10/)
- [OWASP Agentic AI Threats and Mitigations](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/)
- [NIST AI 100-2 E2025: Adversarial Machine Learning Taxonomy](https://www.nist.gov/publications/adversarial-machine-learning-taxonomy-and-terminology-attacks-and-mitigations)
