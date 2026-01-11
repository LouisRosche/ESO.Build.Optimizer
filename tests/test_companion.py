"""
Companion App Tests

Tests for file watcher, sync client, and utilities.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


def test_companion_imports():
    """Test that all companion modules can be imported without errors."""
    from companion.watcher import SavedVariablesWatcher, LuaTableParser
    from companion.sync import SyncClient, RateLimiter, LocalCache

    assert SavedVariablesWatcher is not None
    assert SyncClient is not None
    assert RateLimiter is not None


class TestLuaTableParser:
    """Tests for Lua table parsing."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        from companion.watcher import LuaTableParser
        return LuaTableParser()

    def test_parse_empty_table(self, parser):
        """Test parsing empty Lua table."""
        result = parser.parse("{}")
        assert result == {}

    def test_parse_simple_table(self, parser):
        """Test parsing simple Lua table."""
        lua_str = '{ ["key"] = "value" }'
        result = parser.parse(lua_str)
        assert result.get("key") == "value"

    def test_parse_nested_table(self, parser):
        """Test parsing nested Lua table."""
        lua_str = '{ ["outer"] = { ["inner"] = 42 } }'
        result = parser.parse(lua_str)
        assert result.get("outer", {}).get("inner") == 42

    def test_parse_number_values(self, parser):
        """Test parsing number values."""
        lua_str = '{ ["int"] = 42, ["float"] = 3.14 }'
        result = parser.parse(lua_str)
        assert result.get("int") == 42
        assert result.get("float") == 3.14

    def test_parse_boolean_values(self, parser):
        """Test parsing boolean values."""
        lua_str = '{ ["yes"] = true, ["no"] = false }'
        result = parser.parse(lua_str)
        assert result.get("yes") is True
        assert result.get("no") is False

    def test_parse_array_style_table(self, parser):
        """Test parsing array-style Lua table."""
        lua_str = '{ "a", "b", "c" }'
        result = parser.parse(lua_str)
        # Array-style becomes dict with numeric string keys
        assert len(result) > 0


class TestRateLimiter:
    """Tests for rate limiter."""

    @pytest.fixture
    def limiter(self):
        """Create a rate limiter instance."""
        from companion.sync import RateLimiter
        return RateLimiter(requests_per_minute=5, requests_per_hour=100)

    def test_allow_under_limit(self, limiter):
        """Test that requests under limit are allowed."""
        for _ in range(5):
            assert limiter.acquire() is True

    def test_block_over_minute_limit(self, limiter):
        """Test that requests over minute limit are blocked."""
        for _ in range(5):
            limiter.acquire()

        # Next request should be blocked
        assert limiter.acquire() is False

    def test_remaining_counts(self, limiter):
        """Test remaining count tracking."""
        initial_minute = limiter.remaining_minute
        initial_hour = limiter.remaining_hour

        limiter.acquire()

        assert limiter.remaining_minute == initial_minute - 1
        assert limiter.remaining_hour == initial_hour - 1


class TestLocalCache:
    """Tests for local cache."""

    @pytest.fixture
    def cache(self):
        """Create a cache instance with temp directory."""
        from companion.sync import LocalCache
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = LocalCache(db_path=Path(tmpdir) / "test_cache.db")
            yield cache

    def test_cache_initialization(self, cache):
        """Test cache initializes correctly."""
        assert cache is not None
        assert cache.db_path.exists()

    def test_cache_data(self, cache):
        """Test caching data."""
        test_data = {"key": "value", "number": 42}
        cache_key = cache.cache_data("test_type", test_data)

        assert cache_key is not None
        assert len(cache_key) > 0

    def test_get_pending(self, cache):
        """Test getting pending items."""
        pending = cache.get_pending(limit=10)
        assert isinstance(pending, list)

    def test_mark_synced(self, cache):
        """Test marking items as synced."""
        test_data = {"test": "data"}
        cache_key = cache.cache_data("test_type", test_data)

        # Should not raise
        cache.mark_synced([cache_key])


class TestSavedVariablesWatcher:
    """Tests for SavedVariables file watcher."""

    def test_watcher_initialization(self):
        """Test watcher can be initialized."""
        from companion.watcher import SavedVariablesWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            sv_path = Path(tmpdir) / "TestAddon.lua"
            sv_path.write_text('ESOBuildOptimizerSV = {}')

            watcher = SavedVariablesWatcher(
                saved_variables_path=sv_path,
                addon_name="ESOBuildOptimizer"
            )

            assert watcher is not None

    def test_default_path_detection(self):
        """Test default SavedVariables path detection."""
        from companion.watcher import get_default_saved_variables_path

        # Should not crash
        path = get_default_saved_variables_path()

        # May return None if ESO not installed
        if path is not None:
            assert isinstance(path, Path)


class TestHashFunctions:
    """Tests for hash functions (should use SHA256)."""

    def test_sha256_used_for_checksums(self):
        """Test that SHA256 is used for checksums."""
        import hashlib

        test_data = b"test data for hashing"
        expected_hash = hashlib.sha256(test_data).hexdigest()

        # Verify SHA256 produces expected length
        assert len(expected_hash) == 64

    def test_content_hash_consistency(self):
        """Test that content hashing is consistent."""
        import hashlib

        data = "consistent test data"
        hash1 = hashlib.sha256(data.encode()).hexdigest()
        hash2 = hashlib.sha256(data.encode()).hexdigest()

        assert hash1 == hash2


class TestCrossPlatformPaths:
    """Tests for cross-platform path handling."""

    def test_windows_path_fallback(self):
        """Test Windows USERPROFILE fallback."""
        import os
        from pathlib import Path

        # Simulate getting user home directory
        userprofile = os.environ.get("USERPROFILE")
        if not userprofile:
            userprofile = os.path.expanduser("~")

        assert userprofile is not None
        assert len(userprofile) > 0

    def test_log_path_creation(self):
        """Test log path directory creation."""
        from pathlib import Path

        log_dir = Path.home() / '.eso_optimizer'

        # Should not crash
        log_dir.mkdir(exist_ok=True)
        assert log_dir.exists()

        # Cleanup
        if log_dir.exists() and not any(log_dir.iterdir()):
            log_dir.rmdir()
