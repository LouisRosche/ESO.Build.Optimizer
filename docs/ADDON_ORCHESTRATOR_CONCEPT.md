# Addon Orchestrator Concept

> **Vision**: A modern addon manager that goes beyond simple enable/disable to provide intelligent profile management, dependency awareness, and performance optimization.

---

## Current State: Addon Selector

The existing Addon Selector provides basic functionality:
- Enable/disable addons
- Create addon profiles
- Switch profiles on logout

**Limitations:**
- No visual feedback during gameplay
- No dependency awareness (can break addons)
- No performance impact visibility
- Requires logout to switch profiles
- No search/filter for large addon lists
- No categorization or grouping

---

## Proposed: Addon Orchestrator

### 1. Core Features

#### 1.1 Smart Profile Management

```
┌─────────────────────────────────────────────────────────────┐
│  ADDON ORCHESTRATOR                              [_][□][X]  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │  ⚔️ COMBAT      │  │  🏠 CASUAL      │  [+ New Profile]  │
│  │  Active         │  │                 │                   │
│  │  42 addons      │  │  28 addons      │                   │
│  └─────────────────┘  └─────────────────┘                   │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │  🛒 TRADING     │  │  📸 SCREENSHOT  │                   │
│  │                 │  │                 │                   │
│  │  35 addons      │  │  12 addons      │                   │
│  └─────────────────┘  └─────────────────┘                   │
├─────────────────────────────────────────────────────────────┤
│  [Apply on Logout]  [Apply Now (ReloadUI)]  [Quick Toggle]  │
└─────────────────────────────────────────────────────────────┘
```

**Profile Types:**
| Profile | Purpose | Typical Addons |
|---------|---------|----------------|
| Combat | Trials/Dungeons | Combat Metrics, Raid Notifier, Code's Combat Alerts |
| Casual | Questing/Exploration | Destinations, Skyshards, Lore Books |
| Trading | Guild trading | Master Merchant, Tamriel Trade Centre, Arkadius' Trade Tools |
| Screenshot | Clean UI | Minimal - hide all HUD elements |
| PvP | Cyrodiil/BGs | Battleground Healers, Cyrodiil Alert |

#### 1.2 Visual Profile Indicator

Small, unobtrusive indicator showing current profile:

```
┌────────────────┐
│ ⚔️ COMBAT      │  ← Top-left corner, fades after 5s
└────────────────┘
```

Configurable:
- Position (corner selection)
- Auto-hide delay
- Show on zone change
- Show on combat start/end

#### 1.3 Dependency Awareness

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️ DEPENDENCY WARNING                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Disabling "LibAddonMenu-2.0" will break:                   │
│                                                             │
│    • Combat Metrics (settings panel)                        │
│    • Bandit's UI (settings panel)                           │
│    • Inventory Insight (settings panel)                     │
│    + 23 more addons                                         │
│                                                             │
│  [Disable Anyway]  [Keep Enabled]  [Show All Dependents]    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Dependency Graph Features:**
- Visual dependency tree
- Required vs Optional dependencies
- Circular dependency detection
- Missing dependency alerts

#### 1.4 Performance Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  PERFORMANCE IMPACT                          [Refresh]      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Load Time Impact (estimated):                              │
│  ████████████████████░░░░░░░░░░  68%  (~45s total)          │
│                                                             │
│  Top Impact Addons:                                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Master Merchant      ████████████████  32s  (71%)       ││
│  │ Awesome Guild Store  ████████          16s  (36%)       ││
│  │ Tamriel Trade Centre ███               6s   (13%)       ││
│  │ WritWorthy           ██                4s   (9%)        ││
│  │ Other (38 addons)    █                 2s   (4%)        ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  Memory Usage: 1.2 GB (High - consider disabling some)      │
│                                                             │
│  [Optimize Profile]  [View Details]                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Metrics Tracked:**
- Addon load time (measured during login)
- Memory footprint
- Event callback frequency
- CPU time in combat

#### 1.5 Search and Filter

```
┌─────────────────────────────────────────────────────────────┐
│  🔍 [Search addons...                              ]  ⚙️    │
├─────────────────────────────────────────────────────────────┤
│  Filter: [All▼] [Enabled▼] [Category▼] [Author▼]            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ▼ COMBAT (12)                                              │
│    ☑ Combat Metrics          @Solinur       v2.5.1          │
│    ☑ Code's Combat Alerts    @code65536     v1.8.0          │
│    ☑ Raid Notifier           @Kyoma         v3.1.2          │
│    ☐ Untaunted               @Wheels        v1.2.0          │
│                                                             │
│  ▼ LIBRARIES (8)                                            │
│    ☑ LibAddonMenu-2.0        @sirinsidiator v2.0.35         │
│    ☑ LibAsync                @sirinsidiator v2.3.0          │
│    ☑ LibFilters-3.0          @Baertram      v3.5.2          │
│                                                             │
│  ▶ TRADING (6)                                              │
│  ▶ UI ENHANCEMENT (15)                                      │
│  ▶ MAPS & EXPLORATION (9)                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Categories (Auto-detected from ESOUI):**
- Combat
- Trading
- Crafting
- UI Enhancement
- Maps & Exploration
- Libraries
- Character
- Housing
- PvP
- Miscellaneous

#### 1.6 Quick Toggle Overlay

In-game overlay for rapid profile switching (hotkey activated):

```
         ┌───────────────────┐
         │  QUICK SWITCH     │
         ├───────────────────┤
         │ [1] ⚔️ Combat     │  ← Current
         │ [2] 🏠 Casual     │
         │ [3] 🛒 Trading    │
         │ [4] 📸 Screenshot │
         ├───────────────────┤
         │ [R] ReloadUI      │
         │ [ESC] Cancel      │
         └───────────────────┘
```

---

### 2. Advanced Features

#### 2.1 Per-Addon Overrides

Override specific addons without changing entire profile:

```lua
-- Temporary override: Enable Master Merchant in Combat profile
/orchestrator override "Master Merchant" enable

-- Clear override
/orchestrator override "Master Merchant" clear

-- List overrides
/orchestrator overrides
```

#### 2.2 Context-Aware Auto-Switching

Optional automatic profile switching based on context:

| Trigger | Action |
|---------|--------|
| Enter trial/dungeon | Switch to Combat profile |
| Enter Cyrodiil/BG | Switch to PvP profile |
| Open guild store | Enable trading addons |
| Enter housing | Switch to Housing profile |

```lua
-- Enable auto-switching
/orchestrator auto on

-- Configure triggers
/orchestrator auto trigger "trial" "Combat"
/orchestrator auto trigger "cyrodiil" "PvP"
```

#### 2.3 Profile Sharing

Export/import profiles for sharing with guildmates:

```
┌─────────────────────────────────────────────────────────────┐
│  SHARE PROFILE                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Profile: Combat                                            │
│  Addons: 42                                                 │
│                                                             │
│  Export Options:                                            │
│  ☑ Include addon versions                                   │
│  ☑ Include addon sources (ESOUI links)                      │
│  ☐ Include personal settings                                │
│                                                             │
│  Export Code:                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ AORCH:v1:Q29tYmF0fDQyfENvbWJhdE1ldHJpY3N8Q29kZ...      ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  [Copy to Clipboard]  [Share via Website]                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.4 Update Awareness

```
┌─────────────────────────────────────────────────────────────┐
│  🔄 ADDON UPDATES AVAILABLE                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  3 addons have updates:                                     │
│                                                             │
│  Combat Metrics     v2.5.0 → v2.5.1  [View Changelog]       │
│  LibAddonMenu-2.0   v2.0.34 → v2.0.35  [View Changelog]     │
│  Bandit's UI        v4.2.0 → v4.2.1  [View Changelog]       │
│                                                             │
│  [Open Minion]  [Dismiss]                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 3. Slash Commands

```
/orchestrator help              - Show all commands
/orchestrator profile <name>    - Switch to profile
/orchestrator profiles          - List all profiles
/orchestrator create <name>     - Create new profile
/orchestrator delete <name>     - Delete profile
/orchestrator copy <src> <dst>  - Copy profile
/orchestrator override <addon> <on|off|clear>  - Override addon
/orchestrator auto <on|off>     - Toggle auto-switching
/orchestrator performance       - Show performance dashboard
/orchestrator dependencies      - Show dependency graph
/orchestrator export <profile>  - Export profile code
/orchestrator import <code>     - Import profile from code
```

---

### 4. Technical Implementation

#### 4.1 Data Storage

```lua
-- SavedVariables structure
AddonOrchestratorSV = {
    profiles = {
        ["Combat"] = {
            icon = "⚔️",
            addons = { "CombatMetrics", "RaidNotifier", ... },
            overrides = {},
            autoTriggers = { "trial", "dungeon" },
        },
        ["Casual"] = { ... },
    },
    activeProfile = "Combat",
    settings = {
        showIndicator = true,
        indicatorPosition = "topleft",
        autoSwitch = false,
        quickToggleKey = "F12",
    },
    performance = {
        loadTimes = {},  -- Cached load time measurements
        lastMeasured = 0,
    },
}
```

#### 4.2 Addon Detection

```lua
-- Get all installed addons
local function GetInstalledAddons()
    local addons = {}
    for i = 1, GetNumAddOns() do
        local name, title, author, description, enabled, state, isOutOfDate, isLibrary = GetAddOnInfo(i)
        table.insert(addons, {
            name = name,
            title = title,
            author = author,
            enabled = enabled,
            isLibrary = isLibrary,
            dependencies = { GetAddOnDependencyInfo(i) },
        })
    end
    return addons
end
```

#### 4.3 Profile Application

```lua
-- Apply profile (requires ReloadUI or logout)
local function ApplyProfile(profileName)
    local profile = savedVars.profiles[profileName]
    if not profile then return false end

    -- Build addon enable/disable map
    local enableMap = {}
    for _, addonName in ipairs(profile.addons) do
        enableMap[addonName] = true
    end

    -- Apply to all addons
    for i = 1, GetNumAddOns() do
        local name = GetAddOnInfo(i)
        local shouldEnable = enableMap[name] or false

        -- Check for overrides
        if profile.overrides[name] ~= nil then
            shouldEnable = profile.overrides[name]
        end

        -- Libraries always enabled if any dependent is enabled
        if IsLibraryRequiredByEnabledAddon(name) then
            shouldEnable = true
        end

        SetAddOnEnabled(i, shouldEnable)
    end

    savedVars.activeProfile = profileName
    return true
end
```

#### 4.4 Performance Measurement

```lua
-- Hook into addon load events to measure load times
local loadStartTimes = {}

local function OnAddOnLoadStarted(addonName)
    loadStartTimes[addonName] = GetGameTimeMilliseconds()
end

local function OnAddOnLoadFinished(addonName)
    local startTime = loadStartTimes[addonName]
    if startTime then
        local loadTime = GetGameTimeMilliseconds() - startTime
        savedVars.performance.loadTimes[addonName] = loadTime
    end
end
```

---

### 5. Integration with ESO Build Optimizer

The Addon Orchestrator can integrate with our main addon:

```lua
-- Suggest profile based on content
EVENT_MANAGER:RegisterForEvent("AddonOrchestrator", EVENT_ZONE_UPDATE, function()
    local zoneId = GetZoneId(GetCurrentMapZoneIndex())

    if IsTrialZone(zoneId) or IsDungeonZone(zoneId) then
        -- Suggest Combat profile if not active
        if savedVars.activeProfile ~= "Combat" then
            ShowProfileSuggestion("Combat", "You're entering group content!")
        end
    end
end)
```

---

### 6. UI/UX Guidelines

Following our ESO_UI_BEST_PRACTICES.md:

- **Colors**: DarkUI compatible palette
- **Fonts**: Standard ESO fonts (ZoFontGameMedium, ZoFontGameBold)
- **Position**: Movable, lockable, resettable
- **Accessibility**: Full slash command support for console
- **Performance**: Event-driven, no OnUpdate polling

---

### 7. Development Phases

| Phase | Features | Status |
|-------|----------|--------|
| 1 | Basic profile management, enable/disable | Planned |
| 2 | Dependency awareness, warnings | Planned |
| 3 | Performance dashboard | Planned |
| 4 | Auto-switching, context awareness | Future |
| 5 | Profile sharing, cloud sync | Future |

---

### 8. Comparison: Addon Selector vs Addon Orchestrator

| Feature | Addon Selector | Addon Orchestrator |
|---------|---------------|-------------------|
| Enable/disable addons | ✅ | ✅ |
| Profile management | ✅ | ✅ |
| Visual profile indicator | ❌ | ✅ |
| Dependency awareness | ❌ | ✅ |
| Performance metrics | ❌ | ✅ |
| Search/filter | ❌ | ✅ |
| Category grouping | ❌ | ✅ |
| Quick toggle overlay | ❌ | ✅ |
| Per-addon overrides | ❌ | ✅ |
| Auto-switching | ❌ | ✅ |
| Profile sharing | ❌ | ✅ |
| Update notifications | ❌ | ✅ |
| Console accessibility | Limited | Full |

---

*Concept document - February 2026*
