# 系统架构文档

> CommerceCare Agent（智售管家）完整系统架构

---

## 1. 总览

```mermaid
graph TB
    subgraph Frontend["前端 (Next.js + ChatKit React)"]
        CHAT[聊天面板 ChatKit Panel]
        AGENT_PANEL[Agent 可视化面板]
        RUNNER[Runner 执行轨迹]
        GUARD_STATUS[Guardrail 状态指示]
        CTX_PANEL[会话上下文面板]
    end

    subgraph Backend["后端 (FastAPI + Uvicorn)"]
        APP[FastAPI App<br/>main.py]
        SERVER[CommerceCareServer<br/>ChatKit 集成]
        MEM_STORE[MemoryStore<br/>会话存储]
    end

    subgraph Agents["Agent 层"]
        TRIAGE[Triage Agent]
        KNOWLEDGE[Knowledge Support Agent]
        ORDER[Order Service Agent]
        LOGISTICS[Logistics Agent]
        AFTERSALES[After-Sales Agent]
        HUMAN_HO[Human Handoff Agent]
        SAFETY_G[Safety Guardrail Agent]
        RELEVANCE_G[Relevance Guardrail Agent]
    end

    subgraph Tools["工具层"]
        RAG_TOOL[RAG 检索]
        FAQ_TOOL[FAQ 查询]
        ORDER_TOOLS[订单工具]
        LOGISTICS_TOOLS[物流工具]
        AS_TOOLS[售后工具]
        TICKET_TOOL[工单工具]
        SAFETY_TOOL[安全检查]
    end

    subgraph Data["数据层"]
        MOCK_DATA[(Mock 数据<br/>JSON)]
        VECTOR_DB[(ChromaDB<br/>向量库)]
        KB[知识库文档<br/>12+ Markdown]
        TICKETS[(工单存储<br/>In-Memory)]
        LOGS[(质量日志<br/>JSONL)]
    end

    CHAT <-->|SSE Stream| APP
    APP --> SERVER
    SERVER --> MEM_STORE
    SERVER --> Agents
    Agents --> Tools
    Tools --> Data
    TRIAGE -->|Handoff| KNOWLEDGE
    TRIAGE -->|Handoff| ORDER
    TRIAGE -->|Handoff| LOGISTICS
    TRIAGE -->|Handoff| AFTERSALES
    TRIAGE -->|Handoff| HUMAN_HO
    KNOWLEDGE --> TRIAGE
    ORDER --> TRIAGE
    LOGISTICS --> TRIAGE
    AFTERSALES --> TRIAGE
    HUMAN_HO --> TRIAGE
```

## 2. Agent 拓扑

```
Triage Agent (路由)
├── Knowledge Support Agent (RAG+FAQ) → Triage
├── Order Service Agent (查询) → Logistics/After-Sales/Triage
├── Logistics Agent (轨迹) → After-Sales/HumanHandoff/Triage
├── After-Sales Agent (退换/退款) → HumanHandoff/Triage
└── Human Handoff Agent (工单) → Triage
```

每个 Agent 都配有双层 Guardrail：
- **Domain Relevance Guardrail** — 话题相关性
- **Safety Guardrail** — 隐私/欺诈/越狱检测

## 3. RAG 调用链

```
用户提问
  → KnowledgeSupportAgent
    → rag_retrieve 工具
      → OpenAI Embeddings (text-embedding-3-small)
      → ChromaDB 语义检索 (cosine similarity)
      → Score Threshold 过滤 (≥ 0.45)
      → 格式化结果（来源+内容+相关度）
    → 无结果 → faq_lookup_tool (补充)
    → 仍无结果 → 拒答 + 建议人工
```

## 4. 确认流程（Human-in-the-Loop）

```
写操作工具首次调用
  → 返回 ⚠️ 操作预览
  → 设置 pending_action + requires_confirmation
  → 等待用户确认

用户回复 "确认"
  → Server 检测确认意图
  → 再次调用同一工具
  → 工具检测 requires_confirmation=True
  → 执行操作 + 清除状态
  → 返回 ✅ 成功 + 受理编号

用户回复其他
  → 清除 pending_action
  → 返回已取消提示
```

## 5. 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | 0.139 |
| Agent SDK | OpenAI Agents SDK | 0.17.7 |
| 前端框架 | Next.js | 15.5 |
| UI 组件 | ChatKit React | 1.3 |
| 向量数据库 | ChromaDB | - |
| Embedding | text-embedding-3-small | - |
| LLM | gpt-4.1-mini | - |
| 日志 | JSONL (按日分文件) | - |
| 包管理 | Python venv + npm | - |
