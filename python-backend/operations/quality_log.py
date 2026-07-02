"""Quality logging for customer service operations.

Logs agent routing, RAG hits, tool calls, safety triggers, handoffs, and timing.
Never logs API keys, phone numbers, full addresses, or payment info.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def _ensure_log_dir() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class QualityLogEntry:
    session_id: str
    timestamp: str
    user_intent: str
    routed_agent: str
    rag_hit: bool
    rag_sources: list[str]
    human_handoff_triggered: bool
    safety_triggered: bool
    tools_called: list[str]
    tool_results_summary: list[str]
    elapsed_ms: float
    error: str | None
    confirmation_required: bool
    confirmation_granted: bool


def _sanitize_tool_result(result: str) -> str:
    """Truncate and sanitize tool result for logging."""
    if len(result) > 150:
        result = result[:150] + "..."
    return result


def log_event(
    session_id: str = "",
    user_intent: str = "",
    routed_agent: str = "",
    rag_hit: bool = False,
    rag_sources: list[str] | None = None,
    human_handoff_triggered: bool = False,
    safety_triggered: bool = False,
    tools_called: list[str] | None = None,
    tool_results: list[str] | None = None,
    elapsed_ms: float = 0.0,
    error: str | None = None,
    confirmation_required: bool = False,
    confirmation_granted: bool = False,
) -> QualityLogEntry:
    """Log a customer service quality event to file."""
    _ensure_log_dir()

    entry = QualityLogEntry(
        session_id=session_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        user_intent=user_intent[:200],
        routed_agent=routed_agent,
        rag_hit=rag_hit,
        rag_sources=rag_sources or [],
        human_handoff_triggered=human_handoff_triggered,
        safety_triggered=safety_triggered,
        tools_called=tools_called or [],
        tool_results_summary=[_sanitize_tool_result(r) for r in (tool_results or [])],
        elapsed_ms=round(elapsed_ms, 2),
        error=error,
        confirmation_required=confirmation_required,
        confirmation_granted=confirmation_granted,
    )

    # Append JSON line to daily log file
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = _LOG_DIR / f"quality_{date_str}.jsonl"

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.__dict__, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Never let logging break the main flow

    return entry


def read_logs(date_str: str | None = None, limit: int = 100) -> list[dict]:
    """Read quality logs for a given date (default: today)."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = _LOG_DIR / f"quality_{date_str}.jsonl"
    if not log_path.exists():
        return []

    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries[-limit:]


def get_log_stats(date_str: str | None = None) -> dict:
    """Aggregate stats from quality logs for a given date."""
    entries = read_logs(date_str)
    if not entries:
        return {"total_sessions": 0}

    total = len(entries)
    rag_hits = sum(1 for e in entries if e.get("rag_hit"))
    human_handoffs = sum(1 for e in entries if e.get("human_handoff_triggered"))
    safety_triggers = sum(1 for e in entries if e.get("safety_triggered"))
    confirmations = sum(1 for e in entries if e.get("confirmation_required"))
    errors = sum(1 for e in entries if e.get("error"))
    avg_elapsed = sum(e.get("elapsed_ms", 0) for e in entries) / total if total else 0

    return {
        "total_sessions": total,
        "rag_hit_rate": round(rag_hits / total, 3) if total else 0,
        "rag_hits": rag_hits,
        "human_handoff_rate": round(human_handoffs / total, 3) if total else 0,
        "human_handoffs": human_handoffs,
        "safety_trigger_rate": round(safety_triggers / total, 3) if total else 0,
        "safety_triggers": safety_triggers,
        "confirmation_rate": round(confirmations / total, 3) if total else 0,
        "error_rate": round(errors / total, 3) if total else 0,
        "avg_elapsed_ms": round(avg_elapsed, 2),
    }


def clear_logs(date_str: str | None = None) -> None:
    """Remove log files (for testing)."""
    if date_str:
        log_path = _LOG_DIR / f"quality_{date_str}.jsonl"
        if log_path.exists():
            log_path.unlink()
    else:
        if _LOG_DIR.exists():
            for f in _LOG_DIR.glob("quality_*.jsonl"):
                f.unlink()
