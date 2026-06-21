#!/bin/sh
set -e

# Human: Run Alembic once per stack start; sync worker can skip via SKIP_MIGRATIONS=1.
# Agent: CALLS alembic upgrade head unless SKIP_MIGRATIONS set; failure modes: migration error exits container.
if [ "${SKIP_MIGRATIONS:-0}" != "1" ]; then
  echo "Running database migrations..."
  alembic upgrade head
else
  echo "Skipping database migrations (SKIP_MIGRATIONS=1)."
fi

exec "$@"
