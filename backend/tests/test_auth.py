"""Authentication helper tests."""

# Human: Unit tests for admin password verification and JWT create/decode round-trip.
# Agent: CALLS authenticate_admin, create_access_token, decode_access_token; READS Settings; no HTTP/DB.
from passlib.hash import bcrypt

from app.auth.jwt import authenticate_admin, create_access_token, decode_access_token
from app.config import Settings


# Human: Verify bcrypt login succeeds/fails and issued JWT decodes back to the admin username.
# Agent: CALLS authenticate_admin (bcrypt), create_access_token, decode_access_token; READS Settings fields; WRITES token string; failure: assert on wrong password or bad decode.
def test_authenticate_and_jwt_roundtrip() -> None:
    password = "test-password"
    settings = Settings(
        admin_username="admin",
        admin_password_hash=bcrypt.hash(password),
        jwt_secret="test-secret-key",
        jwt_expire_hours=1,
    )
    assert authenticate_admin("admin", password, settings)
    assert not authenticate_admin("admin", "wrong", settings)

    token = create_access_token("admin", settings)
    assert decode_access_token(token, settings) == "admin"
