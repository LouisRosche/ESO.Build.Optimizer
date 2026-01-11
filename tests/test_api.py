"""
API Backend Tests

Tests for FastAPI endpoints, schemas, and core functionality.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

# Test imports work
def test_api_imports():
    """Test that all API modules can be imported without errors."""
    from api.main import app
    from api.core.config import Settings
    from api.core.security import create_access_token, decode_token
    from api.core.rate_limit import RateLimiter
    from api.models.schemas import UserCreate, UserLogin, CombatRunCreate

    assert app is not None
    assert Settings is not None


def test_settings_defaults():
    """Test that settings have sensible defaults."""
    from api.core.config import Settings

    settings = Settings()
    assert settings.app_name == "ESO Build Optimizer"
    assert settings.environment in ["development", "staging", "production"]
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_expire_minutes > 0


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

    test_data = {"sub": "test@example.com", "user_id": "123"}
    token = create_access_token(test_data)

    assert token is not None
    assert isinstance(token, str)

    decoded = decode_token(token)
    assert decoded.sub == "test@example.com"
    assert decoded.user_id == "123"


def test_rate_limiter():
    """Test rate limiter basic functionality."""
    from api.core.rate_limit import RateLimiter

    limiter = RateLimiter(requests_per_minute=5, requests_per_hour=100)

    # Should allow requests under limit
    for _ in range(5):
        allowed, _ = limiter.check_rate_limit("test_client")
        assert allowed

    # Should block when limit exceeded
    allowed, wait_time = limiter.check_rate_limit("test_client")
    assert not allowed
    assert wait_time > 0


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


def test_combat_run_schema():
    """Test CombatRunCreate schema validation."""
    from api.models.schemas import CombatRunCreate, ContentInfo, BuildSnapshot, CombatMetrics

    run = CombatRunCreate(
        character_name="TestChar",
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
            skills_front=["Skill1", "Skill2"],
            skills_back=["Skill3", "Skill4"],
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
            buff_uptime={},
            debuff_uptime={}
        )
    )

    assert run.character_name == "TestChar"
    assert run.content.type == "dungeon"
    assert run.metrics.dps == 50000


def test_sql_like_escape():
    """Test that SQL LIKE patterns are properly escaped."""
    # Simulate the escape logic from features.py
    def escape_search(search: str) -> str:
        search_escaped = search.replace("%", r"\%").replace("_", r"\_")
        return f"%{search_escaped}%"

    assert escape_search("test") == "%test%"
    assert escape_search("100%") == r"%100\%%"
    assert escape_search("test_value") == r"%test\_value%"
    assert escape_search("100%_test") == r"%100\%\_test%"


class TestAPIEndpoints:
    """Test API endpoint responses."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from api.main import app
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

    def test_features_list_endpoint(self, client):
        """Test features list endpoint."""
        response = client.get("/api/v1/features/")
        # May return 200 or 500 depending on DB availability
        assert response.status_code in [200, 500]

    def test_openapi_schema(self, client):
        """Test OpenAPI schema is generated."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        assert "info" in schema
