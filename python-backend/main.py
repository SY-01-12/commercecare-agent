# Adapted and significantly modified from openai/openai-cs-agents-demo (MIT License)
# Copyright (c) 2025 OpenAI
# See NOTICE.md and LICENSE for full attribution.
#
# CommerceCare Agent — FastAPI application entry point.

from __future__ import annotations as _annotations

import json
import os
from typing import Any, Dict

from chatkit.server import StreamingResult
from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from commerce.agents import (
    after_sales_agent,
    human_handoff_agent,
    knowledge_support_agent,
    logistics_agent,
    order_service_agent,
    triage_agent,
)
from commerce.context import (
    CommerceCareAgentContext,
    CommerceCareChatContext,
    create_initial_context,
    public_context,
)
from server import CommerceCareServer

app = FastAPI(title="CommerceCare Agent", version="0.1.0")

# Disable tracing for zero data retention orgs
os.environ.setdefault("OPENAI_TRACING_DISABLED", "1")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_server = CommerceCareServer()


def get_server() -> CommerceCareServer:
    return chat_server


@app.post("/chatkit")
async def chatkit_endpoint(
    request: Request, server: CommerceCareServer = Depends(get_server)
) -> Response:
    payload = await request.body()
    result = await server.process(payload, {"request": request})
    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    if hasattr(result, "json"):
        return Response(content=result.json, media_type="application/json")
    return Response(content=result)


@app.get("/chatkit/state")
async def chatkit_state(
    thread_id: str = Query(...),
    server: CommerceCareServer = Depends(get_server),
) -> Dict[str, Any]:
    return await server.snapshot(thread_id, {"request": None})


@app.get("/chatkit/bootstrap")
async def chatkit_bootstrap(
    server: CommerceCareServer = Depends(get_server),
) -> Dict[str, Any]:
    return await server.snapshot(None, {"request": None})


@app.get("/chatkit/state/stream")
async def chatkit_state_stream(
    thread_id: str = Query(...),
    server: CommerceCareServer = Depends(get_server),
):
    thread = await server.ensure_thread(thread_id, {"request": None})
    queue = server.register_listener(thread.id)

    async def event_generator():
        try:
            initial = await server.snapshot(thread.id, {"request": None})
            yield f"data: {json.dumps(initial, default=str)}\n\n"
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        finally:
            server.unregister_listener(thread.id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}


__all__ = [
    "CommerceCareAgentContext",
    "CommerceCareChatContext",
    "after_sales_agent",
    "app",
    "chat_server",
    "create_initial_context",
    "human_handoff_agent",
    "knowledge_support_agent",
    "logistics_agent",
    "order_service_agent",
    "public_context",
    "triage_agent",
]
