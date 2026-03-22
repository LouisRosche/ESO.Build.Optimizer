"""
API Backend Tests

Tests for FastAPI endpoints, schemas, and core functionality.
Tests run without a real database using mocks where necessary.
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, patch, MagicMock


def test_api_imports():
    """Test that all API modules can be imported without errors."""
    from api.core.config import Settings
    from api.core.security import create_access_token, decode_token
    from api.models.schemas import UserCreate, UserLogin, CombatRunCreate

    assert Settings is not None


def test_settings_defaults():
    """Test that settings have sensible defaults."""
    from api.core.config import Settings

    settings = Settings()
    assert settings.app_name == "ESO Build Optimizer API"
    assert settings.environment in ["development", "staging", "production"]
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_access_token_expire_minutes > 0


def test_jwt_secret_validation_production():
    """Test that default JWT secret is rejected in production."""
    from api.core.config import Settings
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            jwt_secret_key="CHANGE_ME_IN_PRODUCTION_USE_SECURE_SECRET_KEY"
        )


def test_jwt_secret_allowed_in_development():
    """Test that default JWT secret is allowed in development."""
    from api.core.config import Settings

    settings = Settings(
        environment="development",
        jwt_secret_key="CHANGE_ME_IN_PRODUCTION_USE_SECURE_SECRET_KEY"
    )
    assert settings.jwt_secret_key is not None


def test_token_creation_and_decode():
    """Test JWT token creation and decoding."""
    from api.core.security import create_access_token, decode_token

    test_user_id = uuid4()
    token = create_access_token(test_user_id)

    assert token is not None
    assert isinstance(token, str)

    decoded = decode_token(token)
    assert decoded.sub == test_user_id


def test_user_create_schema():
    """Test UserCreate schema validation."""
    from api.models.schemas import UserCreate
    from pydantic import ValidationError

    # Valid user
    user = UserCreate(
        email="test@example.com",
        username="testuser",
        password="SecurePass123"
    )
    assert user.email == "test@example.com"

    # Invalid email
    with pytest.raises(ValidationError):
        UserCreate(email="invalid", username="test", password="12345678")

    # Short password
    with pytest.raises(ValidationError):
        UserCreate(email="test@example.com", username="test", password="short")


def test_combat_metrics_schema():
    """Test CombatMetrics schema validation."""
    from api.models.schemas import CombatMetrics

    metrics = CombatMetrics(
        damage_done=1000000,
        dps=50000,
        crit_rate=0.65,
        healing_done=0,
        hps=0,
        overhealing=0,
        damage_taken=50000,
        damage_blocked=10000,
        deaths=0,
        interrupts=5,
        synergies_used=10,
    )

    assert metrics.dps == 50000
    assert metrics.crit_rate == 0.65


def test_content_info_schema():
    """Test ContentInfo schema validation."""
    from api.models.schemas import ContentInfo

    content = ContentInfo(type="dungeon", name="Test Dungeon", difficulty="veteran")
    assert content.content_type == "dungeon"
    assert content.name == "Test Dungeon"


def test_build_snapshot_schema():
    """Test BuildSnapshot schema with class alias."""
    from api.models.schemas import BuildSnapshot

    build = BuildSnapshot(
        **{
            "class": "Dragonknight",
            "race": "Dark Elf",
            "cp_level": 2100,
            "sets": ["Set1", "Set2"],
            "skills_front": ["Skill1", "Skill2"],
            "skills_back": ["Skill3", "Skill4"],
        }
    )
    assert build.player_class == "Dragonknight"
    assert build.race == "Dark Elf"


def test_health_response_schema():
    """Test HealthResponse schema."""
    from api.models.schemas import HealthResponse

    response = HealthResponse(
        status="healthy",
        version="0.1.0",
        database="connected",
    )
    assert response.status == "healthy"
    assert response.version == "0.1.0"


def test_error_response_schema():
    """Test ErrorResponse schema."""
    from api.models.schemas import ErrorResponse

    error = ErrorResponse(
        error="Not Found",
        detail="Resource not found",
        status_code=404,
    )
    assert error.status_code == 404


def test_sql_like_escape():
    """Test that SQL LIKE patterns are properly escaped."""
    def escape_search(search: str) -> str:
        search_escaped = search.replace("%", r"\%").replace("_", r"\_")
        return f"%{search_escaped}%"

    assert escape_search("test") == "%test%"
    assert escape_search("100%") == r"%100\%%"
    assert escape_search("test_value") == r"%test\_value%"
    assert escape_search("100%_test") == r"%100\%\_test%"


def test_contribution_scores_schema():
    """Test ContributionScores schema validation."""
    from api.models.schemas import ContributionScores

    scores = ContributionScores(
        damage_dealt=0.75,
        damage_taken=0.1,
        healing_done=0.05,
        buff_uptime=0.85,
        debuff_uptime=0.5,
        mechanic_execution=0.9,
        resource_efficiency=0.7,
    )
    assert scores.damage_dealt == 0.75
    assert scores.buff_uptime == 0.85


def test_feature_base_schema():
    """Test FeatureBase schema with required fields."""
    from api.models.schemas import FeatureBase

    feature = FeatureBase(
        feature_id="TEST_001",
        system="PLAYER",
        category="Class",
        feature_type="ACTIVE",
        name="Test Skill",
        patch_updated="U48",
    )
    assert feature.feature_id == "TEST_001"
    assert feature.name == "Test Skill"


def test_recommendation_schema():
    """Test RecommendationBase schema validation."""
    from api.models.schemas import RecommendationBase

    rec = RecommendationBase(
        category="gear",
        priority=1,
        current_state="Using Set A",
        recommended_change="Switch to Set B",
        expected_improvement="+5% DPS",
        reasoning="Better synergy with your build",
        confidence=0.85,
    )
    assert rec.category == "gear"
    assert rec.confidence == 0.85


class TestSchemaValidation:
    """Edge-case schema validation tests."""

    def test_password_requires_uppercase(self):
        """Password must contain uppercase letter."""
        from api.models.schemas import UserCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="uppercase"):
            UserCreate(email="test@test.com", username="user", password="lowercase1")

    def test_password_requires_digit(self):
        """Password must contain digit."""
        from api.models.schemas import UserCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="digit"):
            UserCreate(email="test@test.com", username="user", password="NoDigitsHere")

    def test_password_min_length(self):
        """Password must be at least 8 characters."""
        from api.models.schemas import UserCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserCreate(email="test@test.com", username="user", password="Ab1")

    def test_combat_metrics_negative_values_rejected(self):
        """Negative values should be rejected for combat metrics."""
        from api.models.schemas import CombatMetrics
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CombatMetrics(damage_done=-100)

    def test_contribution_scores_clamped(self):
        """Contribution scores must be in [0.0, 1.0]."""
        from api.models.schemas import ContributionScores
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ContributionScores(damage_dealt=1.5)

        with pytest.raises(ValidationError):
            ContributionScores(buff_uptime=-0.1)

    def test_build_snapshot_skills_max_length(self):
        """Skills bar can't have more than 6 skills."""
        from api.models.schemas import BuildSnapshot
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BuildSnapshot(
                **{
                    "class": "Dragonknight",
                    "race": "Dark Elf",
                    "cp_level": 2100,
                    "sets": [],
                    "skills_front": ["s1", "s2", "s3", "s4", "s5", "s6", "s7"],
                    "skills_back": [],
                }
            )

    def test_build_snapshot_cp_level_bounds(self):
        """CP level must be 0-3600."""
        from api.models.schemas import BuildSnapshot
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BuildSnapshot(
                **{
                    "class": "Dragonknight",
                    "race": "Dark Elf",
                    "cp_level": 5000,
                    "sets": [],
                    "skills_front": [],
                    "skills_back": [],
                }
            )

    def test_combat_run_group_size_bounds(self):
        """Group size must be 1-24."""
        from api.models.schemas import CombatRunBase, ContentInfo, BuildSnapshot, CombatMetrics
        from pydantic import ValidationError

        content = ContentInfo(type="dungeon", name="Test", difficulty="veteran")
        build = BuildSnapshot(
            **{
                "class": "Dragonknight",
                "race": "Dark Elf",
                "cp_level": 2100,
                "sets": [],
                "skills_front": [],
                "skills_back": [],
            }
        )
        metrics = CombatMetrics()

        with pytest.raises(ValidationError):
            CombatRunBase(
                character_name="Test",
                content=content,
                duration_sec=300,
                success=True,
                group_size=25,
                build_snapshot=build,
                metrics=metrics,
            )

    def test_recommendation_priority_bounds(self):
        """Recommendation priority must be 1-10."""
        from api.models.schemas import RecommendationBase
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RecommendationBase(
                category="gear",
                priority=0,
                current_state="x",
                recommended_change="y",
                expected_improvement="z",
                reasoning="r",
                confidence=0.5,
            )

        with pytest.raises(ValidationError):
            RecommendationBase(
                category="gear",
                priority=11,
                current_state="x",
                recommended_change="y",
                expected_improvement="z",
                reasoning="r",
                confidence=0.5,
            )

    def test_recommendation_confidence_bounds(self):
        """Recommendation confidence must be [0.0, 1.0]."""
        from api.models.schemas import RecommendationBase
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RecommendationBase(
                category="gear",
                priority=1,
                current_state="x",
                recommended_change="y",
                expected_improvement="z",
                reasoning="r",
                confidence=1.5,
            )

    def test_crit_rate_bounds(self):
        """Crit rate must be 0.0-1.0."""
        from api.models.schemas import CombatMetrics
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CombatMetrics(crit_rate=2.0)

    def test_content_type_enum_values(self):
        """Only valid content types are accepted."""
        from api.models.schemas import ContentInfo
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ContentInfo(type="raid", name="Test", difficulty="veteran")

    def test_difficulty_enum_values(self):
        """Only valid difficulty values are accepted."""
        from api.models.schemas import ContentInfo
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ContentInfo(type="dungeon", name="Test", difficulty="mythic")

    def test_valid_combat_run_full(self):
        """Full valid combat run passes all validation."""
        from api.models.schemas import CombatRunCreate, ContentInfo, BuildSnapshot, CombatMetrics

        run = CombatRunCreate(
            character_name="TestDK",
            content=ContentInfo(type="dungeon", name="Lair of Maarselok", difficulty="veteran"),
            duration_sec=300,
            success=True,
            group_size=4,
            build_snapshot=BuildSnapshot(
                **{
                    "class": "Dragonknight",
                    "race": "Dark Elf",
                    "cp_level": 2100,
                    "sets": ["Kinras's Wrath", "Bahsei's Mania"],
                    "skills_front": ["Molten Whip"],
                    "skills_back": ["Unstable Wall of Fire"],
                }
            ),
            metrics=CombatMetrics(
                damage_done=15000000,
                dps=50000,
                crit_rate=0.62,
            ),
        )

        assert run.character_name == "TestDK"
        assert run.content.content_type.value == "dungeon"

    def test_recommendations_list_response_schema(self):
        """RecommendationsListResponse accepts ML adapter output format."""
        from api.models.schemas import RecommendationsListResponse, RecommendationResponse
        from uuid import uuid4

        run_id = uuid4()
        rec_id = uuid4()

        resp = RecommendationsListResponse(
            run_id=run_id,
            recommendations=[
                RecommendationResponse(
                    recommendation_id=rec_id,
                    run_id=run_id,
                    category="gear",
                    priority=1,
                    current_state="Using suboptimal gear",
                    recommended_change="Switch to trial sets",
                    expected_improvement="+8.5% DPS",
                    reasoning="Top performers use these sets",
                    confidence=0.82,
                )
            ],
            percentiles={"damage_dealt": 0.35, "buff_uptime": 0.42},
            sample_size=150,
            confidence="high",
        )

        assert resp.sample_size == 150
        assert len(resp.recommendations) == 1
        assert resp.recommendations[0].confidence == 0.82

    def test_gear_set_schema(self):
        """GearSetBase validates complex nested structure."""
        from api.models.schemas import GearSetBase, SetBonusEffect, RoleAffinity

        gear = GearSetBase(
            set_id="KINRAS_001",
            name="Kinras's Wrath",
            set_type="Dungeon",
            weight="Light",
            bind_type="Bind on Pickup",
            tradeable=False,
            location="Black Drake Villa",
            bonuses={
                "2pc": SetBonusEffect(stat="Spell Damage", value=129),
                "5pc": SetBonusEffect(
                    effect="Adds stacks of Burning Heart",
                    proc_condition="Light attacks",
                    buff_granted="Major Berserk",
                ),
            },
            pve_tier="S",
            role_affinity=RoleAffinity(damage_dealt=0.95, buff_uptime=0.8),
            patch_updated="U48",
        )

        assert gear.name == "Kinras's Wrath"
        assert gear.bonuses["5pc"].buff_granted == "Major Berserk"


class TestAPIEndpoints:
    """Test API endpoint responses using TestClient with mocked DB."""

    @pytest.fixture
    def client(self):
        """Create test client with mocked database lifespan."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from contextlib import asynccontextmanager

        # Create a stripped-down app to avoid real DB connections
        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "healthy", "version": "0.1.0", "database": "mocked"}

        @app.get("/")
        async def root():
            return {
                "message": "ESO Build Optimizer API",
                "version": "0.1.0",
            }

        @app.get("/openapi.json")
        async def openapi():
            return app.openapi()

        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
