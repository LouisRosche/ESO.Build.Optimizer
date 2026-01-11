"""
Combat run routes for ESO Build Optimizer API.

Handles submission, retrieval, and management of combat runs.
"""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Integer, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.security import CurrentUser
from api.models.database import CombatRun, Recommendation, get_db
from api.models.schemas import (
    CombatRunCreate,
    CombatRunFilters,
    CombatRunListItem,
    CombatRunResponse,
    ContentType,
    Difficulty,
    ErrorResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/runs", tags=["Combat Runs"])


# =============================================================================
# Submit Combat Run
# =============================================================================

@router.post(
    "",
    response_model=CombatRunResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Combat run submitted successfully"},
        400: {"description": "Invalid run data", "model": ErrorResponse},
        401: {"description": "Not authenticated", "model": ErrorResponse},
    },
    summary="Submit a combat run",
    description="Submit a new combat run with metrics and build snapshot.",
)
async def submit_run(
    run_data: CombatRunCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CombatRunResponse:
    """
    Submit a new combat run.

    The run will be associated with the authenticated user and
    contribution scores will be calculated asynchronously.
    """
    # Create combat run record
    new_run = CombatRun(
        player_id=current_user.id,
        character_name=run_data.character_name,
        content_type=run_data.content.content_type.value,
        content_name=run_data.content.name,
        difficulty=run_data.content.difficulty.value,
        duration_sec=run_data.duration_sec,
        success=run_data.success,
        group_size=run_data.group_size,
        build_snapshot=run_data.build_snapshot.model_dump(by_alias=True),
        metrics=run_data.metrics.model_dump(),
        dps=run_data.metrics.dps,
        cp_level=run_data.build_snapshot.cp_level,
    )

    db.add(new_run)
    await db.commit()
    await db.refresh(new_run)

    return CombatRunResponse(
        run_id=new_run.run_id,
        player_id=new_run.player_id,
        character_name=new_run.character_name,
        timestamp=new_run.timestamp,
        content=run_data.content,
        duration_sec=new_run.duration_sec,
        success=new_run.success,
        group_size=new_run.group_size,
        build_snapshot=run_data.build_snapshot,
        metrics=run_data.metrics,
        contribution_scores=None,  # Will be calculated async
    )


# =============================================================================
# List Combat Runs
# =============================================================================

class RunsListResponse(PaginatedResponse):
    """Response model for runs list."""
    runs: list[CombatRunListItem]


@router.get(
    "",
    response_model=RunsListResponse,
    responses={
        200: {"description": "List of combat runs"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
    },
    summary="List combat runs",
    description="Get a paginated list of the current user's combat runs with optional filtering.",
)
async def list_runs(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    content_type: ContentType | None = Query(None, description="Filter by content type"),
    content_name: str | None = Query(None, description="Filter by content name"),
    difficulty: Difficulty | None = Query(None, description="Filter by difficulty"),
    character_name: str | None = Query(None, description="Filter by character name"),
    success: bool | None = Query(None, description="Filter by success status"),
    from_date: datetime | None = Query(None, description="Filter runs after this date"),
    to_date: datetime | None = Query(None, description="Filter runs before this date"),
    min_dps: float | None = Query(None, ge=0, description="Minimum DPS threshold"),
    limit: int = Query(50, ge=1, le=100, description="Number of results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> RunsListResponse:
    """
    List the current user's combat runs with optional filtering.

    Supports filtering by content type, name, difficulty, character,
    success status, date range, and minimum DPS.
    """
    # Build query with filters
    query = select(CombatRun).where(CombatRun.player_id == current_user.id)

    if content_type:
        query = query.where(CombatRun.content_type == content_type.value)
    if content_name:
        query = query.where(CombatRun.content_name.ilike(f"%{content_name}%"))
    if difficulty:
        query = query.where(CombatRun.difficulty == difficulty.value)
    if character_name:
        query = query.where(CombatRun.character_name.ilike(f"%{character_name}%"))
    if success is not None:
        query = query.where(CombatRun.success == success)
    if from_date:
        query = query.where(CombatRun.timestamp >= from_date)
    if to_date:
        query = query.where(CombatRun.timestamp <= to_date)
    if min_dps is not None:
        query = query.where(CombatRun.dps >= min_dps)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(CombatRun.timestamp.desc())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    runs = result.scalars().all()

    # Convert to list items
    run_items = [
        CombatRunListItem(
            run_id=run.run_id,
            character_name=run.character_name,
            content_name=run.content_name,
            content_type=ContentType(run.content_type),
            difficulty=Difficulty(run.difficulty),
            timestamp=run.timestamp,
            duration_sec=run.duration_sec,
            success=run.success,
            dps=run.dps,
        )
        for run in runs
    ]

    return RunsListResponse(
        runs=run_items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(run_items) < total,
    )


# =============================================================================
# Get Single Combat Run
# =============================================================================

@router.get(
    "/{run_id}",
    response_model=CombatRunResponse,
    responses={
        200: {"description": "Combat run details"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
        403: {"description": "Access denied", "model": ErrorResponse},
        404: {"description": "Run not found", "model": ErrorResponse},
    },
    summary="Get combat run details",
    description="Get detailed information about a specific combat run.",
)
async def get_run(
    run_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CombatRunResponse:
    """
    Get details of a specific combat run.

    Returns full metrics, build snapshot, and contribution scores.
    """
    result = await db.execute(
        select(CombatRun).where(CombatRun.run_id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Combat run not found",
        )

    # Check ownership
    if run.player_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this combat run",
        )

    # Reconstruct response from stored data
    from api.models.schemas import (
        BuildSnapshot,
        CombatMetrics,
        ContentInfo,
        ContributionScores,
    )

    return CombatRunResponse(
        run_id=run.run_id,
        player_id=run.player_id,
        character_name=run.character_name,
        timestamp=run.timestamp,
        content=ContentInfo(
            type=ContentType(run.content_type),
            name=run.content_name,
            difficulty=Difficulty(run.difficulty),
        ),
        duration_sec=run.duration_sec,
        success=run.success,
        group_size=run.group_size,
        build_snapshot=BuildSnapshot.model_validate(run.build_snapshot),
        metrics=CombatMetrics.model_validate(run.metrics),
        contribution_scores=(
            ContributionScores.model_validate(run.contribution_scores)
            if run.contribution_scores
            else None
        ),
    )


# =============================================================================
# Delete Combat Run
# =============================================================================

@router.delete(
    "/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Combat run deleted"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
        403: {"description": "Access denied", "model": ErrorResponse},
        404: {"description": "Run not found", "model": ErrorResponse},
    },
    summary="Delete combat run",
    description="Delete a combat run and its associated recommendations.",
)
async def delete_run(
    run_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a combat run.

    This will also delete all recommendations associated with the run.
    """
    result = await db.execute(
        select(CombatRun).where(CombatRun.run_id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Combat run not found",
        )

    if run.player_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this combat run",
        )

    await db.delete(run)
    await db.commit()


# =============================================================================
# Get Run Statistics
# =============================================================================

class RunStatistics(PaginatedResponse):
    """Statistics for user's runs."""
    total_runs: int
    successful_runs: int
    average_dps: float
    best_dps: float
    total_play_time_sec: int
    favorite_content: str | None
    favorite_character: str | None


@router.get(
    "/stats/summary",
    response_model=RunStatistics,
    responses={
        200: {"description": "Run statistics"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
    },
    summary="Get run statistics",
    description="Get aggregated statistics for the current user's combat runs.",
)
async def get_run_statistics(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RunStatistics:
    """
    Get aggregated statistics for the user's combat runs.

    Includes total runs, success rate, average DPS, and favorites.
    """
    # Get basic stats
    stats_query = select(
        func.count(CombatRun.run_id).label("total"),
        func.sum(CombatRun.success.cast(Integer)).label("successful"),
        func.avg(CombatRun.dps).label("avg_dps"),
        func.max(CombatRun.dps).label("max_dps"),
        func.sum(CombatRun.duration_sec).label("total_time"),
    ).where(CombatRun.player_id == current_user.id)

    result = await db.execute(stats_query)
    stats = result.one()

    # Get favorite content (most played)
    content_query = (
        select(CombatRun.content_name, func.count().label("count"))
        .where(CombatRun.player_id == current_user.id)
        .group_by(CombatRun.content_name)
        .order_by(func.count().desc())
        .limit(1)
    )
    content_result = await db.execute(content_query)
    favorite_content = content_result.first()

    # Get favorite character (most used)
    char_query = (
        select(CombatRun.character_name, func.count().label("count"))
        .where(CombatRun.player_id == current_user.id)
        .group_by(CombatRun.character_name)
        .order_by(func.count().desc())
        .limit(1)
    )
    char_result = await db.execute(char_query)
    favorite_char = char_result.first()

    return RunStatistics(
        total=stats.total or 0,
        limit=0,
        offset=0,
        has_more=False,
        total_runs=stats.total or 0,
        successful_runs=stats.successful or 0,
        average_dps=float(stats.avg_dps or 0),
        best_dps=float(stats.max_dps or 0),
        total_play_time_sec=stats.total_time or 0,
        favorite_content=favorite_content[0] if favorite_content else None,
        favorite_character=favorite_char[0] if favorite_char else None,
    )


# =============================================================================
# Compare Runs
# =============================================================================

class RunComparison(PaginatedResponse):
    """Comparison between two runs."""
    run_a: CombatRunListItem
    run_b: CombatRunListItem
    dps_diff: float
    dps_diff_percent: float
    duration_diff_sec: int
    build_differences: dict


@router.get(
    "/compare/{run_id_a}/{run_id_b}",
    response_model=RunComparison,
    responses={
        200: {"description": "Run comparison"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
        403: {"description": "Access denied", "model": ErrorResponse},
        404: {"description": "One or both runs not found", "model": ErrorResponse},
    },
    summary="Compare two runs",
    description="Compare metrics and builds between two combat runs.",
)
async def compare_runs(
    run_id_a: UUID,
    run_id_b: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RunComparison:
    """
    Compare two combat runs.

    Both runs must belong to the current user.
    Returns differences in DPS, duration, and build configuration.
    """
    # Fetch both runs
    result_a = await db.execute(
        select(CombatRun).where(CombatRun.run_id == run_id_a)
    )
    run_a = result_a.scalar_one_or_none()

    result_b = await db.execute(
        select(CombatRun).where(CombatRun.run_id == run_id_b)
    )
    run_b = result_b.scalar_one_or_none()

    if not run_a or not run_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both combat runs not found",
        )

    if run_a.player_id != current_user.id or run_b.player_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to one or both runs",
        )

    # Calculate differences
    dps_diff = run_a.dps - run_b.dps
    dps_diff_percent = (
        (dps_diff / run_b.dps * 100) if run_b.dps > 0 else 0
    )

    # Compare builds
    build_a = run_a.build_snapshot
    build_b = run_b.build_snapshot
    build_differences = {}

    if build_a.get("sets") != build_b.get("sets"):
        build_differences["sets"] = {
            "run_a": build_a.get("sets", []),
            "run_b": build_b.get("sets", []),
        }

    if build_a.get("skills_front") != build_b.get("skills_front"):
        build_differences["skills_front"] = {
            "run_a": build_a.get("skills_front", []),
            "run_b": build_b.get("skills_front", []),
        }

    if build_a.get("skills_back") != build_b.get("skills_back"):
        build_differences["skills_back"] = {
            "run_a": build_a.get("skills_back", []),
            "run_b": build_b.get("skills_back", []),
        }

    return RunComparison(
        total=2,
        limit=2,
        offset=0,
        has_more=False,
        run_a=CombatRunListItem(
            run_id=run_a.run_id,
            character_name=run_a.character_name,
            content_name=run_a.content_name,
            content_type=ContentType(run_a.content_type),
            difficulty=Difficulty(run_a.difficulty),
            timestamp=run_a.timestamp,
            duration_sec=run_a.duration_sec,
            success=run_a.success,
            dps=run_a.dps,
        ),
        run_b=CombatRunListItem(
            run_id=run_b.run_id,
            character_name=run_b.character_name,
            content_name=run_b.content_name,
            content_type=ContentType(run_b.content_type),
            difficulty=Difficulty(run_b.difficulty),
            timestamp=run_b.timestamp,
            duration_sec=run_b.duration_sec,
            success=run_b.success,
            dps=run_b.dps,
        ),
        dps_diff=dps_diff,
        dps_diff_percent=dps_diff_percent,
        duration_diff_sec=run_a.duration_sec - run_b.duration_sec,
        build_differences=build_differences,
    )
