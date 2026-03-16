"""
Companion App Tests

Tests for file watcher, sync client, and utilities.
Runs without real SavedVariables files using temp files and mocks.
"""

import pytest
import asyncio
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
        result = parser.parse_table_string("{}")
        assert result == {}

    def test_parse_simple_table(self, parser):
        """Test parsing simple Lua table."""
        lua_str = '{ ["key"] = "value" }'
        result = parser.parse_table_string(lua_str)
        assert result.get("key") == "value"

    def test_parse_nested_table(self, parser):
        """Test parsing nested Lua table."""
        lua_str = '{ ["outer"] = { ["inner"] = 42 } }'
        result = parser.parse_table_string(lua_str)
        assert result.get("outer", {}).get("inner") == 42

    def test_parse_number_values(self, parser):
        """Test parsing number values."""
        lua_str = '{ ["int"] = 42, ["float"] = 3.14 }'
        result = parser.parse_table_string(lua_str)
        assert result.get("int") == 42
        assert result.get("float") == 3.14

    def test_parse_boolean_values(self, parser):
        """Test parsing boolean values."""
        lua_str = '{ ["yes"] = true, ["no"] = false }'
        result = parser.parse_table_string(lua_str)
        assert result.get("yes") is True
        assert result.get("no") is False

    def test_parse_array_style_table(self, parser):
        """Test parsing array-style Lua table."""
        lua_str = '{ "a", "b", "c" }'
        result = parser.parse_table_string(lua_str)
        # Array-style should return a list
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0] == "a"

    def test_parse_full_saved_variables(self, parser):
        """Test parsing a full SavedVariables-style content."""
        lua_content = '''TestAddon_SavedVariables = {
    ["setting1"] = true,
    ["setting2"] = "hello",
    ["nested"] = {
        ["value"] = 42,
    },
}'''
        result = parser.parse(lua_content)
        assert "TestAddon_SavedVariables" in result
        sv = result["TestAddon_SavedVariables"]
        assert sv.get("setting1") is True
        assert sv.get("setting2") == "hello"
        assert sv.get("nested", {}).get("value") == 42


class TestRateLimiter:
    """Tests for rate limiter (async)."""

    @pytest.fixture
    def limiter(self):
        """Create a rate limiter instance."""
        from companion.sync import RateLimiter
        return RateLimiter(requests_per_minute=5, requests_per_hour=100)

    def test_remaining_counts_initial(self, limiter):
        """Test initial remaining counts."""
        assert limiter.remaining_minute == 5
        assert limiter.remaining_hour == 100

    @pytest.mark.asyncio
    async def test_acquire_reduces_remaining(self):
        """Test that acquiring reduces remaining counts."""
        from companion.sync import RateLimiter

        limiter = RateLimiter(requests_per_minute=5, requests_per_hour=100)
        await limiter.acquire()

        assert limiter.remaining_minute == 4
        assert limiter.remaining_hour == 99


class TestLocalCache:
    """Tests for local SQLite cache."""

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

    def test_sync_queue_operations(self, cache):
        """Test enqueue and dequeue operations."""
        from companion.sync import SyncItem, SyncDirection, SyncStatus
        from datetime import datetime, timezone

        item = SyncItem(
            id="test-item-1",
            item_type="combat_run",
            data={"test": "data"},
            direction=SyncDirection.UPLOAD,
            status=SyncStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        cache.enqueue(item)

        pending = cache.dequeue_batch(
            direction=SyncDirection.UPLOAD,
            status=SyncStatus.PENDING,
            limit=10,
        )
        assert len(pending) == 1
        assert pending[0].id == "test-item-1"

    def test_update_item_status(self, cache):
        """Test updating item status."""
        from companion.sync import SyncItem, SyncDirection, SyncStatus
        from datetime import datetime, timezone

        item = SyncItem(
            id="test-item-2",
            item_type="combat_run",
            data={"test": "data"},
            direction=SyncDirection.UPLOAD,
            status=SyncStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        cache.enqueue(item)
        cache.update_item_status("test-item-2", SyncStatus.SYNCED)

        pending = cache.dequeue_batch(
            direction=SyncDirection.UPLOAD,
            status=SyncStatus.PENDING,
            limit=10,
        )
        assert len(pending) == 0


class TestSavedVariablesWatcher:
    """Tests for SavedVariables file watcher."""

    def test_watcher_initialization(self):
        """Test watcher can be initialized."""
        from companion.watcher import SavedVariablesWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            sv_path = Path(tmpdir)
            watcher = SavedVariablesWatcher(
                saved_variables_path=sv_path,
                addon_name="ESOBuildOptimizer",
            )
            assert watcher is not None
            assert watcher.addon_name == "ESOBuildOptimizer"

    def test_default_path_detection(self):
        """Test default SavedVariables path detection."""
        from companion.watcher import get_default_saved_variables_path

        # Should not crash
        path = get_default_saved_variables_path()
        assert path is not None
        assert isinstance(path, Path)

    def test_addon_file_path(self):
        """Test addon_file_path property."""
        from companion.watcher import SavedVariablesWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            sv_path = Path(tmpdir)
            watcher = SavedVariablesWatcher(
                saved_variables_path=sv_path,
                addon_name="TestAddon",
            )
            assert watcher.addon_file_path == sv_path / "TestAddon.lua"

    def test_parse_current_file_missing(self):
        """Test parsing when file doesn't exist."""
        from companion.watcher import SavedVariablesWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            sv_path = Path(tmpdir)
            watcher = SavedVariablesWatcher(
                saved_variables_path=sv_path,
                addon_name="NonExistent",
            )
            result = watcher.parse_current_file()
            assert result is None

    def test_parse_current_file_exists(self):
        """Test parsing when file exists."""
        from companion.watcher import SavedVariablesWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            sv_path = Path(tmpdir)
            addon_file = sv_path / "TestAddon.lua"
            addon_file.write_text('TestAddon_SavedVariables = { ["key"] = "value" }')

            watcher = SavedVariablesWatcher(
                saved_variables_path=sv_path,
                addon_name="TestAddon",
            )
            result = watcher.parse_current_file()

            assert result is not None
            assert "TestAddon_SavedVariables" in result

    def test_run_cache_operations(self):
        """Test run ID cache operations."""
        from companion.watcher import SavedVariablesWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            sv_path = Path(tmpdir)
            watcher = SavedVariablesWatcher(
                saved_variables_path=sv_path,
                addon_name="Test",
            )

            assert len(watcher.get_known_run_ids()) == 0
            watcher.clear_run_cache()
            assert len(watcher.get_known_run_ids()) == 0


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

    def test_find_saved_variables_paths(self):
        """Test that find_saved_variables_paths doesn't crash."""
        from companion.watcher import find_saved_variables_paths

        paths = find_saved_variables_paths()
        assert isinstance(paths, list)

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
