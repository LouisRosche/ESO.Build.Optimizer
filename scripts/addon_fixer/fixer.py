"""
Main addon fixer orchestrator.

Coordinates all fixing operations: manifest updates, Lua transformation,
XML fixes, dependency validation, and packaging.
"""

import logging
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .constants import CURRENT_API_VERSION, REPLACEMENT_RECOMMENDATIONS
from .manifest import ManifestParser, ManifestFixer, ManifestData
from .lua_analyzer import LuaAnalyzer, LuaTransformer, LuaAnalysisResult
from .xml_fixer import XMLAnalyzer, XMLTransformer, XMLAnalysisResult
from .validator import validate_addon, ValidationResult
from .migrations import MigrationDatabase

logger = logging.getLogger(__name__)


@dataclass
class FixerConfig:
    """Configuration for the addon fixer."""
    update_api_version: bool = True
    fix_libstub: bool = True
    fix_deprecated_functions: bool = True
    fix_font_paths: bool = True
    fix_xml_issues: bool = True
    add_nil_guards: bool = False  # More aggressive, disabled by default
    validate_dependencies: bool = True
    create_backup: bool = True
    dry_run: bool = False


@dataclass
class FileFixResult:
    """Result of fixing a single file."""
    file_path: Path
    file_type: str  # "lua", "xml", "manifest"
    changes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    was_modified: bool = False


@dataclass
class AddonFixResult:
    """Result of fixing an entire addon."""
    addon_path: Path
    addon_name: str
    success: bool = True
    manifest_result: Optional[FileFixResult] = None
    lua_results: list[FileFixResult] = field(default_factory=list)
    xml_results: list[FileFixResult] = field(default_factory=list)
    validation_result: Optional[ValidationResult] = None
    backup_path: Optional[Path] = None
    package_path: Optional[Path] = None
    total_changes: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class AddonFixer:
    """Main addon fixer class that orchestrates all fixes."""

    def __init__(self, config: Optional[FixerConfig] = None):
        """Initialize the addon fixer."""
        self.config = config or FixerConfig()
        self.migration_db = MigrationDatabase()
        self.lua_analyzer = LuaAnalyzer(self.migration_db)
        self.lua_transformer = LuaTransformer(self.migration_db)
        self.xml_analyzer = XMLAnalyzer()
        self.xml_transformer = XMLTransformer()

    def analyze(self, addon_path: Path) -> AddonFixResult:
        """Analyze an addon without making changes."""
        addon_path = Path(addon_path)
        result = AddonFixResult(
            addon_path=addon_path,
            addon_name=addon_path.name,
        )

        # Check for replacement recommendations
        if addon_path.name in REPLACEMENT_RECOMMENDATIONS:
            result.recommendations.extend(REPLACEMENT_RECOMMENDATIONS[addon_path.name])
            result.warnings.append(
                f"This addon ({addon_path.name}) is recommended for replacement, not repair."
            )

        # Analyze manifest
        manifest_path = addon_path / f"{addon_path.name}.txt"
        if manifest_path.exists():
            manifest_result = self._analyze_manifest(manifest_path)
            result.manifest_result = manifest_result
            if manifest_result.errors:
                result.errors.extend(manifest_result.errors)

        # Analyze Lua files
        for lua_file in addon_path.rglob("*.lua"):
            lua_result = self._analyze_lua(lua_file)
            result.lua_results.append(lua_result)
            if lua_result.errors:
                result.errors.extend(lua_result.errors)

        # Analyze XML files
        for xml_file in addon_path.rglob("*.xml"):
            xml_result = self._analyze_xml(xml_file)
            result.xml_results.append(xml_result)
            if xml_result.errors:
                result.errors.extend(xml_result.errors)

        # Validate dependencies
        if self.config.validate_dependencies:
            result.validation_result = validate_addon(addon_path)
            if result.validation_result.errors:
                result.errors.extend(result.validation_result.errors)
            result.warnings.extend(result.validation_result.warnings)

        # Calculate total potential changes
        result.total_changes = (
            len(result.manifest_result.changes if result.manifest_result else []) +
            sum(len(r.changes) for r in result.lua_results) +
            sum(len(r.changes) for r in result.xml_results)
        )

        result.success = len(result.errors) == 0

        return result

    def fix(self, addon_path: Path, output_path: Optional[Path] = None) -> AddonFixResult:
        """Fix an addon and optionally package it."""
        addon_path = Path(addon_path)
        result = AddonFixResult(
            addon_path=addon_path,
            addon_name=addon_path.name,
        )

        # Check for replacement recommendations
        if addon_path.name in REPLACEMENT_RECOMMENDATIONS:
            result.recommendations.extend(REPLACEMENT_RECOMMENDATIONS[addon_path.name])
            result.warnings.append(
                f"This addon ({addon_path.name}) is not recommended for automated repair."
            )
            # Still allow fixing if user insists

        # Create backup if enabled
        if self.config.create_backup and not self.config.dry_run:
            result.backup_path = self._create_backup(addon_path)

        try:
            # Fix manifest
            manifest_path = addon_path / f"{addon_path.name}.txt"
            if manifest_path.exists():
                result.manifest_result = self._fix_manifest(manifest_path)
                result.total_changes += len(result.manifest_result.changes)

            # Fix Lua files
            for lua_file in addon_path.rglob("*.lua"):
                lua_result = self._fix_lua(lua_file)
                result.lua_results.append(lua_result)
                result.total_changes += len(lua_result.changes)

            # Fix XML files
            if self.config.fix_xml_issues:
                for xml_file in addon_path.rglob("*.xml"):
                    xml_result = self._fix_xml(xml_file)
                    result.xml_results.append(xml_result)
                    result.total_changes += len(xml_result.changes)

            # Validate after fixes
            if self.config.validate_dependencies:
                result.validation_result = validate_addon(addon_path)
                result.warnings.extend(result.validation_result.warnings)

            # Package if output path specified
            if output_path and not self.config.dry_run:
                result.package_path = self._package_addon(addon_path, output_path)

            result.success = True

        except Exception as e:
            logger.error(f"Error fixing addon: {e}")
            result.errors.append(str(e))
            result.success = False

            # Restore from backup on failure
            if result.backup_path and not self.config.dry_run:
                self._restore_backup(result.backup_path, addon_path)

        return result

    def _analyze_manifest(self, manifest_path: Path) -> FileFixResult:
        """Analyze manifest file for issues."""
        result = FileFixResult(file_path=manifest_path, file_type="manifest")

        parser = ManifestParser(manifest_path)
        data = parser.parse()

        # Check for issues
        if data.validation_errors:
            result.errors.extend(data.validation_errors)

        if data.encoding_issues:
            result.changes.append("Fix encoding issues")

        # Check API version
        if data.api_version:
            max_version = max(data.api_version)
            if max_version < CURRENT_API_VERSION:
                result.changes.append(
                    f"Update APIVersion from {max_version} to {CURRENT_API_VERSION}"
                )

        # Check for LibStub dependency
        if "LibStub" in data.depends_on:
            result.changes.append("Remove LibStub from dependencies")

        return result

    def _analyze_lua(self, lua_path: Path) -> FileFixResult:
        """Analyze Lua file for issues."""
        result = FileFixResult(file_path=lua_path, file_type="lua")

        analysis = self.lua_analyzer.analyze_file(lua_path)

        for issue in analysis.issues:
            if issue.auto_fixable:
                result.changes.append(f"Fix: {issue.message}")
            else:
                if issue.severity == "error":
                    result.errors.append(f"Line {issue.line_number}: {issue.message}")
                else:
                    result.changes.append(f"Manual fix needed: {issue.message}")

        return result

    def _analyze_xml(self, xml_path: Path) -> FileFixResult:
        """Analyze XML file for issues."""
        result = FileFixResult(file_path=xml_path, file_type="xml")

        analysis = self.xml_analyzer.analyze_file(xml_path)

        for issue in analysis.issues:
            if issue.auto_fixable:
                result.changes.append(f"Fix: {issue.message}")
            else:
                if issue.severity == "error":
                    result.errors.append(f"Line {issue.line_number}: {issue.message}")
                else:
                    result.changes.append(f"Manual fix needed: {issue.message}")

        return result

    def _fix_manifest(self, manifest_path: Path) -> FileFixResult:
        """Fix manifest file issues."""
        result = FileFixResult(file_path=manifest_path, file_type="manifest")

        parser = ManifestParser(manifest_path)
        data = parser.parse()

        if self.config.update_api_version or data.encoding_issues:
            fixer = ManifestFixer(data)
            content, changes = fixer.fix_all()
            result.changes = changes

            if changes and not self.config.dry_run:
                # Write with proper line endings
                with open(manifest_path, "w", encoding="utf-8", newline="\r\n") as f:
                    f.write(content)
                result.was_modified = True

        return result

    def _fix_lua(self, lua_path: Path) -> FileFixResult:
        """Fix Lua file issues."""
        result = FileFixResult(file_path=lua_path, file_type="lua")

        _, changes = self.lua_transformer.fix_file(lua_path, dry_run=self.config.dry_run)
        result.changes = changes
        result.was_modified = len(changes) > 0 and not self.config.dry_run

        return result

    def _fix_xml(self, xml_path: Path) -> FileFixResult:
        """Fix XML file issues."""
        result = FileFixResult(file_path=xml_path, file_type="xml")

        _, changes = self.xml_transformer.fix_file(xml_path, dry_run=self.config.dry_run)
        result.changes = changes
        result.was_modified = len(changes) > 0 and not self.config.dry_run

        return result

    def _create_backup(self, addon_path: Path) -> Path:
        """Create a backup of the addon folder."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{addon_path.name}_backup_{timestamp}"
        backup_path = addon_path.parent / backup_name

        shutil.copytree(addon_path, backup_path)
        logger.info(f"Created backup at: {backup_path}")

        return backup_path

    def _restore_backup(self, backup_path: Path, original_path: Path) -> None:
        """Restore addon from backup."""
        if original_path.exists():
            shutil.rmtree(original_path)
        shutil.copytree(backup_path, original_path)
        logger.info(f"Restored from backup: {backup_path}")

    def _package_addon(self, addon_path: Path, output_path: Path) -> Path:
        """Package addon into a zip file for distribution."""
        output_path = Path(output_path)

        # Create proper addon structure
        addon_name = addon_path.name
        zip_name = f"{addon_name}.zip"
        zip_path = output_path / zip_name

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in addon_path.rglob("*"):
                if file_path.is_file():
                    # Skip backup files and temp files
                    if "_backup_" in str(file_path) or file_path.suffix in [".bak", ".tmp"]:
                        continue

                    # Create proper archive path (AddonName/file.ext)
                    arcname = addon_name / file_path.relative_to(addon_path)
                    zf.write(file_path, arcname)

        logger.info(f"Created package: {zip_path}")
        return zip_path


def analyze_addon(addon_path: Path, config: Optional[FixerConfig] = None) -> AddonFixResult:
    """Convenience function to analyze an addon."""
    fixer = AddonFixer(config)
    return fixer.analyze(addon_path)


def fix_addon(
    addon_path: Path,
    output_path: Optional[Path] = None,
    config: Optional[FixerConfig] = None
) -> AddonFixResult:
    """Convenience function to fix an addon."""
    fixer = AddonFixer(config)
    return fixer.fix(addon_path, output_path)
