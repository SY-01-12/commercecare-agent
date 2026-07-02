#!/usr/bin/env python
"""RAG CLI: reindex knowledge base and debug retrieval.

Usage:
    python -m rag.cli reindex          # Rebuild the vector index
    python -m rag.cli retrieve <query>  # Test retrieval with a query
    python -m rag.cli stats             # Show collection stats
"""

from __future__ import annotations

import sys

from .loader import load_documents
from .splitter import split_markdown
from .store import index_documents, retrieve, get_collection_stats


def cmd_reindex() -> None:
    """Rebuild the vector index from knowledge_base/ documents."""
    print("Loading documents...")
    docs = load_documents()
    print(f"Found {len(docs)} documents.")

    print("Splitting into chunks...")
    chunks_per_doc = [split_markdown(d["content"]) for d in docs]
    total_chunks = sum(len(c) for c in chunks_per_doc)
    print(f"Created {total_chunks} chunks.")

    print("Indexing with embeddings...")
    index_documents(docs, chunks_per_doc)
    print("Reindex complete.")


def cmd_retrieve(query: str, top_k: int = 5, threshold: float = 0.45) -> None:
    """Run a retrieval query and display results."""
    results = retrieve(query, top_k=top_k, score_threshold=threshold)

    if not results:
        print(f"No results found for: {query}")
        print("(Score threshold: {})".format(threshold))
        return

    print(f"\nQuery: {query}")
    print(f"Results ({len(results)}):\n")
    for i, r in enumerate(results, 1):
        print(f"--- Result {i} ---")
        print(f"Source: {r['source']}")
        print(f"Title:  {r['title']}")
        print(f"Score:  {r['score']}")
        print(f"Content: {r['content'][:200]}...")
        print()


def cmd_stats() -> None:
    """Print vector store stats."""
    stats = get_collection_stats()
    print(f"Collection: {stats['name']}")
    print(f"Documents:  {stats['count']}")
    print(f"Storage:    {stats['storage_dir']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m rag.cli <reindex|retrieve|stats> [args...]")
        sys.exit(1)

    command = sys.argv[1]
    if command == "reindex":
        cmd_reindex()
    elif command == "retrieve":
        if len(sys.argv) < 3:
            print("Usage: python -m rag.cli retrieve <query>")
            sys.exit(1)
        cmd_retrieve(" ".join(sys.argv[2:]))
    elif command == "stats":
        cmd_stats()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
