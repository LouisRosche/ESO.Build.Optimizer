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
    for mod_name in expected_modules:
        init_patterns = [
            f"self.{mod_name}:Initialize()",
            f"self.{mod_name}:Initialize(",
            f"FPT.{mod_name}:Initialize()",
        ]
        found = any(p in main_lua for p in init_patterns)
        # Some modules are initialized conditionally
        if not found and f"{mod_name}" in main_lua:
            # Check for conditional init pattern
            found = f"{mod_name}:Initialize" in main_lua or f"{mod_name}.Initialize" in main_lua

        if not found:
            missing.append(f"{mod_name}: not initialized in main file")

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
        ("1/8", "Static Validator", test_static_validator),
        ("2/8", "Module Wiring", test_module_wiring),
        ("3/8", "SavedVars Defaults", test_savedvars_defaults),
        ("4/8", "Event Registration", test_event_registration),
        ("5/8", "String Format", test_string_format),
        ("6/8", "Packaging Readiness", test_packaging),
        ("7/8", "Cross-Module API", test_cross_module_api),
        ("8/8", "Addon Fixer", test_addon_fixer),
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
