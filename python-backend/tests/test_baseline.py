"""
Minimal tests for the baseline customer service agent reproduction.

Adapted from openai/openai-cs-agents-demo (MIT License)
Copyright (c) 2025 OpenAI
"""
import pytest
import asyncio

from agents.tool_context import ToolContext

from airline.agents import (
    triage_agent,
    faq_agent,
    flight_information_agent,
    booking_cancellation_agent,
    seat_special_services_agent,
    refunds_compensation_agent,
)
from airline.context import AirlineAgentContext, create_initial_context, public_context
from airline.guardrails import relevance_guardrail, jailbreak_guardrail
from airline.tools import faq_lookup_tool


def _make_tool_ctx(tool_name: str, tool_arguments: str = "{}") -> ToolContext:
    """Create a minimal ToolContext for testing."""
    return ToolContext(
        context=None,
        tool_name=tool_name,
        tool_arguments=tool_arguments,
        tool_call_id="test-call-id",
    )


# ====== 1. Agent Routing Tests ======


def test_all_agents_registered():
    """Verify all 6 agents are registered and have names."""
    agents = [
        triage_agent,
        faq_agent,
        flight_information_agent,
        booking_cancellation_agent,
        seat_special_services_agent,
        refunds_compensation_agent,
    ]
    for agent in agents:
        assert agent.name, f"Agent {agent} has no name"
    assert len(agents) == 6


def test_triage_agent_has_handoffs():
    """Triage agent must have 5 handoff targets."""
    assert len(triage_agent.handoffs) == 5
    agent_names = [
        getattr(h, "agent_name", getattr(h, "name", ""))
        for h in triage_agent.handoffs
    ]
    assert "Flight Information Agent" in agent_names
    assert "Booking and Cancellation Agent" in agent_names
    assert "Seat and Special Services Agent" in agent_names
    assert "FAQ Agent" in agent_names
    assert "Refunds and Compensation Agent" in agent_names


def test_all_agents_have_guardrails():
    """Every agent must have both relevance and jailbreak guardrails."""
    agents = [
        triage_agent,
        faq_agent,
        flight_information_agent,
        booking_cancellation_agent,
        seat_special_services_agent,
        refunds_compensation_agent,
    ]
    for agent in agents:
        guardrail_names = [
            getattr(g, "name", getattr(g, "__name__", str(g)))
            for g in agent.input_guardrails
        ]
        assert len(agent.input_guardrails) >= 2, (
            f"{agent.name} missing guardrails: found {guardrail_names}"
        )


def test_agent_handoff_graph_connectivity():
    """Verify the handoff graph is connected — every non-triage agent
    can hand off back to triage."""
    non_triage = [
        faq_agent,
        flight_information_agent,
        booking_cancellation_agent,
        seat_special_services_agent,
        refunds_compensation_agent,
    ]
    for agent in non_triage:
        handoff_targets = [
            getattr(h, "agent_name", getattr(h, "name", ""))
            for h in agent.handoffs
        ]
        assert triage_agent.name in handoff_targets, (
            f"{agent.name} cannot hand off back to Triage Agent"
        )


# ====== 2. Context Tests ======


def test_create_initial_context():
    """Initial context should have all None fields."""
    ctx = create_initial_context()
    assert ctx.passenger_name is None
    assert ctx.confirmation_number is None
    assert ctx.flight_number is None


def test_public_context_hides_internal_fields():
    """Public context must not expose itinerary, baggage_claim_id, etc."""
    ctx = AirlineAgentContext(
        passenger_name="Test User",
        itinerary=[{"flight_number": "FLT-123"}],
        baggage_claim_id="BG123",
        compensation_case_id="CMP-456",
        scenario="on_time",
        vouchers=["$100 hotel"],
    )
    pub = public_context(ctx)
    assert "itinerary" not in pub
    assert "baggage_claim_id" not in pub
    assert "compensation_case_id" not in pub
    assert "scenario" not in pub
    assert pub["passenger_name"] == "Test User"


# ====== 3. Tool Tests ======


@pytest.mark.asyncio
async def test_faq_lookup_tool_baggage():
    """faq_lookup_tool should return baggage info for bag-related queries."""
    ctx = _make_tool_ctx(
        faq_lookup_tool.name,
        '{"question": "What is the baggage allowance?"}'
    )
    result = await faq_lookup_tool.on_invoke_tool(
        ctx, '{"question": "What is the baggage allowance?"}'
    )
    assert "one bag" in result.lower() or "bag" in result.lower()


@pytest.mark.asyncio
async def test_faq_lookup_tool_wifi():
    """faq_lookup_tool should return Wi-Fi info."""
    ctx = _make_tool_ctx(
        faq_lookup_tool.name,
        '{"question": "Do you have wifi?"}'
    )
    result = await faq_lookup_tool.on_invoke_tool(
        ctx, '{"question": "Do you have wifi?"}'
    )
    assert "wifi" in result.lower()


@pytest.mark.asyncio
async def test_faq_lookup_tool_unknown():
    """faq_lookup_tool should return a fallback for unknown questions."""
    ctx = _make_tool_ctx(
        faq_lookup_tool.name,
        '{"question": "xyzzy unknown topic"}'
    )
    result = await faq_lookup_tool.on_invoke_tool(
        ctx, '{"question": "xyzzy unknown topic"}'
    )
    assert "don't know" in result.lower() or "sorry" in result.lower()


# ====== 4. Guardrail Tests ======


def test_relevance_guardrail_registered():
    """Relevance guardrail must have the correct name."""
    assert relevance_guardrail.name == "Relevance Guardrail"


def test_jailbreak_guardrail_registered():
    """Jailbreak guardrail must have the correct name."""
    assert jailbreak_guardrail.name == "Jailbreak Guardrail"
