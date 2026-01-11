# FastAPI Production Best Practices

> **Last Updated**: January 2026
> **Source**: [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices), [FastAPI Docs](https://fastapi.tiangolo.com/)

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Application Lifecycle](#application-lifecycle)
3. [Async Best Practices](#async-best-practices)
4. [Pydantic Validation](#pydantic-validation)
5. [JWT Authentication](#jwt-authentication)
6. [Rate Limiting](#rate-limiting)
7. [Middleware Configuration](#middleware-configuration)
8. [Health Check Endpoints](#health-check-endpoints)
9. [Error Handling](#error-handling)
10. [Dependencies](#dependencies)
11. [Configuration Management](#configuration-management)
12. [Database Best Practices](#database-best-practices)
13. [Security Checklist](#security-checklist)
14. [Testing](#testing)
15. [Production Server Configuration](#production-server-configuration)

---

## Project Structure

Organize by **domain/module** rather than file type for scalability. Our implementation uses a hybrid approach:

```
api/
├── main.py                 # FastAPI app initialization, middleware, exception handlers
├── __init__.py
├── core/                   # Shared infrastructure
│   ├── config.py           # Pydantic BaseSettings
│   ├── security.py         # JWT, password hashing, auth dependencies
│   └── rate_limit.py       # Rate limiting middleware and utilities
├── models/                 # Data layer
│   ├── database.py         # SQLAlchemy models and engine
│   └── schemas.py          # Pydantic schemas for all domains
└── routes/                 # API endpoints by domain
    ├── auth.py             # Authentication endpoints
    ├── runs.py             # Combat runs endpoints
    ├── recommendations.py  # Recommendations endpoints
    └── features.py         # Feature database endpoints
```

**Key principles:**
- `core/` contains cross-cutting concerns (config, security, rate limiting)
- `models/` separates database models from Pydantic schemas
- `routes/` organizes endpoints by domain with their own routers
- Each router uses a prefix (e.g., `/auth`, `/runs`) and tags for OpenAPI

---

## Application Lifecycle

### Lifespan Context Manager (Modern Pattern)

Use the `lifespan` context manager instead of deprecated `@app.on_event`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info(f"Starting {settings.app_name}")
    await init_db()
    logger.info("Database initialized")

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down application")
    # Clean up connections, flush caches, etc.

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)
```

### OpenAPI Configuration

Configure documentation endpoints and metadata:

```python
tags_metadata = [
    {"name": "Health", "description": "Health check endpoints"},
    {"name": "Auth", "description": "Authentication endpoints"},
    {"name": "Runs", "description": "Combat run endpoints"},
]

app = FastAPI(
    title="ESO Build Optimizer API",
    description="""
    API for ESO performance analytics.

    ## Features
    * **Combat Runs** - Track encounter metrics
    * **Recommendations** - AI-generated suggestions
    """,
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    openapi_tags=tags_metadata,
)
```

---

## Async Best Practices

### I/O-Intensive Routes

Use `async def` for database queries, HTTP calls, and file operations:

```python
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/runs")
async def get_runs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
) -> list[CombatRunResponse]:
    result = await db.execute(
        select(CombatRun).where(CombatRun.player_id == current_user.id)
    )
    return result.scalars().all()
```

**Never block the event loop:**
```python
# BAD: Blocks event loop
@router.get("/runs")
async def get_runs():
    time.sleep(1)  # Blocks everything!
    return {"data": "..."}

# GOOD: Non-blocking
import asyncio

@router.get("/runs")
async def get_runs():
    await asyncio.sleep(1)  # Yields control
    return {"data": "..."}
```

### CPU-Intensive Tasks

Offload heavy computation to background tasks or process pools:

```python
from fastapi import BackgroundTasks
from concurrent.futures import ProcessPoolExecutor
import asyncio

# Option 1: Background Tasks (fire-and-forget)
@router.post("/analyze")
async def analyze_run(
    run_id: str,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(compute_percentiles, run_id)
    return {"status": "processing"}

# Option 2: ProcessPoolExecutor (need result)
executor = ProcessPoolExecutor(max_workers=4)

@router.get("/heavy-compute")
async def heavy_compute():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, cpu_bound_function)
    return result
```

### Request Timing Middleware

Track response times for monitoring:

```python
import time
from fastapi import Request

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response
```

---

## Pydantic Validation

### Pydantic v2 Patterns

Use `model_config` with `ConfigDict` instead of inner `class Config`:

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime

class CombatRunResponse(BaseModel):
    """Schema with Pydantic v2 configuration."""
    model_config = ConfigDict(
        from_attributes=True,      # Allow ORM model conversion
        populate_by_name=True,     # Accept field aliases
    )

    run_id: UUID
    player_class: ESOClass = Field(..., alias="class")
    timestamp: datetime
    dps: float = Field(..., ge=0.0, le=500000.0)
```

### Field Validators

Use `field_validator` with explicit modes:

```python
from pydantic import field_validator

class Settings(BaseSettings):
    jwt_secret_key: str
    environment: str = "development"

    @field_validator("jwt_secret_key", mode="after")
    @classmethod
    def validate_jwt_secret(cls, v, info):
        """Validate after all fields are set."""
        environment = info.data.get("environment", "development")
        if environment == "production" and v == "CHANGE_ME":
            raise ValueError("Must set JWT_SECRET_KEY in production")
        return v

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        """Parse before validation - convert string to list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
```

### String Enums for API Compatibility

Use `str, Enum` for JSON-serializable enums:

```python
from enum import Enum

class ContentType(str, Enum):
    DUNGEON = "dungeon"
    TRIAL = "trial"
    ARENA = "arena"
    OVERWORLD = "overworld"

class ESOClass(str, Enum):
    DRAGONKNIGHT = "Dragonknight"
    NIGHTBLADE = "Nightblade"
    SORCERER = "Sorcerer"
    TEMPLAR = "Templar"
    WARDEN = "Warden"
    NECROMANCER = "Necromancer"
    ARCANIST = "Arcanist"
```

### Annotated Type Patterns

Use `Annotated` for reusable dependency injection:

```python
from typing import Annotated
from fastapi import Depends

# Define reusable type aliases
CurrentUser = Annotated[User, Depends(get_current_active_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]

# Use in routes - clean and readable
@router.get("/me")
async def get_profile(
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    return UserResponse.model_validate(current_user)
```

---

## JWT Authentication

### Security Configuration

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt

# Password hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Configurable rounds
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# JWT Bearer scheme
security = HTTPBearer(auto_error=True)
```

### Token Creation

Implement access and refresh token patterns:

```python
from datetime import datetime, timedelta, timezone
from uuid import UUID

def create_access_token(user_id: UUID, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=30))

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "type": "access",
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

def create_refresh_token(user_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=7)

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "type": "refresh",
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
```

### Token Validation and User Retrieval

```python
from pydantic import BaseModel

class TokenPayload(BaseModel):
    sub: UUID
    exp: datetime
    iat: datetime

def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenPayload(
            sub=UUID(payload["sub"]),
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    token_data = decode_token(credentials.credentials)

    # Check expiration
    if token_data.exp < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user
    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    return user

# Type alias for clean routes
CurrentUser = Annotated[User, Depends(get_current_user)]
```

### Auth Endpoints Pattern

```python
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    # Find user
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: CurrentUser) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(current_user.id),
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )
```

---

## Rate Limiting

### In-Memory Rate Limiter (Development/Single Instance)

```python
from collections import defaultdict
import time

class InMemoryRateLimiter:
    """Sliding window rate limiter for development."""

    def __init__(self):
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.cleanup_interval = 60
        self.last_cleanup = time.time()

    def _cleanup_old_requests(self, key: str, window_seconds: int):
        cutoff = time.time() - window_seconds
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]

    def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        """
        Returns (is_allowed, remaining_requests, retry_after_seconds).
        """
        self._cleanup_old_requests(key, window_seconds)
        current = len(self.requests[key])

        if current >= max_requests:
            oldest = min(self.requests[key]) if self.requests[key] else time.time()
            retry_after = int(oldest + window_seconds - time.time())
            return False, 0, max(1, retry_after)

        self.requests[key].append(time.time())
        return True, max_requests - len(self.requests[key]), 0

rate_limiter = InMemoryRateLimiter()
```

### Rate Limit Middleware

```python
from fastapi import Request
from starlette.responses import JSONResponse

class RateLimitMiddleware:
    """ASGI middleware for rate limiting."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Skip health checks
        if request.url.path in ["/health", "/api/v1/health"]:
            await self.app(scope, receive, send)
            return

        # Get client identifier
        forwarded = request.headers.get("X-Forwarded-For")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (
            request.client.host if request.client else "unknown"
        )
        key = f"ip:{client_ip}:{request.url.path}"

        # Check rate limit
        allowed, remaining, retry_after = rate_limiter.is_allowed(
            key,
            settings.rate_limit_requests_per_minute,
            60,
        )

        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(settings.rate_limit_requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                },
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

# Register after CORS middleware
app.add_middleware(RateLimitMiddleware)
```

### Per-Endpoint Rate Limits

Create a dependency for custom limits on specific endpoints:

```python
def rate_limit_dependency(requests_per_minute: int | None = None):
    """Create rate limit dependency with custom limits."""
    limit = requests_per_minute or settings.rate_limit_requests_per_minute

    async def dependency(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        key = f"custom:{client_ip}:{request.url.path}"

        allowed, _, retry_after = rate_limiter.is_allowed(key, limit, 60)

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )

    return Depends(dependency)

# Usage: Stricter limit on expensive endpoint
@router.post("/analyze", dependencies=[rate_limit_dependency(10)])
async def analyze_run(run_id: str):
    ...
```

### Production Rate Limiting with Redis

For multi-instance deployments, use Redis:

```python
import redis.asyncio as redis

class RedisRateLimiter:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        pipe = self.redis.pipeline()
        now = time.time()
        window_start = now - window_seconds

        # Remove old entries and count current
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window_seconds)

        results = await pipe.execute()
        current_count = results[1]

        if current_count >= max_requests:
            return False, 0, window_seconds

        return True, max_requests - current_count - 1, 0
```

---

## Middleware Configuration

### GZip Compression

Compress responses larger than the minimum threshold:

```python
from fastapi.middleware.gzip import GZipMiddleware

# Compress responses > 500 bytes
app.add_middleware(GZipMiddleware, minimum_size=500)
```

**Request body size limits** must be configured at the server level:

```bash
# Uvicorn
uvicorn app.main:app --limit-request-body 10485760  # 10MB

# Nginx (reverse proxy)
client_max_body_size 10m;
```

### CORS Configuration

Be explicit about allowed methods and headers:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)
```

### Middleware Order

Order matters - middleware executes in reverse order of registration:

```python
# 1. GZip (last to run on response, first to run on request)
app.add_middleware(GZipMiddleware, minimum_size=500)

# 2. CORS (handle preflight early)
app.add_middleware(CORSMiddleware, ...)

# 3. Custom middleware (function-based, runs via decorator)
@app.middleware("http")
async def add_process_time_header(request, call_next):
    ...

# 4. Rate limiting (after CORS)
app.add_middleware(RateLimitMiddleware)
```

---

## Health Check Endpoints

### Comprehensive Health Check

```python
from pydantic import BaseModel
from sqlalchemy import text

class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str
    database: str = "connected"

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check for load balancers and monitoring."""
    db_status = "disconnected"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")

    overall_status = "healthy" if db_status == "connected" else "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        database=db_status,
    )

# Alias at API path for consistency
@app.get("/api/v1/health", response_model=HealthResponse, include_in_schema=False)
async def health_check_v1() -> HealthResponse:
    return await health_check()
```

### Extended Health Check (for detailed monitoring)

```python
class DetailedHealthResponse(BaseModel):
    status: str
    version: str
    database: str
    redis: str | None = None
    uptime_seconds: float
    checks: dict[str, bool]

startup_time = time.time()

@app.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    checks = {}

    # Database check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    # Redis check (if configured)
    if settings.redis_url:
        try:
            r = redis.from_url(settings.redis_url)
            await r.ping()
            checks["redis"] = True
        except Exception:
            checks["redis"] = False

    return DetailedHealthResponse(
        status="healthy" if all(checks.values()) else "degraded",
        version=settings.app_version,
        database="connected" if checks.get("database") else "disconnected",
        redis="connected" if checks.get("redis") else None,
        uptime_seconds=time.time() - startup_time,
        checks=checks,
    )
```

---

## Error Handling

### Standard Error Response Schema

```python
class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    status_code: int
```

### HTTP Exception Handler

```python
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail if isinstance(exc.detail, str) else "Error",
            detail=str(exc.detail) if not isinstance(exc.detail, str) else None,
            status_code=exc.status_code,
        ).model_dump(),
        headers=getattr(exc, "headers", None),
    )
```

### Validation Error Handler

Provide detailed validation errors to clients:

```python
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = exc.errors()
    error_messages = []

    for error in errors:
        loc = " -> ".join(str(x) for x in error["loc"])
        msg = error["msg"]
        error_messages.append(f"{loc}: {msg}")

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="Validation Error",
            detail="; ".join(error_messages),
            status_code=422,
        ).model_dump(),
    )
```

### General Exception Handler

Handle unexpected errors without exposing internals:

```python
@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception(f"Unexpected error: {exc}")

    # Don't expose internal errors in production
    if settings.environment == "production":
        detail = "An unexpected error occurred"
    else:
        detail = str(exc)

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=detail,
            status_code=500,
        ).model_dump(),
    )
```

### Custom Domain Exceptions

```python
class RunNotFoundError(Exception):
    def __init__(self, run_id: str):
        self.run_id = run_id

@app.exception_handler(RunNotFoundError)
async def run_not_found_handler(request: Request, exc: RunNotFoundError):
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error="Not Found",
            detail=f"Run {exc.run_id} not found",
            status_code=404,
        ).model_dump(),
    )
```

---

## Dependencies

### Layered Dependencies

Build complex auth requirements by layering:

```python
# Base: Get current user from token
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    ...

# Layer 1: Ensure user is active
async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(403, "Account disabled")
    return current_user

# Layer 2: Ensure user is verified (for premium features)
async def get_verified_user(
    user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    if not user.is_verified:
        raise HTTPException(403, "Email not verified")
    return user

# Type aliases for clean usage
CurrentUser = Annotated[User, Depends(get_current_active_user)]
VerifiedUser = Annotated[User, Depends(get_verified_user)]
```

### Dependency Caching

Dependencies are cached within request scope - use this intentionally:

```python
# Called ONCE per request, even if used by multiple dependencies
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

# Both these use the SAME session instance
@router.get("/data")
async def get_data(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentUser,  # Also uses get_db internally
):
    ...
```

---

## Configuration Management

```python
from functools import lru_cache
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "ESO Build Optimizer API"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # API
    api_v1_prefix: str = "/api/v1"
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"]
    )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/db"

    # JWT
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst_size: int = 10

    # Password Hashing
    password_hash_rounds: int = 12

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("jwt_secret_key", mode="after")
    @classmethod
    def validate_jwt_secret(cls, v, info):
        if info.data.get("environment") == "production":
            if v == "CHANGE_ME_IN_PRODUCTION":
                raise ValueError("JWT secret must be set in production")
        return v

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

---

## Database Best Practices

### Async Engine Configuration

```python
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,      # Verify connections before use
    pool_size=10,            # Persistent connections
    max_overflow=20,         # Additional connections under load
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,  # Keep objects accessible after commit
    autocommit=False,
    autoflush=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### Model Definition with Type Hints

```python
from sqlalchemy import String, Integer, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships with type hints
    combat_runs: Mapped[list["CombatRun"]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )

    # Composite indexes
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )
```

### Naming Conventions

```python
from sqlalchemy import MetaData

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)
```

---

## Security Checklist

- [ ] Use HTTPS in production (via reverse proxy)
- [ ] Set secure cookie flags: `httponly=True, secure=True, samesite="lax"`
- [ ] Implement rate limiting (per-IP and per-user)
- [ ] Validate all input with Pydantic
- [ ] Use parameterized queries (SQLAlchemy handles this)
- [ ] Set CORS explicitly (avoid `allow_origins=["*"]` in production)
- [ ] Never log sensitive data (passwords, tokens, PII)
- [ ] Use environment variables for secrets
- [ ] Validate JWT secret is changed in production
- [ ] Set appropriate token expiration times
- [ ] Hash passwords with bcrypt (12+ rounds)
- [ ] Return generic error messages in production
- [ ] Use HTTPBearer instead of OAuth2PasswordBearer for API tokens

---

## Testing

### Async Test Setup

```python
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from api.main import app
from api.models.database import Base, get_db

# Test database
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"

@pytest.fixture
async def test_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    app.dependency_overrides.clear()

@pytest.fixture
async def client(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in ["healthy", "degraded"]

@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@test.com", "password": "wrong"},
    )
    assert response.status_code == 401
```

### Testing with Authentication

```python
@pytest.fixture
async def auth_headers(client, test_db):
    # Register user
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@test.com",
            "username": "testuser",
            "password": "testpass123",
        },
    )

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@test.com", "password": "testpass123"},
    )
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_get_profile(client, auth_headers):
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "test@test.com"
```

---

## Production Server Configuration

### Gunicorn + Uvicorn

```bash
gunicorn api.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile -
```

**Worker calculation**: For async workers, use `workers = CPU_CORES` (not the 2n+1 formula for sync workers).

### Docker Configuration

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY api/ api/

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "api.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

### Environment Variables for Production

```bash
# Required
JWT_SECRET_KEY=your-secure-random-key-here
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
ENVIRONMENT=production

# Optional
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
DEBUG=false
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

---

*This document should be refreshed when FastAPI or key dependencies release major updates.*
