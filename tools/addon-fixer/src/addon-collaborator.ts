/**
 * Addon Collaborator - Data Synergy Framework
 *
 * The "Addon Collaborator" is a concept for a central addon that maximizes
 * synergy between different ESO addons by:
 *
 * 1. Brokering data between addons that don't natively integrate
 * 2. Aggregating related data from multiple sources
 * 3. Providing a unified API for addon developers
 * 4. Enabling analytics across addon boundaries
 *
 * This file defines the architecture and provides a reference implementation.
 */

// ===========================================================================
// DESIGN PHILOSOPHY
// ===========================================================================
/**
 * Why "Addon Collaborator"?
 *
 * Problem: ESO addons are siloed. Combat Metrics tracks DPS but doesn't know
 * your gear. Dressing Room tracks gear but doesn't know your performance.
 * Master Merchant knows prices but not your inventory needs.
 *
 * Solution: A lightweight broker addon that:
 * - Listens to existing addon events/data
 * - Correlates data across addon boundaries
 * - Exposes unified APIs for consumption
 * - Generates insights no single addon can provide
 *
 * Philosophy:
 * - Zero configuration for end users
 * - Automatic detection of installed addons
 * - Passive data collection (no performance impact)
 * - Open API for other addon authors
 */

// ===========================================================================
// CORE TYPES
// ===========================================================================

export interface DataSource {
  /** Unique identifier for this data source */
  readonly id: string;
  /** Human-readable name */
  readonly name: string;
  /** The addon this data comes from */
  readonly sourceAddon: string;
  /** Whether the source addon is detected as installed */
  detected: boolean;
  /** How to fetch the data */
  readonly fetchMethod: () => unknown;
  /** Data schema description */
  readonly schema: string;
  /** Update frequency */
  readonly updateFrequency: 'realtime' | 'periodic' | 'on-demand';
}

export interface CorrelatedInsight {
  /** Unique ID for this insight type */
  readonly id: string;
  /** Human-readable name */
  readonly name: string;
  /** Required data sources */
  readonly requiredSources: string[];
  /** Function to generate the insight */
  readonly generate: (data: Map<string, unknown>) => unknown;
  /** Description of what this insight provides */
  readonly description: string;
}

export interface CollaboratorEvent {
  readonly type: string;
  readonly timestamp: number;
  readonly source: string;
  readonly data: unknown;
}

// ===========================================================================
// ADDON COLLABORATOR ARCHITECTURE
// ===========================================================================

/**
 * The Addon Collaborator acts as a data broker and correlation engine.
 *
 * Architecture:
 *
 * ┌─────────────────────────────────────────────────────────────────┐
 * │                    ADDON COLLABORATOR                          │
 * │                                                                 │
 * │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
 * │  │   Combat    │   │  Inventory  │   │   Trading   │          │
 * │  │   Sources   │   │   Sources   │   │   Sources   │          │
 * │  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘          │
 * │         │                 │                 │                  │
 * │         ▼                 ▼                 ▼                  │
 * │  ┌─────────────────────────────────────────────────────┐      │
 * │  │              DATA AGGREGATION LAYER                 │      │
 * │  │  - Normalizes data formats                          │      │
 * │  │  - Timestamps all events                            │      │
 * │  │  - Maintains data freshness                         │      │
 * │  └─────────────────────────────────────────────────────┘      │
 * │                          │                                     │
 * │                          ▼                                     │
 * │  ┌─────────────────────────────────────────────────────┐      │
 * │  │              CORRELATION ENGINE                     │      │
 * │  │  - Links DPS to gear sets                          │      │
 * │  │  - Links prices to inventory needs                 │      │
 * │  │  - Links boss phases to performance                │      │
 * │  └─────────────────────────────────────────────────────┘      │
 * │                          │                                     │
 * │                          ▼                                     │
 * │  ┌─────────────────────────────────────────────────────┐      │
 * │  │              INSIGHT GENERATION                     │      │
 * │  │  - Build performance rankings                       │      │
 * │  │  - Farming efficiency suggestions                  │      │
 * │  │  - Trading opportunity alerts                      │      │
 * │  └─────────────────────────────────────────────────────┘      │
 * │                          │                                     │
 * │                          ▼                                     │
 * │  ┌─────────────────────────────────────────────────────┐      │
 * │  │              PUBLIC API                             │      │
 * │  │  AddonCollaborator:GetBuildPerformance(build)       │      │
 * │  │  AddonCollaborator:GetMaterialNeeds()               │      │
 * │  │  AddonCollaborator:RegisterCallback(event, fn)      │      │
 * │  └─────────────────────────────────────────────────────┘      │
 * │                                                                 │
 * └─────────────────────────────────────────────────────────────────┘
 *                          │
 *                          ▼
 *         Other addons can consume aggregated data
 */

// ===========================================================================
// REFERENCE IMPLEMENTATION (TypeScript)
// ===========================================================================

/**
 * AddonCollaborator class - reference implementation.
 *
 * In Lua, this would be structured similarly but use EVENT_MANAGER
 * and CALLBACK_MANAGER for the pub/sub pattern.
 */
export class AddonCollaborator {
  private sources: Map<string, DataSource> = new Map();
  private insights: Map<string, CorrelatedInsight> = new Map();
  private dataCache: Map<string, { data: unknown; timestamp: number }> = new Map();
  private callbacks: Map<string, Array<(event: CollaboratorEvent) => void>> = new Map();
  private eventHistory: CollaboratorEvent[] = [];

  constructor() {
    this.registerDefaultSources();
    this.registerDefaultInsights();
  }

  // -------------------------------------------------------------------------
  // Source Registration
  // -------------------------------------------------------------------------

  private registerDefaultSources(): void {
    // Combat Metrics - DPS/HPS data
    this.registerSource({
      id: 'cmx.fight',
      name: 'Combat Metrics Fight Data',
      sourceAddon: 'Combat Metrics',
      detected: false,
      fetchMethod: () => {
        // In Lua: return CMX and CMX.currentFight
        return null;
      },
      schema: '{ dps: number, hps: number, duration: number, damage: number }',
      updateFrequency: 'realtime',
    });

    // Dressing Room - Build data
    this.registerSource({
      id: 'dressingroom.builds',
      name: 'Dressing Room Saved Builds',
      sourceAddon: 'Dressing Room',
      detected: false,
      fetchMethod: () => {
        // In Lua: return DressingRoom and DressingRoom.savedSets
        return null;
      },
      schema: 'table<buildName, gearConfig>',
      updateFrequency: 'on-demand',
    });

    // Master Merchant - Price data
    this.registerSource({
      id: 'mm.prices',
      name: 'Master Merchant Prices',
      sourceAddon: 'Master Merchant',
      detected: false,
      fetchMethod: () => {
        // In Lua: return MasterMerchant
        return null;
      },
      schema: '{ ItemPriceByItemLink: function }',
      updateFrequency: 'on-demand',
    });

    // Inventory Insight - Inventory data
    this.registerSource({
      id: 'iifa.inventory',
      name: 'Inventory Insight Data',
      sourceAddon: 'Inventory Insight',
      detected: false,
      fetchMethod: () => {
        // In Lua: return IIfA and IIfA.data
        return null;
      },
      schema: 'table<characterName, inventoryData>',
      updateFrequency: 'on-demand',
    });

    // FTC - Buff tracking
    this.registerSource({
      id: 'ftc.buffs',
      name: 'FTC Active Buffs',
      sourceAddon: 'FTC',
      detected: false,
      fetchMethod: () => {
        // In Lua: return FTC and FTC.Buffs
        return null;
      },
      schema: 'table<abilityId, buffInfo>',
      updateFrequency: 'realtime',
    });

    // Raid Notifier - Boss phase
    this.registerSource({
      id: 'rn.phase',
      name: 'Raid Notifier Boss Phase',
      sourceAddon: 'Raid Notifier',
      detected: false,
      fetchMethod: () => {
        // In Lua: return RaidNotifier and RaidNotifier.currentPhase
        return null;
      },
      schema: 'number',
      updateFrequency: 'realtime',
    });
  }

  registerSource(source: DataSource): void {
    this.sources.set(source.id, source);
  }

  // -------------------------------------------------------------------------
  // Insight Registration
  // -------------------------------------------------------------------------

  private registerDefaultInsights(): void {
    // Build Performance Insight
    this.registerInsight({
      id: 'build.performance',
      name: 'Build Performance Correlation',
      requiredSources: ['cmx.fight', 'dressingroom.builds'],
      description: 'Correlates DPS performance with equipped gear sets',
      generate: (data) => {
        const fights = data.get('cmx.fight') as unknown[];
        const builds = data.get('dressingroom.builds') as Record<string, unknown>;

        if (!fights || !builds) return null;

        // Calculate average DPS per build
        const buildPerformance: Record<string, { avgDps: number; fights: number }> = {};

        // In a real implementation, this would:
        // 1. Track which build was active during each fight
        // 2. Aggregate DPS across fights for each build
        // 3. Calculate averages and rankings

        return buildPerformance;
      },
    });

    // Material Needs Insight
    this.registerInsight({
      id: 'material.needs',
      name: 'Cross-Character Material Needs',
      requiredSources: ['iifa.inventory'],
      description: 'Identifies materials needed across all characters',
      generate: (data) => {
        const inventory = data.get('iifa.inventory') as Record<string, unknown>;

        if (!inventory) return null;

        // Analyze inventory and identify:
        // - Low-stock materials
        // - Items to bank/withdraw
        // - Crafting material distribution

        return {
          lowStock: [],
          toBank: [],
          toWithdraw: [],
        };
      },
    });

    // Price Opportunity Insight
    this.registerInsight({
      id: 'price.opportunity',
      name: 'Trading Opportunities',
      requiredSources: ['mm.prices', 'iifa.inventory'],
      description: 'Identifies valuable items in inventory',
      generate: (data) => {
        const prices = data.get('mm.prices');
        const inventory = data.get('iifa.inventory');

        if (!prices || !inventory) return null;

        // In a real implementation, this would:
        // 1. Scan all inventory items
        // 2. Look up prices via MM API
        // 3. Flag high-value items not marked for keeping

        return {
          highValue: [],
          priceSpiking: [],
          underpriced: [],
        };
      },
    });

    // Buff Uptime Insight
    this.registerInsight({
      id: 'buff.uptime',
      name: 'Buff Uptime Analysis',
      requiredSources: ['ftc.buffs', 'cmx.fight'],
      description: 'Correlates buff uptime with DPS performance',
      generate: (data) => {
        const buffs = data.get('ftc.buffs');
        const fights = data.get('cmx.fight');

        if (!buffs || !fights) return null;

        // Calculate buff uptime percentages
        // Correlate with DPS output

        return {
          majorBuffs: {},
          minorBuffs: {},
          correlation: 0,
        };
      },
    });

    // Phase Performance Insight
    this.registerInsight({
      id: 'phase.performance',
      name: 'Boss Phase Performance',
      requiredSources: ['cmx.fight', 'rn.phase'],
      description: 'Tracks DPS per boss phase for trial optimization',
      generate: (data) => {
        const fights = data.get('cmx.fight');
        const phases = data.get('rn.phase');

        if (!fights || !phases) return null;

        // Track DPS by phase
        // Identify weak phases for targeted practice

        return {
          phaseData: {},
          weakestPhase: null,
          recommendations: [],
        };
      },
    });
  }

  registerInsight(insight: CorrelatedInsight): void {
    this.insights.set(insight.id, insight);
  }

  // -------------------------------------------------------------------------
  // Data Fetching & Caching
  // -------------------------------------------------------------------------

  fetchData(sourceId: string): unknown {
    const source = this.sources.get(sourceId);
    if (!source || !source.detected) return null;

    const now = Date.now();
    const cached = this.dataCache.get(sourceId);

    // Return cached data if fresh enough
    if (cached) {
      const maxAge =
        source.updateFrequency === 'realtime' ? 1000 :
        source.updateFrequency === 'periodic' ? 60000 :
        300000; // on-demand: 5 minutes

      if (now - cached.timestamp < maxAge) {
        return cached.data;
      }
    }

    // Fetch fresh data
    const data = source.fetchMethod();
    this.dataCache.set(sourceId, { data, timestamp: now });

    // Emit event
    this.emitEvent({
      type: 'dataFetched',
      timestamp: now,
      source: sourceId,
      data,
    });

    return data;
  }

  // -------------------------------------------------------------------------
  // Insight Generation
  // -------------------------------------------------------------------------

  generateInsight(insightId: string): unknown {
    const insight = this.insights.get(insightId);
    if (!insight) return null;

    // Fetch all required data
    const data = new Map<string, unknown>();
    for (const sourceId of insight.requiredSources) {
      const sourceData = this.fetchData(sourceId);
      if (sourceData === null) {
        // Missing required source
        return null;
      }
      data.set(sourceId, sourceData);
    }

    // Generate the insight
    const result = insight.generate(data);

    // Emit event
    this.emitEvent({
      type: 'insightGenerated',
      timestamp: Date.now(),
      source: insightId,
      data: result,
    });

    return result;
  }

  // -------------------------------------------------------------------------
  // Event System
  // -------------------------------------------------------------------------

  registerCallback(
    eventType: string,
    callback: (event: CollaboratorEvent) => void
  ): void {
    if (!this.callbacks.has(eventType)) {
      this.callbacks.set(eventType, []);
    }
    this.callbacks.get(eventType)!.push(callback);
  }

  private emitEvent(event: CollaboratorEvent): void {
    this.eventHistory.push(event);

    // Trim history if too long
    if (this.eventHistory.length > 1000) {
      this.eventHistory = this.eventHistory.slice(-500);
    }

    // Notify callbacks
    const callbacks = this.callbacks.get(event.type) || [];
    for (const callback of callbacks) {
      try {
        callback(event);
      } catch {
        // Ignore callback errors
      }
    }
  }

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  /**
   * Check which addons are detected.
   */
  getDetectedAddons(): string[] {
    const detected: string[] = [];
    for (const source of this.sources.values()) {
      if (source.detected && !detected.includes(source.sourceAddon)) {
        detected.push(source.sourceAddon);
      }
    }
    return detected;
  }

  /**
   * Get available insights based on detected addons.
   */
  getAvailableInsights(): string[] {
    const available: string[] = [];
    for (const [id, insight] of this.insights) {
      const hasAllSources = insight.requiredSources.every(sourceId => {
        const source = this.sources.get(sourceId);
        return source && source.detected;
      });
      if (hasAllSources) {
        available.push(id);
      }
    }
    return available;
  }

  /**
   * Get all registered data sources.
   */
  getSources(): DataSource[] {
    return Array.from(this.sources.values());
  }

  /**
   * Get all registered insights.
   */
  getInsights(): CorrelatedInsight[] {
    return Array.from(this.insights.values());
  }
}

// ===========================================================================
// LUA REFERENCE IMPLEMENTATION
// ===========================================================================

/**
 * This is how the Addon Collaborator would be implemented in Lua.
 * Provided as reference for actual addon development.
 */
export const LUA_REFERENCE = `
-- AddonCollaborator.lua
-- A data broker and correlation engine for ESO addons

AddonCollaborator = {
    name = "AddonCollaborator",
    version = "1.0.0",

    -- Data sources registry
    sources = {},

    -- Insight generators
    insights = {},

    -- Data cache
    cache = {},

    -- Callbacks
    callbacks = {},
}

-- Initialize on addon load
function AddonCollaborator:Initialize()
    -- Detect installed addons
    self:DetectAddons()

    -- Register event hooks
    self:RegisterEventHooks()

    -- Set up periodic data refresh
    EVENT_MANAGER:RegisterForUpdate(
        self.name .. "_Refresh",
        5000, -- Every 5 seconds
        function() self:RefreshData() end
    )
end

-- Detect which addons are installed
function AddonCollaborator:DetectAddons()
    -- Combat Metrics
    if CMX then
        self.sources["cmx.fight"] = {
            detected = true,
            fetch = function()
                return CMX.currentFight
            end,
        }
    end

    -- Dressing Room
    if DressingRoom then
        self.sources["dressingroom.builds"] = {
            detected = true,
            fetch = function()
                return DressingRoom.savedSets
            end,
        }
    end

    -- Master Merchant
    if MasterMerchant then
        self.sources["mm.prices"] = {
            detected = true,
            fetch = function()
                return MasterMerchant
            end,
        }
    end

    -- Inventory Insight
    if IIfA then
        self.sources["iifa.inventory"] = {
            detected = true,
            fetch = function()
                return IIfA.data
            end,
        }
    end

    -- FTC
    if FTC then
        self.sources["ftc.buffs"] = {
            detected = true,
            fetch = function()
                return FTC.Buffs
            end,
        }
    end

    -- Raid Notifier
    if RaidNotifier then
        self.sources["rn.phase"] = {
            detected = true,
            fetch = function()
                return RaidNotifier.currentPhase
            end,
        }
    end
end

-- Register event hooks for real-time data
function AddonCollaborator:RegisterEventHooks()
    -- Combat state changes
    EVENT_MANAGER:RegisterForEvent(
        self.name,
        EVENT_PLAYER_COMBAT_STATE,
        function(_, inCombat)
            self:OnCombatStateChanged(inCombat)
        end
    )

    -- Gear changes (for build correlation)
    EVENT_MANAGER:RegisterForEvent(
        self.name,
        EVENT_INVENTORY_SINGLE_SLOT_UPDATE,
        function(_, bagId, slotIndex)
            if bagId == BAG_WORN then
                self:OnGearChanged()
            end
        end
    )

    -- Register callbacks with other addons if they support it
    if CMX and CMX.RegisterCallback then
        CMX:RegisterCallback("CombatStateChanged", function(inCombat)
            self:OnCMXCombatState(inCombat)
        end)
    end

    if DressingRoom and CALLBACK_MANAGER then
        CALLBACK_MANAGER:RegisterCallback("DressingRoom_GearSwapped", function(setName)
            self:OnBuildSwapped(setName)
        end)
    end
end

-- Public API: Get build performance data
function AddonCollaborator:GetBuildPerformance()
    if not self.sources["cmx.fight"] or not self.sources["dressingroom.builds"] then
        return nil
    end

    -- Implementation would aggregate fight data by build
    return self.insights.buildPerformance
end

-- Public API: Get material needs
function AddonCollaborator:GetMaterialNeeds()
    if not self.sources["iifa.inventory"] then
        return nil
    end

    -- Implementation would analyze inventory
    return self.insights.materialNeeds
end

-- Public API: Register for events
function AddonCollaborator:RegisterCallback(eventType, callback)
    if not self.callbacks[eventType] then
        self.callbacks[eventType] = {}
    end
    table.insert(self.callbacks[eventType], callback)
end

-- Emit event to callbacks
function AddonCollaborator:EmitEvent(eventType, data)
    local callbacks = self.callbacks[eventType]
    if callbacks then
        for _, callback in ipairs(callbacks) do
            callback(data)
        end
    end
end

-- Initialize when addon loads
EVENT_MANAGER:RegisterForEvent(
    AddonCollaborator.name,
    EVENT_ADD_ON_LOADED,
    function(_, addonName)
        if addonName == AddonCollaborator.name then
            AddonCollaborator:Initialize()
        end
    end
)
`;

// ===========================================================================
// EXAMPLE USAGE SCENARIOS
// ===========================================================================

/**
 * Scenario 1: Build Performance Tracking
 *
 * A player wants to know which of their gear sets performs best.
 *
 * Without Addon Collaborator:
 * - Use Dressing Room to swap builds
 * - Use Combat Metrics to track DPS
 * - Manually note which build was active for each fight
 * - Manually calculate averages
 *
 * With Addon Collaborator:
 * - Automatically correlates DPS to active build
 * - Generates per-build performance statistics
 * - Shows "Build A: avg 45k DPS | Build B: avg 52k DPS"
 */

/**
 * Scenario 2: Smart Farming Suggestions
 *
 * A player wants to farm materials efficiently.
 *
 * Without Addon Collaborator:
 * - Open Inventory Insight to check what materials are low
 * - Open Harvest Map to find node locations
 * - Manually correlate the two
 *
 * With Addon Collaborator:
 * - Analyzes inventory across all characters
 * - Identifies materials below threshold
 * - Highlights Harvest Map nodes for needed materials only
 */

/**
 * Scenario 3: Buff Rotation Optimization
 *
 * A player wants to improve their buff uptime.
 *
 * Without Addon Collaborator:
 * - Watch FTC buff bars during combat
 * - Try to correlate with Combat Metrics DPS
 * - Mentally track patterns
 *
 * With Addon Collaborator:
 * - Records buff states during combat
 * - Correlates buff uptime with DPS output
 * - Shows "Your DPS is 15% higher when Major Brutality is up"
 */

/**
 * Scenario 4: Trial Phase Analysis
 *
 * A trial group wants to identify weak phases.
 *
 * Without Addon Collaborator:
 * - Use Raid Notifier for phase alerts
 * - Use Combat Metrics for overall DPS
 * - Manually segment the data
 *
 * With Addon Collaborator:
 * - Tracks DPS per boss phase automatically
 * - Shows "Phase 2 DPS: 35k | Phase 3 DPS: 28k"
 * - Recommends focus areas
 */

export default AddonCollaborator;
