"""
ML Pipeline Tests

Tests for percentile calculation and recommendation engine.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch


def test_ml_percentile_imports():
    """Test that percentile module can be imported."""
    from ml.percentile import (
        PercentileCalculator,
        CombatRun,
        ContributionMetrics,
        ContentInfo,
        ContentType,
        Difficulty,
        RoleType,
        SimilarityCriteria,
        PercentileResult,
    )

    assert PercentileCalculator is not None


def test_ml_recommendations_imports():
    """Test that recommendation module can be imported."""
    from ml.recommendations import (
        RecommendationEngine,
        Recommendation,
        BUFF_UPTIME_THRESHOLD,
        DOT_UPTIME_THRESHOLD,
        OVERHEALING_THRESHOLD,
        BUILD_OVERHAUL_PERCENTILE_THRESHOLD,
        TOP_PERFORMER_CLASS_USAGE_THRESHOLD,
    )

    assert RecommendationEngine is not None


class TestPercentileCalculator:
    """Tests for PercentileCalculator class."""

    @pytest.fixture
    def calculator(self):
        """Create a fresh calculator instance."""
        from ml.percentile import PercentileCalculator
        return PercentileCalculator()

    @pytest.fixture
    def sample_run(self):
        """Create a sample combat run matching ml.percentile's CombatRun."""
        from ml.percentile import (
            CombatRun, ContributionMetrics, ContentInfo,
            ContentType, Difficulty, RoleType,
        )

        return CombatRun(
            run_id="test-run-1",
            player_id="player-1",
            character_name="TestChar",
            timestamp=datetime.now(),
            content=ContentInfo(
                content_type=ContentType.DUNGEON,
                name="Test Dungeon",
                difficulty=Difficulty.VETERAN,
            ),
            duration_sec=300,
            success=True,
            group_size=4,
            cp_level=2100,
            role=RoleType.DPS,
            metrics=ContributionMetrics(
                damage_dealt=0.75,
                damage_taken=0.2,
                healing_done=0.05,
                buff_uptime=0.9,
                debuff_uptime=0.5,
                mechanic_execution=0.85,
                resource_efficiency=0.7,
            ),
        )

    @pytest.fixture
    def population(self, sample_run):
        """Create a population of runs for comparison."""
        from ml.percentile import (
            CombatRun, ContributionMetrics, ContentInfo,
            ContentType, Difficulty, RoleType,
        )

        population = []
        for i in range(50):
            run = CombatRun(
                run_id=f"pop-run-{i}",
                player_id=f"player-{i}",
                character_name=f"Char{i}",
                timestamp=datetime.now(),
                content=ContentInfo(
                    content_type=ContentType.DUNGEON,
                    name="Test Dungeon",
                    difficulty=Difficulty.VETERAN,
                ),
                duration_sec=300,
                success=True,
                group_size=4,
                cp_level=2000 + i * 10,
                role=RoleType.DPS,
                metrics=ContributionMetrics(
                    damage_dealt=0.3 + i * 0.01,
                    damage_taken=0.5 - i * 0.005,
                    healing_done=0.05,
                    buff_uptime=0.6 + i * 0.006,
                    debuff_uptime=0.4 + i * 0.005,
                    mechanic_execution=0.5 + i * 0.008,
                    resource_efficiency=0.5 + i * 0.007,
                ),
            )
            population.append(run)
        return population

    def test_calculator_initialization(self, calculator):
        """Test calculator initializes correctly."""
        assert calculator is not None
        assert calculator._cache is not None

    def test_empty_population(self, calculator, sample_run):
        """Test percentile calculation with empty population."""
        result = calculator.calculate_percentile(sample_run, [])

        assert result is not None
        assert result.confidence == 0.0
        assert result.sample_size == 0

    def test_none_population(self, calculator, sample_run):
        """Test percentile calculation with None population."""
        result = calculator.calculate_percentile(sample_run, None)

        assert result is not None
        assert result.sample_size == 0

    def test_percentile_calculation(self, calculator, sample_run, population):
        """Test basic percentile calculation."""
        result = calculator.calculate_percentile(sample_run, population)

        assert result is not None
        assert result.sample_size > 0
        assert 0.0 <= result.weighted_overall <= 1.0
        assert "damage_dealt" in result.percentiles

    def test_similar_runs_filtering(self, calculator, sample_run, population):
        """Test that only similar runs are included."""
        from ml.percentile import ContentInfo, ContentType, Difficulty

        # Modify some runs to be dissimilar (different content)
        for run in population[:10]:
            run.content = ContentInfo(
                content_type=ContentType.TRIAL,
                name="Different",
                difficulty=Difficulty.NORMAL,
            )

        result = calculator.calculate_percentile(sample_run, population)

        # Should filter out the dissimilar runs
        assert result.sample_size <= len(population)

    def test_confidence_calculation(self, calculator):
        """Test confidence calculation based on sample size."""
        from ml.percentile import ContentInfo, ContentType, Difficulty

        content = ContentInfo(
            content_type=ContentType.DUNGEON,
            name="Test",
            difficulty=Difficulty.VETERAN,
        )

        # Zero samples
        assert calculator.calculate_confidence(0) == 0.0

        # Small sample
        conf_small = calculator.calculate_confidence(5)
        assert 0.0 < conf_small < 0.5

        # Large sample
        conf_large = calculator.calculate_confidence(200)
        assert conf_large > 0.85

    def test_batch_calculation(self, calculator, sample_run, population):
        """Test batch percentile calculation."""
        from ml.percentile import CombatRun

        runs = [sample_run]
        results = calculator.calculate_batch(runs, population)

        assert len(results) == 1
        assert results[0].sample_size > 0

    def test_cache_operations(self, calculator):
        """Test cache clear and stats."""
        stats = calculator.get_cache_stats()
        assert "size" in stats
        assert stats["size"] == 0

        cleared = calculator.clear_cache()
        assert cleared == 0

    def test_get_similar_runs(self, calculator, sample_run, population):
        """Test get_similar_runs filtering."""
        similar = calculator.get_similar_runs(sample_run, population)

        # All population runs should match (same content, within CP range)
        assert len(similar) > 0
        for run in similar:
            assert run.run_id != sample_run.run_id

    def test_weighted_percentile_method(self, calculator):
        """Test public calculate_weighted_percentile method."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = calculator.calculate_weighted_percentile(values, 0.5)
        assert result == pytest.approx(30.0, abs=5.0)

    def test_weighted_percentile_empty(self, calculator):
        """Test weighted percentile with empty list."""
        result = calculator.calculate_weighted_percentile([], 0.5)
        assert result == 0.0

    def test_contribution_metrics_clamping(self):
        """Test that ContributionMetrics clamps values."""
        from ml.percentile import ContributionMetrics

        metrics = ContributionMetrics(
            damage_dealt=1.5,  # Over 1.0
            damage_taken=-0.1,  # Under 0.0
        )

        assert metrics.damage_dealt == 1.0
        assert metrics.damage_taken == 0.0

    def test_create_combat_run_from_dict(self):
        """Test factory function for creating CombatRun from dict."""
        from ml.percentile import create_combat_run_from_dict

        data = {
            "run_id": "test-1",
            "player_id": "player-1",
            "character_name": "Test",
            "timestamp": datetime.now().isoformat(),
            "content": {"type": "dungeon", "name": "Test", "difficulty": "veteran"},
            "duration_sec": 300,
            "success": True,
            "group_size": 4,
            "cp_level": 2000,
            "role": "dps",
            "metrics": {
                "damage_dealt": 0.8,
                "healing_done": 0.1,
            },
        }

        run = create_combat_run_from_dict(data)
        assert run is not None
        assert run.run_id == "test-1"
        assert run.character_name == "Test"


class TestRecommendationEngine:
    """Tests for RecommendationEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a fresh recommendation engine instance."""
        from ml.recommendations import RecommendationEngine
        return RecommendationEngine()

    def test_engine_initialization(self, engine):
        """Test engine initializes correctly."""
        assert engine is not None

    def test_threshold_constants(self):
        """Test that threshold constants are defined."""
        from ml.recommendations import (
            BUFF_UPTIME_THRESHOLD,
            DOT_UPTIME_THRESHOLD,
            OVERHEALING_THRESHOLD,
            BUILD_OVERHAUL_PERCENTILE_THRESHOLD,
            TOP_PERFORMER_CLASS_USAGE_THRESHOLD,
        )

        assert 0.0 <= BUFF_UPTIME_THRESHOLD <= 1.0
        assert 0.0 <= DOT_UPTIME_THRESHOLD <= 1.0
        assert 0.0 <= OVERHEALING_THRESHOLD <= 1.0
        assert 0.0 <= BUILD_OVERHAUL_PERCENTILE_THRESHOLD <= 1.0
        assert 0.0 <= TOP_PERFORMER_CLASS_USAGE_THRESHOLD <= 1.0

    def test_recommendation_dataclass(self):
        """Test Recommendation dataclass."""
        from ml.recommendations import Recommendation

        rec = Recommendation(
            recommendation_id="rec-1",
            run_id="run-1",
            category="gear",
            priority=1,
            current_state="Using Set A",
            recommended_change="Switch to Set B",
            expected_improvement="+5% DPS",
            reasoning="Better synergy",
            confidence=0.85,
        )

        assert rec.category == "gear"
        assert rec.priority == 1
        assert 0.0 <= rec.confidence <= 1.0

    def test_combat_run_from_dict(self):
        """Test CombatRun.from_dict from recommendations module."""
        from ml.recommendations import CombatRun

        data = {
            "run_id": "test-1",
            "player_id": "player-1",
            "character_name": "Test",
            "timestamp": datetime.now().isoformat(),
            "content": {
                "content_type": "dungeon",
                "name": "Test",
                "difficulty": "veteran",
            },
            "duration_sec": 300,
            "success": True,
            "group_size": 4,
            "build_snapshot": {
                "class": "Dragonknight",
                "subclass": None,
                "race": "Dark Elf",
                "cp_level": 2000,
                "sets": [],
                "skills_front": [],
                "skills_back": [],
                "champion_points": {},
            },
            "metrics": {
                "damage_done": 1000000,
                "dps": 50000,
                "crit_rate": 0.65,
                "healing_done": 0,
                "hps": 0,
                "overhealing": 0,
                "damage_taken": 50000,
                "damage_blocked": 10000,
                "damage_mitigated": 5000,
                "deaths": 0,
                "interrupts": 5,
                "synergies_used": 10,
                "buff_uptime": {},
                "debuff_uptime": {},
            },
            "contribution_scores": {},
        }

        run = CombatRun.from_dict(data)
        assert run is not None
        assert run.run_id == "test-1"

    def test_combat_run_from_dict_invalid_timestamp(self):
        """Test CombatRun.from_dict handles invalid timestamps."""
        from ml.recommendations import CombatRun

        data = {
            "run_id": "test-1",
            "player_id": "player-1",
            "character_name": "Test",
            "timestamp": "invalid-timestamp",
            "content": {
                "content_type": "dungeon",
                "name": "Test",
                "difficulty": "veteran",
            },
            "duration_sec": 300,
            "success": True,
            "group_size": 4,
            "build_snapshot": {
                "class": "Dragonknight",
                "subclass": None,
                "race": "Dark Elf",
                "cp_level": 2000,
                "sets": [],
                "skills_front": [],
                "skills_back": [],
                "champion_points": {},
            },
            "metrics": {
                "damage_done": 1000000,
                "dps": 50000,
                "crit_rate": 0.65,
            },
            "contribution_scores": {},
        }

        run = CombatRun.from_dict(data)
        assert run is not None
        assert run.timestamp is not None

    def test_combat_metrics_unknown_fields(self):
        """Test CombatMetrics filters unknown fields."""
        from ml.recommendations import CombatRun

        data = {
            "run_id": "test-1",
            "player_id": "player-1",
            "character_name": "Test",
            "timestamp": datetime.now().isoformat(),
            "content": {
                "content_type": "dungeon",
                "name": "Test",
                "difficulty": "veteran",
            },
            "duration_sec": 300,
            "success": True,
            "group_size": 4,
            "build_snapshot": {
                "class": "Dragonknight",
                "subclass": None,
                "race": "Dark Elf",
                "cp_level": 2000,
                "sets": [],
                "skills_front": [],
                "skills_back": [],
                "champion_points": {},
            },
            "metrics": {
                "damage_done": 1000000,
                "dps": 50000,
                "crit_rate": 0.65,
                "unknown_field": "should be ignored",
                "another_unknown": 12345,
            },
            "contribution_scores": {},
        }

        run = CombatRun.from_dict(data)
        assert run is not None
        assert run.metrics is not None

    def test_percentile_result_dataclass(self):
        """Test PercentileResult from recommendations module."""
        from ml.recommendations import PercentileResult

        result = PercentileResult(
            metric="damage_dealt",
            percentile=0.75,
            sample_size=100,
            confidence="high",
        )

        assert result.confidence in ["low", "medium", "high"]
        assert result.is_below_median is False

    def test_contribution_scores_dataclass(self):
        """Test ContributionScores from recommendations module."""
        from ml.recommendations import ContributionScores

        scores = ContributionScores(
            damage_dealt=0.8,
            healing_done=0.1,
            buff_uptime=0.9,
        )

        d = scores.to_dict()
        assert d["damage_dealt"] == 0.8


class TestDataValidation:
    """Tests for data validation utilities."""

    def test_json_data_loading(self):
        """Test that JSON data files can be loaded."""
        import json
        from pathlib import Path

        data_dir = Path("data/raw")
        if not data_dir.exists():
            pytest.skip("Data directory not found")

        for json_file in data_dir.glob("*.json"):
            with open(json_file) as f:
                data = json.load(f)
                assert isinstance(data, list)
                assert len(data) > 0

    def test_feature_count(self):
        """Test that feature count meets minimum threshold."""
        import json
        from pathlib import Path

        data_dir = Path("data/raw")
        if not data_dir.exists():
            pytest.skip("Data directory not found")

        total = 0
        for json_file in data_dir.glob("*.json"):
            with open(json_file) as f:
                data = json.load(f)
                total += len(data)

        assert total >= 1900, f"Feature count {total} is below expected minimum 1900"
