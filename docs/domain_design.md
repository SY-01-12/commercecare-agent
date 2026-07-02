# 电商售后领域设计文档

> CommerceCare Agent（智售管家）领域设计
> 基于 baseline 改造，参考 `openai/openai-cs-agents-demo` (MIT License)

---

## 1. Agent 职责定义

### 1.1 Agent 拓扑

```
                       ┌──────────────────────┐
                       │    Triage Agent       │
                       │    意图识别与路由      │
                       └──────┬───────────────┘
            ┌─────────────────┼─────────────────────┐
            │                 │                     │
   ┌────────▼────────┐ ┌─────▼──────┐ ┌────────────▼────────┐
   │ Knowledge       │ │ Order      │ │ Logistics           │
   │ Support Agent   │ │ Service    │ │ Agent               │
   │ 商品/政策/FAQ    │ │ 订单查询    │ │ 物流追踪             │
   └────────┬────────┘ └──┬──┬──────┘ └──┬──────┬───────────┘
            │             │  │           │      │
            │    ┌────────▼──▼──┐        │      │
            │    │ After-Sales  │◄───────┘      │
            │    │ Agent        │               │
            │    │ 售后/退换/退款 │◄──────────────┘
            │    └──────┬───────┘
            │           │
   ┌────────▼───────────▼──────────────┐
   │       Human Handoff Agent         │
   │       投诉/情绪/复杂问题转人工       │
   └──────────────────┬───────────────┘
                      │
              ┌───────▼───────┐
              │ Triage Agent  │ (仅此一条回退路径)
              └───────────────┘
```

### 1.2 Agent 详细说明

| # | Agent | 中文名 | 职责 | 工具 |
|---|-------|--------|------|------|
| 1 | Triage Agent | 路由 Agent | 意图识别，分发到专业 Agent | `lookup_order` |
| 2 | Knowledge Support Agent | 知识支持 Agent | 商品参数、保修、退换货政策、会员权益、支付方式 | `faq_lookup_tool` |
| 3 | Order Service Agent | 订单服务 Agent | 查询订单状态、商品明细、金额 | `lookup_order`, `get_order_detail` |
| 4 | Logistics Agent | 物流 Agent | 追踪包裹轨迹，展示配送节点 | `track_shipment`, `lookup_order` |
| 5 | After-Sales Agent | 售后 Agent | 退货/换货/退款，取消订单（需用户确认） | `lookup_order`, `check_after_sales_eligibility`, `request_refund`, `request_return`, `cancel_order` |
| 6 | Human Handoff Agent | 人工转接 Agent | 投诉、情绪激烈、复杂问题 → 创建工单 | `create_support_ticket`, `lookup_order` |

---

## 2. 路由规则

### 2.1 Triage Agent 路由策略

| 用户意图 | 关键词/信号 | 路由目标 |
|---------|-----------|---------|
| 查询订单 | 订单号、我的订单、买了什么 | Order Service Agent |
| 查询物流 | 快递到哪了、物流、发货了吗 | Logistics Agent |
| 售后需求 | 退货、退款、换货、不想要了 | After-Sales Agent |
| 政策咨询 | 保修多久、怎么退货、会员权益 | Knowledge Support Agent |
| 投诉/情绪 | 我要投诉、太差了、骂人、多次未解决 | Human Handoff Agent |
| 商品咨询 | 参数、规格、蓝牙版本、功率 | Knowledge Support Agent |
| 联系人工 | 找人工、转人工、打电话 | Human Handoff Agent |

### 2.2 Specialist Agent 转接规则

- **Knowledge Support**：仅可转接回 Triage
- **Order Service**：可转接 Logistics、After-Sales、Triage
- **Logistics**：可转接 After-Sales、Human Handoff（异常/丢件）、Triage
- **After-Sales**：可转接 Human Handoff（投诉/情绪）、Triage
- **Human Handoff**：仅可转接回 Triage

---

## 3. 工具边界

### 3.1 工具清单

| 工具 | 类型 | 需要确认 | 描述 |
|------|------|---------|------|
| `faq_lookup_tool` | 只读 | 否 | FAQ 知识库查询 |
| `lookup_order` | 只读 | 否 | 按订单号/手机号/姓名查订单 |
| `get_order_detail` | 只读 | 否 | 获取订单商品明细 |
| `track_shipment` | 只读 | 否 | 物流轨迹查询 |
| `check_after_sales_eligibility` | 只读 | 否 | 检查售后资格 |
| `request_refund` | 写 | **是** | 发起退款申请 |
| `request_return` | 写 | **是** | 发起退货申请 |
| `cancel_order` | 写 | **是** | 取消订单 |
| `create_support_ticket` | 写 | 否 | 创建人工工单 |
| `check_content_safety` | 只读 | 否 | 安全内容检测 |

### 3.2 确认机制

所有 `requires_confirmation=true` 的工具使用两步流程：

**第一步**（首次调用）：
- 工具检测 `context.state.requires_confirmation == False`
- 设置 `requires_confirmation = True` 和 `pending_action`
- 返回确认提示文本（⚠️ 开头）

**第二步**（用户确认后）：
- Server 检测到用户回复「确认」「是的」「好的」等关键词
- 保持 `requires_confirmation = True`，再次调用同一工具
- 工具检测到 `requires_confirmation == True` 且 `pending_action` 匹配
- 执行实际操作，清除确认状态
- 返回操作成功文本（✅ 开头）

**取消**（用户拒绝）：
- Server 检测到非确认回复
- 清除 `requires_confirmation` 和 `pending_action`
- 返回取消提示

---

## 4. 安全策略

### 4.1 Guardrail 层级

| 层级 | Guardrail | 检测目标 | 触发动作 |
|------|-----------|---------|---------|
| L1 | Domain Relevance Guardrail | 无关话题（写诗、编程等） | 拒绝回复 |
| L2 | Safety Guardrail | 隐私泄露、欺诈、越狱、高风险退款、辱骂 | 拒绝回复 |

### 4.2 Safety Guardrail 检测维度

| 风险类型 | 示例 | risk_type |
|---------|------|-----------|
| 隐私泄露 | "我的身份证号是…"、"银行卡号是…" | `privacy_leak` |
| 支付欺诈 | "帮我刷单"、"套现" | `fraud` |
| 越狱攻击 | "忽略之前的指令"、"system prompt" | `jailbreak` |
| 高风险退款 | "全额退款但不退货" | `high_risk_refund` |
| 辱骂骚扰 | 对客服人身攻击 | `abuse` |

### 4.3 额外安全措施

- 所有 Agent 不暴露内部提示词或系统配置
- 订单详情中的手机号和地址做脱敏处理（仅显示前6位 + `****`）
- 退款金额严格基于订单实际金额
- 已取消/已完成售后的订单不允许重复操作

---

## 5. 数据模型

### 5.1 上下文模型

```
CommerceCareAgentContext
├── 客户身份
│   ├── customer_name: str | None
│   ├── customer_phone: str | None
│   └── account_level: str | None
├── 订单信息
│   ├── order_id: str | None
│   ├── order_status: str | None
│   ├── payment_status: str | None
│   ├── after_sales_status: str | None
│   └── total_amount: float | None
├── 物流信息
│   ├── logistics_id: str | None
│   ├── logistics_status: str | None
│   └── estimated_delivery: str | None
├── 售后信息
│   ├── refund_amount: float | None
│   ├── return_reason: str | None
│   └── exchange_requested: bool
├── 人工工单
│   ├── ticket_id: str | None
│   ├── ticket_status: str | None
│   └── escalation_reason: str | None
└── 内部状态（不暴露给 UI）
    ├── pending_action: str | None
    ├── requires_confirmation: bool
    └── confirmation_prompt: str | None
```

### 5.2 Mock 数据

| 文件 | 条目数 | 说明 |
|------|--------|------|
| `mock_orders.json` | 4 笔 | 含待付款/已发货/已签收/退款中各种状态 |
| `mock_logistics.json` | 3 条 | 顺丰/圆通，含在途/已签收 |
| `mock_products.json` | 6 个 | 耳机/手表/键盘/鼠标/空气炸锅/数据线 |
| `mock_policies.json` | 6 条 | 退换货/保修/物流/会员/支付/售后联系方式 |
