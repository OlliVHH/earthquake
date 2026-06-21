"""Generate bcrypt hash for ADMIN_PASSWORD_HASH."""

from passlib.hash import bcrypt

# Human: CLI helper to print a bcrypt hash for ADMIN_PASSWORD_HASH env configuration.
# Agent: READS optional argv[1] password (defaults to "admin"); CALLS bcrypt.hash; WRITES hash to stdout; no DB/HTTP.
if __name__ == "__main__":
    import sys

    password = sys.argv[1] if len(sys.argv) > 1 else "admin"
    print(bcrypt.hash(password))
