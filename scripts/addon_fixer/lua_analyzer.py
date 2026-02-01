"""
Lua code analyzer and transformer for ESO addon fixer.

Analyzes Lua files for deprecated API usage, LibStub patterns,
and other issues. Provides automated fixes.
"""

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .migrations import MigrationDatabase, MigrationType, COMMON_PATTERNS, NIL_GUARD_TEMPLATES
from .constants import LIBRARY_GLOBALS, FONT_EXTENSIONS_OLD, FONT_EXTENSION_NEW

logger = logging.getLogger(__name__)


@dataclass
class LuaIssue:
    """Represents an issue found in Lua code."""
    file_path: Path
    line_number: int
    column: int
    issue_type: str
    message: str
    old_code: str
    suggested_fix: Optional[str] = None
    severity: str = "warning"  # warning, error, info
    auto_fixable: bool = False


@dataclass
class LuaAnalysisResult:
    """Result of analyzing a Lua file."""
    file_path: Path
    issues: list[LuaIssue] = field(default_factory=list)
    deprecated_functions: list[str] = field(default_factory=list)
    libstub_usages: list[tuple[int, str]] = field(default_factory=list)
    font_paths: list[tuple[int, str]] = field(default_factory=list)
    potential_nil_calls: list[tuple[int, str]] = field(default_factory=list)


class LuaAnalyzer:
    """Analyze Lua files for ESO addon issues."""

    # Patterns for analysis
    LIBSTUB_PATTERN = re.compile(
        r'LibStub\s*\(\s*["\']([^"\']+)["\']\s*(?:,\s*\w+)?\s*\)',
        re.MULTILINE
    )
    LIBSTUB_GETLIB_PATTERN = re.compile(
        r'LibStub\s*:\s*GetLibrary\s*\(\s*["\']([^"\']+)["\']\s*\)',
        re.MULTILINE
    )
    FUNCTION_CALL_PATTERN = re.compile(
        r'\b([A-Z][a-zA-Z0-9_]*)\s*\(',
        re.MULTILINE
    )
    FONT_PATH_PATTERN = re.compile(
        r'["\']([^"\']+)\.(ttf|otf)(\|[^"\']*)?["\']',
        re.IGNORECASE | re.MULTILINE
    )
    STRING_LITERAL_PATTERN = re.compile(
        r'(["\'])(?:(?!\1)[^\\]|\\.)*\1|--\[\[[\s\S]*?\]\]|--[^\n]*',
        re.MULTILINE
    )

    def __init__(self, migration_db: Optional[MigrationDatabase] = None):
        """Initialize analyzer with migration database."""
        self.migration_db = migration_db or MigrationDatabase()
        self.deprecated_funcs = set(self.migration_db.get_all_deprecated_functions())

    def analyze_file(self, file_path: Path) -> LuaAnalysisResult:
        """Analyze a single Lua file for issues."""
        result = LuaAnalysisResult(file_path=file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="windows-1252") as f:
                    content = f.read()
                result.issues.append(LuaIssue(
                    file_path=file_path,
                    line_number=0,
                    column=0,
                    issue_type="encoding",
                    message="File uses Windows-1252 encoding, should be UTF-8",
                    old_code="",
                    severity="warning",
                    auto_fixable=True,
                ))
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                return result

        # Create mask for string literals (to avoid false positives)
        string_mask = self._create_string_mask(content)

        # Analyze for various issues
        self._find_libstub_usage(content, string_mask, file_path, result)
        self._find_deprecated_functions(content, string_mask, file_path, result)
        self._find_font_paths(content, file_path, result)
        self._find_potential_nil_calls(content, string_mask, file_path, result)

        return result

    def _create_string_mask(self, content: str) -> list[bool]:
        """Create a mask indicating which positions are inside string literals."""
        mask = [False] * len(content)

        for match in self.STRING_LITERAL_PATTERN.finditer(content):
            for i in range(match.start(), match.end()):
                if i < len(mask):
                    mask[i] = True

        return mask

    def _is_in_string(self, pos: int, mask: list[bool]) -> bool:
        """Check if position is inside a string literal or comment."""
        return pos < len(mask) and mask[pos]

    def _find_libstub_usage(
        self,
        content: str,
        mask: list[bool],
        file_path: Path,
        result: LuaAnalysisResult
    ) -> None:
        """Find LibStub usage patterns."""
        lines = content.split("\n")

        # Find LibStub() calls
        for match in self.LIBSTUB_PATTERN.finditer(content):
            if self._is_in_string(match.start(), mask):
                continue

            line_num = content[:match.start()].count("\n") + 1
            lib_name = match.group(1)
            full_match = match.group(0)

            result.libstub_usages.append((line_num, lib_name))

            # Get the replacement global variable
            global_var = LIBRARY_GLOBALS.get(lib_name, lib_name.replace("-", ""))

            result.issues.append(LuaIssue(
                file_path=file_path,
                line_number=line_num,
                column=match.start() - content.rfind("\n", 0, match.start()),
                issue_type="libstub",
                message=f"LibStub is deprecated, use global variable instead",
                old_code=full_match,
                suggested_fix=global_var,
                severity="warning",
                auto_fixable=True,
            ))

        # Find LibStub:GetLibrary() calls
        for match in self.LIBSTUB_GETLIB_PATTERN.finditer(content):
            if self._is_in_string(match.start(), mask):
                continue

            line_num = content[:match.start()].count("\n") + 1
            lib_name = match.group(1)

            result.libstub_usages.append((line_num, lib_name))

            global_var = LIBRARY_GLOBALS.get(lib_name, lib_name.replace("-", ""))

            result.issues.append(LuaIssue(
                file_path=file_path,
                line_number=line_num,
                column=match.start() - content.rfind("\n", 0, match.start()),
                issue_type="libstub",
                message=f"LibStub:GetLibrary is deprecated",
                old_code=match.group(0),
                suggested_fix=global_var,
                severity="warning",
                auto_fixable=True,
            ))

    def _find_deprecated_functions(
        self,
        content: str,
        mask: list[bool],
        file_path: Path,
        result: LuaAnalysisResult
    ) -> None:
        """Find deprecated function calls."""
        for match in self.FUNCTION_CALL_PATTERN.finditer(content):
            if self._is_in_string(match.start(), mask):
                continue

            func_name = match.group(1)

            if func_name in self.deprecated_funcs:
                line_num = content[:match.start()].count("\n") + 1
                migration = self.migration_db.get_function_migration(func_name)

                result.deprecated_functions.append(func_name)

                suggested_fix = None
                if migration:
                    if migration.new_name:
                        suggested_fix = migration.new_name
                    elif migration.replacement_code:
                        suggested_fix = migration.replacement_code

                severity = "error" if migration and migration.migration_type == MigrationType.REMOVED else "warning"

                result.issues.append(LuaIssue(
                    file_path=file_path,
                    line_number=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    issue_type="deprecated_function",
                    message=f"Deprecated function: {func_name}" + (f" - {migration.notes}" if migration and migration.notes else ""),
                    old_code=func_name,
                    suggested_fix=suggested_fix,
                    severity=severity,
                    auto_fixable=migration is not None and migration.new_name is not None,
                ))

    def _find_font_paths(
        self,
        content: str,
        file_path: Path,
        result: LuaAnalysisResult
    ) -> None:
        """Find font paths that need migration to .slug format."""
        for match in self.FONT_PATH_PATTERN.finditer(content):
            line_num = content[:match.start()].count("\n") + 1
            font_path = match.group(0)

            result.font_paths.append((line_num, font_path))

            # Suggest the fixed path
            suggested = font_path.replace(".ttf", ".slug").replace(".otf", ".slug")
            suggested = suggested.replace(".TTF", ".slug").replace(".OTF", ".slug")

            result.issues.append(LuaIssue(
                file_path=file_path,
                line_number=line_num,
                column=match.start() - content.rfind("\n", 0, match.start()),
                issue_type="font_path",
                message="Font path uses old TTF/OTF format, should use .slug (Update 41+)",
                old_code=font_path,
                suggested_fix=suggested,
                severity="warning",
                auto_fixable=True,
            ))

    def _find_potential_nil_calls(
        self,
        content: str,
        mask: list[bool],
        file_path: Path,
        result: LuaAnalysisResult
    ) -> None:
        """Find function calls that might be nil in newer API versions."""
        # Look for potentially problematic patterns
        # These are functions that may not exist in all versions
        potentially_nil_funcs = [
            "GetUnitVeteranRank",
            "GetUnitVeteranPoints",
            "IsUnitVeteran",
            "GetPlayerVeteranRank",
            "GetMaxVeteranRank",
            "GetSlotBoundId",  # May not exist for all slot types
            "GetAbilityUpgradeLines",  # Signature varies
        ]

        for match in self.FUNCTION_CALL_PATTERN.finditer(content):
            if self._is_in_string(match.start(), mask):
                continue

            func_name = match.group(1)

            if func_name in potentially_nil_funcs:
                line_num = content[:match.start()].count("\n") + 1

                # Check if already guarded
                line_start = content.rfind("\n", 0, match.start()) + 1
                line_end = content.find("\n", match.start())
                line_content = content[line_start:line_end if line_end != -1 else len(content)]

                # Simple check for existing guard
                if "if " + func_name in line_content or func_name + " and" in line_content:
                    continue

                result.potential_nil_calls.append((line_num, func_name))

                result.issues.append(LuaIssue(
                    file_path=file_path,
                    line_number=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    issue_type="potential_nil",
                    message=f"Function {func_name} may be nil in current API, consider adding guard",
                    old_code=func_name + "(...)",
                    suggested_fix=f"if {func_name} then {func_name}(...) end",
                    severity="info",
                    auto_fixable=False,
                ))


class LuaTransformer:
    """Transform Lua code to fix issues."""

    def __init__(self, migration_db: Optional[MigrationDatabase] = None):
        """Initialize transformer with migration database."""
        self.migration_db = migration_db or MigrationDatabase()
        self.changes_made: list[str] = []

    def fix_file(self, file_path: Path, dry_run: bool = False) -> tuple[str, list[str]]:
        """Fix issues in a Lua file and return the fixed content."""
        self.changes_made = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="windows-1252") as f:
                content = f.read()
            self.changes_made.append("Converted encoding from Windows-1252 to UTF-8")

        # Apply fixes in order
        content = self._fix_libstub(content)
        content = self._fix_deprecated_functions(content)
        content = self._fix_font_paths(content)

        if not dry_run and self.changes_made:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        return content, self.changes_made

    def _fix_libstub(self, content: str) -> str:
        """Replace LibStub patterns with global variable access."""
        # Pattern for LibStub("LibName") or LibStub("LibName", true)
        def replace_libstub(match):
            lib_name = match.group(1)
            global_var = LIBRARY_GLOBALS.get(lib_name, lib_name.replace("-", "").replace(".", ""))
            self.changes_made.append(f"Replaced LibStub(\"{lib_name}\") with {global_var}")
            return global_var

        # Replace LibStub() calls
        pattern = r'LibStub\s*\(\s*["\']([^"\']+)["\']\s*(?:,\s*\w+)?\s*\)'
        content = re.sub(pattern, replace_libstub, content)

        # Replace LibStub:GetLibrary() calls
        pattern = r'LibStub\s*:\s*GetLibrary\s*\(\s*["\']([^"\']+)["\']\s*\)'
        content = re.sub(pattern, replace_libstub, content)

        # Add hybrid fallback pattern at the top if LibStub was used
        # This provides backward compatibility
        if "LibStub" in content and "LibStub and LibStub" not in content:
            # Find all unique libraries used
            libs_used = set(re.findall(r'= (Lib\w+)', content))
            for lib in libs_used:
                if lib in LIBRARY_GLOBALS.values():
                    # Already using global, skip
                    continue

        return content

    def _fix_deprecated_functions(self, content: str) -> str:
        """Replace deprecated function calls with their replacements."""
        for func_name, migration in self.migration_db.function_migrations.items():
            if migration.migration_type == MigrationType.RENAMED and migration.new_name:
                # Simple rename - use word boundaries
                pattern = rf'\b{re.escape(func_name)}\b'

                if re.search(pattern, content):
                    content = re.sub(pattern, migration.new_name, content)
                    self.changes_made.append(
                        f"Renamed {func_name} to {migration.new_name}"
                    )

        return content

    def _fix_font_paths(self, content: str) -> str:
        """Fix font paths from .ttf/.otf to .slug format."""
        def replace_font(match):
            old_path = match.group(0)
            new_path = re.sub(r'\.(ttf|otf)', '.slug', old_path, flags=re.IGNORECASE)
            if new_path != old_path:
                self.changes_made.append(f"Updated font path: {old_path} → {new_path}")
            return new_path

        pattern = r'["\'][^"\']+\.(ttf|otf)(?:\|[^"\']*)?["\']'
        content = re.sub(pattern, replace_font, content, flags=re.IGNORECASE)

        return content

    def add_nil_guards(self, content: str, func_names: list[str]) -> str:
        """Add nil guards for specified function names."""
        for func_name in func_names:
            # Find calls to this function
            pattern = rf'(\s*)({re.escape(func_name)})\s*\(([^)]*)\)'

            def add_guard(match):
                indent = match.group(1)
                name = match.group(2)
                args = match.group(3)

                # Check if already guarded
                if f"if {name}" in content:
                    return match.group(0)

                self.changes_made.append(f"Added nil guard for {name}")
                return f"{indent}if {name} then {name}({args}) end"

            content = re.sub(pattern, add_guard, content)

        return content


def analyze_lua_file(file_path: Path) -> LuaAnalysisResult:
    """Convenience function to analyze a Lua file."""
    analyzer = LuaAnalyzer()
    return analyzer.analyze_file(file_path)


def fix_lua_file(file_path: Path, dry_run: bool = False) -> tuple[str, list[str]]:
    """Convenience function to fix a Lua file."""
    transformer = LuaTransformer()
    return transformer.fix_file(file_path, dry_run)
