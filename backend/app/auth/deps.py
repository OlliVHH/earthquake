"""FastAPI dependencies for authentication."""

from typing import Annotated

from fastapi import Depends, Header

from app.auth.jwt import decode_access_token
from app.errors import AppError


# Human: FastAPI dependency that extracts the authenticated username from a Bearer JWT.
# Agent: READS Authorization header; CALLS decode_access_token; RETURNS subject username; failure modes: 401 UNAUTHORIZED when header missing/malformed, 401 INVALID_TOKEN from jwt module.
def get_current_user(authorization: Annotated[str | None, Header()] = None) -> str:
    """Extract and validate Bearer token from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("UNAUTHORIZED", "Authentication required.", 401)
    token = authorization.removeprefix("Bearer ").strip()
    return decode_access_token(token)
