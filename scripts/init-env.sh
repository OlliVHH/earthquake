#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  echo ".env already exists — skipping."
  exit 0
fi
cp "$ROOT/.env.example" "$ROOT/.env"
echo "Created .env from .env.example — edit ADMIN_PASSWORD_HASH before use."
