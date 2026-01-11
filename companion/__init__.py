"""
ESO Build Optimizer - Companion App

Cloud sync client for syncing combat data between the local
SavedVariables and the ESO Build Optimizer cloud API.
"""

from .sync import (
    # Main classes
    SyncClient,
    LocalCache,
    TokenManager,
    RateLimiter,

    # Configuration
    SyncConfig,

    # Data models
    SyncItem,
    SyncStatus,
    SyncDirection,
    SyncResult,
    AuthToken,
    ConflictResolution,

    # Exceptions
    SyncError,
    AuthenticationError,
    RateLimitError,
    ConflictError,
    NetworkError,

    # Convenience functions
    create_sync_client,
    sync_session,
)

__version__ = "0.1.0"
__all__ = [
    # Main classes
    "SyncClient",
    "LocalCache",
    "TokenManager",
    "RateLimiter",

    # Configuration
    "SyncConfig",

    # Data models
    "SyncItem",
    "SyncStatus",
    "SyncDirection",
    "SyncResult",
    "AuthToken",
    "ConflictResolution",

    # Exceptions
    "SyncError",
    "AuthenticationError",
    "RateLimitError",
    "ConflictError",
    "NetworkError",

    # Convenience functions
    "create_sync_client",
    "sync_session",
]
