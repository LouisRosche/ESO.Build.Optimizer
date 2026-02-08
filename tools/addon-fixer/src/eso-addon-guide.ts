/**
 * ESO Addon Development Guide
 *
 * Comprehensive documentation of best practices, common bugs, and solutions
 * assembled from ESOUI wiki insights and community knowledge.
 *
 * This serves as both a reference and a rule set for the addon fixer.
 */

// ===========================================================================
// COMMON BUGS AND FIXES
// ===========================================================================

export interface CommonBug {
  readonly id: string;
  readonly title: string;
  readonly description: string;
  readonly symptoms: string[];
  readonly cause: string;
  readonly fix: string;
  readonly codeExample?: {
    readonly bad: string;
    readonly good: string;
  };
  readonly affectedVersions?: string;
  readonly severity: 'critical' | 'major' | 'minor';
  readonly category: 'memory' | 'performance' | 'api' | 'events' | 'ui' | 'savedvars' | 'threading';
}

export const COMMON_BUGS: readonly CommonBug[] = [
  // Memory Bugs
  {
    id: 'MEM001',
    title: 'Unbounded Table Growth',
    description: 'Tables that grow without limit during gameplay, causing memory bloat and eventual crashes',
    symptoms: [
      'Memory usage increases over time',
      'Game becomes sluggish after extended play',
      'Eventual crash with "out of memory" errors',
    ],
    cause: 'Storing data in tables without ever cleaning up old entries',
    fix: 'Implement table size limits with oldest-entry eviction, or use weak tables',
    codeExample: {
      bad: `-- BAD: Unbounded history
local history = {}
function OnCombatEvent(...)
    table.insert(history, {...})  -- Never cleaned up!
end`,
      good: `-- GOOD: Bounded history with eviction
local MAX_HISTORY = 1000
local history = {}
function OnCombatEvent(...)
    table.insert(history, {...})
    while #history > MAX_HISTORY do
        table.remove(history, 1)
    end
end`,
    },
    severity: 'critical',
    category: 'memory',
  },
  {
    id: 'MEM002',
    title: 'String Concatenation in Loops',
    description: 'Creating new strings in tight loops causes excessive garbage collection',
    symptoms: [
      'Frame rate drops during combat',
      'Micro-stutters when many events fire',
    ],
    cause: 'Lua strings are immutable; each concatenation creates a new string object',
    fix: 'Use table.concat() or string.format() for building strings',
    codeExample: {
      bad: `-- BAD: Creates N string objects
local msg = ""
for i = 1, 100 do
    msg = msg .. items[i].name .. ", "
end`,
      good: `-- GOOD: Single string allocation
local parts = {}
for i = 1, 100 do
    parts[i] = items[i].name
end
local msg = table.concat(parts, ", ")`,
    },
    severity: 'major',
    category: 'memory',
  },
  {
    id: 'MEM003',
    title: 'Closure Memory Leaks',
    description: 'Anonymous functions capturing large upvalues that persist',
    symptoms: [
      'Memory not released after UI is closed',
      'Gradual memory growth',
    ],
    cause: 'Closures keep references to all captured variables',
    fix: 'Nil out references when done, or avoid capturing large tables in closures',
    codeExample: {
      bad: `-- BAD: largeData kept alive by closure
local largeData = GetLargeDataSet()
button:SetHandler("OnClicked", function()
    DoSomethingWith(largeData)
end)`,
      good: `-- GOOD: Only capture what you need
local smallRef = GetSmallReference()
button:SetHandler("OnClicked", function()
    local data = FetchDataFrom(smallRef)
    DoSomethingWith(data)
end)`,
    },
    severity: 'major',
    category: 'memory',
  },

  // Event Bugs
  {
    id: 'EVT001',
    title: 'Unfiltered Combat Events',
    description: 'Processing every combat event without filtering causes severe lag in busy fights',
    symptoms: [
      'Major FPS drops in trials/dungeons',
      'UI becomes unresponsive during boss fights',
    ],
    cause: 'EVENT_COMBAT_EVENT fires thousands of times per second in group content',
    fix: 'Use RegisterForEvent with filterType parameter to filter server-side',
    codeExample: {
      bad: `-- BAD: Receives ALL combat events
EVENT_MANAGER:RegisterForEvent("MyAddon", EVENT_COMBAT_EVENT,
    function(_, result, isError, ...)
        if result == ACTION_RESULT_DAMAGE then  -- Client-side filter
            ProcessDamage(...)
        end
    end
)`,
      good: `-- GOOD: Server-side filter, only receives damage
EVENT_MANAGER:RegisterForEvent("MyAddon", EVENT_COMBAT_EVENT, ProcessDamage)
EVENT_MANAGER:AddFilterForEvent("MyAddon", EVENT_COMBAT_EVENT,
    REGISTER_FILTER_COMBAT_RESULT, ACTION_RESULT_DAMAGE
)`,
    },
    severity: 'critical',
    category: 'events',
  },
  {
    id: 'EVT002',
    title: 'Multiple Event Registrations',
    description: 'Registering the same event multiple times causes handler to fire multiple times',
    symptoms: [
      'Effects applied multiple times',
      'Actions happening 2x, 3x, etc.',
    ],
    cause: 'Re-registering events without unregistering first (common in UI refresh)',
    fix: 'Always unregister before registering, or use a registration guard',
    codeExample: {
      bad: `-- BAD: Called every time UI refreshes
function RefreshUI()
    EVENT_MANAGER:RegisterForEvent("MyAddon", EVENT_INVENTORY_SINGLE_SLOT_UPDATE, OnSlotUpdate)
end`,
      good: `-- GOOD: Registration guard
local registered = false
function RefreshUI()
    if not registered then
        EVENT_MANAGER:RegisterForEvent("MyAddon", EVENT_INVENTORY_SINGLE_SLOT_UPDATE, OnSlotUpdate)
        registered = true
    end
end`,
    },
    severity: 'major',
    category: 'events',
  },
  {
    id: 'EVT003',
    title: 'Event Handler During Load Screen',
    description: 'Events that fire during loading screens when addon is not ready',
    symptoms: [
      'Nil reference errors in logs',
      'Addon state corruption after zone change',
    ],
    cause: 'Some events fire before addon is fully initialized after load screen',
    fix: 'Guard handlers with initialization check, or use EVENT_PLAYER_ACTIVATED',
    codeExample: {
      bad: `-- BAD: May fire before addon is ready
EVENT_MANAGER:RegisterForEvent("MyAddon", EVENT_COMBAT_EVENT, function(...)
    MyAddon.currentFight.damage = MyAddon.currentFight.damage + damage  -- MyAddon may be nil
end)`,
      good: `-- GOOD: Initialization guard
EVENT_MANAGER:RegisterForEvent("MyAddon", EVENT_COMBAT_EVENT, function(...)
    if not MyAddon or not MyAddon.initialized then return end
    MyAddon.currentFight.damage = MyAddon.currentFight.damage + damage
end)`,
    },
    severity: 'major',
    category: 'events',
  },

  // API Bugs
  {
    id: 'API001',
    title: 'LibStub Usage After Deprecation',
    description: 'Using LibStub pattern instead of direct global variable access',
    symptoms: [
      'Addon works but shows deprecation warnings',
      'Breaks when library updates',
    ],
    cause: 'LibStub was deprecated with the library system overhaul',
    fix: 'Access libraries via their global variable directly',
    codeExample: {
      bad: `-- BAD: Deprecated LibStub pattern
local LAM = LibStub("LibAddonMenu-2.0")
local LGS = LibStub:GetLibrary("LibGuildStore")`,
      good: `-- GOOD: Direct global access
local LAM = LibAddonMenu2
local LGS = LibGuildStore`,
    },
    affectedVersions: 'API 100023+',
    severity: 'major',
    category: 'api',
  },
  {
    id: 'API002',
    title: 'Deprecated Function Usage',
    description: 'Using API functions that have been removed or renamed',
    symptoms: [
      'Function not found errors',
      'Addon fails to load',
    ],
    cause: 'ZOS periodically removes/renames API functions',
    fix: 'Use the migration database to find replacement functions',
    codeExample: {
      bad: `-- BAD: Removed in API 100015
local vr = GetUnitVeteranRank("player")`,
      good: `-- GOOD: Modern equivalent
local cp = GetUnitChampionPoints("player")`,
    },
    severity: 'critical',
    category: 'api',
  },
  {
    id: 'API003',
    title: 'Hardcoded API Version',
    description: 'Using a single APIVersion instead of supporting multiple',
    symptoms: [
      'Addon disabled after game update',
      'Users have to wait for addon update',
    ],
    cause: 'Only declaring one APIVersion in manifest',
    fix: 'Declare multiple APIVersions to support current and next patch',
    codeExample: {
      bad: `## APIVersion: 101047`,
      good: `## APIVersion: 101047 101048`,
    },
    severity: 'minor',
    category: 'api',
  },

  // UI Bugs
  {
    id: 'UI001',
    title: 'Font Path Using .ttf Extension',
    description: 'Using .ttf font extension instead of .slug in newer API versions',
    symptoms: [
      'Text not rendering',
      'Default font used instead of custom font',
    ],
    cause: 'ESO changed font loading to use .slug files',
    fix: 'Replace .ttf with .slug in font paths',
    codeExample: {
      bad: `control:SetFont("MyAddon/fonts/custom.ttf|18|soft-shadow-thin")`,
      good: `control:SetFont("MyAddon/fonts/custom.slug|18|soft-shadow-thin")`,
    },
    affectedVersions: 'API 101041+',
    severity: 'major',
    category: 'ui',
  },
  {
    id: 'UI002',
    title: 'Creating Controls Every Frame',
    description: 'Creating new UI controls in OnUpdate handlers',
    symptoms: [
      'Memory grows rapidly',
      'FPS drops over time',
    ],
    cause: 'Controls are not garbage collected; each creation persists',
    fix: 'Create controls once and reuse by showing/hiding',
    codeExample: {
      bad: `-- BAD: Creates new label every frame
function OnUpdate()
    local label = WINDOW_MANAGER:CreateControl("MyLabel", parent, CT_LABEL)
    label:SetText(GetCurrentValue())
end`,
      good: `-- GOOD: Create once, update as needed
local label = WINDOW_MANAGER:CreateControl("MyLabel", parent, CT_LABEL)
function OnUpdate()
    label:SetText(GetCurrentValue())
end`,
    },
    severity: 'critical',
    category: 'ui',
  },
  {
    id: 'UI003',
    title: 'SetHandler Overwriting',
    description: 'Using SetHandler instead of SetScript loses existing handlers',
    symptoms: [
      'Other addon\'s handlers stop working',
      'Base UI functionality breaks',
    ],
    cause: 'SetHandler replaces any existing handler',
    fix: 'Use ZO_PreHook or ZO_PostHook to chain handlers',
    codeExample: {
      bad: `-- BAD: Overwrites existing handler
control:SetHandler("OnMouseUp", function() MyFunction() end)`,
      good: `-- GOOD: Chains with existing handler
ZO_PreHook(control, "OnMouseUp", function()
    MyFunction()
    -- return true to prevent original handler, false/nil to continue
end)`,
    },
    severity: 'major',
    category: 'ui',
  },

  // SavedVariables Bugs
  {
    id: 'SV001',
    title: 'SavedVariables Not Persisting',
    description: 'Data saved to SavedVariables not persisting between sessions',
    symptoms: [
      'Settings reset on reload',
      'Data lost after logout',
    ],
    cause: 'Writing to SavedVariables during load screen or using wrong table reference',
    fix: 'Only modify SavedVariables after EVENT_PLAYER_ACTIVATED',
    codeExample: {
      bad: `-- BAD: Too early, SavedVariables not loaded yet
function OnAddonLoaded(_, addonName)
    if addonName == ADDON_NAME then
        MyAddon.settings = MyAddonSavedVars or {}
        MyAddon.settings.loaded = true  -- May not persist
    end
end`,
      good: `-- GOOD: Wait for player activated
function OnAddonLoaded(_, addonName)
    if addonName == ADDON_NAME then
        EVENT_MANAGER:RegisterForEvent(ADDON_NAME, EVENT_PLAYER_ACTIVATED, OnPlayerActivated)
    end
end
function OnPlayerActivated()
    EVENT_MANAGER:UnregisterForEvent(ADDON_NAME, EVENT_PLAYER_ACTIVATED)
    MyAddon.settings = MyAddonSavedVars or {}
    MyAddon.settings.loaded = true  -- Will persist
end`,
    },
    severity: 'critical',
    category: 'savedvars',
  },
  {
    id: 'SV002',
    title: 'Circular References in SavedVariables',
    description: 'Tables with circular references cannot be serialized',
    symptoms: [
      'SavedVariables file corrupted',
      'Game hangs on logout',
    ],
    cause: 'Storing references to objects that reference back',
    fix: 'Only store plain data (strings, numbers, simple tables)',
    codeExample: {
      bad: `-- BAD: Circular reference
local player = { name = "Test" }
player.self = player  -- Circular!
MyAddonSavedVars.player = player`,
      good: `-- GOOD: Only store needed data
MyAddonSavedVars.playerName = "Test"`,
    },
    severity: 'critical',
    category: 'savedvars',
  },

  // Threading/Async Bugs
  {
    id: 'THR001',
    title: 'Blocking Operations in Main Thread',
    description: 'Long-running operations blocking the game\'s main thread',
    symptoms: [
      'Game freezes during addon operation',
      'Input unresponsive',
    ],
    cause: 'Processing large datasets synchronously',
    fix: 'Use LibAsync or zo_callLater to spread work across frames',
    codeExample: {
      bad: `-- BAD: Blocks for entire loop
function ProcessAllItems()
    for i = 1, 10000 do
        ProcessItem(i)  -- Blocks until all done
    end
end`,
      good: `-- GOOD: Spread across frames with LibAsync
local async = LibAsync:Create("MyAddon")
function ProcessAllItems()
    async:For(1, 10000):Do(function(i)
        ProcessItem(i)
    end)
end`,
    },
    severity: 'major',
    category: 'threading',
  },
];

// ===========================================================================
// BEST PRACTICES
// ===========================================================================

export interface BestPractice {
  readonly id: string;
  readonly title: string;
  readonly description: string;
  readonly rationale: string;
  readonly codeExample?: string;
  readonly category: 'performance' | 'maintainability' | 'compatibility' | 'ux' | 'security';
}

export const BEST_PRACTICES: readonly BestPractice[] = [
  // Performance
  {
    id: 'PERF001',
    title: 'Use Local Variables',
    description: 'Declare frequently-accessed values as local variables',
    rationale: 'Local variable access is significantly faster than global lookups',
    codeExample: `-- At top of file
local GetGameTimeMilliseconds = GetGameTimeMilliseconds
local math_floor = math.floor

-- In function
local now = GetGameTimeMilliseconds()`,
    category: 'performance',
  },
  {
    id: 'PERF002',
    title: 'Cache Repeated Calculations',
    description: 'Store results of expensive calculations that don\'t change',
    rationale: 'Avoid recalculating values that remain constant',
    codeExample: `-- Calculate once
local playerClass = GetUnitClass("player")

-- Not every time needed
function GetPlayerClass()
    return playerClass
end`,
    category: 'performance',
  },
  {
    id: 'PERF003',
    title: 'Throttle High-Frequency Updates',
    description: 'Limit how often expensive operations run',
    rationale: 'OnUpdate fires every frame (60+ times/second)',
    codeExample: `local lastUpdate = 0
local UPDATE_INTERVAL = 100  -- ms

function OnUpdate()
    local now = GetGameTimeMilliseconds()
    if now - lastUpdate < UPDATE_INTERVAL then return end
    lastUpdate = now

    -- Expensive operation here
end`,
    category: 'performance',
  },
  {
    id: 'PERF004',
    title: 'Use Event Filters',
    description: 'Filter events server-side instead of client-side',
    rationale: 'Reduces the number of events your handler receives',
    codeExample: `-- Only receive combat events for player
EVENT_MANAGER:AddFilterForEvent("MyAddon", EVENT_COMBAT_EVENT,
    REGISTER_FILTER_SOURCE_COMBAT_UNIT_TYPE, COMBAT_UNIT_TYPE_PLAYER
)`,
    category: 'performance',
  },

  // Compatibility
  {
    id: 'COMPAT001',
    title: 'Support Multiple API Versions',
    description: 'List both current live and upcoming PTS API versions',
    rationale: 'Prevents addon from being disabled during patch week',
    codeExample: `## APIVersion: 101047 101048`,
    category: 'compatibility',
  },
  {
    id: 'COMPAT002',
    title: 'Check for Optional Dependencies',
    description: 'Gracefully handle missing optional libraries',
    rationale: 'Addon should work even if optional libraries aren\'t installed',
    codeExample: `local LAM = LibAddonMenu2
if LAM then
    -- Build settings panel
else
    -- Skip settings panel or use fallback
end`,
    category: 'compatibility',
  },
  {
    id: 'COMPAT003',
    title: 'Use Semantic Versioning',
    description: 'Follow semver for AddOnVersion: MAJOR.MINOR.PATCH as integer',
    rationale: 'Enables proper version comparison and update detection',
    codeExample: `## AddOnVersion: 10203  -- Represents 1.2.3
-- Encoding: major*10000 + minor*100 + patch`,
    category: 'compatibility',
  },

  // Maintainability
  {
    id: 'MAINT001',
    title: 'Namespace All Globals',
    description: 'Put all addon globals under a single namespace table',
    rationale: 'Prevents conflicts with other addons and makes debugging easier',
    codeExample: `-- Create single global namespace
MyAddon = {}
MyAddon.name = "MyAddon"
MyAddon.version = "1.0.0"
MyAddon.settings = {}

-- NOT this:
-- MY_ADDON_NAME = "MyAddon"
-- MY_ADDON_VERSION = "1.0.0"`,
    category: 'maintainability',
  },
  {
    id: 'MAINT002',
    title: 'Use Consistent Event Naming',
    description: 'Use addon name as event namespace prefix',
    rationale: 'Prevents event name collisions and aids debugging',
    codeExample: `-- Good: Namespaced event registration
EVENT_MANAGER:RegisterForEvent("MyAddon", EVENT_COMBAT_EVENT, handler)
EVENT_MANAGER:RegisterForUpdate("MyAddon_Update", 1000, updateHandler)`,
    category: 'maintainability',
  },
  {
    id: 'MAINT003',
    title: 'Separate Data from Logic',
    description: 'Keep configuration data in separate tables from functions',
    rationale: 'Makes it easier to modify behavior without changing code',
    codeExample: `-- Data table
local ABILITY_ICONS = {
    [12345] = "icon/path/here.dds",
    [12346] = "icon/path/other.dds",
}

-- Logic uses data
function GetAbilityIcon(abilityId)
    return ABILITY_ICONS[abilityId] or DEFAULT_ICON
end`,
    category: 'maintainability',
  },

  // UX
  {
    id: 'UX001',
    title: 'Provide Default Settings',
    description: 'Initialize SavedVariables with sensible defaults',
    rationale: 'New users get a working configuration out of the box',
    codeExample: `local defaults = {
    enabled = true,
    scale = 1.0,
    showInCombat = true,
}

function InitializeSettings()
    MyAddonSavedVars = MyAddonSavedVars or {}
    for key, value in pairs(defaults) do
        if MyAddonSavedVars[key] == nil then
            MyAddonSavedVars[key] = value
        end
    end
end`,
    category: 'ux',
  },
  {
    id: 'UX002',
    title: 'Use Slash Commands for Quick Access',
    description: 'Register /commands for common operations',
    rationale: 'Faster than navigating through settings menus',
    codeExample: `SLASH_COMMANDS["/myaddon"] = function(args)
    if args == "toggle" then
        MyAddon:Toggle()
    elseif args == "reset" then
        MyAddon:ResetSettings()
    else
        MyAddon:ShowHelp()
    end
end`,
    category: 'ux',
  },

  // Security
  {
    id: 'SEC001',
    title: 'Sanitize User Input',
    description: 'Validate and sanitize any user-provided strings',
    rationale: 'Prevents injection attacks in chat/UI',
    codeExample: `function ProcessUserInput(input)
    -- Remove control characters and limit length
    local sanitized = input:gsub("[%c]", ""):sub(1, 256)
    return sanitized
end`,
    category: 'security',
  },
];

// ===========================================================================
// PERFORMANCE OPTIMIZATION PATTERNS
// ===========================================================================

export interface OptimizationPattern {
  readonly id: string;
  readonly title: string;
  readonly impact: 'high' | 'medium' | 'low';
  readonly description: string;
  readonly before: string;
  readonly after: string;
  readonly explanation: string;
}

export const OPTIMIZATION_PATTERNS: readonly OptimizationPattern[] = [
  {
    id: 'OPT001',
    title: 'Table Pre-allocation',
    impact: 'medium',
    description: 'Pre-allocate table size when known',
    before: `local results = {}
for i = 1, 1000 do
    results[i] = ProcessItem(i)
end`,
    after: `local results = {}
for i = 1, 1000 do
    results[i] = ProcessItem(i)
end
-- Note: Lua 5.1 doesn't have table.create, but you can use
-- a C library or simply accept the reallocation cost`,
    explanation: 'Reduces memory reallocation as table grows',
  },
  {
    id: 'OPT002',
    title: 'Avoid pairs() in Hot Paths',
    impact: 'medium',
    description: 'Use numeric iteration when possible',
    before: `for key, value in pairs(items) do
    ProcessItem(value)
end`,
    after: `for i = 1, #items do
    ProcessItem(items[i])
end`,
    explanation: 'Numeric iteration is faster than pairs()',
  },
  {
    id: 'OPT003',
    title: 'Pool Frequently Created Objects',
    impact: 'high',
    description: 'Reuse objects instead of creating new ones',
    before: `function GetDamageEvent()
    return {
        damage = 0,
        source = "",
        target = "",
    }
end`,
    after: `local eventPool = {}
local poolSize = 0

function GetDamageEvent()
    if poolSize > 0 then
        local event = eventPool[poolSize]
        eventPool[poolSize] = nil
        poolSize = poolSize - 1
        event.damage = 0
        event.source = ""
        event.target = ""
        return event
    end
    return { damage = 0, source = "", target = "" }
end

function ReleaseDamageEvent(event)
    poolSize = poolSize + 1
    eventPool[poolSize] = event
end`,
    explanation: 'Reduces garbage collection pressure',
  },
  {
    id: 'OPT004',
    title: 'Batch UI Updates',
    impact: 'high',
    description: 'Update UI once per frame, not per event',
    before: `function OnCombatEvent(damage)
    totalDamage = totalDamage + damage
    dpsLabel:SetText(FormatDPS(totalDamage / duration))  -- Every event!
end`,
    after: `local dirty = false
function OnCombatEvent(damage)
    totalDamage = totalDamage + damage
    dirty = true
end

function OnUpdate()
    if dirty then
        dpsLabel:SetText(FormatDPS(totalDamage / duration))
        dirty = false
    end
end`,
    explanation: 'UI updates are expensive; batch them',
  },
];

// ===========================================================================
// API DEPRECATION TIMELINE
// ===========================================================================

export interface ApiChange {
  readonly apiVersion: number;
  readonly update: string;
  readonly date: string;
  readonly changes: Array<{
    readonly type: 'removed' | 'deprecated' | 'renamed' | 'changed';
    readonly item: string;
    readonly replacement?: string;
    readonly notes?: string;
  }>;
}

export const API_DEPRECATION_TIMELINE: readonly ApiChange[] = [
  {
    apiVersion: 100015,
    update: 'Update 10 (Orsinium)',
    date: '2015-11-02',
    changes: [
      { type: 'removed', item: 'GetUnitVeteranRank()', replacement: 'GetUnitChampionPoints()', notes: 'Champion system replaced veteran ranks' },
      { type: 'removed', item: 'GetUnitVeteranPoints()', replacement: 'GetPlayerChampionPointsEarned()' },
    ],
  },
  {
    apiVersion: 100023,
    update: 'Update 17 (Summerset)',
    date: '2018-05-21',
    changes: [
      { type: 'deprecated', item: 'LibStub', replacement: 'Direct global access', notes: 'Libraries now have global variables' },
      { type: 'changed', item: 'WINDOW_MANAGER:CreateTopLevelWindow()', notes: 'Different signature' },
    ],
  },
  {
    apiVersion: 101033,
    update: 'Update 33 (Ascending Tide)',
    date: '2022-03-14',
    changes: [
      { type: 'changed', item: 'Achievement tracking', notes: 'Per-character tracking removed' },
    ],
  },
  {
    apiVersion: 101041,
    update: 'Update 41 (Scions of Ithelia)',
    date: '2024-03-11',
    changes: [
      { type: 'changed', item: 'Font paths', replacement: '.slug extension', notes: '.ttf no longer works' },
    ],
  },
  {
    apiVersion: 101046,
    update: 'Update 46 (Gold Road)',
    date: '2024-06-03',
    changes: [
      { type: 'changed', item: 'Console addon support', notes: 'PS5/Xbox addons now supported' },
      { type: 'changed', item: 'Manifest format', notes: '.addon extension required for console' },
    ],
  },
];

// ===========================================================================
// HELPER FUNCTIONS
// ===========================================================================

/**
 * Get all bugs by category.
 */
export function getBugsByCategory(category: CommonBug['category']): CommonBug[] {
  return COMMON_BUGS.filter(bug => bug.category === category);
}

/**
 * Get all bugs by severity.
 */
export function getBugsBySeverity(severity: CommonBug['severity']): CommonBug[] {
  return COMMON_BUGS.filter(bug => bug.severity === severity);
}

/**
 * Get all best practices by category.
 */
export function getPracticesByCategory(category: BestPractice['category']): BestPractice[] {
  return BEST_PRACTICES.filter(practice => practice.category === category);
}

/**
 * Get API changes for a specific version range.
 */
export function getApiChangesInRange(minVersion: number, maxVersion: number): ApiChange[] {
  return API_DEPRECATION_TIMELINE.filter(
    change => change.apiVersion >= minVersion && change.apiVersion <= maxVersion
  );
}

/**
 * Find bugs that might affect given code patterns.
 */
export function findPotentialBugs(codePatterns: string[]): CommonBug[] {
  const found: CommonBug[] = [];

  for (const bug of COMMON_BUGS) {
    if (bug.codeExample?.bad) {
      for (const pattern of codePatterns) {
        if (bug.codeExample.bad.toLowerCase().includes(pattern.toLowerCase())) {
          found.push(bug);
          break;
        }
      }
    }
  }

  return found;
}

/**
 * Get documentation summary statistics.
 */
export function getDocStats() {
  return {
    totalBugs: COMMON_BUGS.length,
    criticalBugs: COMMON_BUGS.filter(b => b.severity === 'critical').length,
    totalPractices: BEST_PRACTICES.length,
    totalOptimizations: OPTIMIZATION_PATTERNS.length,
    apiChanges: API_DEPRECATION_TIMELINE.reduce((sum, c) => sum + c.changes.length, 0),
  };
}
