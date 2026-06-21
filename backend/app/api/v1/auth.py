"""Authentication routes."""

from fastapi import APIRouter

from app.auth.jwt import authenticate_admin, create_access_token
from app.config import get_settings
from app.errors import AppError
from app.schemas.auth import LoginRequest, TokenResponse

# Human: Admin login routes under /auth for JWT issuance.
# Agent: HTTP POST /auth/login; READS env via get_settings; CALLS jwt helpers.
router = APIRouter(prefix="/auth", tags=["auth"])


# Human: Validate admin credentials and return a signed JWT access token.
# Agent: HTTP POST /auth/login; READS ADMIN_* env via Settings; CALLS authenticate_admin, create_access_token; RETURNS TokenResponse; failure modes: 401 INVALID_CREDENTIALS.
@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    """Authenticate admin and return JWT."""
    settings = get_settings()
    if not authenticate_admin(body.username, body.password, settings):
        raise AppError("INVALID_CREDENTIALS", "Invalid username or password.", 401)
    token = create_access_token(body.username, settings)
    return TokenResponse(access_token=token)
