"""
API migration database for ESO addon fixer.

Contains mappings of deprecated functions to their replacements,
parameter changes, and removal notices across ESO API versions.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class MigrationType(Enum):
    """Type of API migration."""
    RENAMED = "renamed"  # Function renamed, same signature
    SIGNATURE_CHANGED = "signature_changed"  # Parameters added/removed/reordered
    REMOVED = "removed"  # Function completely removed
    RETURN_CHANGED = "return_changed"  # Return value(s) changed
    DEPRECATED = "deprecated"  # Still works but will be removed
    REPLACED = "replaced"  # Different function with different name


@dataclass
class Migration:
    """Single API migration entry."""
    old_name: str
    migration_type: MigrationType
    new_name: Optional[str] = None
    old_signature: Optional[str] = None
    new_signature: Optional[str] = None
    version_deprecated: Optional[int] = None
    version_removed: Optional[int] = None
    notes: str = ""
    replacement_code: Optional[str] = None
    category: str = "general"


@dataclass
class EventMigration:
    """Event constant migration entry."""
    old_name: str
    removed: bool
    version_changed: int
    new_name: Optional[str] = None
    notes: str = ""


@dataclass
class LibraryMigration:
    """Library access pattern migration."""
    old_pattern: str
    new_pattern: str
    library_name: str
    global_var: str
    notes: str = ""


class MigrationDatabase:
    """Database of API migrations for ESO addons."""

    def __init__(self):
        """Initialize the migration database."""
        self.function_migrations: dict[str, Migration] = {}
        self.event_migrations: dict[str, EventMigration] = {}
        self.library_migrations: dict[str, LibraryMigration] = {}
        self._load_migrations()

    def _load_migrations(self) -> None:
        """Load all migration data."""
        self._load_function_migrations()
        self._load_event_migrations()
        self._load_library_migrations()

    def _load_function_migrations(self) -> None:
        """Load function migration mappings."""
        # Champion Points migration (Update 10 / API 100015)
        cp_migrations = [
            Migration(
                old_name="GetUnitVeteranRank",
                migration_type=MigrationType.RENAMED,
                new_name="GetUnitChampionPoints",
                version_deprecated=100015,
                category="champion_points",
                notes="Veteran Ranks replaced with Champion Points",
            ),
            Migration(
                old_name="GetUnitVeteranPoints",
                migration_type=MigrationType.REMOVED,
                version_removed=100015,
                category="champion_points",
                notes="Veteran Points system removed",
                replacement_code="-- GetUnitVeteranPoints removed, no replacement",
            ),
            Migration(
                old_name="IsUnitVeteran",
                migration_type=MigrationType.REPLACED,
                replacement_code="GetUnitChampionPoints(unitTag) > 0",
                version_deprecated=100015,
                category="champion_points",
                notes="Check CP > 0 instead",
            ),
            Migration(
                old_name="GetPlayerVeteranRank",
                migration_type=MigrationType.RENAMED,
                new_name="GetPlayerChampionPointsEarned",
                version_deprecated=100015,
                category="champion_points",
            ),
            Migration(
                old_name="GetMaxVeteranRank",
                migration_type=MigrationType.REMOVED,
                version_removed=100015,
                category="champion_points",
                replacement_code="GetMaxChampionPoints()",
            ),
        ]

        # Guild Store API changes (Update 21 / API 100027)
        guild_store_migrations = [
            Migration(
                old_name="SetTradingHouseFilter",
                migration_type=MigrationType.SIGNATURE_CHANGED,
                old_signature="SetTradingHouseFilter(filterType, ...)",
                new_signature="SetTradingHouseFilter(filterType, minValue, maxValue)",
                version_deprecated=100027,
                category="guild_store",
                notes="Changed from fixed parameters to variable arguments",
            ),
            Migration(
                old_name="SearchTradingHouse",
                migration_type=MigrationType.DEPRECATED,
                new_name="ExecuteTradingHouseSearch",
                version_deprecated=100027,
                category="guild_store",
            ),
        ]

        # Item API changes
        item_migrations = [
            Migration(
                old_name="GetItemType",
                migration_type=MigrationType.RETURN_CHANGED,
                old_signature="GetItemType(bagId, slotIndex) -> itemType",
                new_signature="GetItemType(bagId, slotIndex) -> itemType, specializedItemType",
                version_deprecated=100023,
                category="inventory",
                notes="Now returns two values: itemType and specializedItemType",
            ),
            Migration(
                old_name="GetItemInfo",
                migration_type=MigrationType.RETURN_CHANGED,
                version_deprecated=101033,
                category="inventory",
                notes="Return values expanded, check current signature",
            ),
        ]

        # Player stats API changes
        stat_migrations = [
            Migration(
                old_name="GetPlayerStat",
                migration_type=MigrationType.SIGNATURE_CHANGED,
                notes="Removed softCapOption parameter",
                version_deprecated=100027,
                category="stats",
            ),
        ]

        # Combat API changes
        combat_migrations = [
            Migration(
                old_name="GetUnitPower",
                migration_type=MigrationType.RETURN_CHANGED,
                old_signature="GetUnitPower(unitTag, powerType) -> current, max, effective",
                new_signature="GetUnitPower(unitTag, powerType) -> current, max, effectiveMax",
                version_deprecated=100023,
                category="combat",
            ),
            Migration(
                old_name="GetCriticalStrikeChance",
                migration_type=MigrationType.RENAMED,
                new_name="GetPlayerStat",
                notes="Use GetPlayerStat(STAT_CRITICAL_STRIKE) instead",
                version_deprecated=100027,
                category="combat",
                replacement_code="GetPlayerStat(STAT_CRITICAL_STRIKE)",
            ),
        ]

        # UI/Control API changes
        ui_migrations = [
            Migration(
                old_name="SetDesaturation",
                migration_type=MigrationType.SIGNATURE_CHANGED,
                old_signature="control:SetDesaturation(desaturation)",
                new_signature="control:SetDesaturation(desaturation)",
                version_deprecated=101041,
                category="ui",
                notes="Value range changed from 0-1 to boolean or normalized",
            ),
            Migration(
                old_name="PlaySound",
                migration_type=MigrationType.SIGNATURE_CHANGED,
                notes="Some sound constants renamed or removed",
                version_deprecated=101033,
                category="ui",
            ),
        ]

        # Zone/Map API changes
        zone_migrations = [
            Migration(
                old_name="GetZoneId",
                migration_type=MigrationType.SIGNATURE_CHANGED,
                version_deprecated=100027,
                category="zones",
                notes="Zone IDs restructured for new zones",
            ),
            Migration(
                old_name="GetMapPlayerPosition",
                migration_type=MigrationType.DEPRECATED,
                new_name="GetMapPlayerPosition",
                notes="Consider using LibGPS3 for accurate coordinates",
                category="zones",
            ),
        ]

        # Achievement API changes (Update 33)
        achievement_migrations = [
            Migration(
                old_name="GetAchievementProgress",
                migration_type=MigrationType.SIGNATURE_CHANGED,
                version_deprecated=101033,
                category="achievements",
                notes="Per-character tracking removed, now account-wide only",
            ),
        ]

        # Deprecated globals and constants
        deprecated_globals = [
            Migration(
                old_name="VETERAN_RANK_MAX",
                migration_type=MigrationType.REMOVED,
                version_removed=100015,
                category="constants",
                replacement_code="-- Use GetMaxChampionPoints() instead",
            ),
            Migration(
                old_name="SOUNDS.POSITIVE_CLICK",
                migration_type=MigrationType.RENAMED,
                new_name="SOUNDS.DEFAULT_CLICK",
                version_deprecated=100027,
                category="constants",
            ),
        ]

        # Endeavors API removal (Update 49 / API 101049)
        endeavor_migrations = [
            Migration(
                old_name="GetDailyEndeavors",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="endeavors",
                notes="Endeavors system removed in Update 49",
                replacement_code="-- GetDailyEndeavors removed (Endeavors system removed in U49)",
            ),
            Migration(
                old_name="GetWeeklyEndeavors",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="endeavors",
                notes="Endeavors system removed in Update 49",
                replacement_code="-- GetWeeklyEndeavors removed (Endeavors system removed in U49)",
            ),
            Migration(
                old_name="GetEndeavorsProgress",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="endeavors",
                notes="Endeavors system removed in Update 49",
                replacement_code="-- GetEndeavorsProgress removed (Endeavors system removed in U49)",
            ),
            Migration(
                old_name="GetEndeavorsInfo",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="endeavors",
                notes="Endeavors system removed in Update 49",
                replacement_code="-- GetEndeavorsInfo removed (Endeavors system removed in U49)",
            ),
            Migration(
                old_name="GetNumEndeavors",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="endeavors",
                notes="Endeavors system removed in Update 49",
                replacement_code="-- GetNumEndeavors removed (Endeavors system removed in U49)",
            ),
            Migration(
                old_name="IsEndeavorsSystemAvailable",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="endeavors",
                notes="Endeavors system removed in Update 49",
                replacement_code="-- IsEndeavorsSystemAvailable removed; always returns false equivalent",
            ),
        ]

        # Daily Login Rewards API removal (Update 49 / API 101049)
        daily_login_migrations = [
            Migration(
                old_name="GetDailyLoginRewardInfo",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="daily_login",
                notes="Daily Login Rewards system removed in Update 49",
                replacement_code="-- GetDailyLoginRewardInfo removed (Daily Login Rewards removed in U49)",
            ),
            Migration(
                old_name="GetDailyLoginRewardIndex",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="daily_login",
                notes="Daily Login Rewards system removed in Update 49",
                replacement_code="-- GetDailyLoginRewardIndex removed (Daily Login Rewards removed in U49)",
            ),
            Migration(
                old_name="GetNumDailyLoginRewards",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="daily_login",
                notes="Daily Login Rewards system removed in Update 49",
                replacement_code="-- GetNumDailyLoginRewards removed (Daily Login Rewards removed in U49)",
            ),
            Migration(
                old_name="IsDailyLoginRewardClaimed",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="daily_login",
                notes="Daily Login Rewards system removed in Update 49",
                replacement_code="-- IsDailyLoginRewardClaimed removed (Daily Login Rewards removed in U49)",
            ),
            Migration(
                old_name="ClaimDailyLoginReward",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="daily_login",
                notes="Daily Login Rewards system removed in Update 49",
                replacement_code="-- ClaimDailyLoginReward removed (Daily Login Rewards removed in U49)",
            ),
            Migration(
                old_name="GetDailyLoginClaimableRewardIndex",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="daily_login",
                notes="Daily Login Rewards system removed in Update 49",
                replacement_code="-- GetDailyLoginClaimableRewardIndex removed (Daily Login Rewards removed in U49)",
            ),
        ]

        # Transmute Crystal cap change (Update 49 / API 101049)
        transmute_migrations = [
            Migration(
                old_name="GetMaxTransmuteCrystals",
                migration_type=MigrationType.RETURN_CHANGED,
                version_deprecated=101049,
                category="currency",
                notes="Transmute Crystal cap tripled from 1000 to 3000 in U49. Function still works but returns new max.",
            ),
        ]

        # Tamriel Tomes API - new in Update 49 (API 101049)
        tamriel_tomes_migrations = [
            Migration(
                old_name="GetTomeProgressionInfo",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="tamriel_tomes",
                notes="New in U49: Tamriel Tomes progression. Not available on API < 101049.",
                replacement_code="-- GetTomeProgressionInfo is new in API 101049 (U49)",
            ),
            Migration(
                old_name="GetNumTomePoints",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="tamriel_tomes",
                notes="New in U49: Tome Points currency. Not available on API < 101049.",
                replacement_code="-- GetNumTomePoints is new in API 101049 (U49)",
            ),
            Migration(
                old_name="GetNumPremiumTomeTokens",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="tamriel_tomes",
                notes="New in U49: Premium Tome Tokens currency. Not available on API < 101049.",
                replacement_code="-- GetNumPremiumTomeTokens is new in API 101049 (U49)",
            ),
            Migration(
                old_name="GetCurrentTomeSeason",
                migration_type=MigrationType.REMOVED,
                version_removed=101049,
                category="tamriel_tomes",
                notes="New in U49: Tamriel Tomes season info. Not available on API < 101049.",
                replacement_code="-- GetCurrentTomeSeason is new in API 101049 (U49)",
            ),
        ]

        # Outfit Slot API changes - now account-wide (Update 49 / API 101049)
        outfit_migrations = [
            Migration(
                old_name="GetOutfitSlotDataForCharacter",
                migration_type=MigrationType.REPLACED,
                version_deprecated=101049,
                version_removed=101049,
                category="outfit",
                notes="Outfit Slots are now account-wide in U49. Character-specific API removed.",
                replacement_code="GetOutfitSlotData(outfitIndex, slotIndex)",
            ),
            Migration(
                old_name="SetOutfitSlotForCharacter",
                migration_type=MigrationType.REPLACED,
                version_deprecated=101049,
                version_removed=101049,
                category="outfit",
                notes="Outfit Slots are now account-wide in U49. Character-specific API removed.",
                replacement_code="SetOutfitSlot(outfitIndex, slotIndex, collectibleId)",
            ),
            Migration(
                old_name="GetNumOutfitsForCharacter",
                migration_type=MigrationType.RENAMED,
                new_name="GetNumOutfits",
                version_deprecated=101049,
                version_removed=101049,
                category="outfit",
                notes="Outfit Slots are now account-wide in U49. No character parameter needed.",
            ),
            Migration(
                old_name="RenameOutfitForCharacter",
                migration_type=MigrationType.RENAMED,
                new_name="RenameOutfit",
                version_deprecated=101049,
                version_removed=101049,
                category="outfit",
                notes="Outfit Slots are now account-wide in U49. No character parameter needed.",
            ),
        ]

        # Currency constant changes (Update 49 / API 101049)
        currency_migrations = [
            Migration(
                old_name="GetCurrencyAmount",
                migration_type=MigrationType.SIGNATURE_CHANGED,
                version_deprecated=101049,
                category="currency",
                notes="Event Tickets (CURT_EVENT_TICKETS) and Endeavor Seals (CURT_ENDEAVOR_SEALS) currency types removed in U49. New types added: CURT_TRADE_BARS, CURT_OUTFIT_CHANGE_TOKENS, CURT_TOME_POINTS, CURT_PREMIUM_TOME_TOKENS.",
            ),
        ]

        # Experience API changes (Update 49 / API 101049)
        experience_migrations = [
            Migration(
                old_name="GetUnitXPBarInfo",
                migration_type=MigrationType.RETURN_CHANGED,
                version_deprecated=101049,
                category="experience",
                notes="Back bar now earns equal XP in U49. XP values no longer differ based on active bar.",
            ),
        ]

        # Compile all migrations
        all_migrations = (
            cp_migrations +
            guild_store_migrations +
            item_migrations +
            stat_migrations +
            combat_migrations +
            ui_migrations +
            zone_migrations +
            achievement_migrations +
            deprecated_globals +
            endeavor_migrations +
            daily_login_migrations +
            transmute_migrations +
            tamriel_tomes_migrations +
            outfit_migrations +
            currency_migrations +
            experience_migrations
        )

        for migration in all_migrations:
            self.function_migrations[migration.old_name] = migration

    def _load_event_migrations(self) -> None:
        """Load event constant migration mappings."""
        # Veteran system events (Update 10 / API 100015)
        veteran_event_migrations = [
            EventMigration(
                old_name="EVENT_VETERAN_RANK_UPDATE",
                removed=True,
                version_changed=100015,
                notes="Veteran system removed. Use EVENT_CHAMPION_POINT_UPDATE instead.",
            ),
            EventMigration(
                old_name="EVENT_VETERAN_POINTS_UPDATE",
                removed=True,
                version_changed=100015,
                notes="Veteran system removed.",
            ),
        ]

        # Endeavors events removed (Update 49 / API 101049)
        endeavor_event_migrations = [
            EventMigration(
                old_name="EVENT_ENDEAVOR_PROGRESS_UPDATE",
                removed=True,
                version_changed=101049,
                notes="Endeavors system removed in Update 49.",
            ),
            EventMigration(
                old_name="EVENT_ENDEAVOR_COMPLETED",
                removed=True,
                version_changed=101049,
                notes="Endeavors system removed in Update 49.",
            ),
            EventMigration(
                old_name="EVENT_ENDEAVORS_RESET",
                removed=True,
                version_changed=101049,
                notes="Endeavors system removed in Update 49.",
            ),
        ]

        # Daily Login Rewards events removed (Update 49 / API 101049)
        daily_login_event_migrations = [
            EventMigration(
                old_name="EVENT_DAILY_LOGIN_REWARDS_UPDATED",
                removed=True,
                version_changed=101049,
                notes="Daily Login Rewards system removed in Update 49.",
            ),
            EventMigration(
                old_name="EVENT_DAILY_LOGIN_REWARDS_CLAIMED",
                removed=True,
                version_changed=101049,
                notes="Daily Login Rewards system removed in Update 49.",
            ),
        ]

        # Outfit events changed (Update 49 / API 101049)
        outfit_event_migrations = [
            EventMigration(
                old_name="EVENT_OUTFIT_CHANGE_RESPONSE",
                removed=False,
                version_changed=101049,
                new_name="EVENT_OUTFIT_CHANGE_RESPONSE",
                notes="Outfit events now account-wide in U49. Character parameter removed from callback.",
            ),
        ]

        # Compile all event migrations
        all_event_migrations = (
            veteran_event_migrations +
            endeavor_event_migrations +
            daily_login_event_migrations +
            outfit_event_migrations
        )

        for migration in all_event_migrations:
            self.event_migrations[migration.old_name] = migration

    def _load_library_migrations(self) -> None:
        """Load library access pattern migrations."""
        # LibStub patterns that need replacement
        libstub_patterns = [
            LibraryMigration(
                old_pattern='LibStub("LibAddonMenu-2.0")',
                new_pattern="LibAddonMenu2",
                library_name="LibAddonMenu-2.0",
                global_var="LibAddonMenu2",
                notes="LibStub is deprecated since Summerset",
            ),
            LibraryMigration(
                old_pattern='LibStub("LibAddonMenu")',
                new_pattern="LibAddonMenu2",
                library_name="LibAddonMenu",
                global_var="LibAddonMenu2",
            ),
            LibraryMigration(
                old_pattern='LibStub:GetLibrary("LibAddonMenu-2.0")',
                new_pattern="LibAddonMenu2",
                library_name="LibAddonMenu-2.0",
                global_var="LibAddonMenu2",
            ),
            LibraryMigration(
                old_pattern='LibStub("LibCustomMenu")',
                new_pattern="LibCustomMenu",
                library_name="LibCustomMenu",
                global_var="LibCustomMenu",
            ),
            LibraryMigration(
                old_pattern='LibStub("LibFilters-3.0")',
                new_pattern="LibFilters3",
                library_name="LibFilters-3.0",
                global_var="LibFilters3",
            ),
            LibraryMigration(
                old_pattern='LibStub("LibGPS3")',
                new_pattern="LibGPS3",
                library_name="LibGPS3",
                global_var="LibGPS3",
            ),
            LibraryMigration(
                old_pattern='LibStub("LibAsync")',
                new_pattern="LibAsync",
                library_name="LibAsync",
                global_var="LibAsync",
            ),
            LibraryMigration(
                old_pattern='LibStub("LibHistoire")',
                new_pattern="LibHistoire",
                library_name="LibHistoire",
                global_var="LibHistoire",
            ),
            LibraryMigration(
                old_pattern='LibStub("LibDebugLogger")',
                new_pattern="LibDebugLogger",
                library_name="LibDebugLogger",
                global_var="LibDebugLogger",
            ),
            LibraryMigration(
                old_pattern='LibStub("LibChatMessage")',
                new_pattern="LibChatMessage",
                library_name="LibChatMessage",
                global_var="LibChatMessage",
            ),
        ]

        for migration in libstub_patterns:
            self.library_migrations[migration.library_name] = migration

    def get_function_migration(self, func_name: str) -> Optional[Migration]:
        """Look up migration for a function name."""
        return self.function_migrations.get(func_name)

    def get_library_migration(self, lib_name: str) -> Optional[LibraryMigration]:
        """Look up migration for a library."""
        return self.library_migrations.get(lib_name)

    def get_all_deprecated_functions(self) -> list[str]:
        """Get list of all deprecated function names."""
        return list(self.function_migrations.keys())

    def get_migrations_by_category(self, category: str) -> list[Migration]:
        """Get all migrations for a category."""
        return [
            m for m in self.function_migrations.values()
            if m.category == category
        ]

    def get_migrations_by_version(self, api_version: int) -> list[Migration]:
        """Get migrations that became relevant at a specific API version."""
        return [
            m for m in self.function_migrations.values()
            if m.version_deprecated == api_version or m.version_removed == api_version
        ]

    def get_event_migration(self, event_name: str) -> Optional[EventMigration]:
        """Look up migration for an event constant."""
        return self.event_migrations.get(event_name)

    def get_all_deprecated_events(self) -> list[str]:
        """Get list of all deprecated event constant names."""
        return list(self.event_migrations.keys())

    def get_event_migrations_by_version(self, api_version: int) -> list[EventMigration]:
        """Get event migrations that became relevant at a specific API version."""
        return [
            m for m in self.event_migrations.values()
            if m.version_changed == api_version
        ]

    def export_to_json(self, output_path: Path) -> None:
        """Export migration database to JSON file."""
        data = {
            "functions": {
                name: {
                    "old_name": m.old_name,
                    "migration_type": m.migration_type.value,
                    "new_name": m.new_name,
                    "old_signature": m.old_signature,
                    "new_signature": m.new_signature,
                    "version_deprecated": m.version_deprecated,
                    "version_removed": m.version_removed,
                    "notes": m.notes,
                    "replacement_code": m.replacement_code,
                    "category": m.category,
                }
                for name, m in self.function_migrations.items()
            },
            "libraries": {
                name: {
                    "old_pattern": m.old_pattern,
                    "new_pattern": m.new_pattern,
                    "library_name": m.library_name,
                    "global_var": m.global_var,
                    "notes": m.notes,
                }
                for name, m in self.library_migrations.items()
            },
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported migration database to {output_path}")


# Additional common patterns that need fixing (not function-specific)
COMMON_PATTERNS = {
    # Font path patterns (.ttf → .slug)
    "font_paths": {
        "pattern": r'(["\'])([^"\']+)\.(ttf|otf)(\|[^"\']+)?(["\'])',
        "replacement": r'\1\2.slug\4\5',
        "notes": "Convert TTF/OTF fonts to Slug format (Update 41+)",
    },

    # Texture path updates
    "texture_paths": {
        "pattern": r'EsoUI/Art/(\w+)/(\w+)\.dds',
        "notes": "Some texture paths changed in various updates",
    },

    # Old control creation patterns
    "control_creation": {
        "old": "WINDOW_MANAGER:CreateControl",
        "new": "CreateControl",
        "notes": "CreateControl is now a global function",
    },

    # Old ZO_Object patterns
    "zo_object": {
        "old": "ZO_Object.Subclass()",
        "new": "ZO_InitializingObject:Subclass()",
        "notes": "ZO_InitializingObject is preferred for automatic initialization",
    },
}


# Nil-guarded function wrappers
NIL_GUARD_TEMPLATES = {
    "simple": '''
local function SafeCall_{func_name}(...)
    if {func_name} then
        return {func_name}(...)
    end
    return nil
end
''',

    "with_fallback": '''
local function SafeCall_{func_name}(...)
    if {func_name} then
        return {func_name}(...)
    end
    return {fallback}
end
''',

    "check_and_call": '''
if {func_name} then
    {func_name}({args})
end
''',
}
