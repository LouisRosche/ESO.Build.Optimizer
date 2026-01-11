"""
Recommendation routes for ESO Build Optimizer API.

Handles generation and retrieval of build recommendations.
"""

import bisect
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.security import CurrentUser
from api.models.database import CombatRun, Recommendation, get_db
from api.models.schemas import (
    ErrorResponse,
    RecommendationCategory,
    RecommendationResponse,
    RecommendationsListResponse,
)

router = APIRouter(prefix="/runs", tags=["Recommendations"])


# =============================================================================
# Percentile Calculation
# =============================================================================

CONTRIBUTION_METRICS = [
    "damage_dealt",
    "healing_done",
    "buff_uptime",
    "debuff_uptime",
    "mechanic_execution",
    "resource_efficiency",
]


async def calculate_percentiles(
    run: CombatRun,
    db: AsyncSession,
) -> tuple[dict[str, float], int, str]:
    """
    Calculate percentiles for a combat run compared to similar runs.

    Similarity criteria:
    - Same content (dungeon name + difficulty)
    - Similar CP level (+/- 200)

    Returns:
        Tuple of (percentiles dict, sample size, confidence level)
    """
    # Find similar runs
    similar_query = (
        select(CombatRun)
        .where(
            and_(
                CombatRun.content_name == run.content_name,
                CombatRun.difficulty == run.difficulty,
                CombatRun.cp_level.between(run.cp_level - 200, run.cp_level + 200),
                CombatRun.run_id != run.run_id,
            )
        )
        .limit(1000)  # Limit for performance
    )

    result = await db.execute(similar_query)
    similar_runs = result.scalars().all()

    sample_size = len(similar_runs)

    # Determine confidence based on sample size
    if sample_size < 10:
        confidence = "low"
    elif sample_size < 50:
        confidence = "medium"
    else:
        confidence = "high"

    if sample_size == 0:
        # No comparison data available
        return {}, 0, "low"

    # Calculate percentiles for DPS (primary metric)
    dps_values = sorted([r.dps for r in similar_runs])
    player_dps = run.dps
    if len(dps_values) > 0:
        dps_percentile = bisect.bisect_left(dps_values, player_dps) / len(dps_values)
    else:
        dps_percentile = 0.0

    percentiles = {
        "dps": dps_percentile,
        "damage_dealt": dps_percentile,  # Proxy for now
    }

    # Calculate percentiles for other metrics if contribution scores exist
    if run.contribution_scores:
        for metric in CONTRIBUTION_METRICS:
            if metric in run.contribution_scores:
                # Get metric values from similar runs that have contribution scores
                metric_values = sorted([
                    r.contribution_scores.get(metric, 0)
                    for r in similar_runs
                    if r.contribution_scores and metric in r.contribution_scores
                ])
                if len(metric_values) > 0:
                    player_value = run.contribution_scores.get(metric, 0)
                    percentiles[metric] = (
                        bisect.bisect_left(metric_values, player_value) / len(metric_values)
                    )
                else:
                    percentiles[metric] = 0.0

    return percentiles, sample_size, confidence


# =============================================================================
# Recommendation Generation
# =============================================================================

async def generate_recommendations_for_run(
    run: CombatRun,
    percentiles: dict[str, float],
    db: AsyncSession,
) -> list[Recommendation]:
    """
    Generate recommendations based on run performance and percentiles.

    This is a placeholder implementation. The full ML-based recommendation
    engine will be implemented in the ml/ module.
    """
    recommendations = []
    priority = 1

    # Find weakest areas (below 50th percentile)
    weak_areas = [
        (metric, pct)
        for metric, pct in percentiles.items()
        if pct < 0.5
    ]
    weak_areas.sort(key=lambda x: x[1])

    # Generate recommendations for weak areas
    for metric, pct in weak_areas[:3]:  # Top 3 weakest
        if metric == "dps" or metric == "damage_dealt":
            # DPS-related recommendation
            build = run.build_snapshot
            current_sets = build.get("sets", [])

            rec = Recommendation(
                run_id=run.run_id,
                category="gear",
                priority=priority,
                current_state=f"Current sets: {', '.join(current_sets)}",
                recommended_change=(
                    "Consider optimizing your gear sets for higher DPS output. "
                    "Look into trial sets like Bahsei's Mania or Kinras's Wrath."
                ),
                expected_improvement=f"Potential +{int((0.5 - pct) * 20)}% DPS based on similar players",
                reasoning=(
                    f"Your DPS is at the {int(pct * 100)}th percentile for this content. "
                    "Higher-performing players typically use optimized gear combinations."
                ),
                confidence=0.7,
            )
            recommendations.append(rec)
            priority += 1

        elif metric == "buff_uptime":
            rec = Recommendation(
                run_id=run.run_id,
                category="execution",
                priority=priority,
                current_state="Buff uptime could be improved",
                recommended_change=(
                    "Focus on maintaining buffs more consistently. "
                    "Consider adding a skill that provides Major buffs."
                ),
                expected_improvement="Better buff uptime directly increases damage output",
                reasoning=(
                    f"Your buff uptime is at the {int(pct * 100)}th percentile. "
                    "Consistent buff maintenance is key to optimal performance."
                ),
                confidence=0.65,
            )
            recommendations.append(rec)
            priority += 1

        elif metric == "resource_efficiency":
            rec = Recommendation(
                run_id=run.run_id,
                category="skill",
                priority=priority,
                current_state="Resource management could be improved",
                recommended_change=(
                    "Consider adding a sustain skill or optimizing your rotation "
                    "to reduce resource waste."
                ),
                expected_improvement="Better sustain allows for more consistent ability usage",
                reasoning=(
                    f"Your resource efficiency is at the {int(pct * 100)}th percentile. "
                    "Running out of resources leads to damage downtime."
                ),
                confidence=0.6,
            )
            recommendations.append(rec)
            priority += 1

    return recommendations


# =============================================================================
# Get Recommendations for Run
# =============================================================================

@router.get(
    "/{run_id}/recommendations",
    response_model=RecommendationsListResponse,
    responses={
        200: {"description": "Recommendations for the run"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
        403: {"description": "Access denied", "model": ErrorResponse},
        404: {"description": "Run not found", "model": ErrorResponse},
    },
    summary="Get recommendations for a run",
    description="Get AI-generated recommendations to improve performance based on a combat run.",
)
async def get_recommendations(
    run_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    regenerate: bool = Query(
        False,
        description="Force regeneration of recommendations",
    ),
) -> RecommendationsListResponse:
    """
    Get recommendations for a specific combat run.

    Recommendations are generated by comparing the run's metrics
    against similar runs and identifying areas for improvement.

    Set regenerate=true to force new recommendations even if
    cached ones exist.
    """
    # Fetch the run
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

    # Check for existing recommendations
    if not regenerate:
        existing_result = await db.execute(
            select(Recommendation)
            .where(Recommendation.run_id == run_id)
            .order_by(Recommendation.priority)
        )
        existing_recs = existing_result.scalars().all()

        if existing_recs:
            # Return cached recommendations
            percentiles, sample_size, confidence = await calculate_percentiles(run, db)
            return RecommendationsListResponse(
                run_id=run_id,
                recommendations=[
                    RecommendationResponse(
                        recommendation_id=rec.recommendation_id,
                        run_id=rec.run_id,
                        category=RecommendationCategory(rec.category),
                        priority=rec.priority,
                        current_state=rec.current_state,
                        recommended_change=rec.recommended_change,
                        expected_improvement=rec.expected_improvement,
                        reasoning=rec.reasoning,
                        confidence=rec.confidence,
                    )
                    for rec in existing_recs
                ],
                percentiles=percentiles,
                sample_size=sample_size,
                confidence=confidence,
            )

    # Calculate percentiles
    percentiles, sample_size, confidence = await calculate_percentiles(run, db)

    # Generate new recommendations
    if regenerate:
        # Delete existing recommendations
        await db.execute(
            Recommendation.__table__.delete().where(
                Recommendation.run_id == run_id
            )
        )

    new_recommendations = await generate_recommendations_for_run(
        run, percentiles, db
    )

    # Save recommendations
    for rec in new_recommendations:
        db.add(rec)
    await db.commit()

    # Refresh to get IDs
    for rec in new_recommendations:
        await db.refresh(rec)

    return RecommendationsListResponse(
        run_id=run_id,
        recommendations=[
            RecommendationResponse(
                recommendation_id=rec.recommendation_id,
                run_id=rec.run_id,
                category=RecommendationCategory(rec.category),
                priority=rec.priority,
                current_state=rec.current_state,
                recommended_change=rec.recommended_change,
                expected_improvement=rec.expected_improvement,
                reasoning=rec.reasoning,
                confidence=rec.confidence,
            )
            for rec in new_recommendations
        ],
        percentiles=percentiles,
        sample_size=sample_size,
        confidence=confidence,
    )


# =============================================================================
# Get Percentiles Only
# =============================================================================

class PercentilesResponse(RecommendationsListResponse):
    """Response for percentiles endpoint."""
    pass


@router.get(
    "/{run_id}/percentiles",
    response_model=PercentilesResponse,
    responses={
        200: {"description": "Percentiles for the run"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
        403: {"description": "Access denied", "model": ErrorResponse},
        404: {"description": "Run not found", "model": ErrorResponse},
    },
    summary="Get percentiles for a run",
    description="Get percentile rankings compared to similar runs without generating recommendations.",
)
async def get_percentiles(
    run_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PercentilesResponse:
    """
    Get percentile rankings for a combat run.

    Compares the run against similar runs (same content, similar CP level)
    to determine where the player ranks.
    """
    # Fetch the run
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

    # Calculate percentiles
    percentiles, sample_size, confidence = await calculate_percentiles(run, db)

    return PercentilesResponse(
        run_id=run_id,
        recommendations=[],
        percentiles=percentiles,
        sample_size=sample_size,
        confidence=confidence,
    )


# =============================================================================
# Global Leaderboard
# =============================================================================

class LeaderboardEntry(RecommendationResponse):
    """Leaderboard entry with player info."""
    rank: int
    character_name: str
    dps: float
    content_name: str
    difficulty: str


class LeaderboardResponse(RecommendationsListResponse):
    """Response for leaderboard endpoint."""
    entries: list[LeaderboardEntry]
    content_name: str
    difficulty: str


# Note: A proper leaderboard would be in a separate router, but including
# a simple version here for reference
