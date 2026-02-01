"""
ESO Addon Fixer - Automated tool for fixing broken ESO addons.

This package provides tools to analyze and fix broken Elder Scrolls Online
addons by updating deprecated API calls, fixing manifest files, removing
LibStub dependencies, and more.

Target API Version: 101048 (Update 48 - January 2026)
"""

__version__ = "1.0.0"
__author__ = "ESO Build Optimizer Team"

from .fixer import AddonFixer
from .manifest import ManifestParser, ManifestFixer
from .lua_analyzer import LuaAnalyzer
from .migrations import MigrationDatabase

__all__ = [
    "AddonFixer",
    "ManifestParser",
    "ManifestFixer",
    "LuaAnalyzer",
    "MigrationDatabase",
]
