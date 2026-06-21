"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import auth, earthquakes, health, sync

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(earthquakes.router)
api_router.include_router(sync.router)
