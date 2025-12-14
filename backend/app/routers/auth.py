from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel, EmailStr
from supabase_client import get_supabase_client
from supabase import create_client
from gotrue.errors import AuthApiError
import os
from routers.utils import verify_user_token
from typing import Optional


router = APIRouter(prefix="/auth", tags=["Authentication"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    access_token: str
    refresh_token: str


@router.post("/signup")
async def signup(request: SignupRequest):
    try:
        supabase = get_supabase_client()
        auth_res = supabase.auth.sign_up(
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
        try:
            profile_result = (
                supabase.table("user_profiles").insert(profile_data).execute()
            )

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
                    os.getenv(
                        "VITE_SUPABASE_ANON_KEY"
                    ),  # Use anon key for user context
                )
                user_supabase.auth.set_session(
                    auth_res.session.access_token, auth_res.session.refresh_token
                )

                try:
                    profile_result = (
                        user_supabase.table("user_profiles")
                        .insert(profile_data)
                        .execute()
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

    except AuthApiError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server Error: {str(e)}",
        )


@router.post("/login")
async def login(request: LoginRequest):
    try:
        supabase = get_supabase_client()

        auth_res = supabase.auth.sign_in_with_password(
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

        profile = (
            supabase.table("user_profiles")
            .select("*")
            .eq("user_id", auth_res.user.id)
            .single()
            .execute()
        )

        return {
            "access_token": auth_res.session.access_token,
            "user": {
                "id": auth_res.user.id,
                "email": profile.data["email"],
                "first_name": profile.data["first_name"],
                "last_name": profile.data["last_name"],
            },
        }

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


@router.get("/google")
async def google_login():
    try:
        supabase = get_supabase_client()

        # redirect_url = f"{os.getenv('FRONT_END_LINK')}/auth/callback"
        redirect_url = "http://localhost:5173//auth/callback"

        auth_res = supabase.auth.sign_in_with_oauth(
            {"provider": "google", "options": {"redirect_to": redirect_url}}
        )

        return {"url": auth_res.url, "provider": "google"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google OAuth Initialization failed: {str(e)}",
        )


@router.post("/google/callback")
async def google_callback(request: GoogleAuthRequest):
    try:
        supabase = get_supabase_client()
        session_response = supabase.auth.set_session(
            request.access_token, request.refresh_token
        )

        if not session_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to authenticate with Google",
            )

        user = session_response.user
        email = user.email

        existing_profile = (
            supabase.table("user_profiles").select("*").eq("email", email).execute()
        )

        if existing_profile.data and len(existing_profile.data) > 0:
            profile = existing_profile.data[0]

            supabase.table("user_profiles").update(
                {
                    "user_id": user.id,
                    "auth_provider": "email, google",
                }
            ).eq("email", email).execute()

            return {
                "access_token": session_response.session.access_token,
                "user": {
                    "id": user.id,
                    "email": profile["email"],
                    "first_name": profile["first_name"],
                    "last_name": profile["last_name"],
                },
                "message": "Google account linked successfully",
                "linked": True,
            }
        else:
            user_metadata = user.user_metadata or {}

            profile_data = {
                "user_id": user.id,
                "email": email,
                "first_name": (
                    user_metadata.get("full_name").split()[0]
                    if user_metadata.get("full_name")
                    else user_metadata.get("given_name", "User")
                ),
                "last_name": (
                    user_metadata.get("full_name").split()[-1]
                    if user_metadata.get("full_name")
                    and len(user_metadata.get("full_name", "").split()) > 1
                    else user_metadata.get("family_name", "")
                ),
            }

            supabase.table("user_profiles").insert(profile_data).execute()

            return {
                "access_token": session_response.session.access_token,
                "user": {
                    "id": user.id,
                    "email": email,
                    "first_name": profile_data["first_name"],
                    "last_name": profile_data["last_name"],
                },
                "message": "Google signup successfully",
                "linked": False,
            }
    except AuthApiError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google authentication error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)},",
        )


@router.post("/logout")
async def logout():
    try:
        supabase = get_supabase_client()
        supabase.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}",
        )


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
    user = verify_user_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    supabase = get_supabase_client()
    res = (
        supabase.table("user_profiles")
        .select("*")
        .eq("user_id", user["id"])
        .single()
        .execute()
    )

    # If Supabase client returns an error or no data, handle accordingly
    if getattr(res, "error", None):
        raise HTTPException(status_code=500, detail=str(res.error))

    if not res.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Return the profile record
    return res.data


# Optional: allow the user to update their profile (PATCH)
@router.patch("/profile")
async def update_profile(profile_update: dict, authorization: str = Header(...)):
    """
    Partial update to the current user's profile.
    Example payload: { "first_name": "Ava", "phone": "555-1234" }
    """
    token = authorization.replace("Bearer ", "")
    user = verify_user_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not profile_update:
        raise HTTPException(status_code=400, detail="No update data provided")

    supabase = get_supabase_client()
    res = (
        supabase.table("user_profiles")
        .update(profile_update)
        .eq("user_id", user["id"])
        .execute()
    )

    if getattr(res, "error", None):
        raise HTTPException(status_code=500, detail=str(res.error))

    # Return the updated profile (you may want to re-select to reflect DB defaults/triggers)
    refreshed = (
        supabase.table("user_profiles")
        .select("*")
        .eq("user_id", user["id"])
        .single()
        .execute()
    )
    if getattr(refreshed, "error", None):
        raise HTTPException(status_code=500, detail=str(refreshed.error))
    return refreshed.data
