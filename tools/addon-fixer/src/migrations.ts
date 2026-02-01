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
    isLive: true,
    isPTS: false,
    significantChanges: [
      'Current live version',
    ],
  },
  {
    version: 101049,
    update: 'Update 49 (PTS)',
    releaseDate: '2026-03-09',
    isLive: false,
    isPTS: true,
    significantChanges: [
      'PTS version',
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
];

// ============================================================================
// Functions that should NOT be flagged (false positive prevention)
// ============================================================================

/**
 * Functions that exist and work fine in current API.
 * These should NOT be flagged as deprecated.
 */
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
