"""
Tests for the ML adapter module that bridges DB models to ML pipeline.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ml.adapter import db_run_to_ml_run, ml_recommendation_to_dict, percentile_results_to_dict
from ml.recommendations import (
    CombatRun as MLCombatRun,
    ContentInfo as MLContentInfo,
    PercentileResult,
    PercentileResults,
    Recommendation as MLRecommendation,
    RecommendationCategory,
)


def _make_db_run(**overrides):
    """Create a mock DB CombatRun with sensible defaults."""
    defaults = {
        "run_id": uuid.uuid4(),
        "player_id": uuid.uuid4(),
        "character_name": "TestChar",
        "timestamp": datetime.now(timezone.utc),
        "content_type": "dungeon",
        "content_name": "Lair of Maarselok",
        "difficulty": "veteran",
        "duration_sec": 300,
        "success": True,
        "group_size": 4,
        "cp_level": 2100,
        "dps": 45000.0,
        "build_snapshot": {
            "class": "Dragonknight",
            "subclass": None,
            "race": "Dark Elf",
            "cp_level": 2100,
            "sets": ["Kinras's Wrath", "Bahsei's Mania"],
            "skills_front": ["Molten Whip"],
            "skills_back": ["Unstable Wall of Fire"],
            "champion_points": {},
        },
        "metrics": {
            "damage_done": 13500000,
            "dps": 45000.0,
            "crit_rate": 0.62,
            "healing_done": 500,
            "hps": 1.7,
            "overhealing": 200,
            "damage_taken": 150000,
            "damage_blocked": 5000,
            "damage_mitigated": 10000,
            "buff_uptime": {"Major Brutality": 0.92},
            "debuff_uptime": {},
            "deaths": 0,
            "interrupts": 3,
            "synergies_used": 8,
        },
        "contribution_scores": {
            "damage_dealt": 0.75,
            "damage_taken": 0.15,
            "healing_done": 0.02,
            "buff_uptime": 0.88,
            "debuff_uptime": 0.4,
            "mechanic_execution": 0.82,
            "resource_efficiency": 0.7,
        },
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestDbRunToMlRun:
    """Test conversion from DB CombatRun to ML CombatRun."""

    def test_basic_conversion(self):
        db_run = _make_db_run()
        ml_run = db_run_to_ml_run(db_run)

        assert isinstance(ml_run, MLCombatRun)
        assert ml_run.run_id == str(db_run.run_id)
        assert ml_run.character_name == "TestChar"
        assert isinstance(ml_run.content, MLContentInfo)
        assert ml_run.content.name == "Lair of Maarselok"
        assert ml_run.content.difficulty == "veteran"

    def test_build_snapshot_extraction(self):
        db_run = _make_db_run()
        ml_run = db_run_to_ml_run(db_run)

        assert ml_run.build_snapshot.player_class == "Dragonknight"
        assert "Kinras's Wrath" in ml_run.build_snapshot.sets

    def test_contribution_scores_extraction(self):
        db_run = _make_db_run()
        ml_run = db_run_to_ml_run(db_run)

        assert ml_run.contribution_scores.damage_dealt == 0.75
        assert ml_run.contribution_scores.buff_uptime == 0.88

    def test_null_contribution_scores(self):
        db_run = _make_db_run(contribution_scores=None)
        ml_run = db_run_to_ml_run(db_run)

        assert ml_run.contribution_scores.damage_dealt == 0.0

    def test_empty_build_snapshot(self):
        db_run = _make_db_run(build_snapshot={})
        ml_run = db_run_to_ml_run(db_run)

        assert ml_run.build_snapshot.player_class == "Unknown"
        assert ml_run.build_snapshot.sets == []


class TestMlRecommendationToDict:
    """Test conversion from ML Recommendation to dict."""

    def test_basic_conversion(self):
        rec = MLRecommendation(
            recommendation_id="rec-1",
            run_id="run-1",
            category=RecommendationCategory.GEAR,
            priority=1,
            current_state="Using Set A",
            recommended_change="Switch to Set B",
            expected_improvement="+8% DPS",
            reasoning="Better synergy with class",
            confidence=0.85,
        )

        d = ml_recommendation_to_dict(rec)

        assert d["category"] == "gear"
        assert d["priority"] == 1
        assert d["confidence"] == 0.85
        assert "run_id" not in d  # run_id set by caller


class TestPercentileResultsToDict:
    """Test conversion from PercentileResults to flat dict."""

    def test_basic_conversion(self):
        results = PercentileResults(
            run_id="run-1",
            percentiles={
                "damage_dealt": PercentileResult("damage_dealt", 0.82, 100, "high"),
                "buff_uptime": PercentileResult("buff_uptime", 0.65, 100, "high"),
            },
            overall_confidence="high",
            sample_size=100,
        )

        d = percentile_results_to_dict(results)

        assert d["damage_dealt"] == 0.82
        assert d["buff_uptime"] == 0.65
        assert len(d) == 2
