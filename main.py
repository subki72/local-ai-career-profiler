"""FastAPI application entrypoint for the CV Nexus backend service."""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from src.api.routes import router as api_router
from src.config import Settings, configure_logging, get_settings

logger = logging.getLogger(__name__)

APP_VERSION = "1.0.0"


async def add_security_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach baseline HTTP security headers to every API response."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unhandled errors internally while returning a safe generic 500 response."""
    logger.exception(
        "Unhandled server exception during %s %s.",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application instance.

    Args:
        settings: Optional Settings override for testing or custom deployments.

    Returns:
        Configured FastAPI application with CORS, health probe, and routes.
    """
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)

    application = FastAPI(
        title="CV Nexus API",
        description="Privacy-first local AI CV analysis and job matching engine",
        version=APP_VERSION,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    application.middleware("http")(add_security_headers)
    application.add_exception_handler(Exception, unhandled_exception_handler)

    @application.get("/health", tags=["Operations"])
    async def health_check() -> dict[str, str]:
        """Return service liveness metadata for container and load-balancer probes."""
        return {
            "status": "healthy",
            "service": "cv-nexus-api",
            "version": APP_VERSION,
        }

    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()


if __name__ == "__main__":
    logger.info("Starting CV Nexus Backend Server on 0.0.0.0:8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
