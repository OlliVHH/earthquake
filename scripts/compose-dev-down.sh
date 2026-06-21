#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "${1:-}" == "--destroy-volumes" ]]; then
  if [[ "${EARTHQUAKE_CONFIRM_DESTROY_DATA:-}" != "yes" ]]; then
    echo "Refusing to destroy volumes. Set EARTHQUAKE_CONFIRM_DESTROY_DATA=yes to confirm."
    exit 1
  fi
  docker compose down -v
  echo "Stack stopped and volumes removed."
else
  docker compose down
  echo "Stack stopped (volumes preserved)."
fi
