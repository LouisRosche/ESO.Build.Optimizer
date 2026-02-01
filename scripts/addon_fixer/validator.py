"""
Dependency validator for ESO addons.

Validates library dependencies, checks version requirements,
and identifies missing or outdated dependencies.
"""

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .constants import LIBRARY_VERSIONS, LIBRARY_GLOBALS
from .manifest import ManifestData, ManifestParser

logger = logging.getLogger(__name__)


@dataclass
class DependencyInfo:
    """Information about a dependency."""
    name: str
    required_version: Optional[int] = None
    is_optional: bool = False
    is_available: bool = False
    current_version: Optional[int] = None
    global_var: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of dependency validation."""
    addon_name: str
    is_valid: bool = True
    dependencies: list[DependencyInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class DependencyValidator:
    """Validate addon dependencies."""

    # Dependency pattern with optional version
    DEP_PATTERN = re.compile(r"([A-Za-z][\w-]*)(?:>=(\d+))?")

    def __init__(self, known_libraries: Optional[dict] = None):
        """Initialize validator with known library information."""
        self.known_libraries = known_libraries or LIBRARY_VERSIONS

    def validate(self, manifest_data: ManifestData) -> ValidationResult:
        """Validate all dependencies for an addon."""
        result = ValidationResult(addon_name=manifest_data.title)

        # Validate required dependencies
        for dep_str in manifest_data.depends_on:
            dep_info = self._parse_dependency(dep_str, is_optional=False)
            self._validate_dependency(dep_info, result)
            result.dependencies.append(dep_info)

        # Validate optional dependencies
        for dep_str in manifest_data.optional_depends_on:
            dep_info = self._parse_dependency(dep_str, is_optional=True)
            self._validate_dependency(dep_info, result)
            result.dependencies.append(dep_info)

        # Check for LibStub dependency (deprecated)
        for dep in result.dependencies:
            if dep.name == "LibStub":
                result.warnings.append(
                    "LibStub is deprecated since Summerset. "
                    "Use global variables instead (e.g., LibAddonMenu2)."
                )
                result.suggestions.append(
                    "Remove LibStub from DependsOn and update library access patterns."
                )

        # Set overall validity
        result.is_valid = len(result.errors) == 0

        return result

    def _parse_dependency(self, dep_str: str, is_optional: bool) -> DependencyInfo:
        """Parse a dependency string into DependencyInfo."""
        match = self.DEP_PATTERN.match(dep_str)
        if not match:
            return DependencyInfo(
                name=dep_str,
                is_optional=is_optional,
            )

        name = match.group(1)
        version = int(match.group(2)) if match.group(2) else None

        # Look up known library info
        lib_info = self.known_libraries.get(name, {})

        return DependencyInfo(
            name=name,
            required_version=version,
            is_optional=is_optional,
            is_available=name in self.known_libraries,
            current_version=lib_info.get("version"),
            global_var=lib_info.get("global") or LIBRARY_GLOBALS.get(name),
        )

    def _validate_dependency(
        self,
        dep_info: DependencyInfo,
        result: ValidationResult
    ) -> None:
        """Validate a single dependency."""
        # Check if dependency is known
        if not dep_info.is_available and not dep_info.is_optional:
            if dep_info.name not in ["LibStub"]:  # Skip LibStub warning here
                result.warnings.append(
                    f"Unknown required dependency: {dep_info.name}. "
                    "Verify it exists on ESOUI.com."
                )

        # Check version requirements
        if dep_info.required_version and dep_info.current_version:
            if dep_info.required_version > dep_info.current_version:
                result.errors.append(
                    f"Dependency {dep_info.name} requires version >={dep_info.required_version}, "
                    f"but current known version is {dep_info.current_version}."
                )

        # Suggest global variable if known
        if dep_info.global_var and not dep_info.is_optional:
            result.suggestions.append(
                f"Access {dep_info.name} via global variable: {dep_info.global_var}"
            )


class SavedVariablesValidator:
    """Validate SavedVariables declarations and usage."""

    def __init__(self):
        """Initialize the validator."""
        pass

    def validate_declaration(
        self,
        manifest_data: ManifestData,
        lua_content: str
    ) -> list[str]:
        """Validate SavedVariables are properly used."""
        issues = []

        # Check for ZO_SavedVars usage
        if manifest_data.saved_variables:
            for sv_name in manifest_data.saved_variables:
                # Check if SavedVariables name is used in code
                if sv_name not in lua_content:
                    issues.append(
                        f"SavedVariable '{sv_name}' declared in manifest but not found in code"
                    )

        # Check for ZO_SavedVars:New usage
        if "ZO_SavedVars:New" in lua_content:
            # Extract the first argument (table name)
            pattern = r'ZO_SavedVars:New(?:AccountWide|CharacterIdSettings)?\s*\(\s*["\'](\w+)["\']'
            for match in re.finditer(pattern, lua_content):
                table_name = match.group(1)
                if table_name not in manifest_data.saved_variables:
                    issues.append(
                        f"ZO_SavedVars uses '{table_name}' but it's not declared in manifest"
                    )

        return issues


class StructureValidator:
    """Validate addon folder structure."""

    REQUIRED_FILES = ["manifest"]  # Manifest file must exist

    def __init__(self):
        """Initialize the validator."""
        pass

    def validate(self, addon_path: Path) -> list[str]:
        """Validate addon folder structure."""
        issues = []

        if not addon_path.is_dir():
            issues.append(f"Addon path is not a directory: {addon_path}")
            return issues

        # Check for manifest file
        addon_name = addon_path.name
        manifest_path = addon_path / f"{addon_name}.txt"

        if not manifest_path.exists():
            issues.append(
                f"Missing manifest file: {addon_name}.txt "
                f"(must match folder name)"
            )

        # Check for at least one Lua file
        lua_files = list(addon_path.glob("*.lua")) + list(addon_path.glob("**/*.lua"))
        if not lua_files:
            issues.append("No Lua files found in addon")

        # Check for common structural issues
        if (addon_path / "libs").exists():
            issues.append(
                "Found 'libs' folder - consider using standalone library installations "
                "via Minion to avoid version conflicts"
            )

        return issues


def validate_addon(addon_path: Path) -> ValidationResult:
    """Convenience function to validate an entire addon."""
    addon_path = Path(addon_path)
    addon_name = addon_path.name

    # Parse manifest
    manifest_path = addon_path / f"{addon_name}.txt"
    parser = ManifestParser(manifest_path)
    manifest_data = parser.parse()

    # Run dependency validation
    dep_validator = DependencyValidator()
    result = dep_validator.validate(manifest_data)

    # Run structure validation
    struct_validator = StructureValidator()
    struct_issues = struct_validator.validate(addon_path)
    result.warnings.extend(struct_issues)

    # Run SavedVariables validation
    sv_validator = SavedVariablesValidator()

    # Read main Lua file
    main_lua = addon_path / f"{addon_name}.lua"
    if main_lua.exists():
        try:
            with open(main_lua, "r", encoding="utf-8") as f:
                lua_content = f.read()
        except UnicodeDecodeError:
            with open(main_lua, "r", encoding="windows-1252") as f:
                lua_content = f.read()

        sv_issues = sv_validator.validate_declaration(manifest_data, lua_content)
        result.warnings.extend(sv_issues)

    # Update validity based on all checks
    result.is_valid = len(result.errors) == 0

    return result
