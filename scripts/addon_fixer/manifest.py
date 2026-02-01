"""
Manifest parser and fixer for ESO addon .txt files.

Handles parsing, validation, and fixing of ESO addon manifest files.
The manifest file must match the addon folder name (e.g., MyAddon/MyAddon.txt).
"""

import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from .constants import (
    CURRENT_API_VERSION,
    DUAL_API_VERSION,
    MANIFEST_DIRECTIVES,
    LIBRARY_VERSIONS,
)

logger = logging.getLogger(__name__)


@dataclass
class ManifestData:
    """Parsed manifest data structure."""

    path: Path
    title: str = ""
    api_version: list[int] = field(default_factory=list)
    addon_version: Optional[int] = None
    version: str = ""
    author: str = ""
    description: str = ""
    depends_on: list[str] = field(default_factory=list)
    optional_depends_on: list[str] = field(default_factory=list)
    saved_variables: list[str] = field(default_factory=list)
    is_library: bool = False
    credits: str = ""
    files: list[str] = field(default_factory=list)
    raw_lines: list[str] = field(default_factory=list)
    encoding_issues: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)


class ManifestParser:
    """Parse ESO addon manifest files."""

    # Regex patterns for manifest directives
    DIRECTIVE_PATTERN = re.compile(r"^##\s*(\w+):\s*(.*)$")
    FILE_PATTERN = re.compile(r"^([^#\s].*\.(lua|xml))$", re.IGNORECASE)
    DEPENDENCY_PATTERN = re.compile(r"(\w[\w-]*(?:>=\d+)?)")

    def __init__(self, manifest_path: Path):
        """Initialize parser with manifest file path."""
        self.path = Path(manifest_path)
        self.data = ManifestData(path=self.path)

    def parse(self) -> ManifestData:
        """Parse the manifest file and return structured data."""
        if not self.path.exists():
            self.data.validation_errors.append(f"Manifest file not found: {self.path}")
            return self.data

        # Read file with encoding detection
        content = self._read_with_encoding()
        if content is None:
            return self.data

        # Parse lines
        for line_num, line in enumerate(content.splitlines(), 1):
            self._parse_line(line, line_num)

        # Validate required fields
        self._validate()

        return self.data

    def _read_with_encoding(self) -> Optional[str]:
        """Read file with proper encoding, detecting issues."""
        try:
            # Try UTF-8 first (preferred)
            with open(self.path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for BOM
            if content.startswith("\ufeff"):
                self.data.encoding_issues.append("File has UTF-8 BOM (should be UTF-8 without BOM)")
                content = content[1:]  # Strip BOM for parsing

            self.data.raw_lines = content.splitlines()
            return content

        except UnicodeDecodeError:
            # Try Windows-1252 (common for old addons)
            try:
                with open(self.path, "r", encoding="windows-1252") as f:
                    content = f.read()
                self.data.encoding_issues.append("File uses Windows-1252 encoding (should be UTF-8)")
                self.data.raw_lines = content.splitlines()
                return content
            except UnicodeDecodeError as e:
                self.data.validation_errors.append(f"Failed to decode file: {e}")
                return None

    def _parse_line(self, line: str, line_num: int) -> None:
        """Parse a single manifest line."""
        line = line.rstrip()  # Remove trailing whitespace

        # Check line length (ESO limit: 301 bytes)
        if len(line.encode("utf-8")) > 301:
            self.data.validation_errors.append(
                f"Line {line_num} exceeds 301 byte limit ({len(line.encode('utf-8'))} bytes)"
            )

        # Empty or comment-only lines
        if not line or line.startswith("# ") or line == "#":
            return

        # Directive lines (## Key: Value)
        match = self.DIRECTIVE_PATTERN.match(line)
        if match:
            key, value = match.groups()
            self._handle_directive(key, value.strip())
            return

        # File references
        file_match = self.FILE_PATTERN.match(line)
        if file_match:
            self.data.files.append(file_match.group(1))

    def _handle_directive(self, key: str, value: str) -> None:
        """Handle a parsed directive."""
        key_lower = key.lower()

        if key_lower == "title":
            self.data.title = value
        elif key_lower == "apiversion":
            self._parse_api_version(value)
        elif key_lower == "addonversion":
            try:
                self.data.addon_version = int(value)
            except ValueError:
                self.data.validation_errors.append(
                    f"AddOnVersion must be integer, got: {value}"
                )
        elif key_lower == "version":
            self.data.version = value
        elif key_lower == "author":
            self.data.author = value
        elif key_lower == "description":
            self.data.description = value
        elif key_lower == "dependson":
            self.data.depends_on = self._parse_dependencies(value)
        elif key_lower == "optionaldependson":
            self.data.optional_depends_on = self._parse_dependencies(value)
        elif key_lower == "savedvariables":
            self.data.saved_variables = value.split()
        elif key_lower == "islibrary":
            self.data.is_library = value.lower() == "true"
        elif key_lower == "credits":
            self.data.credits = value

    def _parse_api_version(self, value: str) -> None:
        """Parse API version(s) from directive value."""
        versions = []
        for part in value.split():
            try:
                versions.append(int(part))
            except ValueError:
                self.data.validation_errors.append(
                    f"Invalid API version: {part}"
                )
        self.data.api_version = versions

    def _parse_dependencies(self, value: str) -> list[str]:
        """Parse dependency list from directive value."""
        if not value:
            return []
        return self.DEPENDENCY_PATTERN.findall(value)

    def _validate(self) -> None:
        """Validate parsed manifest data."""
        # Check required directives
        if not self.data.title:
            self.data.validation_errors.append("Missing required directive: ## Title:")

        if not self.data.api_version:
            self.data.validation_errors.append("Missing required directive: ## APIVersion:")

        # Check for outdated API version
        if self.data.api_version:
            max_version = max(self.data.api_version)
            if max_version < CURRENT_API_VERSION:
                self.data.validation_errors.append(
                    f"Outdated API version: {max_version} (current: {CURRENT_API_VERSION})"
                )


class ManifestFixer:
    """Fix issues in ESO addon manifest files."""

    def __init__(self, manifest_data: ManifestData):
        """Initialize fixer with parsed manifest data."""
        self.data = manifest_data
        self.fixes_applied: list[str] = []

    def fix_all(self) -> tuple[str, list[str]]:
        """Apply all fixes and return fixed content with list of fixes."""
        content = self._build_fixed_content()
        return content, self.fixes_applied

    def _build_fixed_content(self) -> str:
        """Build the fixed manifest content."""
        lines = []

        for line in self.data.raw_lines:
            fixed_line = self._fix_line(line)
            lines.append(fixed_line)

        # Ensure proper line endings (CRLF for ESO)
        content = "\r\n".join(lines)

        # Ensure no BOM
        if content.startswith("\ufeff"):
            content = content[1:]
            self.fixes_applied.append("Removed UTF-8 BOM")

        return content

    def _fix_line(self, line: str) -> str:
        """Fix a single manifest line."""
        # Check for API version directive
        if line.strip().startswith("## APIVersion:"):
            return self._fix_api_version(line)

        # Check for LibStub in DependsOn (should be removed)
        if "## DependsOn:" in line and "LibStub" in line:
            fixed = self._remove_libstub_dependency(line)
            if fixed != line:
                return fixed

        return line

    def _fix_api_version(self, line: str) -> str:
        """Update API version to current."""
        # Check if already current
        if str(CURRENT_API_VERSION) in line:
            return line

        # Replace with dual version
        new_line = f"## APIVersion: {DUAL_API_VERSION}"
        self.fixes_applied.append(
            f"Updated APIVersion to {DUAL_API_VERSION}"
        )
        return new_line

    def _remove_libstub_dependency(self, line: str) -> str:
        """Remove LibStub from dependencies (it's deprecated)."""
        # Remove LibStub entries
        original = line
        line = re.sub(r"\bLibStub\s*", "", line)
        line = re.sub(r"\s+", " ", line)  # Clean up extra spaces
        line = line.rstrip()

        if line != original:
            self.fixes_applied.append("Removed LibStub from DependsOn (deprecated)")

        return line

    def update_dependency_versions(self) -> None:
        """Update library dependency versions to current."""
        for i, line in enumerate(self.data.raw_lines):
            if "## DependsOn:" in line or "## OptionalDependsOn:" in line:
                for lib_name, lib_info in LIBRARY_VERSIONS.items():
                    if lib_name in line:
                        # Update version requirement
                        pattern = rf"\b{re.escape(lib_name)}(?:>=\d+)?"
                        replacement = f"{lib_name}>={lib_info['version']}"
                        new_line = re.sub(pattern, replacement, line)
                        if new_line != line:
                            self.data.raw_lines[i] = new_line
                            self.fixes_applied.append(
                                f"Updated {lib_name} version to >={lib_info['version']}"
                            )
                            line = new_line  # For subsequent replacements


def parse_manifest(manifest_path: Path) -> ManifestData:
    """Convenience function to parse a manifest file."""
    parser = ManifestParser(manifest_path)
    return parser.parse()


def fix_manifest(manifest_path: Path) -> tuple[str, list[str]]:
    """Convenience function to fix a manifest file."""
    parser = ManifestParser(manifest_path)
    data = parser.parse()
    fixer = ManifestFixer(data)
    return fixer.fix_all()
