"""Health check endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

# Human: Public health routes for load balancers and orchestration probes.
# Agent: HTTP GET /health; READS DB via get_db dependency.
router = APIRouter(tags=["health"])


# Human: Lightweight liveness probe — no DB so Docker healthcheck passes while migrations finish.
# Agent: HTTP GET /health; RETURNS {"status": "ok"}; no DB I/O.
@router.get("/health")
def health() -> dict[str, str]:
    """Public liveness probe for orchestration (process up)."""
    return {"status": "ok"}


# Human: Readiness probe including database connectivity for ops dashboards.
# Agent: HTTP GET /health/ready; READS DB (SELECT 1); failure modes: DB errors return 500.
@router.get("/health/ready")
def health_ready(db: Session = Depends(get_db)) -> dict[str, str]:
    """Readiness probe with DB connectivity check."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
