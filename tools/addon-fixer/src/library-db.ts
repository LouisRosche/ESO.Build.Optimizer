/**
 * Library version database for ESO addon ecosystem.
 *
 * Tracks the latest known versions of common libraries and provides
 * health check functionality to identify outdated dependencies.
 *
 * Sources:
 * - ESOUI.com addon listings
 * - GitHub repositories where available
 */

export interface LibraryVersionInfo {
  /** Library name as used in manifests */
  readonly name: string;
  /** ESOUI.com addon ID for update checking */
  readonly esouiId?: number;
  /** Latest known version number */
  readonly latestVersion: string;
  /** Last update date (YYYY-MM-DD) */
  readonly lastUpdated: string;
  /** Global variable name when loaded */
  readonly globalVariable: string;
  /** What this library provides */
  readonly purpose: string;
  /** GitHub repo if available */
  readonly githubRepo?: string;
  /** Minimum ESO API version required */
  readonly minApiVersion?: number;
  /** Is this library actively maintained? */
  readonly maintained: boolean;
  /** Suggested replacement if deprecated */
  readonly replacedBy?: string;
}

/**
 * Known ESO addon libraries with version tracking.
 * Updated: February 2026
 */
export const LIBRARY_DATABASE: readonly LibraryVersionInfo[] = [
  // ============================================================================
  // Core UI Libraries
  // ============================================================================
  {
    name: 'LibAddonMenu-2.0',
    esouiId: 450,
    latestVersion: '2.0.35',
    lastUpdated: '2025-06-15',
    globalVariable: 'LibAddonMenu2',
    purpose: 'Settings panel creation and management',
    githubRepo: 'sirinsidiator/ESO-LibAddonMenu',
    minApiVersion: 101041,
    maintained: true,
  },
  {
    name: 'LibCustomMenu',
    esouiId: 457,
    latestVersion: '7.3.0',
    lastUpdated: '2025-03-20',
    globalVariable: 'LibCustomMenu',
    purpose: 'Custom context menu creation',
    maintained: true,
  },
  {
    name: 'LibDialog',
    esouiId: 562,
    latestVersion: '2.0.3',
    lastUpdated: '2024-06-10',
    globalVariable: 'LibDialog',
    purpose: 'Custom dialog/popup creation',
    maintained: true,
  },
  {
    name: 'LibScrollableMenu',
    esouiId: 2582,
    latestVersion: '2.3.0',
    lastUpdated: '2025-09-01',
    globalVariable: 'LibScrollableMenu',
    purpose: 'Scrollable dropdown menus',
    maintained: true,
  },

  // ============================================================================
  // Inventory & Trading Libraries
  // ============================================================================
  {
    name: 'LibFilters-3.0',
    esouiId: 2424,
    latestVersion: '3.5.2',
    lastUpdated: '2025-06-20',
    globalVariable: 'LibFilters3',
    purpose: 'Inventory filtering API',
    maintained: true,
  },
  {
    name: 'LibHistoire',
    esouiId: 2175,
    latestVersion: '1.4.0',
    lastUpdated: '2025-03-15',
    globalVariable: 'LibHistoire',
    purpose: 'Guild history event coordination',
    maintained: true,
  },
  {
    name: 'LibPrice',
    esouiId: 1466,
    latestVersion: '8.0.0',
    lastUpdated: '2025-06-01',
    globalVariable: 'LibPrice',
    purpose: 'Item price calculation',
    maintained: true,
  },

  // ============================================================================
  // Map & Location Libraries
  // ============================================================================
  {
    name: 'LibGPS3',
    esouiId: 2092,
    latestVersion: '3.4.0',
    lastUpdated: '2024-11-10',
    globalVariable: 'LibGPS3',
    purpose: 'Normalized map coordinates',
    maintained: true,
  },
  {
    name: 'LibMapPing',
    esouiId: 625,
    latestVersion: '1.2.0',
    lastUpdated: '2023-06-15',
    globalVariable: 'LibMapPing',
    purpose: 'Custom map ping handling',
    maintained: true,
  },

  // ============================================================================
  // Utility Libraries
  // ============================================================================
  {
    name: 'LibAsync',
    esouiId: 1576,
    latestVersion: '2.4.0',
    lastUpdated: '2025-01-20',
    globalVariable: 'LibAsync',
    purpose: 'Async task scheduling to prevent UI lag',
    maintained: true,
  },
  {
    name: 'LibDebugLogger',
    esouiId: 2275,
    latestVersion: '2.6.0',
    lastUpdated: '2025-06-01',
    globalVariable: 'LibDebugLogger',
    purpose: 'Debug logging with categories',
    maintained: true,
  },
  {
    name: 'LibChatMessage',
    esouiId: 2169,
    latestVersion: '1.2.0',
    lastUpdated: '2024-03-10',
    globalVariable: 'LibChatMessage',
    purpose: 'Chat message formatting utilities',
    maintained: true,
  },
  {
    name: 'LibSavedVars',
    esouiId: 564,
    latestVersion: '1.3.1',
    lastUpdated: '2023-09-01',
    globalVariable: 'LibSavedVars',
    purpose: 'Extended SavedVariables management',
    maintained: true,
  },
  {
    name: 'LibMediaProvider',
    esouiId: 468,
    latestVersion: '1.2.0',
    lastUpdated: '2022-08-15',
    globalVariable: 'LibMediaProvider',
    purpose: 'Shared fonts, textures, sounds',
    maintained: true,
  },
  {
    name: 'LibLoadedAddons',
    esouiId: 2835,
    latestVersion: '1.5.0',
    lastUpdated: '2025-06-10',
    globalVariable: 'LibLoadedAddons',
    purpose: 'Track loaded addon states',
    maintained: true,
  },

  // ============================================================================
  // Combat & Group Libraries
  // ============================================================================
  {
    name: 'LibGroupSocket',
    esouiId: 1498,
    latestVersion: '1.3.0',
    lastUpdated: '2024-06-01',
    globalVariable: 'LibGroupSocket',
    purpose: 'Group data synchronization',
    maintained: true,
  },
  {
    name: 'LibCombat',
    esouiId: 2508,
    latestVersion: '1.1.0',
    lastUpdated: '2024-09-15',
    globalVariable: 'LibCombat',
    purpose: 'Combat data aggregation',
    maintained: true,
  },

  // ============================================================================
  // Deprecated Libraries (Still Tracked)
  // ============================================================================
  {
    name: 'LibStub',
    esouiId: 44,
    latestVersion: '1.0.0',
    lastUpdated: '2018-05-01',
    globalVariable: 'LibStub',
    purpose: 'Library loading (DEPRECATED)',
    maintained: false,
    replacedBy: 'Direct global variable access',
  },
  {
    name: 'LibFilters-2.0',
    esouiId: 1165,
    latestVersion: '2.7.0',
    lastUpdated: '2021-03-01',
    globalVariable: 'LibFilters',
    purpose: 'Inventory filtering (DEPRECATED)',
    maintained: false,
    replacedBy: 'LibFilters-3.0',
  },
  {
    name: 'LibGPS',
    esouiId: 944,
    latestVersion: '2.0.0',
    lastUpdated: '2020-01-01',
    globalVariable: 'LibGPS2',
    purpose: 'Map coordinates (DEPRECATED)',
    maintained: false,
    replacedBy: 'LibGPS3',
  },
];

/**
 * Patterns that suggest an addon should use a library but doesn't.
 */
export interface LibraryRecommendation {
  /** Pattern that triggers this recommendation */
  readonly pattern: RegExp;
  /** What this pattern suggests */
  readonly description: string;
  /** Recommended library */
  readonly library: string;
  /** Why this library helps */
  readonly benefit: string;
}

export const LIBRARY_RECOMMENDATIONS: readonly LibraryRecommendation[] = [
  {
    pattern: /WINDOW_MANAGER:CreateControl.*type\s*=\s*["']?panel/i,
    description: 'Manual settings panel creation',
    library: 'LibAddonMenu-2.0',
    benefit: 'Standardized settings UI, automatic profile support',
  },
  {
    pattern: /ZO_ListDialog.*SetupList|DialogList/i,
    description: 'Manual dialog list setup',
    library: 'LibDialog',
    benefit: 'Simplified dialog creation, consistent styling',
  },
  {
    pattern: /GetMapPlayerPosition|GetMapPinManager/i,
    description: 'Direct map coordinate access',
    library: 'LibGPS3',
    benefit: 'Normalized coordinates across all zones',
  },
  {
    pattern: /zo_callLater.*loop|while.*zo_callLater/i,
    description: 'Manual async loop pattern',
    library: 'LibAsync',
    benefit: 'Proper frame-spreading, prevents UI lag',
  },
  {
    pattern: /d\(.*tostring|d\(string\.format/i,
    description: 'Manual debug output formatting',
    library: 'LibDebugLogger',
    benefit: 'Categorized logging, enable/disable per addon',
  },
  {
    pattern: /SHARED_INVENTORY.*filterCallback|AddFilter/i,
    description: 'Manual inventory filtering',
    library: 'LibFilters-3.0',
    benefit: 'Standard filter registration, cross-addon compatibility',
  },
  {
    pattern: /ZO_Menu_.*ShowMenu|ZO_Menu_AddMenuItem/i,
    description: 'Direct menu API usage',
    library: 'LibCustomMenu',
    benefit: 'Enhanced menu features, dividers, submenus',
  },
];

// ============================================================================
// Library Health Check Functions
// ============================================================================

export interface LibraryHealthResult {
  readonly name: string;
  readonly declaredVersion?: string;
  readonly latestVersion: string;
  readonly isOutdated: boolean;
  readonly isDeprecated: boolean;
  readonly replacement?: string;
  readonly esouiUrl?: string;
}

/**
 * Parse version string to comparable number.
 * Handles formats: "2.0.35", "35", "2.0", "v2.0.35"
 */
export function parseVersion(version: string): number {
  // Remove 'v' prefix if present
  const cleaned = version.replace(/^v/i, '');

  // Split by dots and convert to weighted number
  const parts = cleaned.split('.').map(p => parseInt(p, 10) || 0);

  // Weight: major*10000 + minor*100 + patch
  return (parts[0] || 0) * 10000 + (parts[1] || 0) * 100 + (parts[2] || 0);
}

/**
 * Check library health against known versions.
 */
export function checkLibraryHealth(
  libraryName: string,
  declaredVersion?: string
): LibraryHealthResult | null {
  const lib = LIBRARY_DATABASE.find(
    l => l.name.toLowerCase() === libraryName.toLowerCase() ||
         l.globalVariable.toLowerCase() === libraryName.toLowerCase()
  );

  if (!lib) {
    return null; // Unknown library
  }

  let isOutdated = false;
  if (declaredVersion && lib.latestVersion) {
    const declared = parseVersion(declaredVersion);
    const latest = parseVersion(lib.latestVersion);
    isOutdated = declared < latest;
  }

  return {
    name: lib.name,
    declaredVersion,
    latestVersion: lib.latestVersion,
    isOutdated,
    isDeprecated: !lib.maintained,
    replacement: lib.replacedBy,
    esouiUrl: lib.esouiId ? `https://www.esoui.com/downloads/info${lib.esouiId}` : undefined,
  };
}

/**
 * Get library info by name.
 */
export function getLibraryInfo(name: string): LibraryVersionInfo | undefined {
  return LIBRARY_DATABASE.find(
    l => l.name.toLowerCase() === name.toLowerCase() ||
         l.globalVariable.toLowerCase() === name.toLowerCase()
  );
}

/**
 * Check for library recommendations based on code patterns.
 */
export function getLibraryRecommendations(code: string): LibraryRecommendation[] {
  const recommendations: LibraryRecommendation[] = [];

  for (const rec of LIBRARY_RECOMMENDATIONS) {
    if (rec.pattern.test(code)) {
      recommendations.push(rec);
    }
  }

  return recommendations;
}
