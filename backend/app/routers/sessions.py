"""
REST endpoints for managing chat sessions: list, fetch history, rename, delete. Separate from routers/chat.py (the WebSocket itself) since these are plain request/response endpoints with nothing streaming or stateful.
"""

from fastapi import APIRouter, HTTPException, Header

from db import verify_user_token, load_chat_history, get_user_session
from supabase_client import get_supabase_client
import asyncio

router = APIRouter(prefix="/ws", tags=["Chat Sessions"])


@router.get("/sessions")
async def list_sessions(user_id: str, authorization: str = Header(...)):
    """
    Get list of user's chat sessions.
    Requires Bearer token in Authorization header.
    """
    # Extract token from "Bearer <token>" or handle raw token
    try:
        if authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
        else:
            token = authorization
    except AttributeError:
        raise HTTPException(
            status_code=401, detail="Invalid authorization header format"
        )

    user = await verify_user_token(token)
    if not user or user["id"] != user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await get_user_session(user_id)


@router.get("/chat-history")
async def get_chat_history(
    session_id: str, user_id: str, authorization: str = Header(...)
):
    """
    Get chat history for a specific session.
    Requires Bearer token in Authorization header.
    """
    token = authorization.replace("Bearer ", "")

    user = await verify_user_token(token)
    if not user or user["id"] != user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await load_chat_history(session_id)


def _update_session_title_sync(session_id: str, user_id: str, title: str):
    supabase = get_supabase_client()
    session_check = (
        supabase.table("chat_sessions").select("user_id").eq("id", session_id).execute()
    )
    if not session_check.data or session_check.data[0]["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    result = (
        supabase.table("chat_sessions")
        .update({"title": title})
        .eq("id", session_id)
        .execute()
    )
    if getattr(result, "error", None):
        raise HTTPException(status_code=500, detail=str(result.error))


@router.put("/sessions/{session_id}/title")
async def update_session_title_endpoint(
    session_id: str, title_data: dict, authorization: str = Header(...)
):
    token = authorization.replace("Bearer ", "")
    user = await verify_user_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not title_data or "title" not in title_data:
        raise HTTPException(status_code=400, detail="Missing 'title' in request body")

    await asyncio.to_thread(
        _update_session_title_sync, session_id, user["id"], title_data["title"]
    )

    return {"message": "Title updated successfully"}


def _delete_session_sync(session_id: str, user_id: str):
    supabase = get_supabase_client()

    session_check = (
        supabase.table("chat_sessions").select("user_id").eq("id", session_id).execute()
    )
    if not session_check.data or session_check.data[0]["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    supabase.table("chat_messages").delete().eq("session_id", session_id).execute()
    supabase.table("chat_sessions").delete().eq("id", session_id).execute()


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, authorization: str = Header(...)):
    """Delete a chat session and all its messages."""
    try:
        token = authorization.replace("Bearer ", "")
        user = await verify_user_token(token)
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        await asyncio.to_thread(_delete_session_sync, session_id, user["id"])

        return {"message": "Session deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete session: {str(e)}"
        )
