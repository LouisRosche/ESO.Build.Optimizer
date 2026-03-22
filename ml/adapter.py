"""
ML Pipeline Adapter for the FastAPI Backend

Converts between SQLAlchemy database models (api.models.database) and
ML pipeline dataclasses (ml.recommendations), then runs the sync ML
engine in an async-compatible way via run_in_executor.

Usage in API routes:
    from ml.adapter import MLAdapter

    adapter = MLAdapter()
    percentiles, recs = await adapter.analyze_run(db_run, db_similar_runs)
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from ml.recommendations import (
    BuildSnapshot,
    CombatMetrics,
    CombatRun as MLCombatRun,
    ContentInfo as MLContentInfo,
    ContributionScores,
    PercentileResults,
    Recommendation as MLRecommendation,
    RecommendationEngine,
)

if TYPE_CHECKING:
    from api.models.database import CombatRun as DBCombatRun, Recommendation as DBRecommendation

logger = logging.getLogger(__name__)

# Shared executor for ML work (CPU-bound, keep pool small)
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ml-pipeline")


def db_run_to_ml_run(db_run: DBCombatRun) -> MLCombatRun:
    """Convert a SQLAlchemy CombatRun to an ML pipeline CombatRun.

    Args:
        db_run: Database combat run model.

    Returns:
        ML pipeline CombatRun dataclass.
    """
    build_data = db_run.build_snapshot or {}
    metrics_data = db_run.metrics or {}
    contrib_data = db_run.contribution_scores or {}

    return MLCombatRun(
        run_id=str(db_run.run_id),
        player_id=str(db_run.player_id),
        character_name=db_run.character_name,
        timestamp=db_run.timestamp,
        content=MLContentInfo(
            content_type=db_run.content_type,
            name=db_run.content_name,
            difficulty=db_run.difficulty,
        ),
        duration_sec=db_run.duration_sec,
        success=db_run.success,
        group_size=db_run.group_size,
        build_snapshot=BuildSnapshot(
            player_class=build_data.get("class", "Unknown"),
            subclass=build_data.get("subclass"),
            race=build_data.get("race", "Unknown"),
            cp_level=build_data.get("cp_level", db_run.cp_level),
            sets=build_data.get("sets", []),
            skills_front=build_data.get("skills_front", []),
            skills_back=build_data.get("skills_back", []),
            champion_points=build_data.get("champion_points", {}),
        ),
        metrics=CombatMetrics(
            damage_done=metrics_data.get("damage_done", 0),
            dps=metrics_data.get("dps", db_run.dps),
            crit_rate=metrics_data.get("crit_rate", 0.0),
            healing_done=metrics_data.get("healing_done", 0),
            hps=metrics_data.get("hps", 0.0),
            overhealing=metrics_data.get("overhealing", 0),
            damage_taken=metrics_data.get("damage_taken", 0),
            damage_blocked=metrics_data.get("damage_blocked", 0),
            damage_mitigated=metrics_data.get("damage_mitigated", 0),
            buff_uptime=metrics_data.get("buff_uptime", {}),
            debuff_uptime=metrics_data.get("debuff_uptime", {}),
            deaths=metrics_data.get("deaths", 0),
            interrupts=metrics_data.get("interrupts", 0),
            synergies_used=metrics_data.get("synergies_used", 0),
        ),
        contribution_scores=ContributionScores(
            damage_dealt=contrib_data.get("damage_dealt", 0.0),
            damage_taken=contrib_data.get("damage_taken", 0.0),
            healing_done=contrib_data.get("healing_done", 0.0),
            buff_uptime=contrib_data.get("buff_uptime", 0.0),
            debuff_uptime=contrib_data.get("debuff_uptime", 0.0),
            mechanic_execution=contrib_data.get("mechanic_execution", 0.0),
            resource_efficiency=contrib_data.get("resource_efficiency", 0.0),
        ),
    )


def ml_recommendation_to_dict(rec: MLRecommendation) -> dict[str, Any]:
    """Convert an ML Recommendation to a dict suitable for creating a DB Recommendation.

    Args:
        rec: ML pipeline recommendation dataclass.

    Returns:
        Dict with fields matching the DB Recommendation model.
    """
    return {
        "category": rec.category.value,
        "priority": rec.priority,
        "current_state": rec.current_state,
        "recommended_change": rec.recommended_change,
        "expected_improvement": rec.expected_improvement,
        "reasoning": rec.reasoning,
        "confidence": rec.confidence,
    }


def percentile_results_to_dict(results: PercentileResults) -> dict[str, float]:
    """Extract flat percentile dict from PercentileResults.

    Args:
        results: ML pipeline percentile results.

    Returns:
        Dict mapping metric name to percentile value (0.0-1.0).
    """
    return {
        metric: pr.percentile
        for metric, pr in results.percentiles.items()
    }


class MLAdapter:
    """Bridges the async API layer with the sync ML pipeline.

    Maintains a singleton RecommendationEngine and provides async methods
    that run ML computations off the event loop via a thread pool.
    """

    def __init__(self) -> None:
        self._engine = RecommendationEngine()

    async def analyze_run(
        self,
        db_run: DBCombatRun,
        db_similar_runs: list[DBCombatRun],
    ) -> tuple[dict[str, float], int, str, list[dict[str, Any]]]:
        """Run full ML analysis: percentiles + recommendations.

        Args:
            db_run: The target combat run (DB model).
            db_similar_runs: Similar runs for comparison (DB models).

        Returns:
            Tuple of (percentiles_dict, sample_size, confidence, recommendation_dicts).
        """
        loop = asyncio.get_running_loop()

        ml_run = db_run_to_ml_run(db_run)
        ml_pool = [db_run_to_ml_run(r) for r in db_similar_runs]

        def _compute() -> tuple[PercentileResults, list[MLRecommendation]]:
            self._engine.add_runs(ml_pool)
            percentiles = self._engine.calculate_percentiles(ml_run, ml_pool)
            recs = self._engine.generate_recommendations(ml_run, percentiles)
            return percentiles, recs

        percentiles, recs = await loop.run_in_executor(_executor, _compute)

        pct_dict = percentile_results_to_dict(percentiles)
        rec_dicts = [ml_recommendation_to_dict(r) for r in recs]

        return pct_dict, percentiles.sample_size, percentiles.overall_confidence, rec_dicts

    async def calculate_percentiles_only(
        self,
        db_run: DBCombatRun,
        db_similar_runs: list[DBCombatRun],
    ) -> tuple[dict[str, float], int, str]:
        """Calculate percentiles without generating recommendations.

        Args:
            db_run: The target combat run (DB model).
            db_similar_runs: Similar runs for comparison (DB models).

        Returns:
            Tuple of (percentiles_dict, sample_size, confidence).
        """
        loop = asyncio.get_running_loop()

        ml_run = db_run_to_ml_run(db_run)
        ml_pool = [db_run_to_ml_run(r) for r in db_similar_runs]

        def _compute() -> PercentileResults:
            return self._engine.calculate_percentiles(ml_run, ml_pool)

        percentiles = await loop.run_in_executor(_executor, _compute)

        return (
            percentile_results_to_dict(percentiles),
            percentiles.sample_size,
            percentiles.overall_confidence,
        )
