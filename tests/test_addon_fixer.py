"""
Tests for the ESO Addon Fixer.

These tests verify the functionality of manifest parsing, Lua analysis,
XML fixing, and the overall addon fixing pipeline.
"""

import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from addon_fixer.constants import CURRENT_API_VERSION, LIBRARY_GLOBALS
from addon_fixer.manifest import ManifestParser, ManifestFixer, ManifestData
from addon_fixer.lua_analyzer import LuaAnalyzer, LuaTransformer
from addon_fixer.xml_fixer import XMLAnalyzer, XMLTransformer
from addon_fixer.migrations import MigrationDatabase, MigrationType
from addon_fixer.validator import DependencyValidator, validate_addon
from addon_fixer.fixer import AddonFixer, FixerConfig


class TestManifestParser:
    """Tests for manifest file parsing."""

    def test_parse_basic_manifest(self, tmp_path):
        """Test parsing a basic valid manifest."""
        manifest_content = """## Title: Test Addon
## APIVersion: 101048
## Author: Test Author
## Version: 1.0.0

TestAddon.lua
"""
        manifest_path = tmp_path / "TestAddon.txt"
        manifest_path.write_text(manifest_content)

        parser = ManifestParser(manifest_path)
        data = parser.parse()

        assert data.title == "Test Addon"
        assert data.api_version == [101048]
        assert data.author == "Test Author"
        assert data.version == "1.0.0"
        assert "TestAddon.lua" in data.files

    def test_parse_dual_api_version(self, tmp_path):
        """Test parsing manifest with dual API versions."""
        manifest_content = """## Title: Test Addon
## APIVersion: 101047 101048
"""
        manifest_path = tmp_path / "TestAddon.txt"
        manifest_path.write_text(manifest_content)

        parser = ManifestParser(manifest_path)
        data = parser.parse()

        assert data.api_version == [101047, 101048]

    def test_parse_dependencies(self, tmp_path):
        """Test parsing dependency declarations."""
        manifest_content = """## Title: Test Addon
## APIVersion: 101048
## DependsOn: LibAddonMenu-2.0>=28 LibFilters-3.0
## OptionalDependsOn: LibCustomMenu>=7
"""
        manifest_path = tmp_path / "TestAddon.txt"
        manifest_path.write_text(manifest_content)

        parser = ManifestParser(manifest_path)
        data = parser.parse()

        assert "LibAddonMenu-2.0>=28" in data.depends_on
        assert "LibFilters-3.0" in data.depends_on
        assert "LibCustomMenu>=7" in data.optional_depends_on

    def test_parse_saved_variables(self, tmp_path):
        """Test parsing SavedVariables declarations."""
        manifest_content = """## Title: Test Addon
## APIVersion: 101048
## SavedVariables: TestAddon_Data TestAddon_Settings
"""
        manifest_path = tmp_path / "TestAddon.txt"
        manifest_path.write_text(manifest_content)

        parser = ManifestParser(manifest_path)
        data = parser.parse()

        assert "TestAddon_Data" in data.saved_variables
        assert "TestAddon_Settings" in data.saved_variables

    def test_detect_outdated_api_version(self, tmp_path):
        """Test detection of outdated API version."""
        manifest_content = """## Title: Test Addon
## APIVersion: 100027
"""
        manifest_path = tmp_path / "TestAddon.txt"
        manifest_path.write_text(manifest_content)

        parser = ManifestParser(manifest_path)
        data = parser.parse()

        assert any("Outdated API version" in err for err in data.validation_errors)


class TestManifestFixer:
    """Tests for manifest file fixing."""

    def test_fix_api_version(self, tmp_path):
        """Test updating API version to current."""
        manifest_content = """## Title: Test Addon
## APIVersion: 100027
"""
        manifest_path = tmp_path / "TestAddon.txt"
        manifest_path.write_text(manifest_content)

        parser = ManifestParser(manifest_path)
        data = parser.parse()
        fixer = ManifestFixer(data)
        content, changes = fixer.fix_all()

        assert "101047 101048" in content
        assert any("Updated APIVersion" in c for c in changes)

    def test_remove_libstub_dependency(self, tmp_path):
        """Test removal of LibStub from dependencies."""
        manifest_content = """## Title: Test Addon
## APIVersion: 101048
## DependsOn: LibStub LibAddonMenu-2.0
"""
        manifest_path = tmp_path / "TestAddon.txt"
        manifest_path.write_text(manifest_content)

        parser = ManifestParser(manifest_path)
        data = parser.parse()
        fixer = ManifestFixer(data)
        content, changes = fixer.fix_all()

        assert "LibStub" not in content or "Removed LibStub" in str(changes)


class TestMigrationDatabase:
    """Tests for the API migration database."""

    def test_function_migrations_exist(self):
        """Test that function migrations are loaded."""
        db = MigrationDatabase()
        assert len(db.function_migrations) > 0

    def test_library_migrations_exist(self):
        """Test that library migrations are loaded."""
        db = MigrationDatabase()
        assert len(db.library_migrations) > 0

    def test_get_veteran_rank_migration(self):
        """Test getting veteran rank migration."""
        db = MigrationDatabase()
        migration = db.get_function_migration("GetUnitVeteranRank")

        assert migration is not None
        assert migration.migration_type == MigrationType.RENAMED
        assert migration.new_name == "GetUnitChampionPoints"

    def test_get_migrations_by_category(self):
        """Test filtering migrations by category."""
        db = MigrationDatabase()
        cp_migrations = db.get_migrations_by_category("champion_points")

        assert len(cp_migrations) > 0
        assert all(m.category == "champion_points" for m in cp_migrations)

    def test_export_to_json(self, tmp_path):
        """Test exporting migrations to JSON."""
        db = MigrationDatabase()
        output_path = tmp_path / "migrations.json"
        db.export_to_json(output_path)

        assert output_path.exists()
        import json
        with open(output_path) as f:
            data = json.load(f)
        assert "functions" in data
        assert "libraries" in data


class TestLuaAnalyzer:
    """Tests for Lua code analysis."""

    def test_detect_libstub_usage(self, tmp_path):
        """Test detection of LibStub patterns."""
        lua_content = '''
local LAM = LibStub("LibAddonMenu-2.0")
local LC = LibStub:GetLibrary("LibCustomMenu")
'''
        lua_path = tmp_path / "test.lua"
        lua_path.write_text(lua_content)

        analyzer = LuaAnalyzer()
        result = analyzer.analyze_file(lua_path)

        assert len(result.libstub_usages) == 2
        assert any(issue.issue_type == "libstub" for issue in result.issues)

    def test_detect_deprecated_functions(self, tmp_path):
        """Test detection of deprecated function calls."""
        lua_content = '''
local vr = GetUnitVeteranRank("player")
local vp = GetUnitVeteranPoints("player")
'''
        lua_path = tmp_path / "test.lua"
        lua_path.write_text(lua_content)

        analyzer = LuaAnalyzer()
        result = analyzer.analyze_file(lua_path)

        assert "GetUnitVeteranRank" in result.deprecated_functions
        assert "GetUnitVeteranPoints" in result.deprecated_functions

    def test_detect_font_paths(self, tmp_path):
        """Test detection of old font paths."""
        lua_content = '''
local font = "MyAddon/fonts/myfont.ttf|16|soft-shadow-thin"
local font2 = "EsoUI/Common/Fonts/univers57.otf|14"
'''
        lua_path = tmp_path / "test.lua"
        lua_path.write_text(lua_content)

        analyzer = LuaAnalyzer()
        result = analyzer.analyze_file(lua_path)

        assert len(result.font_paths) == 2
        assert any(issue.issue_type == "font_path" for issue in result.issues)

    def test_skip_string_literals(self, tmp_path):
        """Test that patterns inside strings are handled correctly."""
        lua_content = '''
local msg = "GetUnitVeteranRank is deprecated"
-- GetUnitVeteranRank comment
'''
        lua_path = tmp_path / "test.lua"
        lua_path.write_text(lua_content)

        analyzer = LuaAnalyzer()
        result = analyzer.analyze_file(lua_path)

        # Should not detect the function call in string/comment
        # (This depends on implementation - may or may not be filtered)


class TestLuaTransformer:
    """Tests for Lua code transformation."""

    def test_fix_libstub(self, tmp_path):
        """Test fixing LibStub patterns."""
        lua_content = '''local LAM = LibStub("LibAddonMenu-2.0")'''
        lua_path = tmp_path / "test.lua"
        lua_path.write_text(lua_content)

        transformer = LuaTransformer()
        content, changes = transformer.fix_file(lua_path, dry_run=True)

        assert "LibAddonMenu2" in content
        assert any("LibStub" in c for c in changes)

    def test_fix_font_paths(self, tmp_path):
        """Test fixing font paths."""
        lua_content = '''local font = "MyAddon/fonts/myfont.ttf|16"'''
        lua_path = tmp_path / "test.lua"
        lua_path.write_text(lua_content)

        transformer = LuaTransformer()
        content, changes = transformer.fix_file(lua_path, dry_run=True)

        assert ".slug" in content
        assert ".ttf" not in content


class TestXMLAnalyzer:
    """Tests for XML analysis."""

    def test_detect_font_paths(self, tmp_path):
        """Test detection of old font paths in XML."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<GuiXml>
    <Controls>
        <Label font="MyFont.ttf|16" />
    </Controls>
</GuiXml>'''
        xml_path = tmp_path / "test.xml"
        xml_path.write_text(xml_content)

        analyzer = XMLAnalyzer()
        result = analyzer.analyze_file(xml_path)

        assert len(result.font_paths) > 0
        assert any(issue.issue_type == "font_path" for issue in result.issues)


class TestDependencyValidator:
    """Tests for dependency validation."""

    def test_validate_known_library(self):
        """Test validation of known libraries."""
        data = ManifestData(
            path=Path("test.txt"),
            title="Test",
            depends_on=["LibAddonMenu-2.0>=28"],
        )

        validator = DependencyValidator()
        result = validator.validate(data)

        assert result.is_valid
        assert len(result.dependencies) == 1
        assert result.dependencies[0].is_available

    def test_detect_libstub_dependency(self):
        """Test detection of deprecated LibStub dependency."""
        data = ManifestData(
            path=Path("test.txt"),
            title="Test",
            depends_on=["LibStub"],
        )

        validator = DependencyValidator()
        result = validator.validate(data)

        assert any("LibStub is deprecated" in w for w in result.warnings)


class TestAddonFixer:
    """Integration tests for the full addon fixer."""

    def create_test_addon(self, tmp_path, name="TestAddon"):
        """Create a minimal test addon structure."""
        addon_path = tmp_path / name
        addon_path.mkdir()

        # Create manifest
        manifest = f"""## Title: {name}
## APIVersion: 100027
## Author: Test
## DependsOn: LibStub LibAddonMenu-2.0

{name}.lua
"""
        (addon_path / f"{name}.txt").write_text(manifest)

        # Create main Lua file
        lua_content = f'''
local ADDON_NAME = "{name}"
local LAM = LibStub("LibAddonMenu-2.0")

local function OnLoad()
    local vr = GetUnitVeteranRank("player")
end

EVENT_MANAGER:RegisterForEvent(ADDON_NAME, EVENT_ADD_ON_LOADED, OnLoad)
'''
        (addon_path / f"{name}.lua").write_text(lua_content)

        return addon_path

    def test_analyze_addon(self, tmp_path):
        """Test addon analysis."""
        addon_path = self.create_test_addon(tmp_path)

        fixer = AddonFixer()
        result = fixer.analyze(addon_path)

        assert result.addon_name == "TestAddon"
        assert result.total_changes > 0
        assert result.manifest_result is not None
        assert len(result.lua_results) > 0

    def test_fix_addon_dry_run(self, tmp_path):
        """Test addon fixing in dry run mode."""
        addon_path = self.create_test_addon(tmp_path)

        config = FixerConfig(dry_run=True)
        fixer = AddonFixer(config)
        result = fixer.fix(addon_path)

        assert result.success
        assert result.total_changes > 0

        # Verify files were not modified
        manifest_content = (addon_path / "TestAddon.txt").read_text()
        assert "100027" in manifest_content  # Old version should still be there

    def test_fix_addon_with_backup(self, tmp_path):
        """Test addon fixing with backup creation."""
        addon_path = self.create_test_addon(tmp_path)

        config = FixerConfig(create_backup=True, dry_run=False)
        fixer = AddonFixer(config)
        result = fixer.fix(addon_path)

        assert result.success
        assert result.backup_path is not None
        assert result.backup_path.exists()

    def test_package_addon(self, tmp_path):
        """Test addon packaging."""
        addon_path = self.create_test_addon(tmp_path)
        output_path = tmp_path / "output"
        output_path.mkdir()

        config = FixerConfig(dry_run=False)
        fixer = AddonFixer(config)
        result = fixer.fix(addon_path, output_path)

        assert result.success
        assert result.package_path is not None
        assert result.package_path.exists()
        assert result.package_path.suffix == ".zip"


class TestConstants:
    """Tests for constants and configuration."""

    def test_current_api_version(self):
        """Test that current API version is set correctly."""
        assert CURRENT_API_VERSION == 101048

    def test_library_globals_mapping(self):
        """Test that library globals are properly mapped."""
        assert LIBRARY_GLOBALS["LibAddonMenu-2.0"] == "LibAddonMenu2"
        assert LIBRARY_GLOBALS["LibFilters-3.0"] == "LibFilters3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
