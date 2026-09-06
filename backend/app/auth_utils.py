import os
import logging
from typing import Optional, Dict
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from db import verify_user_token

load_dotenv()
logger = logging.getLogger(__name__)

ALLOW_UNAUTHENTICATED_TRAIN = (
    os.getenv("ALLOW_UNAUTHENTICATED_TRAIN", "false").lower() == "true"
)
ALLOW_UNAUTHENTICATED_RAG_UPLOAD = (
    os.getenv("ALLOW_UNAUTHENTICATED_RAG_UPLOAD", "false").lower() == "true"
)

# Comma-separated allowlist, same convention as ALLOWED_ORIGINS. Empty means
# "any logged-in user" (no extra restriction) - only endpoints that pass
# this into require_admin_auth actually enforce it.
ADMIN_EMAILS = {
    e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()
}

security = HTTPBearer(auto_error=False)  # Don't auto-raise error, handle manually


def require_admin_auth(allow_unauthenticated: bool, allowed_emails: Optional[set] = None):
    """
    Dependency factory for admin-only endpoints (training, document upload):
    requires a valid Bearer token, unless the given dev-mode flag allows
    bypassing it locally, optionally narrowed to a specific email allowlist.
    Shared so every caller gets the same (correctly awaited) token check,
    rather than each router re-implementing its own.
    """

    async def verify(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ) -> Dict:
        if allow_unauthenticated:
            logger.warning("Admin endpoint accessible without authentication (dev mode)")
            return {"id": "dev_user", "role": "admin"}

        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Please provide a valid Bearer token.",
            )

        user = await verify_user_token(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        if allowed_emails and (user.get("email") or "").lower() not in allowed_emails:
            raise HTTPException(
                status_code=403, detail="This account isn't authorized for this action."
            )

        return user

    return verify
