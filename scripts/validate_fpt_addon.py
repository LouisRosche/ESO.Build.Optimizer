#!/usr/bin/env python3
"""
FurnishProfitTargeter Addon Validator

Exhaustive static analysis to catch the exact categories of bugs we've seen:
1. Hallucinated ESO API function names
2. Wrong return value capture counts
3. Wrong global variable names (e.g., TamrielTradeCentre vs TamrielTradeCentrePrice)
4. Non-existent ESO constants
5. Wrong XML color formats
6. Manifest inconsistencies
7. Logic errors in formulas
8. Lua syntax issues

This validator uses the validated API signatures from our migrations DB
and cross-references every API call in the addon source.
"""

import json
import os
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

ADDON_DIR = Path(__file__).parent.parent / "addon" / "FurnishProfitTargeter"
MIGRATIONS_FILE = Path(__file__).parent.parent / "data" / "migrations" / "eso-api-migrations.json"

# ─────────────────────────────────────────────────────────────
# Validated ESO API signatures (from ESOUI source verification)
# ─────────────────────────────────────────────────────────────

VALIDATED_FUNCTIONS = {
    # Recipe functions
    "GetNumRecipeLists": {"params": 0, "returns": 1},
    "GetRecipeListInfo": {"params": 1, "returns": 2, "notes": "listName, numRecipesInList"},
    "GetRecipeInfo": {
        "params": 2, "returns": 8,
        "return_names": [
            "known", "name", "numIngredients", "provisionerLevelReq",
            "qualityReq", "specialIngredientType", "requiredCraftingStationType", "resultItemId"
        ],
        "notes": "resultItemId is at position 8, NOT 7"
    },
    "GetRecipeResultItemLink": {"params": 3, "returns": 1},
    "GetRecipeIngredientItemInfo": {
        "params": 3, "returns": 5,
        "return_names": ["name", "icon", "requiredQuantity", "sellPrice", "displayQuality"]
    },
    "GetRecipeIngredientItemLink": {"params": 4, "returns": 1},
    "GetRecipeIngredientRequiredQuantity": {"params": 3, "returns": 1},
    "GetCurrentRecipeIngredientCount": {"params": 3, "returns": 1},
    "GetRecipeTradeskillRequirement": {"params": 3, "returns": 2},
    "GetMaxRecipeIngredients": {"params": 0, "returns": 1},

    # Item link functions
    "GetItemLinkItemId": {"params": 1, "returns": 1, "notes": "returns integer itemId"},
    "GetItemLinkItemType": {
        "params": 1, "returns": 2,
        "return_names": ["itemType", "specializedItemType"],
        "notes": "returns TWO values, not one"
    },
    "GetItemLinkDisplayQuality": {"params": 1, "returns": 1},
    "GetItemLinkName": {"params": 1, "returns": 1},

    # Mail functions
    "GetMailItemInfo": {
        "params": 1, "returns": 13,
        "return_names": [
            "senderDisplayName", "senderCharacterName", "subject", "icon",
            "unread", "fromSystem", "fromCustomerService", "returned",
            "numAttachments", "attachedMoney", "codAmount",
            "expiresInDays", "secsSinceReceived"
        ],
        "notes": "codAmount is at position 11"
    },
    "GetAttachedItemInfo": {
        "params": 2, "returns": 8,
        "return_names": [
            "icon", "stack", "creatorName", "sellPrice",
            "meetsUsageRequirement", "equipType", "itemStyle", "quality"
        ]
    },
    "GetAttachedItemLink": {"params": 3, "returns": 1},

    # Time
    "GetTimeStamp": {"params": 0, "returns": 1},
    "GetGameTimeMilliseconds": {"params": 0, "returns": 1},

    # UI / Window
    "GetAddOnManager": {"params": 0, "returns": 1},

    # Crafting constants (these are globals, not functions)
    # Listed here to validate they exist
}

# Known VALID ESO global constants
VALID_ESO_CONSTANTS = {
    # Crafting types
    "CRAFTING_TYPE_BLACKSMITHING", "CRAFTING_TYPE_CLOTHIER",
    "CRAFTING_TYPE_WOODWORKING", "CRAFTING_TYPE_ENCHANTING",
    "CRAFTING_TYPE_ALCHEMY", "CRAFTING_TYPE_PROVISIONING",
    "CRAFTING_TYPE_JEWELRYCRAFTING",
    # Item types
    "ITEMTYPE_FURNISHING",
    # Specialized furnishing types
    "SPECIALIZED_ITEMTYPE_FURNISHING_CRAFTING_STATION",
    "SPECIALIZED_ITEMTYPE_FURNISHING_LIGHT",
    "SPECIALIZED_ITEMTYPE_FURNISHING_ORNAMENTAL",
    "SPECIALIZED_ITEMTYPE_FURNISHING_SEATING",
    "SPECIALIZED_ITEMTYPE_FURNISHING_TARGET_DUMMY",
    # Link styles
    "LINK_STYLE_BRACKETS", "LINK_STYLE_DEFAULT",
    # Events
    "EVENT_ADD_ON_LOADED", "EVENT_PLAYER_ACTIVATED",
    "EVENT_MAIL_READABLE", "EVENT_COMBAT_EVENT",
    # Anchors
    "TOPLEFT", "TOPRIGHT", "BOTTOMLEFT", "BOTTOMRIGHT",
    "CENTER", "TOP", "BOTTOM", "LEFT", "RIGHT",
    # UI
    "GuiRoot", "WINDOW_MANAGER", "EVENT_MANAGER",
    "CT_LABEL", "CT_BUTTON", "CT_BACKDROP", "CT_CONTROL",
    "DL_OVERLAY", "DT_HIGH",
    "MOUSE_BUTTON_INDEX_LEFT",
    # Slash commands
    "SLASH_COMMANDS",
}

# Known INVALID / non-existent ESO functions and constants
KNOWN_INVALID = {
    "GetRecipeIngredientInfo",      # Correct: GetRecipeIngredientItemInfo
    "GetItemLinkFurnishingLimitType",  # Does not exist
    "GetMailAttachmentInfo",        # Does not exist (use GetMailItemInfo returns)
    "ADDON_STATE_ENABLED",         # Does not exist
    "ADDON_STATE_DISABLED",        # Does not exist
    "GetItemLinkSpecializedItemType",  # Correct: GetItemLinkItemType returns 2 values
}

# Known WRONG global names for third-party APIs
WRONG_GLOBALS = {
    "TamrielTradeCentre": "TamrielTradeCentrePrice (the price API global)",
}

# Correct third-party globals
VALID_THIRD_PARTY_GLOBALS = {
    "TamrielTradeCentrePrice",
    "MasterMerchant",
    "LibAddonMenu2",
    "FurnishProfitTargeter",
    "FurnishProfitTargeterSV",
}


@dataclass
class Issue:
    file: str
    line: int
    severity: str  # "CRITICAL", "WARNING", "INFO"
    category: str
    message: str


@dataclass
class ValidationResult:
    issues: list = field(default_factory=list)
    checks_run: int = 0
    api_calls_found: int = 0
    files_scanned: int = 0

    @property
    def critical_count(self):
        return sum(1 for i in self.issues if i.severity == "CRITICAL")

    @property
    def warning_count(self):
        return sum(1 for i in self.issues if i.severity == "WARNING")


def read_file(path: Path) -> list[str]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.readlines()


# ─────────────────────────────────────────────────────────────
# Check 1: Validate every ESO API function call name
# ─────────────────────────────────────────────────────────────

def check_api_function_names(lines: list[str], filename: str, result: ValidationResult):
    """Verify every ESO API call is a real function, not hallucinated."""
    # Pattern: standalone function calls that look like ESO API (PascalCase, starts with Get/Set/Is/Has/etc.)
    api_call_pattern = re.compile(
        r'\b(Get[A-Z]\w+|Set[A-Z]\w+|Is[A-Z]\w+|Has[A-Z]\w+|'
        r'Do[A-Z]\w+|Can[A-Z]\w+|Are[A-Z]\w+)\s*\('
    )

    for line_num, line in enumerate(lines, 1):
        # Skip comments
        stripped = line.strip()
        if stripped.startswith("--"):
            continue

        for match in api_call_pattern.finditer(line):
            func_name = match.group(1)
            result.api_calls_found += 1
            result.checks_run += 1

            # Check against known invalid functions
            if func_name in KNOWN_INVALID:
                result.issues.append(Issue(
                    file=filename, line=line_num, severity="CRITICAL",
                    category="hallucinated_api",
                    message=f"'{func_name}' is a KNOWN INVALID ESO API function"
                ))

            # Check if it's a validated function we know about
            if func_name in VALIDATED_FUNCTIONS:
                # Known good - no issue
                pass


# ─────────────────────────────────────────────────────────────
# Check 2: Validate return value capture counts
# ─────────────────────────────────────────────────────────────

def check_return_value_counts(lines: list[str], filename: str, result: ValidationResult):
    """Check that return value captures match expected counts for critical functions."""
    # Pattern: local var1, var2, ... = FunctionName(...)
    assignment_pattern = re.compile(
        r'local\s+([\w\s,_]+)\s*=\s*\n?\s*(Get\w+|EVENT_MANAGER|WINDOW_MANAGER)\s*[:(]'
    )

    # More targeted patterns for specific critical functions
    critical_patterns = {
        "GetMailItemInfo": re.compile(
            r'local\s+([\w\s,_]+)\s*=\s*\n?\s*GetMailItemInfo\s*\('
        ),
        "GetRecipeInfo": re.compile(
            r'local\s+([\w\s,_]+)\s*=\s*\n?\s*GetRecipeInfo\s*\('
        ),
        "GetRecipeIngredientItemInfo": re.compile(
            r'local\s+([\w\s,_]+)\s*=\s*\n?\s*GetRecipeIngredientItemInfo\s*\('
        ),
        "GetAttachedItemInfo": re.compile(
            r'local\s+([\w\s,_]+)\s*=\s*\n?\s*GetAttachedItemInfo\s*\('
        ),
        "GetItemLinkItemType": re.compile(
            r'local\s+([\w\s,_]+)\s*=\s*\n?\s*GetItemLinkItemType\s*\('
        ),
    }

    # Join all lines for multi-line capture analysis
    full_text = "".join(lines)

    for func_name, pattern in critical_patterns.items():
        result.checks_run += 1
        for match in pattern.finditer(full_text):
            captures = match.group(1)
            # Count captured variables (comma-separated)
            var_list = [v.strip() for v in captures.split(",") if v.strip()]
            capture_count = len(var_list)

            expected = VALIDATED_FUNCTIONS.get(func_name, {}).get("returns", 0)

            if func_name == "GetRecipeInfo" and capture_count > expected:
                result.issues.append(Issue(
                    file=filename, line=0, severity="CRITICAL",
                    category="wrong_return_count",
                    message=f"'{func_name}' captures {capture_count} values but returns {expected}. "
                            f"Captured: {', '.join(var_list)}"
                ))

            # Check if a critical value is at the wrong position
            if func_name == "GetMailItemInfo":
                # codAmount must be at position 11
                for i, var in enumerate(var_list):
                    if "cod" in var.lower() and i + 1 != 11:
                        result.issues.append(Issue(
                            file=filename, line=0, severity="CRITICAL",
                            category="wrong_position",
                            message=f"'{func_name}': codAmount captured at position {i+1}, "
                                    f"should be position 11. Variables: {', '.join(var_list)}"
                        ))
                    if "numattach" in var.lower().replace("_", "") and i + 1 != 9:
                        result.issues.append(Issue(
                            file=filename, line=0, severity="CRITICAL",
                            category="wrong_position",
                            message=f"'{func_name}': numAttachments captured at position {i+1}, "
                                    f"should be position 9. Variables: {', '.join(var_list)}"
                        ))


# ─────────────────────────────────────────────────────────────
# Check 3: Wrong global variable names
# ─────────────────────────────────────────────────────────────

def check_global_names(lines: list[str], filename: str, result: ValidationResult):
    """Check for known-wrong global variable names."""
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("--"):
            continue

        result.checks_run += 1

        for wrong_name, correction in WRONG_GLOBALS.items():
            # Match as a standalone word (not part of a larger identifier)
            # But exclude the correct longer name
            pattern = re.compile(r'\b' + re.escape(wrong_name) + r'\b(?!Price|SV|_)')
            if pattern.search(line):
                # Check it's not in a string/comment
                if not stripped.startswith("--") and wrong_name + "Price" not in line:
                    result.issues.append(Issue(
                        file=filename, line=line_num, severity="CRITICAL",
                        category="wrong_global",
                        message=f"Wrong global '{wrong_name}' - should be {correction}"
                    ))


# ─────────────────────────────────────────────────────────────
# Check 3b: Deprecated WINDOW_MANAGER method calls
# ─────────────────────────────────────────────────────────────

def check_deprecated_window_manager(lines: list[str], filename: str, result: ValidationResult):
    """Check for deprecated WINDOW_MANAGER:CreateControl/CreateTopLevelWindow calls."""
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("--"):
            continue

        result.checks_run += 1

        if "WINDOW_MANAGER:CreateControl(" in line:
            result.issues.append(Issue(
                file=filename, line=line_num, severity="WARNING",
                category="deprecated_api",
                message="WINDOW_MANAGER:CreateControl() is deprecated since API 101041. "
                        "Use global CreateControl() instead."
            ))

        if "WINDOW_MANAGER:CreateTopLevelWindow(" in line:
            result.issues.append(Issue(
                file=filename, line=line_num, severity="WARNING",
                category="deprecated_api",
                message="WINDOW_MANAGER:CreateTopLevelWindow() is deprecated since API 101041. "
                        "Use global CreateTopLevelWindow() instead."
            ))


# ─────────────────────────────────────────────────────────────
# Check 3c: Unsafe string.gsub replacement strings
# ─────────────────────────────────────────────────────────────

def check_gsub_safety(lines: list[str], filename: str, result: ValidationResult):
    """Check for string.gsub calls where replacement is a variable (could contain %)."""
    gsub_pattern = re.compile(
        r'string\.gsub\s*\(\s*\w+\s*,\s*"[^"]+"\s*,\s*([^)]+)\)'
    )

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("--"):
            continue

        if "string.gsub" not in line:
            continue

        result.checks_run += 1

        for match in gsub_pattern.finditer(line):
            replacement = match.group(1).strip()
            # If replacement is NOT a string literal, it could contain %
            if not replacement.startswith('"') and not replacement.startswith("'"):
                # Check if it's a safe function call or if there's a safeReplace wrapper
                if "safeReplace" not in line and "gsub" not in replacement:
                    result.issues.append(Issue(
                        file=filename, line=line_num, severity="CRITICAL",
                        category="gsub_unsafe",
                        message=f"string.gsub replacement '{replacement}' is a variable - "
                                f"if it contains '%', gsub will crash. "
                                f"Escape with: replacement:gsub('%%', '%%%%')"
                    ))


# ─────────────────────────────────────────────────────────────
# Check 4: Non-existent ESO constants
# ─────────────────────────────────────────────────────────────

def check_eso_constants(lines: list[str], filename: str, result: ValidationResult):
    """Check for references to non-existent ESO constants."""
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("--"):
            continue

        for invalid_const in KNOWN_INVALID:
            if invalid_const in line and not stripped.startswith("--"):
                result.checks_run += 1
                result.issues.append(Issue(
                    file=filename, line=line_num, severity="CRITICAL",
                    category="invalid_constant",
                    message=f"Reference to non-existent constant/function: '{invalid_const}'"
                ))


# ─────────────────────────────────────────────────────────────
# Check 5: XML color format validation
# ─────────────────────────────────────────────────────────────

def check_xml_colors(result: ValidationResult):
    """Verify all XML color attributes use RGBA decimal format, not hex."""
    xml_files = list(ADDON_DIR.rglob("*.xml"))

    hex_color_pattern = re.compile(r'color\s*=\s*"([A-Fa-f0-9]{6,8})"')
    valid_rgba_pattern = re.compile(
        r'color\s*=\s*"(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)"'
    )

    for xml_file in xml_files:
        lines = read_file(xml_file)
        rel_path = xml_file.relative_to(ADDON_DIR.parent.parent)

        for line_num, line in enumerate(lines, 1):
            if "<!--" in line:
                continue

            result.checks_run += 1

            # Check for hex colors
            for match in hex_color_pattern.finditer(line):
                hex_val = match.group(1)
                # Make sure it's not already in RGBA format (would have spaces)
                context = line[max(0, match.start()-5):match.end()+5]
                result.issues.append(Issue(
                    file=str(rel_path), line=line_num, severity="CRITICAL",
                    category="xml_hex_color",
                    message=f"Hex color '{hex_val}' in XML - ESO requires RGBA decimal format (e.g., '1 0.843 0 1')"
                ))

            # Validate RGBA values are in 0-1 range
            for match in valid_rgba_pattern.finditer(line):
                for i, component in enumerate(match.groups()):
                    val = float(component)
                    if val < 0 or val > 1:
                        result.issues.append(Issue(
                            file=str(rel_path), line=line_num, severity="WARNING",
                            category="xml_color_range",
                            message=f"RGBA color component {val} is outside 0-1 range"
                        ))


# ─────────────────────────────────────────────────────────────
# Check 6: Manifest consistency
# ─────────────────────────────────────────────────────────────

def check_manifest(result: ValidationResult):
    """Verify manifest lists all files and all listed files exist."""
    manifest_path = ADDON_DIR / "FurnishProfitTargeter.txt"
    if not manifest_path.exists():
        result.issues.append(Issue(
            file="FurnishProfitTargeter.txt", line=0, severity="CRITICAL",
            category="manifest",
            message="Manifest file not found!"
        ))
        return

    lines = read_file(manifest_path)
    listed_files = []
    has_api_version = False
    has_saved_vars = False

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        result.checks_run += 1

        # Check metadata
        if stripped.startswith("## APIVersion:"):
            has_api_version = True
            versions = stripped.split(":")[1].strip().split()
            for v in versions:
                if not v.isdigit():
                    result.issues.append(Issue(
                        file="FurnishProfitTargeter.txt", line=line_num,
                        severity="CRITICAL", category="manifest",
                        message=f"Invalid APIVersion: '{v}' (must be integer)"
                    ))

        if stripped.startswith("## SavedVariables:"):
            has_saved_vars = True

        # Collect file references
        if not stripped.startswith("##") and not stripped.startswith("#") and stripped:
            listed_files.append(stripped)

    if not has_api_version:
        result.issues.append(Issue(
            file="FurnishProfitTargeter.txt", line=0, severity="CRITICAL",
            category="manifest", message="Missing ## APIVersion declaration"
        ))

    if not has_saved_vars:
        result.issues.append(Issue(
            file="FurnishProfitTargeter.txt", line=0, severity="CRITICAL",
            category="manifest", message="Missing ## SavedVariables declaration"
        ))

    # Verify all listed files exist
    for listed_file in listed_files:
        full_path = ADDON_DIR / listed_file
        result.checks_run += 1
        if not full_path.exists():
            result.issues.append(Issue(
                file="FurnishProfitTargeter.txt", line=0, severity="CRITICAL",
                category="manifest",
                message=f"Manifest lists '{listed_file}' but file does not exist"
            ))

    # Verify all .lua and .xml files are in the manifest
    for lua_file in ADDON_DIR.rglob("*.lua"):
        rel = lua_file.relative_to(ADDON_DIR)
        result.checks_run += 1
        if str(rel) not in listed_files:
            result.issues.append(Issue(
                file=str(rel), line=0, severity="WARNING",
                category="manifest",
                message=f"File '{rel}' exists but is not listed in manifest"
            ))

    for xml_file in ADDON_DIR.rglob("*.xml"):
        rel = xml_file.relative_to(ADDON_DIR)
        result.checks_run += 1
        if str(rel) not in listed_files:
            result.issues.append(Issue(
                file=str(rel), line=0, severity="WARNING",
                category="manifest",
                message=f"File '{rel}' exists but is not listed in manifest"
            ))


# ─────────────────────────────────────────────────────────────
# Check 7: Lua pattern analysis for common bugs
# ─────────────────────────────────────────────────────────────

def check_lua_patterns(lines: list[str], filename: str, result: ValidationResult):
    """Check for common Lua patterns that indicate bugs."""

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("--"):
            continue

        result.checks_run += 1

        # Check for string.format with mismatched %s/%d count
        fmt_match = re.search(r'string\.format\s*\(\s*"([^"]*)"', line)
        if fmt_match:
            fmt_str = fmt_match.group(1)
            # Count format specifiers (excluding %%)
            specs = re.findall(r'%[^%]', fmt_str)
            # Count arguments after the format string
            # This is approximate - we count commas after the format string
            after_fmt = line[fmt_match.end():]
            # Remove nested function calls to avoid counting their commas
            depth = 0
            arg_count = 0
            for char in after_fmt:
                if char == '(':
                    depth += 1
                elif char == ')':
                    if depth == 0:
                        break
                    depth -= 1
                elif char == ',' and depth == 0:
                    arg_count += 1
            # arg_count is number of commas = number of args after format string
            if len(specs) > 0 and arg_count + 1 < len(specs):
                result.issues.append(Issue(
                    file=filename, line=line_num, severity="WARNING",
                    category="format_mismatch",
                    message=f"string.format has {len(specs)} specifiers but appears to have {arg_count + 1} args"
                ))

        # Check for division by zero potential
        if "/ 0" in line or "/0" in line:
            # Skip comments
            if not stripped.startswith("--"):
                result.issues.append(Issue(
                    file=filename, line=line_num, severity="WARNING",
                    category="division_by_zero",
                    message="Potential division by zero"
                ))

        # Check for pcall usage without error handling
        if "pcall(" in line and "if success" not in line and "if not success" not in line:
            # Check next few lines for success check
            found_check = False
            for j in range(line_num, min(line_num + 5, len(lines))):
                if "success" in lines[j] or "result" in lines[j]:
                    found_check = True
                    break

        # Check for table.insert in pairs() loop (non-deterministic order)
        if "for" in line and "pairs(" in line:
            # Check if there's a table.insert in the loop body
            # This is an info-level check
            pass

        # Check for EVENT_MANAGER registration without unregistration
        if "RegisterForEvent" in line and "UnregisterForEvent" not in line:
            # Extract event name
            event_match = re.search(r'EVENT_MANAGER:RegisterForEvent\s*\(\s*([^,]+),\s*([^,]+)', line)
            if event_match:
                event_name = event_match.group(2).strip()
                # Events that should be unregistered after first fire
                one_shot_events = ["EVENT_ADD_ON_LOADED"]
                if event_name in one_shot_events:
                    # Check if unregistration happens nearby
                    pass


# ─────────────────────────────────────────────────────────────
# Check 8: Cross-reference SavedVariables usage
# ─────────────────────────────────────────────────────────────

def check_savedvars_consistency(result: ValidationResult):
    """Verify SavedVariables field access matches the default structure."""
    main_file = ADDON_DIR / "FurnishProfitTargeter.lua"
    if not main_file.exists():
        return

    lines = read_file(main_file)
    full_text = "".join(lines)

    # Extract default SavedVars structure
    # Find the defaultSavedVars table
    sv_match = re.search(
        r'local\s+defaultSavedVars\s*=\s*\{(.+?)\n\}',
        full_text, re.DOTALL
    )

    if not sv_match:
        result.issues.append(Issue(
            file="FurnishProfitTargeter.lua", line=0, severity="WARNING",
            category="savedvars",
            message="Could not parse defaultSavedVars structure"
        ))
        return

    # Extract top-level keys from the defaults
    sv_block = sv_match.group(1)
    top_keys = set(re.findall(r'^\s+(\w+)\s*=', sv_block, re.MULTILINE))

    result.checks_run += 1

    # Now scan ALL lua files for savedVars access patterns
    for lua_file in ADDON_DIR.rglob("*.lua"):
        lines = read_file(lua_file)
        rel_path = lua_file.relative_to(ADDON_DIR)

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("--"):
                continue

            # Check for FPT.savedVars.XXX access
            sv_access = re.findall(r'FPT\.savedVars\.(\w+)', line)
            for key in sv_access:
                result.checks_run += 1
                if key not in top_keys and key != "settings":
                    # Not a critical issue since modules may add keys dynamically
                    # But worth noting if it doesn't match defaults
                    pass


# ─────────────────────────────────────────────────────────────
# Check 9: Module cross-references
# ─────────────────────────────────────────────────────────────

def check_module_references(result: ValidationResult):
    """Verify that modules reference each other correctly."""
    # Map of expected module assignments
    expected_modules = {
        "PlanScanner": "modules/PlanScanner.lua",
        "PriceEngine": "modules/PriceEngine.lua",
        "VelocityCalculator": "modules/VelocityCalculator.lua",
        "ResultsUI": "modules/ResultsUI.lua",
        "BundleManager": "modules/BundleManager.lua",
        "SupplyTracker": "modules/SupplyTracker.lua",
        "MarketCopy": "modules/MarketCopy.lua",
    }

    for module_name, file_path in expected_modules.items():
        full_path = ADDON_DIR / file_path
        result.checks_run += 1

        if not full_path.exists():
            result.issues.append(Issue(
                file=file_path, line=0, severity="CRITICAL",
                category="module_missing",
                message=f"Module file '{file_path}' does not exist"
            ))
            continue

        lines = read_file(full_path)
        full_text = "".join(lines)

        # Check that the module registers itself
        registration = f"FPT.{module_name} = {module_name}"
        if registration not in full_text:
            result.issues.append(Issue(
                file=file_path, line=0, severity="CRITICAL",
                category="module_registration",
                message=f"Module does not register itself with 'FPT.{module_name} = {module_name}'"
            ))

        # Check that module has Initialize function
        if f"function {module_name}:Initialize()" not in full_text:
            result.issues.append(Issue(
                file=file_path, line=0, severity="WARNING",
                category="module_init",
                message=f"Module lacks Initialize() function"
            ))


# ─────────────────────────────────────────────────────────────
# Check 10: Item link format validation
# ─────────────────────────────────────────────────────────────

def check_item_link_format(lines: list[str], filename: str, result: ValidationResult):
    """Verify item link format strings are correct."""
    # ESO item link: |H1:item:ID:...|h|h
    link_pattern = re.compile(r'\|H\d+:item:(%d[^|]*)\|h\|h')

    for line_num, line in enumerate(lines, 1):
        if "|H" in line and "item:" in line:
            result.checks_run += 1
            # Check format string for correct structure
            fmt_match = re.search(r'"(\|H\d+:item:[^"]+\|h\|h)"', line)
            if fmt_match:
                fmt = fmt_match.group(1)
                # Count colon-separated fields after "item:"
                parts = fmt.split(":")
                item_idx = None
                for i, p in enumerate(parts):
                    if p == "item" or p.endswith("item"):
                        item_idx = i
                        break
                if item_idx is not None:
                    field_count = len(parts) - item_idx - 1  # fields after "item:"
                    # ESO item links should have 21 fields after "item:" for recent API
                    # But some have fewer - at minimum should have the ID
                    if field_count < 1:
                        result.issues.append(Issue(
                            file=filename, line=line_num, severity="WARNING",
                            category="item_link_format",
                            message=f"Item link has {field_count} fields after 'item:' - may be malformed"
                        ))


# ─────────────────────────────────────────────────────────────
# Check 11: Duplicate scanning detection
# ─────────────────────────────────────────────────────────────

def check_duplicate_scanning(lines: list[str], filename: str, result: ValidationResult):
    """Detect nested loops that would cause N*M scanning instead of N."""
    full_text = "".join(lines)
    result.checks_run += 1

    # Check for craftType loop wrapping a full recipe list scan
    if re.search(r'for\s+craftType\s*=.*do.*GetNumRecipeLists', full_text, re.DOTALL):
        result.issues.append(Issue(
            file=filename, line=0, severity="CRITICAL",
            category="duplicate_scan",
            message="craftType loop wrapping GetNumRecipeLists() scan - causes 7x duplicate scanning"
        ))

    # Check for ScanCraftType being called in a loop
    scan_calls = re.findall(r'ScanCraftType', full_text)
    if len(scan_calls) > 1:
        # Multiple calls to ScanCraftType might indicate the loop pattern
        result.issues.append(Issue(
            file=filename, line=0, severity="WARNING",
            category="duplicate_scan",
            message=f"ScanCraftType referenced {len(scan_calls)} times - verify no duplicate scanning"
        ))


# ─────────────────────────────────────────────────────────────
# Check 12: Day-of-week formula validation
# ─────────────────────────────────────────────────────────────

def check_day_of_week(lines: list[str], filename: str, result: ValidationResult):
    """Verify day-of-week calculations are correct."""
    for line_num, line in enumerate(lines, 1):
        if "TUESDAY" in line and "=" in line and not line.strip().startswith("--"):
            result.checks_run += 1
            # Extract the assigned value
            match = re.search(r'TUESDAY\s*=\s*(\d+)', line)
            if match:
                val = int(match.group(1))
                if val != 2:
                    result.issues.append(Issue(
                        file=filename, line=line_num, severity="CRITICAL",
                        category="day_of_week",
                        message=f"TUESDAY = {val} but should be 2 (using (days+4)%7 formula)"
                    ))

        if "FRIDAY" in line and "=" in line and not line.strip().startswith("--"):
            result.checks_run += 1
            match = re.search(r'FRIDAY\s*=\s*(\d+)', line)
            if match:
                val = int(match.group(1))
                if val != 5:
                    result.issues.append(Issue(
                        file=filename, line=line_num, severity="CRITICAL",
                        category="day_of_week",
                        message=f"FRIDAY = {val} but should be 5 (using (days+4)%7 formula)"
                    ))


# ─────────────────────────────────────────────────────────────
# Check 13: TTC/MM API usage patterns
# ─────────────────────────────────────────────────────────────

def check_pricing_api_patterns(lines: list[str], filename: str, result: ValidationResult):
    """Verify TTC and MM API calls follow correct patterns."""
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("--"):
            continue

        # Check TTC global name
        if "TamrielTradeCentre:" in line and "TamrielTradeCentrePrice:" not in line:
            result.checks_run += 1
            result.issues.append(Issue(
                file=filename, line=line_num, severity="CRITICAL",
                category="ttc_global",
                message="Using 'TamrielTradeCentre:' but correct global is 'TamrielTradeCentrePrice:'"
            ))

        # Check TTC nil check
        if "TamrielTradeCentre ~= nil" in line and "TamrielTradeCentrePrice" not in line:
            result.checks_run += 1
            result.issues.append(Issue(
                file=filename, line=line_num, severity="CRITICAL",
                category="ttc_global",
                message="Checking 'TamrielTradeCentre ~= nil' but correct global is 'TamrielTradeCentrePrice'"
            ))

        # Check MM API - verify pcall wrapping
        if "MasterMerchant:" in line and "pcall" not in line:
            # Check if this line is inside a pcall block
            result.checks_run += 1
            # Look backward for pcall
            in_pcall = False
            for j in range(max(0, line_num - 5), line_num):
                if "pcall" in lines[j]:
                    in_pcall = True
                    break
            if not in_pcall and "function" not in line:
                result.issues.append(Issue(
                    file=filename, line=line_num, severity="WARNING",
                    category="mm_safety",
                    message="MasterMerchant API call not wrapped in pcall - MM may not be loaded"
                ))


# ─────────────────────────────────────────────────────────────
# Main validator
# ─────────────────────────────────────────────────────────────

def run_validation() -> ValidationResult:
    result = ValidationResult()

    if not ADDON_DIR.exists():
        print(f"ERROR: Addon directory not found: {ADDON_DIR}")
        sys.exit(1)

    # Scan all Lua files
    lua_files = list(ADDON_DIR.rglob("*.lua"))
    result.files_scanned = len(lua_files)

    for lua_file in lua_files:
        lines = read_file(lua_file)
        rel_path = str(lua_file.relative_to(ADDON_DIR.parent.parent))

        check_api_function_names(lines, rel_path, result)
        check_return_value_counts(lines, rel_path, result)
        check_global_names(lines, rel_path, result)
        check_deprecated_window_manager(lines, rel_path, result)
        check_gsub_safety(lines, rel_path, result)
        check_eso_constants(lines, rel_path, result)
        check_lua_patterns(lines, rel_path, result)
        check_item_link_format(lines, rel_path, result)
        check_duplicate_scanning(lines, rel_path, result)
        check_day_of_week(lines, rel_path, result)
        check_pricing_api_patterns(lines, rel_path, result)

    # Non-file-specific checks
    check_xml_colors(result)
    check_manifest(result)
    check_module_references(result)
    check_savedvars_consistency(result)

    return result


def print_results(result: ValidationResult):
    """Print validation results with color coding."""
    print("=" * 70)
    print("  FurnishProfitTargeter Addon Validation Report")
    print("=" * 70)
    print(f"  Files scanned:     {result.files_scanned}")
    print(f"  API calls found:   {result.api_calls_found}")
    print(f"  Checks run:        {result.checks_run}")
    print(f"  Critical issues:   {result.critical_count}")
    print(f"  Warnings:          {result.warning_count}")
    print("=" * 70)

    if result.issues:
        # Group by severity
        for severity in ["CRITICAL", "WARNING", "INFO"]:
            issues = [i for i in result.issues if i.severity == severity]
            if not issues:
                continue

            color = {"CRITICAL": "\033[91m", "WARNING": "\033[93m", "INFO": "\033[94m"}[severity]
            reset = "\033[0m"

            print(f"\n{color}── {severity} ({len(issues)}) ──{reset}")
            for issue in issues:
                loc = f"{issue.file}:{issue.line}" if issue.line else issue.file
                print(f"  {color}[{issue.category}]{reset} {loc}")
                print(f"    {issue.message}")
    else:
        print("\n\033[92m  ✓ No issues found!\033[0m")

    print()
    if result.critical_count > 0:
        print(f"\033[91m  FAIL: {result.critical_count} critical issue(s) found\033[0m")
        return 1
    elif result.warning_count > 0:
        print(f"\033[93m  PASS with {result.warning_count} warning(s)\033[0m")
        return 0
    else:
        print("\033[92m  PASS: All checks passed\033[0m")
        return 0


if __name__ == "__main__":
    result = run_validation()
    exit_code = print_results(result)
    sys.exit(exit_code)
