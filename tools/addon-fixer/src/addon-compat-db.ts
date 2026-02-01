/**
 * ESO Addon Compatibility Database
 *
 * Community resource tracking popular addons, their compatibility status,
 * and instructions for updating or finding alternatives.
 *
 * Status meanings:
 * - working: Fully compatible with current API
 * - needs_update: Works but has deprecation warnings or minor issues
 * - broken: Does not load or has critical errors
 * - deprecated: No longer maintained, use alternative
 * - unknown: Not yet tested
 */

export type AddonStatus = 'working' | 'needs_update' | 'broken' | 'deprecated' | 'unknown';
export type FixComplexity = 'none' | 'low' | 'medium' | 'high' | 'replacement_needed';

export interface AddonCompatibility {
  /** Addon name as it appears in-game */
  readonly name: string;
  /** ESOUI addon ID */
  readonly esouiId: number;
  /** Current compatibility status */
  readonly status: AddonStatus;
  /** Complexity to fix if not working */
  readonly fixComplexity: FixComplexity;
  /** Category for filtering */
  readonly category: string;
  /** Author/maintainer */
  readonly author: string;
  /** Brief description */
  readonly description: string;
  /** Last known working version */
  readonly lastWorkingVersion?: string;
  /** API version it was last updated for */
  readonly lastApiVersion?: number;
  /** Issues if any */
  readonly issues?: string[];
  /** Fix instructions if applicable */
  readonly fixInstructions?: string[];
  /** Alternative addon if deprecated */
  readonly alternative?: string;
  /** Dependencies */
  readonly dependencies?: string[];
  /** Part of a suite? */
  readonly suite?: string;
  /** Last verified date */
  readonly lastVerified: string;
  /** Notes */
  readonly notes?: string;
}

/**
 * Popular ESO addons with compatibility information.
 * Updated: February 2026
 */
export const ADDON_COMPATIBILITY_DB: readonly AddonCompatibility[] = [
  // ============================================================================
  // Combat & Performance
  // ============================================================================
  {
    name: 'Combat Metrics',
    esouiId: 1360,
    status: 'working',
    fixComplexity: 'none',
    category: 'Combat',
    author: 'Solinur',
    description: 'Advanced combat logging and DPS/HPS tracking',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'Code\'s Combat Alerts',
    esouiId: 2618,
    status: 'working',
    fixComplexity: 'none',
    category: 'Combat',
    author: 'code65536',
    description: 'Customizable combat alerts for mechanics',
    lastApiVersion: 101048,
    lastVerified: '2026-01-15',
  },
  {
    name: 'Raid Notifier',
    esouiId: 1355,
    status: 'working',
    fixComplexity: 'none',
    category: 'Combat',
    author: 'Kyoma',
    description: 'Trial and dungeon mechanic notifications',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'Action Duration Reminder',
    esouiId: 903,
    status: 'working',
    fixComplexity: 'none',
    category: 'Combat',
    author: 'Stormknight',
    description: 'Buff/debuff duration tracking',
    lastApiVersion: 101048,
    lastVerified: '2026-01-15',
  },
  {
    name: 'Qcell\'s Clock TST',
    esouiId: 1967,
    status: 'needs_update',
    fixComplexity: 'low',
    category: 'Combat',
    author: 'Qcell',
    description: 'Time to kill and sustain tracking',
    issues: ['LibStub deprecation warnings'],
    fixInstructions: ['Run addon fixer to update LibStub calls'],
    lastVerified: '2026-01-15',
  },

  // ============================================================================
  // Personal Assistant Suite (by Klingo/Masterroshi)
  // ============================================================================
  {
    name: 'PersonalAssistant',
    esouiId: 2066,
    status: 'working',
    fixComplexity: 'none',
    category: 'Inventory',
    author: 'Klingo',
    description: 'Comprehensive inventory management suite (integration module)',
    lastApiVersion: 101048,
    suite: 'Personal Assistant',
    dependencies: ['LibAddonMenu-2.0', 'LibChatMessage'],
    lastVerified: '2026-02-01',
    notes: 'Actively maintained. Core integration for PA modules.',
  },
  {
    name: 'PersonalAssistant Banking',
    esouiId: 2067,
    status: 'working',
    fixComplexity: 'none',
    category: 'Inventory',
    author: 'Klingo',
    description: 'Automatic banking and withdrawals',
    lastApiVersion: 101048,
    suite: 'Personal Assistant',
    dependencies: ['PersonalAssistant'],
    lastVerified: '2026-02-01',
  },
  {
    name: 'PersonalAssistant Junk',
    esouiId: 2068,
    status: 'working',
    fixComplexity: 'none',
    category: 'Inventory',
    author: 'Klingo',
    description: 'Automatic junk marking and selling',
    lastApiVersion: 101048,
    suite: 'Personal Assistant',
    dependencies: ['PersonalAssistant'],
    lastVerified: '2026-02-01',
  },
  {
    name: 'PersonalAssistant Loot',
    esouiId: 2069,
    status: 'working',
    fixComplexity: 'none',
    category: 'Inventory',
    author: 'Klingo',
    description: 'Loot rules and auto-loot settings',
    lastApiVersion: 101048,
    suite: 'Personal Assistant',
    dependencies: ['PersonalAssistant'],
    lastVerified: '2026-02-01',
  },
  {
    name: 'PersonalAssistant Repair',
    esouiId: 2070,
    status: 'working',
    fixComplexity: 'none',
    category: 'Inventory',
    author: 'Klingo',
    description: 'Automatic repair and recharge',
    lastApiVersion: 101048,
    suite: 'Personal Assistant',
    dependencies: ['PersonalAssistant'],
    lastVerified: '2026-02-01',
  },

  // ============================================================================
  // UI Enhancement
  // ============================================================================
  {
    name: 'Bandit\'s UI',
    esouiId: 1529,
    status: 'working',
    fixComplexity: 'none',
    category: 'UI',
    author: 'Bandit',
    description: 'Comprehensive UI overhaul',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'AUI (Advanced UI)',
    esouiId: 1103,
    status: 'working',
    fixComplexity: 'none',
    category: 'UI',
    author: 'Petsjak',
    description: 'Modular UI enhancement suite',
    lastApiVersion: 101048,
    lastVerified: '2026-01-15',
  },
  {
    name: 'LUI Extended',
    esouiId: 818,
    status: 'working',
    fixComplexity: 'none',
    category: 'UI',
    author: 'ArtOfShred',
    description: 'Extended UI features and customization',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'DarkUI',
    esouiId: 479,
    status: 'working',
    fixComplexity: 'none',
    category: 'UI',
    author: 'Garkin',
    description: 'Dark theme for ESO UI',
    lastApiVersion: 101048,
    lastVerified: '2026-01-15',
  },
  {
    name: 'Pixel Perfect',
    esouiId: 2925,
    status: 'working',
    fixComplexity: 'none',
    category: 'UI',
    author: 'Various',
    description: 'Pixel-perfect UI scaling',
    lastApiVersion: 101048,
    lastVerified: '2026-01-15',
  },
  {
    name: 'Azurah',
    esouiId: 602,
    status: 'working',
    fixComplexity: 'none',
    category: 'UI',
    author: 'Garkin',
    description: 'UI element positioning and customization',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0'],
    lastVerified: '2026-01-15',
  },

  // ============================================================================
  // Inventory & Crafting
  // ============================================================================
  {
    name: 'Inventory Insight',
    esouiId: 839,
    status: 'working',
    fixComplexity: 'none',
    category: 'Inventory',
    author: 'manavortex',
    description: 'Cross-character inventory search',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'Dustman',
    esouiId: 414,
    status: 'working',
    fixComplexity: 'none',
    category: 'Inventory',
    author: 'Garkin',
    description: 'Automatic junk management',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0', 'LibFilters-3.0'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'Item Set Browser',
    esouiId: 1422,
    status: 'working',
    fixComplexity: 'none',
    category: 'Inventory',
    author: 'Arkadius',
    description: 'Browse and track item sets',
    lastApiVersion: 101048,
    lastVerified: '2026-01-15',
  },
  {
    name: 'Dolgubon\'s Lazy Writ Crafter',
    esouiId: 1346,
    status: 'working',
    fixComplexity: 'none',
    category: 'Crafting',
    author: 'Dolgubon',
    description: 'Automated writ crafting',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0', 'LibLazyCrafting'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'WritWorthy',
    esouiId: 1760,
    status: 'working',
    fixComplexity: 'none',
    category: 'Crafting',
    author: 'ziggr',
    description: 'Master writ profitability calculator',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0', 'LibPrice'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'Potion Maker',
    esouiId: 768,
    status: 'working',
    fixComplexity: 'none',
    category: 'Crafting',
    author: 'circonian',
    description: 'Alchemy crafting helper',
    lastApiVersion: 101048,
    lastVerified: '2026-01-15',
  },

  // ============================================================================
  // Trading
  // ============================================================================
  {
    name: 'Master Merchant',
    esouiId: 928,
    status: 'working',
    fixComplexity: 'none',
    category: 'Trading',
    author: 'Philgo68',
    description: 'Guild store sales tracking and pricing',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0', 'LibHistoire'],
    lastVerified: '2026-01-15',
    notes: 'Large database can cause long load times',
  },
  {
    name: 'Tamriel Trade Centre',
    esouiId: 1245,
    status: 'working',
    fixComplexity: 'none',
    category: 'Trading',
    author: 'TTC Team',
    description: 'Price checking with online database',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'Arkadius\' Trade Tools',
    esouiId: 1752,
    status: 'working',
    fixComplexity: 'none',
    category: 'Trading',
    author: 'Arkadius',
    description: 'Trading statistics and analysis',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0', 'LibHistoire'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'Awesome Guild Store',
    esouiId: 1150,
    status: 'working',
    fixComplexity: 'none',
    category: 'Trading',
    author: 'sirinsidiator',
    description: 'Enhanced guild store interface',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0', 'LibFilters-3.0', 'LibCustomMenu'],
    lastVerified: '2026-01-15',
  },

  // ============================================================================
  // Maps & Exploration
  // ============================================================================
  {
    name: 'Destinations',
    esouiId: 614,
    status: 'working',
    fixComplexity: 'none',
    category: 'Maps',
    author: 'Garkin',
    description: 'Points of interest on map',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'Map Pins',
    esouiId: 973,
    status: 'working',
    fixComplexity: 'none',
    category: 'Maps',
    author: 'Fyrakin',
    description: 'Custom map pins for various content',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0', 'LibMapPing'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'HarvestMap',
    esouiId: 367,
    status: 'working',
    fixComplexity: 'none',
    category: 'Maps',
    author: 'Shinni',
    description: 'Resource node tracking on map',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0', 'LibMapPing'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'SkyShards',
    esouiId: 125,
    status: 'working',
    fixComplexity: 'none',
    category: 'Maps',
    author: 'Garkin',
    description: 'Skyshard locations on map',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'Lost Treasure',
    esouiId: 630,
    status: 'working',
    fixComplexity: 'none',
    category: 'Maps',
    author: 'CrazyDutchGuy',
    description: 'Treasure map and survey locations',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0'],
    lastVerified: '2026-01-15',
  },

  // ============================================================================
  // Character & Builds
  // ============================================================================
  {
    name: 'Dressing Room',
    esouiId: 818,
    status: 'working',
    fixComplexity: 'none',
    category: 'Character',
    author: 'calia1120',
    description: 'Gear and skill preset manager',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'Alpha Gear',
    esouiId: 1485,
    status: 'working',
    fixComplexity: 'none',
    category: 'Character',
    author: 'Randactyl',
    description: 'Quick gear set switching',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'Wizard\'s Wardrobe',
    esouiId: 2712,
    status: 'working',
    fixComplexity: 'none',
    category: 'Character',
    author: 'Solinur',
    description: 'Build and gear management',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0'],
    lastVerified: '2026-01-15',
  },

  // ============================================================================
  // Quality of Life
  // ============================================================================
  {
    name: 'Auto Recharge',
    esouiId: 326,
    status: 'working',
    fixComplexity: 'none',
    category: 'QoL',
    author: 'Wheel5',
    description: 'Automatic weapon recharging',
    lastApiVersion: 101048,
    lastVerified: '2026-01-15',
  },
  {
    name: 'RuESO',
    esouiId: 1345,
    status: 'working',
    fixComplexity: 'none',
    category: 'QoL',
    author: 'Jesjin',
    description: 'Russian localization',
    lastApiVersion: 101048,
    lastVerified: '2026-01-15',
  },
  {
    name: 'Votan\'s Minimap',
    esouiId: 1399,
    status: 'working',
    fixComplexity: 'none',
    category: 'QoL',
    author: 'votan',
    description: 'Minimap display',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'FCO ItemSaver',
    esouiId: 815,
    status: 'working',
    fixComplexity: 'none',
    category: 'QoL',
    author: 'Baertram',
    description: 'Item protection and marking',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0', 'LibFilters-3.0'],
    lastVerified: '2026-01-15',
  },
  {
    name: 'pChat',
    esouiId: 1525,
    status: 'working',
    fixComplexity: 'none',
    category: 'QoL',
    author: 'Puddy',
    description: 'Enhanced chat features',
    lastApiVersion: 101048,
    dependencies: ['LibAddonMenu-2.0', 'LibChatMessage'],
    lastVerified: '2026-01-15',
  },

  // ============================================================================
  // Deprecated / Needs Replacement
  // ============================================================================
  {
    name: 'Wykkyd Framework',
    esouiId: 73,
    status: 'deprecated',
    fixComplexity: 'replacement_needed',
    category: 'Framework',
    author: 'Wykkyd',
    description: 'Legacy addon framework',
    alternative: 'Modern addons no longer need this framework',
    lastVerified: '2026-01-15',
    notes: 'Very old, causes conflicts with modern addons',
  },
  {
    name: 'Wykkyd Quest Tracker',
    esouiId: 99,
    status: 'deprecated',
    fixComplexity: 'replacement_needed',
    category: 'Quests',
    author: 'Wykkyd',
    description: 'Quest tracking overlay',
    alternative: 'Use built-in quest tracker or Quest Map',
    lastVerified: '2026-01-15',
  },
  {
    name: 'Foundry Tactical Combat',
    esouiId: 398,
    status: 'deprecated',
    fixComplexity: 'replacement_needed',
    category: 'Combat',
    author: 'Atropos',
    description: 'Combat enhancement suite',
    alternative: 'Bandit\'s UI, AUI, or Combat Metrics',
    lastVerified: '2026-01-15',
    notes: 'Abandoned years ago, use modern alternatives',
  },

  // ============================================================================
  // Addon Management
  // ============================================================================
  {
    name: 'Addon Selector',
    esouiId: 594,
    status: 'working',
    fixComplexity: 'none',
    category: 'Utility',
    author: 'Garkin',
    description: 'Enable/disable addon profiles',
    lastApiVersion: 101048,
    lastVerified: '2026-01-15',
    notes: 'See our Addon Orchestrator concept for enhanced alternative',
  },
];

// ============================================================================
// Query Functions
// ============================================================================

/**
 * Get all addons by category
 */
export function getAddonsByCategory(category: string): AddonCompatibility[] {
  return ADDON_COMPATIBILITY_DB.filter(
    a => a.category.toLowerCase() === category.toLowerCase()
  );
}

/**
 * Get all addons by status
 */
export function getAddonsByStatus(status: AddonStatus): AddonCompatibility[] {
  return ADDON_COMPATIBILITY_DB.filter(a => a.status === status);
}

/**
 * Get all addons in a suite
 */
export function getAddonSuite(suiteName: string): AddonCompatibility[] {
  return ADDON_COMPATIBILITY_DB.filter(
    a => a.suite?.toLowerCase() === suiteName.toLowerCase()
  );
}

/**
 * Get addon by name (case-insensitive)
 */
export function getAddonInfo(name: string): AddonCompatibility | undefined {
  return ADDON_COMPATIBILITY_DB.find(
    a => a.name.toLowerCase() === name.toLowerCase()
  );
}

/**
 * Get addons that need fixes
 */
export function getAddonsNeedingFixes(): AddonCompatibility[] {
  return ADDON_COMPATIBILITY_DB.filter(
    a => a.status === 'needs_update' || a.status === 'broken'
  );
}

/**
 * Get working alternatives for a deprecated addon
 */
export function getAlternatives(addonName: string): string | undefined {
  const addon = getAddonInfo(addonName);
  return addon?.alternative;
}

/**
 * Get all unique categories
 */
export function getCategories(): string[] {
  const categories = new Set(ADDON_COMPATIBILITY_DB.map(a => a.category));
  return Array.from(categories).sort();
}

/**
 * Get statistics
 */
export function getCompatibilityStats(): {
  total: number;
  working: number;
  needsUpdate: number;
  broken: number;
  deprecated: number;
} {
  return {
    total: ADDON_COMPATIBILITY_DB.length,
    working: ADDON_COMPATIBILITY_DB.filter(a => a.status === 'working').length,
    needsUpdate: ADDON_COMPATIBILITY_DB.filter(a => a.status === 'needs_update').length,
    broken: ADDON_COMPATIBILITY_DB.filter(a => a.status === 'broken').length,
    deprecated: ADDON_COMPATIBILITY_DB.filter(a => a.status === 'deprecated').length,
  };
}
