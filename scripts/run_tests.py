#!/usr/bin/env python3
"""
Local Test Runner

Runs all tests and validation checks locally.
Usage: python scripts/run_tests.py
"""

import subprocess
import sys
import json
from pathlib import Path

# Colors for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(title: str):
    """Print a section header."""
    print(f"\n{BLUE}{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}{RESET}\n")


def print_result(name: str, passed: bool, details: str = ""):
    """Print a test result."""
    status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    print(f"  [{status}] {name}")
    if details and not passed:
        print(f"         {details}")


def run_command(cmd: list[str], cwd: Path = None) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except FileNotFoundError:
        return False, f"Command not found: {cmd[0]}"


def check_python_syntax() -> tuple[int, int]:
    """Check Python syntax for all .py files."""
    print_header("Python Syntax Check")

    project_root = Path(__file__).parent.parent
    py_files = list(project_root.glob("**/*.py"))
    py_files = [f for f in py_files if "node_modules" not in str(f) and "__pycache__" not in str(f)]

    passed = 0
    failed = 0

    for py_file in py_files:
        relative_path = py_file.relative_to(project_root)
        success, output = run_command([sys.executable, "-m", "py_compile", str(py_file)])

        if success:
            passed += 1
        else:
            failed += 1
            print_result(str(relative_path), False, output.strip()[:100])

    print(f"\n  Total: {passed} passed, {failed} failed")
    return passed, failed


def check_python_imports() -> tuple[int, int]:
    """Check that key Python modules can be imported."""
    print_header("Python Import Check")

    imports = [
        ("api.main", "app"),
        ("api.core.config", "Settings"),
        ("api.core.security", "create_access_token"),
        ("ml.percentile", "PercentileCalculator"),
        ("ml.recommendations", "RecommendationEngine"),
        ("companion.watcher", "SavedVariablesWatcher"),
        ("companion.sync", "SyncClient"),
    ]

    passed = 0
    failed = 0

    for module, attr in imports:
        try:
            exec(f"from {module} import {attr}")
            print_result(f"{module}.{attr}", True)
            passed += 1
        except Exception as e:
            print_result(f"{module}.{attr}", False, str(e)[:100])
            failed += 1

    return passed, failed


def check_json_data() -> tuple[int, int]:
    """Validate JSON data files."""
    print_header("JSON Data Validation")

    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data" / "raw"

    passed = 0
    failed = 0
    total_features = 0

    for json_file in sorted(data_dir.glob("*.json")):
        try:
            with open(json_file) as f:
                data = json.load(f)
            count = len(data)
            total_features += count
            print_result(f"{json_file.name}: {count} entries", True)
            passed += 1
        except json.JSONDecodeError as e:
            print_result(json_file.name, False, str(e)[:100])
            failed += 1

    print(f"\n  Total features: {total_features}")
    if total_features < 1900:
        print(f"  {YELLOW}Warning: Feature count below expected minimum (1900){RESET}")

    return passed, failed


def check_lua_syntax() -> tuple[int, int]:
    """Check Lua syntax (requires luac)."""
    print_header("Lua Syntax Check")

    # Check if luac is available
    success, _ = run_command(["luac", "-v"])
    if not success:
        print(f"  {YELLOW}luac not found, skipping Lua syntax check{RESET}")
        return 0, 0

    project_root = Path(__file__).parent.parent
    lua_files = list((project_root / "addon").glob("**/*.lua"))

    passed = 0
    failed = 0

    for lua_file in lua_files:
        relative_path = lua_file.relative_to(project_root)
        success, output = run_command(["luac", "-p", str(lua_file)])

        if success:
            print_result(str(relative_path), True)
            passed += 1
        else:
            print_result(str(relative_path), False, output.strip()[:100])
            failed += 1

    return passed, failed


def check_typescript() -> tuple[int, int]:
    """Check TypeScript compilation."""
    print_header("TypeScript Check")

    project_root = Path(__file__).parent.parent
    web_dir = project_root / "web"

    if not (web_dir / "node_modules").exists():
        print(f"  {YELLOW}node_modules not found, run 'npm install' in web/{RESET}")
        return 0, 0

    success, output = run_command(["npx", "tsc", "--noEmit"], cwd=web_dir)

    if success:
        print_result("TypeScript compilation", True)
        return 1, 0
    else:
        print_result("TypeScript compilation", False)
        # Print first few errors
        for line in output.split("\n")[:10]:
            if line.strip():
                print(f"         {line[:80]}")
        return 0, 1


def run_pytest() -> tuple[int, int]:
    """Run pytest tests."""
    print_header("Python Unit Tests")

    project_root = Path(__file__).parent.parent

    success, output = run_command(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=project_root
    )

    # Parse pytest output for results
    passed = output.count(" PASSED")
    failed = output.count(" FAILED")
    errors = output.count(" ERROR")

    # Print summary from pytest output
    for line in output.split("\n"):
        if "passed" in line.lower() or "failed" in line.lower() or "error" in line.lower():
            if "=" in line:
                print(f"  {line.strip()}")

    return passed, failed + errors


def main():
    """Run all checks."""
    print(f"\n{BLUE}ESO Build Optimizer - Test Runner{RESET}")
    print(f"{'=' * 60}")

    results = {}

    # Run all checks
    results["python_syntax"] = check_python_syntax()
    results["python_imports"] = check_python_imports()
    results["json_data"] = check_json_data()
    results["lua_syntax"] = check_lua_syntax()
    results["typescript"] = check_typescript()
    results["pytest"] = run_pytest()

    # Summary
    print_header("Summary")

    total_passed = sum(r[0] for r in results.values())
    total_failed = sum(r[1] for r in results.values())

    for name, (passed, failed) in results.items():
        status = f"{GREEN}✓{RESET}" if failed == 0 else f"{RED}✗{RESET}"
        print(f"  {status} {name}: {passed} passed, {failed} failed")

    print(f"\n  {'-' * 40}")
    print(f"  Total: {total_passed} passed, {total_failed} failed")

    if total_failed > 0:
        print(f"\n  {RED}Some checks failed!{RESET}")
        return 1
    else:
        print(f"\n  {GREEN}All checks passed!{RESET}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
