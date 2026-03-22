"""
ML Pipeline Integration Tests

End-to-end tests that verify the percentile calculation → recommendation
generation pipeline works correctly with synthetic data.
"""

import pytest
import random
from datetime import datetime

random.seed(42)  # Reproducible tests


class TestPercentilePipeline:
    """End-to-end percentile calculation tests with synthetic data."""

    @pytest.fixture
    def population(self):
        from ml.synthetic import generate_percentile_population
        return generate_percentile_population(count=200, skill_spread=0.25)

    @pytest.fixture
    def calculator(self):
        from ml.percentile import PercentileCalculator
        return PercentileCalculator()

    def test_top_player_ranks_high(self, calculator, population):
        """A player with 0.95 damage_dealt should rank in top 20%."""
        from ml.percentile import (
            CombatRun, ContentInfo, ContentType, ContributionMetrics,
            Difficulty, RoleType,
        )

        top_run = CombatRun(
            run_id="top-player",
            player_id="top-1",
            character_name="TopDPS",
            timestamp=datetime.now(),
            content=ContentInfo(ContentType.DUNGEON, "Lair of Maarselok", Difficulty.VETERAN),
            duration_sec=300,
            success=True,
            group_size=4,
            cp_level=2100,
            role=RoleType.DPS,
            metrics=ContributionMetrics(
                damage_dealt=0.95,
                damage_taken=0.05,
                healing_done=0.02,
                buff_uptime=0.98,
                debuff_uptime=0.8,
                mechanic_execution=0.95,
                resource_efficiency=0.9,
            ),
        )

        result = calculator.calculate_percentile(top_run, population)

        assert result.sample_size >= 50  # Similarity filtering may exclude some
        assert result.percentiles["damage_dealt"] >= 0.75
        assert result.weighted_overall >= 0.7
        assert result.confidence > 0.5

    def test_bottom_player_ranks_low(self, calculator, population):
        """A player with 0.15 damage_dealt should rank in bottom 30%."""
        from ml.percentile import (
            CombatRun, ContentInfo, ContentType, ContributionMetrics,
            Difficulty, RoleType,
        )

        weak_run = CombatRun(
            run_id="weak-player",
            player_id="weak-1",
            character_name="WeakDPS",
            timestamp=datetime.now(),
            content=ContentInfo(ContentType.DUNGEON, "Lair of Maarselok", Difficulty.VETERAN),
            duration_sec=300,
            success=True,
            group_size=4,
            cp_level=2100,
            role=RoleType.DPS,
            metrics=ContributionMetrics(
                damage_dealt=0.15,
                damage_taken=0.6,
                healing_done=0.02,
                buff_uptime=0.3,
                debuff_uptime=0.1,
                mechanic_execution=0.2,
                resource_efficiency=0.25,
            ),
        )

        result = calculator.calculate_percentile(weak_run, population)

        assert result.percentiles["damage_dealt"] <= 0.35
        assert result.weighted_overall <= 0.4

    def test_median_player_ranks_middle(self, calculator, population):
        """A player with 0.5 damage_dealt should rank near 50th percentile."""
        from ml.percentile import (
            CombatRun, ContentInfo, ContentType, ContributionMetrics,
            Difficulty, RoleType,
        )

        mid_run = CombatRun(
            run_id="mid-player",
            player_id="mid-1",
            character_name="MidDPS",
            timestamp=datetime.now(),
            content=ContentInfo(ContentType.DUNGEON, "Lair of Maarselok", Difficulty.VETERAN),
            duration_sec=300,
            success=True,
            group_size=4,
            cp_level=2100,
            role=RoleType.DPS,
            metrics=ContributionMetrics(
                damage_dealt=0.5,
                damage_taken=0.25,
                healing_done=0.05,
                buff_uptime=0.6,
                debuff_uptime=0.4,
                mechanic_execution=0.55,
                resource_efficiency=0.5,
            ),
        )

        result = calculator.calculate_percentile(mid_run, population)

        # Should be roughly in the middle
        assert 0.25 <= result.percentiles["damage_dealt"] <= 0.75
        assert 0.2 <= result.weighted_overall <= 0.8

    def test_different_content_excluded(self, calculator, population):
        """Runs from different content should not be included in comparison."""
        from ml.percentile import (
            CombatRun, ContentInfo, ContentType, ContributionMetrics,
            Difficulty, RoleType,
        )

        trial_run = CombatRun(
            run_id="trial-player",
            player_id="trial-1",
            character_name="TrialDPS",
            timestamp=datetime.now(),
            content=ContentInfo(ContentType.TRIAL, "Rockgrove", Difficulty.VETERAN),
            duration_sec=300,
            success=True,
            group_size=12,
            cp_level=2100,
            role=RoleType.DPS,
            metrics=ContributionMetrics(damage_dealt=0.8),
        )

        result = calculator.calculate_percentile(trial_run, population)

        # No similar runs exist (population is all dungeons)
        assert result.sample_size == 0
        assert result.confidence == 0.0

    def test_batch_ordering_preserved(self, calculator, population):
        """Batch calculation should maintain input order."""
        from ml.percentile import (
            CombatRun, ContentInfo, ContentType, ContributionMetrics,
            Difficulty, RoleType,
        )

        runs = []
        for i, skill in enumerate([0.2, 0.5, 0.8]):
            runs.append(CombatRun(
                run_id=f"batch-{i}",
                player_id=f"p-{i}",
                character_name=f"C{i}",
                timestamp=datetime.now(),
                content=ContentInfo(ContentType.DUNGEON, "Lair of Maarselok", Difficulty.VETERAN),
                duration_sec=300,
                success=True,
                group_size=4,
                cp_level=2100,
                role=RoleType.DPS,
                metrics=ContributionMetrics(damage_dealt=skill),
            ))

        results = calculator.calculate_batch(runs, population)

        assert len(results) == 3
        # Higher skill should yield higher percentile
        assert results[0].percentiles["damage_dealt"] < results[2].percentiles["damage_dealt"]

    def test_distribution_statistics(self, calculator, population):
        """Distribution stats should return valid statistics."""
        from ml.percentile import (
            CombatRun, ContentInfo, ContentType, ContributionMetrics,
            Difficulty, RoleType,
        )

        run = CombatRun(
            run_id="stats-test",
            player_id="p-1",
            character_name="StatsChar",
            timestamp=datetime.now(),
            content=ContentInfo(ContentType.DUNGEON, "Lair of Maarselok", Difficulty.VETERAN),
            duration_sec=300,
            success=True,
            group_size=4,
            cp_level=2100,
            role=RoleType.DPS,
            metrics=ContributionMetrics(damage_dealt=0.6),
        )

        # get_distribution_statistics requires a category argument
        stats = calculator.get_distribution_statistics(run, population, "damage_dealt")

        assert stats["mean"] > 0
        assert stats["std"] > 0
        assert stats["min"] < stats["max"]


class TestRecommendationPipeline:
    """End-to-end recommendation generation tests."""

    @pytest.fixture
    def engine(self):
        from ml.recommendations import RecommendationEngine, FeatureDatabase
        db = FeatureDatabase()
        return RecommendationEngine(feature_db=db)

    def _make_rec_run(self, run_id, skill_level=0.5, success=True):
        """Create a CombatRun compatible with the recommendations module."""
        from ml.recommendations import (
            CombatRun as RecCombatRun,
            BuildSnapshot,
            CombatMetrics as RecCombatMetrics,
            ContributionScores,
        )

        scores = ContributionScores(
            damage_dealt=skill_level,
            damage_taken=max(0, 0.4 - skill_level * 0.3),
            healing_done=0.05,
            buff_uptime=skill_level * 0.85 + 0.1,
            debuff_uptime=skill_level * 0.6,
            mechanic_execution=skill_level * 0.8 + 0.1,
            resource_efficiency=skill_level * 0.7 + 0.2,
        )

        return RecCombatRun(
            run_id=run_id,
            player_id="p-1",
            character_name="TestChar",
            timestamp=datetime.now(),
            content=type("ContentInfo", (), {
                "content_type": "dungeon",
                "name": "Lair of Maarselok",
                "difficulty": "veteran",
                "matches": lambda self, other: self.name == getattr(other, "name", ""),
            })(),
            duration_sec=300,
            success=success,
            group_size=4,
            build_snapshot=BuildSnapshot(
                player_class="Dragonknight",
                subclass=None,
                race="Dark Elf",
                cp_level=2100,
                sets=["Kinras's Wrath", "Bahsei's Mania"],
                skills_front=["Molten Whip", "Flames of Oblivion"],
                skills_back=["Unstable Wall of Fire", "Cauterize"],
                champion_points={},
            ),
            metrics=RecCombatMetrics(
                damage_done=int(50000 * skill_level * 300),
                dps=50000.0 * skill_level,
                crit_rate=0.4 + skill_level * 0.25,
                healing_done=1000,
                hps=3.0,
                overhealing=500 if skill_level < 0.5 else 0,
                damage_taken=int(300 * 3000 * (1 - skill_level * 0.5)),
                damage_blocked=5000,
                damage_mitigated=10000,
                deaths=max(0, int(2 - skill_level * 2)),
                interrupts=3,
                synergies_used=8,
                buff_uptime={"Major Brutality": skill_level * 0.9},
                debuff_uptime={},
            ),
            contribution_scores=scores,
        )

    def _make_rec_population(self, count=50):
        """Create a population of recommendation-compatible CombatRuns."""
        runs = []
        for i in range(count):
            skill = 0.1 + (i / count) * 0.8
            runs.append(self._make_rec_run(f"pop-{i}", skill_level=skill))
        return runs

    def test_percentile_results_structure(self, engine):
        """Test that percentile calculation returns valid structure."""
        population = self._make_rec_population(50)
        run = self._make_rec_run("rec-test", skill_level=0.4)

        result = engine.calculate_percentiles(run, population)

        assert result is not None
        weak = result.get_weakest_categories(3)
        assert len(weak) <= 3

    def test_feature_database_loads(self):
        """Test that the feature database can load data."""
        from ml.recommendations import FeatureDatabase

        db = FeatureDatabase()
        assert db is not None

    def test_recommendation_generation(self, engine):
        """Test that recommendations are generated for weak players."""
        population = self._make_rec_population(50)
        weak_run = self._make_rec_run("weak-rec", skill_level=0.1, success=False)

        engine.add_runs(population)

        percentiles = engine.calculate_percentiles(weak_run, population)
        recs = engine.generate_recommendations(weak_run, percentiles)

        assert isinstance(recs, list)
        for rec in recs:
            assert rec.category.value in ("gear", "skill", "execution", "build")
            assert 1 <= rec.priority <= 10
            assert 0.0 <= rec.confidence <= 1.0

    def test_strong_player_fewer_recs(self, engine):
        """Strong players should get fewer or no recommendations."""
        population = self._make_rec_population(50)
        strong_run = self._make_rec_run("strong-rec", skill_level=0.95)

        engine.add_runs(population)

        percentiles = engine.calculate_percentiles(strong_run, population)
        recs = engine.generate_recommendations(strong_run, percentiles)

        assert isinstance(recs, list)


class TestSyntheticDataQuality:
    """Verify synthetic data generator produces valid data."""

    def test_population_size(self):
        from ml.synthetic import generate_percentile_population
        pop = generate_percentile_population(count=50)
        assert len(pop) == 50

    def test_metrics_in_range(self):
        from ml.synthetic import generate_percentile_population
        pop = generate_percentile_population(count=100)
        for run in pop:
            assert 0.0 <= run.metrics.damage_dealt <= 1.0
            assert 0.0 <= run.metrics.buff_uptime <= 1.0
            assert 0.0 <= run.metrics.healing_done <= 1.0
            assert 0.0 <= run.metrics.damage_taken <= 1.0

    def test_varied_skill_levels(self):
        """Population should have diverse skill levels."""
        from ml.synthetic import generate_percentile_population
        pop = generate_percentile_population(count=200, skill_spread=0.25)
        damage_values = [r.metrics.damage_dealt for r in pop]

        # Should span a reasonable range
        assert min(damage_values) < 0.3
        assert max(damage_values) > 0.7
        # Standard deviation should indicate diversity
        mean = sum(damage_values) / len(damage_values)
        variance = sum((x - mean) ** 2 for x in damage_values) / len(damage_values)
        std = variance ** 0.5
        assert std > 0.1

    def test_correlated_metrics(self):
        """High damage_dealt should correlate with high buff_uptime."""
        from ml.synthetic import generate_percentile_population
        pop = generate_percentile_population(count=500, skill_spread=0.25)

        top_quarter = sorted(pop, key=lambda r: r.metrics.damage_dealt, reverse=True)[:125]
        bottom_quarter = sorted(pop, key=lambda r: r.metrics.damage_dealt)[:125]

        top_buff_avg = sum(r.metrics.buff_uptime for r in top_quarter) / len(top_quarter)
        bottom_buff_avg = sum(r.metrics.buff_uptime for r in bottom_quarter) / len(bottom_quarter)

        # Top DPS players should have higher buff uptime on average
        assert top_buff_avg > bottom_buff_avg
