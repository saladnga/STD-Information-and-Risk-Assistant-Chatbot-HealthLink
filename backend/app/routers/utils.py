import os
import json
from supabase_client import get_supabase_client
from datetime import datetime
from typing import Optional, List, Dict

# Load symptom mapping and rules
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(current_dir, "symptom_target_rules.json"), "r") as f:
    symptom_target_rules = json.load(f)
with open(os.path.join(current_dir, "symptom_map.json"), "r") as x:
    symptom_map = json.load(x)


# Text to Feature Vector Conversion
def process_text_to_feature(text: str, base_feature: str, nlp) -> dict:
    """
    Converts user symptom text into binary features for model inference.

    Steps:
    - Detects symptom mentions using MedSpaCy rules
    - Maps them to training feature names
    - Adds demographic/behavior defaults
    """

    features = {col: 0 for col in base_feature}
    doc = nlp(text)

    # Activate features if matching symptom entities are found
    for ent in doc.ents:
        if ent.label_.lower() == "symptom":
            feature_name = symptom_map.get(ent.text.lower())
            if feature_name in features:
                features[feature_name] = 1

    # Default attributes
    features["age"] = 30
    features["new_partners_last_3_months"] = 1
    features["condom_use_consistency_never"] = 0
    features["condom_use_consistency_sometimes"] = 1

    return features


# Model feature order
model_feature_column = [
    "age",
    "new_partners_last_3_months",
    "is_asymptomatic",
    "dysuria",
    "discharge_thin",
    "spotting",
    "discharge_thick",
    "discharge_yellow_green",
    "itching",
    "abdominal_pain",
    "ulcers_painful",
    "ulcer_painless",
    "odor_fishy",
    "urinary_frequency",
    "urinary_urgency",
    "fever",
    "condom_use_consistency_never",
    "condom_use_consistency_sometimes",
]


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
            .single()
            .execute()
        )
        if res and getattr(res, "data", None):
            return res.data
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


def update_session_title(session_id: str, title: str):
    supabase = get_supabase_client()

    supabase.table("chat_sessions").update({"title": title}).eq(
        "id", session_id
    ).execute()


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
