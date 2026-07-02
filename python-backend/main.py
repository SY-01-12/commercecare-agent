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


# -- RAG debug endpoints ------------------------------------------------------


@app.get("/rag/stats")
async def rag_stats() -> Dict[str, Any]:
    """Return vector store statistics."""
    from rag.store import get_collection_stats

    return get_collection_stats()


@app.get("/rag/retrieve")
async def rag_retrieve_debug(
    q: str = Query(..., description="Search query"),
    top_k: int = Query(5, ge=1, le=20),
    threshold: float = Query(0.45, ge=0.0, le=1.0),
) -> Dict[str, Any]:
    """Debug endpoint: retrieve documents from the knowledge base."""
    from rag.store import retrieve as rag_retrieve_fn

    results = rag_retrieve_fn(q, top_k=top_k, score_threshold=threshold)
    return {
        "query": q,
        "count": len(results),
        "threshold": threshold,
        "results": results,
    }


@app.get("/rag/reindex")
async def rag_reindex() -> Dict[str, Any]:
    """Rebuild the RAG index from knowledge_base/ documents."""
    from rag.loader import load_documents
    from rag.splitter import split_markdown
    from rag.store import index_documents, get_collection_stats

    docs = load_documents()
    chunks_per_doc = [split_markdown(d["content"]) for d in docs]
    total_chunks = sum(len(c) for c in chunks_per_doc)
    index_documents(docs, chunks_per_doc)

    stats = get_collection_stats()
    return {
        "documents_loaded": len(docs),
        "chunks_created": total_chunks,
        "collection": stats,
    }


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
