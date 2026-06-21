"""Health check endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

# Human: Public health routes for load balancers and orchestration probes.
# Agent: HTTP GET /health; READS DB via get_db dependency.
router = APIRouter(tags=["health"])


# Human: Liveness endpoint that confirms the API process and database are reachable.
# Agent: HTTP GET /health; READS DB (SELECT 1); RETURNS {"status": "ok"}; failure modes: DB connection errors propagate as 500.
@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Public liveness probe with DB connectivity check."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
