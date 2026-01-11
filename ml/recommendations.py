"""
ESO Build Optimizer - Recommendation Engine

This module generates actionable recommendations based on percentile analysis
and build comparison. It analyzes player performance, compares against top
performers, and generates prioritized suggestions for improvement.

Key Features:
- Analyze weakest contribution categories
- Compare builds to top performers in same content
- Generate gear, skill, and execution recommendations
- Rank recommendations by expected impact
- Provide reasoning with confidence scores

Recommendation Types:
1. Gear swaps - "Switch set X for set Y"
2. Skill usage - "Use skill A more often"
3. Execution - "Your buff uptime is low"
4. Build changes - Wholesale build suggestions
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional


class RecommendationCategory(Enum):
    """Categories of recommendations that can be generated."""
    GEAR = "gear"
    SKILL = "skill"
    EXECUTION = "execution"
    BUILD = "build"


class ContributionMetric(Enum):
    """Contribution metrics used for percentile calculation."""
    DAMAGE_DEALT = "damage_dealt"
    DAMAGE_TAKEN = "damage_taken"
    HEALING_DONE = "healing_done"
    BUFF_UPTIME = "buff_uptime"
    DEBUFF_UPTIME = "debuff_uptime"
    MECHANIC_EXECUTION = "mechanic_execution"
    RESOURCE_EFFICIENCY = "resource_efficiency"


class SetType(Enum):
    """Types of gear sets in ESO."""
    MONSTER = "Monster"
    DUNGEON = "Dungeon"
    TRIAL = "Trial"
    OVERLAND = "Overland"
    CRAFTABLE = "Craftable"
    MYTHIC = "Mythic"
    ARENA = "Arena"
    PVP = "PvP"


@dataclass
class ContentInfo:
    """Information about the content being run."""
    content_type: str  # dungeon, trial, arena, overworld, pvp
    name: str
    difficulty: str  # normal, veteran, hardmode

    def matches(self, other: ContentInfo) -> bool:
        """Check if two content infos match for comparison purposes."""
        return (
            self.content_type == other.content_type
            and self.name == other.name
            and self.difficulty == other.difficulty
        )


@dataclass
class BuildSnapshot:
    """Snapshot of a player's build at time of combat run."""
    player_class: str
    subclass: Optional[str]
    race: str
    cp_level: int
    sets: list[str]
    skills_front: list[str]
    skills_back: list[str]
    champion_points: dict[str, Any] = field(default_factory=dict)
    mundus: Optional[str] = None
    food_buff: Optional[str] = None

    def get_all_skills(self) -> set[str]:
        """Return all equipped skills as a set."""
        return set(self.skills_front + self.skills_back)

    def get_all_sets(self) -> set[str]:
        """Return all equipped sets as a set."""
        return set(self.sets)


@dataclass
class CombatMetrics:
    """Metrics from a combat encounter."""
    damage_done: int = 0
    dps: float = 0.0
    crit_rate: float = 0.0
    healing_done: int = 0
    hps: float = 0.0
    overhealing: int = 0
    damage_taken: int = 0
    damage_blocked: int = 0
    damage_mitigated: int = 0
    buff_uptime: dict[str, float] = field(default_factory=dict)
    debuff_uptime: dict[str, float] = field(default_factory=dict)
    dot_uptime: dict[str, float] = field(default_factory=dict)
    interrupts: int = 0
    synergies_used: int = 0
    synergies_provided: int = 0
    deaths: int = 0
    time_dead: float = 0.0
    magicka_spent: int = 0
    stamina_spent: int = 0
    ultimate_spent: int = 0
    potion_uses: int = 0


@dataclass
class ContributionScores:
    """Normalized contribution scores (0.0 to 1.0)."""
    damage_dealt: float = 0.0
    damage_taken: float = 0.0  # Inverted for non-tanks
    healing_done: float = 0.0
    buff_uptime: float = 0.0
    debuff_uptime: float = 0.0
    mechanic_execution: float = 0.0
    resource_efficiency: float = 0.0

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            ContributionMetric.DAMAGE_DEALT.value: self.damage_dealt,
            ContributionMetric.DAMAGE_TAKEN.value: self.damage_taken,
            ContributionMetric.HEALING_DONE.value: self.healing_done,
            ContributionMetric.BUFF_UPTIME.value: self.buff_uptime,
            ContributionMetric.DEBUFF_UPTIME.value: self.debuff_uptime,
            ContributionMetric.MECHANIC_EXECUTION.value: self.mechanic_execution,
            ContributionMetric.RESOURCE_EFFICIENCY.value: self.resource_efficiency,
        }


@dataclass
class CombatRun:
    """Complete data for a combat run."""
    run_id: str
    player_id: str
    character_name: str
    timestamp: datetime
    content: ContentInfo
    duration_sec: int
    success: bool
    group_size: int
    build_snapshot: BuildSnapshot
    metrics: CombatMetrics
    contribution_scores: ContributionScores

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CombatRun:
        """Create a CombatRun from a dictionary."""
        return cls(
            run_id=data.get("run_id", str(uuid.uuid4())),
            player_id=data["player_id"],
            character_name=data["character_name"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            content=ContentInfo(**data["content"]),
            duration_sec=data["duration_sec"],
            success=data["success"],
            group_size=data["group_size"],
            build_snapshot=BuildSnapshot(
                player_class=data["build_snapshot"]["class"],
                subclass=data["build_snapshot"].get("subclass"),
                race=data["build_snapshot"]["race"],
                cp_level=data["build_snapshot"]["cp_level"],
                sets=data["build_snapshot"]["sets"],
                skills_front=data["build_snapshot"]["skills_front"],
                skills_back=data["build_snapshot"]["skills_back"],
                champion_points=data["build_snapshot"].get("champion_points", {}),
            ),
            metrics=CombatMetrics(**data.get("metrics", {})),
            contribution_scores=ContributionScores(**data.get("contribution_scores", {})),
        )


@dataclass
class PercentileResult:
    """Result of percentile calculation for a single metric."""
    metric: str
    percentile: float
    sample_size: int
    confidence: str  # low, medium, high

    @property
    def is_below_median(self) -> bool:
        """Check if this percentile is below the 50th percentile."""
        return self.percentile < 0.5


@dataclass
class PercentileResults:
    """Complete percentile results for a run."""
    run_id: str
    percentiles: dict[str, PercentileResult]
    overall_confidence: str
    sample_size: int

    def get_weakest_categories(self, count: int = 3) -> list[PercentileResult]:
        """
        Get the weakest contribution categories.

        Args:
            count: Number of weakest categories to return

        Returns:
            List of PercentileResult sorted by percentile (lowest first)
        """
        sorted_results = sorted(
            self.percentiles.values(),
            key=lambda x: x.percentile
        )
        return sorted_results[:count]

    def get_below_median(self) -> list[PercentileResult]:
        """Get all categories below the 50th percentile."""
        return [r for r in self.percentiles.values() if r.is_below_median]


@dataclass
class Recommendation:
    """A single recommendation for improvement."""
    recommendation_id: str
    run_id: str
    category: RecommendationCategory
    priority: int
    current_state: str
    recommended_change: str
    expected_improvement: str
    reasoning: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary matching the output schema."""
        return {
            "recommendation_id": self.recommendation_id,
            "run_id": self.run_id,
            "category": self.category.value,
            "priority": self.priority,
            "current_state": self.current_state,
            "recommended_change": self.recommended_change,
            "expected_improvement": self.expected_improvement,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
        }


@dataclass
class BuildDiff:
    """Differences between two builds."""
    gear_differences: list[tuple[str, str]]  # (player_set, top_performer_set)
    skill_differences: list[tuple[str, str]]  # (player_skill, top_performer_skill)
    missing_skills: list[str]  # Skills top performers use that player doesn't
    extra_skills: list[str]  # Skills player uses that top performers don't
    missing_sets: list[str]  # Sets top performers use that player doesn't
    extra_sets: list[str]  # Sets player uses that top performers don't


@dataclass
class UserPreferences:
    """User preferences for recommendation filtering."""
    exclude_pvp_sets: bool = True
    exclude_trial_sets: bool = False
    exclude_mythics: bool = False
    preferred_weight: Optional[str] = None  # Light, Medium, Heavy
    max_difficulty_to_obtain: str = "veteran"  # normal, veteran, hardmode
    include_craftable: bool = True
    budget_conscious: bool = False  # Prefer cheaper/easier to obtain

    def is_set_allowed(self, set_data: dict[str, Any]) -> bool:
        """Check if a set is allowed based on user preferences."""
        set_type = set_data.get("set_type", "")

        if self.exclude_pvp_sets and set_type == "PvP":
            return False
        if self.exclude_trial_sets and set_type == "Trial":
            return False
        if self.exclude_mythics and set_type == "Mythic":
            return False
        if self.preferred_weight and set_data.get("weight") != self.preferred_weight:
            # Only filter if weight matters for this set type
            if set_type not in ["Mythic", "Arena"]:
                return False

        return True


class FeatureDatabase:
    """
    Database for looking up skills, sets, and other game features.

    This class provides efficient lookup of game data for generating
    recommendations.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the feature database.

        Args:
            data_dir: Directory containing JSON data files.
                     Defaults to data/raw/ relative to project root.
        """
        if data_dir is None:
            # Default to project's data/raw directory
            data_dir = Path(__file__).parent.parent / "data" / "raw"

        self.data_dir = data_dir
        self._skills_cache: dict[str, dict] = {}
        self._sets_cache: dict[str, dict] = {}
        self._loaded = False

    def _load_data(self) -> None:
        """Load all data files into cache."""
        if self._loaded:
            return

        # Load skill files
        skill_patterns = ["phase01_*.json", "phase02_*.json", "phase03_*.json",
                         "phase04_*.json", "phase05_*.json", "phase06_*.json",
                         "phase07_*.json", "phase08_*.json", "phase09_*.json"]

        for pattern in skill_patterns:
            for file_path in self.data_dir.glob(pattern):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for item in data:
                            if "feature_id" in item:
                                self._skills_cache[item["feature_id"]] = item
                                # Also index by name for convenience if present
                                if "name" in item:
                                    self._skills_cache[item["name"]] = item
                except (json.JSONDecodeError, IOError, KeyError):
                    continue

        # Load set files
        for file_path in self.data_dir.glob("sets_*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        if "set_id" in item:
                            self._sets_cache[item["set_id"]] = item
                            # Also index by name if present
                            if "name" in item:
                                self._sets_cache[item["name"]] = item
            except (json.JSONDecodeError, IOError, KeyError):
                continue

        self._loaded = True

    def get_skill(self, skill_id_or_name: str) -> Optional[dict[str, Any]]:
        """
        Look up a skill by ID or name.

        Args:
            skill_id_or_name: The skill's feature_id or name

        Returns:
            Skill data dictionary or None if not found
        """
        self._load_data()
        return self._skills_cache.get(skill_id_or_name)

    def get_set(self, set_id_or_name: str) -> Optional[dict[str, Any]]:
        """
        Look up a gear set by ID or name.

        Args:
            set_id_or_name: The set's set_id or name

        Returns:
            Set data dictionary or None if not found
        """
        self._load_data()
        return self._sets_cache.get(set_id_or_name)

    def get_sets_by_type(self, set_type: SetType) -> list[dict[str, Any]]:
        """
        Get all sets of a specific type.

        Args:
            set_type: The type of sets to retrieve

        Returns:
            List of set data dictionaries
        """
        self._load_data()
        return [
            s for s in self._sets_cache.values()
            if s.get("set_type") == set_type.value and "set_id" in s
        ]

    def get_sets_for_role(
        self,
        role_affinity: str,
        min_affinity: float = 0.5
    ) -> list[dict[str, Any]]:
        """
        Get sets that are good for a specific role.

        Args:
            role_affinity: The role affinity key (e.g., "damage_dealt")
            min_affinity: Minimum affinity score (0.0-1.0)

        Returns:
            List of set data dictionaries sorted by affinity
        """
        self._load_data()
        matching_sets = []

        for set_data in self._sets_cache.values():
            if "set_id" not in set_data:
                continue
            affinity = set_data.get("role_affinity", {}).get(role_affinity, 0)
            if affinity >= min_affinity:
                matching_sets.append((set_data, affinity))

        # Sort by affinity descending
        matching_sets.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in matching_sets]

    def get_top_tier_sets(self, tier: str = "S") -> list[dict[str, Any]]:
        """
        Get all sets of a specific PvE tier.

        Args:
            tier: The PvE tier (S, A, B, C, F)

        Returns:
            List of set data dictionaries
        """
        self._load_data()
        return [
            s for s in self._sets_cache.values()
            if s.get("pve_tier") == tier and "set_id" in s
        ]

    def get_skill_by_buff(self, buff_name: str) -> list[dict[str, Any]]:
        """
        Find skills that grant a specific buff.

        Args:
            buff_name: Name of the buff (e.g., "Major Brutality")

        Returns:
            List of skill data dictionaries
        """
        self._load_data()
        matching = []

        for skill in self._skills_cache.values():
            if "feature_id" not in skill:
                continue
            buffs = skill.get("buff_debuff_granted", "") or ""
            if buff_name.lower() in buffs.lower():
                matching.append(skill)

        return matching


class RecommendationEngine:
    """
    Engine for generating actionable recommendations based on combat analysis.

    This class analyzes player performance, compares against top performers,
    and generates prioritized recommendations for improvement.

    Example usage:
        >>> engine = RecommendationEngine()
        >>> run = CombatRun.from_dict(run_data)
        >>> percentiles = engine.calculate_percentiles(run, comparison_pool)
        >>> recommendations = engine.generate_recommendations(run, percentiles)
        >>> for rec in recommendations:
        ...     print(f"{rec.priority}: {rec.recommended_change}")
    """

    # Metric-specific improvement multipliers
    IMPROVEMENT_MULTIPLIERS = {
        ContributionMetric.DAMAGE_DEALT.value: 1.0,
        ContributionMetric.HEALING_DONE.value: 0.8,
        ContributionMetric.BUFF_UPTIME.value: 0.6,
        ContributionMetric.DEBUFF_UPTIME.value: 0.5,
        ContributionMetric.MECHANIC_EXECUTION.value: 0.7,
        ContributionMetric.RESOURCE_EFFICIENCY.value: 0.4,
        ContributionMetric.DAMAGE_TAKEN.value: 0.3,
    }

    # Minimum sample size for confident recommendations
    MIN_SAMPLE_SIZE = 30

    # CP range for similar players
    CP_RANGE = 200

    def __init__(
        self,
        feature_db: Optional[FeatureDatabase] = None,
        run_database: Optional[list[CombatRun]] = None
    ):
        """
        Initialize the recommendation engine.

        Args:
            feature_db: Database for skill/set lookups. Created if not provided.
            run_database: Database of historical combat runs for comparison.
        """
        self.feature_db = feature_db or FeatureDatabase()
        self.run_database = run_database or []
        self._top_performer_cache: dict[str, list[CombatRun]] = {}

    def add_runs(self, runs: list[CombatRun]) -> None:
        """
        Add combat runs to the database.

        Args:
            runs: List of combat runs to add
        """
        self.run_database.extend(runs)
        # Invalidate cache
        self._top_performer_cache.clear()

    def _get_similar_runs(
        self,
        run: CombatRun,
        cp_range: int = CP_RANGE
    ) -> list[CombatRun]:
        """
        Get runs similar to the given run for comparison.

        Similarity criteria:
        - Same content (name + difficulty)
        - Similar group size
        - Within CP range

        Args:
            run: The run to find similar runs for
            cp_range: Maximum CP difference for similarity

        Returns:
            List of similar combat runs
        """
        similar = []

        for other in self.run_database:
            if other.run_id == run.run_id:
                continue

            # Must be same content
            if not run.content.matches(other.content):
                continue

            # Must be similar group size (within 1)
            if abs(run.group_size - other.group_size) > 1:
                continue

            # Must be within CP range
            if abs(run.build_snapshot.cp_level - other.build_snapshot.cp_level) > cp_range:
                continue

            similar.append(other)

        return similar

    def _get_top_performers(
        self,
        content: ContentInfo,
        metric: str,
        top_percent: float = 0.1
    ) -> list[CombatRun]:
        """
        Get top performers for a specific content and metric.

        Args:
            content: The content to filter by
            metric: The metric to rank by
            top_percent: Top percentage to consider (0.1 = top 10%)

        Returns:
            List of top performing runs
        """
        cache_key = f"{content.name}:{content.difficulty}:{metric}"

        if cache_key in self._top_performer_cache:
            return self._top_performer_cache[cache_key]

        # Filter to matching content
        matching_runs = [
            r for r in self.run_database
            if r.content.matches(content) and r.success
        ]

        if not matching_runs:
            return []

        # Sort by the specified metric
        def get_metric_value(run: CombatRun) -> float:
            scores = run.contribution_scores.to_dict()
            return scores.get(metric, 0.0)

        sorted_runs = sorted(matching_runs, key=get_metric_value, reverse=True)

        # Take top percentage
        top_count = max(1, int(len(sorted_runs) * top_percent))
        top_runs = sorted_runs[:top_count]

        self._top_performer_cache[cache_key] = top_runs
        return top_runs

    def calculate_percentiles(
        self,
        run: CombatRun,
        comparison_pool: Optional[list[CombatRun]] = None
    ) -> PercentileResults:
        """
        Calculate percentiles for a run against similar runs.

        Args:
            run: The combat run to analyze
            comparison_pool: Optional specific pool to compare against.
                           Uses database if not provided.

        Returns:
            PercentileResults containing percentile for each metric
        """
        import bisect

        if comparison_pool is None:
            comparison_pool = self._get_similar_runs(run)

        sample_size = len(comparison_pool)

        # Determine confidence based on sample size
        if sample_size < 10:
            overall_confidence = "low"
        elif sample_size < 50:
            overall_confidence = "medium"
        else:
            overall_confidence = "high"

        percentiles: dict[str, PercentileResult] = {}
        player_scores = run.contribution_scores.to_dict()

        for metric in ContributionMetric:
            metric_name = metric.value
            player_value = player_scores.get(metric_name, 0.0)

            # Get sorted values from comparison pool
            pool_values = sorted([
                r.contribution_scores.to_dict().get(metric_name, 0.0)
                for r in comparison_pool
            ])

            if pool_values:
                # Calculate percentile using bisect
                position = bisect.bisect_left(pool_values, player_value)
                percentile = position / len(pool_values)
            else:
                percentile = 0.5  # Default to median if no data

            # Individual metric confidence
            if sample_size < 10:
                confidence = "low"
            elif sample_size < 30:
                confidence = "medium"
            else:
                confidence = "high"

            percentiles[metric_name] = PercentileResult(
                metric=metric_name,
                percentile=percentile,
                sample_size=sample_size,
                confidence=confidence,
            )

        return PercentileResults(
            run_id=run.run_id,
            percentiles=percentiles,
            overall_confidence=overall_confidence,
            sample_size=sample_size,
        )

    def diff_builds(
        self,
        player_build: BuildSnapshot,
        top_performers: list[CombatRun]
    ) -> BuildDiff:
        """
        Compare a player's build against top performers.

        Args:
            player_build: The player's current build
            top_performers: List of top performing runs to compare against

        Returns:
            BuildDiff containing differences between builds
        """
        if not top_performers:
            return BuildDiff(
                gear_differences=[],
                skill_differences=[],
                missing_skills=[],
                extra_skills=[],
                missing_sets=[],
                extra_sets=[],
            )

        # Aggregate sets and skills from top performers
        top_sets: dict[str, int] = {}
        top_skills: dict[str, int] = {}

        for run in top_performers:
            for gear_set in run.build_snapshot.get_all_sets():
                top_sets[gear_set] = top_sets.get(gear_set, 0) + 1
            for skill in run.build_snapshot.get_all_skills():
                top_skills[skill] = top_skills.get(skill, 0) + 1

        # Calculate prevalence threshold (used by at least 30% of top performers)
        threshold = len(top_performers) * 0.3

        player_sets = player_build.get_all_sets()
        player_skills = player_build.get_all_skills()

        # Find common top performer sets that player is missing
        missing_sets = [
            s for s, count in top_sets.items()
            if count >= threshold and s not in player_sets
        ]

        # Find player sets not used by top performers
        extra_sets = [
            s for s in player_sets
            if top_sets.get(s, 0) < threshold
        ]

        # Find common top performer skills that player is missing
        missing_skills = [
            s for s, count in top_skills.items()
            if count >= threshold and s not in player_skills
        ]

        # Find player skills not used by top performers
        extra_skills = [
            s for s in player_skills
            if top_skills.get(s, 0) < threshold
        ]

        # Generate gear differences (pairs of swaps)
        gear_differences = list(zip(
            sorted(extra_sets)[:len(missing_sets)],
            sorted(missing_sets, key=lambda x: top_sets.get(x, 0), reverse=True)
        ))

        # Generate skill differences
        skill_differences = list(zip(
            sorted(extra_skills)[:len(missing_skills)],
            sorted(missing_skills, key=lambda x: top_skills.get(x, 0), reverse=True)
        ))

        return BuildDiff(
            gear_differences=gear_differences,
            skill_differences=skill_differences,
            missing_skills=missing_skills,
            extra_skills=extra_skills,
            missing_sets=missing_sets,
            extra_sets=extra_sets,
        )

    def estimate_improvement(
        self,
        current_percentile: float,
        metric: str,
        change_type: RecommendationCategory,
        sample_size: int
    ) -> tuple[str, float]:
        """
        Estimate the expected improvement from a recommendation.

        Args:
            current_percentile: Current percentile for the metric
            metric: The metric being improved
            change_type: Type of change being recommended
            sample_size: Size of comparison sample

        Returns:
            Tuple of (improvement description, confidence score)
        """
        # Base improvement estimate (higher for lower percentiles)
        percentile_gap = 0.5 - current_percentile if current_percentile < 0.5 else 0

        # Improvement multiplier based on change type
        type_multipliers = {
            RecommendationCategory.GEAR: 0.08,  # Gear changes have big impact
            RecommendationCategory.SKILL: 0.05,  # Skill changes are medium
            RecommendationCategory.EXECUTION: 0.12,  # Execution has highest potential
            RecommendationCategory.BUILD: 0.15,  # Full build changes are major
        }

        # Metric-specific multiplier
        metric_mult = self.IMPROVEMENT_MULTIPLIERS.get(metric, 0.5)

        # Calculate estimated improvement percentage
        type_mult = type_multipliers.get(change_type, 0.05)
        improvement_pct = (percentile_gap * 100 * type_mult * metric_mult) + (type_mult * 100)

        # Round to reasonable precision
        improvement_pct = round(improvement_pct, 1)

        # Calculate confidence based on sample size and percentile gap
        if sample_size >= 50:
            base_confidence = 0.9
        elif sample_size >= 30:
            base_confidence = 0.75
        elif sample_size >= 10:
            base_confidence = 0.6
        else:
            base_confidence = 0.4

        # Adjust confidence based on percentile gap (more confident for larger gaps)
        confidence = base_confidence * (0.5 + min(percentile_gap, 0.5))
        confidence = min(0.95, max(0.3, confidence))

        # Format improvement string based on metric
        if metric == ContributionMetric.DAMAGE_DEALT.value:
            improvement_str = f"+{improvement_pct}% DPS based on similar players"
        elif metric == ContributionMetric.HEALING_DONE.value:
            improvement_str = f"+{improvement_pct}% HPS based on similar players"
        elif metric == ContributionMetric.BUFF_UPTIME.value:
            improvement_str = f"+{improvement_pct}% buff contribution"
        elif metric == ContributionMetric.DEBUFF_UPTIME.value:
            improvement_str = f"+{improvement_pct}% debuff uptime improvement"
        elif metric == ContributionMetric.MECHANIC_EXECUTION.value:
            improvement_str = f"+{improvement_pct}% mechanic execution score"
        elif metric == ContributionMetric.RESOURCE_EFFICIENCY.value:
            improvement_str = f"+{improvement_pct}% resource efficiency"
        else:
            improvement_str = f"+{improvement_pct}% improvement expected"

        return improvement_str, round(confidence, 2)

    def _generate_gear_recommendations(
        self,
        run: CombatRun,
        percentiles: PercentileResults,
        build_diff: BuildDiff,
        user_prefs: UserPreferences
    ) -> list[Recommendation]:
        """Generate gear-related recommendations."""
        recommendations = []
        weakest = percentiles.get_weakest_categories(3)

        for idx, (player_set, recommended_set) in enumerate(build_diff.gear_differences):
            # Check if set is allowed by user preferences
            set_data = self.feature_db.get_set(recommended_set)
            if set_data and not user_prefs.is_set_allowed(set_data):
                continue

            # Find which weak metric this addresses
            target_metric = None
            for weak in weakest:
                if set_data:
                    affinity = set_data.get("role_affinity", {}).get(weak.metric, 0)
                    if affinity > 0.5:
                        target_metric = weak
                        break

            if target_metric is None and weakest:
                target_metric = weakest[0]

            improvement_str, confidence = self.estimate_improvement(
                target_metric.percentile if target_metric else 0.5,
                target_metric.metric if target_metric else "damage_dealt",
                RecommendationCategory.GEAR,
                percentiles.sample_size,
            )

            # Generate reasoning
            if set_data:
                set_type = set_data.get("set_type", "Unknown")
                tier = set_data.get("pve_tier", "?")
                location = set_data.get("location", "Unknown location")
                reasoning = (
                    f"{recommended_set} is a {tier}-tier {set_type} set from {location}. "
                    f"Top performers in this content commonly use it for improved "
                    f"{target_metric.metric.replace('_', ' ') if target_metric else 'performance'}."
                )
            else:
                reasoning = f"Top performers commonly use {recommended_set} in this content."

            rec = Recommendation(
                recommendation_id=str(uuid.uuid4()),
                run_id=run.run_id,
                category=RecommendationCategory.GEAR,
                priority=idx + 1,
                current_state=f"Using {player_set}",
                recommended_change=f"Switch to {recommended_set}",
                expected_improvement=improvement_str,
                reasoning=reasoning,
                confidence=confidence,
            )
            recommendations.append(rec)

        # Also recommend missing sets if we have room
        for missing_set in build_diff.missing_sets:
            if any(r.recommended_change.endswith(missing_set) for r in recommendations):
                continue  # Already recommended

            set_data = self.feature_db.get_set(missing_set)
            if set_data and not user_prefs.is_set_allowed(set_data):
                continue

            if len(recommendations) >= 3:
                break

            improvement_str, confidence = self.estimate_improvement(
                weakest[0].percentile if weakest else 0.5,
                weakest[0].metric if weakest else "damage_dealt",
                RecommendationCategory.GEAR,
                percentiles.sample_size,
            )

            rec = Recommendation(
                recommendation_id=str(uuid.uuid4()),
                run_id=run.run_id,
                category=RecommendationCategory.GEAR,
                priority=len(recommendations) + 1,
                current_state="Current gear setup",
                recommended_change=f"Consider adding {missing_set} to your build",
                expected_improvement=improvement_str,
                reasoning=f"Many top performers use {missing_set} for this content.",
                confidence=confidence * 0.8,  # Lower confidence for generic recs
            )
            recommendations.append(rec)

        return recommendations

    def _generate_skill_recommendations(
        self,
        run: CombatRun,
        percentiles: PercentileResults,
        build_diff: BuildDiff
    ) -> list[Recommendation]:
        """Generate skill-related recommendations."""
        recommendations = []
        weakest = percentiles.get_weakest_categories(3)

        # Skill swap recommendations
        for idx, (player_skill, recommended_skill) in enumerate(build_diff.skill_differences):
            skill_data = self.feature_db.get_skill(recommended_skill)

            # Find relevant weak metric
            target_metric = weakest[0] if weakest else None

            improvement_str, confidence = self.estimate_improvement(
                target_metric.percentile if target_metric else 0.5,
                target_metric.metric if target_metric else "damage_dealt",
                RecommendationCategory.SKILL,
                percentiles.sample_size,
            )

            # Build reasoning
            if skill_data:
                buffs = skill_data.get("buff_debuff_granted", "")
                tags = skill_data.get("tags", "")
                reasoning_parts = []

                if buffs:
                    reasoning_parts.append(f"grants {buffs}")
                if "execute" in tags.lower():
                    reasoning_parts.append("provides execute damage")
                if "sustain" in tags.lower():
                    reasoning_parts.append("improves resource sustain")
                if "aoe" in tags.lower():
                    reasoning_parts.append("adds AoE capability")

                if reasoning_parts:
                    reasoning = f"{recommended_skill} {', '.join(reasoning_parts)}."
                else:
                    reasoning = f"Top performers commonly use {recommended_skill}."
            else:
                reasoning = f"Top performers commonly use {recommended_skill}."

            rec = Recommendation(
                recommendation_id=str(uuid.uuid4()),
                run_id=run.run_id,
                category=RecommendationCategory.SKILL,
                priority=idx + 1,
                current_state=f"Using {player_skill}",
                recommended_change=f"Consider {recommended_skill} instead",
                expected_improvement=improvement_str,
                reasoning=reasoning,
                confidence=confidence,
            )
            recommendations.append(rec)

            if len(recommendations) >= 3:
                break

        return recommendations

    def _generate_execution_recommendations(
        self,
        run: CombatRun,
        percentiles: PercentileResults
    ) -> list[Recommendation]:
        """Generate execution-related recommendations."""
        recommendations = []
        metrics = run.metrics

        # Check buff uptime
        for buff_name, uptime in metrics.buff_uptime.items():
            if uptime < 0.8:  # Less than 80% uptime
                improvement_str, confidence = self.estimate_improvement(
                    uptime,
                    ContributionMetric.BUFF_UPTIME.value,
                    RecommendationCategory.EXECUTION,
                    percentiles.sample_size,
                )

                rec = Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    run_id=run.run_id,
                    category=RecommendationCategory.EXECUTION,
                    priority=len(recommendations) + 1,
                    current_state=f"{buff_name} uptime is {uptime*100:.1f}%",
                    recommended_change=f"Improve {buff_name} uptime to 90%+",
                    expected_improvement=improvement_str,
                    reasoning=(
                        f"Your {buff_name} uptime of {uptime*100:.1f}% is below optimal. "
                        f"Maintain this buff more consistently for better performance."
                    ),
                    confidence=confidence,
                )
                recommendations.append(rec)

        # Check DoT uptime
        for dot_name, uptime in metrics.dot_uptime.items():
            if uptime < 0.85:  # Less than 85% uptime for DoTs
                improvement_str, confidence = self.estimate_improvement(
                    uptime,
                    ContributionMetric.DAMAGE_DEALT.value,
                    RecommendationCategory.EXECUTION,
                    percentiles.sample_size,
                )

                rec = Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    run_id=run.run_id,
                    category=RecommendationCategory.EXECUTION,
                    priority=len(recommendations) + 1,
                    current_state=f"{dot_name} uptime is {uptime*100:.1f}%",
                    recommended_change=f"Keep {dot_name} active more consistently",
                    expected_improvement=improvement_str,
                    reasoning=(
                        f"Your {dot_name} had only {uptime*100:.1f}% uptime. "
                        f"Maintaining DoTs is crucial for sustained damage output."
                    ),
                    confidence=confidence,
                )
                recommendations.append(rec)

        # Check deaths
        if metrics.deaths > 0:
            death_penalty = metrics.time_dead / run.duration_sec if run.duration_sec > 0 else 0

            rec = Recommendation(
                recommendation_id=str(uuid.uuid4()),
                run_id=run.run_id,
                category=RecommendationCategory.EXECUTION,
                priority=1,  # Deaths are high priority
                current_state=f"Died {metrics.deaths} time(s), {metrics.time_dead:.0f}s dead",
                recommended_change="Focus on survival mechanics",
                expected_improvement=f"+{death_penalty*100:.1f}% uptime by avoiding deaths",
                reasoning=(
                    f"You spent {metrics.time_dead:.0f} seconds dead ({death_penalty*100:.1f}% of the fight). "
                    f"Dead players deal no damage - survival is the top priority."
                ),
                confidence=0.95,  # Very confident about death recommendations
            )
            recommendations.insert(0, rec)  # Put at front

        # Check overhealing (for healers)
        if metrics.healing_done > 0 and metrics.overhealing > 0:
            overheal_pct = metrics.overhealing / (metrics.healing_done + metrics.overhealing)
            if overheal_pct > 0.3:  # More than 30% overhealing
                rec = Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    run_id=run.run_id,
                    category=RecommendationCategory.EXECUTION,
                    priority=len(recommendations) + 1,
                    current_state=f"Overhealing at {overheal_pct*100:.1f}%",
                    recommended_change="Reduce overhealing by timing heals better",
                    expected_improvement="Better resource efficiency and damage contribution",
                    reasoning=(
                        f"You overhealed by {overheal_pct*100:.1f}%. Consider weaving in "
                        f"damage skills when the group is healthy."
                    ),
                    confidence=0.7,
                )
                recommendations.append(rec)

        return recommendations[:5]  # Limit to 5 execution recommendations

    def _generate_build_recommendations(
        self,
        run: CombatRun,
        percentiles: PercentileResults,
        top_performers: list[CombatRun]
    ) -> list[Recommendation]:
        """Generate wholesale build change recommendations."""
        recommendations = []

        # Only suggest build overhauls for very low performers
        weakest = percentiles.get_weakest_categories(3)
        avg_percentile = sum(w.percentile for w in weakest) / len(weakest) if weakest else 0.5

        if avg_percentile > 0.3:
            return []  # Don't suggest build overhaul unless really struggling

        # Find most common build archetype among top performers
        if not top_performers:
            return []

        # Analyze build patterns
        class_counts: dict[str, int] = {}
        subclass_counts: dict[str, int] = {}

        for perf in top_performers:
            pc = perf.build_snapshot.player_class
            class_counts[pc] = class_counts.get(pc, 0) + 1
            if perf.build_snapshot.subclass:
                subclass_counts[perf.build_snapshot.subclass] = (
                    subclass_counts.get(perf.build_snapshot.subclass, 0) + 1
                )

        # Get most common class/subclass combo
        if class_counts:
            top_class = max(class_counts, key=class_counts.get)
            top_subclass = max(subclass_counts, key=subclass_counts.get) if subclass_counts else None

            current_class = run.build_snapshot.player_class
            current_subclass = run.build_snapshot.subclass

            # Only recommend if significantly different
            if top_class != current_class or top_subclass != current_subclass:
                class_usage = class_counts.get(top_class, 0) / len(top_performers)

                if class_usage > 0.4:  # At least 40% of top performers use this
                    improvement_str, confidence = self.estimate_improvement(
                        avg_percentile,
                        weakest[0].metric if weakest else "damage_dealt",
                        RecommendationCategory.BUILD,
                        percentiles.sample_size,
                    )

                    build_suggestion = top_class
                    if top_subclass:
                        build_suggestion += f" with {top_subclass} subclass"

                    rec = Recommendation(
                        recommendation_id=str(uuid.uuid4()),
                        run_id=run.run_id,
                        category=RecommendationCategory.BUILD,
                        priority=1,
                        current_state=f"Playing {current_class}" + (
                            f" with {current_subclass}" if current_subclass else ""
                        ),
                        recommended_change=f"Consider {build_suggestion} for this content",
                        expected_improvement=improvement_str,
                        reasoning=(
                            f"{class_usage*100:.0f}% of top performers in this content use {build_suggestion}. "
                            f"This archetype may be better suited for the encounter mechanics."
                        ),
                        confidence=confidence * 0.6,  # Lower confidence for major changes
                    )
                    recommendations.append(rec)

        return recommendations

    def generate_recommendations(
        self,
        run: CombatRun,
        percentiles: PercentileResults,
        user_preferences: Optional[UserPreferences] = None,
        max_recommendations: int = 10
    ) -> list[Recommendation]:
        """
        Generate actionable recommendations for a combat run.

        This is the main entry point for recommendation generation. It analyzes
        the run's performance, compares against top performers, and generates
        prioritized recommendations across multiple categories.

        Algorithm:
        1. Find weakest percentile categories (bottom 3 below median)
        2. Query top performers in same content
        3. Diff their builds against player's build
        4. Generate recommendations with expected improvement estimates

        Args:
            run: The combat run to analyze
            percentiles: Pre-calculated percentile results for the run
            user_preferences: User preferences for filtering recommendations
            max_recommendations: Maximum number of recommendations to return

        Returns:
            List of Recommendation objects sorted by priority

        Example:
            >>> engine = RecommendationEngine()
            >>> run = CombatRun.from_dict(run_data)
            >>> percentiles = engine.calculate_percentiles(run)
            >>> recs = engine.generate_recommendations(run, percentiles)
            >>> print(f"Found {len(recs)} recommendations")
        """
        if user_preferences is None:
            user_preferences = UserPreferences()

        all_recommendations: list[Recommendation] = []

        # Get weakest categories
        weakest = percentiles.get_weakest_categories(3)
        below_median = percentiles.get_below_median()

        # If performing well, fewer recommendations needed
        if len(below_median) == 0:
            return []  # Performing above median in all categories

        # Get top performers for comparison
        primary_metric = weakest[0].metric if weakest else ContributionMetric.DAMAGE_DEALT.value
        top_performers = self._get_top_performers(
            run.content,
            primary_metric,
            top_percent=0.1
        )

        # Calculate build diff
        build_diff = self.diff_builds(run.build_snapshot, top_performers)

        # Generate recommendations by category
        gear_recs = self._generate_gear_recommendations(
            run, percentiles, build_diff, user_preferences
        )
        skill_recs = self._generate_skill_recommendations(
            run, percentiles, build_diff
        )
        execution_recs = self._generate_execution_recommendations(
            run, percentiles
        )
        build_recs = self._generate_build_recommendations(
            run, percentiles, top_performers
        )

        # Combine and prioritize
        all_recommendations.extend(execution_recs)  # Execution first (often most impactful)
        all_recommendations.extend(gear_recs)
        all_recommendations.extend(skill_recs)
        all_recommendations.extend(build_recs)

        # Sort by confidence * improvement potential
        def recommendation_score(rec: Recommendation) -> float:
            # Extract improvement percentage from string
            import re
            match = re.search(r'\+(\d+\.?\d*)%', rec.expected_improvement)
            improvement = float(match.group(1)) if match else 5.0
            return rec.confidence * improvement

        all_recommendations.sort(key=recommendation_score, reverse=True)

        # Re-assign priorities
        for idx, rec in enumerate(all_recommendations):
            rec.priority = idx + 1

        return all_recommendations[:max_recommendations]

    def generate_recommendations_for_metric(
        self,
        run: CombatRun,
        target_metric: ContributionMetric,
        user_preferences: Optional[UserPreferences] = None
    ) -> list[Recommendation]:
        """
        Generate recommendations specifically targeting a single metric.

        Useful when a player wants to focus on improving one aspect
        of their performance (e.g., just DPS or just buff uptime).

        Args:
            run: The combat run to analyze
            target_metric: The specific metric to optimize for
            user_preferences: User preferences for filtering

        Returns:
            List of recommendations focused on the target metric
        """
        if user_preferences is None:
            user_preferences = UserPreferences()

        recommendations: list[Recommendation] = []

        # Get top performers for this specific metric
        top_performers = self._get_top_performers(
            run.content,
            target_metric.value,
            top_percent=0.05  # Top 5% for focused recommendations
        )

        if not top_performers:
            return []

        build_diff = self.diff_builds(run.build_snapshot, top_performers)

        # Get sets that are good for this metric
        metric_sets = self.feature_db.get_sets_for_role(target_metric.value, min_affinity=0.7)

        # Check if player is missing any high-affinity sets
        player_sets = run.build_snapshot.get_all_sets()

        for set_data in metric_sets[:5]:
            set_name = set_data.get("name", "")
            if set_name not in player_sets and user_preferences.is_set_allowed(set_data):
                tier = set_data.get("pve_tier", "?")
                affinity = set_data.get("role_affinity", {}).get(target_metric.value, 0)

                rec = Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    run_id=run.run_id,
                    category=RecommendationCategory.GEAR,
                    priority=len(recommendations) + 1,
                    current_state="Current gear setup",
                    recommended_change=f"Add {set_name} for {target_metric.value}",
                    expected_improvement=f"+{affinity*10:.0f}% {target_metric.value.replace('_', ' ')}",
                    reasoning=(
                        f"{set_name} is a {tier}-tier set with {affinity*100:.0f}% affinity "
                        f"for {target_metric.value.replace('_', ' ')}."
                    ),
                    confidence=0.7 + (affinity * 0.2),
                )
                recommendations.append(rec)

        # Add skill recommendations based on top performers
        for skill in build_diff.missing_skills[:3]:
            skill_data = self.feature_db.get_skill(skill)
            if skill_data:
                buffs = skill_data.get("buff_debuff_granted", "")
                rec = Recommendation(
                    recommendation_id=str(uuid.uuid4()),
                    run_id=run.run_id,
                    category=RecommendationCategory.SKILL,
                    priority=len(recommendations) + 1,
                    current_state="Current skill setup",
                    recommended_change=f"Use {skill}",
                    expected_improvement=f"Improved {target_metric.value.replace('_', ' ')}",
                    reasoning=(
                        f"Top {target_metric.value.replace('_', ' ')} performers commonly use {skill}"
                        + (f" for {buffs}" if buffs else "") + "."
                    ),
                    confidence=0.65,
                )
                recommendations.append(rec)

        return recommendations[:5]


def create_recommendation_engine(
    data_dir: Optional[Path] = None,
    runs: Optional[list[CombatRun]] = None
) -> RecommendationEngine:
    """
    Factory function to create a configured RecommendationEngine.

    Args:
        data_dir: Directory containing JSON data files
        runs: Initial list of combat runs for the database

    Returns:
        Configured RecommendationEngine instance
    """
    feature_db = FeatureDatabase(data_dir)
    engine = RecommendationEngine(feature_db, runs or [])
    return engine


# Export public API
__all__ = [
    "RecommendationEngine",
    "Recommendation",
    "RecommendationCategory",
    "ContributionMetric",
    "CombatRun",
    "CombatMetrics",
    "ContributionScores",
    "BuildSnapshot",
    "BuildDiff",
    "ContentInfo",
    "PercentileResult",
    "PercentileResults",
    "UserPreferences",
    "FeatureDatabase",
    "SetType",
    "create_recommendation_engine",
]
