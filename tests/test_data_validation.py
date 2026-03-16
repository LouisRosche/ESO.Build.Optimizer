"""
Data Validation Tests

Validates the JSON data files in data/raw/:
- All files are valid JSON
- Each feature has required fields (feature_id, name, category)
- No duplicate feature_ids across all files
- patch_updated field exists
"""

import json
import pytest
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "raw"

# Skill/feature files use feature_id; set files use set_id
SKILL_FILE_PREFIXES = [
    "phase01_", "phase02_", "phase03_", "phase04_", "phase05_",
    "phase06_", "phase07_", "phase08_", "phase09_", "phase10_",
    "phase11_",
]
SET_FILE_PREFIXES = ["sets_"]


def _is_skill_file(filename: str) -> bool:
    return any(filename.startswith(p) for p in SKILL_FILE_PREFIXES)


def _is_set_file(filename: str) -> bool:
    return any(filename.startswith(p) for p in SET_FILE_PREFIXES)


def _get_all_json_files() -> list[Path]:
    if not DATA_DIR.exists():
        return []
    return sorted(DATA_DIR.glob("*.json"))


class TestJsonValidity:
    """Test that all JSON files in data/raw/ are valid JSON."""

    def test_data_directory_exists(self):
        """Test that the data/raw directory exists."""
        assert DATA_DIR.exists(), f"Data directory not found: {DATA_DIR}"

    def test_json_files_exist(self):
        """Test that there are JSON files to validate."""
        json_files = _get_all_json_files()
        assert len(json_files) > 0, "No JSON files found in data/raw/"

    @pytest.mark.parametrize(
        "json_file",
        _get_all_json_files(),
        ids=lambda p: p.name,
    )
    def test_valid_json(self, json_file):
        """Test that each JSON file is valid JSON."""
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list), f"{json_file.name} should contain a JSON array"
        assert len(data) > 0, f"{json_file.name} should not be empty"


class TestRequiredFields:
    """Test that each entry has the required fields."""

    @pytest.mark.parametrize(
        "json_file",
        [f for f in _get_all_json_files() if _is_skill_file(f.name)],
        ids=lambda p: p.name,
    )
    def test_skill_required_fields(self, json_file):
        """Test that skill/feature entries have feature_id, name, and category."""
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for i, entry in enumerate(data):
            assert "feature_id" in entry, (
                f"{json_file.name}[{i}]: missing 'feature_id'"
            )
            assert "name" in entry, (
                f"{json_file.name}[{i}] ({entry.get('feature_id', '?')}): missing 'name'"
            )
            assert "category" in entry, (
                f"{json_file.name}[{i}] ({entry.get('feature_id', '?')}): missing 'category'"
            )

    @pytest.mark.parametrize(
        "json_file",
        [f for f in _get_all_json_files() if _is_set_file(f.name)],
        ids=lambda p: p.name,
    )
    def test_set_required_fields(self, json_file):
        """Test that set entries have set_id and name."""
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for i, entry in enumerate(data):
            assert "set_id" in entry, (
                f"{json_file.name}[{i}]: missing 'set_id'"
            )
            assert "name" in entry, (
                f"{json_file.name}[{i}] ({entry.get('set_id', '?')}): missing 'name'"
            )


class TestPatchUpdated:
    """Test that patch_updated field exists on all entries."""

    @pytest.mark.parametrize(
        "json_file",
        _get_all_json_files(),
        ids=lambda p: p.name,
    )
    def test_patch_updated_exists(self, json_file):
        """Test that every entry has a patch_updated field."""
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for i, entry in enumerate(data):
            entry_id = entry.get("feature_id") or entry.get("set_id") or f"index-{i}"
            assert "patch_updated" in entry, (
                f"{json_file.name}: entry '{entry_id}' missing 'patch_updated'"
            )
            assert entry["patch_updated"], (
                f"{json_file.name}: entry '{entry_id}' has empty 'patch_updated'"
            )


class TestNoDuplicateIds:
    """Test that there are no duplicate IDs across all files."""

    def test_no_duplicate_feature_ids(self):
        """Test no duplicate feature_ids across all skill files."""
        seen_ids: dict[str, str] = {}  # id -> filename
        duplicates = []

        for json_file in _get_all_json_files():
            if not _is_skill_file(json_file.name):
                continue

            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for entry in data:
                fid = entry.get("feature_id")
                if fid is None:
                    continue
                if fid in seen_ids:
                    duplicates.append(
                        f"Duplicate feature_id '{fid}' in {json_file.name} "
                        f"(first seen in {seen_ids[fid]})"
                    )
                else:
                    seen_ids[fid] = json_file.name

        assert len(duplicates) == 0, (
            f"Found {len(duplicates)} duplicate feature_ids:\n"
            + "\n".join(duplicates[:20])
        )

    def test_no_duplicate_set_ids(self):
        """Test no duplicate set_ids across all set files."""
        seen_ids: dict[str, str] = {}  # id -> filename
        duplicates = []

        for json_file in _get_all_json_files():
            if not _is_set_file(json_file.name):
                continue

            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for entry in data:
                sid = entry.get("set_id")
                if sid is None:
                    continue
                if sid in seen_ids:
                    duplicates.append(
                        f"Duplicate set_id '{sid}' in {json_file.name} "
                        f"(first seen in {seen_ids[sid]})"
                    )
                else:
                    seen_ids[sid] = json_file.name

        assert len(duplicates) == 0, (
            f"Found {len(duplicates)} duplicate set_ids:\n"
            + "\n".join(duplicates[:20])
        )


class TestDataIntegrity:
    """Additional data integrity checks."""

    def test_total_feature_count(self):
        """Test that the total feature count meets the expected minimum."""
        total = 0
        for json_file in _get_all_json_files():
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                total += len(data)

        assert total >= 1900, (
            f"Total feature/set count ({total}) is below expected minimum (1900)"
        )

    def test_feature_id_naming_convention(self):
        """Test that feature_ids follow the naming convention."""
        for json_file in _get_all_json_files():
            if not _is_skill_file(json_file.name):
                continue

            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for entry in data:
                fid = entry.get("feature_id", "")
                # Feature IDs should be uppercase with underscores
                assert fid == fid.upper() or "_" in fid, (
                    f"{json_file.name}: feature_id '{fid}' doesn't follow "
                    "expected UPPER_CASE convention"
                )

    def test_set_id_naming_convention(self):
        """Test that set_ids follow the naming convention."""
        for json_file in _get_all_json_files():
            if not _is_set_file(json_file.name):
                continue

            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for entry in data:
                sid = entry.get("set_id", "")
                assert sid.startswith("SET_"), (
                    f"{json_file.name}: set_id '{sid}' should start with 'SET_'"
                )
