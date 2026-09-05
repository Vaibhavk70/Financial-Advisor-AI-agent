"""Auth Service — FastAPI application entry point."""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.database import Base, engine
from app.routes.auth import router as auth_router
from app.routes.users import router as users_router

# ─── 1. Structured Logging Configuration ────────────────────────────
from structlog.processors import CallsiteParameter, CallsiteParameterAdder

def add_service_context(logger, method_name, event_dict):
    event_dict["service"] = "auth-service"
    return event_dict

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        add_service_context,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        CallsiteParameterAdder(
            [
                CallsiteParameter.FILENAME,
                CallsiteParameter.LINENO,
                CallsiteParameter.FUNC_NAME,
            ]
        ),
        structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger(__name__)



# ─── 2. Lifespan Event Manager (Startup / Shutdown) ───────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handles startup and shutdown tasks for the application."""
    # ── Startup ──
    logger.info(
        "auth-service starting up",
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
    )

    # In development mode, verify/create database tables automatically
    if settings.DEBUG or settings.TESTING:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified/created")

    yield  # ← The application runs here while handling HTTP requests

    # ── Shutdown ──
    logger.info("auth-service shutting down")
    await engine.dispose()  # Close all database connections cleanly in pool


# ─── 3. FastAPI Application Instance ─────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## AI Financial Advisor — Authentication Service

Handles user registration, login, JWT token rotation, and profile management.

### Key Features:
- 🔐 **JWT Auth**: Access & Refresh token rotation
- 🚫 **Logout Revocation**: Instant token invalidation via Redis
- 👤 **User Profiles**: Financial risk & goal tracking
- 🛡️ **Security**: Bcrypt password hashing, rate limiting ready
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ─── 4. CORS Middleware ───────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ─── 5. Prometheus Metrics Instrumentation ────────────────────────────
Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    excluded_handlers=["/health", "/metrics"],
).instrument(app).expose(app, include_in_schema=False)

# ─── 6. Include API Routers ───────────────────────────────────────────
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)


# ─── 7. System Endpoints ──────────────────────────────────────────────
@app.get("/health", tags=["System"], summary="Health check endpoint")
async def health_check() -> dict:
    """Endpoint checked by Docker Healthcheck and Load Balancers."""
    return {
        "status": "healthy",
        "service": "auth-service",
        "version": settings.APP_VERSION,
    }


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "service": "AI Financial Advisor — Auth Service",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }