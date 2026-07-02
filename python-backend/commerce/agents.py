# Adapted and significantly modified from openai/openai-cs-agents-demo (MIT License)
# Copyright (c) 2025 OpenAI
# See NOTICE.md and LICENSE for full attribution.
#
# CommerceCare Agent — 7-agent e-commerce after-sales orchestration.

from __future__ import annotations

from agents import Agent, RunContextWrapper, handoff
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from .context import CommerceCareChatContext
from .guardrails import relevance_guardrail, safety_guardrail
from .tools import (
    cancel_order,
    check_after_sales_eligibility,
    check_content_safety,
    create_support_ticket,
    faq_lookup_tool,
    get_order_detail,
    lookup_order,
    rag_retrieve_tool,
    request_refund,
    request_return,
    track_shipment,
)

MODEL = "gpt-4.1-mini"

# Aliases to avoid name collisions with function_tool objects in agent instructions.
_lookup_order = lookup_order
_faq_lookup = faq_lookup_tool
_rag_retrieve = rag_retrieve_tool
_track_shipment = track_shipment
_get_order_detail = get_order_detail
_request_refund = request_refund
_request_return = request_return
_cancel_order = cancel_order
_check_eligibility = check_after_sales_eligibility
_create_ticket = create_support_ticket

# =============================================================================
#  Agent #1: TriageAgent — entry point, intent routing
# =============================================================================


triage_agent = Agent[CommerceCareChatContext](
    name="Triage Agent",
    model=MODEL,
    handoff_description="判断用户意图并路由到合适的专业 Agent。",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX} "
        "你是智售管家（CommerceCare Agent）的入口路由 Agent。根据用户消息判断意图并转接：\n\n"
        "1. Order Service Agent — 查询订单、订单详情、购买记录\n"
        "2. Logistics Agent — 物流轨迹、配送进度、是否发货\n"
        "3. After-Sales Agent — 退货/换货/退款申请、售后资格\n"
        "4. Knowledge Support Agent — 商品参数、保修、配送政策、会员权益\n"
        "5. Human Handoff Agent — 投诉、情绪激烈、多次无法解决、要求人工\n\n"
        "规则：\n"
        "- 如果用户提供了订单号/手机号并询问订单，先用 lookup_order 获取订单再转接。\n"
        "- 如果意图明确，立刻转接一个 Agent，不要多轮确认。\n"
        "- 如果用户表达投诉、辱骂、强烈不满，直接转接 Human Handoff Agent。\n"
        "- 如果消息提及退货/退款/换货但未提供订单号，引导用户提供后再转接。\n"
        "- 每次只转接一个 Agent，让专业 Agent 完成后续工作。"
    ),
    tools=[_lookup_order],
    handoffs=[],
    input_guardrails=[relevance_guardrail, safety_guardrail],
)


# =============================================================================
#  Agent #2: KnowledgeSupportAgent — FAQ / product / policy
# =============================================================================


knowledge_support_agent = Agent[CommerceCareChatContext](
    name="Knowledge Support Agent",
    model=MODEL,
    handoff_description="回答商品参数、保修、退换货政策、会员权益、支付方式等常见问题，基于 RAG 知识库检索。",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}\n"
        "你是智售管家的知识支持 Agent。你的职责是回答用户关于商品、政策和服务的常见问题。\n\n"
        "工作流程：\n"
        "1. 识别用户的问题类别（商品参数/保修/退换货政策/物流政策/会员权益/支付方式/发票）。\n"
        "2. 优先使用 rag_retrieve 从企业知识库中检索相关文档。\n"
        "3. 如果 RAG 未找到相关内容，再使用 faq_lookup_tool 补充查询。\n"
        "4. 用简洁清晰的中文回复用户，并附带检索到的来源文档名称。\n"
        "5. 如果知识库和 FAQ 都没有覆盖用户的问题，不要编造答案！诚实地告知用户，并建议联系人工客服（拨打 400-888-6666）或转接 Human Handoff Agent。\n"
        "6. 如果用户需要订单查询、物流追踪或售后操作，转接回 Triage Agent。\n\n"
        "重要：不得凭自己的知识编造政策信息。所有政策回答必须基于检索到的文档内容。\n"
        "完成回答后无需转接。如果需要其他 Agent 处理，转接回 Triage Agent。"
    ),
    tools=[_rag_retrieve, _faq_lookup],
    input_guardrails=[relevance_guardrail, safety_guardrail],
)


# =============================================================================
#  Agent #3: OrderServiceAgent — order lookup & details
# =============================================================================


order_service_agent = Agent[CommerceCareChatContext](
    name="Order Service Agent",
    model=MODEL,
    handoff_description="查询订单状态、订单详情和购买记录。",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}\n"
        "你是智售管家的订单服务 Agent。你的职责是帮助用户查询订单。\n\n"
        "工作流程：\n"
        "1. 如果上下文中已有订单信息，直接展示。否则先询问订单号或手机号，使用 lookup_order 查询。\n"
        "2. 用户询问详细商品信息时，使用 get_order_detail 展示完整明细。\n"
        "3. 用友好的中文回复，包含订单状态、商品列表、金额和物流单号。\n"
        "4. 如果订单已签收且用户想退货，告知可以转接 After-Sales Agent。\n"
        "5. 如果用户需要物流详情，告知可以转接 Logistics Agent。\n\n"
        "完成后如用户有进一步需求，根据意图转接到对应 Agent；否则回到 Triage Agent。"
    ),
    tools=[_lookup_order, _get_order_detail],
    input_guardrails=[relevance_guardrail, safety_guardrail],
)


# =============================================================================
#  Agent #4: LogisticsAgent — shipment tracking
# =============================================================================


logistics_agent = Agent[CommerceCareChatContext](
    name="Logistics Agent",
    model=MODEL,
    handoff_description="查询物流轨迹、配送进度、预计送达时间和物流异常。",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}\n"
        "你是智售管家的物流查询 Agent。你的职责是帮助用户追踪包裹。\n\n"
        "工作流程：\n"
        "1. 如果上下文中已有物流单号，直接使用 track_shipment 查询。\n"
        "2. 如果没有物流单号但有订单号，先告知用户订单号，建议先查询订单获取物流单号。\n"
        "3. 展示完整的物流轨迹，包括每个节点的时间和状态。\n"
        "4. 如果物流异常（延迟、丢失），告知用户可以转接 After-Sales Agent 申请售后。\n"
        "5. 如果是已签收状态但用户表示未收到，建议用户联系人工客服。\n\n"
        "完成后如用户有进一步需求，根据意图转接；否则回到 Triage Agent。"
    ),
    tools=[_track_shipment, _lookup_order],
    input_guardrails=[relevance_guardrail, safety_guardrail],
)


# =============================================================================
#  Agent #5: AfterSalesAgent — returns, refunds, exchanges
# =============================================================================


after_sales_agent = Agent[CommerceCareChatContext](
    name="After-Sales Agent",
    model=MODEL,
    handoff_description="处理退货、换货、退款申请和售后资格查询。涉及资金或状态变更需用户二次确认。",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}\n"
        "你是智售管家的售后处理 Agent。你的职责是帮助用户处理退换货和退款。\n\n"
        "⚠️ 核心安全规则：\n"
        "1. 所有涉及退款、退货、取消订单的操作，必须调用对应工具发起确认流程。\n"
        "2. 工具会返回确认提示 — 你必须将此提示完整展示给用户。\n"
        "3. 用户明确回复「确认」「是的」「同意」等肯定词语后，再次调用同一工具完成操作。\n"
        "4. 如果用户回复其他内容，放弃操作并告知用户。\n\n"
        "工作流程：\n"
        "1. 确认上下文中已有订单信息（如无，先调用 lookup_order）。\n"
        "2. 使用 check_after_sales_eligibility 检查售后资格。\n"
        "3. 根据用户需求调用对应工具：request_refund（退款）、request_return（退货）、cancel_order（取消订单）。\n"
        "4. 首次调用会返回确认提示；用户确认后再次调用同一工具完成操作。\n"
        "5. 操作完成后展示受理编号和后续步骤。\n\n"
        "如果用户投诉或情绪激烈，转接 Human Handoff Agent。完成售后操作后回到 Triage Agent。"
    ),
    tools=[
        _lookup_order,
        _check_eligibility,
        _request_refund,
        _request_return,
        _cancel_order,
    ],
    input_guardrails=[relevance_guardrail, safety_guardrail],
)


# =============================================================================
#  Agent #6: HumanHandoffAgent — escalation to human support
# =============================================================================


human_handoff_agent = Agent[CommerceCareChatContext](
    name="Human Handoff Agent",
    model=MODEL,
    handoff_description="处理投诉、情绪激烈、多次无法解决的复杂问题，创建人工工单。",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}\n"
        "你是智售管家的人工转接 Agent。当用户需要人工客服时，由你来处理。\n\n"
        "触发场景：\n"
        "1. 用户明确要求人工客服/打电话/找真人。\n"
        "2. 用户表达强烈不满、投诉或辱骂。\n"
        "3. 连续多轮无法解决用户问题。\n"
        "4. 涉及赔偿、重大投诉、法律问题等高风险场景。\n\n"
        "工作流程：\n"
        "1. 先安抚用户情绪，表达理解和歉意。\n"
        "2. 使用 create_support_ticket 创建工单，设置合适的优先级。\n"
        "3. 告知用户工单编号、预计处理时间和人工客服联系方式。\n"
        "4. 如果用户提供了联系方式，备注在工单中。\n\n"
        "创建工单后，如果用户还有简单问题可以继续帮助；否则告知等待人工联系即可。\n"
        "完成后回到 Triage Agent（如果用户有其他需求）。"
    ),
    tools=[_create_ticket, _lookup_order],
    input_guardrails=[safety_guardrail],  # Human handoff agent uses safety only, relevance is too restrictive for this agent
)


# =============================================================================
#  Handoff Graph
# =============================================================================

# Triage → all specialists
triage_agent.handoffs = [
    knowledge_support_agent,
    order_service_agent,
    logistics_agent,
    after_sales_agent,
    human_handoff_agent,
]

# Knowledge Support → Triage
knowledge_support_agent.handoffs = [triage_agent]

# Order Service → Logistics, After-Sales, Triage
order_service_agent.handoffs = [
    logistics_agent,
    after_sales_agent,
    triage_agent,
]

# Logistics → After-Sales, Human Handoff, Triage
logistics_agent.handoffs = [
    after_sales_agent,
    human_handoff_agent,
    triage_agent,
]

# After-Sales → Human Handoff, Triage
after_sales_agent.handoffs = [
    human_handoff_agent,
    triage_agent,
]

# Human Handoff → Triage
human_handoff_agent.handoffs = [triage_agent]


# =============================================================================
#  Agent Registry
# =============================================================================

_ALL_AGENTS = [
    triage_agent,
    knowledge_support_agent,
    order_service_agent,
    logistics_agent,
    after_sales_agent,
    human_handoff_agent,
]


def get_agent_by_name(name: str) -> Agent[CommerceCareChatContext]:
    """Return the agent object by name."""
    agent_map = {a.name: a for a in _ALL_AGENTS}
    return agent_map.get(name, triage_agent)


def build_agents_list() -> list[dict]:
    """Build a list of all available agents and their metadata for the UI."""

    def _gname(g) -> str:
        name_attr = getattr(g, "name", None)
        if isinstance(name_attr, str) and name_attr:
            return name_attr
        fn = getattr(g, "guardrail_function", None)
        if fn is not None and hasattr(fn, "__name__"):
            return fn.__name__.replace("_", " ").title()
        return str(g)

    result = []
    for a in _ALL_AGENTS:
        result.append({
            "name": a.name,
            "description": getattr(a, "handoff_description", ""),
            "handoffs": [
                getattr(h, "agent_name", getattr(h, "name", ""))
                for h in getattr(a, "handoffs", [])
            ],
            "tools": [
                getattr(t, "name", getattr(t, "__name__", ""))
                for t in getattr(a, "tools", [])
            ],
            "input_guardrails": [_gname(g) for g in getattr(a, "input_guardrails", [])],
        })
    return result
