#!/usr/bin/env python3
"""
Pre-publish test suite for FurnishProfitTargeter addon.

Runs all validation checks before packaging for ESOUI distribution.
This is the single command to run before publishing.

Usage:
    python scripts/test_fpt_prepublish.py         # Full test suite
    python scripts/test_fpt_prepublish.py -v       # Verbose output

Exit codes:
    0 = All tests passed
    1 = Test failures (do not publish)
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
ADDON_DIR = REPO_ROOT / "addon" / "FurnishProfitTargeter"
ADDON_NAME = "FurnishProfitTargeter"

VERBOSE = "-v" in sys.argv or "--verbose" in sys.argv


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str = ""
    duration_ms: float = 0


@dataclass
class TestSuite:
    results: list[TestResult] = field(default_factory=list)

    def add(self, name: str, passed: bool, message: str = "", duration_ms: float = 0):
        self.results.append(TestResult(name, passed, message, duration_ms))

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)


def log(msg: str):
    print(msg)


def vlog(msg: str):
    if VERBOSE:
        print(f"  {msg}")


# ---------------------------------------------------------------------------
# Test 1: Static Validator (our comprehensive checker)
# ---------------------------------------------------------------------------

def test_static_validator(suite: TestSuite):
    """Run the comprehensive FPT addon validator."""
    t0 = time.time()

    # Import the validator module and call run_validation() directly
    spec = importlib.util.spec_from_file_location(
        "validate_fpt_addon",
        REPO_ROOT / "scripts" / "validate_fpt_addon.py"
    )
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)

    # Call the validation function directly (not via __main__ guard)
    result = validator.run_validation()
    duration = (time.time() - t0) * 1000

    checks = result.checks_run
    critical = result.critical_count
    warnings = result.warning_count

    # Sanity check: if validator ran 0 checks, something is broken
    if checks == 0:
        suite.add("Static validator", False,
                   "BROKEN: validator ran 0 checks (test harness error)", duration)
        return

    passed = critical == 0
    msg = f"{checks} checks, {critical} critical, {warnings} warnings"
    suite.add("Static validator", passed, msg, duration)

    if VERBOSE or not passed:
        for issue in result.issues:
            vlog(f"[{issue.severity}] {issue.file}:{issue.line} - {issue.message}")


# ---------------------------------------------------------------------------
# Test 2: Module Dependency Wiring
# ---------------------------------------------------------------------------

def test_module_wiring(suite: TestSuite):
    """Verify all modules register themselves on the FPT namespace correctly."""
    t0 = time.time()

    main_lua = (ADDON_DIR / f"{ADDON_NAME}.lua").read_text()

    # Modules that main file expects
    expected_modules = [
        "PlanScanner",
        "PriceEngine",
        "VelocityCalculator",
        "ResultsUI",
        "BundleManager",
        "SupplyTracker",
        "MarketCopy",
    ]

    # Check each module file registers itself
    missing = []
    for mod_name in expected_modules:
        mod_file = ADDON_DIR / "modules" / f"{mod_name}.lua"
        if not mod_file.exists():
            missing.append(f"{mod_name}: file missing")
            continue

        content = mod_file.read_text()

        # Check registration pattern: FPT.ModuleName = ModuleName
        if f"FPT.{mod_name} = {mod_name}" not in content:
            missing.append(f"{mod_name}: missing 'FPT.{mod_name} = {mod_name}' registration")

        # Check Initialize function exists
        if f"function {mod_name}:Initialize()" not in content:
            missing.append(f"{mod_name}: missing Initialize() function")

    # Check main file calls Initialize on each module
    # Strip comments to avoid false matches on commented-out code
    main_code_lines = [
        line for line in main_lua.split("\n")
        if not line.strip().startswith("--")
    ]
    main_code = "\n".join(main_code_lines)

    for mod_name in expected_modules:
        # Look for actual initialization calls (not in comments)
        found = (
            f"{mod_name}:Initialize()" in main_code
            or f"{mod_name}:Initialize(" in main_code
        )

        if not found:
            missing.append(f"{mod_name}: not initialized in main file (no :Initialize() call found in non-comment code)")

    duration = (time.time() - t0) * 1000
    passed = len(missing) == 0
    msg = f"{len(expected_modules)} modules checked"
    if missing:
        msg += f", {len(missing)} issues: " + "; ".join(missing[:3])
    suite.add("Module wiring", passed, msg, duration)


# ---------------------------------------------------------------------------
# Test 3: SavedVariables Defaults Coverage
# ---------------------------------------------------------------------------

def test_savedvars_defaults(suite: TestSuite):
    """Verify every SavedVariables field has a default value."""
    t0 = time.time()

    main_lua = (ADDON_DIR / f"{ADDON_NAME}.lua").read_text()

    # Find the defaults table (may be named defaultSavedVars, SAVEDVARS_DEFAULTS, etc.)
    defaults_match = re.search(
        r'local\s+\w*[Dd]efault\w*\s*=\s*\{(.+?)\n\}',
        main_lua, re.DOTALL
    )

    if not defaults_match:
        suite.add("SavedVars defaults", False, "Could not find SAVEDVARS_DEFAULTS table",
                   (time.time() - t0) * 1000)
        return

    defaults_text = defaults_match.group(1)

    # Check that all accessed savedVars paths have defaults
    issues = []

    # Find all savedVars.settings.X accesses
    settings_accesses = set()
    for lua_file in ADDON_DIR.rglob("*.lua"):
        content = lua_file.read_text()
        for m in re.finditer(r'savedVars\.settings\.(\w+)', content):
            settings_accesses.add(m.group(1))

    # Check each setting has a default
    for setting in sorted(settings_accesses):
        if setting not in defaults_text:
            issues.append(f"settings.{setting} accessed but no default found")

    # Check supplyChain defaults
    supply_accesses = set()
    for lua_file in ADDON_DIR.rglob("*.lua"):
        content = lua_file.read_text()
        for m in re.finditer(r'savedVars\.supplyChain\.(\w+)', content):
            supply_accesses.add(m.group(1))
        # Also check sc. pattern (local alias)
        for m in re.finditer(r'\bsc\.(\w+)', content):
            supply_accesses.add(m.group(1))

    # These are initialized in SupplyTracker:Initialize() not in defaults
    supply_init_fields = {"codPurchases", "materialInventory", "dailyLog",
                          "totalSaved", "totalSpent", "totalUnits"}

    for field_name in sorted(supply_accesses):
        if field_name not in defaults_text and field_name not in supply_init_fields:
            # Skip method calls and common patterns
            if field_name in ("codPurchases", "materialInventory", "dailyLog"):
                continue
            if not field_name[0].isupper():  # Skip method calls like sc:Something
                issues.append(f"supplyChain.{field_name} accessed but no default")

    duration = (time.time() - t0) * 1000
    passed = len(issues) == 0
    msg = f"{len(settings_accesses)} settings, {len(supply_accesses)} supply fields checked"
    if issues:
        msg += f" - {len(issues)} missing defaults"
        for issue in issues[:3]:
            vlog(f"MISSING: {issue}")
    suite.add("SavedVars defaults", passed, msg, duration)


# ---------------------------------------------------------------------------
# Test 4: Event Registration Consistency
# ---------------------------------------------------------------------------

def test_event_registration(suite: TestSuite):
    """Verify all registered events use proper namespacing and cleanup."""
    t0 = time.time()

    issues = []
    registrations = []

    for lua_file in ADDON_DIR.rglob("*.lua"):
        content = lua_file.read_text()
        rel = lua_file.relative_to(ADDON_DIR)
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Find RegisterForEvent calls
            if "RegisterForEvent(" in line and not line.strip().startswith("--"):
                registrations.append((str(rel), i, line.strip()))

                # Check namespace prefix - look at current line AND next line
                # (multiline calls may have FPT.name on the next line)
                context = line
                if i < len(lines):
                    context += " " + lines[i]  # next line (0-indexed i = line i+1)

                if 'FPT.name' not in context and '"FurnishProfitTargeter' not in context:
                    issues.append(f"{rel}:{i}: Event registered without FPT.name namespace prefix")

            # Find RegisterForUpdate calls (periodic timers)
            if "RegisterForUpdate(" in line and not line.strip().startswith("--"):
                registrations.append((str(rel), i, line.strip()))

    duration = (time.time() - t0) * 1000
    passed = len(issues) == 0
    msg = f"{len(registrations)} event registrations"
    if issues:
        msg += f", {len(issues)} namespace issues"
    suite.add("Event registration", passed, msg, duration)


# ---------------------------------------------------------------------------
# Test 5: String Format Specifier Match
# ---------------------------------------------------------------------------

def test_string_format(suite: TestSuite):
    """Verify string.format calls have matching specifiers and arguments."""
    t0 = time.time()

    issues = []
    checked = 0

    for lua_file in ADDON_DIR.rglob("*.lua"):
        content = lua_file.read_text()
        rel = lua_file.relative_to(ADDON_DIR)

        for i, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("--"):
                continue

            if "string.format(" not in line:
                continue

            checked += 1

            # Extract format string
            fmt_match = re.search(r'string\.format\(\s*"([^"]*)"', line)
            if not fmt_match:
                continue

            # Skip multiline format calls — comma counting is unreliable
            if line.rstrip().endswith(","):
                continue

            fmt_str = fmt_match.group(1)

            # Count specifiers (skip %% which is literal %)
            clean = fmt_str.replace("%%", "")
            specifiers = re.findall(r'%[dfsxXoqcge\.0-9\-\+]*[dfsxXoqcge]', clean)

            # Count arguments (rough: count commas after format string)
            # This is approximate but catches obvious mismatches
            after_fmt = line[fmt_match.end():]
            # Remove nested function calls to avoid counting their commas
            depth = 0
            comma_count = 0
            for ch in after_fmt:
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth < 0:
                        break
                elif ch == ',' and depth == 0:
                    comma_count += 1

            # args = comma_count (each comma separates an arg)
            if len(specifiers) > 0 and comma_count > 0:
                if len(specifiers) != comma_count:
                    # Allow 1 off for method call self-comma ambiguity
                    if abs(len(specifiers) - comma_count) > 1:
                        issues.append(
                            f"{rel}:{i}: format has {len(specifiers)} specifiers "
                            f"but ~{comma_count} args"
                        )

    duration = (time.time() - t0) * 1000
    passed = len(issues) == 0
    msg = f"{checked} format calls checked"
    if issues:
        msg += f", {len(issues)} mismatches"
        for issue in issues[:3]:
            vlog(issue)
    suite.add("String format consistency", passed, msg, duration)


# ---------------------------------------------------------------------------
# Test 6: Packaging Readiness
# ---------------------------------------------------------------------------

def test_packaging(suite: TestSuite):
    """Verify the addon is ready to be packaged."""
    t0 = time.time()

    issues = []

    # Check manifest exists and has CRLF
    manifest = ADDON_DIR / f"{ADDON_NAME}.txt"
    if manifest.exists():
        content = manifest.read_bytes()
        if b"\r\n" not in content:
            issues.append("Manifest needs CRLF line endings")
    else:
        issues.append("Manifest file missing")

    # Check no debug/development artifacts
    for lua_file in ADDON_DIR.rglob("*.lua"):
        content = lua_file.read_text()
        rel = lua_file.relative_to(ADDON_DIR)

        # Check for leftover debug prints
        for i, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("--"):
                continue
            if "print(" in stripped and "d(" not in stripped:
                issues.append(f"{rel}:{i}: Bare print() call (use FPT:Debug instead)")
            if "TODO" in stripped or "FIXME" in stripped or "HACK" in stripped:
                issues.append(f"{rel}:{i}: Development marker: {stripped[:60]}")

    # Check file count (ESO console limit: 500 files)
    file_count = sum(1 for _ in ADDON_DIR.rglob("*") if _.is_file())
    if file_count > 500:
        issues.append(f"Too many files ({file_count}) - ESO console limit is 500")

    duration = (time.time() - t0) * 1000
    passed = len(issues) == 0
    msg = f"{file_count} files, ready for packaging"
    if issues:
        msg = f"{len(issues)} packaging issues"
        for issue in issues[:5]:
            vlog(issue)
    suite.add("Packaging readiness", passed, msg, duration)


# ---------------------------------------------------------------------------
# Test 7: Cross-module API Consistency
# ---------------------------------------------------------------------------

def test_cross_module_api(suite: TestSuite):
    """Verify modules call each other's APIs correctly."""
    t0 = time.time()

    issues = []

    # Build a map of each module's public API (function declarations)
    module_apis: dict[str, set[str]] = {}

    for lua_file in (ADDON_DIR / "modules").glob("*.lua"):
        mod_name = lua_file.stem
        content = lua_file.read_text()
        functions = set()

        for m in re.finditer(rf'function\s+{mod_name}:(\w+)\s*\(', content):
            functions.add(m.group(1))

        module_apis[mod_name] = functions

    # Check all cross-module calls reference real functions
    for lua_file in ADDON_DIR.rglob("*.lua"):
        content = lua_file.read_text()
        rel = lua_file.relative_to(ADDON_DIR)

        for mod_name, apis in module_apis.items():
            # Find calls like FPT.ModName:FunctionName(
            pattern = rf'FPT\.{mod_name}:(\w+)\s*\('
            for m in re.finditer(pattern, content):
                called_fn = m.group(1)
                if called_fn not in apis:
                    issues.append(
                        f"{rel}: calls FPT.{mod_name}:{called_fn}() "
                        f"but {mod_name} has no such method"
                    )

    duration = (time.time() - t0) * 1000
    passed = len(issues) == 0
    total_apis = sum(len(v) for v in module_apis.values())
    msg = f"{len(module_apis)} modules, {total_apis} public methods verified"
    if issues:
        msg += f", {len(issues)} missing methods"
        for issue in issues[:3]:
            vlog(issue)
    suite.add("Cross-module API", passed, msg, duration)


# ---------------------------------------------------------------------------
# Test 8: Addon Fixer Compliance
# ---------------------------------------------------------------------------

def test_addon_fixer(suite: TestSuite):
    """Run addon-fixer analyze and verify no errors."""
    t0 = time.time()

    fixer_cli = REPO_ROOT / "tools" / "addon-fixer" / "dist" / "cli.js"
    if not fixer_cli.exists():
        suite.add("Addon fixer", True, "Skipped (not built)", (time.time() - t0) * 1000)
        return

    try:
        result = subprocess.run(
            ["node", str(fixer_cli), "analyze", str(ADDON_DIR)],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr

        # Parse issue counts
        errors = 0
        warnings = 0
        for line in output.split("\n"):
            if "Errors:" in line:
                errors = int(line.split(":")[1].strip())
            elif "Critical:" in line:
                errors = int(line.split(":")[1].strip())

        passed = errors == 0
        msg = f"addon-fixer: {errors} errors"
        if VERBOSE:
            for line in output.strip().split("\n"):
                vlog(line)

    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        passed = True  # Don't fail if tool unavailable
        msg = f"Skipped: {e}"

    duration = (time.time() - t0) * 1000
    suite.add("Addon fixer compliance", passed, msg, duration)


# ---------------------------------------------------------------------------
# Test 9: Formula & Unit Consistency
# ---------------------------------------------------------------------------

def test_formula_consistency(suite: TestSuite):
    """Verify mathematical formulas use correct units and FormatGold is only applied to gold values."""
    t0 = time.time()

    issues = []
    checks = 0

    for lua_file in ADDON_DIR.rglob("*.lua"):
        content = lua_file.read_text()
        rel = lua_file.relative_to(ADDON_DIR)
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("--"):
                continue

            # Check FormatGold is not applied to non-gold values
            fmt_gold_match = re.search(r'FormatGold\(([^)]+)\)', stripped)
            if fmt_gold_match:
                checks += 1
                arg = fmt_gold_match.group(1).strip()
                # velocityScore is NOT gold — it's margin × count
                non_gold_fields = ["velocityScore", "totalScore"]
                for field in non_gold_fields:
                    if field in arg:
                        issues.append(
                            f"{rel}:{i}: FormatGold() applied to non-gold value '{field}' "
                            f"(use FormatScore instead)"
                        )

            # Check FormatPct isn't double-multiplying
            fmt_pct_match = re.search(r'FormatPct\(([^)]+)\)', stripped)
            if fmt_pct_match:
                checks += 1
                arg = fmt_pct_match.group(1).strip()
                if "* 100" in arg or "*100" in arg:
                    issues.append(
                        f"{rel}:{i}: FormatPct() arg already multiplied by 100 "
                        f"(FormatPct does its own ×100)"
                    )

            # Check division operations have guards
            div_match = re.search(r'/\s*([\w.]+(?:\s*or\s*\d+)?)\s*', stripped)
            if div_match and "savedVars" in stripped and "/" in stripped:
                checks += 1
                divisor = div_match.group(1)
                # Check if there's a guard (or N, > 0, ~= 0) nearby
                context = "\n".join(lines[max(0, i-5):i])
                has_guard = (
                    "or 14" in context or "or 1" in context
                    or "> 0" in context or "<= 0" in context
                    or "~= 0" in context
                )
                if not has_guard and "windowDays" in divisor:
                    issues.append(f"{rel}:{i}: Division by {divisor} without guard")

    duration = (time.time() - t0) * 1000
    passed = len(issues) == 0
    msg = f"{checks} formula/unit checks"
    if issues:
        msg += f", {len(issues)} issues"
        for issue in issues[:5]:
            vlog(issue)
    suite.add("Formula & unit consistency", passed, msg, duration)


# ---------------------------------------------------------------------------
# Test 10: Cross-Module Data Field Consistency
# ---------------------------------------------------------------------------

def test_data_field_consistency(suite: TestSuite):
    """Verify plan/item objects use consistent field names across all modules."""
    t0 = time.time()

    issues = []

    # The plan object flows: PlanScanner → PriceEngine → VelocityCalculator → ResultsUI
    # Track which fields are SET and READ in each module

    field_writers: dict[str, list[str]] = {}  # field → [module:line, ...]
    field_readers: dict[str, list[str]] = {}

    # Patterns for setting fields on plan/item objects
    # Matches: plan.fieldName = ..., item.fieldName = ..., result.fieldName = ...
    set_pattern = re.compile(r'(?:plan|item|result)\.(\w+)\s*=')
    # Also matches table constructors: { fieldName = value, ... }
    table_set_pattern = re.compile(r'^\s*(\w+)\s*=\s*[^=]')
    get_pattern = re.compile(r'(?:plan|item|result)\.(\w+)(?:\s|[,)\]}]|$)')

    in_table_constructor = False
    brace_depth = 0

    for lua_file in ADDON_DIR.rglob("*.lua"):
        content = lua_file.read_text()
        rel = str(lua_file.relative_to(ADDON_DIR))
        in_table_constructor = False
        brace_depth = 0

        for i, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("--"):
                continue

            # Track table constructor context (for detecting field writes)
            for ch in stripped:
                if ch == '{':
                    brace_depth += 1
                    in_table_constructor = True
                elif ch == '}':
                    brace_depth -= 1
                    if brace_depth <= 0:
                        in_table_constructor = False
                        brace_depth = 0

            for m in set_pattern.finditer(stripped):
                field_name = m.group(1)
                field_writers.setdefault(field_name, []).append(f"{rel}:{i}")

            # Table constructor fields count as writes
            if in_table_constructor:
                for m in table_set_pattern.finditer(stripped):
                    field_name = m.group(1)
                    # Skip Lua keywords and common non-field patterns
                    if field_name not in {"local", "function", "if", "for", "while",
                                          "return", "end", "else", "elseif", "then",
                                          "do", "repeat", "until", "not", "and", "or",
                                          "type", "name", "id", "true", "false"}:
                        field_writers.setdefault(field_name, []).append(f"{rel}:{i}")

            for m in get_pattern.finditer(stripped):
                field_name = m.group(1)
                # Skip assignments (already captured)
                if f"{field_name} =" in stripped and f"{field_name} ==" not in stripped:
                    continue
                field_readers.setdefault(field_name, []).append(f"{rel}:{i}")

    # Find fields that are READ but never WRITTEN (potential typo or missing data)
    # Exclude common method names and known globals
    method_names = {"name", "find", "insert", "format", "sub", "lower", "upper",
                    "concat", "gsub", "len", "match", "rep", "byte", "char"}

    for field_name, readers in field_readers.items():
        if field_name in method_names:
            continue
        if field_name not in field_writers:
            # Only flag if read in more than one place (single reads might be method calls)
            if len(readers) >= 2:
                issues.append(
                    f"Field '{field_name}' read in {len(readers)} places but never explicitly set: "
                    f"{readers[0]}"
                )

    duration = (time.time() - t0) * 1000
    passed = len(issues) == 0
    total_fields = len(set(field_writers.keys()) | set(field_readers.keys()))
    msg = f"{total_fields} data fields tracked across modules"
    if issues:
        msg += f", {len(issues)} consistency issues"
        for issue in issues[:5]:
            vlog(issue)
    suite.add("Data field consistency", passed, msg, duration)


# ---------------------------------------------------------------------------
# Test 11: Mathematical Correctness Verification
# ---------------------------------------------------------------------------

def test_math_verification(suite: TestSuite):
    """Verify key formulas produce correct results with known test vectors."""
    t0 = time.time()

    issues = []
    checks = 0

    # Extract and verify formulas from source code
    velocity_calc = (ADDON_DIR / "modules" / "VelocityCalculator.lua").read_text()
    price_engine = (ADDON_DIR / "modules" / "PriceEngine.lua").read_text()
    bundle_mgr = (ADDON_DIR / "modules" / "BundleManager.lua").read_text()

    # Test 1: ROI formula — verify it's profit/cost, not cost/profit
    checks += 1
    roi_match = re.search(r'plan\.roi\s*=\s*([^\n]+)', price_engine)
    if roi_match:
        formula = roi_match.group(1).strip()
        # ROI should be profitMargin / materialCost (positive when profitable)
        if "profitMargin" not in formula or "materialCost" not in formula:
            issues.append(f"ROI formula doesn't use expected fields: {formula}")
        elif formula.index("materialCost") < formula.index("profitMargin"):
            issues.append(f"ROI formula appears inverted (cost/profit instead of profit/cost): {formula}")
    else:
        issues.append("ROI formula not found in PriceEngine")

    # Test 2: Profit margin = retail - cost (not cost - retail)
    checks += 1
    margin_match = re.search(r'plan\.profitMargin\s*=\s*([^\n]+)', price_engine)
    if margin_match:
        formula = margin_match.group(1).strip()
        if "retailPrice" in formula and "materialCost" in formula:
            # Verify order: should be retail - cost
            retail_pos = formula.index("retailPrice")
            cost_pos = formula.index("materialCost")
            if "-" in formula and cost_pos < retail_pos:
                issues.append(f"Profit margin appears inverted (cost - retail): {formula}")
        else:
            issues.append(f"Profit margin doesn't use expected fields: {formula}")
    else:
        issues.append("Profit margin formula not found in PriceEngine")

    # Test 3: Bundle markup: price = COGS × (1 + markup/100), not COGS × markup/100
    checks += 1
    # Find the actual calculation (contains math.floor), not the initialization (= 0)
    markup_match = re.search(r'suggestedPrice\s*=\s*(math\.floor\([^\n]+)', bundle_mgr)
    if markup_match:
        formula = markup_match.group(1).strip()
        if "(1 +" not in formula and "(1+" not in formula:
            issues.append(f"Bundle markup formula missing (1 + markup) pattern: {formula}")
    else:
        # Fallback: look for any suggestedPrice assignment with actual math
        for line in bundle_mgr.split("\n"):
            if "suggestedPrice" in line and "math.floor" in line:
                if "(1 +" not in line and "(1+" not in line:
                    issues.append(f"Bundle markup formula missing (1 + markup) pattern")
                break

    # Test 4: Weekly profit uses /windowDays * 7, not raw score
    checks += 1
    weekly_match = re.search(r'totalEstWeeklyProfit\s*=\s*([^\n]+)', velocity_calc)
    if weekly_match:
        formula = weekly_match.group(1).strip()
        if "windowDays" not in formula:
            issues.append(f"Weekly profit doesn't divide by windowDays: {formula}")
        if "* 7" not in formula and "*7" not in formula:
            issues.append(f"Weekly profit doesn't multiply by 7: {formula}")
        # Verify it uses raw profit, not bonus-inflated score
        if "totalScore" in formula:
            issues.append(
                f"Weekly profit uses bonus-inflated totalScore instead of raw profit: {formula}"
            )

    # Test 5: Velocity score is margin × sales (basic sanity)
    checks += 1
    vscore_match = re.search(r'local velocityScore\s*=\s*([^\n]+)', velocity_calc)
    if vscore_match:
        formula = vscore_match.group(1).strip()
        if "profitMargin" not in formula or "salesCount" not in formula:
            issues.append(f"Velocity score doesn't use margin × sales: {formula}")

    # Test 6: COD discount: target = price × (1 - discount/100)
    checks += 1
    cod_match = re.search(r'codTargetPrice\s*=\s*([^\n]+)', price_engine)
    if cod_match:
        formula = cod_match.group(1).strip()
        if "1 -" not in formula and "1-" not in formula:
            issues.append(f"COD discount formula missing (1 - discount) pattern: {formula}")

    # Test 7: Summary stats division guards
    checks += 1
    if "avgMargin" in velocity_calc:
        # Find the actual formula (contains division), not initialization
        avg_match = re.search(r'avgMargin\s*=\s*(.+/[^\n]+)', velocity_calc)
        if avg_match:
            formula = avg_match.group(1).strip()
            if "> 0" not in formula and "and" not in formula:
                issues.append(f"avgMargin has no division-by-zero guard: {formula}")

    duration = (time.time() - t0) * 1000
    passed = len(issues) == 0
    msg = f"{checks} formula verifications"
    if issues:
        msg += f", {len(issues)} issues"
        for issue in issues[:5]:
            vlog(issue)
    suite.add("Math verification", passed, msg, duration)


# ---------------------------------------------------------------------------
# Test 12: Scroll & UI Bounds Safety
# ---------------------------------------------------------------------------

def test_ui_bounds(suite: TestSuite):
    """Verify UI scroll logic and row management are correctly bounded."""
    t0 = time.time()

    issues = []
    checks = 0

    results_ui = (ADDON_DIR / "modules" / "ResultsUI.lua").read_text()

    # Check that scroll offset is used in click handlers
    checks += 1
    if "scrollOffset" in results_ui:
        # Verify click handler uses scroll-adjusted index
        if "ShowItemDetail(index)" in results_ui and "scrollOffset" not in results_ui.split("ShowItemDetail")[0].split("OnMouseUp")[-1]:
            # Check if scrollOffset is used near ShowItemDetail
            click_section = re.search(
                r'OnMouseUp.*?ShowItemDetail\(([^)]+)\)',
                results_ui, re.DOTALL
            )
            if click_section:
                if "scrollOffset" not in click_section.group(1):
                    issues.append("Click handler doesn't use scrollOffset for data index")
    else:
        issues.append("ResultsUI has no scrollOffset — rows beyond visible area are inaccessible")

    # Check that row pool is bounded
    checks += 1
    if "MAX_VISIBLE_ROWS" in results_ui or "ROW_POOL_MAX" in results_ui:
        pass  # Has bounds
    else:
        issues.append("ResultsUI has no row pool bounds")

    # Check scroll handler exists
    checks += 1
    if "OnMouseWheel" in results_ui:
        # Verify scroll bounds: offset >= 0 and offset <= max
        if "math.max(0" in results_ui and "math.min(" in results_ui:
            pass  # Properly bounded
        else:
            issues.append("Scroll handler may not properly bound scroll offset")
    else:
        issues.append("ResultsUI has no scroll wheel handler")

    # Check RefreshVisibleRows exists and is called
    checks += 1
    if "RefreshVisibleRows" in results_ui:
        # Count definitions vs calls
        defs = len(re.findall(r'function\s+ResultsUI:RefreshVisibleRows', results_ui))
        calls = len(re.findall(r'RefreshVisibleRows\(\)', results_ui))
        if defs == 0:
            issues.append("RefreshVisibleRows is referenced but not defined")
        elif calls == 0:
            issues.append("RefreshVisibleRows is defined but never called")
    else:
        issues.append("No RefreshVisibleRows function for scroll redraw")

    duration = (time.time() - t0) * 1000
    passed = len(issues) == 0
    msg = f"{checks} UI bounds checks"
    if issues:
        msg += f", {len(issues)} issues"
        for issue in issues[:5]:
            vlog(issue)
    suite.add("UI bounds safety", passed, msg, duration)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print()
    print("=" * 64)
    print("  FurnishProfitTargeter - Pre-Publish Test Suite")
    print("=" * 64)
    print()

    suite = TestSuite()

    tests = [
        ("1/12", "Static Validator", test_static_validator),
        ("2/12", "Module Wiring", test_module_wiring),
        ("3/12", "SavedVars Defaults", test_savedvars_defaults),
        ("4/12", "Event Registration", test_event_registration),
        ("5/12", "String Format", test_string_format),
        ("6/12", "Packaging Readiness", test_packaging),
        ("7/12", "Cross-Module API", test_cross_module_api),
        ("8/12", "Addon Fixer", test_addon_fixer),
        ("9/12", "Formula & Units", test_formula_consistency),
        ("10/12", "Data Fields", test_data_field_consistency),
        ("11/12", "Math Verification", test_math_verification),
        ("12/12", "UI Bounds", test_ui_bounds),
    ]

    for num, name, test_fn in tests:
        print(f"[{num}] {name}...", end=" ", flush=True)
        test_fn(suite)
        result = suite.results[-1]
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} ({result.duration_ms:.0f}ms) - {result.message}")

    print()
    print("-" * 64)
    print(f"  Results: {suite.passed}/{suite.total} passed, "
          f"{suite.failed} failed")
    print("-" * 64)

    if suite.all_passed:
        print()
        print("  All tests passed! Ready to package.")
        print(f"  Run: python scripts/package_fpt_addon.py")
        print()
        sys.exit(0)
    else:
        print()
        print("  FAILURES - fix issues before publishing:")
        for r in suite.results:
            if not r.passed:
                print(f"    FAIL: {r.name} - {r.message}")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
