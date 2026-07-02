# 工具调用与人工转接文档

> CommerceCare Agent（智售管家）  
> 更新日期：2026-07-02

---

## 1. 工具清单

### 1.1 只读工具（无副作用）

| 工具 | 描述 | 所在 Agent |
|------|------|-----------|
| `lookup_order` | 按订单号/手机号/姓名查订单 | Triage, Order, Logistics, After-Sales, Human Handoff |
| `get_order_detail` | 获取订单完整商品明细 | Order Service |
| `track_shipment` | 查询物流轨迹 | Logistics |
| `get_logistics_status` | 查询物流配送状态 | Logistics |
| `check_after_sales_eligibility` | 检查售后资格 | After-Sales |
| `faq_lookup_tool` | FAQ 关键词查询 | Knowledge Support |
| `rag_retrieve` | RAG 知识库语义检索 | Knowledge Support |
| `get_ticket_status` | 查询工单状态 | Human Handoff |
| `check_content_safety` | 内容安全检查 | Safety (内部) |

### 1.2 写操作工具（需确认）

| 工具 | 描述 | 确认机制 |
|------|------|---------|
| `request_refund` | 发起退款申请 | ✅ 两步确认 |
| `request_return` | 发起退货申请 | ✅ 两步确认 |
| `cancel_order` | 取消订单 | ✅ 两步确认 |
| `create_exchange_request` | 发起换货申请 | ✅ 两步确认 |
| `create_support_ticket` | 创建人工工单 | ❌ 无需确认（创建即执行） |

---

## 2. 确认机制

### 两步流程

```
第一步（首次调用）
  ├── 工具检测 requires_confirmation == False
  ├── 设置 requires_confirmation = True
  ├── 设置 pending_action = "refund" / "return" / "cancel" / "exchange"
  ├── 返回 ⚠️ 确认提示（包含订单信息、金额、操作内容）
  └── 等待用户回复

第二步（用户确认后）
  ├── Server 层检测用户回复
  ├── 识别确认关键词（确认/是的/同意/好的/可以/yes/ok）
  ├── 保持 requires_confirmation = True
  ├── 再次调用同一工具
  ├── 工具检测到 has_confirmation
  ├── 执行实际操作（修改订单状态、生成受理号）
  ├── 清除确认状态
  └── 返回 ✅ 成功提示

取消（用户拒绝）
  ├── Server 检测到非确认回复
  ├── 清除 requires_confirmation 和 pending_action
  └── 返回取消提示
```

### 确认关键词

```
确认 / 是的 / 同意 / 好的 / 可以 / yes / ok / 确认退款 / 确认退货 / 确认取消
```

---

## 3. 工单系统

### 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `ticket_id` | str | 工单编号（TK-xxxxx） |
| `summary` | str | 用户问题摘要 |
| `category` | str | 分类（general/complaint/refund/logistics/other） |
| `priority` | str | urgent / high / normal / low |
| `status` | str | opened / in_progress / resolved / closed |
| `reason` | str | 转人工原因 |
| `order_id` | str\|None | 关联订单号 |
| `customer_name` | str\|None | 客户名称 |
| `created_at` | str | ISO 创建时间 |
| `updated_at` | str | ISO 最后更新时间 |
| `notes` | list[str] | 处理备注 |

### 状态流转

```
opened → in_progress → resolved → closed
  ↓                      ↓
closed                 closed
```

---

## 4. 质量日志

### 记录字段

| 字段 | 说明 |
|------|------|
| `session_id` | 会话标识 |
| `timestamp` | UTC 时间戳 |
| `user_intent` | 用户意图分类 |
| `routed_agent` | 最终路由 Agent |
| `rag_hit` | 是否命中 RAG |
| `rag_sources` | RAG 来源文档列表 |
| `human_handoff_triggered` | 是否触发人工转接 |
| `safety_triggered` | 是否触发安全拦截 |
| `tools_called` | 本次调用的工具列表 |
| `tool_results_summary` | 工具结果摘要（脱敏） |
| `elapsed_ms` | 处理耗时（毫秒） |
| `error` | 错误信息（如有） |
| `confirmation_required` | 是否需要确认 |
| `confirmation_granted` | 确认是否通过 |

### 安全规则

- **不记录**：API Key、完整手机号、完整地址、支付信息
- **脱敏**：工具结果截断至 150 字符
- **存储**：按日期分文件（`logs/quality_YYYY-MM-DD.jsonl`）

---

## 5. 人工转接触发条件

| 条件 | 优先级 | 示例 |
|------|--------|------|
| 用户明确要求 | normal | "转人工""找真人客服" |
| 投诉 | high | "你们的服务太差了" |
| 情绪激烈/辱骂 | urgent | 人身攻击、威胁 |
| 3 轮未解决 | high | 同一问题反复无法解决 |
| 高风险操作 | urgent | 涉嫌欺诈、套现 |
| 赔偿协商 | high | 要求经济赔偿 |
