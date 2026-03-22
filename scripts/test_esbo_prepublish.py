#!/usr/bin/env python3
"""
ESOBuildOptimizer pre-publish validation suite.

Validates the addon is ready for ESOUI.com submission by checking:
1. Manifest compliance
2. Module wiring (all modules register properly)
3. SavedVariables defaults
4. Event registration patterns
5. ESO API usage correctness
6. File packaging readiness

Usage:
    python scripts/test_esbo_prepublish.py
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ADDON_DIR = REPO_ROOT / "addon" / "ESOBuildOptimizer"
ADDON_NAME = "ESOBuildOptimizer"

passed = 0
failed = 0
warnings = 0


def test(name: str):
    """Decorator for test functions."""
    def decorator(func):
        def wrapper():
            global passed, failed, warnings
            try:
                warns = func()
                passed += 1
                warn_msg = f" ({warns} warnings)" if warns else ""
                print(f"[PASS] {name}{warn_msg}")
                warnings += warns if warns else 0
            except AssertionError as e:
                failed += 1
                print(f"[FAIL] {name}: {e}")
            except Exception as e:
                failed += 1
                print(f"[FAIL] {name}: {type(e).__name__}: {e}")
        return wrapper
    return decorator


def read_lua(filename: str) -> str:
    """Read a Lua file from the addon directory."""
    return (ADDON_DIR / filename).read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@test("1. Manifest validation")
def test_manifest():
    txt = ADDON_DIR / f"{ADDON_NAME}.txt"
    addon = ADDON_DIR / f"{ADDON_NAME}.addon"

    assert txt.exists(), ".txt manifest missing"
    assert addon.exists(), ".addon manifest missing"

    content = txt.read_bytes()
    text = content.decode("utf-8", errors="replace")

    assert "## Title:" in text, "Missing ## Title:"
    assert "## APIVersion:" in text, "Missing ## APIVersion:"
    assert "## AddOnVersion:" in text, "Missing ## AddOnVersion:"
    assert "## SavedVariables:" in text, "Missing ## SavedVariables:"

    # Check API version includes 101049
    api_line = [l for l in text.split("\n") if "## APIVersion:" in l][0]
    assert "101049" in api_line, f"APIVersion should include 101049: {api_line}"

    # Check .txt and .addon are in sync
    txt_norm = content.replace(b"\r\n", b"\n")
    addon_norm = addon.read_bytes().replace(b"\r\n", b"\n")
    assert txt_norm == addon_norm, ".txt and .addon manifests differ"


@test("2. Module wiring (4 modules)")
def test_module_wiring():
    main_lua = read_lua("ESOBuildOptimizer.lua")

    expected_modules = ["CombatTracker", "BuildSnapshot", "MetricsUI", "SkillAdvisor"]
    for mod in expected_modules:
        # Check module file exists
        mod_path = ADDON_DIR / "modules" / f"{mod}.lua"
        assert mod_path.exists(), f"Module file missing: modules/{mod}.lua"

        # Check module is referenced in main addon
        assert mod in main_lua, f"Module '{mod}' not referenced in main addon"


@test("3. SavedVariables defaults")
def test_saved_vars():
    main_lua = read_lua("ESOBuildOptimizer.lua")

    # Should have a defaults table or initialization
    assert "ESOBuildOptimizerSV" in main_lua or "SavedVariables" in main_lua, \
        "No SavedVariables reference found"

    # Check for defaults initialization pattern
    has_defaults = (
        "defaults" in main_lua.lower() or
        "ZO_SavedVars" in main_lua or
        "ESOBuildOptimizerSV" in main_lua
    )
    assert has_defaults, "No SavedVariables defaults pattern found"


@test("4. Event registration")
def test_event_registration():
    # All event registration happens in main addon file
    main_lua = read_lua("ESOBuildOptimizer.lua")
    assert "EVENT_ADD_ON_LOADED" in main_lua, "Missing EVENT_ADD_ON_LOADED registration"
    assert "EVENT_COMBAT_EVENT" in main_lua, "Missing EVENT_COMBAT_EVENT registration"
    assert "EVENT_PLAYER_COMBAT_STATE" in main_lua, "Missing combat state event"

    # Count total event registrations across all files
    all_lua = ""
    for f in ADDON_DIR.rglob("*.lua"):
        all_lua += f.read_text(encoding="utf-8", errors="replace")

    event_count = len(re.findall(r"RegisterForEvent", all_lua))
    assert event_count >= 3, f"Only {event_count} event registrations (expected >= 3)"


@test("5. Event filtering (performance)")
def test_event_filtering():
    # Event filtering is done in main addon file where events are registered
    main_lua = read_lua("ESOBuildOptimizer.lua")

    has_filtering = (
        "AddFilterForEvent" in main_lua or
        "REGISTER_FILTER" in main_lua
    )
    assert has_filtering, "Should filter combat events for performance"


@test("6. Namespace isolation")
def test_namespace():
    main_lua = read_lua("ESOBuildOptimizer.lua")

    # Should use a namespace pattern
    assert "ESOBuildOptimizer" in main_lua, "Missing addon namespace"

    # Should use local variables
    local_count = main_lua.count("local ")
    assert local_count >= 5, f"Only {local_count} local declarations (expected >= 5)"


@test("7. BuildSnapshot gear tracking")
def test_build_snapshot():
    build = read_lua("modules/BuildSnapshot.lua")

    # Should access equip slots
    equip_patterns = ["EQUIP_SLOT_HEAD", "EQUIP_SLOT_CHEST", "EQUIP_SLOT_MAIN_HAND"]
    found = sum(1 for p in equip_patterns if p in build)
    assert found >= 2, f"BuildSnapshot only references {found}/3 equip slot constants"

    # Should capture skill bar
    assert "GetSlotBoundId" in build or "GetSlotName" in build or "HOTBAR" in build, \
        "BuildSnapshot should read skill bar slots"


@test("8. MetricsUI display creation")
def test_metrics_ui():
    ui = read_lua("modules/MetricsUI.lua")

    # Should create UI elements
    assert "CreateControl" in ui or "CT_LABEL" in ui or "CT_CONTROL" in ui, \
        "MetricsUI should create UI controls"

    # Should update dynamically
    assert "SetText" in ui or "SetHidden" in ui, \
        "MetricsUI should update UI elements"


@test("9. SkillAdvisor recommendations")
def test_skill_advisor():
    advisor = read_lua("modules/SkillAdvisor.lua")

    # Should access skill information
    assert "GetSlotBoundId" in advisor or "GetSlotName" in advisor or "HOTBAR" in advisor, \
        "SkillAdvisor should read skill bar"


@test("10. Console compatibility")
def test_console_compat():
    main_lua = read_lua("ESOBuildOptimizer.lua")

    # Should check for console/gamepad mode
    has_console_check = (
        "IsConsoleUI" in main_lua or
        "IsInGamepadPreferredMode" in main_lua or
        "isConsole" in main_lua
    )
    assert has_console_check, "Should check for console/gamepad mode"


@test("11. No hardcoded paths")
def test_no_hardcoded_paths():
    warns = 0
    for lua_file in ADDON_DIR.rglob("*.lua"):
        content = lua_file.read_text(encoding="utf-8", errors="replace")
        rel = lua_file.relative_to(ADDON_DIR)

        # Check for hardcoded Windows/Mac paths
        if re.search(r'[A-Z]:\\|/Users/|/home/', content):
            warns += 1

    return warns


@test("12. Packaging readiness")
def test_packaging():
    required = [
        "ESOBuildOptimizer.txt",
        "ESOBuildOptimizer.addon",
        "ESOBuildOptimizer.lua",
        "modules/CombatTracker.lua",
        "modules/BuildSnapshot.lua",
        "modules/MetricsUI.lua",
        "modules/SkillAdvisor.lua",
    ]

    for f in required:
        assert (ADDON_DIR / f).exists(), f"Missing required file: {f}"

    # Count total files (should be under console limit of 500)
    total_files = sum(1 for _ in ADDON_DIR.rglob("*") if _.is_file())
    assert total_files < 500, f"Too many files for console: {total_files}"

    # Check total size
    total_size = sum(f.stat().st_size for f in ADDON_DIR.rglob("*") if f.is_file())
    assert total_size < 5_000_000, f"Total size too large: {total_size/1024/1024:.1f}MB"

    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print(f"  ESOBuildOptimizer Pre-Publish Test Suite")
    print("=" * 60)
    print()

    tests = [
        test_manifest, test_module_wiring, test_saved_vars,
        test_event_registration, test_event_filtering, test_namespace,
        test_build_snapshot, test_metrics_ui, test_skill_advisor,
        test_console_compat, test_no_hardcoded_paths, test_packaging,
    ]

    for t in tests:
        t()

    print()
    print(f"Results: {passed} passed, {failed} failed, {warnings} warnings")

    if failed > 0:
        print("\nFAILED — Fix issues before submitting to ESOUI.com")
        sys.exit(1)
    else:
        print("\nPASSED — Addon is ready for ESOUI.com submission!")


if __name__ == "__main__":
    main()
