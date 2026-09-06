"""
Data access for chat sessions, messages, and token verification. Lives at the app root (not under routers/) because it's shared plumbing, not a router.
"""

from supabase_client import get_supabase_client
from typing import Optional, List, Dict
import asyncio


def _verify_user_token(token: str) -> Optional[Dict]:
    if not token:
        return None
    try:
        supabase = get_supabase_client()
        # Validates this token directly - must NOT use set_session, which
        # would mutate the shared client's identity for every other request.
        user_res = supabase.auth.get_user(token)

        if user_res and user_res.user:
            return {"id": user_res.user.id, "email": user_res.user.email}
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        return None
    return None


async def verify_user_token(token: str) -> Optional[Dict]:
    return await asyncio.to_thread(_verify_user_token, token)


def _get_or_create_session_sync(
    user_id: str, session_id: Optional[str] = None, token: Optional[str] = None
) -> Dict:
    # Service-role key already bypasses RLS and every query is scoped by
    # user_id - must not mutate the shared client's session per request.
    supabase = get_supabase_client()
    if session_id:
        res = (
            supabase.table("chat_sessions")
            .select("*")
            .eq("id", session_id)
            .eq("user_id", user_id)
            .execute()
        )
        if res and res.data:
            return res.data[0]
    new_session = (
        supabase.table("chat_sessions")
        .insert({"user_id": user_id, "title": "New Health Consultation"})
        .execute()
    )

    return new_session.data[0]


async def get_or_create_session(
    user_id: str, session_id: Optional[str] = None, token: Optional[str] = None
) -> Dict:
    return await asyncio.to_thread(
        _get_or_create_session_sync, user_id, session_id, token
    )


def _load_chat_history_sync(session_id: str, limit: int = 50) -> List[Dict]:
    supabase = get_supabase_client()

    result = (
        supabase.table("chat_messages")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )

    return result.data if result.data else []


async def load_chat_history(session_id: str, limit: int = 50) -> List[Dict]:
    return await asyncio.to_thread(_load_chat_history_sync, session_id, limit)


def _save_message_sync(
    session_id: str, user_id: str, role: str, content: str, token: Optional[str] = None
) -> Dict:
    supabase = get_supabase_client()

    message = (
        supabase.table("chat_messages")
        .insert(
            {
                "session_id": session_id,
                "user_id": user_id,
                "role": role,
                "content": content,
            }
        )
        .execute()
    )

    return message.data[0] if message.data else None


async def save_message(
    session_id: str, user_id: str, role: str, content: str, token: Optional[str] = None
) -> Dict:
    return await asyncio.to_thread(
        _save_message_sync, session_id, user_id, role, content, token
    )


def _get_user_session_sync(user_id: str, limit: int = 10) -> List[Dict]:
    supabase = get_supabase_client()

    result = (
        supabase.table("chat_sessions")
        .select("*")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )

    return result.data if result.data else []


async def get_user_session(user_id: str, limit: int = 10) -> List[Dict]:
    return await asyncio.to_thread(_get_user_session_sync, user_id, limit)


def _get_user_openai_settings_sync(user_id: str) -> tuple[Optional[str], Optional[str]]:
    # Selects only these two columns, never "*" - openai_api_key must never
    # ride along with the rest of the profile (see auth.py's _strip_openai_key).
    supabase = get_supabase_client()
    res = (
        supabase.table("user_profiles")
        .select("openai_api_key, openai_model")
        .eq("user_id", user_id)
        .execute()
    )
    if not res.data:
        return None, None
    row = res.data[0]
    return row.get("openai_api_key") or None, row.get("openai_model") or None


async def get_user_openai_settings(user_id: str) -> tuple[Optional[str], Optional[str]]:
    """Returns (api_key, model) - either may be None."""
    return await asyncio.to_thread(_get_user_openai_settings_sync, user_id)


def _update_session_title_sync(session_id: str, title: str):
    supabase = get_supabase_client()

    supabase.table("chat_sessions").update({"title": title}).eq(
        "id", session_id
    ).execute()


async def update_session_title(session_id: str, title: str):
    await asyncio.to_thread(_update_session_title_sync, session_id, title)
