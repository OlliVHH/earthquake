"""Dev-mode authentication fallback tests."""

from app.auth.jwt import authenticate_admin
from app.config import Settings


def test_dev_password_fallback_when_hash_empty() -> None:
    settings = Settings(admin_username="admin", admin_password_hash="", admin_password="admin")
    assert authenticate_admin("admin", "admin", settings)
    assert not authenticate_admin("admin", "wrong", settings)
