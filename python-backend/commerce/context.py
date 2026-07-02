# Adapted and significantly modified from openai/openai-cs-agents-demo (MIT License)
# Copyright (c) 2025 OpenAI
# See NOTICE.md and LICENSE for full attribution.

from __future__ import annotations

from chatkit.agents import AgentContext
from pydantic import BaseModel


class CommerceCareAgentContext(BaseModel):
    """Context for e-commerce after-sales customer service agents."""

    # Customer identity
    customer_name: str | None = None
    customer_phone: str | None = None
    account_level: str | None = None  # 普通会员/银卡/金卡/钻石会员

    # Current order context
    order_id: str | None = None
    order_status: str | None = None
    payment_status: str | None = None
    after_sales_status: str | None = None
    total_amount: float | None = None

    # Logistics context
    logistics_id: str | None = None
    logistics_status: str | None = None
    estimated_delivery: str | None = None

    # Product context
    product_id: str | None = None
    product_name: str | None = None

    # After-sales context
    refund_amount: float | None = None
    return_reason: str | None = None
    exchange_requested: bool = False

    # Human handoff context
    ticket_id: str | None = None
    ticket_status: str | None = None
    escalation_reason: str | None = None

    # Internal fields (not exposed to UI)
    pending_action: str | None = None  # e.g. "refund", "cancel_order"
    requires_confirmation: bool = False
    confirmation_prompt: str | None = None


class CommerceCareChatContext(AgentContext[dict]):
    """
    AgentContext wrapper used during ChatKit runs.
    Holds the persisted CommerceCareAgentContext in `state`.
    """

    state: CommerceCareAgentContext


def create_initial_context() -> CommerceCareAgentContext:
    """Factory for a new CommerceCareAgentContext."""
    return CommerceCareAgentContext()


def public_context(ctx: CommerceCareAgentContext) -> dict:
    """
    Return a filtered view of the context for UI display.
    Hides internal fields.
    """
    data = ctx.model_dump()
    hidden_keys = {
        "pending_action",
        "confirmation_prompt",
    }
    for key in list(data.keys()):
        if key in hidden_keys:
            data.pop(key, None)
    return data
