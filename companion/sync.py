#!/usr/bin/env python3
"""
ESO Build Optimizer - Cloud Sync Client

Production-ready sync module for uploading combat data and downloading
recommendations between the local companion app and cloud API.

Features:
- Async HTTP client with connection pooling
- Queue-based batch uploads to minimize API calls
- Exponential backoff retry logic
- SQLite cache for offline operation
- Conflict resolution (server wins for aggregated, client wins for settings)
- OAuth2-style token management with refresh
- Rate limiting to respect API quotas
"""

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, Generic
from collections import deque

import httpx

# Configure module logger
logger = logging.getLogger("eso_sync")
logger.setLevel(logging.DEBUG)

# Type variable for generic operations
T = TypeVar("T")


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class SyncConfig:
    """Configuration for the sync client."""

    # API settings
    api_base_url: str = "https://api.eso-optimizer.com/v1"
    api_timeout: float = 30.0

    # Sync intervals (seconds)
    upload_interval: float = 60.0  # Batch uploads every minute
    download_interval: float = 300.0  # Check for updates every 5 minutes
    full_sync_interval: float = 3600.0  # Full sync every hour

    # Batch settings
    max_batch_size: int = 50  # Max items per upload batch
    max_queue_size: int = 1000  # Max pending items before force flush

    # Retry settings
    max_retries: int = 5
    base_retry_delay: float = 1.0  # Starting delay for exponential backoff
    max_retry_delay: float = 60.0  # Cap retry delay at 1 minute

    # Rate limiting
    requests_per_minute: int = 60
    requests_per_hour: int = 1000

    # Cache settings
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".eso_optimizer")
    cache_db_name: str = "sync_cache.db"
    max_cache_age_days: int = 30

    # Auth settings
    token_refresh_buffer: int = 300  # Refresh token 5 min before expiry

    def __post_init__(self):
        """Ensure cache directory exists."""
        self.cache_dir = Path(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cache_db_path(self) -> Path:
        """Full path to the cache database."""
        return self.cache_dir / self.cache_db_name


# =============================================================================
# Data Models
# =============================================================================

class SyncStatus(Enum):
    """Status of a sync item."""
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    FAILED = "failed"
    CONFLICT = "conflict"


class SyncDirection(Enum):
    """Direction of sync operation."""
    UPLOAD = "upload"
    DOWNLOAD = "download"


class ConflictResolution(Enum):
    """How to resolve sync conflicts."""
    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"
    NEWEST_WINS = "newest_wins"
    MANUAL = "manual"


@dataclass
class SyncItem:
    """An item to be synced."""
    id: str
    item_type: str  # "combat_run", "build_snapshot", "recommendation", "feature_update"
    data: dict
    direction: SyncDirection
    status: SyncStatus = SyncStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    attempts: int = 0
    last_error: Optional[str] = None
    checksum: Optional[str] = None

    def __post_init__(self):
        """Calculate checksum if not provided."""
        if self.checksum is None:
            self.checksum = self._calculate_checksum()

    def _calculate_checksum(self) -> str:
        """Calculate SHA256 checksum of the data."""
        data_str = json.dumps(self.data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "item_type": self.item_type,
            "data": self.data,
            "direction": self.direction.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "attempts": self.attempts,
            "last_error": self.last_error,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SyncItem":
        """Create from dictionary."""
        return cls(
            id=d["id"],
            item_type=d["item_type"],
            data=d["data"],
            direction=SyncDirection(d["direction"]),
            status=SyncStatus(d["status"]),
            created_at=datetime.fromisoformat(d["created_at"]),
            updated_at=datetime.fromisoformat(d["updated_at"]),
            attempts=d["attempts"],
            last_error=d.get("last_error"),
            checksum=d.get("checksum"),
        )


@dataclass
class AuthToken:
    """OAuth2-style authentication token."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    scope: str = ""

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now(timezone.utc) >= self.expires_at

    def needs_refresh(self, buffer_seconds: int = 300) -> bool:
        """Check if token needs refresh (within buffer of expiry)."""
        buffer = timedelta(seconds=buffer_seconds)
        return datetime.now(timezone.utc) >= (self.expires_at - buffer)

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat(),
            "scope": self.scope,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AuthToken":
        """Create from dictionary."""
        return cls(
            access_token=d["access_token"],
            refresh_token=d["refresh_token"],
            token_type=d.get("token_type", "Bearer"),
            expires_at=datetime.fromisoformat(d["expires_at"]),
            scope=d.get("scope", ""),
        )


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    items_processed: int = 0
    items_failed: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Exceptions
# =============================================================================

class SyncError(Exception):
    """Base exception for sync operations."""
    pass


class AuthenticationError(SyncError):
    """Authentication failed."""
    pass


class RateLimitError(SyncError):
    """Rate limit exceeded."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class ConflictError(SyncError):
    """Sync conflict detected."""
    def __init__(self, message: str, server_data: dict, client_data: dict):
        super().__init__(message)
        self.server_data = server_data
        self.client_data = client_data


class NetworkError(SyncError):
    """Network-related error."""
    pass


# =============================================================================
# Rate Limiter
# =============================================================================

class RateLimiter:
    """Token bucket rate limiter with sliding window."""

    def __init__(self, requests_per_minute: int, requests_per_hour: int):
        self.rpm_limit = requests_per_minute
        self.rph_limit = requests_per_hour
        self.minute_window: deque[float] = deque()
        self.hour_window: deque[float] = deque()
        self._lock = asyncio.Lock()
        self._sync_lock = threading.Lock()  # For sync property access

    async def acquire(self) -> None:
        """Acquire permission to make a request, blocking if necessary."""
        async with self._lock:
            now = time.time()

            # Clean old entries
            minute_ago = now - 60
            hour_ago = now - 3600

            while self.minute_window and self.minute_window[0] < minute_ago:
                self.minute_window.popleft()
            while self.hour_window and self.hour_window[0] < hour_ago:
                self.hour_window.popleft()

            # Check limits and wait if necessary
            while len(self.minute_window) >= self.rpm_limit:
                wait_time = self.minute_window[0] - minute_ago
                if wait_time > 0:
                    logger.debug(f"Rate limit (minute): waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                now = time.time()
                minute_ago = now - 60
                while self.minute_window and self.minute_window[0] < minute_ago:
                    self.minute_window.popleft()

            while len(self.hour_window) >= self.rph_limit:
                wait_time = self.hour_window[0] - hour_ago
                if wait_time > 0:
                    logger.debug(f"Rate limit (hour): waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                now = time.time()
                hour_ago = now - 3600
                while self.hour_window and self.hour_window[0] < hour_ago:
                    self.hour_window.popleft()

            # Record this request
            now = time.time()
            self.minute_window.append(now)
            self.hour_window.append(now)

    @property
    def remaining_minute(self) -> int:
        """Remaining requests this minute."""
        with self._sync_lock:
            now = time.time()
            minute_ago = now - 60
            count = sum(1 for t in self.minute_window if t >= minute_ago)
            return max(0, self.rpm_limit - count)

    @property
    def remaining_hour(self) -> int:
        """Remaining requests this hour."""
        with self._sync_lock:
            now = time.time()
            hour_ago = now - 3600
            count = sum(1 for t in self.hour_window if t >= hour_ago)
            return max(0, self.rph_limit - count)


# =============================================================================
# Local Cache (SQLite)
# =============================================================================

class LocalCache:
    """SQLite-based local cache for offline operation."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS sync_queue (
        id TEXT PRIMARY KEY,
        item_type TEXT NOT NULL,
        direction TEXT NOT NULL,
        status TEXT NOT NULL,
        data TEXT NOT NULL,
        checksum TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        attempts INTEGER DEFAULT 0,
        last_error TEXT
    );

    CREATE TABLE IF NOT EXISTS cached_data (
        key TEXT PRIMARY KEY,
        data_type TEXT NOT NULL,
        data TEXT NOT NULL,
        checksum TEXT,
        server_timestamp TEXT,
        cached_at TEXT NOT NULL,
        expires_at TEXT
    );

    CREATE TABLE IF NOT EXISTS auth_tokens (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        access_token TEXT NOT NULL,
        refresh_token TEXT NOT NULL,
        token_type TEXT DEFAULT 'Bearer',
        expires_at TEXT NOT NULL,
        scope TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS sync_metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON sync_queue(status);
    CREATE INDEX IF NOT EXISTS idx_sync_queue_type ON sync_queue(item_type);
    CREATE INDEX IF NOT EXISTS idx_cached_data_type ON cached_data(data_type);
    CREATE INDEX IF NOT EXISTS idx_cached_data_expires ON cached_data(expires_at);
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._get_connection() as conn:
            conn.executescript(self.SCHEMA)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper cleanup and retry for SQLITE_BUSY."""
        conn = None
        for attempt in range(5):
            try:
                conn = sqlite3.connect(str(self.db_path), timeout=30.0)
                conn.row_factory = sqlite3.Row
                break
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < 4:
                    time.sleep(0.1 * (2 ** attempt))
                else:
                    raise
        try:
            yield conn
        finally:
            if conn:
                conn.close()

    # === Sync Queue Operations ===

    def enqueue(self, item: SyncItem) -> None:
        """Add an item to the sync queue."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sync_queue
                (id, item_type, direction, status, data, checksum,
                 created_at, updated_at, attempts, last_error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.id,
                    item.item_type,
                    item.direction.value,
                    item.status.value,
                    json.dumps(item.data),
                    item.checksum,
                    item.created_at.isoformat(),
                    item.updated_at.isoformat(),
                    item.attempts,
                    item.last_error,
                ),
            )
            conn.commit()
        logger.debug(f"Enqueued sync item: {item.id} ({item.item_type})")

    def dequeue_batch(
        self,
        direction: SyncDirection,
        status: SyncStatus = SyncStatus.PENDING,
        limit: int = 50,
    ) -> list[SyncItem]:
        """Get a batch of items from the queue."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM sync_queue
                WHERE direction = ? AND status = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (direction.value, status.value, limit),
            )
            rows = cursor.fetchall()

        items = []
        for row in rows:
            items.append(SyncItem(
                id=row["id"],
                item_type=row["item_type"],
                data=json.loads(row["data"]),
                direction=SyncDirection(row["direction"]),
                status=SyncStatus(row["status"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                attempts=row["attempts"],
                last_error=row["last_error"],
                checksum=row["checksum"],
            ))

        return items

    def update_item_status(
        self,
        item_id: str,
        status: SyncStatus,
        error: Optional[str] = None,
    ) -> None:
        """Update the status of a sync item."""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE sync_queue
                SET status = ?, last_error = ?, updated_at = ?, attempts = attempts + 1
                WHERE id = ?
                """,
                (status.value, error, datetime.now(timezone.utc).isoformat(), item_id),
            )
            conn.commit()

    def remove_item(self, item_id: str) -> None:
        """Remove an item from the queue."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM sync_queue WHERE id = ?", (item_id,))
            conn.commit()

    def get_queue_stats(self) -> dict[str, int]:
        """Get statistics about the sync queue."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT status, COUNT(*) as count
                FROM sync_queue
                GROUP BY status
                """
            )
            return {row["status"]: row["count"] for row in cursor.fetchall()}

    def clear_completed(self, older_than_days: int = 7) -> int:
        """Clear completed items older than specified days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM sync_queue
                WHERE status = ? AND updated_at < ?
                """,
                (SyncStatus.UPLOADED.value, cutoff.isoformat()),
            )
            conn.commit()
            return cursor.rowcount

    # === Cached Data Operations ===

    def cache_data(
        self,
        key: str,
        data_type: str,
        data: dict,
        server_timestamp: Optional[datetime] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Cache data locally."""
        now = datetime.now(timezone.utc)
        expires_at = None
        if ttl_seconds:
            expires_at = now + timedelta(seconds=ttl_seconds)

        checksum = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cached_data
                (key, data_type, data, checksum, server_timestamp, cached_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    data_type,
                    json.dumps(data),
                    checksum,
                    server_timestamp.isoformat() if server_timestamp else None,
                    now.isoformat(),
                    expires_at.isoformat() if expires_at else None,
                ),
            )
            conn.commit()

    def get_cached(self, key: str) -> Optional[dict]:
        """Get cached data if not expired."""
        now = datetime.now(timezone.utc)
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT data, expires_at FROM cached_data
                WHERE key = ?
                """,
                (key,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            # Check expiry
            if row["expires_at"]:
                expires_at = datetime.fromisoformat(row["expires_at"])
                if now >= expires_at:
                    # Expired - remove it
                    conn.execute("DELETE FROM cached_data WHERE key = ?", (key,))
                    conn.commit()
                    return None

            return json.loads(row["data"])

    def get_cached_checksum(self, key: str) -> Optional[str]:
        """Get the checksum of cached data."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT checksum FROM cached_data WHERE key = ?",
                (key,),
            )
            row = cursor.fetchone()
            return row["checksum"] if row else None

    def clear_expired_cache(self) -> int:
        """Clear all expired cached data."""
        now = datetime.now(timezone.utc)
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM cached_data WHERE expires_at IS NOT NULL AND expires_at < ?",
                (now.isoformat(),),
            )
            conn.commit()
            return cursor.rowcount

    # === Auth Token Operations ===

    def save_token(self, token: AuthToken) -> None:
        """Save authentication token."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO auth_tokens
                (id, access_token, refresh_token, token_type, expires_at, scope)
                VALUES (1, ?, ?, ?, ?, ?)
                """,
                (
                    token.access_token,
                    token.refresh_token,
                    token.token_type,
                    token.expires_at.isoformat(),
                    token.scope,
                ),
            )
            conn.commit()

    def get_token(self) -> Optional[AuthToken]:
        """Get stored authentication token."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM auth_tokens WHERE id = 1")
            row = cursor.fetchone()

            if not row:
                return None

            return AuthToken(
                access_token=row["access_token"],
                refresh_token=row["refresh_token"],
                token_type=row["token_type"],
                expires_at=datetime.fromisoformat(row["expires_at"]),
                scope=row["scope"],
            )

    def clear_token(self) -> None:
        """Clear stored authentication token."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM auth_tokens WHERE id = 1")
            conn.commit()

    # === Metadata Operations ===

    def set_metadata(self, key: str, value: str) -> None:
        """Set a metadata value."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sync_metadata (key, value, updated_at)
                VALUES (?, ?, ?)
                """,
                (key, value, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

    def get_metadata(self, key: str) -> Optional[str]:
        """Get a metadata value."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT value FROM sync_metadata WHERE key = ?",
                (key,),
            )
            row = cursor.fetchone()
            return row["value"] if row else None


# =============================================================================
# Token Manager
# =============================================================================

class TokenManager:
    """Manages OAuth2-style authentication tokens."""

    def __init__(self, cache: LocalCache, config: SyncConfig):
        self.cache = cache
        self.config = config
        self._token: Optional[AuthToken] = None
        self._refresh_lock = asyncio.Lock()
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.api_timeout),
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    def load_token(self) -> Optional[AuthToken]:
        """Load token from cache."""
        if self._token is None:
            self._token = self.cache.get_token()
        return self._token

    async def get_valid_token(self) -> AuthToken:
        """Get a valid (non-expired) token, refreshing if necessary."""
        token = self.load_token()

        if token is None:
            raise AuthenticationError("No authentication token available. Please login.")

        if token.needs_refresh(self.config.token_refresh_buffer):
            async with self._refresh_lock:
                # Double-check after acquiring lock
                token = self.load_token()
                if token and token.needs_refresh(self.config.token_refresh_buffer):
                    token = await self._refresh_token(token)

        return token

    async def _refresh_token(self, token: AuthToken) -> AuthToken:
        """Refresh an expired token."""
        logger.info("Refreshing authentication token...")

        client = await self._get_http_client()

        try:
            response = await client.post(
                f"{self.config.api_base_url}/auth/refresh",
                json={"refresh_token": token.refresh_token},
            )

            if response.status_code == 401:
                self.cache.clear_token()
                self._token = None
                raise AuthenticationError("Refresh token expired. Please login again.")

            response.raise_for_status()
            data = response.json()

            new_token = AuthToken(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", token.refresh_token),
                token_type=data.get("token_type", "Bearer"),
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"]),
                scope=data.get("scope", ""),
            )

            self.cache.save_token(new_token)
            self._token = new_token
            logger.info("Token refreshed successfully")
            return new_token

        except httpx.HTTPStatusError as e:
            raise AuthenticationError(f"Token refresh failed: {e}")
        except httpx.RequestError as e:
            raise NetworkError(f"Network error during token refresh: {e}")

    async def login(self, username: str, password: str) -> AuthToken:
        """Authenticate with username and password."""
        logger.info(f"Logging in user: {username}")

        client = await self._get_http_client()

        try:
            response = await client.post(
                f"{self.config.api_base_url}/auth/login",
                json={"username": username, "password": password},
            )

            if response.status_code == 401:
                raise AuthenticationError("Invalid username or password")

            response.raise_for_status()
            data = response.json()

            token = AuthToken(
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                token_type=data.get("token_type", "Bearer"),
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"]),
                scope=data.get("scope", ""),
            )

            self.cache.save_token(token)
            self._token = token
            logger.info("Login successful")
            return token

        except httpx.HTTPStatusError as e:
            raise AuthenticationError(f"Login failed: {e}")
        except httpx.RequestError as e:
            raise NetworkError(f"Network error during login: {e}")

    async def logout(self) -> None:
        """Logout and clear stored tokens."""
        if self._token:
            try:
                client = await self._get_http_client()
                await client.post(
                    f"{self.config.api_base_url}/auth/logout",
                    headers={"Authorization": f"Bearer {self._token.access_token}"},
                )
            except Exception as e:
                logger.warning(f"Error during logout: {e}")

        self.cache.clear_token()
        self._token = None
        logger.info("Logged out successfully")

    def get_auth_header(self) -> dict[str, str]:
        """Get authorization header for API requests."""
        if self._token is None:
            raise AuthenticationError("Not authenticated")
        return {"Authorization": f"{self._token.token_type} {self._token.access_token}"}


# =============================================================================
# Sync Client
# =============================================================================

class SyncClient:
    """Main client for syncing data with the cloud API."""

    def __init__(self, config: Optional[SyncConfig] = None):
        self.config = config or SyncConfig()
        self.cache = LocalCache(self.config.cache_db_path)
        self.token_manager = TokenManager(self.cache, self.config)
        self.rate_limiter = RateLimiter(
            self.config.requests_per_minute,
            self.config.requests_per_hour,
        )

        self._http_client: Optional[httpx.AsyncClient] = None
        self._upload_queue: asyncio.Queue[SyncItem] = asyncio.Queue()
        self._running = False
        self._sync_task: Optional[asyncio.Task] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.api_timeout),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._http_client

    async def close(self) -> None:
        """Close the sync client and cleanup resources."""
        self._running = False

        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

        await self.token_manager.close()
        logger.info("Sync client closed")

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> httpx.Response:
        """Make an authenticated API request with retry logic."""
        client = await self._get_http_client()
        url = f"{self.config.api_base_url}{endpoint}"

        # Ensure we have valid auth
        token = await self.token_manager.get_valid_token()
        headers = kwargs.pop("headers", {})
        headers.update(self.token_manager.get_auth_header())

        last_exception: Optional[Exception] = None

        for attempt in range(self.config.max_retries):
            try:
                # Rate limit
                await self.rate_limiter.acquire()

                response = await client.request(
                    method,
                    url,
                    headers=headers,
                    **kwargs,
                )

                # Handle rate limiting response
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise RateLimitError(
                        f"Rate limit exceeded. Retry after {retry_after}s",
                        retry_after=retry_after,
                    )

                # Handle auth errors
                if response.status_code == 401:
                    # Try refreshing token once
                    if attempt == 0:
                        token = await self.token_manager._refresh_token(token)
                        headers.update(self.token_manager.get_auth_header())
                        continue
                    raise AuthenticationError("Authentication failed")

                response.raise_for_status()
                return response

            except RateLimitError as e:
                wait_time = e.retry_after or self._calculate_backoff(attempt)
                logger.warning(f"Rate limited, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
                last_exception = e

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    # Server error - retry with backoff
                    wait_time = self._calculate_backoff(attempt)
                    logger.warning(f"Server error {e.response.status_code}, retry in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    last_exception = e
                else:
                    # Client error - don't retry
                    raise SyncError(f"API error: {e.response.status_code} - {e.response.text}")

            except httpx.RequestError as e:
                wait_time = self._calculate_backoff(attempt)
                logger.warning(f"Network error: {e}, retry in {wait_time}s")
                await asyncio.sleep(wait_time)
                last_exception = NetworkError(str(e))

        raise last_exception or SyncError("Max retries exceeded")

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = self.config.base_retry_delay * (2 ** attempt)
        # Add jitter (0-25% of delay)
        jitter = delay * 0.25 * (hash(time.time()) % 100) / 100
        return min(delay + jitter, self.config.max_retry_delay)

    # === Upload Operations ===

    async def upload_run(self, run_data: dict) -> str:
        """
        Queue a combat run for upload.

        Args:
            run_data: Combat run data matching the CombatRun schema

        Returns:
            The sync item ID for tracking
        """
        item_id = str(uuid.uuid4())
        item = SyncItem(
            id=item_id,
            item_type="combat_run",
            data=run_data,
            direction=SyncDirection.UPLOAD,
        )

        # Store in local cache
        self.cache.enqueue(item)

        # Add to in-memory queue for immediate processing
        await self._upload_queue.put(item)

        logger.info(f"Queued combat run for upload: {item_id}")
        return item_id

    async def upload_build_snapshot(self, build_data: dict) -> str:
        """
        Queue a build snapshot for upload.

        Args:
            build_data: Build snapshot data

        Returns:
            The sync item ID for tracking
        """
        item_id = str(uuid.uuid4())
        item = SyncItem(
            id=item_id,
            item_type="build_snapshot",
            data=build_data,
            direction=SyncDirection.UPLOAD,
        )

        self.cache.enqueue(item)
        await self._upload_queue.put(item)

        logger.info(f"Queued build snapshot for upload: {item_id}")
        return item_id

    async def _process_upload_batch(self, items: list[SyncItem]) -> SyncResult:
        """Process a batch of upload items."""
        if not items:
            return SyncResult(success=True)

        start_time = time.time()
        results = {"processed": 0, "failed": 0, "errors": []}

        # Group by item type for batch upload
        by_type: dict[str, list[SyncItem]] = {}
        for item in items:
            by_type.setdefault(item.item_type, []).append(item)

        for item_type, type_items in by_type.items():
            try:
                endpoint = f"/sync/{item_type}s/batch"
                payload = {
                    "items": [
                        {"id": item.id, "data": item.data, "checksum": item.checksum}
                        for item in type_items
                    ]
                }

                response = await self._request("POST", endpoint, json=payload)
                response_data = response.json()

                # Process individual results
                for item_result in response_data.get("results", []):
                    item_id = item_result["id"]
                    if item_result["success"]:
                        self.cache.update_item_status(item_id, SyncStatus.UPLOADED)
                        results["processed"] += 1
                    else:
                        error = item_result.get("error", "Unknown error")
                        self.cache.update_item_status(item_id, SyncStatus.FAILED, error)
                        results["failed"] += 1
                        results["errors"].append(f"{item_id}: {error}")

            except SyncError as e:
                # Mark all items in this batch as failed
                for item in type_items:
                    self.cache.update_item_status(item.id, SyncStatus.FAILED, str(e))
                    results["failed"] += 1
                    results["errors"].append(f"{item.id}: {e}")

        duration = time.time() - start_time

        return SyncResult(
            success=results["failed"] == 0,
            items_processed=results["processed"],
            items_failed=results["failed"],
            errors=results["errors"],
            duration_seconds=duration,
        )

    async def flush_upload_queue(self) -> SyncResult:
        """Force flush all pending uploads."""
        pending = self.cache.dequeue_batch(
            SyncDirection.UPLOAD,
            SyncStatus.PENDING,
            limit=self.config.max_batch_size,
        )

        if not pending:
            return SyncResult(success=True)

        logger.info(f"Flushing {len(pending)} pending uploads")
        return await self._process_upload_batch(pending)

    # === Download Operations ===

    async def download_recommendations(
        self,
        run_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> list[dict]:
        """
        Download recommendations from the server.

        Args:
            run_id: Optional specific run ID to get recommendations for
            since: Only get recommendations newer than this timestamp

        Returns:
            List of recommendation dictionaries
        """
        params = {}
        if run_id:
            params["run_id"] = run_id
        if since:
            params["since"] = since.isoformat()

        # Check cache first
        cache_key = f"recommendations:{run_id or 'all'}:{since.isoformat() if since else 'all'}"
        cached = self.cache.get_cached(cache_key)

        if cached:
            logger.debug(f"Using cached recommendations for {cache_key}")
            return cached

        try:
            response = await self._request("GET", "/recommendations", params=params)
            data = response.json()

            recommendations = data.get("recommendations", [])

            # Cache the results
            self.cache.cache_data(
                cache_key,
                "recommendations",
                recommendations,
                server_timestamp=datetime.now(timezone.utc),
                ttl_seconds=300,  # Cache for 5 minutes
            )

            logger.info(f"Downloaded {len(recommendations)} recommendations")
            return recommendations

        except SyncError as e:
            logger.error(f"Failed to download recommendations: {e}")
            # Return cached data if available (even if expired)
            return cached or []

    async def download_feature_updates(
        self,
        since_patch: Optional[str] = None,
    ) -> dict:
        """
        Download feature updates (skill/set changes) from the server.

        Args:
            since_patch: Only get updates since this patch version

        Returns:
            Dictionary with feature updates
        """
        params = {}
        if since_patch:
            params["since_patch"] = since_patch

        # Get current checksum for conditional fetch
        cache_key = "feature_updates"
        current_checksum = self.cache.get_cached_checksum(cache_key)

        headers = {}
        if current_checksum:
            headers["If-None-Match"] = current_checksum

        try:
            response = await self._request(
                "GET",
                "/features/updates",
                params=params,
                headers=headers,
            )

            if response.status_code == 304:
                # Not modified - use cache
                cached = self.cache.get_cached(cache_key)
                if cached:
                    return cached

            data = response.json()

            # Extract server checksum if provided
            server_checksum = response.headers.get("ETag")

            # Cache with long TTL (features don't change often)
            self.cache.cache_data(
                cache_key,
                "feature_updates",
                data,
                server_timestamp=datetime.now(timezone.utc),
                ttl_seconds=86400,  # Cache for 24 hours
            )

            logger.info(f"Downloaded feature updates: {len(data.get('features', []))} features")
            return data

        except SyncError as e:
            logger.error(f"Failed to download feature updates: {e}")
            return self.cache.get_cached(cache_key) or {}

    # === Full Sync ===

    async def sync_all(self) -> SyncResult:
        """
        Perform a full sync: upload pending, download updates.

        Returns:
            Combined SyncResult from all operations
        """
        start_time = time.time()
        total_processed = 0
        total_failed = 0
        all_errors: list[str] = []

        logger.info("Starting full sync...")

        # 1. Upload pending items
        upload_result = await self.flush_upload_queue()
        total_processed += upload_result.items_processed
        total_failed += upload_result.items_failed
        all_errors.extend(upload_result.errors)

        # 2. Download recommendations
        try:
            last_sync = self.cache.get_metadata("last_recommendation_sync")
            since = datetime.fromisoformat(last_sync) if last_sync else None

            recommendations = await self.download_recommendations(since=since)
            total_processed += len(recommendations)

            # Update last sync time
            self.cache.set_metadata(
                "last_recommendation_sync",
                datetime.now(timezone.utc).isoformat(),
            )
        except Exception as e:
            all_errors.append(f"Recommendation download failed: {e}")
            total_failed += 1

        # 3. Download feature updates
        try:
            last_patch = self.cache.get_metadata("last_patch_version")
            await self.download_feature_updates(since_patch=last_patch)
            total_processed += 1
        except Exception as e:
            all_errors.append(f"Feature update download failed: {e}")
            total_failed += 1

        duration = time.time() - start_time

        result = SyncResult(
            success=total_failed == 0,
            items_processed=total_processed,
            items_failed=total_failed,
            errors=all_errors,
            duration_seconds=duration,
        )

        logger.info(
            f"Full sync completed in {duration:.2f}s: "
            f"{total_processed} processed, {total_failed} failed"
        )

        return result

    # === Conflict Resolution ===

    async def resolve_conflict(
        self,
        item_id: str,
        resolution: ConflictResolution,
        custom_data: Optional[dict] = None,
    ) -> bool:
        """
        Resolve a sync conflict.

        Args:
            item_id: The conflicting item ID
            resolution: How to resolve the conflict
            custom_data: Custom merged data if resolution is MANUAL

        Returns:
            True if resolution was successful
        """
        try:
            payload = {
                "item_id": item_id,
                "resolution": resolution.value,
            }

            if resolution == ConflictResolution.MANUAL:
                if not custom_data:
                    raise ValueError("Manual resolution requires custom_data")
                payload["data"] = custom_data

            response = await self._request(
                "POST",
                "/sync/conflicts/resolve",
                json=payload,
            )

            if response.status_code == 200:
                self.cache.update_item_status(item_id, SyncStatus.UPLOADED)
                logger.info(f"Conflict resolved for {item_id}: {resolution.value}")
                return True

            return False

        except SyncError as e:
            logger.error(f"Failed to resolve conflict for {item_id}: {e}")
            return False

    # === Background Sync ===

    async def start_background_sync(self) -> None:
        """Start background sync tasks."""
        if self._running:
            logger.warning("Background sync already running")
            return

        self._running = True
        self._sync_task = asyncio.create_task(self._background_sync_loop())
        logger.info("Background sync started")

    async def stop_background_sync(self) -> None:
        """Stop background sync tasks."""
        self._running = False
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        logger.info("Background sync stopped")

    async def _background_sync_loop(self) -> None:
        """Main background sync loop."""
        last_upload = time.time()
        last_download = time.time()
        last_full_sync = time.time()

        while self._running:
            try:
                now = time.time()

                # Process upload queue
                if now - last_upload >= self.config.upload_interval:
                    pending = self.cache.dequeue_batch(
                        SyncDirection.UPLOAD,
                        SyncStatus.PENDING,
                        limit=self.config.max_batch_size,
                    )
                    if pending:
                        await self._process_upload_batch(pending)
                    last_upload = now

                # Check for downloads
                if now - last_download >= self.config.download_interval:
                    await self.download_recommendations()
                    last_download = now

                # Full sync
                if now - last_full_sync >= self.config.full_sync_interval:
                    await self.sync_all()
                    last_full_sync = now

                # Sleep before next iteration
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background sync: {e}")
                await asyncio.sleep(10)  # Back off on error

    # === Utility Methods ===

    def get_sync_status(self) -> dict:
        """Get current sync status information."""
        queue_stats = self.cache.get_queue_stats()

        return {
            "queue_stats": queue_stats,
            "rate_limit_remaining": {
                "minute": self.rate_limiter.remaining_minute,
                "hour": self.rate_limiter.remaining_hour,
            },
            "is_authenticated": self.token_manager.load_token() is not None,
            "background_sync_running": self._running,
        }

    async def health_check(self) -> bool:
        """Check if the API is reachable and we're authenticated."""
        try:
            response = await self._request("GET", "/health")
            return response.status_code == 200
        except Exception:
            return False


# =============================================================================
# Convenience Functions
# =============================================================================

async def create_sync_client(
    config: Optional[SyncConfig] = None,
    auto_start_background: bool = False,
) -> SyncClient:
    """
    Create and optionally start a sync client.

    Args:
        config: Optional configuration
        auto_start_background: Whether to start background sync

    Returns:
        Configured SyncClient instance
    """
    client = SyncClient(config)

    if auto_start_background:
        await client.start_background_sync()

    return client


@asynccontextmanager
async def sync_session(config: Optional[SyncConfig] = None):
    """
    Context manager for a sync session.

    Usage:
        async with sync_session() as client:
            await client.upload_run(run_data)
    """
    client = SyncClient(config)
    try:
        yield client
    finally:
        await client.close()


# =============================================================================
# CLI Interface (for testing)
# =============================================================================

async def main():
    """CLI interface for testing the sync client."""
    import argparse

    parser = argparse.ArgumentParser(description="ESO Build Optimizer Sync Client")
    parser.add_argument("--login", action="store_true", help="Login to the API")
    parser.add_argument("--sync", action="store_true", help="Perform full sync")
    parser.add_argument("--status", action="store_true", help="Show sync status")
    parser.add_argument("--flush", action="store_true", help="Flush upload queue")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    async with sync_session() as client:
        if args.login:
            username = input("Username: ")
            import getpass
            password = getpass.getpass("Password: ")
            try:
                await client.token_manager.login(username, password)
                print("Login successful!")
            except AuthenticationError as e:
                print(f"Login failed: {e}")
                return

        if args.status:
            status = client.get_sync_status()
            print("\n=== Sync Status ===")
            print(f"Queue: {status['queue_stats']}")
            print(f"Rate limits: {status['rate_limit_remaining']}")
            print(f"Authenticated: {status['is_authenticated']}")
            print(f"Background sync: {status['background_sync_running']}")

        if args.flush:
            result = await client.flush_upload_queue()
            print(f"\nFlush result: {result.items_processed} processed, {result.items_failed} failed")

        if args.sync:
            result = await client.sync_all()
            print(f"\nSync result: {result.items_processed} processed, {result.items_failed} failed")
            if result.errors:
                print("Errors:")
                for error in result.errors:
                    print(f"  - {error}")


if __name__ == "__main__":
    asyncio.run(main())
