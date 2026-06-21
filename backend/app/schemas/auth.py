"""Authentication request/response schemas."""

from pydantic import BaseModel, Field


# Human: Login body validated before credential check; both fields required non-empty strings.
# Agent: HTTP request body for POST /auth/login; READS username/password; failure modes: 422 if min_length validation fails.
class LoginRequest(BaseModel):
    """Credentials for admin login."""

    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


# Human: OAuth2-style token payload returned on successful admin authentication.
# Agent: HTTP response shape; WRITES access_token from JWT encode; token_type defaults to bearer.
class TokenResponse(BaseModel):
    """JWT access token payload."""

    access_token: str
    token_type: str = "bearer"
