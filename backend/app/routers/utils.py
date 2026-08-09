from supabase_client import get_supabase_client
from typing import Optional, List, Dict

def verify_user_token(token: str) -> Optional[Dict]:
    if not token:
        return None
    try:
        supabase = get_supabase_client()
        supabase.auth.set_session(token, "")
        user_res = supabase.auth.get_user(token)

        if user_res and user_res.user:
            return {"id": user_res.user.id, "email": user_res.user.email}
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        return None
    return None

def get_or_create_session(
    user_id: str, session_id: Optional[str] = None, token: Optional[str] = None
) -> Dict:
    supabase = get_supabase_client()
    # If a JWT token is provided, set the Supabase auth session so RLS policies
    # that rely on auth.uid() will work for subsequent inserts/queries.
    try:
        if token:
            supabase.auth.set_session(token, "")
    except Exception:
        # If auth client doesn't support set_session or fails, continue —
        # caller will handle permission errors.
        pass
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

def load_chat_history(session_id: str, limit: int = 50) -> List[Dict]:
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

def save_message(
    session_id: str, user_id: str, role: str, content: str, token: Optional[str] = None
) -> Dict:
    supabase = get_supabase_client()
    # If token provided, set supabase auth session so RLS allows insert
    try:
        if token:
            supabase.auth.set_session(token, "")
    except Exception:
        pass

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


def get_user_session(user_id: str, limit: int = 10) -> List[Dict]:
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

def update_session_title(session_id: str, title: str):
    supabase = get_supabase_client()

    supabase.table("chat_sessions").update({"title": title}).eq(
        "id", session_id
    ).execute()