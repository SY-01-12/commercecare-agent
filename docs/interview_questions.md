# 项目面试问答

> CommerceCare Agent（智售管家）  
> 15+ 个面试常见问题及简洁答案

---

## 1. 多 Agent 路由

**Q1: 为什么要用多 Agent 架构而不是单个大模型？**

单 Agent 在复杂场景下容易出现幻觉、上下文过长、职责混乱。多 Agent 将任务拆分给专业 Agent（订单/物流/售后/知识/人工），每个有独立的 tools 和 instructions，通过 Triage Agent 语义路由分发，提高准确性和可维护性。

**Q2: Triage Agent 如何判断用户意图？**

使用 GPT-4.1-mini 模型 + 明确的 instructions，让模型根据用户输入判断意图类别（订单查询/物流追踪/售后处理/FAQ/投诉），然后通过 Handoff 机制转接到对应的专业 Agent。

**Q3: Handoff 和 function call 有什么区别？**

- **Handoff**：将一个 Agent 的对话控制权转移给另一个 Agent，后续对话由新 Agent 处理
- **Function Call**：Agent 调用工具函数获取信息，但控制权仍在原 Agent

本项目中 Triage → Specialist 用 Handoff；Agent 内部查数据用 Function Call。

---

## 2. Tool Calling

**Q4: 哪些工具需要用户确认？为什么？**

退款（request_refund）、退货（request_return）、换货（create_exchange_request）、取消订单（cancel_order）需要确认。因为这些操作会产生资金变动和状态变更，需要 Human-in-the-Loop 保护，防止误操作或恶意请求。

**Q5: 确认机制是如何实现的？**

两步流程：首次调用 → 工具设置 `requires_confirmation=True` + `pending_action` → 返回 ⚠️ 预览。Server 层检测用户回复，如果是确认关键词 → 再次调用同一工具 → 工具检测状态后执行 → 返回 ✅ 成功。

**Q6: 如何保证工具调用的安全性？**

双层 Guardrail：Domain Relevance Guardrail（话题相关性）+ Safety Guardrail（隐私泄露、欺诈、越狱、高风险退款）。所有 Agent 的 input 都经过这两层检查，不通过则拒绝回复。

---

## 3. RAG 与向量检索

**Q7: RAG 模块的技术选型是什么？**

- **文档存储**：Markdown 文件（12+ 份，分 4 个类别目录）
- **文本分块**：自定义 Markdown Splitter，800 char/chunk，80 char overlap，标题和段落边界感知
- **向量化**：OpenAI text-embedding-3-small（1536 维）
- **向量库**：ChromaDB（PersistentClient，本地持久化）
- **检索**：语义相似度搜索，Top-K=5，Score Threshold=0.45

**Q8: 如果 RAG 检索不到相关内容怎么办？**

不编造！返回 "未在知识库中找到相关文档"，建议用户换种方式描述问题或联系人工客服（400-888-6666）。同时可回退到 FAQ 关键词匹配。

**Q9: 如何展示信息来源？**

每次 RAG 检索结果都附带：来源文件路径（如 `policies/warranty.md`）、文档标题、相关度百分比。前端以"参考资料"形式展示，用户可以验证信息可信度。

---

## 4. 安全确认

**Q10: Safety Guardrail 检测哪些风险？**

- **隐私泄露**：身份证号、银行卡号、密码
- **支付欺诈**：刷单、套现、虚假交易
- **越狱攻击**：提示词注入、指令绕过
- **高风险退款**：保留商品同时全额退款
- **辱骂骚扰**：人身攻击、性骚扰

**Q11: Guardrail 触发了会怎样？**

返回固定拒绝语，同时质量日志记录触发原因和输入内容（脱敏）。前端 Guardrail 面板显示红色 "Failed" 状态。

---

## 5. Human-in-the-Loop

**Q12: 什么情况下会转接人工客服？**

- 用户明确要求（"转人工""找真人"）
- 投诉/情绪激烈/辱骂
- 连续 3 轮以上未解决问题
- 涉及赔偿、法律问题等高风险场景
- 复杂售后（多商品退换、物流丢失赔付）

**Q13: 工单系统支持哪些功能？**

创建工单（TK-xxxxx）、查询工单状态、更新状态流转（opened → in_progress → resolved → closed）、按状态列表、处理备注。工单包含：编号、摘要、分类、优先级、关联订单、创建/更新时间。

---

## 6. 可观测性与评测

**Q14: 如何监控系统运行质量？**

质量日志（`logs/quality_YYYY-MM-DD.jsonl`）记录每次会话的：用户意图、路由 Agent、RAG 命中情况、工具调用、安全触发、人工转接、耗时、错误信息。提供聚合统计 API。

**Q15: 评测体系包含哪些指标？**

32 条评测集覆盖 7 个类别，统计：路由准确率（80.8%）、拒答正确率（83.3%）、RAG 引用覆盖率（57.1%）、人工转接触发率（100%）、工具调用成功率（80.8%）、各类别准确率。

---

## 7. 工程实践

**Q16: 项目的 Git 分支策略是什么？**

- `main` — 总是可运行
- `chore/` — 构建和配置
- `feat/` — 功能分支（6 个阶段各一个）
- `fix/` — 修复
- `docs/` — 文档

每个功能分支通过 PR 合并到 main，保留完整开发历史。

**Q17: 如何做到上游项目合规引用？**

- 保留上游 MIT LICENSE
- NOTICE.md 详细说明来源和改造内容
- README 中声明参考来源与独立改造
- 每个源文件头部标注 "Adapted from openai/openai-cs-agents-demo (MIT License)"
- 不包装为完全原创项目

---

## 8. 开放性思考

**Q18: 如果要上线生产，需要做哪些改进？**

1. MemoryStore → Redis/PostgreSQL 持久化
2. 接入真实订单/物流 API
3. 用户认证 + 会话管理
4. 前端完整卡片展示（订单/物流/工单/确认）
5. 日志系统接入 ELK/Prometheus
6. 并发优化 + 容器化部署（Docker Compose）
7. 知识库增量更新 + 自动索引
8. 端到端测试 + 压测
