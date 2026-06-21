"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import auth, earthquakes, health, sync

# Human: Mount all v1 sub-routers under a single /api/v1 prefix for the FastAPI app.
# Agent: READS auth, earthquakes, health, sync routers; WRITES api_router; HTTP mounts /api/v1/*.
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(earthquakes.router)
api_router.include_router(sync.router)
