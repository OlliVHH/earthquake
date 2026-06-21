"""Generate bcrypt hash for ADMIN_PASSWORD_HASH."""

from passlib.hash import bcrypt

if __name__ == "__main__":
    import sys

    password = sys.argv[1] if len(sys.argv) > 1 else "admin"
    print(bcrypt.hash(password))
