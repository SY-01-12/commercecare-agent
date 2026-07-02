"""Vector store: ChromaDB persistence, indexing, and retrieval."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI

_VECTOR_STORE_DIR = Path(__file__).resolve().parent.parent / "vector_store"
_COLLECTION_NAME = "commercecare_knowledge"
_EMBEDDING_MODEL = "text-embedding-3-small"

_client: chromadb.ClientAPI | None = None


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(_VECTOR_STORE_DIR),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def _get_embedding(texts: list[str]) -> list[list[float]]:
    """Get OpenAI embeddings for a list of texts."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required for embeddings")

    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(
        model=_EMBEDDING_MODEL,
        input=texts,
    )
    return [d.embedding for d in response.data]


def index_documents(documents: list[dict], chunks: list[list[str]]) -> None:
    """Index document chunks into ChromaDB.

    Args:
        documents: List of document dicts from loader.
        chunks: List of chunk lists from splitter (parallel to documents).
    """
    client = _get_client()

    # Delete existing collection and recreate
    try:
        client.delete_collection(_COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=_COLLECTION_NAME,
        metadata={"description": "CommerceCare Agent knowledge base"},
    )

    all_ids: list[str] = []
    all_texts: list[str] = []
    all_metadatas: list[dict[str, Any]] = []
    all_embeddings: list[list[float]] = []

    # Collect all texts for batch embedding
    for doc, doc_chunks in zip(documents, chunks):
        for i, chunk in enumerate(doc_chunks):
            chunk_id = f"{doc['path']}_chunk_{i}"
            all_ids.append(chunk_id)
            all_texts.append(chunk)
            all_metadatas.append({
                "source": doc["path"],
                "title": doc["title"],
                "category": doc["category"],
                "chunk_index": i,
            })

    if not all_texts:
        print("No documents to index.")
        return

    # Batch embed (OpenAI API limit: ~2048 texts per call, but we batch 100 at a time for safety)
    batch_size = 100
    for start in range(0, len(all_texts), batch_size):
        batch_texts = all_texts[start:start + batch_size]
        batch_embeddings = _get_embedding(batch_texts)
        all_embeddings.extend(batch_embeddings)

    # Add to ChromaDB in batches
    for start in range(0, len(all_texts), batch_size):
        end = start + batch_size
        collection.add(
            ids=all_ids[start:end],
            embeddings=all_embeddings[start:end],
            documents=all_texts[start:end],
            metadatas=all_metadatas[start:end],
        )

    print(f"Indexed {len(all_texts)} chunks from {len(documents)} documents into '{_COLLECTION_NAME}'.")


def retrieve(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.45,
) -> list[dict]:
    """Retrieve relevant document chunks for a query.

    Args:
        query: User's question.
        top_k: Max number of results.
        score_threshold: Minimum similarity score (0-1 scale, lower = more lenient).

    Returns:
        List of dicts with keys: content, source, title, category, score.
    """
    client = _get_client()

    try:
        collection = client.get_collection(_COLLECTION_NAME)
    except Exception:
        return []  # Collection not yet created

    if collection.count() == 0:
        return []

    query_embedding = _get_embedding([query])

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
    )

    output: list[dict] = []
    if not results["ids"] or not results["ids"][0]:
        return output

    for i in range(len(results["ids"][0])):
        distance = results.get("distances", [[0.0]])[0][i]
        # ChromaDB returns cosine distance (0 to 2); convert to similarity score (1 to -1 → 1 to 0)
        score = 1.0 - (distance / 2.0)

        if score < score_threshold:
            continue

        metadata = results["metadatas"][0][i] if results["metadatas"] else {}
        output.append({
            "content": results["documents"][0][i],
            "source": metadata.get("source", "unknown"),
            "title": metadata.get("title", "Unknown"),
            "category": metadata.get("category", "unknown"),
            "score": round(score, 4),
        })

    return output


def get_collection_stats() -> dict:
    """Return stats about the current vector store."""
    client = _get_client()
    try:
        collection = client.get_collection(_COLLECTION_NAME)
        return {
            "name": _COLLECTION_NAME,
            "count": collection.count(),
            "storage_dir": str(_VECTOR_STORE_DIR),
        }
    except Exception:
        return {"name": _COLLECTION_NAME, "count": 0, "storage_dir": str(_VECTOR_STORE_DIR)}
