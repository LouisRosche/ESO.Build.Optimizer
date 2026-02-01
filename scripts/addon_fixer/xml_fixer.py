"""
XML fixer for ESO addon UI files.

Handles virtual control inheritance updates, texture path fixes,
and other XML-related issues in ESO addon UI definitions.
"""

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


@dataclass
class XMLIssue:
    """Represents an issue found in XML code."""
    file_path: Path
    line_number: int
    issue_type: str
    message: str
    old_code: str
    suggested_fix: Optional[str] = None
    severity: str = "warning"
    auto_fixable: bool = False


@dataclass
class XMLAnalysisResult:
    """Result of analyzing an XML file."""
    file_path: Path
    issues: list[XMLIssue] = field(default_factory=list)
    virtual_controls: list[str] = field(default_factory=list)
    texture_paths: list[str] = field(default_factory=list)
    font_paths: list[str] = field(default_factory=list)


# Deprecated virtual control templates and their replacements
DEPRECATED_VIRTUAL_CONTROLS = {
    # Old base templates that may have changed
    "ZO_ScrollContainer": {
        "notes": "Still valid but check scroll bar bindings",
        "severity": "info",
    },
    "ZO_SortFilterList": {
        "notes": "Verify callback signature matches current API",
        "severity": "info",
    },
    "ZO_ObjectPoolEditControl": {
        "notes": "Object pool patterns may have changed",
        "severity": "warning",
    },
}

# Texture paths that have changed or been removed
DEPRECATED_TEXTURE_PATHS = {
    "EsoUI/Art/Buttons/button_disabled.dds": "EsoUI/Art/Buttons/button_normal.dds",
    "EsoUI/Art/Miscellaneous/": {
        "notes": "Some textures moved to different directories",
    },
}

# Font path migrations
FONT_PATH_UPDATES = {
    r'\.(ttf|otf)': '.slug',
}


class XMLAnalyzer:
    """Analyze ESO addon XML files for issues."""

    def __init__(self):
        """Initialize the XML analyzer."""
        self.namespace = {"ui": "http://www.esoui.com/gui/2010"}

    def analyze_file(self, file_path: Path) -> XMLAnalysisResult:
        """Analyze a single XML file for issues."""
        result = XMLAnalysisResult(file_path=file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="windows-1252") as f:
                    content = f.read()
                result.issues.append(XMLIssue(
                    file_path=file_path,
                    line_number=0,
                    issue_type="encoding",
                    message="File uses Windows-1252 encoding, should be UTF-8",
                    old_code="",
                    severity="warning",
                    auto_fixable=True,
                ))
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                return result

        # Use regex-based analysis for line numbers
        self._analyze_virtual_controls(content, file_path, result)
        self._analyze_texture_paths(content, file_path, result)
        self._analyze_font_paths(content, file_path, result)
        self._analyze_handlers(content, file_path, result)

        return result

    def _analyze_virtual_controls(
        self,
        content: str,
        file_path: Path,
        result: XMLAnalysisResult
    ) -> None:
        """Find and analyze virtual control usage."""
        # Pattern for inherits attribute
        pattern = r'inherits\s*=\s*["\']([^"\']+)["\']'

        for match in re.finditer(pattern, content, re.IGNORECASE):
            line_num = content[:match.start()].count("\n") + 1
            control_name = match.group(1)

            # Handle multiple inheritance
            controls = [c.strip() for c in control_name.split(",")]

            for ctrl in controls:
                result.virtual_controls.append(ctrl)

                if ctrl in DEPRECATED_VIRTUAL_CONTROLS:
                    info = DEPRECATED_VIRTUAL_CONTROLS[ctrl]
                    result.issues.append(XMLIssue(
                        file_path=file_path,
                        line_number=line_num,
                        issue_type="virtual_control",
                        message=f"Virtual control {ctrl}: {info.get('notes', 'May need verification')}",
                        old_code=ctrl,
                        severity=info.get("severity", "info"),
                        auto_fixable=False,
                    ))

    def _analyze_texture_paths(
        self,
        content: str,
        file_path: Path,
        result: XMLAnalysisResult
    ) -> None:
        """Find and analyze texture paths."""
        # Pattern for texture file references
        pattern = r'(?:textureFile|normalTexture|pressedTexture|mouseOverTexture|disabledTexture)\s*=\s*["\']([^"\']+\.dds)["\']'

        for match in re.finditer(pattern, content, re.IGNORECASE):
            line_num = content[:match.start()].count("\n") + 1
            texture_path = match.group(1)

            result.texture_paths.append(texture_path)

            # Check if path is deprecated
            for old_path, replacement in DEPRECATED_TEXTURE_PATHS.items():
                if old_path in texture_path:
                    if isinstance(replacement, dict):
                        result.issues.append(XMLIssue(
                            file_path=file_path,
                            line_number=line_num,
                            issue_type="texture_path",
                            message=f"Texture path may have changed: {replacement.get('notes', '')}",
                            old_code=texture_path,
                            severity="info",
                            auto_fixable=False,
                        ))
                    else:
                        result.issues.append(XMLIssue(
                            file_path=file_path,
                            line_number=line_num,
                            issue_type="texture_path",
                            message=f"Deprecated texture path",
                            old_code=texture_path,
                            suggested_fix=texture_path.replace(old_path, replacement),
                            severity="warning",
                            auto_fixable=True,
                        ))

    def _analyze_font_paths(
        self,
        content: str,
        file_path: Path,
        result: XMLAnalysisResult
    ) -> None:
        """Find and analyze font paths."""
        # Pattern for font references
        pattern = r'font\s*=\s*["\']([^"\']+\.(ttf|otf|slug)(?:\|[^"\']*)?)["\']'

        for match in re.finditer(pattern, content, re.IGNORECASE):
            line_num = content[:match.start()].count("\n") + 1
            font_path = match.group(1)

            result.font_paths.append(font_path)

            # Check for old font extensions
            if ".ttf" in font_path.lower() or ".otf" in font_path.lower():
                suggested = re.sub(r'\.(ttf|otf)', '.slug', font_path, flags=re.IGNORECASE)
                result.issues.append(XMLIssue(
                    file_path=file_path,
                    line_number=line_num,
                    issue_type="font_path",
                    message="Font uses old TTF/OTF format, should use .slug",
                    old_code=font_path,
                    suggested_fix=suggested,
                    severity="warning",
                    auto_fixable=True,
                ))

    def _analyze_handlers(
        self,
        content: str,
        file_path: Path,
        result: XMLAnalysisResult
    ) -> None:
        """Analyze event handlers for deprecated patterns."""
        # Pattern for OnEvent handlers with old event names
        deprecated_events = [
            "OnVeteranRankUpdate",
            "OnVeteranPointsUpdate",
        ]

        for event in deprecated_events:
            pattern = rf'On{event}\s*=\s*["\']([^"\']+)["\']'
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count("\n") + 1
                result.issues.append(XMLIssue(
                    file_path=file_path,
                    line_number=line_num,
                    issue_type="deprecated_event",
                    message=f"Deprecated event handler: {event}",
                    old_code=match.group(0),
                    severity="error",
                    auto_fixable=False,
                ))


class XMLTransformer:
    """Transform XML files to fix issues."""

    def __init__(self):
        """Initialize the transformer."""
        self.changes_made: list[str] = []

    def fix_file(self, file_path: Path, dry_run: bool = False) -> tuple[str, list[str]]:
        """Fix issues in an XML file and return the fixed content."""
        self.changes_made = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="windows-1252") as f:
                content = f.read()
            self.changes_made.append("Converted encoding from Windows-1252 to UTF-8")

        # Apply fixes
        content = self._fix_font_paths(content)
        content = self._fix_texture_paths(content)

        if not dry_run and self.changes_made:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        return content, self.changes_made

    def _fix_font_paths(self, content: str) -> str:
        """Fix font paths from .ttf/.otf to .slug format."""
        def replace_font(match):
            old_path = match.group(0)
            new_path = re.sub(r'\.(ttf|otf)', '.slug', old_path, flags=re.IGNORECASE)
            if new_path != old_path:
                self.changes_made.append(f"Updated font path: {old_path} → {new_path}")
            return new_path

        # Pattern for font attributes in XML
        pattern = r'font\s*=\s*["\'][^"\']+\.(ttf|otf)(?:\|[^"\']*)?["\']'
        content = re.sub(pattern, replace_font, content, flags=re.IGNORECASE)

        return content

    def _fix_texture_paths(self, content: str) -> str:
        """Fix deprecated texture paths."""
        for old_path, replacement in DEPRECATED_TEXTURE_PATHS.items():
            if isinstance(replacement, str):
                if old_path in content:
                    content = content.replace(old_path, replacement)
                    self.changes_made.append(f"Updated texture path: {old_path} → {replacement}")

        return content


def analyze_xml_file(file_path: Path) -> XMLAnalysisResult:
    """Convenience function to analyze an XML file."""
    analyzer = XMLAnalyzer()
    return analyzer.analyze_file(file_path)


def fix_xml_file(file_path: Path, dry_run: bool = False) -> tuple[str, list[str]]:
    """Convenience function to fix an XML file."""
    transformer = XMLTransformer()
    return transformer.fix_file(file_path, dry_run)
