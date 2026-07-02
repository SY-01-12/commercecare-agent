# 架构基线

> 基于上游项目 `openai/openai-cs-agents-demo` 分析绘制，作为 CommerceCare Agent 改造的架构基线。

---

## 1. 系统整体架构

```mermaid
graph TB
    subgraph Frontend["前端 (Next.js + ChatKit React)"]
        CHAT[聊天面板<br/>ChatKit Panel]
        AGENTS[Agent 列表面板<br/>Agents List]
        RUNNER[Runner 轨迹面板<br/>Runner Output]
        GUARD[Guardrail 状态<br/>Guardrails Panel]
        CTX[会话上下文<br/>Conversation Context]
    end

    subgraph Backend["后端 (FastAPI + Uvicorn)"]
        APP[FastAPI App<br/>main.py]
        SERVER[AirlineServer<br/>ChatKitServer 子类]
        STORE[MemoryStore<br/>内存存储]
    end

    subgraph AgentSDK["OpenAI Agents SDK"]
        RUNNER_ENGINE[Runner<br/>run_streamed]
        TRIAGE[Triage Agent]
        S1[Flight Info Agent]
        S2[Booking Agent]
        S3[Seat Agent]
        S4[FAQ Agent]
        S5[Refunds Agent]
        GR1[Relevance Guardrail]
        GR2[Jailbreak Guardrail]
    end

    subgraph Tools["工具层"]
        T1[flight_status_tool]
        T2[get_matching_flights]
        T3[book_new_flight]
        T4[cancel_flight]
        T5[update_seat]
        T6[display_seat_map]
        T7[faq_lookup_tool]
        T8[issue_compensation]
    end

    CHAT <-->|SSE Stream| APP
    APP --> SERVER
    SERVER --> STORE
    SERVER --> RUNNER_ENGINE
    RUNNER_ENGINE --> TRIAGE
    TRIAGE -->|Handoff| S1
    TRIAGE -->|Handoff| S2
    TRIAGE -->|Handoff| S3
    TRIAGE -->|Handoff| S4
    TRIAGE -->|Handoff| S5
    S1 --> GR1
    S1 --> GR2
    S1 --> T1
    S1 --> T2
    S2 --> T3
    S2 --> T4
    S3 --> T5
    S3 --> T6
    S4 --> T7
    S5 --> T8
```

---

## 2. 请求处理流程

```mermaid
sequenceDiagram
    participant U as 用户 (UI)
    participant CK as ChatKit Panel
    participant API as FastAPI
    participant S as AirlineServer
    participant R as Runner
    participant A as Agent
    participant T as Tool
    participant G as Guardrail

    U->>CK: 输入消息
    CK->>API: POST /chatkit (SSE)
    API->>S: respond(thread, message)
    S->>G: 执行 Input Guardrails
    alt Guardrail 触发
        G-->>S: Tripwire Triggered
        S-->>CK: 拒绝回复 + Guardrail 状态
    else Guardrail 通过
        G-->>S: Pass
        S->>R: run_streamed(agent, input)
        loop Agent 循环
            R->>A: 推理
            A->>T: 调用工具
            T-->>A: 工具结果
            A->>A: Handoff 决策
        end
        R-->>S: 流式事件
        S-->>CK: SSE: 消息 + Agent 事件 + Handoff
        CK-->>U: 逐步渲染
    end
```

---

## 3. Agent Handoff 状态机

```mermaid
stateDiagram-v2
    [*] --> Triage

    Triage --> FlightInfo: 航班状态/延误
    Triage --> Booking: 订票/改签/取消
    Triage --> SeatService: 选座/特殊服务
    Triage --> FAQ: 政策问答
    Triage --> Refunds: 补偿/退款

    FlightInfo --> Booking: 需要改签
    FlightInfo --> Triage: 其他问题

    Booking --> SeatService: 需要选座
    Booking --> Refunds: 需要补偿
    Booking --> Triage: 完成/其他

    SeatService --> Refunds: 需要补偿
    SeatService --> Triage: 完成/其他

    Refunds --> FAQ: 查询政策
    Refunds --> Triage: 完成/其他

    FAQ --> Triage: 完成/需要转接
```

---

## 4. 数据模型

```mermaid
classDiagram
    class AirlineAgentContext {
        +str passenger_name
        +str confirmation_number
        +str seat_number
        +str flight_number
        +str account_number
        +List~dict~ itinerary
        +str baggage_claim_id
        +str compensation_case_id
        +str scenario
        +List~str~ vouchers
        +str special_service_note
        +str origin
        +str destination
    }

    class AirlineAgentChatContext {
        +AirlineAgentContext state
        +ThreadMetadata thread
        +Store store
        +dict request_context
    }

    class ConversationState {
        +List input_items
        +AirlineAgentContext context
        +str current_agent_name
        +List~AgentEvent~ events
        +List~GuardrailCheck~ guardrails
    }

    AirlineAgentChatContext *-- AirlineAgentContext
    ConversationState *-- AirlineAgentContext
```

---

## 5. CommerceCare Agent 改造目标架构

```mermaid
graph TB
    subgraph Frontend["前端 (Next.js + ChatKit React)"]
        CHAT_CC[聊天面板]
        AGENTS_CC[Agent 面板]
        RUNNER_CC[Runner 轨迹]
    end

    subgraph Backend["后端 (FastAPI + Uvicorn)"]
        APP_CC[FastAPI App]
        SERVER_CC[CommerceCareServer]
        DB[(SQLite / PostgreSQL)]
        VEC[(向量数据库)]
    end

    subgraph Agents["智能体层"]
        TRIAGE_CC[Triage Agent<br/>意图识别与路由]
        ORDER[Order Agent<br/>订单查询与详情]
        LOGISTICS[Logistics Agent<br/>物流追踪与异常]
        REFUND_CC[Refund Agent<br/>退款与退货处理]
        FAQ_CC[FAQ Agent<br/>RAG 知识库问答]
        HUMAN[Human Handoff Agent<br/>人工客服转接]
    end

    subgraph Tools_CC["工具层"]
        OT[订单查询工具]
        LT[物流追踪工具]
        RT[退款处理工具]
        RAG_TOOL[RAG 检索工具]
        TICKET[工单创建工具]
    end

    CHAT_CC <--> APP_CC
    APP_CC --> SERVER_CC
    SERVER_CC --> DB
    SERVER_CC --> VEC
    SERVER_CC --> Agents
    Agents --> Tools_CC
    HUMAN --> TICKET
    FAQ_CC --> RAG_TOOL --> VEC
```

---

## 6. 关键差异对比

| 维度 | 上游（航旅客服） | CommerceCare（电商售后） |
|------|-----------------|------------------------|
| 业务领域 | 航班、座位、补偿 | 订单、物流、退款、退货 |
| Agent 数量 | 6 个 | 6 个（角色不同） |
| 知识库 | Mock FAQ（if/else） | RAG + 企业知识库 |
| 数据存储 | 内存 | SQLite → PostgreSQL |
| 人工介入 | 无 | Human Handoff + 工单 |
| 工具数量 | 10 个 Mock 工具 | 逐步对接真实 API |
| 向量检索 | 无 | ChromaDB / FAISS |
