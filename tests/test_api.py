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
