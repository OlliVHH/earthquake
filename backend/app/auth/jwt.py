"""JWT creation and validation."""

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.hash import bcrypt

from app.config import Settings, get_settings
from app.errors import AppError


# Human: Compare a plaintext password against a stored bcrypt hash.
# Agent: READS hashed string; CALLS bcrypt.verify; RETURNS bool; failure modes: empty hash returns False.
def verify_password(plain: str, hashed: str) -> bool:
    """Check plaintext password against bcrypt hash."""
    if not hashed:
        return False
    return bcrypt.verify(plain, hashed)


# Human: Validate admin username/password against Settings (hash preferred, dev plaintext fallback).
# Agent: READS Settings (admin_username, admin_password_hash, admin_password); CALLS verify_password or plaintext compare; RETURNS bool; env vars: ADMIN_USERNAME, ADMIN_PASSWORD_HASH, ADMIN_PASSWORD.
def authenticate_admin(username: str, password: str, settings: Settings | None = None) -> bool:
    """Validate admin credentials from settings."""
    cfg = settings or get_settings()
    if username != cfg.admin_username:
        return False
    if cfg.admin_password_hash:
        return verify_password(password, cfg.admin_password_hash)
    # Development fallback when no hash is configured
    dev_password = getattr(cfg, "admin_password", "") or "admin"
    return password == dev_password


# Human: Issue a signed JWT for the given subject (admin username).
# Agent: READS JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS from Settings; WRITES signed token; RETURNS JWT string.
def create_access_token(subject: str, settings: Settings | None = None) -> str:
    """Issue a signed JWT for the given subject."""
    cfg = settings or get_settings()
    expire = datetime.now(UTC) + timedelta(hours=cfg.jwt_expire_hours)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, cfg.jwt_secret, algorithm=cfg.jwt_algorithm)


# Human: Validate a JWT and return the subject (username) claim.
# Agent: READS JWT_SECRET, JWT_ALGORITHM from Settings; CALLS jwt.decode; RETURNS subject str; failure modes: 401 INVALID_TOKEN on missing sub or JWTError (expired/signature).
def decode_access_token(token: str, settings: Settings | None = None) -> str:
    """Validate JWT and return subject username."""
    cfg = settings or get_settings()
    try:
        payload = jwt.decode(token, cfg.jwt_secret, algorithms=[cfg.jwt_algorithm])
        sub = payload.get("sub")
        if not sub:
            raise AppError("INVALID_TOKEN", "Invalid authentication token.", 401)
        return str(sub)
    except JWTError as exc:
        raise AppError("INVALID_TOKEN", "Invalid or expired authentication token.", 401) from exc
