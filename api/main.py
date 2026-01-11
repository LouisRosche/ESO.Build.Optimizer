"""
ESO Build Optimizer API

A FastAPI-based backend for the ESO Build Optimizer system.
Provides endpoints for combat run tracking, recommendation generation,
and feature database access.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.core.config import settings
from api.core.rate_limit import RateLimitMiddleware
from api.models.database import init_db
from api.models.schemas import ErrorResponse, HealthResponse
from api.routes import auth, features, recommendations, runs

# =============================================================================
# Logging Configuration
# =============================================================================

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Application Lifespan
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Runs startup and shutdown logic for the application.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize database tables
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title=settings.app_name,
    description="""
ESO Build Optimizer API provides intelligent ESO performance analytics.

## Features

* **Combat Runs** - Submit and track combat encounter metrics
* **Recommendations** - Get AI-generated build improvement suggestions
* **Percentile Rankings** - Compare performance against similar players
* **Feature Database** - Access skills, gear sets, and game data

## Authentication

All endpoints (except /health) require JWT authentication.
Use the `/api/v1/auth/login` endpoint to obtain a token.
    """,
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# =============================================================================
# Middleware
# =============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)


# Request Timing Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to all responses."""
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response


# Rate Limiting Middleware (applied after CORS)
app.add_middleware(RateLimitMiddleware)


# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.debug(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.debug(f"{request.method} {request.url.path} - {response.status_code}")
    return response


# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail if isinstance(exc.detail, str) else "Error",
            detail=str(exc.detail) if not isinstance(exc.detail, str) else None,
            status_code=exc.status_code,
        ).model_dump(),
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle request validation errors with details."""
    errors = exc.errors()
    error_messages = []

    for error in errors:
        loc = " -> ".join(str(x) for x in error["loc"])
        msg = error["msg"]
        error_messages.append(f"{loc}: {msg}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation Error",
            detail="; ".join(error_messages),
            status_code=422,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception(f"Unexpected error: {exc}")

    # Don't expose internal errors in production
    if settings.environment == "production":
        detail = "An unexpected error occurred"
    else:
        detail = str(exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=detail,
            status_code=500,
        ).model_dump(),
    )


# =============================================================================
# Health Check Endpoint
# =============================================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check",
    description="Check if the API is running and database is connected.",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the current status of the API and database connection.
    Used by load balancers and monitoring systems.
    """
    # TODO: Add actual database connection check
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        database="connected",
    )


@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    tags=["Health"],
    include_in_schema=False,
)
async def health_check_v1() -> HealthResponse:
    """Alias for health check at API path."""
    return await health_check()


# =============================================================================
# API Routes
# =============================================================================

# Include all routers under /api/v1 prefix
app.include_router(
    auth.router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    runs.router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    recommendations.router,
    prefix=settings.api_v1_prefix,
)

app.include_router(
    features.router,
    prefix=settings.api_v1_prefix,
)


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get(
    "/",
    tags=["Root"],
    summary="API Information",
    description="Get basic API information and links to documentation.",
)
async def root() -> dict[str, Any]:
    """
    Root endpoint with API information.

    Provides links to documentation and basic API info.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "documentation": {
            "openapi": "/api/openapi.json",
            "swagger": "/api/docs",
            "redoc": "/api/redoc",
        },
        "endpoints": {
            "auth": f"{settings.api_v1_prefix}/auth",
            "runs": f"{settings.api_v1_prefix}/runs",
            "features": f"{settings.api_v1_prefix}/features",
            "health": "/health",
        },
    }


# =============================================================================
# Development Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
