import re
import logging
from fastapi import APIRouter, HTTPException, status, Header, Request
from pydantic import BaseModel, EmailStr, field_validator
from supabase_client import get_supabase_client
from supabase import create_client
from supabase_auth.errors import AuthApiError
from openai import AsyncOpenAI, AuthenticationError
import os
from db import verify_user_token, get_user_openai_settings
from typing import Optional
import asyncio
from rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("Password must contain at least one symbol")
    return password


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, v):
        return validate_password_strength(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password_strength(cls, v):
        return validate_password_strength(v)


def _signup_sync(request: SignupRequest):
    auth_client = create_client(
        os.getenv("VITE_SUPABASE_URL"),
        os.getenv("VITE_SUPABASE_ANON_KEY"),
    )
    auth_res = auth_client.auth.sign_up(
        {
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "first_name": request.first_name,
                    "last_name": request.last_name,
                }
            },
        }
    )

    if auth_res.user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Signup failed"
        )

    profile_data = {
        "user_id": auth_res.user.id,
        "email": request.email,
        "first_name": request.first_name,
        "last_name": request.last_name,
    }

    # Insert profile with service role (bypasses RLS)
    supabase = get_supabase_client()
    try:
        profile_result = supabase.table("user_profiles").insert(profile_data).execute()

        # Check if insert was successful
        if not profile_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user profile",
            )
    except Exception as profile_error:
        # If service role insert fails, try with user session context
        if auth_res.session and auth_res.session.access_token:
            # Create a new supabase client with user context
            user_supabase = create_client(
                os.getenv("VITE_SUPABASE_URL"),
                os.getenv("VITE_SUPABASE_ANON_KEY"),  # Use anon key for user context
            )
            user_supabase.auth.set_session(
                auth_res.session.access_token, auth_res.session.refresh_token
            )

            try:
                profile_result = (
                    user_supabase.table("user_profiles").insert(profile_data).execute()
                )
            except Exception as user_insert_error:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Profile creation failed: {str(user_insert_error)}",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Profile creation failed: {str(profile_error)}",
            )

    # Check if session exists (may be None if email confirmation is required)
    access_token = auth_res.session.access_token if auth_res.session else None

    return {
        "access_token": access_token,
        "user": {
            "id": auth_res.user.id,
            "email": request.email,
            "first_name": request.first_name,
            "last_name": request.last_name,
        },
        "message": (
            "Signup successful. Please check your email to confirm your account."
            if not access_token
            else "Signup successful."
        ),
    }


@router.post("/signup")
async def signup(request: SignupRequest):
    try:
        return await asyncio.to_thread(_signup_sync, request)

    except HTTPException:
        raise  # let our own intentional 4xx responses through unchanged

    except AuthApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server Error: {str(e)}",
        )


def _login_sync(request: LoginRequest):
    # Fresh client, not the shared one - signing in on the shared client makes supabase-py silently swap its Authorization header to this user's own token, breaking every other request using it afterward.
    auth_client = create_client(
        os.getenv("VITE_SUPABASE_URL"),
        os.getenv("VITE_SUPABASE_ANON_KEY"),
    )
    auth_res = auth_client.auth.sign_in_with_password(
        {"email": request.email, "password": request.password}
    )

    if auth_res.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    if auth_res.session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Please verify your email or try again.",
        )

    supabase = get_supabase_client()
    profile_res = (
        supabase.table("user_profiles")
        .select("*")
        .eq("user_id", auth_res.user.id)
        .execute()
    )
    if not profile_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile found for this account. Please contact support.",
        )
    profile = profile_res.data[0]

    return {
        "access_token": auth_res.session.access_token,
        "user": {
            "id": auth_res.user.id,
            "email": profile["email"],
            "first_name": profile["first_name"],
            "last_name": profile["last_name"],
        },
    }


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, login_data: LoginRequest):
    try:
        return await asyncio.to_thread(_login_sync, login_data)

    except HTTPException:
        raise  # let our own intentional 4xx responses through unchanged

    except AuthApiError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}",
        )


def _logout_sync():
    supabase = get_supabase_client()
    supabase.auth.sign_out()


@router.post("/logout")
async def logout():
    try:
        await asyncio.to_thread(_logout_sync)
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}",
        )


def _forgot_password_sync(email: str):
    supabase = get_supabase_client()
    frontend_url = os.getenv(
        "FRONTEND_URL", "http://localhost:5173"
    )
    try:
        supabase.auth.reset_password_for_email(
            email, {"redirect_to": f"{frontend_url}/reset-password"}
        )
    except Exception as e:
        # Same generic response either way - never leak whether this email exists (prevents account enumeration).
        logger.warning(f"Password reset email error: {str(e)}")


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, body: ForgotPasswordRequest):
    await asyncio.to_thread(_forgot_password_sync, body.email)
    return {
        "message": "If an account exists for that email, a reset link has been sent"
    }


def _reset_password_sync(user_id: str, new_password: str):
    supabase = get_supabase_client()
    supabase.auth.admin.update_user_by_id(user_id, {"password": new_password})


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    user = await verify_user_token(body.token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired reset link")
    await asyncio.to_thread(_reset_password_sync, user["id"], body.new_password)
    return {"message": "Password updated successfully. Please log in"}


def _strip_openai_key(profile: dict) -> dict:
    # Never let the raw key reach the frontend - it gets persisted straight into localStorage. Swap it for a boolean the UI can show status from.
    profile["has_custom_openai_key"] = bool(profile.pop("openai_api_key", None))
    return profile


def _get_profile_sync(user_id: str) -> dict:
    supabase = get_supabase_client()
    res = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()

    # If Supabase client returns an error or no data, handle accordingly
    if getattr(res, "error", None):
        raise HTTPException(status_code=500, detail=str(res.error))

    if not res.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    return _strip_openai_key(res.data[0])


# GET current user's profile
@router.get("/profile")
async def get_profile(authorization: Optional[str] = Header(None)):
    """
    Retrieve the authenticated user's profile from `user_profiles`.
    Requires Authorization: Bearer <token>
    """
    if not authorization:
        # Explicit 401 instead of FastAPI 422 when header missing
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "")
    user = await verify_user_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await asyncio.to_thread(_get_profile_sync, user["id"])


def _update_profile_sync(user_id: str, profile_update: dict) -> dict:
    # openai_api_key has its own dedicated, validated endpoint below - never settable through this generic passthrough.
    profile_update.pop("openai_api_key", None)

    supabase = get_supabase_client()
    res = (
        supabase.table("user_profiles")
        .update(profile_update)
        .eq("user_id", user_id)
        .execute()
    )

    if getattr(res, "error", None):
        raise HTTPException(status_code=500, detail=str(res.error))

    # Return the updated profile (you may want to re-select to reflect DB defaults/triggers)
    refreshed = (
        supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
    )
    if getattr(refreshed, "error", None):
        raise HTTPException(status_code=500, detail=str(refreshed.error))
    if not refreshed.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _strip_openai_key(refreshed.data[0])


# Optional: allow the user to update their profile (PATCH)
@router.patch("/profile")
async def update_profile(profile_update: dict, authorization: str = Header(...)):
    """
    Partial update to the current user's profile.
    Example payload: { "first_name": "Ava", "phone": "555-1234" }
    """
    token = authorization.replace("Bearer ", "")
    user = await verify_user_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not profile_update:
        raise HTTPException(status_code=400, detail="No update data provided")

    return await asyncio.to_thread(_update_profile_sync, user["id"], profile_update)


# Kept small and explicit, not any string - this becomes a real API call.
# chat.py imports this same list for its fallback.
ALLOWED_CUSTOM_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
DEFAULT_CUSTOM_MODEL = "gpt-4o"


class OpenAIKeyRequest(BaseModel):
    api_key: Optional[str] = None  # omit/empty to update the model only (see below) - use DELETE to clear
    model: Optional[str] = None  # defaults to DEFAULT_CUSTOM_MODEL when omitted


def _set_openai_key_sync(user_id: str, api_key: Optional[str], model: Optional[str]) -> None:
    supabase = get_supabase_client()
    res = (
        supabase.table("user_profiles")
        .update({"openai_api_key": api_key, "openai_model": model})
        .eq("user_id", user_id)
        .execute()
    )
    if getattr(res, "error", None):
        raise HTTPException(status_code=500, detail=str(res.error))


@router.put("/openai-key")
async def set_openai_key(body: OpenAIKeyRequest, authorization: str = Header(...)):
    """
    Set a personal OpenAI API key (+ model), or - with api_key omitted and a
    key already on file - change just the model choice without re-submitting
    the key. Use DELETE /auth/openai-key to actually clear it; this endpoint
    never clears on its own, so there's no ambiguity between "not provided"
    and "please remove." Never returns the raw key back - see
    _strip_openai_key - only has_custom_openai_key/openai_model.
    """
    token = authorization.replace("Bearer ", "")
    user = await verify_user_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    submitted_key = (body.api_key or "").strip() or None

    if submitted_key:
        model = body.model if body.model in ALLOWED_CUSTOM_MODELS else DEFAULT_CUSTOM_MODEL
        # Validate before storing - a bad/revoked key should fail loudly
        # here, not confusingly mid-conversation later.
        try:
            await AsyncOpenAI(api_key=submitted_key).models.list()
        except AuthenticationError:
            raise HTTPException(status_code=400, detail="That API key was rejected by OpenAI - double check it.")
        except Exception as e:
            logger.warning(f"OpenAI key validation error: {e}")
            raise HTTPException(status_code=400, detail="Could not verify that API key right now. Please try again.")

        await asyncio.to_thread(_set_openai_key_sync, user["id"], submitted_key, model)
        return {"has_custom_openai_key": True, "openai_model": model}

    # No new key submitted - a model-only change, but only meaningful if a
    # key is already on file to pair it with.
    existing_key, _ = await get_user_openai_settings(user["id"])
    if not existing_key:
        raise HTTPException(status_code=400, detail="No API key on file yet - add one first.")
    if body.model not in ALLOWED_CUSTOM_MODELS:
        raise HTTPException(status_code=400, detail="Unrecognized model choice.")

    await asyncio.to_thread(_set_openai_key_sync, user["id"], existing_key, body.model)
    return {"has_custom_openai_key": True, "openai_model": body.model}


@router.delete("/openai-key")
async def clear_openai_key(authorization: str = Header(...)):
    """Remove the current user's personal API key and model choice entirely."""
    token = authorization.replace("Bearer ", "")
    user = await verify_user_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    await asyncio.to_thread(_set_openai_key_sync, user["id"], None, None)
    return {"has_custom_openai_key": False, "openai_model": None}
