"""
Human-in-the-Loop Approval Queue API.
Supports review, approval, rejection, and manual editing of drafted counter-messages.
Strictly enforces the policy that nothing is ever auto-posted.
"""
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.posts import _ANALYZED_POSTS
from backend.app.core.security import verify_api_key
from memory.store.db import KnowledgeBaseStore

router = APIRouter(prefix="/api/queue", tags=["Approval Queue"])

class QueueEditRequest(BaseModel):
    edited_formal_response: str
    edited_pidgin_response: str | None = None
    editor_notes: str | None = None

@router.get("", response_model=list[dict[str, Any]])
async def list_approval_queue(
    status: str | None = "pending",
    api_key: str = Depends(verify_api_key)
):
    """Lists staged items in the human-in-the-loop queue from PostgreSQL with in-memory fallback."""
    try:
        db_items = KnowledgeBaseStore().list_approval_items(status=status)
        if db_items:
            return db_items
    except Exception:
        pass

    if status:
        return [p for p in _ANALYZED_POSTS if p.get("approval_status") == status]
    return _ANALYZED_POSTS

@router.post("/{post_id}/approve")
async def approve_response(
    post_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Approves a drafted response for dissemination."""
    # Persist in DB
    updated_item = None
    try:
        updated_item = KnowledgeBaseStore().update_approval_status(post_id, status="approved")
    except Exception:
        pass

    # Synchronize in-memory cache
    for post in _ANALYZED_POSTS:
        if post.get("post_id") == post_id:
            post["approval_status"] = "approved"
            if not updated_item:
                updated_item = post
            break

    if updated_item:
        return {"status": "success", "message": f"Post {post_id} response approved.", "item": updated_item}
    raise HTTPException(status_code=404, detail=f"Post ID '{post_id}' not found.")

@router.post("/{post_id}/reject")
async def reject_response(
    post_id: str,
    reason: str = Body(..., embed=True),
    api_key: str = Depends(verify_api_key)
):
    """Rejects a drafted response with an audit reason."""
    updated_item = None
    try:
        updated_item = KnowledgeBaseStore().update_approval_status(post_id, status="rejected", rejection_reason=reason)
    except Exception:
        pass

    for post in _ANALYZED_POSTS:
        if post.get("post_id") == post_id:
            post["approval_status"] = "rejected"
            post["rejection_reason"] = reason
            if not updated_item:
                updated_item = post
            break

    if updated_item:
        return {"status": "success", "message": f"Post {post_id} response rejected.", "item": updated_item}
    raise HTTPException(status_code=404, detail=f"Post ID '{post_id}' not found.")

@router.post("/{post_id}/edit")
async def edit_response(
    post_id: str,
    req: QueueEditRequest,
    api_key: str = Depends(verify_api_key)
):
    """Saves human-edited text for a drafted response and marks as edited."""
    updated_item = None
    try:
        updated_item = KnowledgeBaseStore().update_approval_status(
            post_id,
            status="edited",
            editor_notes=req.editor_notes,
            edited_formal=req.edited_formal_response,
            edited_pidgin=req.edited_pidgin_response
        )
    except Exception:
        pass

    for post in _ANALYZED_POSTS:
        if post.get("post_id") == post_id:
            post["approval_status"] = "edited"
            if "response_draft" not in post:
                post["response_draft"] = {}
            post["response_draft"]["formal_response"] = req.edited_formal_response
            if req.edited_pidgin_response:
                post["response_draft"]["pidgin_response"] = req.edited_pidgin_response
            post["editor_notes"] = req.editor_notes
            if not updated_item:
                updated_item = post
            break

    if updated_item:
        return {"status": "success", "message": f"Post {post_id} response edited and saved.", "item": updated_item}
    raise HTTPException(status_code=404, detail=f"Post ID '{post_id}' not found.")

