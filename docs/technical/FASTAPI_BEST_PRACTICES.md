# FastAPI Production Best Practices

> **Last Updated**: January 2026
> **Source**: [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices), [FastAPI Docs](https://fastapi.tiangolo.com/)

---

## Project Structure

Organize by **domain/module** rather than file type for scalability:

```
app/
├── main.py                 # FastAPI app initialization
├── config.py               # Pydantic BaseSettings
├── __init__.py
├── auth/                   # Auth domain
│   ├── router.py           # Auth endpoints
│   ├── schemas.py          # Pydantic models
│   ├── models.py           # SQLAlchemy models
│   ├── service.py          # Business logic
│   ├── dependencies.py     # Route dependencies
│   ├── constants.py        # Module constants
│   ├── exceptions.py       # Custom exceptions
│   └── utils.py            # Helper functions
├── runs/                   # Combat runs domain
│   └── ...
└── recommendations/        # Recommendations domain
    └── ...
```

## Async Best Practices

### I/O-Intensive Routes
```python
# GOOD: Async for non-blocking I/O
@router.get("/runs")
async def get_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Run))
    return result.scalars().all()

# BAD: Blocking call in async route
@router.get("/runs")
async def get_runs():
    time.sleep(1)  # Blocks event loop!
    return {"data": "..."}
```

### CPU-Intensive Tasks
```python
# GOOD: Offload to background worker
from celery import Celery

@router.post("/analyze")
async def analyze_run(run_id: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(compute_percentiles, run_id)
    return {"status": "processing"}

# Or use ProcessPoolExecutor for in-process parallelism
import asyncio
from concurrent.futures import ProcessPoolExecutor

executor = ProcessPoolExecutor(max_workers=4)

@router.get("/heavy-compute")
async def heavy_compute():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, cpu_bound_function)
    return result
```

## Pydantic Best Practices

### Custom Base Model
```python
from datetime import datetime
from pydantic import BaseModel

class AppBaseModel(BaseModel):
    """Base model with common configuration."""

    class Config:
        # Convert datetime to ISO format in JSON
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        # Allow population by field name
        populate_by_name = True
        # Validate on assignment
        validate_assignment = True

# Use for all schemas
class RunSchema(AppBaseModel):
    run_id: str
    timestamp: datetime
    dps: int
```

### Strict Validation
```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal

class RunCreate(BaseModel):
    content_type: Literal["dungeon", "trial", "arena", "overworld"]
    difficulty: Literal["normal", "veteran", "hardmode"]
    dps: int = Field(ge=0, le=500000)  # Reasonable DPS range

    @field_validator("dps")
    @classmethod
    def validate_dps(cls, v):
        if v < 0:
            raise ValueError("DPS cannot be negative")
        return v
```

## Dependencies

### Layered Dependencies
```python
# Base auth check
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    user = await verify_token(token)
    if not user:
        raise HTTPException(401, "Invalid token")
    return user

# Layered: requires base + additional check
async def get_verified_user(user: User = Depends(get_current_user)) -> User:
    if not user.email_verified:
        raise HTTPException(403, "Email not verified")
    return user

# Route uses layered dependency
@router.get("/premium")
async def premium_content(user: User = Depends(get_verified_user)):
    return {"content": "premium"}
```

### Dependency Caching
Dependencies are cached within request scope by default:
```python
# Called ONCE per request, even if used by multiple dependencies
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
```

## Configuration Management

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    database_url: str
    redis_url: str | None = None
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()

# Usage
settings = get_settings()
```

## Error Handling

```python
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

# Custom exception
class RunNotFoundError(Exception):
    def __init__(self, run_id: str):
        self.run_id = run_id

# Exception handler
@app.exception_handler(RunNotFoundError)
async def run_not_found_handler(request: Request, exc: RunNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": f"Run {exc.run_id} not found"}
    )
```

## Production Server Configuration

### Gunicorn + Uvicorn
```bash
# Production command
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --graceful-timeout 30
```

**Worker calculation**: For async workers, use `workers = CPU_CORES` (not 2n+1 formula for sync workers).

### Health Checks
```python
@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        raise HTTPException(503, "Database unavailable")
```

## Security Checklist

- [ ] Use HTTPS in production (handled by reverse proxy)
- [ ] Set secure cookie flags: `httponly=True, secure=True, samesite="lax"`
- [ ] Implement rate limiting
- [ ] Validate all input with Pydantic
- [ ] Use parameterized queries (SQLAlchemy handles this)
- [ ] Set CORS appropriately
- [ ] Never log sensitive data (passwords, tokens)
- [ ] Use environment variables for secrets

## Database Best Practices

```python
# Explicit naming conventions (set once, use everywhere)
from sqlalchemy import MetaData

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
```

## Testing

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_get_runs(client):
    response = await client.get("/api/v1/runs")
    assert response.status_code == 200
```

---

*This document should be refreshed when FastAPI or key dependencies release major updates.*
