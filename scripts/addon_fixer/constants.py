"""
Constants for ESO Addon Fixer.

Contains API versions, library mappings, and other fixed values.
"""

# Current ESO API versions (February 2026)
CURRENT_API_VERSION = 101048  # Update 48 - Live
PTS_API_VERSION = 101049  # Update 49 - PTS

# Dual version string for manifests (supports both Live and PTS)
DUAL_API_VERSION = "101047 101048"

# Minimum supported API version for fixes
MIN_SUPPORTED_API = 100015  # Update 10 (Champion Points migration)

# ESO Update timeline with significant API changes
API_VERSION_HISTORY = {
    100003: {"update": "Launch (2014)", "changes": ["Major API restrictions", "Combat event limitations"]},
    100015: {"update": "Update 10", "changes": ["Veteran Rank → Champion Points migration"]},
    100023: {"update": "Update 18", "changes": ["64-bit Lua support", "Larger SavedVariables"]},
    100027: {"update": "Update 21", "changes": ["Guild store text search API overhaul"]},
    100030: {"update": "Update 30", "changes": ["Removed 'Allow out of date addons' checkbox"]},
    101033: {"update": "Update 33", "changes": ["Per-character achievement tracking removed"]},
    101041: {"update": "Update 41", "changes": ["Slug font format migration (.ttf → .slug)"]},
    101046: {"update": "Update 46", "changes": ["Subclassing system", "Console addon support"]},
    101048: {"update": "Update 48", "changes": ["Current live version"]},
}

# Library global variable mappings (LibStub replacement)
LIBRARY_GLOBALS = {
    "LibAddonMenu-2.0": "LibAddonMenu2",
    "LibAddonMenu": "LibAddonMenu2",
    "LibCustomMenu": "LibCustomMenu",
    "LibGPS": "LibGPS3",
    "LibGPS3": "LibGPS3",
    "LibAsync": "LibAsync",
    "LibFilters": "LibFilters3",
    "LibFilters-3.0": "LibFilters3",
    "LibHistoire": "LibHistoire",
    "LibChatMessage": "LibChatMessage",
    "LibDebugLogger": "LibDebugLogger",
    "LibMediaProvider-1.0": "LibMediaProvider",
    "LibMapPing": "LibMapPing",
    "LibPromises": "LibPromises",
    "LibTextFilter": "LibTextFilter",
    "LibGetText": "LibGetText",
    "LibSavedVars": "LibSavedVars",
    "LibSlashCommander": "LibSlashCommander",
}

# Current library versions (for dependency validation)
LIBRARY_VERSIONS = {
    "LibAddonMenu-2.0": {"version": 41, "global": "LibAddonMenu2"},
    "LibCustomMenu": {"version": 7, "global": "LibCustomMenu"},
    "LibGPS3": {"version": 30, "global": "LibGPS3"},
    "LibAsync": {"version": 3, "global": "LibAsync"},
    "LibFilters-3.0": {"version": 39, "global": "LibFilters3"},
    "LibHistoire": {"version": 5, "global": "LibHistoire"},
    "LibDebugLogger": {"version": 2, "global": "LibDebugLogger"},
    "LibChatMessage": {"version": 4, "global": "LibChatMessage"},
}

# Manifest directive patterns
MANIFEST_DIRECTIVES = {
    "required": ["Title", "APIVersion"],
    "optional": [
        "Author",
        "Version",
        "AddOnVersion",
        "Description",
        "DependsOn",
        "OptionalDependsOn",
        "SavedVariables",
        "IsLibrary",
        "Credits",
    ],
}

# File extensions to process
LUA_EXTENSIONS = [".lua"]
XML_EXTENSIONS = [".xml"]
MANIFEST_EXTENSION = ".txt"

# Font file extensions (for slug migration)
FONT_EXTENSIONS_OLD = [".ttf", ".otf"]
FONT_EXTENSION_NEW = ".slug"

# Common broken addon patterns
ADDON_COMPLEXITY = {
    "low": ["Dustman", "Set Tracker", "Simple addons"],
    "medium": ["Foundry Tactical Combat", "PersonalAssistant modules", "CraftStore"],
    "high": ["AwesomeGuildStore", "Multi-dependency chains"],
    "very_high": ["Wykkyd Framework"],  # Recommend replacement
}

# Addons that should be replaced rather than fixed
REPLACEMENT_RECOMMENDATIONS = {
    "Wykkyd Framework": [
        "Wykkyd's framework is deeply tangled legacy code.",
        "Recommend using modern alternatives:",
        "  - Addon settings: LibAddonMenu-2.0",
        "  - Toolbar: CustomCompassPins or pChat toolbar",
        "  - Outfitter: AlphaGear or Dressing Room",
    ],
}
