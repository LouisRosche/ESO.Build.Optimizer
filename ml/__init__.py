"""
ESO Build Optimizer - Machine Learning Module

This module provides ML-powered analytics for ESO combat performance:
- Percentile calculation against similar runs
- Contribution analysis and classification
- Recommendation generation

Example:
    from ml.percentile import PercentileCalculator, CombatRun
    from ml.recommendations import RecommendationEngine

    calculator = PercentileCalculator()
    result = calculator.calculate_percentile(player_run, population)

    engine = RecommendationEngine()
    recommendations = engine.generate_recommendations(run, percentiles)
"""

from ml.percentile import (
    # Core classes
    PercentileCalculator,
    CombatRun,
    ContributionMetrics,
    ContentInfo,
    SimilarityCriteria,
    PercentileResult,
    # Enums
    ContentType,
    Difficulty,
    RoleType,
    # Constants
    CONTRIBUTION_CATEGORIES,
    DEFAULT_CATEGORY_WEIGHTS,
    ROLE_WEIGHT_PROFILES,
    # Utility functions
    create_combat_run_from_dict,
    calculate_player_percentile,
)

from ml.recommendations import (
    # Core classes
    RecommendationEngine,
    Recommendation,
    FeatureDatabase,
    BuildSnapshot,
    BuildDiff,
    CombatMetrics,
    ContributionScores,
    UserPreferences,
    # Enums
    RecommendationCategory,
    ContributionMetric,
    SetType,
    # Factory functions
    create_recommendation_engine,
)

__all__ = [
    # Percentile module
    "PercentileCalculator",
    "CombatRun",
    "ContributionMetrics",
    "ContentInfo",
    "SimilarityCriteria",
    "PercentileResult",
    "ContentType",
    "Difficulty",
    "RoleType",
    "CONTRIBUTION_CATEGORIES",
    "DEFAULT_CATEGORY_WEIGHTS",
    "ROLE_WEIGHT_PROFILES",
    "create_combat_run_from_dict",
    "calculate_player_percentile",
    # Recommendation module
    "RecommendationEngine",
    "Recommendation",
    "RecommendationCategory",
    "ContributionMetric",
    "FeatureDatabase",
    "BuildSnapshot",
    "BuildDiff",
    "CombatMetrics",
    "ContributionScores",
    "UserPreferences",
    "SetType",
    "create_recommendation_engine",
]

__version__ = "0.1.0"
