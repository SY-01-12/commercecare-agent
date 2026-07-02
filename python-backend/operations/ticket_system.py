"""In-memory ticket system for human handoff workflow.

Supports: create, query, update ticket status.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# -- Ticket data model --------------------------------------------------------


@dataclass
class Ticket:
    ticket_id: str
    summary: str
    category: str
    priority: str  # urgent / high / normal / low
    status: str  # opened / in_progress / resolved / closed
    reason: str
    order_id: str | None
    customer_name: str | None
    created_at: str
    updated_at: str
    notes: list[str] = field(default_factory=list)


# -- In-memory store ----------------------------------------------------------

_tickets: dict[str, Ticket] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# -- Public API ---------------------------------------------------------------


def create_ticket(
    summary: str = "",
    category: str = "general",
    priority: str = "normal",
    reason: str = "",
    order_id: str | None = None,
    customer_name: str | None = None,
) -> Ticket:
    """Create a new support ticket. Returns the Ticket object."""
    ticket_id = f"TK-{random.randint(10000, 99999)}"
    now = _now()
    ticket = Ticket(
        ticket_id=ticket_id,
        summary=summary or reason,
        category=category,
        priority=priority,
        status="opened",
        reason=reason,
        order_id=order_id,
        customer_name=customer_name,
        created_at=now,
        updated_at=now,
    )
    _tickets[ticket_id] = ticket
    return ticket


def get_ticket(ticket_id: str) -> Ticket | None:
    """Get a ticket by ID."""
    return _tickets.get(ticket_id)


def update_ticket_status(ticket_id: str, status: str, note: str = "") -> Ticket | None:
    """Update ticket status and optionally add a note."""
    ticket = _tickets.get(ticket_id)
    if not ticket:
        return None
    valid_statuses = {"opened", "in_progress", "resolved", "closed"}
    if status not in valid_statuses:
        raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
    ticket.status = status
    ticket.updated_at = _now()
    if note:
        ticket.notes.append(note)
    return ticket


def get_ticket_status(ticket_id: str) -> dict[str, Any] | None:
    """Return a dict summary of ticket status for the UI."""
    ticket = _tickets.get(ticket_id)
    if not ticket:
        return None
    return {
        "ticket_id": ticket.ticket_id,
        "summary": ticket.summary,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "reason": ticket.reason,
        "order_id": ticket.order_id,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "notes": ticket.notes,
    }


def list_tickets(status: str | None = None) -> list[dict[str, Any]]:
    """List all tickets, optionally filtered by status."""
    result = []
    for t in _tickets.values():
        if status and t.status != status:
            continue
        result.append(get_ticket_status(t.ticket_id))
    return sorted(result, key=lambda x: x["created_at"], reverse=True)


def ticket_count() -> int:
    return len(_tickets)
