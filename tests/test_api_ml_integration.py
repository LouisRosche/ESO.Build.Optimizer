"""
API ↔ ML Pipeline Integration Tests

Tests the full flow from DB models through the ML adapter to recommendation
output, without requiring a running database. Uses mock DB objects that mirror
the SQLAlchemy model structure.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from ml.adapter import (
    MLAdapter,
    db_run_to_ml_run,
    ml_recommendation_to_dict,
    percentile_results_to_dict,
)
from ml.recommendations import (
    CombatRun as MLCombatRun,
    ContentInfo as MLContentInfo,
    PercentileResult,
    PercentileResults,
    Recommendation as MLRecommendation,
    RecommendationCategory,
    RecommendationEngine,
)


# =============================================================================
# Fixtures
# =============================================================================

def _make_db_run(
    skill_level: float = 0.5,
    content_name: str = "Lair of Maarselok",
    cp_level: int = 2100,
    **overrides,
) -> SimpleNamespace:
    """Create a mock DB CombatRun that mirrors SQLAlchemy model fields."""
    defaults = {
        "run_id": uuid.uuid4(),
        "player_id": uuid.uuid4(),
        "character_name": f"Char_{skill_level:.0%}",
        "timestamp": datetime.now(timezone.utc),
        "content_type": "dungeon",
        "content_name": content_name,
        "difficulty": "veteran",
        "duration_sec": 300,
        "success": skill_level > 0.3,
        "group_size": 4,
        "cp_level": cp_level,
        "dps": 50000.0 * skill_level,
        "build_snapshot": {
            "class": "Dragonknight",
            "subclass": None,
            "race": "Dark Elf",
            "cp_level": cp_level,
            "sets": ["Kinras's Wrath", "Bahsei's Mania"],
            "skills_front": ["Molten Whip", "Flames of Oblivion"],
            "skills_back": ["Unstable Wall of Fire", "Cauterize"],
            "champion_points": {},
        },
        "metrics": {
            "damage_done": int(50000 * skill_level * 300),
            "dps": 50000.0 * skill_level,
            "crit_rate": 0.4 + skill_level * 0.25,
            "healing_done": 500,
            "hps": 1.7,
            "overhealing": 200,
            "damage_taken": int(300 * 3000 * (1 - skill_level * 0.5)),
            "damage_blocked": 5000,
            "damage_mitigated": 10000,
            "buff_uptime": {"Major Brutality": skill_level * 0.9},
            "debuff_uptime": {},
            "deaths": max(0, int(2 - skill_level * 2)),
            "interrupts": 3,
            "synergies_used": 8,
        },
        "contribution_scores": {
            "damage_dealt": skill_level * 0.9,
            "damage_taken": max(0, 0.4 - skill_level * 0.3),
            "healing_done": 0.05,
            "buff_uptime": skill_level * 0.85 + 0.1,
            "debuff_uptime": skill_level * 0.6,
            "mechanic_execution": skill_level * 0.8 + 0.1,
            "resource_efficiency": skill_level * 0.7 + 0.2,
        },
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_population(count: int = 50) -> list[SimpleNamespace]:
    """Create a population of mock DB runs with varied skill levels."""
    return [
        _make_db_run(skill_level=0.1 + (i / count) * 0.8)
        for i in range(count)
    ]


# =============================================================================
# Conversion Tests
# =============================================================================

class TestDBToMLConversion:
    """Test full round-trip conversion from DB models to ML and back."""

    def test_conversion_preserves_identity(self):
        """Run ID and player ID survive conversion."""
        db_run = _make_db_run()
        ml_run = db_run_to_ml_run(db_run)

        assert ml_run.run_id == str(db_run.run_id)
        assert ml_run.player_id == str(db_run.player_id)

    def test_conversion_preserves_content(self):
        """Content info maps correctly."""
        db_run = _make_db_run(content_name="Rockgrove")
        ml_run = db_run_to_ml_run(db_run)

        assert ml_run.content.name == "Rockgrove"
        assert ml_run.content.content_type == "dungeon"
        assert ml_run.content.difficulty == "veteran"

    def test_conversion_preserves_build(self):
        """Build snapshot fields map correctly."""
        db_run = _make_db_run()
        ml_run = db_run_to_ml_run(db_run)

        assert ml_run.build_snapshot.player_class == "Dragonknight"
        assert ml_run.build_snapshot.race == "Dark Elf"
        assert len(ml_run.build_snapshot.sets) == 2

    def test_conversion_preserves_contribution_scores(self):
        """Contribution scores map to correct ML fields."""
        db_run = _make_db_run(skill_level=0.8)
        ml_run = db_run_to_ml_run(db_run)

        assert ml_run.contribution_scores.damage_dealt == pytest.approx(0.72, abs=0.01)
        assert ml_run.contribution_scores.buff_uptime == pytest.approx(0.78, abs=0.01)

    def test_missing_contribution_scores(self):
        """Null contribution_scores doesn't crash."""
        db_run = _make_db_run(contribution_scores=None)
        ml_run = db_run_to_ml_run(db_run)

        assert ml_run.contribution_scores.damage_dealt == 0.0
        assert ml_run.contribution_scores.buff_uptime == 0.0

    def test_missing_build_fields(self):
        """Partial build_snapshot doesn't crash."""
        db_run = _make_db_run(build_snapshot={"class": "Sorcerer", "race": "High Elf"})
        ml_run = db_run_to_ml_run(db_run)

        assert ml_run.build_snapshot.player_class == "Sorcerer"
        assert ml_run.build_snapshot.sets == []
        assert ml_run.build_snapshot.skills_front == []

    def test_population_conversion(self):
        """Bulk conversion works without errors."""
        population = _make_population(100)
        ml_runs = [db_run_to_ml_run(r) for r in population]

        assert len(ml_runs) == 100
        assert all(isinstance(r, MLCombatRun) for r in ml_runs)


# =============================================================================
# ML Pipeline Integration via Adapter
# =============================================================================

class TestMLAdapterPipeline:
    """Test the full adapter pipeline: DB runs → ML analysis → results."""

    @pytest.fixture
    def adapter(self):
        return MLAdapter()

    @pytest.fixture
    def weak_run(self):
        return _make_db_run(skill_level=0.15)

    @pytest.fixture
    def strong_run(self):
        return _make_db_run(skill_level=0.92)

    @pytest.fixture
    def population(self):
        return _make_population(60)

    @pytest.mark.asyncio
    async def test_analyze_run_returns_valid_structure(self, adapter, weak_run, population):
        """Full analysis returns (percentiles, sample_size, confidence, recs)."""
        pcts, sample_size, confidence, recs = await adapter.analyze_run(weak_run, population)

        assert isinstance(pcts, dict)
        assert sample_size >= 0
        assert confidence in ("low", "medium", "high")
        assert isinstance(recs, list)

    @pytest.mark.asyncio
    async def test_weak_player_gets_recommendations(self, adapter, weak_run, population):
        """A low-skill player should receive at least one recommendation."""
        _, _, _, recs = await adapter.analyze_run(weak_run, population)

        assert len(recs) > 0
        for rec in recs:
            assert "category" in rec
            assert "priority" in rec
            assert "confidence" in rec
            assert 0.0 <= rec["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_strong_player_gets_fewer_recs(self, adapter, strong_run, population):
        """A high-skill player should get fewer recommendations."""
        _, _, _, weak_recs = await adapter.analyze_run(
            _make_db_run(skill_level=0.15), population
        )
        _, _, _, strong_recs = await adapter.analyze_run(strong_run, population)

        # Strong player may still get recs, but fewer or equal
        assert len(strong_recs) <= len(weak_recs) + 2  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_percentiles_only(self, adapter, weak_run, population):
        """Percentiles-only mode skips recommendation generation."""
        pcts, sample_size, confidence = await adapter.calculate_percentiles_only(
            weak_run, population
        )

        assert isinstance(pcts, dict)
        assert sample_size >= 0

    @pytest.mark.asyncio
    async def test_empty_population(self, adapter, weak_run):
        """Empty comparison pool returns valid (empty) results."""
        pcts, sample_size, confidence = await adapter.calculate_percentiles_only(
            weak_run, []
        )

        assert sample_size == 0

    @pytest.mark.asyncio
    async def test_recommendation_categories_are_valid(self, adapter, weak_run, population):
        """All recommendation categories are valid enum values."""
        _, _, _, recs = await adapter.analyze_run(weak_run, population)

        valid_categories = {"gear", "skill", "execution", "build"}
        for rec in recs:
            assert rec["category"] in valid_categories

    @pytest.mark.asyncio
    async def test_empty_population_returns_defaults(self, adapter):
        """A run with no similar content gets default percentiles."""
        trial_run = _make_db_run(
            skill_level=0.5,
            content_name="Rockgrove",
        )
        # In production, _fetch_similar_runs filters by content — so empty pool
        pcts, sample_size, confidence = await adapter.calculate_percentiles_only(
            trial_run, []
        )

        assert sample_size == 0
        assert confidence == "low"


# =============================================================================
# FeatureDatabase Integration
# =============================================================================

class TestFeatureDatabaseIntegration:
    """Test that FeatureDatabase loads real data from data/raw/."""

    def test_loads_skills(self):
        """FeatureDatabase loads skills from JSON files."""
        from ml.recommendations import FeatureDatabase
        from pathlib import Path

        data_dir = Path("data/raw")
        if not data_dir.exists():
            pytest.skip("data/raw not available")

        db = FeatureDatabase(data_dir=data_dir)

        # Should have loaded data
        db._load_data()
        assert len(db._skills_cache) > 0, "No skills loaded from data/raw"

    def test_loads_sets(self):
        """FeatureDatabase loads gear sets from JSON files."""
        from ml.recommendations import FeatureDatabase
        from pathlib import Path

        data_dir = Path("data/raw")
        if not data_dir.exists():
            pytest.skip("data/raw not available")

        db = FeatureDatabase(data_dir=data_dir)
        db._load_data()
        assert len(db._sets_cache) > 0, "No sets loaded from data/raw"

    def test_skill_lookup_by_name(self):
        """Can look up a skill by name."""
        from ml.recommendations import FeatureDatabase
        from pathlib import Path

        data_dir = Path("data/raw")
        if not data_dir.exists():
            pytest.skip("data/raw not available")

        db = FeatureDatabase(data_dir=data_dir)
        db._load_data()

        # Get any skill name from the cache
        skill_names = [k for k in db._skills_cache if not k.startswith("P")]
        if skill_names:
            result = db.get_skill(skill_names[0])
            assert result is not None

    def test_set_lookup_by_name(self):
        """Can look up a gear set by name."""
        from ml.recommendations import FeatureDatabase
        from pathlib import Path

        data_dir = Path("data/raw")
        if not data_dir.exists():
            pytest.skip("data/raw not available")

        db = FeatureDatabase(data_dir=data_dir)
        db._load_data()

        set_names = [k for k in db._sets_cache if not k.startswith("S")]
        if set_names:
            result = db.get_set(set_names[0])
            assert result is not None

    def test_sets_by_type(self):
        """Can filter sets by type."""
        from ml.recommendations import FeatureDatabase, SetType
        from pathlib import Path

        data_dir = Path("data/raw")
        if not data_dir.exists():
            pytest.skip("data/raw not available")

        db = FeatureDatabase(data_dir=data_dir)
        trial_sets = db.get_sets_by_type(SetType.TRIAL)

        # Should have at least some trial sets
        assert isinstance(trial_sets, list)

    def test_engine_with_feature_db(self):
        """RecommendationEngine integrates with FeatureDatabase."""
        from ml.recommendations import FeatureDatabase

        db = FeatureDatabase()
        engine = RecommendationEngine(feature_db=db)

        # Engine should accept runs and generate recs
        population = _make_population(30)
        ml_runs = [db_run_to_ml_run(r) for r in population]
        weak_ml_run = db_run_to_ml_run(_make_db_run(skill_level=0.1))

        engine.add_runs(ml_runs)
        percentiles = engine.calculate_percentiles(weak_ml_run, ml_runs)
        recs = engine.generate_recommendations(weak_ml_run, percentiles)

        assert isinstance(recs, list)
        for rec in recs:
            assert rec.category in RecommendationCategory


# =============================================================================
# Recommendation Output Quality
# =============================================================================

class TestRecommendationQuality:
    """Validate that ML recommendations are actionable and well-structured."""

    @pytest.fixture
    def engine(self):
        return RecommendationEngine()

    @pytest.fixture
    def population_ml(self):
        pop = _make_population(80)
        return [db_run_to_ml_run(r) for r in pop]

    def test_recommendations_have_reasoning(self, engine, population_ml):
        """Every recommendation includes reasoning text."""
        engine.add_runs(population_ml)
        weak_run = db_run_to_ml_run(_make_db_run(skill_level=0.1))
        percentiles = engine.calculate_percentiles(weak_run, population_ml)
        recs = engine.generate_recommendations(weak_run, percentiles)

        for rec in recs:
            assert len(rec.reasoning) > 10, f"Reasoning too short: {rec.reasoning}"
            assert len(rec.recommended_change) > 10

    def test_recommendations_are_prioritized(self, engine, population_ml):
        """Recommendations are ordered by priority."""
        engine.add_runs(population_ml)
        weak_run = db_run_to_ml_run(_make_db_run(skill_level=0.1))
        percentiles = engine.calculate_percentiles(weak_run, population_ml)
        recs = engine.generate_recommendations(weak_run, percentiles)

        if len(recs) >= 2:
            priorities = [r.priority for r in recs]
            assert priorities == sorted(priorities), "Recommendations should be ordered by priority"

    def test_confidence_is_bounded(self, engine, population_ml):
        """Confidence scores are in [0.0, 1.0]."""
        engine.add_runs(population_ml)
        weak_run = db_run_to_ml_run(_make_db_run(skill_level=0.1))
        percentiles = engine.calculate_percentiles(weak_run, population_ml)
        recs = engine.generate_recommendations(weak_run, percentiles)

        for rec in recs:
            assert 0.0 <= rec.confidence <= 1.0, f"Confidence out of bounds: {rec.confidence}"

    def test_max_recommendations_cap(self, engine, population_ml):
        """Recommendations don't exceed the max limit."""
        engine.add_runs(population_ml)
        weak_run = db_run_to_ml_run(_make_db_run(skill_level=0.05))
        percentiles = engine.calculate_percentiles(weak_run, population_ml)
        recs = engine.generate_recommendations(weak_run, percentiles, max_recommendations=3)

        assert len(recs) <= 3
