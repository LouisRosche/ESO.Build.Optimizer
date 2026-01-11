--[[
    ESO Build Optimizer
    Main Addon File

    Combat metrics tracking with ML-powered recommendations.
    This addon collects combat data and build information for analysis
    by the companion app and cloud ML pipeline.

    Author: ESO Build Optimizer Team
    Version: 0.1.0
]]--

---------------------------------------------------------------------------
-- Addon Namespace
---------------------------------------------------------------------------

ESOBuildOptimizer = ESOBuildOptimizer or {}
local addon = ESOBuildOptimizer

addon.name = "ESOBuildOptimizer"
addon.displayName = "ESO Build Optimizer"
addon.version = "0.1.0"
addon.author = "ESO Build Optimizer Team"

-- Module references (populated when modules load)
addon.CombatTracker = nil
addon.BuildSnapshot = nil
addon.MetricsUI = nil
addon.SkillAdvisor = nil

---------------------------------------------------------------------------
-- Default SavedVariables Structure
---------------------------------------------------------------------------

local defaultSavedVars = {
    -- Settings
    settings = {
        enabled = true,
        showUI = true,
        trackOutOfCombat = false,
        verboseLogging = false,
        uiScale = 1.0,
        uiLocked = false,
        uiPosition = { x = 100, y = 100 },

        -- UI View Settings
        expandedView = false,           -- Default collapsed (minimal view)
        autoDisplayMetrics = true,      -- Opt-in default for auto-display during combat

        -- Skill Advisor Settings
        showSkillAdvisor = true,        -- Opt-in default for skill suggestions
        skillHighlightEnabled = true,   -- Glow effect on recommended abilities
    },

    -- Combat run history (synced to companion app)
    runs = {},

    -- Current character build snapshot
    currentBuild = nil,

    -- Pending sync data for companion app
    pendingSync = {
        runs = {},
        builds = {},
        lastSyncTimestamp = 0,
    },

    -- Statistics
    stats = {
        totalRunsRecorded = 0,
        totalDamageDealt = 0,
        totalHealingDone = 0,
        totalDeaths = 0,
    },
}

---------------------------------------------------------------------------
-- Local State
---------------------------------------------------------------------------

local isInitialized = false
local isPlayerActivated = false

---------------------------------------------------------------------------
-- Utility Functions
---------------------------------------------------------------------------

-- Debug logging
function addon:Debug(message, ...)
    if self.savedVars and self.savedVars.settings.verboseLogging then
        d(string.format("[%s] %s", self.name, string.format(message, ...)))
    end
end

-- Info logging (always shown)
function addon:Info(message, ...)
    d(string.format("[%s] %s", self.displayName, string.format(message, ...)))
end

-- Error logging
function addon:Error(message, ...)
    d(string.format("[%s] ERROR: %s", self.name, string.format(message, ...)))
end

-- Get current timestamp in ISO8601 format
function addon:GetTimestamp()
    local ts = GetTimeStamp()
    return GetDateStringFromTimestamp(ts) .. "T" .. GetTimeString()
end

-- Generate a simple unique ID
function addon:GenerateRunId()
    return string.format("%s_%d_%d",
        GetDisplayName():gsub("@", ""),
        GetTimeStamp(),
        math.random(1000, 9999)
    )
end

---------------------------------------------------------------------------
-- SavedVariables Management
---------------------------------------------------------------------------

local function InitializeSavedVariables()
    -- Initialize SavedVariables with defaults
    ESOBuildOptimizerSV = ESOBuildOptimizerSV or {}

    -- Merge defaults with saved data
    for key, defaultValue in pairs(defaultSavedVars) do
        if ESOBuildOptimizerSV[key] == nil then
            if type(defaultValue) == "table" then
                ESOBuildOptimizerSV[key] = {}
                for k, v in pairs(defaultValue) do
                    ESOBuildOptimizerSV[key][k] = v
                end
            else
                ESOBuildOptimizerSV[key] = defaultValue
            end
        end
    end

    addon.savedVars = ESOBuildOptimizerSV
    addon:Debug("SavedVariables initialized")
end

---------------------------------------------------------------------------
-- Event Handlers
---------------------------------------------------------------------------

-- Called when addon is loaded
local function OnAddonLoaded(eventCode, addonName)
    if addonName ~= addon.name then return end

    -- Unregister this event
    EVENT_MANAGER:UnregisterForEvent(addon.name, EVENT_ADD_ON_LOADED)

    -- Initialize SavedVariables
    InitializeSavedVariables()

    -- Mark as initialized
    isInitialized = true
    addon:Debug("Addon loaded")
end

-- Called when player fully enters the world
local function OnPlayerActivated(eventCode, initial)
    if not isInitialized then return end
    if isPlayerActivated then return end

    isPlayerActivated = true

    -- Initialize modules
    if addon.CombatTracker then
        addon.CombatTracker:Initialize()
    end

    if addon.BuildSnapshot then
        addon.BuildSnapshot:Initialize()
        -- Capture initial build state
        addon.BuildSnapshot:CaptureFullSnapshot()
    end

    if addon.MetricsUI then
        addon.MetricsUI:Initialize()
    end

    if addon.SkillAdvisor then
        addon.SkillAdvisor:Initialize()
    end

    addon:Info("Ready - v%s", addon.version)
end

-- Combat event handler (delegates to CombatTracker)
local function OnCombatEvent(eventCode, result, isError, abilityName, abilityGraphic,
    abilityActionSlotType, sourceName, sourceType, targetName, targetType,
    hitValue, powerType, damageType, log, sourceUnitId, targetUnitId, abilityId, overflow)

    if addon.CombatTracker then
        addon.CombatTracker:OnCombatEvent(
            eventCode, result, isError, abilityName, abilityGraphic,
            abilityActionSlotType, sourceName, sourceType, targetName, targetType,
            hitValue, powerType, damageType, log, sourceUnitId, targetUnitId, abilityId, overflow
        )
    end
end

-- Unit death state handler
local function OnUnitDeathStateChanged(eventCode, unitTag, isDead)
    if addon.CombatTracker then
        addon.CombatTracker:OnUnitDeathStateChanged(unitTag, isDead)
    end
end

-- Inventory slot update (gear changes)
local function OnInventorySlotUpdate(eventCode, bagId, slotIndex, isNewItem,
    itemSoundCategory, inventoryUpdateReason, stackCountChange)

    if addon.BuildSnapshot and isPlayerActivated then
        -- Only track equipment changes
        if bagId == BAG_WORN then
            addon.BuildSnapshot:OnEquipmentChanged(slotIndex)
        end
    end
end

-- Skill rank update
local function OnSkillRankUpdate(eventCode, skillType, skillLineIndex, skillIndex,
    rank, advised, progressionIndex, skillAbilityId)

    if addon.BuildSnapshot and isPlayerActivated then
        addon.BuildSnapshot:OnSkillChanged()
    end
end

-- Action slot update (skill bar changes)
local function OnActionSlotUpdated(eventCode, actionSlotIndex)
    if addon.BuildSnapshot and isPlayerActivated then
        addon.BuildSnapshot:OnActionBarChanged(actionSlotIndex)
    end

    -- Notify SkillAdvisor of action bar changes
    if addon.SkillAdvisor and isPlayerActivated then
        addon.SkillAdvisor:OnActionBarChanged(actionSlotIndex)
    end
end

-- Boss encounter detection via combat state
local function OnPlayerCombatState(eventCode, inCombat)
    if addon.CombatTracker then
        addon.CombatTracker:OnCombatStateChanged(inCombat)
    end

    -- Notify SkillAdvisor of combat state
    if addon.SkillAdvisor then
        addon.SkillAdvisor:OnCombatStateChanged(inCombat)
    end

    -- Notify MetricsUI for auto-display
    if addon.MetricsUI then
        addon.MetricsUI:OnCombatStateChanged(inCombat)
    end
end

-- Bosses health tracking for encounter detection
local function OnBossesChanged()
    if addon.CombatTracker then
        addon.CombatTracker:OnBossesChanged()
    end
end

-- Effect changed (for buff/debuff tracking)
local function OnEffectChanged(eventCode, changeType, effectSlot, effectName,
    unitTag, beginTime, endTime, stackCount, iconName, buffType, effectType,
    abilityType, statusEffectType, unitName, unitId, abilityId, sourceType)

    if addon.CombatTracker then
        addon.CombatTracker:OnEffectChanged(
            changeType, effectSlot, effectName, unitTag, beginTime, endTime,
            stackCount, iconName, buffType, effectType, abilityType,
            statusEffectType, unitName, unitId, abilityId, sourceType
        )
    end
end

---------------------------------------------------------------------------
-- Event Registration
---------------------------------------------------------------------------

local function RegisterEvents()
    local em = EVENT_MANAGER
    local name = addon.name

    -- Core addon events
    em:RegisterForEvent(name, EVENT_ADD_ON_LOADED, OnAddonLoaded)
    em:RegisterForEvent(name, EVENT_PLAYER_ACTIVATED, OnPlayerActivated)

    -- Combat events
    em:RegisterForEvent(name, EVENT_COMBAT_EVENT, OnCombatEvent)
    em:RegisterForEvent(name, EVENT_UNIT_DEATH_STATE_CHANGED, OnUnitDeathStateChanged)
    em:RegisterForEvent(name, EVENT_PLAYER_COMBAT_STATE, OnPlayerCombatState)
    em:RegisterForEvent(name, EVENT_BOSSES_CHANGED, OnBossesChanged)
    em:RegisterForEvent(name, EVENT_EFFECT_CHANGED, OnEffectChanged)

    -- Build state events
    em:RegisterForEvent(name, EVENT_INVENTORY_SINGLE_SLOT_UPDATE, OnInventorySlotUpdate)
    em:RegisterForEvent(name, EVENT_SKILL_RANK_UPDATE, OnSkillRankUpdate)
    em:RegisterForEvent(name, EVENT_ACTION_SLOT_UPDATED, OnActionSlotUpdated)

    -- Filter combat events to relevant ones only (performance optimization)
    em:AddFilterForEvent(name, EVENT_COMBAT_EVENT, REGISTER_FILTER_SOURCE_COMBAT_UNIT_TYPE, COMBAT_UNIT_TYPE_PLAYER)
    em:AddFilterForEvent(name, EVENT_COMBAT_EVENT, REGISTER_FILTER_IS_ERROR, false)
end

---------------------------------------------------------------------------
-- Public API
---------------------------------------------------------------------------

-- Save a completed combat run
function addon:SaveRun(runData)
    if not self.savedVars then return end

    -- Add to runs history
    table.insert(self.savedVars.runs, runData)

    -- Add to pending sync
    table.insert(self.savedVars.pendingSync.runs, runData)

    -- Update stats
    self.savedVars.stats.totalRunsRecorded = self.savedVars.stats.totalRunsRecorded + 1

    self:Debug("Run saved: %s", runData.run_id or "unknown")
end

-- Get current build snapshot
function addon:GetCurrentBuild()
    if self.BuildSnapshot then
        return self.BuildSnapshot:GetCurrentBuild()
    end
    return nil
end

-- Toggle UI visibility
function addon:ToggleUI()
    if self.MetricsUI then
        self.MetricsUI:Toggle()
    end
end

-- Slash commands
SLASH_COMMANDS["/ebo"] = function(args)
    if args == "toggle" or args == "" then
        addon:ToggleUI()
    elseif args == "expand" then
        if addon.MetricsUI then
            addon.MetricsUI:ToggleExpanded()
            addon:Info("UI %s", addon.MetricsUI:IsExpanded() and "expanded" or "collapsed")
        end
    elseif args == "advisor" then
        if addon.SkillAdvisor then
            local newState = not addon.SkillAdvisor:IsEnabled()
            addon.SkillAdvisor:SetEnabled(newState)
            addon:Info("Skill Advisor: %s", newState and "ON" or "OFF")
        end
    elseif args == "highlight" then
        if addon.SkillAdvisor then
            local newState = not addon.SkillAdvisor:IsHighlightEnabled()
            addon.SkillAdvisor:SetHighlightEnabled(newState)
            addon:Info("Skill Highlights: %s", newState and "ON" or "OFF")
        end
    elseif args == "auto" then
        if addon.MetricsUI then
            addon.MetricsUI:ToggleAutoDisplay()
            addon:Info("Auto-display: %s", addon.MetricsUI:IsAutoDisplayEnabled() and "ON" or "OFF")
        end
    elseif args == "debug" then
        addon.savedVars.settings.verboseLogging = not addon.savedVars.settings.verboseLogging
        addon:Info("Debug logging: %s", addon.savedVars.settings.verboseLogging and "ON" or "OFF")
    elseif args == "snapshot" then
        if addon.BuildSnapshot then
            addon.BuildSnapshot:CaptureFullSnapshot()
            addon:Info("Build snapshot captured")
        end
    elseif args == "status" then
        addon:Info("Status: %s", addon.CombatTracker and addon.CombatTracker:GetStatus() or "Unknown")
    else
        addon:Info("Commands: /ebo [toggle|expand|advisor|highlight|auto|debug|snapshot|status]")
    end
end

---------------------------------------------------------------------------
-- Initialize
---------------------------------------------------------------------------

RegisterEvents()
