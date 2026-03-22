"""
Character routes for ESO Build Optimizer API.

Derives character information from combat run history.
Characters are not stored as a separate entity — they're extracted
from the character_name and build_snapshot fields of combat runs.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.security import CurrentUser
from api.models.database import CombatRun, get_db

router = APIRouter(prefix="/characters", tags=["Characters"])


@router.get("")
async def list_characters(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    List all characters for the authenticated user.

    Characters are derived from combat run history — each unique
    character_name that appears in runs becomes a character entry.
    """
    # Get distinct character names with their latest build snapshot and stats
    subq = (
        select(
            CombatRun.character_name,
            func.count().label("total_runs"),
            func.max(CombatRun.dps).label("best_dps"),
            func.avg(CombatRun.dps).label("avg_dps"),
            func.max(CombatRun.timestamp).label("last_played"),
            func.max(CombatRun.cp_level).label("cp_level"),
        )
        .where(CombatRun.player_id == user.id)
        .group_by(CombatRun.character_name)
    )

    result = await db.execute(subq)
    character_rows = result.all()

    characters = []
    for row in character_rows:
        # Get the latest build snapshot for this character
        latest_run_stmt = (
            select(CombatRun.build_snapshot)
            .where(
                and_(
                    CombatRun.player_id == user.id,
                    CombatRun.character_name == row.character_name,
                )
            )
            .order_by(CombatRun.timestamp.desc())
            .limit(1)
        )
        latest_result = await db.execute(latest_run_stmt)
        build_snapshot = latest_result.scalar()

        characters.append({
            "character_name": row.character_name,
            "total_runs": row.total_runs,
            "best_dps": round(float(row.best_dps), 0) if row.best_dps else 0,
            "avg_dps": round(float(row.avg_dps), 0) if row.avg_dps else 0,
            "last_played": row.last_played.isoformat() if row.last_played else None,
            "cp_level": row.cp_level,
            "build": build_snapshot or {},
        })

    return characters


@router.get("/{character_name}")
async def get_character(
    character_name: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get detailed info for a specific character."""
    # Check character exists for this user
    exists_stmt = select(func.count()).select_from(CombatRun).where(
        and_(
            CombatRun.player_id == user.id,
            CombatRun.character_name == character_name,
        )
    )
    result = await db.execute(exists_stmt)
    count = result.scalar()

    if not count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character '{character_name}' not found",
        )

    # Get stats
    stats_stmt = (
        select(
            func.count().label("total_runs"),
            func.max(CombatRun.dps).label("best_dps"),
            func.avg(CombatRun.dps).label("avg_dps"),
            func.max(CombatRun.timestamp).label("last_played"),
            func.max(CombatRun.cp_level).label("cp_level"),
            func.sum(CombatRun.duration_sec).label("total_play_time"),
        )
        .where(
            and_(
                CombatRun.player_id == user.id,
                CombatRun.character_name == character_name,
            )
        )
    )
    stats_result = await db.execute(stats_stmt)
    stats = stats_result.one()

    # Get latest build
    latest_stmt = (
        select(CombatRun.build_snapshot)
        .where(
            and_(
                CombatRun.player_id == user.id,
                CombatRun.character_name == character_name,
            )
        )
        .order_by(CombatRun.timestamp.desc())
        .limit(1)
    )
    latest_result = await db.execute(latest_stmt)
    build_snapshot = latest_result.scalar()

    return {
        "character_name": character_name,
        "total_runs": stats.total_runs,
        "best_dps": round(float(stats.best_dps), 0) if stats.best_dps else 0,
        "avg_dps": round(float(stats.avg_dps), 0) if stats.avg_dps else 0,
        "last_played": stats.last_played.isoformat() if stats.last_played else None,
        "cp_level": stats.cp_level,
        "total_play_time_sec": stats.total_play_time or 0,
        "build": build_snapshot or {},
    }
