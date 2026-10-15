"""
Posts API Endpoints: Analysis SSE streaming, feed history, and seed replay.
"""
import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from backend.app.agents.pipeline import AnalysisPipeline
from backend.app.core.security import validate_post_length, verify_api_key
from backend.app.llm.mock_provider import MockProvider
from backend.app.llm.openai_provider import OpenAIProvider
from backend.app.models.schemas import PostAnalyzeRequest
from memory.store.db import KnowledgeBaseStore

logger = logging.getLogger("financial_watch.api.posts")

router = APIRouter(prefix="/api/posts", tags=["Posts & Analysis"])

# In-memory post store for demo session
_ANALYZED_POSTS: list[dict[str, Any]] = []

def get_pipeline() -> AnalysisPipeline:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and not api_key.startswith("mock-") and len(api_key) > 20:
        llm = OpenAIProvider(api_key=api_key)
    else:
        llm = MockProvider()
    return AnalysisPipeline(llm=llm, store=KnowledgeBaseStore())

@router.post("/analyze")
async def analyze_post_stream(
    req: PostAnalyzeRequest,
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """
    Primary intake endpoint.
    Runs the multi-agent pipeline and streams live execution steps via Server-Sent Events (SSE).
    Emits heartbeat events to maintain connection through firewalls and CDNs.
    """
    validate_post_length(req.text)
    pipeline = get_pipeline()

    async def event_generator():
        try:
            async for sse_chunk in pipeline.execute_stream(req):
                if await request.is_disconnected():
                    logger.info("Client disconnected from SSE stream; terminating pipeline processing.")
                    break
                # Check if this is the final payload so we can persist in local session & PostgreSQL
                if "event: pipeline_complete" in sse_chunk:
                    try:
                        raw_data = sse_chunk.split("data: ")[1].strip()
                        payload = json.loads(raw_data)
                        _ANALYZED_POSTS.insert(0, payload)
                        post_id = payload.get("post_id")
                        if post_id:
                            try:
                                KnowledgeBaseStore().save_approval_item(
                                    post_id=post_id,
                                    payload=payload,
                                    approval_status=payload.get("approval_status", "pending")
                                )
                            except Exception as dbe:
                                logger.debug(f"DB persistence fallback to in-memory: {dbe}")
                    except Exception as e:
                        logger.debug(f"Error caching analyzed post: {e}")
                yield sse_chunk
        except Exception as e:
            logger.info(f"Stream interrupted: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@router.get("", response_model=list[dict[str, Any]])
async def list_analyzed_posts(
    limit: int = Query(50, ge=1, le=200),
    category: str | None = None,
    api_key: str = Depends(verify_api_key)
):
    """Returns recent posts analyzed during this session, queried from persistent PostgreSQL storage with fallback."""
    results = []
    try:
        db_items = KnowledgeBaseStore().list_approval_items()
        if db_items:
            results = db_items
    except Exception as e:
        logger.debug(f"Could not read from persistent store: {e}")

    if not results:
        results = _ANALYZED_POSTS

    if category:
        results = [p for p in results if p.get("classification", {}).get("category") == category]
    return results[:limit]

@router.get("/seed")
async def get_seed_posts(
    api_key: str = Depends(verify_api_key)
) -> list[dict[str, Any]]:
    """Returns the gold seed dataset for replay and inspection."""
    seed_file = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "seed_posts.json")
    if not os.path.exists(seed_file):
        raise HTTPException(status_code=404, detail="Seed posts file not found.")

    with open(seed_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data
