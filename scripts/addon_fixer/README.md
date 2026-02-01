# ESO Addon Fixer

Automated tool for fixing broken Elder Scrolls Online addons. This tool analyzes and repairs addons that have broken due to API changes, updating them to work with **APIVersion 101048** (Update 48 - January 2026).

## Features

- **API Version Updates**: Automatically updates manifest APIVersion to current
- **LibStub Removal**: Converts deprecated LibStub patterns to modern global variables
- **Deprecated Function Migration**: Renames/replaces deprecated API functions
- **Font Path Migration**: Converts .ttf/.otf paths to .slug format (Update 41+)
- **XML Virtual Control Fixes**: Updates virtual control inheritance and textures
- **Dependency Validation**: Verifies library dependencies and versions
- **Automatic Packaging**: Creates distribution-ready .zip files

## Quick Start

```bash
# Analyze an addon (no changes made)
python scripts/fix_addon.py analyze /path/to/MyAddon

# Fix an addon (creates backup)
python scripts/fix_addon.py fix /path/to/MyAddon

# Fix and package for distribution
python scripts/fix_addon.py fix /path/to/MyAddon -o /output/dir

# Dry run (preview changes)
python scripts/fix_addon.py fix /path/to/MyAddon --dry-run
```

## Commands

### analyze

Analyze an addon for issues without making changes.

```bash
python scripts/fix_addon.py analyze /path/to/addon [-v]
```

Options:
- `-v, --verbose`: Show detailed file-by-file analysis

### fix

Fix issues in an addon.

```bash
python scripts/fix_addon.py fix /path/to/addon [options]
```

Options:
- `-o, --output DIR`: Create packaged .zip in output directory
- `-v, --verbose`: Show detailed changes
- `--dry-run`: Preview changes without modifying files
- `--no-backup`: Skip backup creation
- `--no-version-update`: Don't update API version
- `--no-libstub-fix`: Don't fix LibStub patterns
- `--no-font-fix`: Don't fix font paths
- `--no-xml-fix`: Don't fix XML issues
- `--add-nil-guards`: Add nil guards for potentially-nil calls (aggressive)

### migrations

List known API migrations.

```bash
python scripts/fix_addon.py migrations [-c CATEGORY] [--version VERSION]
```

Options:
- `-c, --category`: Filter by category (champion_points, guild_store, etc.)
- `--version`: Filter by API version

### info

Show ESO API version information.

```bash
python scripts/fix_addon.py info
```

### export

Export migration database to JSON.

```bash
python scripts/fix_addon.py export [-o FILE]
```

## What Gets Fixed

### Manifest Updates

| Issue | Fix Applied |
|-------|-------------|
| Outdated APIVersion | Updated to `101047 101048` |
| LibStub dependency | Removed from DependsOn |
| Encoding issues | Converted to UTF-8, CRLF line endings |

### Lua Code Fixes

| Pattern | Replacement |
|---------|-------------|
| `LibStub("LibAddonMenu-2.0")` | `LibAddonMenu2` |
| `LibStub("LibFilters-3.0")` | `LibFilters3` |
| `GetUnitVeteranRank(unitTag)` | `GetUnitChampionPoints(unitTag)` |
| `"path/font.ttf\|16"` | `"path/font.slug\|16"` |

### XML Fixes

| Issue | Fix Applied |
|-------|-------------|
| Font paths with .ttf/.otf | Converted to .slug |
| Deprecated texture paths | Updated to current paths |

## Addon Complexity Guide

| Complexity | Addons | Notes |
|------------|--------|-------|
| Low | Dustman, Set Tracker | Simple fixes, usually work immediately |
| Medium | FTC, PersonalAssistant, CraftStore | May need manual review after fixes |
| High | AwesomeGuildStore | Complex dependency chains |
| Very High | Wykkyd Framework | Recommend replacement addons instead |

## Known Migrations

### Champion Points (API 100015)

| Old | New |
|-----|-----|
| `GetUnitVeteranRank` | `GetUnitChampionPoints` |
| `GetUnitVeteranPoints` | Removed |
| `IsUnitVeteran` | `GetUnitChampionPoints() > 0` |

### Guild Store (API 100027)

- `SetTradingHouseFilter` signature changed to variable arguments
- New async functions: `MatchTradingHouseItemNames()`

### Font Migration (API 101041)

- All `.ttf` and `.otf` paths must become `.slug`
- Use `game/client/slugfont.exe` to convert fonts

## Library Global Variables

Modern ESO addons access libraries via globals, not LibStub:

| Library | Global Variable |
|---------|-----------------|
| LibAddonMenu-2.0 | `LibAddonMenu2` |
| LibCustomMenu | `LibCustomMenu` |
| LibGPS3 | `LibGPS3` |
| LibAsync | `LibAsync` |
| LibFilters-3.0 | `LibFilters3` |
| LibHistoire | `LibHistoire` |
| LibDebugLogger | `LibDebugLogger` |

## Programmatic Usage

```python
from addon_fixer import AddonFixer, FixerConfig

# Configure fixes
config = FixerConfig(
    update_api_version=True,
    fix_libstub=True,
    fix_deprecated_functions=True,
    fix_font_paths=True,
    create_backup=True,
    dry_run=False,
)

# Fix an addon
fixer = AddonFixer(config)
result = fixer.fix("/path/to/addon", "/output/path")

print(f"Success: {result.success}")
print(f"Total changes: {result.total_changes}")
for change in result.manifest_result.changes:
    print(f"  - {change}")
```

## Testing

```bash
# Run addon fixer tests
pytest tests/test_addon_fixer.py -v

# Run with coverage
pytest tests/test_addon_fixer.py --cov=scripts/addon_fixer
```

## Contributing

When adding new migrations:

1. Add to `migrations.py` in the appropriate category
2. Add test cases in `test_addon_fixer.py`
3. Update this README with any new patterns

## Resources

- [ESOUI Wiki](https://wiki.esoui.com/Main_Page) - Official addon API documentation
- [esoui/esoui](https://github.com/esoui/esoui) - Official UI source code
- [UESP ESO API](https://esoapi.uesp.net/) - Historical API archive
- [ESOUI.com](https://www.esoui.com/) - Addon distribution

## License

MIT License - See project root LICENSE file.
