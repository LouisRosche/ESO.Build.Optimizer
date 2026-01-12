# ESO Addon API Reference

> **Last Updated**: January 2026
> **API Version**: 101047 (ESO 11.0.0 "Seasons of the Worm Cult Part 1")
> **Source**: [ESOUI Wiki](https://wiki.esoui.com/Main_Page), [UESP ESO Data](https://esoapi.uesp.net/)

---

## Table of Contents

1. [Overview](#overview)
2. [Key Documentation Sources](#key-documentation-sources)
3. [Manifest File Requirements](#manifest-file-requirements)
4. [Initialization Pattern](#initialization-pattern)
5. [Namespace and Variable Conventions](#namespace-and-variable-conventions)
6. [Event System](#event-system)
7. [Event Filtering (CRITICAL)](#event-filtering-critical)
8. [SavedVariables](#savedvariables)
9. [Performance Best Practices](#performance-best-practices)
10. [Protected Functions](#protected-functions)
11. [Combat Events](#combat-events)
12. [Unit Information Functions](#unit-information-functions)
13. [Equipment/Build Functions](#equipmentbuild-functions)
14. [UI Creation](#ui-creation)
15. [API Update Protocol](#api-update-protocol)

---

## Overview

ESO uses **Lua 5.1** (Havok Script variant). Addons cannot make network requests - all sync must happen via SavedVariables files read by external applications.

**Key Constraints:**
- No HTTP/socket access from Lua
- No filesystem access outside SavedVariables
- Data only persists on zone change, `/reloadui`, or logout (NOT during loading screens)
- Cannot modify game files
- Some functions are protected during combat

---

## Key Documentation Sources

| Resource | URL | Description |
|----------|-----|-------------|
| ESOUI Wiki | https://wiki.esoui.com/Main_Page | Community-maintained API docs |
| ESOUI API | https://wiki.esoui.com/API | Function reference by category |
| APIVersion History | https://wiki.esoui.com/APIVersion | API version changelog |
| ESOUI GitHub | https://github.com/esoui/esoui | Official UI source code |
| UESP ESO Data | https://esoapi.uesp.net/ | Extracted game data |
| ZOS API Updates | https://www.esoui.com/forums/forumdisplay.php?f=166 | Official patch notes |
| Addon Best Practices | https://wiki.esoui.com/Best_Practices | Official coding guidelines |

---

## Manifest File Requirements

The addon manifest (`.txt` file) has strict formatting requirements. Errors here cause silent failures.

### File Encoding

```
Encoding: UTF-8 WITHOUT BOM (Byte Order Mark)
Line Endings: CRLF (Windows-style: \r\n)
Line Length: Maximum 301 bytes per line (HARD LIMIT)
```

> **WARNING**: UTF-8 with BOM will cause the addon to fail silently. Many text editors add BOM by default.

### Required Directives

```ini
## Title: ESOBuildOptimizer
## APIVersion: 101047
## AddOnVersion: 100
## Author: Your Name
## SavedVariables: ESOBuildOptimizerSV
```

### Directive Reference

| Directive | Format | Description |
|-----------|--------|-------------|
| `Title` | String | Display name in addon manager |
| `APIVersion` | Integer (101047) | Current ESO API version. **MUST** match game version |
| `AddOnVersion` | Integer only | Your addon's version number (e.g., `100` for v1.0.0) |
| `Author` | String | Author name(s) |
| `SavedVariables` | Identifier | Global variable name(s) for account-wide data |
| `SavedVariablesCharacter` | Identifier | Global variable name(s) for character-specific data |
| `Description` | String | Shown in addon manager |
| `DependsOn` | name>=version | Required dependencies with minimum versions |
| `OptionalDependsOn` | name | Optional dependencies (load order hint) |
| `IsLibrary` | 1 | Mark as library (not shown in addon list) |

### Dependency Format

```ini
## DependsOn: LibAddonMenu-2.0>=30 LibAsync>=20
## OptionalDependsOn: LibDebugLogger
```

- Version numbers after `>=` are **integers** (not semantic versions)
- Multiple dependencies separated by spaces
- Missing required dependencies = addon won't load

### Complete Manifest Example

```ini
## Title: ESOBuildOptimizer
## Description: Combat analytics and build optimization for ESO
## Author: @YourAccountName
## APIVersion: 101047
## AddOnVersion: 100
## Version: 1.0.0
## SavedVariables: ESOBuildOptimizerSV
## DependsOn: LibAddonMenu-2.0>=30
## OptionalDependsOn: LibAsync LibDebugLogger

; File list (order matters for dependencies)
libs/LibStub/LibStub.lua
libs/LibAddonMenu-2.0/LibAddonMenu-2.0.lua
ESOBuildOptimizer.lua
Modules/Combat.lua
Modules/UI.lua
```

### File List Rules

- Relative paths from addon root
- Forward slashes only (`/` not `\`)
- One file per line
- Comments with `;` or blank lines allowed
- Files load in listed order (dependencies first!)
- XML files can also be listed

---

## Initialization Pattern

**CRITICAL**: Always use `EVENT_ADD_ON_LOADED` to initialize your addon.

### Correct Pattern

```lua
local ADDON_NAME = "ESOBuildOptimizer"

-- Single global namespace
ESOBuildOptimizer = {}
local addon = ESOBuildOptimizer

-- Local initialization function
local function OnAddonLoaded(eventCode, addonName)
    -- CRITICAL: Check if this is YOUR addon
    if addonName ~= ADDON_NAME then return end

    -- Unregister immediately (only fires once per addon)
    EVENT_MANAGER:UnregisterForEvent(ADDON_NAME, EVENT_ADD_ON_LOADED)

    -- Now safe to initialize
    addon:Initialize()
end

function addon:Initialize()
    -- Load saved variables
    self.savedVars = ZO_SavedVars:NewCharacterIdSettings(
        "ESOBuildOptimizerSV",
        1,  -- Database version
        nil,
        self.defaults
    )

    -- Register events
    self:RegisterEvents()

    -- Create UI
    self:CreateUI()
end

-- Register for addon loaded event
EVENT_MANAGER:RegisterForEvent(ADDON_NAME, EVENT_ADD_ON_LOADED, OnAddonLoaded)
```

### Why This Pattern Matters

1. **Check addon name**: `EVENT_ADD_ON_LOADED` fires for EVERY addon. Without the check, your init runs multiple times.
2. **Unregister after**: Prevents memory leaks and duplicate initialization.
3. **Single entry point**: All initialization flows through one function.

### Initialization Order Events

```lua
-- Order of relevant events during login:
-- 1. EVENT_ADD_ON_LOADED (for each addon, in load order)
-- 2. EVENT_PLAYER_ACTIVATED (player fully loaded, can use most APIs)
-- 3. EVENT_PLAYER_COMBAT_STATE (combat state available)

-- Some APIs require EVENT_PLAYER_ACTIVATED:
EVENT_MANAGER:RegisterForEvent(ADDON_NAME, EVENT_PLAYER_ACTIVATED, function()
    -- Safe to query character data here
    local characterName = GetUnitName("player")
    local level = GetUnitLevel("player")
end)
```

---

## Namespace and Variable Conventions

### Single Global Table

```lua
-- CORRECT: One global, everything else local
ESOBuildOptimizer = {}
local addon = ESOBuildOptimizer

local combatData = {}
local currentRun = nil

function addon:StartCombat()
    -- ...
end

-- WRONG: Multiple globals polluting namespace
ESOBuildOptimizer_Data = {}      -- BAD
ESOBuildOptimizer_Combat = {}    -- BAD
currentRun = nil                  -- BAD (global variable)
```

### Variable Scoping

```lua
-- Local everything that doesn't need to be global
local ADDON_NAME = "ESOBuildOptimizer"
local defaults = { enabled = true }

-- Cache frequently used globals for performance
local GetGameTimeMilliseconds = GetGameTimeMilliseconds
local zo_strformat = zo_strformat
local pairs = pairs
local ipairs = ipairs

-- Module-level locals
local eventNamespace = ADDON_NAME .. "_Combat"
```

### String ID Conventions

All localized strings must use a consistent prefix:

```lua
-- String IDs in lang/en.lua or inline
ZO_CreateStringId("SI_ESOBUILDOPTIMIZER_TITLE", "ESO Build Optimizer")
ZO_CreateStringId("SI_ESOBUILDOPTIMIZER_DPS_LABEL", "DPS")
ZO_CreateStringId("SI_ESOBUILDOPTIMIZER_SETTINGS_HEADER", "Settings")

-- Usage
local title = GetString(SI_ESOBUILDOPTIMIZER_TITLE)

-- Format with placeholders
ZO_CreateStringId("SI_ESOBUILDOPTIMIZER_DAMAGE_FORMAT", "<<1>> dealt <<2>> damage")
local text = zo_strformat(SI_ESOBUILDOPTIMIZER_DAMAGE_FORMAT, playerName, damageAmount)
```

### Keybind Naming

```lua
-- Keybind IDs also need prefix
ZO_CreateStringId("SI_BINDING_NAME_ESOBUILDOPTIMIZER_TOGGLE", "Toggle Build Optimizer")
ZO_CreateStringId("SI_BINDING_NAME_ESOBUILDOPTIMIZER_RESET", "Reset Combat Data")
```

---

## Event System

### Registration Basics

```lua
local ADDON_NAME = "ESOBuildOptimizer"

-- Register for an event
EVENT_MANAGER:RegisterForEvent(ADDON_NAME, EVENT_COMBAT_EVENT, OnCombatEvent)

-- Unregister when no longer needed
EVENT_MANAGER:UnregisterForEvent(ADDON_NAME, EVENT_COMBAT_EVENT)

-- Check if registered
local isRegistered = EVENT_MANAGER:IsEventRegistered(ADDON_NAME, EVENT_COMBAT_EVENT)
```

### Unique Namespaces Per Filtered Event

**CRITICAL**: Each filtered event registration MUST have a unique namespace.

```lua
-- WRONG: Same namespace, filters overwrite each other
EVENT_MANAGER:RegisterForEvent(ADDON_NAME, EVENT_COMBAT_EVENT, OnPlayerDamage)
EVENT_MANAGER:AddFilterForEvent(ADDON_NAME, EVENT_COMBAT_EVENT,
    REGISTER_FILTER_SOURCE_COMBAT_UNIT_TYPE, COMBAT_UNIT_TYPE_PLAYER)

EVENT_MANAGER:RegisterForEvent(ADDON_NAME, EVENT_COMBAT_EVENT, OnBossDamage)
EVENT_MANAGER:AddFilterForEvent(ADDON_NAME, EVENT_COMBAT_EVENT,  -- OVERWRITES!
    REGISTER_FILTER_TARGET_COMBAT_UNIT_TYPE, COMBAT_UNIT_TYPE_BOSS)

-- CORRECT: Unique namespace per filtered registration
local NS_PLAYER_COMBAT = ADDON_NAME .. "_PlayerCombat"
local NS_BOSS_COMBAT = ADDON_NAME .. "_BossCombat"

EVENT_MANAGER:RegisterForEvent(NS_PLAYER_COMBAT, EVENT_COMBAT_EVENT, OnPlayerDamage)
EVENT_MANAGER:AddFilterForEvent(NS_PLAYER_COMBAT, EVENT_COMBAT_EVENT,
    REGISTER_FILTER_SOURCE_COMBAT_UNIT_TYPE, COMBAT_UNIT_TYPE_PLAYER)

EVENT_MANAGER:RegisterForEvent(NS_BOSS_COMBAT, EVENT_COMBAT_EVENT, OnBossDamage)
EVENT_MANAGER:AddFilterForEvent(NS_BOSS_COMBAT, EVENT_COMBAT_EVENT,
    REGISTER_FILTER_TARGET_COMBAT_UNIT_TYPE, COMBAT_UNIT_TYPE_BOSS)
```

---

## Event Filtering (CRITICAL)

> **PERFORMANCE CRITICAL**: High-frequency events MUST be filtered. Unfiltered combat events can fire thousands of times per second and cause severe FPS drops.

### High-Frequency Events Requiring Filters

| Event | Frequency | Filter Required |
|-------|-----------|-----------------|
| `EVENT_COMBAT_EVENT` | 1000s/sec in combat | YES |
| `EVENT_EFFECT_CHANGED` | 100s/sec | YES |
| `EVENT_INVENTORY_SINGLE_SLOT_UPDATE` | High during looting | YES |
| `EVENT_POWER_UPDATE` | Continuous | YES |
| `EVENT_RETICLE_TARGET_CHANGED` | High | Recommended |

### Filter Types

```lua
-- Unit tag filters
REGISTER_FILTER_UNIT_TAG            -- "player", "boss1", etc.
REGISTER_FILTER_UNIT_TAG_PREFIX     -- "group" matches group1-group24

-- Combat unit type filters
REGISTER_FILTER_SOURCE_COMBAT_UNIT_TYPE
REGISTER_FILTER_TARGET_COMBAT_UNIT_TYPE
-- Values: COMBAT_UNIT_TYPE_PLAYER, COMBAT_UNIT_TYPE_GROUP,
--         COMBAT_UNIT_TYPE_TARGET_DUMMY, COMBAT_UNIT_TYPE_BOSS,
--         COMBAT_UNIT_TYPE_OTHER, COMBAT_UNIT_TYPE_NONE

-- Ability filters
REGISTER_FILTER_ABILITY_ID          -- Specific ability ID
REGISTER_FILTER_COMBAT_RESULT       -- ACTION_RESULT_*

-- Power type filters
REGISTER_FILTER_POWER_TYPE          -- POWERTYPE_HEALTH, POWERTYPE_MAGICKA, etc.

-- Inventory filters
REGISTER_FILTER_BAG_ID              -- BAG_BACKPACK, BAG_WORN, etc.
REGISTER_FILTER_INVENTORY_UPDATE_REASON

-- Boolean filters
REGISTER_FILTER_IS_ERROR
REGISTER_FILTER_IS_IN_GAMEPAD_PREFERRED_MODE
```

### Combat Event Filtering Examples

```lua
local ADDON_NAME = "ESOBuildOptimizer"

-- Filter 1: Player as damage source (your damage dealt)
local NS_PLAYER_DAMAGE = ADDON_NAME .. "_PlayerDamage"
EVENT_MANAGER:RegisterForEvent(NS_PLAYER_DAMAGE, EVENT_COMBAT_EVENT, OnPlayerDamage)
EVENT_MANAGER:AddFilterForEvent(NS_PLAYER_DAMAGE, EVENT_COMBAT_EVENT,
    REGISTER_FILTER_SOURCE_COMBAT_UNIT_TYPE, COMBAT_UNIT_TYPE_PLAYER)
EVENT_MANAGER:AddFilterForEvent(NS_PLAYER_DAMAGE, EVENT_COMBAT_EVENT,
    REGISTER_FILTER_IS_ERROR, false)

-- Filter 2: Player as target (damage taken)
local NS_DAMAGE_TAKEN = ADDON_NAME .. "_DamageTaken"
EVENT_MANAGER:RegisterForEvent(NS_DAMAGE_TAKEN, EVENT_COMBAT_EVENT, OnDamageTaken)
EVENT_MANAGER:AddFilterForEvent(NS_DAMAGE_TAKEN, EVENT_COMBAT_EVENT,
    REGISTER_FILTER_TARGET_COMBAT_UNIT_TYPE, COMBAT_UNIT_TYPE_PLAYER)
EVENT_MANAGER:AddFilterForEvent(NS_DAMAGE_TAKEN, EVENT_COMBAT_EVENT,
    REGISTER_FILTER_IS_ERROR, false)

-- Filter 3: Specific combat results only (e.g., interrupts)
local NS_INTERRUPTS = ADDON_NAME .. "_Interrupts"
EVENT_MANAGER:RegisterForEvent(NS_INTERRUPTS, EVENT_COMBAT_EVENT, OnInterrupt)
EVENT_MANAGER:AddFilterForEvent(NS_INTERRUPTS, EVENT_COMBAT_EVENT,
    REGISTER_FILTER_COMBAT_RESULT, ACTION_RESULT_INTERRUPT)

-- Filter 4: Boss damage only
local NS_BOSS_DAMAGE = ADDON_NAME .. "_BossDamage"
EVENT_MANAGER:RegisterForEvent(NS_BOSS_DAMAGE, EVENT_COMBAT_EVENT, OnBossDamage)
EVENT_MANAGER:AddFilterForEvent(NS_BOSS_DAMAGE, EVENT_COMBAT_EVENT,
    REGISTER_FILTER_TARGET_COMBAT_UNIT_TYPE, COMBAT_UNIT_TYPE_BOSS)
```

### Effect Changed Filtering

```lua
-- Filter to player effects only
local NS_PLAYER_EFFECTS = ADDON_NAME .. "_PlayerEffects"
EVENT_MANAGER:RegisterForEvent(NS_PLAYER_EFFECTS, EVENT_EFFECT_CHANGED, OnPlayerEffect)
EVENT_MANAGER:AddFilterForEvent(NS_PLAYER_EFFECTS, EVENT_EFFECT_CHANGED,
    REGISTER_FILTER_UNIT_TAG, "player")

-- Filter to specific buff by ability ID
local NS_MAJOR_BRUTALITY = ADDON_NAME .. "_MajorBrutality"
EVENT_MANAGER:RegisterForEvent(NS_MAJOR_BRUTALITY, EVENT_EFFECT_CHANGED, OnMajorBrutality)
EVENT_MANAGER:AddFilterForEvent(NS_MAJOR_BRUTALITY, EVENT_EFFECT_CHANGED,
    REGISTER_FILTER_ABILITY_ID, 61665) -- Major Brutality ability ID
```

### Inventory Filtering

```lua
-- Only worn equipment changes
local NS_EQUIPMENT = ADDON_NAME .. "_Equipment"
EVENT_MANAGER:RegisterForEvent(NS_EQUIPMENT, EVENT_INVENTORY_SINGLE_SLOT_UPDATE, OnEquipmentChanged)
EVENT_MANAGER:AddFilterForEvent(NS_EQUIPMENT, EVENT_INVENTORY_SINGLE_SLOT_UPDATE,
    REGISTER_FILTER_BAG_ID, BAG_WORN)

-- Only backpack changes
local NS_BACKPACK = ADDON_NAME .. "_Backpack"
EVENT_MANAGER:RegisterForEvent(NS_BACKPACK, EVENT_INVENTORY_SINGLE_SLOT_UPDATE, OnBackpackChanged)
EVENT_MANAGER:AddFilterForEvent(NS_BACKPACK, EVENT_INVENTORY_SINGLE_SLOT_UPDATE,
    REGISTER_FILTER_BAG_ID, BAG_BACKPACK)
```

### Multiple Filters on Same Registration

You can chain multiple filters - they act as AND conditions:

```lua
local NS_PLAYER_CRIT = ADDON_NAME .. "_PlayerCrit"
EVENT_MANAGER:RegisterForEvent(NS_PLAYER_CRIT, EVENT_COMBAT_EVENT, OnPlayerCrit)
-- Filter: Player source AND critical damage result
EVENT_MANAGER:AddFilterForEvent(NS_PLAYER_CRIT, EVENT_COMBAT_EVENT,
    REGISTER_FILTER_SOURCE_COMBAT_UNIT_TYPE, COMBAT_UNIT_TYPE_PLAYER)
EVENT_MANAGER:AddFilterForEvent(NS_PLAYER_CRIT, EVENT_COMBAT_EVENT,
    REGISTER_FILTER_COMBAT_RESULT, ACTION_RESULT_CRITICAL_DAMAGE)
```

---

## SavedVariables

### ZO_SavedVars (Recommended)

Use `ZO_SavedVars` for proper versioning and defaults handling.

```lua
-- Account-wide settings
self.accountVars = ZO_SavedVars:NewAccountWide(
    "ESOBuildOptimizerSV",  -- SavedVariables name from manifest
    1,                       -- Database version (increment to reset)
    nil,                     -- Namespace (nil = default)
    defaults                 -- Default values table
)

-- Character-specific settings (PREFERRED for character data)
self.charVars = ZO_SavedVars:NewCharacterIdSettings(
    "ESOBuildOptimizerSV",
    1,
    nil,
    characterDefaults
)
```

### NewCharacterIdSettings vs New

```lua
-- CORRECT: Uses character ID (survives renames)
ZO_SavedVars:NewCharacterIdSettings(savedVarName, version, namespace, defaults)

-- AVOID: Uses character name (breaks on rename)
ZO_SavedVars:New(savedVarName, version, namespace, defaults)
```

### Data Persistence Timing

**Data is written to disk ONLY on:**
- Zone change (including entering/exiting houses)
- `/reloadui` command
- Logout/quit
- Character select

**Data is NOT saved:**
- During loading screens
- On crash
- Periodically (no auto-save!)

**Implication**: For critical data, consider periodic `/reloadui` hints or accept potential loss.

### String Length Limit

```lua
-- SavedVariables have a ~2000 character limit per string value
-- For large data, split across multiple keys:

-- WRONG: Single huge string
self.savedVars.combatLog = hugeJsonString  -- May truncate!

-- CORRECT: Chunked storage
local function chunkString(str, size)
    local chunks = {}
    for i = 1, #str, size do
        table.insert(chunks, str:sub(i, i + size - 1))
    end
    return chunks
end

self.savedVars.combatLogChunks = chunkString(hugeJsonString, 1900)
```

### Defaults Pattern

```lua
local defaults = {
    enabled = true,
    showUI = true,
    position = { x = 100, y = 100 },
    settings = {
        trackDamage = true,
        trackHealing = true,
        trackBuffs = true,
    },
    -- Version for migration
    dataVersion = 1,
}

function addon:Initialize()
    self.savedVars = ZO_SavedVars:NewCharacterIdSettings(
        "ESOBuildOptimizerSV",
        1,
        nil,
        defaults
    )

    -- Migration logic
    if self.savedVars.dataVersion < 2 then
        self:MigrateToV2()
        self.savedVars.dataVersion = 2
    end
end
```

### SavedVariables File Location

```
Windows: %USERPROFILE%\Documents\Elder Scrolls Online\live\SavedVariables\
Mac: ~/Documents/Elder Scrolls Online/live/SavedVariables/
```

---

## Performance Best Practices

### NEVER Use OnUpdate Handlers

```lua
-- WRONG: OnUpdate fires every frame (60+ times/second)
control:SetHandler("OnUpdate", function()
    self:UpdateDisplay()  -- Causes massive FPS drop
end)

-- CORRECT: Use EVENT_MANAGER:RegisterForUpdate with interval
EVENT_MANAGER:RegisterForUpdate(ADDON_NAME .. "_Update", 1000, function()
    self:UpdateDisplay()  -- Fires once per second
end)

-- Unregister when done
EVENT_MANAGER:UnregisterForUpdate(ADDON_NAME .. "_Update")
```

### Use LibAsync for Heavy Operations

```lua
-- For operations that would block the main thread
local async = LibAsync:Create(ADDON_NAME)

function addon:ProcessLargeDataSet(data)
    async:For(1, #data, function(i)
        self:ProcessItem(data[i])
    end):Then(function()
        self:OnProcessingComplete()
    end)
end

-- With yielding for very heavy work
async:Call(function()
    for i = 1, 10000 do
        -- Heavy computation
        ProcessItem(i)

        -- Yield every 100 items to prevent frame drops
        if i % 100 == 0 then
            async:Yield()
        end
    end
end)
```

### Cache Globals

```lua
-- CORRECT: Cache at module level
local GetGameTimeMilliseconds = GetGameTimeMilliseconds
local GetUnitPower = GetUnitPower
local zo_strformat = zo_strformat
local pairs = pairs
local ipairs = ipairs
local math_floor = math.floor
local table_insert = table.insert

function addon:OnCombatEvent(...)
    local now = GetGameTimeMilliseconds()  -- Uses cached local
    -- ...
end
```

### Minimize Table Creation in Hot Paths

```lua
-- WRONG: Creates new table every call
function addon:GetPlayerStats()
    return {
        health = GetUnitPower("player", POWERTYPE_HEALTH),
        magicka = GetUnitPower("player", POWERTYPE_MAGICKA),
        stamina = GetUnitPower("player", POWERTYPE_STAMINA),
    }
end

-- CORRECT: Reuse table
local playerStats = { health = 0, magicka = 0, stamina = 0 }

function addon:GetPlayerStats()
    playerStats.health = GetUnitPower("player", POWERTYPE_HEALTH)
    playerStats.magicka = GetUnitPower("player", POWERTYPE_MAGICKA)
    playerStats.stamina = GetUnitPower("player", POWERTYPE_STAMINA)
    return playerStats
end
```

### String Concatenation

```lua
-- WRONG: Creates intermediate strings
local result = "Player: " .. name .. " dealt " .. damage .. " damage"

-- CORRECT: Use zo_strformat
local result = zo_strformat("Player: <<1>> dealt <<2>> damage", name, damage)

-- CORRECT: Use table.concat for many strings
local parts = {}
for i, entry in ipairs(log) do
    table_insert(parts, entry.text)
end
local result = table.concat(parts, "\n")
```

### Batch UI Updates

```lua
-- WRONG: Update UI in every event
function addon:OnCombatEvent(...)
    self.damageTotal = self.damageTotal + damage
    self:UpdateDamageLabel()  -- Called 1000s of times
end

-- CORRECT: Flag for update, process in interval
function addon:OnCombatEvent(...)
    self.damageTotal = self.damageTotal + damage
    self.needsUpdate = true
end

-- Separate update loop (once per second)
EVENT_MANAGER:RegisterForUpdate(ADDON_NAME .. "_UIUpdate", 1000, function()
    if addon.needsUpdate then
        addon:UpdateDamageLabel()
        addon.needsUpdate = false
    end
end)
```

---

## Protected Functions

Some functions cannot be called during combat. These are typically related to keybinds and action slots.

### Protected (Cannot Execute in Combat)

```lua
-- Action bar manipulation
ClearSlot(slotIndex, hotbarCategory)           -- PROTECTED
SelectSlotSkillAbility(skillType, lineIndex, abilityIndex, slotIndex) -- PROTECTED
SlotSkillAbilityInSlot(...)                    -- PROTECTED

-- Keybind manipulation
BindKeyToAction(...)                           -- PROTECTED
UnbindKeyFromAction(...)                       -- PROTECTED

-- Add-on settings that affect gameplay
-- Various set functions for secure settings
```

### NOT Protected (Safe During Combat)

Contrary to some documentation, these UI functions are safe:

```lua
-- UI anchor/position functions - SAFE during combat
control:ClearAnchors()
control:SetAnchor(point, relativeTo, relativePoint, offsetX, offsetY)
control:SetDimensions(width, height)
control:SetHidden(hidden)
control:SetAlpha(alpha)

-- Label functions - SAFE
label:SetText(text)
label:SetColor(r, g, b, a)
label:SetFont(font)

-- Most UI manipulation - SAFE
WINDOW_MANAGER:CreateControl(...)
WINDOW_MANAGER:CreateTopLevelWindow(...)
```

### Checking Combat State

```lua
function addon:TryProtectedAction()
    if IsUnitInCombat("player") then
        -- Queue for after combat
        self.pendingAction = true
        return false
    end

    -- Safe to execute
    self:ExecuteProtectedAction()
    return true
end

-- Execute pending after combat ends
EVENT_MANAGER:RegisterForEvent(ADDON_NAME, EVENT_PLAYER_COMBAT_STATE, function(_, inCombat)
    if not inCombat and addon.pendingAction then
        addon:ExecuteProtectedAction()
        addon.pendingAction = false
    end
end)
```

---

## Combat Events

### Primary Combat Event

```lua
EVENT_COMBAT_EVENT = 131103
-- Callback signature:
function OnCombatEvent(eventCode, result, isError, abilityName, abilityGraphic,
    abilityActionSlotType, sourceName, sourceType, targetName, targetType,
    hitValue, powerType, damageType, log, sourceUnitId, targetUnitId,
    abilityId, overflow)
```

### Key Action Results

```lua
-- Damage
ACTION_RESULT_DAMAGE = 1
ACTION_RESULT_CRITICAL_DAMAGE = 2
ACTION_RESULT_DOT_TICK = 3
ACTION_RESULT_DOT_TICK_CRITICAL = 4

-- Healing
ACTION_RESULT_HEAL = 16
ACTION_RESULT_CRITICAL_HEAL = 17
ACTION_RESULT_HOT_TICK = 18
ACTION_RESULT_HOT_TICK_CRITICAL = 19

-- Mitigation
ACTION_RESULT_BLOCKED = 34
ACTION_RESULT_BLOCKED_DAMAGE = 35
ACTION_RESULT_DAMAGE_SHIELDED = 116
ACTION_RESULT_DODGED = 38
ACTION_RESULT_MISS = 37
ACTION_RESULT_PARRIED = 39
ACTION_RESULT_RESIST = 40
ACTION_RESULT_IMMUNE = 41

-- CC/Utility
ACTION_RESULT_INTERRUPT = 81
ACTION_RESULT_STUNNED = 26
ACTION_RESULT_KNOCKBACK = 24
ACTION_RESULT_STAGGERED = 27

-- Death
ACTION_RESULT_DIED = 80
ACTION_RESULT_KILLING_BLOW = 86
```

### Combat Unit Types

```lua
COMBAT_UNIT_TYPE_NONE = 0
COMBAT_UNIT_TYPE_PLAYER = 1
COMBAT_UNIT_TYPE_PLAYER_PET = 2
COMBAT_UNIT_TYPE_GROUP = 3
COMBAT_UNIT_TYPE_TARGET_DUMMY = 4
COMBAT_UNIT_TYPE_OTHER = 5
COMBAT_UNIT_TYPE_BOSS = 6
```

### Effect/Buff Tracking

```lua
EVENT_EFFECT_CHANGED = 131084
-- Callback signature:
function OnEffectChanged(eventCode, changeType, effectSlot, effectName,
    unitTag, beginTime, endTime, stackCount, iconName, buffType,
    effectType, abilityType, statusEffectType, unitName, unitId,
    abilityId, sourceType)

-- Change types:
EFFECT_RESULT_GAINED = 3
EFFECT_RESULT_FADED = 4
EFFECT_RESULT_UPDATED = 5

-- Buff types:
BUFF_EFFECT_TYPE_BUFF = 1
BUFF_EFFECT_TYPE_DEBUFF = 2
```

### Calculating Buff Uptime

```lua
local buffTracking = {}

function addon:OnEffectChanged(eventCode, changeType, effectSlot, effectName,
    unitTag, beginTime, endTime, stackCount, iconName, buffType,
    effectType, abilityType, statusEffectType, unitName, unitId, abilityId)

    if unitTag ~= "player" then return end

    local now = GetGameTimeMilliseconds() / 1000

    if changeType == EFFECT_RESULT_GAINED then
        buffTracking[abilityId] = {
            startTime = now,
            totalUptime = buffTracking[abilityId] and buffTracking[abilityId].totalUptime or 0
        }
    elseif changeType == EFFECT_RESULT_FADED then
        local tracking = buffTracking[abilityId]
        if tracking and tracking.startTime then
            tracking.totalUptime = tracking.totalUptime + (now - tracking.startTime)
            tracking.startTime = nil
        end
    end
end

function addon:GetBuffUptime(abilityId, combatDuration)
    local tracking = buffTracking[abilityId]
    if not tracking then return 0 end

    local uptime = tracking.totalUptime
    if tracking.startTime then
        uptime = uptime + (GetGameTimeMilliseconds() / 1000 - tracking.startTime)
    end

    return uptime / combatDuration
end
```

---

## Unit Information Functions

```lua
-- Player info
GetUnitName("player")
GetUnitLevel("player")
GetUnitEffectiveChampionPoints("player")
GetUnitClass("player")
GetUnitRace("player")

-- Power (returns current, max, effectiveMax)
local current, max, effectiveMax = GetUnitPower("player", POWERTYPE_HEALTH)
GetUnitPower("player", POWERTYPE_MAGICKA)
GetUnitPower("player", POWERTYPE_STAMINA)
GetUnitPower("player", POWERTYPE_ULTIMATE)

-- Boss detection
MAX_BOSSES = 12
DoesUnitExist("boss1")
IsUnitDead("boss1")
GetUnitName("boss1")
GetUnitDifficulty("boss1")  -- Returns difficulty level

-- Group
GetGroupSize()
GetGroupUnitTagByIndex(index)  -- 1-24
IsUnitGroupLeader("player")
GetUnitZone("group1")

-- Combat state
IsUnitInCombat("player")
IsUnitDead("player")
GetUnitAttributeVisualizerEffectInfo(unitTag, visualizerType)
```

---

## Equipment/Build Functions

```lua
-- Equipped items
GetItemLink(BAG_WORN, slotIndex, LINK_STYLE_DEFAULT)
GetItemInfo(BAG_WORN, slotIndex)
GetItemName(BAG_WORN, slotIndex)
GetItemTrait(BAG_WORN, slotIndex)
GetItemQuality(BAG_WORN, slotIndex)

-- Equipment slot indices (BAG_WORN):
EQUIP_SLOT_HEAD = 0
EQUIP_SLOT_NECK = 1
EQUIP_SLOT_CHEST = 2
EQUIP_SLOT_SHOULDERS = 3
EQUIP_SLOT_MAIN_HAND = 4
EQUIP_SLOT_OFF_HAND = 5
EQUIP_SLOT_WAIST = 6
EQUIP_SLOT_LEGS = 8
EQUIP_SLOT_FEET = 9
EQUIP_SLOT_RING1 = 11
EQUIP_SLOT_RING2 = 12
EQUIP_SLOT_HAND = 16
EQUIP_SLOT_BACKUP_MAIN = 20
EQUIP_SLOT_BACKUP_OFF = 21

-- Active abilities
GetSlotBoundId(slotIndex, hotbarCategory)
GetSlotName(slotIndex, hotbarCategory)
GetSlotTexture(slotIndex, hotbarCategory)
GetSlotCooldownInfo(slotIndex, hotbarCategory)
-- HOTBAR_CATEGORY_PRIMARY = 0
-- HOTBAR_CATEGORY_BACKUP = 1
-- HOTBAR_CATEGORY_OVERLOAD = 2 (Sorcerer)
-- Slot indices: 3-7 (abilities), 8 (ultimate)

-- Set bonuses
GetItemLinkSetInfo(itemLink)  -- Returns setId, setName, numBonuses, numEquipped, maxEquipped
GetItemSetInfo(setId)
```

### Build Snapshot Example

```lua
function addon:GetBuildSnapshot()
    local snapshot = {
        class = GetUnitClass("player"),
        race = GetUnitRace("player"),
        level = GetUnitLevel("player"),
        cp = GetUnitEffectiveChampionPoints("player"),
        gear = {},
        skillsFront = {},
        skillsBack = {},
    }

    -- Capture gear
    for slot = 0, 21 do
        local link = GetItemLink(BAG_WORN, slot)
        if link and link ~= "" then
            local setId, setName = GetItemLinkSetInfo(link)
            snapshot.gear[slot] = {
                name = GetItemName(BAG_WORN, slot),
                link = link,
                setId = setId,
                setName = setName,
            }
        end
    end

    -- Capture skills (front bar)
    for slot = 3, 8 do
        local abilityId = GetSlotBoundId(slot, HOTBAR_CATEGORY_PRIMARY)
        if abilityId > 0 then
            snapshot.skillsFront[slot] = {
                id = abilityId,
                name = GetSlotName(slot, HOTBAR_CATEGORY_PRIMARY),
            }
        end
    end

    -- Capture skills (back bar)
    for slot = 3, 8 do
        local abilityId = GetSlotBoundId(slot, HOTBAR_CATEGORY_BACKUP)
        if abilityId > 0 then
            snapshot.skillsBack[slot] = {
                id = abilityId,
                name = GetSlotName(slot, HOTBAR_CATEGORY_BACKUP),
            }
        end
    end

    return snapshot
end
```

---

## UI Creation

### Window Manager Basics

```lua
-- Create top-level window
local window = WINDOW_MANAGER:CreateTopLevelWindow("ESOBuildOptimizer_MainWindow")
window:SetDimensions(400, 300)
window:SetAnchor(CENTER, GuiRoot, CENTER, 0, 0)
window:SetMovable(true)
window:SetMouseEnabled(true)
window:SetClampedToScreen(true)
window:SetHidden(false)

-- Add backdrop
local bg = WINDOW_MANAGER:CreateControl("$(parent)BG", window, CT_BACKDROP)
bg:SetAnchorFill(window)
bg:SetCenterColor(0, 0, 0, 0.8)
bg:SetEdgeColor(0.3, 0.3, 0.3, 1)
bg:SetEdgeTexture("", 1, 1, 1)

-- Create label
local label = WINDOW_MANAGER:CreateControl("$(parent)Title", window, CT_LABEL)
label:SetFont("ZoFontWinH1")
label:SetText("Build Optimizer")
label:SetAnchor(TOP, window, TOP, 0, 10)
label:SetColor(1, 1, 1, 1)
```

### Control Types

```lua
CT_LABEL = 1
CT_TEXTURE = 2
CT_BACKDROP = 3
CT_BUTTON = 4
CT_STATUSBAR = 5
CT_EDITBOX = 6
CT_TOPLEVELCONTROL = 7
CT_SCROLL = 8
CT_SLIDER = 9
CT_COOLDOWN = 10
```

### Scene Integration

```lua
-- Create fragment for proper scene management
local fragment = ZO_HUDFadeSceneFragment:New(window)

-- Add to HUD scene (shows during gameplay)
HUD_SCENE:AddFragment(fragment)
HUD_UI_SCENE:AddFragment(fragment)

-- Or create custom scene
local scene = ZO_Scene:New("ESOBuildOptimizerScene", SCENE_MANAGER)
scene:AddFragment(fragment)
scene:AddFragment(FRAME_EMOTE_FRAGMENT_INVENTORY)  -- Shows with inventory

-- Show/hide via scene
SCENE_MANAGER:Show("ESOBuildOptimizerScene")
SCENE_MANAGER:Hide("ESOBuildOptimizerScene")
```

### Drag Handling

```lua
window:SetHandler("OnMoveStart", function()
    -- Optional: Do something when drag starts
end)

window:SetHandler("OnMoveStop", function()
    -- Save position
    addon.savedVars.position = {
        x = window:GetLeft(),
        y = window:GetTop()
    }
end)
```

---

## API Update Protocol

When ESO patches:

1. **Check API Version**
   - Visit https://wiki.esoui.com/APIVersion
   - Compare current vs new `APIVersion`

2. **Review Patch Notes**
   - Check ESOUI forum "Tutorials & Other Helpful Info"
   - Look for deprecated/removed functions
   - Note new events or filters

3. **Update Manifest**
   ```ini
   ## APIVersion: 101048  -- Update this
   ```

4. **Test Core Functionality**
   - Combat event tracking
   - SavedVariables read/write
   - UI rendering
   - All registered events

5. **Check for Breaking Changes**
   - Renamed constants
   - Changed function signatures
   - Removed/deprecated APIs

### APIVersion History (Recent)

| Version | ESO Version | Notes |
|---------|-------------|-------|
| 101047 | 11.0.0 | Seasons of the Worm Cult P1 |
| 101046 | 10.3.0 | Gold Road Update |
| 101045 | 10.2.0 | Update 45 |
| 101044 | 10.1.0 | Update 44 |
| 101043 | 10.0.0 | Gold Road Chapter |

---

## Common Patterns

### Slash Command Registration

```lua
SLASH_COMMANDS["/ebo"] = function(args)
    if args == "toggle" then
        addon:ToggleUI()
    elseif args == "reset" then
        addon:ResetData()
    elseif args == "debug" then
        addon.debug = not addon.debug
        d("Debug mode: " .. tostring(addon.debug))
    else
        d("ESOBuildOptimizer commands: /ebo toggle | reset | debug")
    end
end
```

### LibAddonMenu-2.0 Settings

```lua
local LAM = LibAddonMenu2

local panelData = {
    type = "panel",
    name = "ESO Build Optimizer",
    author = "@YourName",
    version = "1.0.0",
    registerForRefresh = true,
}

local optionsData = {
    {
        type = "header",
        name = "General Settings",
    },
    {
        type = "checkbox",
        name = "Enable Tracking",
        tooltip = "Enable combat tracking",
        getFunc = function() return addon.savedVars.enabled end,
        setFunc = function(value) addon.savedVars.enabled = value end,
        default = true,
    },
    {
        type = "slider",
        name = "Update Interval",
        tooltip = "How often to update the display (ms)",
        min = 100,
        max = 2000,
        step = 100,
        getFunc = function() return addon.savedVars.updateInterval end,
        setFunc = function(value)
            addon.savedVars.updateInterval = value
            addon:RestartUpdateLoop()
        end,
        default = 1000,
    },
}

LAM:RegisterAddonPanel("ESOBuildOptimizerPanel", panelData)
LAM:RegisterOptionControls("ESOBuildOptimizerPanel", optionsData)
```

### Debug Output

```lua
-- Simple debug
local function Debug(...)
    if addon.debug then
        d("[EBO]", ...)
    end
end

-- Formatted debug with timestamp
local function DebugF(formatString, ...)
    if addon.debug then
        local timestamp = GetTimeString()
        d(string.format("[EBO %s] " .. formatString, timestamp, ...))
    end
end

-- Table dump (development only)
local function DumpTable(t, indent)
    indent = indent or 0
    for k, v in pairs(t) do
        if type(v) == "table" then
            d(string.rep("  ", indent) .. tostring(k) .. ":")
            DumpTable(v, indent + 1)
        else
            d(string.rep("  ", indent) .. tostring(k) .. " = " .. tostring(v))
        end
    end
end
```

---

## Quick Reference: Event Constants

```lua
-- Lifecycle
EVENT_ADD_ON_LOADED = 65536
EVENT_PLAYER_ACTIVATED = 131125
EVENT_PLAYER_DEACTIVATED = 131126

-- Combat
EVENT_COMBAT_EVENT = 131103
EVENT_PLAYER_COMBAT_STATE = 131102
EVENT_BOSSES_CHANGED = 131149

-- Effects
EVENT_EFFECT_CHANGED = 131084
EVENT_EFFECTS_FULL_UPDATE = 131085

-- Equipment
EVENT_INVENTORY_SINGLE_SLOT_UPDATE = 131150
EVENT_ACTIVE_WEAPON_PAIR_CHANGED = 131180

-- Power
EVENT_POWER_UPDATE = 131096

-- Zone
EVENT_ZONE_CHANGED = 131208
EVENT_PLAYER_ALIVE = 131126

-- Group
EVENT_GROUP_MEMBER_JOINED = 131198
EVENT_GROUP_MEMBER_LEFT = 131199
EVENT_GROUP_UPDATE = 131200
```

---

*This document should be refreshed after each ESO quarterly update.*
*Last verified: January 2026 (Update 47/48)*
