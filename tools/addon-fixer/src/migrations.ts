/**
 * Comprehensive API migration database for ESO addon fixer.
 *
 * Each migration includes:
 * - Confidence level (0.0-1.0) for precision
 * - Exceptions where the migration doesn't apply
 * - Clear categorization for filtering
 *
 * IMPORTANT: Only migrations with confidence >= threshold will auto-fix.
 * Lower confidence items are flagged for manual review.
 */

import type { FunctionMigration, LibraryMigration, APIVersionInfo } from './types.js';

// ============================================================================
// API Version History
// ============================================================================

export const API_VERSION_HISTORY: readonly APIVersionInfo[] = [
  {
    version: 100003,
    update: 'Launch',
    releaseDate: '2014-04-04',
    isLive: false,
    isPTS: false,
    significantChanges: [
      'Major API restrictions for security',
      'Combat event limitations introduced',
    ],
  },
  {
    version: 100015,
    update: 'Update 10 - Orsinium',
    releaseDate: '2015-11-02',
    isLive: false,
    isPTS: false,
    significantChanges: [
      'Veteran Ranks replaced with Champion Points',
      'GetUnitVeteranRank → GetUnitChampionPoints',
      'IsUnitVeteran removed',
    ],
  },
  {
    version: 100023,
    update: 'Update 18 - Summerset Prep',
    releaseDate: '2018-05-21',
    isLive: false,
    isPTS: false,
    significantChanges: [
      '64-bit Lua support',
      'Larger SavedVariables files allowed',
      'GetItemType now returns two values',
    ],
  },
  {
    version: 100027,
    update: 'Update 21 - Wrathstone',
    releaseDate: '2019-02-25',
    isLive: false,
    isPTS: false,
    significantChanges: [
      'Guild store text search API overhaul',
      'SetTradingHouseFilter signature changed',
    ],
  },
  {
    version: 100030,
    update: 'Update 30 - Blackwood',
    releaseDate: '2021-06-01',
    isLive: false,
    isPTS: false,
    significantChanges: [
      'Removed "Allow out of date addons" checkbox',
      'Addons load regardless of version mismatch',
    ],
  },
  {
    version: 101033,
    update: 'Update 33 - High Isle',
    releaseDate: '2022-03-14',
    isLive: false,
    isPTS: false,
    significantChanges: [
      'Per-character achievement tracking removed (account-wide only)',
      'Various sound constant renames',
    ],
  },
  {
    version: 101041,
    update: 'Update 41 - Necrom',
    releaseDate: '2023-06-05',
    isLive: false,
    isPTS: false,
    significantChanges: [
      'Slug font format migration (.ttf → .slug)',
      'slugfont.exe converter added to game client',
    ],
  },
  {
    version: 101046,
    update: 'Update 46 - Gold Road',
    releaseDate: '2024-06-03',
    isLive: false,
    isPTS: false,
    significantChanges: [
      'Subclassing system introduced',
      'Console addon support announced',
    ],
  },
  {
    version: 101048,
    update: 'Update 48 - Seasons of the Worm Cult',
    releaseDate: '2026-01-13',
    isLive: false,
    isPTS: false,
    significantChanges: [
      'Previous live version',
    ],
  },
  {
    version: 101049,
    update: 'Update 49 - Tamriel Tomes',
    releaseDate: '2026-03-09',
    isLive: true,
    isPTS: false,
    significantChanges: [
      'Current live version',
      'Endeavors and Daily Login Rewards systems removed',
      'Dragonknight class ability rework (visual effects, animations, audio)',
      'Two-Handed skill line updates',
      'Outfit Slots now account-wide (character-specific API removed)',
      'Back bar now earns equal XP (experience API changes)',
      'Transmute Crystal cap tripled (1000 → 3000)',
      'New Tamriel Tomes system (Tome Points, Premium Tome Tokens)',
      'New currencies: Trade Bars, Outfit Change Tokens',
      'Event Tickets and Endeavors currency removed',
    ],
  },
];

// ============================================================================
// Function Migrations
// ============================================================================

/**
 * Function migrations with confidence levels.
 *
 * Confidence guidelines:
 * - 1.0: Definite removal/rename, always safe to fix
 * - 0.9: Very high confidence, minor edge cases
 * - 0.8: High confidence, recommended threshold
 * - 0.7: Moderate confidence, may need review
 * - 0.5: Low confidence, informational only
 */
export const FUNCTION_MIGRATIONS: readonly FunctionMigration[] = [
  // ==================== Champion Points (API 100015) ====================
  {
    oldName: 'GetUnitVeteranRank',
    migrationType: 'renamed',
    newName: 'GetUnitChampionPoints',
    versionDeprecated: 100015,
    versionRemoved: 100015,
    category: 'champion_points',
    notes: 'Veteran Ranks replaced with Champion Points in Update 10',
    confidence: 1.0,
    autoFixable: true,
  },
  {
    oldName: 'GetUnitVeteranPoints',
    migrationType: 'removed',
    versionRemoved: 100015,
    category: 'champion_points',
    notes: 'Veteran Points system removed entirely',
    replacementCode: '-- GetUnitVeteranPoints removed (no replacement)',
    confidence: 1.0,
    autoFixable: false, // No direct replacement
  },
  {
    oldName: 'IsUnitVeteran',
    migrationType: 'replaced',
    replacementCode: 'GetUnitChampionPoints(unitTag) > 0',
    versionDeprecated: 100015,
    versionRemoved: 100015,
    category: 'champion_points',
    notes: 'Check CP > 0 instead of veteran status',
    confidence: 0.9,
    autoFixable: false, // Replacement is an expression, not a rename
  },
  {
    oldName: 'GetPlayerVeteranRank',
    migrationType: 'renamed',
    newName: 'GetPlayerChampionPointsEarned',
    versionDeprecated: 100015,
    versionRemoved: 100015,
    category: 'champion_points',
    notes: 'Returns total CP earned by player',
    confidence: 1.0,
    autoFixable: true,
  },
  {
    oldName: 'GetMaxVeteranRank',
    migrationType: 'removed',
    replacementCode: 'GetMaxChampionPoints()',
    versionRemoved: 100015,
    category: 'champion_points',
    notes: 'Use GetMaxChampionPoints() instead',
    confidence: 1.0,
    autoFixable: false,
  },

  // ==================== Guild Store (API 100027) ====================
  {
    oldName: 'SearchTradingHouse',
    migrationType: 'deprecated',
    newName: 'ExecuteTradingHouseSearch',
    versionDeprecated: 100027,
    category: 'guild_store',
    notes: 'Renamed for clarity',
    confidence: 0.9,
    autoFixable: true,
  },

  // ==================== Item API (API 100023+) ====================
  // NOTE: GetItemType still works, just returns an extra value now
  // This is NOT a breaking change - we should NOT flag it as deprecated
  // Removing from auto-detection to prevent false positives

  // ==================== Removed Constants ====================
  {
    oldName: 'VETERAN_RANK_MAX',
    migrationType: 'removed',
    versionRemoved: 100015,
    category: 'constants',
    notes: 'Constant removed with Veteran Rank system',
    replacementCode: 'GetMaxChampionPoints()',
    confidence: 1.0,
    autoFixable: false,
  },

  // ==================== Sound Constants (API 101033) ====================
  {
    oldName: 'SOUNDS.POSITIVE_CLICK',
    migrationType: 'renamed',
    newName: 'SOUNDS.DEFAULT_CLICK',
    versionDeprecated: 100027,
    category: 'sounds',
    notes: 'Sound constant renamed',
    confidence: 0.85,
    autoFixable: true,
  },

  // ==================== Endeavors API Removal (API 101049) ====================
  {
    oldName: 'GetDailyEndeavors',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'endeavors',
    notes: 'Endeavors system removed in Update 49',
    replacementCode: '-- GetDailyEndeavors removed (Endeavors system removed in U49)',
    confidence: 1.0,
    autoFixable: false,
  },
  {
    oldName: 'GetWeeklyEndeavors',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'endeavors',
    notes: 'Endeavors system removed in Update 49',
    replacementCode: '-- GetWeeklyEndeavors removed (Endeavors system removed in U49)',
    confidence: 1.0,
    autoFixable: false,
  },
  {
    oldName: 'GetEndeavorsProgress',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'endeavors',
    notes: 'Endeavors system removed in Update 49',
    replacementCode: '-- GetEndeavorsProgress removed (Endeavors system removed in U49)',
    confidence: 1.0,
    autoFixable: false,
  },
  {
    oldName: 'GetEndeavorsInfo',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'endeavors',
    notes: 'Endeavors system removed in Update 49',
    replacementCode: '-- GetEndeavorsInfo removed (Endeavors system removed in U49)',
    confidence: 1.0,
    autoFixable: false,
  },
  {
    oldName: 'GetNumEndeavors',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'endeavors',
    notes: 'Endeavors system removed in Update 49',
    replacementCode: '-- GetNumEndeavors removed (Endeavors system removed in U49)',
    confidence: 1.0,
    autoFixable: false,
  },
  {
    oldName: 'IsEndeavorsSystemAvailable',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'endeavors',
    notes: 'Endeavors system removed in Update 49',
    replacementCode: '-- IsEndeavorsSystemAvailable removed; always returns false equivalent',
    confidence: 1.0,
    autoFixable: false,
  },

  // ==================== Daily Login Rewards API Removal (API 101049) ====================
  {
    oldName: 'GetDailyLoginRewardInfo',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'daily_login',
    notes: 'Daily Login Rewards system removed in Update 49',
    replacementCode: '-- GetDailyLoginRewardInfo removed (Daily Login Rewards removed in U49)',
    confidence: 1.0,
    autoFixable: false,
  },
  {
    oldName: 'GetDailyLoginRewardIndex',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'daily_login',
    notes: 'Daily Login Rewards system removed in Update 49',
    replacementCode: '-- GetDailyLoginRewardIndex removed (Daily Login Rewards removed in U49)',
    confidence: 1.0,
    autoFixable: false,
  },
  {
    oldName: 'GetNumDailyLoginRewards',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'daily_login',
    notes: 'Daily Login Rewards system removed in Update 49',
    replacementCode: '-- GetNumDailyLoginRewards removed (Daily Login Rewards removed in U49)',
    confidence: 1.0,
    autoFixable: false,
  },
  {
    oldName: 'IsDailyLoginRewardClaimed',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'daily_login',
    notes: 'Daily Login Rewards system removed in Update 49',
    replacementCode: '-- IsDailyLoginRewardClaimed removed (Daily Login Rewards removed in U49)',
    confidence: 1.0,
    autoFixable: false,
  },
  {
    oldName: 'ClaimDailyLoginReward',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'daily_login',
    notes: 'Daily Login Rewards system removed in Update 49',
    replacementCode: '-- ClaimDailyLoginReward removed (Daily Login Rewards removed in U49)',
    confidence: 1.0,
    autoFixable: false,
  },
  {
    oldName: 'GetDailyLoginClaimableRewardIndex',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'daily_login',
    notes: 'Daily Login Rewards system removed in Update 49',
    replacementCode: '-- GetDailyLoginClaimableRewardIndex removed (Daily Login Rewards removed in U49)',
    confidence: 1.0,
    autoFixable: false,
  },

  // ==================== Transmute Crystal Cap (API 101049) ====================
  {
    oldName: 'GetMaxTransmuteCrystals',
    migrationType: 'return_changed',
    versionDeprecated: 101049,
    category: 'currency',
    notes: 'Transmute Crystal cap tripled from 1000 to 3000 in Update 49. Function still works but returns new max.',
    confidence: 0.7,
    autoFixable: false,
    exceptions: ['Addons that query this dynamically are unaffected'],
  },

  // ==================== Tamriel Tomes API (API 101049) ====================
  // Note: These are new functions. Addons referencing them on older API will get nil.
  // We track them here for forward-compatibility awareness.
  {
    oldName: 'GetTomeProgressionInfo',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'tamriel_tomes',
    notes: 'New in U49: Tamriel Tomes progression. Not available on API < 101049.',
    replacementCode: '-- GetTomeProgressionInfo is new in API 101049 (U49)',
    confidence: 0.5,
    autoFixable: false,
  },
  {
    oldName: 'GetNumTomePoints',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'tamriel_tomes',
    notes: 'New in U49: Tome Points currency. Not available on API < 101049.',
    replacementCode: '-- GetNumTomePoints is new in API 101049 (U49)',
    confidence: 0.5,
    autoFixable: false,
  },
  {
    oldName: 'GetNumPremiumTomeTokens',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'tamriel_tomes',
    notes: 'New in U49: Premium Tome Tokens currency. Not available on API < 101049.',
    replacementCode: '-- GetNumPremiumTomeTokens is new in API 101049 (U49)',
    confidence: 0.5,
    autoFixable: false,
  },
  {
    oldName: 'GetCurrentTomeSeason',
    migrationType: 'removed',
    versionRemoved: 101049,
    category: 'tamriel_tomes',
    notes: 'New in U49: Tamriel Tomes season info. Not available on API < 101049.',
    replacementCode: '-- GetCurrentTomeSeason is new in API 101049 (U49)',
    confidence: 0.5,
    autoFixable: false,
  },

  // ==================== Outfit Slot API Changes (API 101049) ====================
  {
    oldName: 'GetOutfitSlotDataForCharacter',
    migrationType: 'replaced',
    replacementCode: 'GetOutfitSlotData(outfitIndex, slotIndex)',
    versionDeprecated: 101049,
    versionRemoved: 101049,
    category: 'outfit',
    notes: 'Outfit Slots are now account-wide in U49. Character-specific API removed.',
    confidence: 0.9,
    autoFixable: false,
  },
  {
    oldName: 'SetOutfitSlotForCharacter',
    migrationType: 'replaced',
    replacementCode: 'SetOutfitSlot(outfitIndex, slotIndex, collectibleId)',
    versionDeprecated: 101049,
    versionRemoved: 101049,
    category: 'outfit',
    notes: 'Outfit Slots are now account-wide in U49. Character-specific API removed.',
    confidence: 0.9,
    autoFixable: false,
  },
  {
    oldName: 'GetNumOutfitsForCharacter',
    migrationType: 'renamed',
    newName: 'GetNumOutfits',
    versionDeprecated: 101049,
    versionRemoved: 101049,
    category: 'outfit',
    notes: 'Outfit Slots are now account-wide in U49. No character parameter needed.',
    confidence: 0.9,
    autoFixable: true,
  },
  {
    oldName: 'RenameOutfitForCharacter',
    migrationType: 'renamed',
    newName: 'RenameOutfit',
    versionDeprecated: 101049,
    versionRemoved: 101049,
    category: 'outfit',
    notes: 'Outfit Slots are now account-wide in U49. No character parameter needed.',
    confidence: 0.9,
    autoFixable: true,
  },

  // ==================== Removed Currencies (API 101049) ====================
  {
    oldName: 'GetCurrencyAmount',
    migrationType: 'signature_changed',
    versionDeprecated: 101049,
    category: 'currency',
    notes: 'Event Tickets and Endeavor Seals currency types removed in U49. GetCurrencyAmount with CURT_EVENT_TICKETS or CURT_ENDEAVOR_SEALS will return 0. New currency types added: CURT_TRADE_BARS, CURT_OUTFIT_CHANGE_TOKENS, CURT_TOME_POINTS, CURT_PREMIUM_TOME_TOKENS.',
    confidence: 0.7,
    autoFixable: false,
    exceptions: ['Addons that only use standard currency types (gold, AP, Tel Var) are unaffected'],
  },

  // ==================== Experience API Changes (API 101049) ====================
  {
    oldName: 'GetUnitXPBarInfo',
    migrationType: 'return_changed',
    versionDeprecated: 101049,
    category: 'experience',
    notes: 'Back bar now earns equal XP in U49. XP values no longer differ based on active bar.',
    confidence: 0.7,
    autoFixable: false,
    exceptions: ['Addons that do not differentiate front/back bar XP are unaffected'],
  },
];

// ============================================================================
// Library Migrations (LibStub replacements)
// ============================================================================

export const LIBRARY_MIGRATIONS: readonly LibraryMigration[] = [
  {
    libraryName: 'LibAddonMenu-2.0',
    oldPatterns: [
      'LibStub("LibAddonMenu-2.0")',
      'LibStub("LibAddonMenu-2.0", true)',
      'LibStub:GetLibrary("LibAddonMenu-2.0")',
    ],
    globalVariable: 'LibAddonMenu2',
    minVersion: 28,
    notes: 'LibStub deprecated since Summerset. Use global variable.',
  },
  {
    libraryName: 'LibAddonMenu',
    oldPatterns: [
      'LibStub("LibAddonMenu")',
    ],
    globalVariable: 'LibAddonMenu2',
    notes: 'Old library name, use LibAddonMenu2 global',
  },
  {
    libraryName: 'LibCustomMenu',
    oldPatterns: [
      'LibStub("LibCustomMenu")',
      'LibStub:GetLibrary("LibCustomMenu")',
    ],
    globalVariable: 'LibCustomMenu',
    minVersion: 7,
    notes: 'Context menu library',
  },
  {
    libraryName: 'LibFilters-3.0',
    oldPatterns: [
      'LibStub("LibFilters-3.0")',
    ],
    globalVariable: 'LibFilters3',
    notes: 'Inventory filtering library',
  },
  {
    libraryName: 'LibGPS3',
    oldPatterns: [
      'LibStub("LibGPS3")',
      'LibStub("LibGPS")',
    ],
    globalVariable: 'LibGPS3',
    notes: 'Map coordinate library',
  },
  {
    libraryName: 'LibAsync',
    oldPatterns: [
      'LibStub("LibAsync")',
    ],
    globalVariable: 'LibAsync',
    notes: 'Async task scheduling',
  },
  {
    libraryName: 'LibHistoire',
    oldPatterns: [
      'LibStub("LibHistoire")',
    ],
    globalVariable: 'LibHistoire',
    notes: 'Guild history coordination',
  },
  {
    libraryName: 'LibDebugLogger',
    oldPatterns: [
      'LibStub("LibDebugLogger")',
    ],
    globalVariable: 'LibDebugLogger',
    notes: 'Debug logging library',
  },
  {
    libraryName: 'LibChatMessage',
    oldPatterns: [
      'LibStub("LibChatMessage")',
    ],
    globalVariable: 'LibChatMessage',
    notes: 'Chat message formatting',
  },
  {
    libraryName: 'LibMapPing',
    oldPatterns: [
      'LibStub("LibMapPing")',
    ],
    globalVariable: 'LibMapPing',
    notes: 'Map ping utilities',
  },
  {
    libraryName: 'LibSlashCommander',
    oldPatterns: [
      'LibStub("LibSlashCommander")',
    ],
    globalVariable: 'LibSlashCommander',
    notes: 'Slash command management',
  },
];

// ============================================================================
// Event Constant Migrations
// ============================================================================

export interface EventMigration {
  readonly oldName: string;
  readonly newName?: string;
  readonly removed: boolean;
  readonly versionChanged: number;
  readonly notes: string;
}

export const EVENT_MIGRATIONS: readonly EventMigration[] = [
  {
    oldName: 'EVENT_VETERAN_RANK_UPDATE',
    removed: true,
    versionChanged: 100015,
    notes: 'Veteran system removed. Use EVENT_CHAMPION_POINT_UPDATE instead.',
  },
  {
    oldName: 'EVENT_VETERAN_POINTS_UPDATE',
    removed: true,
    versionChanged: 100015,
    notes: 'Veteran system removed.',
  },

  // ==================== Endeavors Events Removed (API 101049) ====================
  {
    oldName: 'EVENT_ENDEAVOR_PROGRESS_UPDATE',
    removed: true,
    versionChanged: 101049,
    notes: 'Endeavors system removed in Update 49.',
  },
  {
    oldName: 'EVENT_ENDEAVOR_COMPLETED',
    removed: true,
    versionChanged: 101049,
    notes: 'Endeavors system removed in Update 49.',
  },
  {
    oldName: 'EVENT_ENDEAVORS_RESET',
    removed: true,
    versionChanged: 101049,
    notes: 'Endeavors system removed in Update 49.',
  },

  // ==================== Daily Login Events Removed (API 101049) ====================
  {
    oldName: 'EVENT_DAILY_LOGIN_REWARDS_UPDATED',
    removed: true,
    versionChanged: 101049,
    notes: 'Daily Login Rewards system removed in Update 49.',
  },
  {
    oldName: 'EVENT_DAILY_LOGIN_REWARDS_CLAIMED',
    removed: true,
    versionChanged: 101049,
    notes: 'Daily Login Rewards system removed in Update 49.',
  },

  // ==================== Outfit Events Changed (API 101049) ====================
  {
    oldName: 'EVENT_OUTFIT_CHANGE_RESPONSE',
    newName: 'EVENT_OUTFIT_CHANGE_RESPONSE',
    removed: false,
    versionChanged: 101049,
    notes: 'Outfit events now account-wide in U49. Character parameter removed from callback.',
  },
];

// ============================================================================
// Functions that should NOT be flagged (false positive prevention)
// ============================================================================

/**
 * Functions that exist and work fine in current API.
 * These should NOT be flagged as deprecated.
 */
// ============================================================================
// Removed Constants (Update 49)
// ============================================================================

/**
 * Currency type constants removed in Update 49.
 * Addons referencing these will get nil errors.
 */
export const REMOVED_CONSTANTS_U49: ReadonlySet<string> = new Set([
  'CURT_EVENT_TICKETS',
  'CURT_ENDEAVOR_SEALS',
]);

/**
 * New currency type constants added in Update 49.
 */
export const NEW_CONSTANTS_U49: ReadonlySet<string> = new Set([
  'CURT_TRADE_BARS',
  'CURT_OUTFIT_CHANGE_TOKENS',
  'CURT_TOME_POINTS',
  'CURT_PREMIUM_TOME_TOKENS',
]);

export const VALID_CURRENT_FUNCTIONS: ReadonlySet<string> = new Set([
  // These still work fine, signature may have changed but backwards compatible
  'GetPlayerStat',
  'GetUnitPower',
  'GetItemType',
  'GetItemInfo',
  'GetSlotBoundId',
  'GetAbilityUpgradeLines',
  'GetZoneId',
  'GetMapPlayerPosition',
  'GetAchievementProgress',

  // Common ZO_ utilities - always valid
  'ZO_Object',
  'ZO_InitializingObject',
  'ZO_CallbackObject',
  'ZO_SavedVars',
  'ZO_DeepTableCopy',
  'ZO_ShallowTableCopy',
]);

// ============================================================================
// Addon Replacement Recommendations
// ============================================================================

export interface AddonRecommendation {
  readonly addonName: string;
  readonly complexity: 'low' | 'medium' | 'high' | 'very_high';
  readonly recommendations: readonly string[];
  readonly shouldAttemptFix: boolean;
}

export const ADDON_RECOMMENDATIONS: readonly AddonRecommendation[] = [
  {
    addonName: 'Wykkyd Framework',
    complexity: 'very_high',
    recommendations: [
      'This addon is too complex for automated repair.',
      'Consider using alternatives:',
      '  - Bandits UI for unit frames',
      '  - Port to Inventory for inventory management',
      '  - Skyshards for achievement tracking',
    ],
    shouldAttemptFix: false,
  },
  {
    addonName: 'AwesomeGuildStore',
    complexity: 'high',
    recommendations: [
      'Complex dependency chain requires careful validation.',
      'Dependencies: LibMapPing, LibGPS, LibPromises, LibTextFilter, LibGetText, LibChatMessage, LibHistoire',
      'Recommend testing thoroughly after fixes.',
    ],
    shouldAttemptFix: true,
  },
  {
    addonName: 'Foundry Tactical Combat',
    complexity: 'medium',
    recommendations: [
      'Active fork available at github.com/Rhyono/Foundry-Tactical-Combat',
      'Main issues: nil value checks, texture string updates',
    ],
    shouldAttemptFix: true,
  },
  {
    addonName: 'PersonalAssistant',
    complexity: 'medium',
    recommendations: [
      'Multi-module architecture (PAG, PAB, PAJ, PAL, PAR)',
      'Active maintenance at github.com/klingo/ESO-PersonalAssistant',
    ],
    shouldAttemptFix: true,
  },
  {
    addonName: 'Dustman',
    complexity: 'low',
    recommendations: [
      'Simple addon, usually just needs version bump and nil checks.',
    ],
    shouldAttemptFix: true,
  },
];

// ============================================================================
// Helper Functions
// ============================================================================

export function getMigrationByName(name: string): FunctionMigration | undefined {
  return FUNCTION_MIGRATIONS.find((m) => m.oldName === name);
}

export function getLibraryMigration(libraryName: string): LibraryMigration | undefined {
  return LIBRARY_MIGRATIONS.find((m) => m.libraryName === libraryName);
}

export function getLibraryByPattern(pattern: string): LibraryMigration | undefined {
  return LIBRARY_MIGRATIONS.find((m) =>
    m.oldPatterns.some((p) => pattern.includes(p.replace(/["']/g, '')))
  );
}

export function getMigrationsByCategory(category: string): readonly FunctionMigration[] {
  return FUNCTION_MIGRATIONS.filter((m) => m.category === category);
}

export function getMigrationsByVersion(version: number): readonly FunctionMigration[] {
  return FUNCTION_MIGRATIONS.filter(
    (m) => m.versionDeprecated === version || m.versionRemoved === version
  );
}

export function getAutoFixableMigrations(
  minConfidence: number = 0.8
): readonly FunctionMigration[] {
  return FUNCTION_MIGRATIONS.filter(
    (m) => m.autoFixable && m.confidence >= minConfidence
  );
}

export function isValidCurrentFunction(name: string): boolean {
  return VALID_CURRENT_FUNCTIONS.has(name);
}

export function getAddonRecommendation(addonName: string): AddonRecommendation | undefined {
  return ADDON_RECOMMENDATIONS.find(
    (r) => addonName.toLowerCase().includes(r.addonName.toLowerCase())
  );
}
