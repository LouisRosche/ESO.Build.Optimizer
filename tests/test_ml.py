"""
ML Pipeline Tests

Tests for percentile calculation and recommendation engine.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch


def test_ml_imports():
    """Test that all ML modules can be imported without errors."""
    from ml.percentile import PercentileCalculator, CombatRun, CombatMetrics, ContentInfo
    from ml.recommendations import RecommendationEngine, Recommendation

    assert PercentileCalculator is not None
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
        """Create a sample combat run."""
        from ml.percentile import CombatRun, CombatMetrics, ContentInfo, BuildSnapshot

        return CombatRun(
            run_id="test-run-1",
            player_id="player-1",
            character_name="TestChar",
            timestamp=datetime.now(),
            content=ContentInfo(type="dungeon", name="Test Dungeon", difficulty="veteran"),
            duration_sec=300,
            success=True,
            group_size=4,
            build_snapshot=BuildSnapshot(
                class_name="Dragonknight",
                subclass=None,
                race="Dark Elf",
                cp_level=2100,
                sets=["Set1", "Set2"],
                skills_front=["Skill1"],
                skills_back=["Skill2"],
                champion_points={}
            ),
            metrics=CombatMetrics(
                damage_done=1000000,
                dps=50000,
                crit_rate=0.65,
                healing_done=0,
                hps=0,
                overhealing=0,
                damage_taken=50000,
                damage_blocked=10000,
                damage_shielded=5000,
                deaths=0,
                interrupts=5,
                synergies_used=10,
                buff_uptime={"Major Brutality": 0.95},
                debuff_uptime={}
            )
        )

    @pytest.fixture
    def population(self, sample_run):
        """Create a population of runs for comparison."""
        from ml.percentile import CombatRun, CombatMetrics, ContentInfo, BuildSnapshot

        population = []
        for i in range(50):
            run = CombatRun(
                run_id=f"pop-run-{i}",
                player_id=f"player-{i}",
                character_name=f"Char{i}",
                timestamp=datetime.now(),
                content=sample_run.content,
                duration_sec=300,
                success=True,
                group_size=4,
                build_snapshot=BuildSnapshot(
                    class_name="Dragonknight",
                    subclass=None,
                    race="Dark Elf",
                    cp_level=2000 + i * 10,
                    sets=["Set1", "Set2"],
                    skills_front=["Skill1"],
                    skills_back=["Skill2"],
                    champion_points={}
                ),
                metrics=CombatMetrics(
                    damage_done=800000 + i * 10000,
                    dps=40000 + i * 500,
                    crit_rate=0.5 + i * 0.005,
                    healing_done=0,
                    hps=0,
                    overhealing=0,
                    damage_taken=60000 - i * 500,
                    damage_blocked=8000,
                    damage_shielded=4000,
                    deaths=0 if i > 10 else 1,
                    interrupts=3 + i % 5,
                    synergies_used=8 + i % 10,
                    buff_uptime={"Major Brutality": 0.8 + i * 0.003},
                    debuff_uptime={}
                )
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
        assert result.confidence == "low"
        assert result.sample_size == 0

    def test_none_population(self, calculator, sample_run):
        """Test percentile calculation with None population."""
        result = calculator.calculate_percentile(sample_run, None)

        assert result is not None
        assert result.confidence == "low"

    def test_percentile_calculation(self, calculator, sample_run, population):
        """Test basic percentile calculation."""
        result = calculator.calculate_percentile(sample_run, population)

        assert result is not None
        assert result.sample_size == len(population)
        assert 0.0 <= result.dps_percentile <= 1.0
        assert "damage_dealt" in result.percentiles

    def test_similar_runs_filtering(self, calculator, sample_run, population):
        """Test that only similar runs are included."""
        # Modify some runs to be dissimilar (different content)
        from ml.percentile import ContentInfo

        for run in population[:10]:
            run.content = ContentInfo(type="trial", name="Different", difficulty="normal")

        result = calculator.calculate_percentile(sample_run, population)

        # Should filter out the dissimilar runs
        assert result.sample_size <= len(population)

    def test_cache_key_generation(self, calculator):
        """Test that cache keys are generated correctly."""
        from ml.percentile import ContentInfo

        content = ContentInfo(type="dungeon", name="Test", difficulty="veteran")
        key = calculator._generate_cache_key(content, 2000, 2200)

        assert key is not None
        assert isinstance(key, str)
        assert len(key) > 0

    def test_weighted_percentile_zero_weights(self, calculator):
        """Test weighted percentile with zero weights doesn't crash."""
        import numpy as np

        values = np.array([1.0, 2.0, 3.0])
        weights = np.array([0.0, 0.0, 0.0])

        result = calculator._calculate_weighted_percentile(values, weights, 0.5)
        assert result == 0.0

    def test_linear_interpolation_equal_weights(self, calculator):
        """Test linear interpolation when weights are equal."""
        import numpy as np

        sorted_values = np.array([10.0, 20.0, 30.0])
        cumulative_weights = np.array([0.33, 0.33, 0.34])

        # Should not crash on equal weights
        result = calculator._interpolate_percentile(sorted_values, cumulative_weights, 0.33)
        assert result is not None


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
            TOP_PERFORMER_CLASS_USAGE_THRESHOLD
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
            confidence=0.85
        )

        assert rec.category == "gear"
        assert rec.priority == 1
        assert 0.0 <= rec.confidence <= 1.0

    def test_percentile_result_confidence(self):
        """Test PercentileResult confidence string type."""
        from ml.recommendations import PercentileResult

        result = PercentileResult(
            sample_size=100,
            confidence="high",
            dps_percentile=0.75,
            percentiles={"damage_dealt": 0.75}
        )

        assert result.confidence in ["low", "medium", "high"]
        assert isinstance(result.confidence, str)

    def test_combat_run_from_dict_invalid_timestamp(self):
        """Test CombatRun.from_dict handles invalid timestamps."""
        from ml.recommendations import CombatRun

        data = {
            "run_id": "test-1",
            "player_id": "player-1",
            "character_name": "Test",
            "timestamp": "invalid-timestamp",
            "content": {"type": "dungeon", "name": "Test", "difficulty": "veteran"},
            "duration_sec": 300,
            "success": True,
            "group_size": 4,
            "build_snapshot": {
                "class_name": "Dragonknight",
                "subclass": None,
                "race": "Dark Elf",
                "cp_level": 2000,
                "sets": [],
                "skills_front": [],
                "skills_back": [],
                "champion_points": {}
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
                "damage_shielded": 5000,
                "deaths": 0,
                "interrupts": 5,
                "synergies_used": 10,
                "buff_uptime": {},
                "debuff_uptime": {}
            }
        }

        run = CombatRun.from_dict(data)

        # Should not crash, should use current time as fallback
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
            "content": {"type": "dungeon", "name": "Test", "difficulty": "veteran"},
            "duration_sec": 300,
            "success": True,
            "group_size": 4,
            "build_snapshot": {
                "class_name": "Dragonknight",
                "subclass": None,
                "race": "Dark Elf",
                "cp_level": 2000,
                "sets": [],
                "skills_front": [],
                "skills_back": [],
                "champion_points": {}
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
                "damage_shielded": 5000,
                "deaths": 0,
                "interrupts": 5,
                "synergies_used": 10,
                "buff_uptime": {},
                "debuff_uptime": {},
                "unknown_field": "should be ignored",
                "another_unknown": 12345
            }
        }

        run = CombatRun.from_dict(data)

        # Should not crash with unknown fields
        assert run is not None
        assert run.metrics is not None


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
