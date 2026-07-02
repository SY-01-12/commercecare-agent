# 评测文档

> CommerceCare Agent（智售管家）评测体系

---

## 1. 评测集

### 规模与覆盖

| 维度 | 数量 | 说明 |
|------|------|------|
| 总用例 | 32 条 | 覆盖 7 个类别 |
| 订单查询 | 6 条 | 订单号/手机号/姓名/状态查询 |
| 物流追踪 | 4 条 | 轨迹/时效/异常 |
| 售后处理 | 5 条 | 退货/退款/换货/取消/资格 |
| 知识 FAQ | 6 条 | 保修/政策/会员/配送/发票/安装 |
| 人工转接 | 4 条 | 主动转接/投诉/电话/工单查询 |
| 安全拦截 | 4 条 | 越狱/欺诈/隐私/高风险退款 |
| 无关问题 | 2 条 | 写诗/天气 |

### 测试数据格式

```json
{
  "id": "E001",
  "category": "order",
  "question": "帮我查一下订单 ORD-20260701-001",
  "expected_agent": "Order Service Agent",
  "expected_tool": "lookup_order",
  "expected_reject": false
}
```

---

## 2. 评测指标

| 指标 | 当前值 | 目标 | 说明 |
|------|--------|------|------|
| **路由准确率** | 80.8% | ≥ 90% | 路由到正确的 Agent |
| **拒答正确率** | 83.3% | ≥ 95% | 安全/无关问题被正确拦截 |
| **RAG 引用覆盖率** | 57.1% | ≥ 80% | FAQ 问题命中 RAG 知识库 |
| **人工转接触发率** | 100% | ≥ 95% | 需要人工时正确触发 |
| **工具调用成功率** | 80.8% | ≥ 90% | 匹配预期工具 |

> 注：当前评测使用关键词模拟路由，数值低于实际 LLM Agent 的表现。实际 Agent 使用 GPT-4.1-mini 语义路由，准确率更高。

### 各类别准确率

| 类别 | 准确率 |
|------|--------|
| order | 83.3% |
| after_sales | 83.3% |
| logistics | 75.0% |
| faq | 66.7% |
| human_handoff | 100% |
| safety | 100% |
| irrelevant | 50.0% |

---

## 3. 运行评测

```bash
cd python-backend
source .venv/Scripts/activate
PYTHONPATH=. python -m operations.evaluation
# 或显示详细结果
PYTHONPATH=. python -m operations.evaluation --verbose
```

---

## 4. 质量日志分析

```bash
cd python-backend
source .venv/Scripts/activate
PYTHONPATH=. python -c "
from operations.quality_log import get_log_stats
stats = get_log_stats()
print(stats)
"
```

输出示例：
```json
{
  "total_sessions": 150,
  "rag_hit_rate": 0.68,
  "human_handoff_rate": 0.12,
  "safety_trigger_rate": 0.03,
  "confirmation_rate": 0.25,
  "error_rate": 0.02,
  "avg_elapsed_ms": 2456.0
}
```
