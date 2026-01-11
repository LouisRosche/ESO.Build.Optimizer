"""
SQLAlchemy async models for ESO Build Optimizer API.

Uses PostgreSQL with async support via asyncpg.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from api.core.config import settings


# =============================================================================
# Database Engine and Session
# =============================================================================

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db():
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        yield session


# =============================================================================
# Base Model
# =============================================================================

class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models."""
    pass


# =============================================================================
# User Model
# =============================================================================

class User(Base):
    """User account model."""
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
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Rate limiting fields
    api_requests_today: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_request_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    combat_runs: Mapped[list["CombatRun"]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )


# =============================================================================
# Combat Run Model
# =============================================================================

class CombatRun(Base):
    """Combat run/encounter model."""
    __tablename__ = "combat_runs"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    character_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Content info
    content_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    content_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    difficulty: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Run metadata
    duration_sec: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )
    group_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Build snapshot (JSON)
    build_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    # Combat metrics (JSON)
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    # Calculated contribution scores (JSON)
    contribution_scores: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Denormalized for quick queries
    dps: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        index=True,
    )
    cp_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Relationships
    player: Mapped["User"] = relationship(back_populates="combat_runs")
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="combat_run",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_runs_content_lookup", "content_type", "content_name", "difficulty"),
        Index("ix_runs_player_timestamp", "player_id", "timestamp"),
        Index("ix_runs_percentile_calc", "content_name", "difficulty", "cp_level", "dps"),
    )


# =============================================================================
# Recommendation Model
# =============================================================================

class Recommendation(Base):
    """Generated recommendation model."""
    __tablename__ = "recommendations"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("combat_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    current_state: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    recommended_change: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    expected_improvement: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    reasoning: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    combat_run: Mapped["CombatRun"] = relationship(back_populates="recommendations")


# =============================================================================
# Feature Model (Skills, etc.)
# =============================================================================

class Feature(Base):
    """Feature database model (skills, passives, etc.)."""
    __tablename__ = "features"

    feature_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )
    system: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    subcategory: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    feature_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    parent_feature: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    class_restriction: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    unlock_method: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    resource_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    resource_cost: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    cast_time: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    target_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    range_m: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    radius_m: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    duration_sec: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    cooldown_sec: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    base_effect: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    scaling_stat: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    max_ranks: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    rank_progression: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    buff_debuff_granted: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    synergy: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    tags: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    dlc_required: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    patch_updated: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        Index("ix_features_search", "name", "category", "system"),
        Index("ix_features_class", "class_restriction", "category"),
    )


# =============================================================================
# Gear Set Model
# =============================================================================

class GearSet(Base):
    """Gear set database model."""
    __tablename__ = "gear_sets"

    set_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    set_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    weight: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    bind_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    tradeable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    location: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    dlc_required: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    bonuses: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    pve_tier: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        index=True,
    )
    role_affinity: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    tags: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    patch_updated: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        Index("ix_sets_search", "name", "set_type"),
    )


# =============================================================================
# Rate Limit Model
# =============================================================================

class RateLimit(Base):
    """Rate limiting tracking model."""
    __tablename__ = "rate_limits"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    request_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_rate_limits_lookup", "user_id", "endpoint", "window_start"),
    )


# =============================================================================
# Database Initialization
# =============================================================================

async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """Drop all database tables (use with caution)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
