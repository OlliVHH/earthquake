"""FastAPI application entrypoint."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.errors import register_exception_handlers

# Human: Configure root logging before the app factory runs so startup and handler logs are visible.
# Agent: WRITES logging config at import; no env vars; failure modes: misconfigured level hides diagnostics.
logging.basicConfig(level=logging.INFO)


# Human: Factory that wires middleware, error handlers, and the versioned API router.
# Agent: CALLS register_exception_handlers, include_router(api_router); RETURNS configured FastAPI instance.
def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(title="Earthquake Analytics API", version="1.0.0")
    register_exception_handlers(app)

    # Human: Permissive CORS for local/dev frontends; tighten origins before production deployment.
    # Agent: HTTP middleware; allow_origins=["*"]; failure modes: overly broad origins in prod.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


# Human: Module-level ASGI app used by uvicorn and Docker entrypoints.
# Agent: CALLS create_app(); READS api_router and exception handlers; no DB at import.
app = create_app()
