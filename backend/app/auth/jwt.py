"""JWT creation and validation."""

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.hash import bcrypt

from app.config import Settings, get_settings
from app.errors import AppError


def verify_password(plain: str, hashed: str) -> bool:
    """Check plaintext password against bcrypt hash."""
    if not hashed:
        return False
    return bcrypt.verify(plain, hashed)


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


def create_access_token(subject: str, settings: Settings | None = None) -> str:
    """Issue a signed JWT for the given subject."""
    cfg = settings or get_settings()
    expire = datetime.now(UTC) + timedelta(hours=cfg.jwt_expire_hours)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, cfg.jwt_secret, algorithm=cfg.jwt_algorithm)


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
