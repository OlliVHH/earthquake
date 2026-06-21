"""FastAPI application entrypoint."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.errors import register_exception_handlers

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(title="Earthquake Analytics API", version="1.0.0")
    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
