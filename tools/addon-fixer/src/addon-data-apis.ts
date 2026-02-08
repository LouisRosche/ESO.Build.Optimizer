/**
 * Addon Data Sharing API Map
 *
 * Documents what data each popular ESO addon exposes via:
 * - Global variables
 * - Callbacks/events
 * - Public APIs
 *
 * This enables the "Addon Collaborator" concept - maximizing synergy
 * between addons by understanding their data sharing capabilities.
 */

export type DataAccessMethod = 'global' | 'callback' | 'api' | 'savedvar' | 'event';

export interface ExposedDataPoint {
  /** Name of the data point */
  readonly name: string;
  /** How to access this data */
  readonly accessMethod: DataAccessMethod;
  /** The actual path/key to access (e.g., "CMX.combatData" or event name) */
  readonly accessPath: string;
  /** Data type/structure */
  readonly dataType: string;
  /** Human-readable description */
  readonly description: string;
  /** Example usage in Lua */
  readonly exampleCode?: string;
  /** Is this data real-time or historical? */
  readonly realtime: boolean;
  /** Refresh rate if applicable */
  readonly updateFrequency?: 'immediate' | 'per-second' | 'per-fight' | 'on-demand';
}

export interface AddonDataAPI {
  /** Addon name */
  readonly name: string;
  /** ESOUI ID for reference */
  readonly esouiId: number;
  /** What the addon primarily does */
  readonly primaryFunction: string;
  /** Data that this addon exposes */
  readonly exposedData: ExposedDataPoint[];
  /** Data that this addon consumes from other addons */
  readonly consumesFrom: string[];
  /** Known integrations */
  readonly knownIntegrations: string[];
  /** Global namespace used */
  readonly globalNamespace?: string;
  /** Notes about data access */
  readonly notes?: string;
}

/**
 * Comprehensive map of addon data sharing capabilities.
 *
 * This is the foundation for building addon synergy - understanding
 * what data each addon can provide to others.
 */
export const ADDON_DATA_APIS: readonly AddonDataAPI[] = [
  // ===========================================================================
  // COMBAT & DPS METERS
  // ===========================================================================
  {
    name: 'Combat Metrics',
    esouiId: 1360,
    primaryFunction: 'Combat logging and DPS/HPS tracking',
    globalNamespace: 'CMX',
    exposedData: [
      {
        name: 'Current Fight Data',
        accessMethod: 'global',
        accessPath: 'CMX.currentFight',
        dataType: '{ dps: number, hps: number, duration: number, ... }',
        description: 'Real-time metrics for the current combat encounter',
        exampleCode: 'local dps = CMX.currentFight and CMX.currentFight.dps or 0',
        realtime: true,
        updateFrequency: 'per-second',
      },
      {
        name: 'Fight History',
        accessMethod: 'global',
        accessPath: 'CMX.fightHistory',
        dataType: 'table[]',
        description: 'Array of completed fight records',
        exampleCode: 'for i, fight in ipairs(CMX.fightHistory) do ... end',
        realtime: false,
        updateFrequency: 'per-fight',
      },
      {
        name: 'Combat State',
        accessMethod: 'callback',
        accessPath: 'CMX:RegisterCallback("CombatStateChanged", callback)',
        dataType: 'boolean (inCombat)',
        description: 'Fires when entering/leaving combat',
        exampleCode: 'CMX:RegisterCallback("CombatStateChanged", function(inCombat) ... end)',
        realtime: true,
        updateFrequency: 'immediate',
      },
      {
        name: 'Boss Info',
        accessMethod: 'global',
        accessPath: 'CMX.currentBoss',
        dataType: '{ name: string, health: number, maxHealth: number }',
        description: 'Current boss target information',
        realtime: true,
        updateFrequency: 'per-second',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0', 'LibCustomMenu'],
    knownIntegrations: ['Bandits UI', 'Raid Notifier'],
    notes: 'Primary combat data source. Most DPS-related addons integrate with CMX.',
  },

  {
    name: 'Foundry Tactical Combat (FTC)',
    esouiId: 165,
    primaryFunction: 'Combat interface and buff/debuff tracking',
    globalNamespace: 'FTC',
    exposedData: [
      {
        name: 'Player Stats',
        accessMethod: 'global',
        accessPath: 'FTC.Player',
        dataType: '{ name: string, class: string, race: string, level: number, ... }',
        description: 'Current player information and stats',
        realtime: true,
        updateFrequency: 'on-demand',
      },
      {
        name: 'Active Buffs',
        accessMethod: 'global',
        accessPath: 'FTC.Buffs.Player',
        dataType: 'table<abilityId, buffInfo>',
        description: 'Currently active buffs on the player',
        realtime: true,
        updateFrequency: 'immediate',
      },
      {
        name: 'Target Info',
        accessMethod: 'global',
        accessPath: 'FTC.Target',
        dataType: '{ name: string, health: number, ... }',
        description: 'Current target information',
        realtime: true,
        updateFrequency: 'immediate',
      },
      {
        name: 'DPS Meter',
        accessMethod: 'global',
        accessPath: 'FTC.Damage',
        dataType: '{ total: number, dps: number, ... }',
        description: 'Damage tracking (if DPS module enabled)',
        realtime: true,
        updateFrequency: 'per-second',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0'],
    knownIntegrations: ['Combat Metrics'],
    notes: 'Comprehensive combat UI. Exposes extensive player/combat state.',
  },

  // ===========================================================================
  // INVENTORY & TRADING
  // ===========================================================================
  {
    name: 'Master Merchant',
    esouiId: 928,
    primaryFunction: 'Guild trader price tracking and analytics',
    globalNamespace: 'MasterMerchant',
    exposedData: [
      {
        name: 'Price Data',
        accessMethod: 'api',
        accessPath: 'MasterMerchant:ItemPriceByItemLink(itemLink)',
        dataType: '{ avgPrice: number, sales: number, ... }',
        description: 'Average price and sales data for an item',
        exampleCode: 'local priceData = MasterMerchant:ItemPriceByItemLink(itemLink)',
        realtime: false,
        updateFrequency: 'on-demand',
      },
      {
        name: 'Sales History',
        accessMethod: 'api',
        accessPath: 'MasterMerchant:GetSalesData(itemId)',
        dataType: 'table[]',
        description: 'Historical sales records for an item',
        realtime: false,
        updateFrequency: 'on-demand',
      },
      {
        name: 'Guild Statistics',
        accessMethod: 'global',
        accessPath: 'MasterMerchant.guildStats',
        dataType: 'table<guildId, stats>',
        description: 'Per-guild trading statistics',
        realtime: false,
        updateFrequency: 'on-demand',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0', 'LibGuildStore'],
    knownIntegrations: ['Awesome Guild Store', 'Tamriel Trade Centre', 'Arkadius Trade Tools'],
    notes: 'Primary price data source for trading. Heavy memory footprint.',
  },

  {
    name: 'Tamriel Trade Centre',
    esouiId: 1245,
    primaryFunction: 'Cross-platform price database integration',
    globalNamespace: 'TamrielTradeCentre',
    exposedData: [
      {
        name: 'Price Check',
        accessMethod: 'api',
        accessPath: 'TamrielTradeCentre:GetPriceInfo(itemLink)',
        dataType: '{ Avg: number, Min: number, Max: number, SuggestedPrice: number }',
        description: 'TTC price data from web database',
        exampleCode: 'local price = TamrielTradeCentre:GetPriceInfo(itemLink)',
        realtime: false,
        updateFrequency: 'on-demand',
      },
      {
        name: 'Listings',
        accessMethod: 'api',
        accessPath: 'TamrielTradeCentre:GetItemListings(itemId)',
        dataType: 'table[]',
        description: 'Active listings across all traders',
        realtime: false,
        updateFrequency: 'on-demand',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0'],
    knownIntegrations: ['Awesome Guild Store', 'Master Merchant', 'Inventory Insight'],
    notes: 'Cross-server price data. Requires desktop app sync.',
  },

  {
    name: 'Arkadius Trade Tools (ATT)',
    esouiId: 1476,
    primaryFunction: 'Guild store analytics and purchase alerts',
    globalNamespace: 'ArkadiusTradeTools',
    exposedData: [
      {
        name: 'Purchase History',
        accessMethod: 'global',
        accessPath: 'ArkadiusTradeTools.Modules.Purchases.purchaseData',
        dataType: 'table[]',
        description: 'Historical purchase records',
        realtime: false,
        updateFrequency: 'per-fight',
      },
      {
        name: 'Flip Profit Data',
        accessMethod: 'api',
        accessPath: 'ArkadiusTradeTools:GetFlipPotential(itemLink)',
        dataType: '{ profit: number, margin: number }',
        description: 'Calculated flip profit for an item',
        realtime: false,
        updateFrequency: 'on-demand',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0', 'Master Merchant'],
    knownIntegrations: ['Master Merchant', 'Awesome Guild Store'],
    notes: 'Specialized trading analytics. Complements MM data.',
  },

  {
    name: 'Inventory Insight',
    esouiId: 724,
    primaryFunction: 'Cross-character inventory management',
    globalNamespace: 'InventoryInsight',
    exposedData: [
      {
        name: 'All Characters Inventory',
        accessMethod: 'api',
        accessPath: 'InventoryInsight:GetItemCount(itemId)',
        dataType: 'number (total count across all characters)',
        description: 'Total count of an item across all characters/banks',
        exampleCode: 'local total = InventoryInsight:GetItemCount(itemId)',
        realtime: false,
        updateFrequency: 'on-demand',
      },
      {
        name: 'Character Inventory',
        accessMethod: 'global',
        accessPath: 'InventoryInsight.data',
        dataType: 'table<characterName, inventoryData>',
        description: 'Per-character inventory snapshots',
        realtime: false,
        updateFrequency: 'on-demand',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0'],
    knownIntegrations: ['Dolgubon Lazy Writ Crafter', 'Dustman', 'FCO ItemSaver'],
    notes: 'Essential for cross-character item tracking.',
  },

  // ===========================================================================
  // MAP & LOCATION
  // ===========================================================================
  {
    name: 'Destinations',
    esouiId: 1391,
    primaryFunction: 'POI and location tracking',
    globalNamespace: 'Destinations',
    exposedData: [
      {
        name: 'Location Data',
        accessMethod: 'global',
        accessPath: 'Destinations.locations',
        dataType: 'table<zoneId, locationData[]>',
        description: 'All tracked POI locations',
        realtime: false,
        updateFrequency: 'on-demand',
      },
      {
        name: 'Nearest POI',
        accessMethod: 'api',
        accessPath: 'Destinations:GetNearestPOI(x, y, zoneId)',
        dataType: '{ name: string, distance: number, ... }',
        description: 'Find nearest point of interest',
        realtime: true,
        updateFrequency: 'on-demand',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0', 'LibGPS3'],
    knownIntegrations: ['Beam Me Up', 'Map Pins'],
    notes: 'Comprehensive POI database.',
  },

  {
    name: 'Harvest Map',
    esouiId: 647,
    primaryFunction: 'Resource node tracking',
    globalNamespace: 'HarvestMap',
    exposedData: [
      {
        name: 'Node Database',
        accessMethod: 'global',
        accessPath: 'HarvestMap.Data',
        dataType: 'table<zoneId, table<nodeType, coordinates[]>>',
        description: 'All discovered resource node locations',
        realtime: false,
        updateFrequency: 'on-demand',
      },
      {
        name: 'Nearby Nodes',
        accessMethod: 'api',
        accessPath: 'HarvestMap:GetNearbyNodes(nodeType)',
        dataType: 'table[]',
        description: 'Resource nodes near player',
        realtime: true,
        updateFrequency: 'per-second',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0', 'LibGPS3', 'LibMapPins'],
    knownIntegrations: ['Votan\'s Minimap', 'Map Pins'],
    notes: 'Primary resource tracking. Large data footprint.',
  },

  // ===========================================================================
  // CRAFTING
  // ===========================================================================
  {
    name: 'Dolgubon\'s Lazy Writ Crafter',
    esouiId: 1265,
    primaryFunction: 'Automated writ crafting',
    globalNamespace: 'WritCreater',
    exposedData: [
      {
        name: 'Writ Status',
        accessMethod: 'global',
        accessPath: 'WritCreater.writStatus',
        dataType: '{ pending: number, completed: number, ... }',
        description: 'Current writ completion status',
        realtime: true,
        updateFrequency: 'immediate',
      },
      {
        name: 'Materials Needed',
        accessMethod: 'api',
        accessPath: 'WritCreater:GetMaterialsNeeded()',
        dataType: 'table<itemId, count>',
        description: 'Materials required for pending writs',
        realtime: true,
        updateFrequency: 'on-demand',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0', 'LibLazyCrafting', 'Inventory Insight'],
    knownIntegrations: ['Inventory Insight', 'FCO CraftFilter'],
    notes: 'Most popular crafting automation. Integrates with inventory addons.',
  },

  {
    name: 'Potion Maker',
    esouiId: 614,
    primaryFunction: 'Alchemy recipe and effect database',
    globalNamespace: 'PotionMaker',
    exposedData: [
      {
        name: 'Reagent Effects',
        accessMethod: 'global',
        accessPath: 'PotionMaker.ReagentData',
        dataType: 'table<reagentId, effects[]>',
        description: 'Known reagent effects',
        realtime: false,
        updateFrequency: 'on-demand',
      },
      {
        name: 'Recipe Calculator',
        accessMethod: 'api',
        accessPath: 'PotionMaker:FindRecipe(desiredEffects)',
        dataType: 'table[] (matching recipes)',
        description: 'Find reagent combinations for desired effects',
        realtime: false,
        updateFrequency: 'on-demand',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0'],
    knownIntegrations: ['Dolgubon\'s Lazy Writ Crafter'],
    notes: 'Comprehensive alchemy database.',
  },

  // ===========================================================================
  // GROUP & RAIDING
  // ===========================================================================
  {
    name: 'Raid Notifier',
    esouiId: 1066,
    primaryFunction: 'Boss mechanic alerts for trials/dungeons',
    globalNamespace: 'RaidNotifier',
    exposedData: [
      {
        name: 'Active Alerts',
        accessMethod: 'callback',
        accessPath: 'RaidNotifier:RegisterCallback("AlertTriggered", callback)',
        dataType: '{ alertType: string, message: string, ... }',
        description: 'Fires when a mechanic alert triggers',
        exampleCode: 'RaidNotifier:RegisterCallback("AlertTriggered", function(alert) ... end)',
        realtime: true,
        updateFrequency: 'immediate',
      },
      {
        name: 'Boss Phase',
        accessMethod: 'global',
        accessPath: 'RaidNotifier.currentPhase',
        dataType: 'number',
        description: 'Current boss fight phase',
        realtime: true,
        updateFrequency: 'immediate',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0', 'LibCustomMenu'],
    knownIntegrations: ['Combat Metrics', 'FTC'],
    notes: 'Essential for endgame content. Phase tracking useful for analysis.',
  },

  {
    name: 'Hodor Reflexes',
    esouiId: 1835,
    primaryFunction: 'Synergy and interrupt notifications',
    globalNamespace: 'HodorReflexes',
    exposedData: [
      {
        name: 'Synergy Available',
        accessMethod: 'callback',
        accessPath: 'CALLBACK_MANAGER:RegisterCallback("HodorSynergyAvailable", callback)',
        dataType: 'synergyInfo',
        description: 'Fires when a synergy becomes available',
        realtime: true,
        updateFrequency: 'immediate',
      },
      {
        name: 'Interrupt Needed',
        accessMethod: 'callback',
        accessPath: 'CALLBACK_MANAGER:RegisterCallback("HodorInterruptNeeded", callback)',
        dataType: 'interruptInfo',
        description: 'Fires when an interrupt is needed',
        realtime: true,
        updateFrequency: 'immediate',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0'],
    knownIntegrations: ['Raid Notifier'],
    notes: 'Group utility tracking. Useful for performance metrics.',
  },

  // ===========================================================================
  // UI & QUALITY OF LIFE
  // ===========================================================================
  {
    name: 'Bandits User Interface',
    esouiId: 1678,
    primaryFunction: 'Complete UI overhaul',
    globalNamespace: 'BUI',
    exposedData: [
      {
        name: 'UI Configuration',
        accessMethod: 'global',
        accessPath: 'BUI.settings',
        dataType: 'table',
        description: 'Current UI configuration',
        realtime: false,
        updateFrequency: 'on-demand',
      },
      {
        name: 'Frame Positions',
        accessMethod: 'global',
        accessPath: 'BUI.frames',
        dataType: 'table<frameName, position>',
        description: 'UI frame positions',
        realtime: false,
        updateFrequency: 'on-demand',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0', 'Combat Metrics'],
    knownIntegrations: ['Combat Metrics', 'FTC'],
    notes: 'Popular UI replacement. Can integrate with combat addons.',
  },

  {
    name: 'pChat',
    esouiId: 422,
    primaryFunction: 'Enhanced chat functionality',
    globalNamespace: 'pChat',
    exposedData: [
      {
        name: 'Chat History',
        accessMethod: 'global',
        accessPath: 'pChat.chatHistory',
        dataType: 'table[]',
        description: 'Persisted chat message history',
        realtime: false,
        updateFrequency: 'immediate',
      },
      {
        name: 'Player Names',
        accessMethod: 'global',
        accessPath: 'pChat.nameCache',
        dataType: 'table<displayName, characterName>',
        description: 'Cache of player name mappings',
        realtime: false,
        updateFrequency: 'on-demand',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0', 'LibChatMessage'],
    knownIntegrations: ['Various chat addons'],
    notes: 'Chat enhancement. Name cache useful for player identification.',
  },

  // ===========================================================================
  // SETS & BUILDS
  // ===========================================================================
  {
    name: 'IIfA (Inventory Insight)',
    esouiId: 724,
    primaryFunction: 'Set collection tracking',
    globalNamespace: 'IIfA',
    exposedData: [
      {
        name: 'Set Completion',
        accessMethod: 'api',
        accessPath: 'IIfA:GetSetCompletion(setId)',
        dataType: '{ owned: number, total: number, pieces: table }',
        description: 'Set completion status',
        realtime: false,
        updateFrequency: 'on-demand',
      },
      {
        name: 'Item Locations',
        accessMethod: 'api',
        accessPath: 'IIfA:GetItemLocations(itemId)',
        dataType: 'table[] (character/bank locations)',
        description: 'Where an item is stored across characters',
        realtime: false,
        updateFrequency: 'on-demand',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0', 'LibSets'],
    knownIntegrations: ['Set Tracker', 'Dressing Room'],
    notes: 'Essential for set farming and build management.',
  },

  {
    name: 'Dressing Room',
    esouiId: 769,
    primaryFunction: 'Gear set management and swapping',
    globalNamespace: 'DressingRoom',
    exposedData: [
      {
        name: 'Saved Builds',
        accessMethod: 'global',
        accessPath: 'DressingRoom.savedSets',
        dataType: 'table<setName, gearConfiguration>',
        description: 'All saved gear sets',
        realtime: false,
        updateFrequency: 'on-demand',
      },
      {
        name: 'Build Changed',
        accessMethod: 'callback',
        accessPath: 'CALLBACK_MANAGER:RegisterCallback("DressingRoom_GearSwapped", callback)',
        dataType: 'string (setName)',
        description: 'Fires when player swaps gear sets',
        realtime: true,
        updateFrequency: 'immediate',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0'],
    knownIntegrations: ['Alpha Gear', 'Combat Metrics'],
    notes: 'Build tracking essential for performance correlation.',
  },

  // ===========================================================================
  // COMPANION ADDONS (Personal Assistant suite)
  // ===========================================================================
  {
    name: 'Personal Assistant',
    esouiId: 2079,
    primaryFunction: 'Suite of automation tools',
    globalNamespace: 'PersonalAssistant',
    exposedData: [
      {
        name: 'Banking Rules',
        accessMethod: 'global',
        accessPath: 'PersonalAssistant.Banking.rules',
        dataType: 'table<itemType, rule>',
        description: 'Configured banking automation rules',
        realtime: false,
        updateFrequency: 'on-demand',
      },
      {
        name: 'Repair Status',
        accessMethod: 'global',
        accessPath: 'PersonalAssistant.Repair.status',
        dataType: '{ goldSpent: number, itemsRepaired: number }',
        description: 'Automatic repair statistics',
        realtime: false,
        updateFrequency: 'on-demand',
      },
      {
        name: 'Junk Rules',
        accessMethod: 'global',
        accessPath: 'PersonalAssistant.Junk.rules',
        dataType: 'table<itemType, shouldJunk>',
        description: 'Item junking configuration',
        realtime: false,
        updateFrequency: 'on-demand',
      },
    ],
    consumesFrom: ['LibAddonMenu-2.0', 'LibAsync'],
    knownIntegrations: ['FCO ItemSaver', 'Inventory Insight'],
    notes: 'Modular suite - all 5 modules expose their configuration.',
  },
] as const;

// ===========================================================================
// Data Synergy Analysis Functions
// ===========================================================================

export interface DataSynergyOpportunity {
  readonly sourceAddon: string;
  readonly targetAddon: string;
  readonly dataPoint: string;
  readonly synergyType: 'enhancement' | 'correlation' | 'automation' | 'aggregation';
  readonly description: string;
  readonly implementationComplexity: 'low' | 'medium' | 'high';
}

/**
 * Identify potential data synergies between addons.
 * This is the foundation for the "Addon Collaborator" concept.
 *
 * NOTE: These are NOVEL synergies that don't exist natively.
 * We exclude:
 * - Synergies already implemented by the addons themselves
 * - Features made irrelevant by ESO+ (craft bag, etc.)
 */
export function findDataSynergies(): DataSynergyOpportunity[] {
  const synergies: DataSynergyOpportunity[] = [];

  // Combat Metrics + Dressing Room = Build Performance Correlation
  // CMX doesn't know which Dressing Room build was active during a fight
  synergies.push({
    sourceAddon: 'Combat Metrics',
    targetAddon: 'Dressing Room',
    dataPoint: 'fightDps + activeBuildName',
    synergyType: 'correlation',
    description: 'Track which gear set was active during each fight to compare build performance over time',
    implementationComplexity: 'medium',
  });

  // Combat Metrics + Raid Notifier = Phase-specific Performance
  // Neither addon segments DPS by boss phase natively
  synergies.push({
    sourceAddon: 'Combat Metrics',
    targetAddon: 'Raid Notifier',
    dataPoint: 'fightData + bossPhase',
    synergyType: 'enhancement',
    description: 'Segment DPS/HPS by boss phase to identify weak execution phases',
    implementationComplexity: 'medium',
  });

  // Hodor Reflexes + Combat Metrics = Group Contribution
  // CMX tracks damage, but not synergies activated or interrupts landed
  synergies.push({
    sourceAddon: 'Hodor Reflexes',
    targetAddon: 'Combat Metrics',
    dataPoint: 'synergiesUsed + interruptsLanded',
    synergyType: 'enhancement',
    description: 'Add synergy activations and interrupts to combat logs for full contribution picture',
    implementationComplexity: 'medium',
  });

  // IIfA + Master Merchant = Set Value Tracking
  // Neither addon calculates total portfolio value
  synergies.push({
    sourceAddon: 'IIfA',
    targetAddon: 'Master Merchant',
    dataPoint: 'setCompletion + priceData',
    synergyType: 'aggregation',
    description: 'Calculate total gold value of your set piece collection across all characters',
    implementationComplexity: 'low',
  });

  // pChat Name Cache + Combat Metrics = Named Performance Logs
  // CMX shows @UserIDs, not character names which are more memorable
  synergies.push({
    sourceAddon: 'pChat',
    targetAddon: 'Combat Metrics',
    dataPoint: 'nameCache + groupDps',
    synergyType: 'enhancement',
    description: 'Display character names instead of @handles in group DPS meters',
    implementationComplexity: 'low',
  });

  // Dressing Room + Personal Assistant = Smart Banking (non-ESO+ players)
  // Useful for players without unlimited bank space
  synergies.push({
    sourceAddon: 'Dressing Room',
    targetAddon: 'Personal Assistant',
    dataPoint: 'savedSets + bankingRules',
    synergyType: 'automation',
    description: 'Auto-bank gear not used in any saved build (useful for non-ESO+ players)',
    implementationComplexity: 'medium',
  });

  // IIfA + LibSets = Missing Set Pieces
  // Know exactly what pieces you still need to complete sets
  synergies.push({
    sourceAddon: 'IIfA',
    targetAddon: 'LibSets',
    dataPoint: 'ownedPieces + setDefinitions',
    synergyType: 'aggregation',
    description: 'Show which specific set pieces (traits/weights) you still need to collect',
    implementationComplexity: 'medium',
  });

  // Combat Metrics + ESO Logs Integration
  // Export fight data in a format for external analysis
  synergies.push({
    sourceAddon: 'Combat Metrics',
    targetAddon: 'ESO Logs',
    dataPoint: 'fightHistory + exportFormat',
    synergyType: 'enhancement',
    description: 'Export combat data to esologs.com for cross-server percentile comparison',
    implementationComplexity: 'high',
  });

  // Group Finder + Raid Notifier = Role Coverage Analysis
  // Know if your group has all important buffs/debuffs covered
  synergies.push({
    sourceAddon: 'Group Composition',
    targetAddon: 'Raid Notifier',
    dataPoint: 'groupClasses + requiredBuffs',
    synergyType: 'enhancement',
    description: 'Analyze group composition to show which major/minor buffs are missing',
    implementationComplexity: 'high',
  });

  // ATT + MM = Flip Profit Validation
  // Compare predicted vs actual profit on flips
  synergies.push({
    sourceAddon: 'Arkadius Trade Tools',
    targetAddon: 'Master Merchant',
    dataPoint: 'purchaseHistory + salesHistory',
    synergyType: 'correlation',
    description: 'Track actual flip profit vs predicted profit to improve trading strategy',
    implementationComplexity: 'medium',
  });

  return synergies;
}

/**
 * Get all addons that expose a specific type of data.
 */
export function getAddonsByDataType(
  dataType: 'combat' | 'price' | 'inventory' | 'location' | 'crafting' | 'ui'
): AddonDataAPI[] {
  const mappings: Record<string, string[]> = {
    combat: ['Combat Metrics', 'FTC', 'Raid Notifier', 'Hodor Reflexes'],
    price: ['Master Merchant', 'Tamriel Trade Centre', 'Arkadius Trade Tools'],
    inventory: ['Inventory Insight', 'IIfA', 'Personal Assistant'],
    location: ['Destinations', 'Harvest Map'],
    crafting: ["Dolgubon's Lazy Writ Crafter", 'Potion Maker'],
    ui: ['Bandits User Interface', 'pChat', 'Dressing Room'],
  };

  const addonNames = mappings[dataType] || [];
  return ADDON_DATA_APIS.filter(a => addonNames.includes(a.name));
}

/**
 * Get integration suggestions for a specific addon.
 */
export function getIntegrationSuggestions(addonName: string): DataSynergyOpportunity[] {
  const synergies = findDataSynergies();
  return synergies.filter(
    s => s.sourceAddon === addonName || s.targetAddon === addonName
  );
}

/**
 * Get the data API for a specific addon.
 */
export function getAddonDataAPI(addonName: string): AddonDataAPI | undefined {
  return ADDON_DATA_APIS.find(
    a => a.name.toLowerCase() === addonName.toLowerCase()
  );
}

/**
 * Find addons that consume from a specific source.
 */
export function findConsumers(sourceAddon: string): AddonDataAPI[] {
  return ADDON_DATA_APIS.filter(a => a.consumesFrom.includes(sourceAddon));
}

/**
 * Get the dependency graph for addon data sharing.
 */
export function getDataDependencyGraph(): Map<string, Set<string>> {
  const graph = new Map<string, Set<string>>();

  for (const addon of ADDON_DATA_APIS) {
    if (!graph.has(addon.name)) {
      graph.set(addon.name, new Set());
    }
    for (const dep of addon.consumesFrom) {
      graph.get(addon.name)!.add(dep);
    }
  }

  return graph;
}
