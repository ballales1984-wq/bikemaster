"""Knowledge API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..routes import get_admin_user, get_current_user

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/")
async def list_knowledge():
    """Return knowledge base statistics (topics, chunks, word counts)."""
    from ...analytics.knowledge_base import get_kb_stats

    stats = get_kb_stats()
    return {
        "topics": stats["topics"],
        "chunks_per_topic": stats["chunks_per_topic"],
        "total_chunks": stats["total_chunks"],
        "total_words": stats["total_words"],
    }


@router.get("/search")
async def search_knowledge_endpoint(query: str = "", max_chunks: int = 4, min_score: float = 0.05):
    """Semantic search over the cycling knowledge base."""
    from ...analytics.knowledge_base import format_context_for_llm, search_knowledge_base

    if not query or not query.strip():
        return {"results": [], "context": "", "count": 0}
    results = search_knowledge_base(query.strip(), max_chunks=max_chunks, min_score=min_score)
    context = format_context_for_llm(results)
    return {
        "results": results,
        "context": context,
        "count": len(results),
        "query": query,
        "topics_matched": sorted({r["topic"] for r in results}),
    }


@router.get("/stats")
async def knowledge_stats(current_user: dict = Depends(get_current_user)):
    """Return knowledge base statistics for the authenticated user."""
    from ...analytics.knowledge_base import get_kb_stats

    stats = get_kb_stats()
    return {
        "topics": stats.get("topics", []),
        "chunks_per_topic": stats.get("chunks_per_topic", {}),
        "total_chunks": stats.get("total_chunks", 0),
        "total_words": stats.get("total_words", 0),
    }


@router.post("/reload")
async def reload_knowledge(current_user: dict = Depends(get_admin_user)):
    """Hot-reload the knowledge base from disk. Admin only."""
    from ...analytics.knowledge_base import reload_kb

    return reload_kb()


@router.post("/init-embeddings")
async def init_kb_embeddings_endpoint(current_user: dict = Depends(get_admin_user)):
    """Initialize embeddings for the knowledge base in PostgreSQL and ChromaDB."""
    from ...analytics.knowledge_base import init_chroma_db, init_kb_embeddings
    from ...db.postgres_db import get_session

    try:
        with get_session() as session:
            pg_result = init_kb_embeddings(session)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail="PostgreSQL not configured") from exc

    chroma_result = init_chroma_db()

    return {"pgvector": pg_result, "chromadb": chroma_result}
