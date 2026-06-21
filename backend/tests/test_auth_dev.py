"""Dev-mode authentication fallback tests."""

# Human: Verify dev-only plain-text password fallback when admin_password_hash is empty.
# Agent: CALLS authenticate_admin; READS Settings with admin_password; no HTTP/DB; failure: assert on wrong password.
from app.auth.jwt import authenticate_admin
from app.config import Settings


# Human: Empty hash should allow login via admin_password plain text in dev settings.
# Agent: CALLS authenticate_admin with hash="" and admin_password; RETURNS bool; failure: assert wrong password rejected.
def test_dev_password_fallback_when_hash_empty() -> None:
    settings = Settings(admin_username="admin", admin_password_hash="", admin_password="admin")
    assert authenticate_admin("admin", "admin", settings)
    assert not authenticate_admin("admin", "wrong", settings)
