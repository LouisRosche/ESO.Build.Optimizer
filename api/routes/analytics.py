"""
Analytics routes for ESO Build Optimizer API.

Provides DPS trends, percentile trends, and buff analysis
derived from combat run history.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.security import CurrentUser
from api.models.database import CombatRun, get_db

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dps-trend")
async def get_dps_trend(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    time_range: str = Query("30d", description="Time range: 7d, 30d, 90d, all"),
    character_name: str | None = Query(None),
) -> list[dict]:
    """Get DPS trend over time for the authenticated user."""
    cutoff = _parse_time_range(time_range)

    conditions = [CombatRun.player_id == user.id]
    if cutoff:
        conditions.append(CombatRun.timestamp >= cutoff)
    if character_name:
        conditions.append(CombatRun.character_name == character_name)

    # Group by date, return average DPS per day
    stmt = (
        select(
            func.date(CombatRun.timestamp).label("date"),
            func.avg(CombatRun.dps).label("avg_dps"),
            func.max(CombatRun.dps).label("max_dps"),
            func.count().label("run_count"),
        )
        .where(and_(*conditions))
        .group_by(func.date(CombatRun.timestamp))
        .order_by(func.date(CombatRun.timestamp))
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "date": str(row.date),
            "avg_dps": round(float(row.avg_dps), 0) if row.avg_dps else 0,
            "max_dps": round(float(row.max_dps), 0) if row.max_dps else 0,
            "run_count": row.run_count,
        }
        for row in rows
    ]


@router.get("/percentile-trend")
async def get_percentile_trend(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    time_range: str = Query("30d"),
    character_name: str | None = Query(None),
) -> list[dict]:
    """
    Get percentile trend over time.

    For each of the user's runs, compute what percentile their DPS falls
    within all runs for that same content+difficulty on that day.
    """
    cutoff = _parse_time_range(time_range)

    conditions = [CombatRun.player_id == user.id]
    if cutoff:
        conditions.append(CombatRun.timestamp >= cutoff)
    if character_name:
        conditions.append(CombatRun.character_name == character_name)

    # Get user's runs
    stmt = (
        select(CombatRun)
        .where(and_(*conditions))
        .order_by(CombatRun.timestamp)
    )
    result = await db.execute(stmt)
    user_runs = result.scalars().all()

    if not user_runs:
        return []

    # For each run, compute percentile against all runs with same content
    trend = []
    for run in user_runs:
        count_stmt = select(func.count()).select_from(CombatRun).where(
            and_(
                CombatRun.content_name == run.content_name,
                CombatRun.difficulty == run.difficulty,
            )
        )
        below_stmt = select(func.count()).select_from(CombatRun).where(
            and_(
                CombatRun.content_name == run.content_name,
                CombatRun.difficulty == run.difficulty,
                CombatRun.dps < run.dps,
            )
        )

        total_result = await db.execute(count_stmt)
        below_result = await db.execute(below_stmt)
        total = total_result.scalar() or 1
        below = below_result.scalar() or 0

        percentile = round((below / total) * 100, 1)
        trend.append({
            "date": run.timestamp.isoformat() if run.timestamp else None,
            "percentile": percentile,
            "dps": round(float(run.dps), 0) if run.dps else 0,
            "content_name": run.content_name,
        })

    return trend


@router.get("/buff-analysis")
async def get_buff_analysis(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    time_range: str = Query("30d"),
    character_name: str | None = Query(None),
) -> list[dict]:
    """
    Get buff uptime analysis across recent runs.

    Aggregates buff_uptime from metrics JSON across runs to show
    average uptimes for each tracked buff.
    """
    cutoff = _parse_time_range(time_range)

    conditions = [CombatRun.player_id == user.id]
    if cutoff:
        conditions.append(CombatRun.timestamp >= cutoff)
    if character_name:
        conditions.append(CombatRun.character_name == character_name)

    stmt = (
        select(CombatRun.metrics)
        .where(and_(*conditions))
        .order_by(CombatRun.timestamp.desc())
        .limit(50)
    )

    result = await db.execute(stmt)
    metrics_list = [row[0] for row in result.all() if row[0]]

    if not metrics_list:
        return []

    # Aggregate buff uptimes across runs
    buff_totals: dict[str, list[float]] = {}
    for metrics in metrics_list:
        buff_uptime = metrics.get("buff_uptime", {})
        if isinstance(buff_uptime, dict):
            for buff_name, uptime in buff_uptime.items():
                if buff_name not in buff_totals:
                    buff_totals[buff_name] = []
                try:
                    buff_totals[buff_name].append(float(uptime))
                except (ValueError, TypeError):
                    pass

    # Compute averages and classify importance
    analysis = []
    for buff_name, uptimes in sorted(buff_totals.items()):
        avg_uptime = sum(uptimes) / len(uptimes)
        importance = "high" if "Major" in buff_name else "medium" if "Minor" in buff_name else "low"
        analysis.append({
            "buff_name": buff_name,
            "avg_uptime": round(avg_uptime, 3),
            "sample_count": len(uptimes),
            "importance": importance,
        })

    # Sort by importance then uptime
    importance_order = {"high": 0, "medium": 1, "low": 2}
    analysis.sort(key=lambda x: (importance_order.get(x["importance"], 3), -x["avg_uptime"]))

    return analysis


def _parse_time_range(time_range: str) -> datetime | None:
    """Parse a time range string like '7d', '30d', '90d' into a cutoff datetime."""
    now = datetime.now(timezone.utc)
    if time_range == "7d":
        return now - timedelta(days=7)
    elif time_range == "30d":
        return now - timedelta(days=30)
    elif time_range == "90d":
        return now - timedelta(days=90)
    return None  # "all"
