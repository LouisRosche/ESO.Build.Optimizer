"""
Command-line interface for ESO Addon Fixer.

Provides analyze, fix, and package commands for broken ESO addons.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .fixer import AddonFixer, FixerConfig, AddonFixResult
from .migrations import MigrationDatabase
from .constants import CURRENT_API_VERSION, PTS_API_VERSION

# ANSI color codes for terminal output
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def colorize(text: str, color: str) -> str:
    """Apply color to text if terminal supports it."""
    if sys.stdout.isatty():
        return f"{color}{text}{Colors.RESET}"
    return text


def print_header(text: str) -> None:
    """Print a header line."""
    print(colorize(f"\n{'='*60}", Colors.CYAN))
    print(colorize(f" {text}", Colors.BOLD + Colors.CYAN))
    print(colorize(f"{'='*60}", Colors.CYAN))


def print_section(text: str) -> None:
    """Print a section header."""
    print(colorize(f"\n--- {text} ---", Colors.BLUE))


def print_success(text: str) -> None:
    """Print success message."""
    print(colorize(f"  [OK] {text}", Colors.GREEN))


def print_warning(text: str) -> None:
    """Print warning message."""
    print(colorize(f"  [WARN] {text}", Colors.YELLOW))


def print_error(text: str) -> None:
    """Print error message."""
    print(colorize(f"  [ERR] {text}", Colors.RED))


def print_info(text: str) -> None:
    """Print info message."""
    print(colorize(f"  [INFO] {text}", Colors.WHITE))


def print_change(text: str) -> None:
    """Print change message."""
    print(colorize(f"  [FIX] {text}", Colors.MAGENTA))


def print_result(result: AddonFixResult, verbose: bool = False) -> None:
    """Print the result of an analysis or fix operation."""
    print_header(f"Addon: {result.addon_name}")

    # Summary
    status = colorize("SUCCESS", Colors.GREEN) if result.success else colorize("FAILED", Colors.RED)
    print(f"\nStatus: {status}")
    print(f"Path: {result.addon_path}")
    print(f"Total changes: {result.total_changes}")

    if result.backup_path:
        print(f"Backup: {result.backup_path}")
    if result.package_path:
        print(f"Package: {result.package_path}")

    # Errors
    if result.errors:
        print_section("Errors")
        for error in result.errors:
            print_error(error)

    # Warnings
    if result.warnings:
        print_section("Warnings")
        for warning in result.warnings:
            print_warning(warning)

    # Recommendations
    if result.recommendations:
        print_section("Recommendations")
        for rec in result.recommendations:
            print_info(rec)

    # Manifest changes
    if result.manifest_result and result.manifest_result.changes:
        print_section("Manifest Changes")
        for change in result.manifest_result.changes:
            print_change(change)

    # Lua file changes
    if verbose and result.lua_results:
        lua_with_changes = [r for r in result.lua_results if r.changes]
        if lua_with_changes:
            print_section("Lua File Changes")
            for lua_result in lua_with_changes:
                rel_path = lua_result.file_path.relative_to(result.addon_path)
                print(f"\n  {colorize(str(rel_path), Colors.CYAN)}:")
                for change in lua_result.changes:
                    print_change(change)

    # XML file changes
    if verbose and result.xml_results:
        xml_with_changes = [r for r in result.xml_results if r.changes]
        if xml_with_changes:
            print_section("XML File Changes")
            for xml_result in xml_with_changes:
                rel_path = xml_result.file_path.relative_to(result.addon_path)
                print(f"\n  {colorize(str(rel_path), Colors.CYAN)}:")
                for change in xml_result.changes:
                    print_change(change)

    # Validation result
    if result.validation_result and verbose:
        print_section("Dependency Validation")
        for dep in result.validation_result.dependencies:
            status = colorize("OK", Colors.GREEN) if dep.is_available else colorize("UNKNOWN", Colors.YELLOW)
            version_info = f" (v{dep.current_version})" if dep.current_version else ""
            print(f"  {dep.name}: {status}{version_info}")

    print()


def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze an addon without making changes."""
    addon_path = Path(args.addon_path)

    if not addon_path.exists():
        print_error(f"Addon path does not exist: {addon_path}")
        return 1

    if not addon_path.is_dir():
        print_error(f"Addon path is not a directory: {addon_path}")
        return 1

    config = FixerConfig(
        update_api_version=True,
        fix_libstub=True,
        fix_deprecated_functions=True,
        fix_font_paths=True,
        fix_xml_issues=True,
        validate_dependencies=True,
        dry_run=True,  # Analysis mode
    )

    fixer = AddonFixer(config)
    result = fixer.analyze(addon_path)

    print_result(result, verbose=args.verbose)

    return 0 if result.success else 1


def cmd_fix(args: argparse.Namespace) -> int:
    """Fix issues in an addon."""
    addon_path = Path(args.addon_path)

    if not addon_path.exists():
        print_error(f"Addon path does not exist: {addon_path}")
        return 1

    if not addon_path.is_dir():
        print_error(f"Addon path is not a directory: {addon_path}")
        return 1

    output_path = Path(args.output) if args.output else None

    config = FixerConfig(
        update_api_version=not args.no_version_update,
        fix_libstub=not args.no_libstub_fix,
        fix_deprecated_functions=True,
        fix_font_paths=not args.no_font_fix,
        fix_xml_issues=not args.no_xml_fix,
        add_nil_guards=args.add_nil_guards,
        validate_dependencies=True,
        create_backup=not args.no_backup,
        dry_run=args.dry_run,
    )

    fixer = AddonFixer(config)
    result = fixer.fix(addon_path, output_path)

    print_result(result, verbose=args.verbose)

    if args.dry_run:
        print(colorize("\n[DRY RUN] No changes were made.", Colors.YELLOW))

    return 0 if result.success else 1


def cmd_migrations(args: argparse.Namespace) -> int:
    """List known API migrations."""
    db = MigrationDatabase()

    if args.category:
        migrations = db.get_migrations_by_category(args.category)
        print_header(f"Migrations for category: {args.category}")
    elif args.version:
        migrations = db.get_migrations_by_version(args.version)
        print_header(f"Migrations for API version: {args.version}")
    else:
        migrations = list(db.function_migrations.values())
        print_header("All API Migrations")

    if not migrations:
        print_info("No migrations found matching criteria.")
        return 0

    for migration in migrations:
        print(f"\n  {colorize(migration.old_name, Colors.CYAN)}")
        print(f"    Type: {migration.migration_type.value}")
        if migration.new_name:
            print(f"    New name: {colorize(migration.new_name, Colors.GREEN)}")
        if migration.replacement_code:
            print(f"    Replacement: {migration.replacement_code}")
        if migration.version_deprecated:
            print(f"    Deprecated in: API {migration.version_deprecated}")
        if migration.version_removed:
            print(f"    Removed in: API {migration.version_removed}")
        if migration.notes:
            print(f"    Notes: {migration.notes}")

    print(f"\nTotal: {len(migrations)} migrations")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Export migration database to JSON."""
    db = MigrationDatabase()
    output_path = Path(args.output)

    db.export_to_json(output_path)
    print_success(f"Exported migration database to: {output_path}")

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show ESO API version information."""
    print_header("ESO API Version Information")

    print(f"\nCurrent Live API Version: {colorize(str(CURRENT_API_VERSION), Colors.GREEN)}")
    print(f"Current PTS API Version: {colorize(str(PTS_API_VERSION), Colors.YELLOW)}")

    print_section("Significant API Changes")

    from .constants import API_VERSION_HISTORY

    for version, info in sorted(API_VERSION_HISTORY.items()):
        print(f"\n  {colorize(str(version), Colors.CYAN)} - {info['update']}")
        for change in info.get("changes", []):
            print(f"    - {change}")

    return 0


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="eso-addon-fixer",
        description="Automated fixer for broken Elder Scrolls Online addons",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Analyze an addon:
    python -m addon_fixer analyze /path/to/MyAddon

  Fix an addon (with backup):
    python -m addon_fixer fix /path/to/MyAddon

  Fix and package for distribution:
    python -m addon_fixer fix /path/to/MyAddon -o /output/dir

  Dry run (show what would be changed):
    python -m addon_fixer fix /path/to/MyAddon --dry-run

  List all known migrations:
    python -m addon_fixer migrations

  Show API version info:
    python -m addon_fixer info
        """
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze an addon for issues without making changes"
    )
    analyze_parser.add_argument(
        "addon_path",
        help="Path to the addon folder"
    )
    analyze_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed file-by-file analysis"
    )

    # Fix command
    fix_parser = subparsers.add_parser(
        "fix",
        help="Fix issues in an addon"
    )
    fix_parser.add_argument(
        "addon_path",
        help="Path to the addon folder"
    )
    fix_parser.add_argument(
        "-o", "--output",
        help="Output directory for packaged addon (creates .zip)"
    )
    fix_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed changes"
    )
    fix_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )
    fix_parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create backup before fixing"
    )
    fix_parser.add_argument(
        "--no-version-update",
        action="store_true",
        help="Don't update API version"
    )
    fix_parser.add_argument(
        "--no-libstub-fix",
        action="store_true",
        help="Don't fix LibStub patterns"
    )
    fix_parser.add_argument(
        "--no-font-fix",
        action="store_true",
        help="Don't fix font paths"
    )
    fix_parser.add_argument(
        "--no-xml-fix",
        action="store_true",
        help="Don't fix XML issues"
    )
    fix_parser.add_argument(
        "--add-nil-guards",
        action="store_true",
        help="Add nil guards for potentially-nil function calls (aggressive)"
    )

    # Migrations command
    migrations_parser = subparsers.add_parser(
        "migrations",
        help="List known API migrations"
    )
    migrations_parser.add_argument(
        "-c", "--category",
        help="Filter by category (e.g., champion_points, guild_store)"
    )
    migrations_parser.add_argument(
        "--version",
        type=int,
        help="Filter by API version"
    )

    # Export command
    export_parser = subparsers.add_parser(
        "export",
        help="Export migration database to JSON"
    )
    export_parser.add_argument(
        "-o", "--output",
        default="eso_api_migrations.json",
        help="Output file path (default: eso_api_migrations.json)"
    )

    # Info command
    info_parser = subparsers.add_parser(
        "info",
        help="Show ESO API version information"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Handle commands
    if args.command == "analyze":
        return cmd_analyze(args)
    elif args.command == "fix":
        return cmd_fix(args)
    elif args.command == "migrations":
        return cmd_migrations(args)
    elif args.command == "export":
        return cmd_export(args)
    elif args.command == "info":
        return cmd_info(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
