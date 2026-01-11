#!/usr/bin/env python3
"""
ESO Build Optimizer - Percentile Calculation Engine

This module calculates player performance percentiles by comparing against similar runs.
It supports multiple similarity criteria, handles low sample sizes gracefully with
confidence scoring, and provides weighted percentile calculations.

Example usage:
    from ml.percentile import PercentileCalculator, CombatRun

    calculator = PercentileCalculator()
    result = calculator.calculate_percentile(player_run, population_runs)
    print(f"Damage percentile: {result['percentiles']['damage_dealt']:.1%}")
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache
from typing import Any, Callable, Optional

import numpy as np
from scipy import stats

# Configure logging
logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Types of PvE content in ESO."""
    DUNGEON = "dungeon"
    TRIAL = "trial"
    ARENA = "arena"
    OVERWORLD = "overworld"


class Difficulty(Enum):
    """Content difficulty levels."""
    NORMAL = "normal"
    VETERAN = "veteran"
    HARDMODE = "hardmode"


class RoleType(Enum):
    """Player role classifications."""
    TANK = "tank"
    HEALER = "healer"
    DPS = "dps"
    SUPPORT = "support"


# Contribution categories that we calculate percentiles for
CONTRIBUTION_CATEGORIES = [
    "damage_dealt",
    "damage_taken",
    "healing_done",
    "buff_uptime",
    "debuff_uptime",
    "mechanic_execution",
    "resource_efficiency",
]

# Default weights for combined score calculation
DEFAULT_CATEGORY_WEIGHTS = {
    "damage_dealt": 0.30,
    "damage_taken": 0.10,
    "healing_done": 0.15,
    "buff_uptime": 0.15,
    "debuff_uptime": 0.10,
    "mechanic_execution": 0.10,
    "resource_efficiency": 0.10,
}

# Role-specific weight profiles
ROLE_WEIGHT_PROFILES = {
    RoleType.DPS: {
        "damage_dealt": 0.50,
        "damage_taken": 0.05,
        "healing_done": 0.00,
        "buff_uptime": 0.15,
        "debuff_uptime": 0.10,
        "mechanic_execution": 0.10,
        "resource_efficiency": 0.10,
    },
    RoleType.HEALER: {
        "damage_dealt": 0.10,
        "damage_taken": 0.05,
        "healing_done": 0.45,
        "buff_uptime": 0.20,
        "debuff_uptime": 0.05,
        "mechanic_execution": 0.10,
        "resource_efficiency": 0.05,
    },
    RoleType.TANK: {
        "damage_dealt": 0.10,
        "damage_taken": 0.30,
        "healing_done": 0.05,
        "buff_uptime": 0.15,
        "debuff_uptime": 0.20,
        "mechanic_execution": 0.15,
        "resource_efficiency": 0.05,
    },
    RoleType.SUPPORT: {
        "damage_dealt": 0.20,
        "damage_taken": 0.10,
        "healing_done": 0.15,
        "buff_uptime": 0.25,
        "debuff_uptime": 0.15,
        "mechanic_execution": 0.10,
        "resource_efficiency": 0.05,
    },
}


@dataclass
class ContentInfo:
    """Information about the content being run."""
    content_type: ContentType
    name: str
    difficulty: Difficulty

    def matches(self, other: ContentInfo, strict: bool = True) -> bool:
        """Check if this content matches another.

        Args:
            other: The content to compare against.
            strict: If True, requires exact match. If False, allows same content
                   type with different difficulty.

        Returns:
            True if contents match according to criteria.
        """
        if strict:
            return (
                self.content_type == other.content_type
                and self.name == other.name
                and self.difficulty == other.difficulty
            )
        return self.content_type == other.content_type and self.name == other.name

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary representation."""
        return {
            "type": self.content_type.value,
            "name": self.name,
            "difficulty": self.difficulty.value,
        }


@dataclass
class ContributionMetrics:
    """Player contribution metrics from a combat run."""
    damage_dealt: float = 0.0
    damage_taken: float = 0.0
    healing_done: float = 0.0
    buff_uptime: float = 0.0
    debuff_uptime: float = 0.0
    mechanic_execution: float = 0.0
    resource_efficiency: float = 0.0

    def __post_init__(self):
        """Validate and clamp all values to [0.0, 1.0] range."""
        for category in CONTRIBUTION_CATEGORIES:
            value = getattr(self, category)
            clamped = max(0.0, min(1.0, float(value)))
            setattr(self, category, clamped)

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary representation."""
        return {cat: getattr(self, cat) for cat in CONTRIBUTION_CATEGORIES}

    def get(self, category: str) -> float:
        """Get a specific category value.

        Args:
            category: The contribution category name.

        Returns:
            The category value, or 0.0 if not found.
        """
        return getattr(self, category, 0.0)


@dataclass
class CombatRun:
    """Represents a single combat encounter run."""
    run_id: str
    player_id: str
    character_name: str
    timestamp: datetime
    content: ContentInfo
    duration_sec: int
    success: bool
    group_size: int
    cp_level: int
    role: RoleType
    metrics: ContributionMetrics
    build_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "run_id": self.run_id,
            "player_id": self.player_id,
            "character_name": self.character_name,
            "timestamp": self.timestamp.isoformat(),
            "content": self.content.to_dict(),
            "duration_sec": self.duration_sec,
            "success": self.success,
            "group_size": self.group_size,
            "cp_level": self.cp_level,
            "role": self.role.value,
            "metrics": self.metrics.to_dict(),
        }


@dataclass
class SimilarityCriteria:
    """Criteria for determining run similarity."""
    content_match: bool = True
    difficulty_match: bool = True
    group_size_tolerance: int = 1
    cp_range_tolerance: int = 200
    success_only: bool = True
    role_match: bool = False
    max_age_days: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "content_match": self.content_match,
            "difficulty_match": self.difficulty_match,
            "group_size_tolerance": self.group_size_tolerance,
            "cp_range_tolerance": self.cp_range_tolerance,
            "success_only": self.success_only,
            "role_match": self.role_match,
            "max_age_days": self.max_age_days,
        }

    def get_cache_key(self, run: CombatRun) -> str:
        """Generate a cache key for this criteria and run combination.

        Args:
            run: The combat run to generate key for.

        Returns:
            A hash string that uniquely identifies this query.
        """
        key_data = {
            "content": run.content.to_dict() if self.content_match else None,
            "group_size": run.group_size if self.group_size_tolerance == 0 else None,
            "cp_bucket": run.cp_level // 100 if self.cp_range_tolerance > 0 else None,
            "success_only": self.success_only,
            "role": run.role.value if self.role_match else None,
            "criteria": self.to_dict(),
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()


@dataclass
class PercentileResult:
    """Result of a percentile calculation."""
    percentiles: dict[str, float]
    weighted_overall: float
    confidence: float
    sample_size: int
    comparison_criteria: dict[str, Any]
    role: str
    statistics: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "percentiles": self.percentiles,
            "weighted_overall": self.weighted_overall,
            "confidence": self.confidence,
            "sample_size": self.sample_size,
            "comparison_criteria": self.comparison_criteria,
            "role": self.role,
            "statistics": self.statistics,
        }


class PercentileCacheEntry:
    """Cache entry for percentile distributions."""

    def __init__(
        self,
        distributions: dict[str, np.ndarray],
        sample_size: int,
        created_at: datetime,
        ttl_seconds: int = 3600,
    ):
        """Initialize cache entry.

        Args:
            distributions: Dictionary mapping category to sorted value arrays.
            sample_size: Number of samples in the distribution.
            created_at: When this cache entry was created.
            ttl_seconds: Time-to-live in seconds.
        """
        self.distributions = distributions
        self.sample_size = sample_size
        self.created_at = created_at
        self.ttl_seconds = ttl_seconds
        self.access_count = 0
        self.last_accessed = created_at

    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl_seconds

    def access(self) -> None:
        """Record an access to this cache entry."""
        self.access_count += 1
        self.last_accessed = datetime.now()


class PercentileCalculator:
    """
    Calculates player performance percentiles by comparing against similar runs.

    This class provides methods for:
    - Finding similar runs based on configurable criteria
    - Calculating percentiles for all contribution categories
    - Computing confidence scores based on sample size
    - Weighted overall percentile calculation
    - Batch processing of multiple runs

    Example:
        calculator = PercentileCalculator()

        # Calculate for a single run
        result = calculator.calculate_percentile(player_run, all_runs)

        # Batch process multiple runs
        results = calculator.calculate_batch(player_runs, all_runs)
    """

    # Minimum sample sizes for confidence levels
    MIN_SAMPLES_HIGH_CONFIDENCE = 100
    MIN_SAMPLES_MEDIUM_CONFIDENCE = 30
    MIN_SAMPLES_LOW_CONFIDENCE = 10

    def __init__(
        self,
        default_criteria: Optional[SimilarityCriteria] = None,
        cache_ttl_seconds: int = 3600,
        max_cache_entries: int = 1000,
    ):
        """Initialize the percentile calculator.

        Args:
            default_criteria: Default similarity criteria to use.
            cache_ttl_seconds: How long to keep cached distributions.
            max_cache_entries: Maximum number of cache entries to keep.
        """
        self.default_criteria = default_criteria or SimilarityCriteria()
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_cache_entries = max_cache_entries
        self._cache: dict[str, PercentileCacheEntry] = {}

    def calculate_percentile(
        self,
        run: CombatRun,
        population: list[CombatRun],
        criteria: Optional[SimilarityCriteria] = None,
        weights: Optional[dict[str, float]] = None,
        use_cache: bool = True,
    ) -> PercentileResult:
        """Calculate percentiles for a combat run against a population.

        This is the main entry point for percentile calculation. It:
        1. Filters the population to similar runs
        2. Calculates percentiles for each contribution category
        3. Computes a weighted overall score
        4. Determines confidence based on sample size

        Args:
            run: The combat run to calculate percentiles for.
            population: List of runs to compare against.
            criteria: Similarity criteria (uses default if not provided).
            weights: Category weights for overall score (uses role-based if not provided).
            use_cache: Whether to use cached distributions.

        Returns:
            PercentileResult with percentiles, confidence, and metadata.
        """
        criteria = criteria or self.default_criteria

        # Try to use cached distribution
        cache_key = criteria.get_cache_key(run)
        cached_entry = self._get_cached_distribution(cache_key) if use_cache else None

        if cached_entry is not None:
            similar_runs = None  # We don't need runs if we have cached distributions
            distributions = cached_entry.distributions
            sample_size = cached_entry.sample_size
        else:
            # Find similar runs
            similar_runs = self.get_similar_runs(run, population, criteria)
            sample_size = len(similar_runs)

            if sample_size == 0:
                return self._create_empty_result(run, criteria)

            # Build distributions
            distributions = self._build_distributions(similar_runs)

            # Cache the distributions
            if use_cache:
                self._cache_distribution(cache_key, distributions, sample_size)

        # Calculate percentiles for each category
        percentiles = self._calculate_category_percentiles(run, distributions)

        # Calculate weighted overall percentile
        effective_weights = self._get_effective_weights(run.role, weights)
        weighted_overall = self._calculate_weighted_percentile(percentiles, effective_weights)

        # Calculate confidence
        confidence = self.calculate_confidence(sample_size, run.content)

        # Calculate statistics for each category
        statistics = self._calculate_statistics(distributions)

        return PercentileResult(
            percentiles=percentiles,
            weighted_overall=weighted_overall,
            confidence=confidence,
            sample_size=sample_size,
            comparison_criteria=criteria.to_dict(),
            role=run.role.value,
            statistics=statistics,
        )

    def get_similar_runs(
        self,
        run: CombatRun,
        population: list[CombatRun],
        criteria: Optional[SimilarityCriteria] = None,
    ) -> list[CombatRun]:
        """Filter population to runs similar to the given run.

        Similarity is determined by the criteria, which can include:
        - Same content (dungeon name + difficulty)
        - Similar group size (within tolerance)
        - Similar CP level (within tolerance)
        - Same role (optional)
        - Successful runs only (optional)

        Args:
            run: The reference run to compare against.
            population: All available runs.
            criteria: The similarity criteria to apply.

        Returns:
            List of runs that match the similarity criteria.
        """
        criteria = criteria or self.default_criteria

        similar = []
        now = datetime.now()

        for candidate in population:
            # Skip the run itself
            if candidate.run_id == run.run_id:
                continue

            # Check success filter
            if criteria.success_only and not candidate.success:
                continue

            # Check content match
            if criteria.content_match:
                if not run.content.matches(
                    candidate.content,
                    strict=criteria.difficulty_match
                ):
                    continue

            # Check group size tolerance
            if abs(candidate.group_size - run.group_size) > criteria.group_size_tolerance:
                continue

            # Check CP range tolerance
            if abs(candidate.cp_level - run.cp_level) > criteria.cp_range_tolerance:
                continue

            # Check role match
            if criteria.role_match and candidate.role != run.role:
                continue

            # Check age
            if criteria.max_age_days is not None:
                age = (now - candidate.timestamp).days
                if age > criteria.max_age_days:
                    continue

            similar.append(candidate)

        return similar

    def calculate_confidence(
        self,
        sample_size: int,
        content: Optional[ContentInfo] = None,
    ) -> float:
        """Calculate confidence score based on sample size and content type.

        Confidence is a value between 0.0 and 1.0 that indicates how reliable
        the percentile calculation is. It depends on:
        - Sample size (larger = more confident)
        - Content type (trials have smaller populations, so lower threshold)

        Args:
            sample_size: Number of similar runs found.
            content: Optional content info for adjusting thresholds.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        if sample_size == 0:
            return 0.0

        # Adjust thresholds for content type
        high_threshold = self.MIN_SAMPLES_HIGH_CONFIDENCE
        medium_threshold = self.MIN_SAMPLES_MEDIUM_CONFIDENCE
        low_threshold = self.MIN_SAMPLES_LOW_CONFIDENCE

        if content is not None:
            # Trials have smaller populations, adjust thresholds down
            if content.content_type == ContentType.TRIAL:
                high_threshold = int(high_threshold * 0.5)
                medium_threshold = int(medium_threshold * 0.5)
                low_threshold = int(low_threshold * 0.5)
            # Hardmode is even rarer
            if content.difficulty == Difficulty.HARDMODE:
                high_threshold = int(high_threshold * 0.3)
                medium_threshold = int(medium_threshold * 0.3)
                low_threshold = int(low_threshold * 0.3)

        if sample_size >= high_threshold:
            # High confidence: 0.85 - 1.0
            extra = min(sample_size - high_threshold, high_threshold)
            return 0.85 + (0.15 * extra / high_threshold)
        elif sample_size >= medium_threshold:
            # Medium confidence: 0.5 - 0.85
            progress = (sample_size - medium_threshold) / (high_threshold - medium_threshold)
            return 0.5 + (0.35 * progress)
        elif sample_size >= low_threshold:
            # Low confidence: 0.2 - 0.5
            progress = (sample_size - low_threshold) / (medium_threshold - low_threshold)
            return 0.2 + (0.3 * progress)
        else:
            # Very low confidence: 0.0 - 0.2
            return 0.2 * (sample_size / low_threshold)

    def calculate_batch(
        self,
        runs: list[CombatRun],
        population: list[CombatRun],
        criteria: Optional[SimilarityCriteria] = None,
        weights: Optional[dict[str, float]] = None,
    ) -> list[PercentileResult]:
        """Calculate percentiles for multiple runs efficiently.

        This method leverages caching to avoid recalculating distributions
        for runs with the same similarity criteria.

        Args:
            runs: List of runs to calculate percentiles for.
            population: All available runs for comparison.
            criteria: Similarity criteria to use.
            weights: Category weights for overall score.

        Returns:
            List of PercentileResult objects in the same order as input runs.
        """
        results = []
        for run in runs:
            result = self.calculate_percentile(
                run, population, criteria, weights, use_cache=True
            )
            results.append(result)
        return results

    def calculate_weighted_percentile(
        self,
        values: list[float],
        percentile: float,
        weights: Optional[list[float]] = None,
    ) -> float:
        """Calculate a weighted percentile of a list of values.

        Uses linear interpolation for values between data points.

        Args:
            values: List of values to calculate percentile from.
            percentile: The percentile to calculate (0.0 to 1.0).
            weights: Optional weights for each value.

        Returns:
            The weighted percentile value.
        """
        if not values:
            return 0.0

        values_array = np.array(values, dtype=np.float64)

        if weights is None:
            return float(np.percentile(values_array, percentile * 100))

        weights_array = np.array(weights, dtype=np.float64)

        # Normalize weights
        weights_array = weights_array / weights_array.sum()

        # Sort by values
        sorted_indices = np.argsort(values_array)
        sorted_values = values_array[sorted_indices]
        sorted_weights = weights_array[sorted_indices]

        # Calculate cumulative weights
        cumsum = np.cumsum(sorted_weights)

        # Find the percentile position
        idx = np.searchsorted(cumsum, percentile)

        if idx == 0:
            return float(sorted_values[0])
        if idx >= len(sorted_values):
            return float(sorted_values[-1])

        # Linear interpolation
        lower_weight = cumsum[idx - 1]
        upper_weight = cumsum[idx]
        fraction = (percentile - lower_weight) / (upper_weight - lower_weight)

        return float(
            sorted_values[idx - 1] + fraction * (sorted_values[idx] - sorted_values[idx - 1])
        )

    def get_distribution_statistics(
        self,
        run: CombatRun,
        population: list[CombatRun],
        category: str,
        criteria: Optional[SimilarityCriteria] = None,
    ) -> dict[str, float]:
        """Get detailed statistics for a specific category.

        Args:
            run: The reference run.
            population: All available runs.
            category: The contribution category to analyze.
            criteria: Similarity criteria.

        Returns:
            Dictionary with mean, median, std, min, max, quartiles.
        """
        similar_runs = self.get_similar_runs(run, population, criteria)

        if not similar_runs:
            return {
                "mean": 0.0,
                "median": 0.0,
                "std": 0.0,
                "min": 0.0,
                "max": 0.0,
                "q25": 0.0,
                "q75": 0.0,
                "sample_size": 0,
            }

        values = np.array([r.metrics.get(category) for r in similar_runs])

        return {
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "q25": float(np.percentile(values, 25)),
            "q75": float(np.percentile(values, 75)),
            "sample_size": len(values),
        }

    def clear_cache(self) -> int:
        """Clear all cached distributions.

        Returns:
            Number of cache entries cleared.
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    def get_cache_stats(self) -> dict[str, Any]:
        """Get statistics about the cache.

        Returns:
            Dictionary with cache size, hit rate, etc.
        """
        if not self._cache:
            return {
                "size": 0,
                "total_accesses": 0,
                "average_accesses": 0,
                "oldest_entry_age_seconds": 0,
            }

        total_accesses = sum(e.access_count for e in self._cache.values())
        oldest = min(e.created_at for e in self._cache.values())

        return {
            "size": len(self._cache),
            "total_accesses": total_accesses,
            "average_accesses": total_accesses / len(self._cache),
            "oldest_entry_age_seconds": (datetime.now() - oldest).total_seconds(),
        }

    # Private methods

    def _build_distributions(
        self,
        runs: list[CombatRun],
    ) -> dict[str, np.ndarray]:
        """Build sorted value distributions for all categories.

        Args:
            runs: List of runs to build distributions from.

        Returns:
            Dictionary mapping category to sorted numpy array.
        """
        distributions = {}

        for category in CONTRIBUTION_CATEGORIES:
            values = np.array([r.metrics.get(category) for r in runs], dtype=np.float64)
            distributions[category] = np.sort(values)

        return distributions

    def _calculate_category_percentiles(
        self,
        run: CombatRun,
        distributions: dict[str, np.ndarray],
    ) -> dict[str, float]:
        """Calculate percentile for each category.

        Uses numpy's searchsorted for efficient percentile calculation.
        For damage_taken, the interpretation is inverted for non-tank roles
        (lower damage taken = higher percentile for DPS/healers).

        Args:
            run: The run to calculate percentiles for.
            distributions: Pre-sorted value distributions.

        Returns:
            Dictionary mapping category to percentile (0.0 to 1.0).
        """
        percentiles = {}

        for category in CONTRIBUTION_CATEGORIES:
            if category not in distributions or len(distributions[category]) == 0:
                percentiles[category] = 0.0
                continue

            values = distributions[category]
            player_value = run.metrics.get(category)

            # Calculate percentile using binary search
            position = np.searchsorted(values, player_value, side="left")
            percentile = position / len(values)

            # Invert damage_taken for non-tank roles
            # Lower damage taken = better for DPS/healers
            if category == "damage_taken" and run.role != RoleType.TANK:
                percentile = 1.0 - percentile

            percentiles[category] = float(percentile)

        return percentiles

    def _calculate_weighted_percentile(
        self,
        percentiles: dict[str, float],
        weights: dict[str, float],
    ) -> float:
        """Calculate weighted average of percentiles.

        Args:
            percentiles: Percentile for each category.
            weights: Weight for each category.

        Returns:
            Weighted average percentile.
        """
        total_weight = 0.0
        weighted_sum = 0.0

        for category, percentile in percentiles.items():
            weight = weights.get(category, 0.0)
            weighted_sum += percentile * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight

    def _calculate_statistics(
        self,
        distributions: dict[str, np.ndarray],
    ) -> dict[str, dict[str, float]]:
        """Calculate summary statistics for all distributions.

        Args:
            distributions: Pre-sorted value distributions.

        Returns:
            Dictionary mapping category to statistics dict.
        """
        statistics = {}

        for category, values in distributions.items():
            if len(values) == 0:
                statistics[category] = {
                    "mean": 0.0,
                    "median": 0.0,
                    "std": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                }
                continue

            statistics[category] = {
                "mean": float(np.mean(values)),
                "median": float(np.median(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
            }

        return statistics

    def _get_effective_weights(
        self,
        role: RoleType,
        custom_weights: Optional[dict[str, float]] = None,
    ) -> dict[str, float]:
        """Get effective weights for overall calculation.

        Uses custom weights if provided, otherwise uses role-based profile.

        Args:
            role: The player's role.
            custom_weights: Optional custom weight overrides.

        Returns:
            Effective weights dictionary.
        """
        if custom_weights is not None:
            return custom_weights

        return ROLE_WEIGHT_PROFILES.get(role, DEFAULT_CATEGORY_WEIGHTS)

    def _get_cached_distribution(
        self,
        cache_key: str,
    ) -> Optional[PercentileCacheEntry]:
        """Get a cached distribution if available and not expired.

        Args:
            cache_key: The cache key to look up.

        Returns:
            Cache entry if found and valid, None otherwise.
        """
        if cache_key not in self._cache:
            return None

        entry = self._cache[cache_key]

        if entry.is_expired():
            del self._cache[cache_key]
            return None

        entry.access()
        return entry

    def _cache_distribution(
        self,
        cache_key: str,
        distributions: dict[str, np.ndarray],
        sample_size: int,
    ) -> None:
        """Cache a distribution for later use.

        Implements LRU eviction when cache is full.

        Args:
            cache_key: The cache key.
            distributions: The distributions to cache.
            sample_size: The sample size.
        """
        # Evict old entries if cache is full
        if len(self._cache) >= self.max_cache_entries:
            self._evict_cache_entries()

        self._cache[cache_key] = PercentileCacheEntry(
            distributions=distributions,
            sample_size=sample_size,
            created_at=datetime.now(),
            ttl_seconds=self.cache_ttl_seconds,
        )

    def _evict_cache_entries(self) -> None:
        """Evict expired and least recently used cache entries."""
        # First, remove expired entries
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]

        # If still over limit, remove least recently used
        while len(self._cache) >= self.max_cache_entries:
            # Find least recently accessed entry
            lru_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].last_accessed
            )
            del self._cache[lru_key]

    def _create_empty_result(
        self,
        run: CombatRun,
        criteria: SimilarityCriteria,
    ) -> PercentileResult:
        """Create an empty result when no similar runs are found.

        Args:
            run: The run that was being calculated.
            criteria: The criteria used.

        Returns:
            PercentileResult with zero values and low confidence.
        """
        return PercentileResult(
            percentiles={cat: 0.0 for cat in CONTRIBUTION_CATEGORIES},
            weighted_overall=0.0,
            confidence=0.0,
            sample_size=0,
            comparison_criteria=criteria.to_dict(),
            role=run.role.value,
            statistics={},
        )


def create_combat_run_from_dict(data: dict[str, Any]) -> CombatRun:
    """Factory function to create a CombatRun from a dictionary.

    Useful for deserializing runs from JSON or database records.

    Args:
        data: Dictionary with run data.

    Returns:
        CombatRun instance.
    """
    content_data = data.get("content", {})
    content = ContentInfo(
        content_type=ContentType(content_data.get("type", "dungeon")),
        name=content_data.get("name", "Unknown"),
        difficulty=Difficulty(content_data.get("difficulty", "normal")),
    )

    metrics_data = data.get("metrics", {})
    metrics = ContributionMetrics(
        damage_dealt=metrics_data.get("damage_dealt", 0.0),
        damage_taken=metrics_data.get("damage_taken", 0.0),
        healing_done=metrics_data.get("healing_done", 0.0),
        buff_uptime=metrics_data.get("buff_uptime", 0.0),
        debuff_uptime=metrics_data.get("debuff_uptime", 0.0),
        mechanic_execution=metrics_data.get("mechanic_execution", 0.0),
        resource_efficiency=metrics_data.get("resource_efficiency", 0.0),
    )

    # Handle both string and RoleType enum
    role_value = data.get("role", "dps")
    if isinstance(role_value, RoleType):
        role = role_value
    else:
        role = RoleType(role_value)

    # Parse timestamp
    timestamp = data.get("timestamp")
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)
    elif timestamp is None:
        timestamp = datetime.now()

    return CombatRun(
        run_id=data.get("run_id", ""),
        player_id=data.get("player_id", ""),
        character_name=data.get("character_name", "Unknown"),
        timestamp=timestamp,
        content=content,
        duration_sec=data.get("duration_sec", 0),
        success=data.get("success", True),
        group_size=data.get("group_size", 4),
        cp_level=data.get("cp_level", 160),
        role=role,
        metrics=metrics,
        build_snapshot=data.get("build_snapshot", {}),
    )


# Convenience function for quick percentile calculation
def calculate_player_percentile(
    run: CombatRun,
    population: list[CombatRun],
    criteria: Optional[SimilarityCriteria] = None,
) -> PercentileResult:
    """Convenience function for one-off percentile calculation.

    Creates a temporary PercentileCalculator and calculates percentiles.
    For batch processing, create a PercentileCalculator instance and reuse it.

    Args:
        run: The run to calculate percentiles for.
        population: All available runs for comparison.
        criteria: Optional similarity criteria.

    Returns:
        PercentileResult with percentiles and metadata.
    """
    calculator = PercentileCalculator(default_criteria=criteria)
    return calculator.calculate_percentile(run, population, criteria)


if __name__ == "__main__":
    # Example usage and basic testing
    import uuid

    # Create sample data
    sample_content = ContentInfo(
        content_type=ContentType.DUNGEON,
        name="Lair of Maarselok",
        difficulty=Difficulty.VETERAN,
    )

    def create_sample_run(
        dps_value: float,
        role: RoleType = RoleType.DPS,
    ) -> CombatRun:
        """Create a sample run for testing."""
        return CombatRun(
            run_id=str(uuid.uuid4()),
            player_id="player_001",
            character_name="TestCharacter",
            timestamp=datetime.now(),
            content=sample_content,
            duration_sec=1200,
            success=True,
            group_size=4,
            cp_level=1800,
            role=role,
            metrics=ContributionMetrics(
                damage_dealt=dps_value,
                damage_taken=0.3,
                healing_done=0.1,
                buff_uptime=0.85,
                debuff_uptime=0.7,
                mechanic_execution=0.9,
                resource_efficiency=0.75,
            ),
        )

    # Create population with varying DPS values
    population = [create_sample_run(dps / 100) for dps in range(20, 100)]

    # Create player run at 75th percentile DPS
    player_run = create_sample_run(0.75)

    # Calculate percentiles
    calculator = PercentileCalculator()
    result = calculator.calculate_percentile(player_run, population)

    print("=" * 60)
    print("ESO Build Optimizer - Percentile Calculation Example")
    print("=" * 60)
    print(f"\nPlayer: {player_run.character_name}")
    print(f"Content: {player_run.content.name} ({player_run.content.difficulty.value})")
    print(f"Role: {player_run.role.value}")
    print(f"\nSample Size: {result.sample_size}")
    print(f"Confidence: {result.confidence:.1%}")
    print("\nPercentiles by Category:")
    for category, percentile in result.percentiles.items():
        print(f"  {category}: {percentile:.1%}")
    print(f"\nWeighted Overall: {result.weighted_overall:.1%}")
    print("\n" + "=" * 60)
