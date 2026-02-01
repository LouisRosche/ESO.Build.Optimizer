--[[
    ESO Build Optimizer
    Main Addon File

    Combat metrics tracking with ML-powered recommendations.
    This addon collects combat data and build information for analysis
    by the companion app and cloud ML pipeline.

    Author: ESO Build Optimizer Team
    Version: 1.0.0
    APIVersion: 101046 101047
]]--

---------------------------------------------------------------------------
-- Addon Namespace
---------------------------------------------------------------------------

ESOBuildOptimizer = ESOBuildOptimizer or {}
local addon = ESOBuildOptimizer

addon.name = "ESOBuildOptimizer"
addon.displayName = "ESO Build Optimizer"
addon.version = "1.0.0"
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
-- Constants
---------------------------------------------------------------------------

local MAX_PENDING_RUNS = 100  -- Maximum pending runs before FIFO eviction

---------------------------------------------------------------------------
-- Local State
---------------------------------------------------------------------------

local isInitialized = false
local isPlayerActivated = false

---------------------------------------------------------------------------
-- Utility Functions
---------------------------------------------------------------------------

-- Deep copy function for nested tables
local function DeepCopy(orig)
    local origType = type(orig)
    local copy
    if origType == "table" then
        copy = {}
        for origKey, origValue in pairs(orig) do
            copy[DeepCopy(origKey)] = DeepCopy(origValue)
        end
    else
        copy = orig
    end
    return copy
end

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

    -- Merge defaults with saved data using deep copy for nested tables
    for key, defaultValue in pairs(defaultSavedVars) do
        if ESOBuildOptimizerSV[key] == nil then
            ESOBuildOptimizerSV[key] = DeepCopy(defaultValue)
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

    -- Initialize random seed for unique ID generation
    math.randomseed(GetGameTimeMilliseconds())

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

    -- Unregister this event after first activation (only need it once)
    EVENT_MANAGER:UnregisterForEvent(addon.name, EVENT_PLAYER_ACTIVATED)

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
-- Note: Filtered at registration to BAG_WORN only
local function OnInventorySlotUpdate(eventCode, bagId, slotIndex, isNewItem,
    itemSoundCategory, inventoryUpdateReason, stackCountChange)

    if addon.BuildSnapshot and isPlayerActivated then
        addon.BuildSnapshot:OnEquipmentChanged(slotIndex)
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

    -- Combat events with unique namespace for filtered event
    local combatEventName = name .. "_combat"
    em:RegisterForEvent(combatEventName, EVENT_COMBAT_EVENT, OnCombatEvent)
    em:AddFilterForEvent(combatEventName, EVENT_COMBAT_EVENT, REGISTER_FILTER_SOURCE_COMBAT_UNIT_TYPE, COMBAT_UNIT_TYPE_PLAYER)
    em:AddFilterForEvent(combatEventName, EVENT_COMBAT_EVENT, REGISTER_FILTER_IS_ERROR, false)

    em:RegisterForEvent(name, EVENT_UNIT_DEATH_STATE_CHANGED, OnUnitDeathStateChanged)
    em:RegisterForEvent(name, EVENT_PLAYER_COMBAT_STATE, OnPlayerCombatState)
    em:RegisterForEvent(name, EVENT_BOSSES_CHANGED, OnBossesChanged)

    -- Effect changed events - HIGH FREQUENCY, requires filtering
    -- Register separately for player buffs and boss debuffs with unique namespaces
    local effectPlayerName = name .. "_effect_player"
    em:RegisterForEvent(effectPlayerName, EVENT_EFFECT_CHANGED, OnEffectChanged)
    em:AddFilterForEvent(effectPlayerName, EVENT_EFFECT_CHANGED, REGISTER_FILTER_UNIT_TAG, "player")

    -- Register for boss unit effects (boss1 through boss6)
    for i = 1, MAX_BOSSES do
        local effectBossName = name .. "_effect_boss" .. i
        em:RegisterForEvent(effectBossName, EVENT_EFFECT_CHANGED, OnEffectChanged)
        em:AddFilterForEvent(effectBossName, EVENT_EFFECT_CHANGED, REGISTER_FILTER_UNIT_TAG, "boss" .. i)
    end

    -- Build state events with filtering
    local inventoryEventName = name .. "_inventory"
    em:RegisterForEvent(inventoryEventName, EVENT_INVENTORY_SINGLE_SLOT_UPDATE, OnInventorySlotUpdate)
    em:AddFilterForEvent(inventoryEventName, EVENT_INVENTORY_SINGLE_SLOT_UPDATE, REGISTER_FILTER_BAG_ID, BAG_WORN)

    em:RegisterForEvent(name, EVENT_SKILL_RANK_UPDATE, OnSkillRankUpdate)
    em:RegisterForEvent(name, EVENT_ACTION_SLOT_UPDATED, OnActionSlotUpdated)
end

---------------------------------------------------------------------------
-- Public API
---------------------------------------------------------------------------

-- Save a completed combat run
function addon:SaveRun(runData)
    if not self.savedVars then return end

    -- Add to runs history
    table.insert(self.savedVars.runs, runData)

    -- Add to pending sync with FIFO eviction if limit exceeded
    table.insert(self.savedVars.pendingSync.runs, runData)
    while #self.savedVars.pendingSync.runs > MAX_PENDING_RUNS do
        table.remove(self.savedVars.pendingSync.runs, 1)
        self:Debug("Pending sync limit exceeded, evicted oldest run")
    end

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

-- Slash commands (comprehensive for gamepad/console accessibility)
SLASH_COMMANDS["/ebo"] = function(args)
    -- Parse command and arguments
    local cmd, param = string.match(args or "", "^(%S*)%s*(.*)$")
    cmd = string.lower(cmd or "")

    if cmd == "" or cmd == "help" then
        -- Show help
        addon:Info("ESO Build Optimizer v" .. addon.version)
        addon:Info("Commands:")
        addon:Info("  /ebo toggle   - Show/hide metrics display")
        addon:Info("  /ebo expand   - Expand to detailed view")
        addon:Info("  /ebo collapse - Collapse to minimal view")
        addon:Info("  /ebo lock     - Lock UI position")
        addon:Info("  /ebo unlock   - Unlock for repositioning")
        addon:Info("  /ebo reset    - Reset current encounter")
        addon:Info("  /ebo resetui  - Reset UI to default position")
        addon:Info("  /ebo advisor  - Toggle skill recommendations")
        addon:Info("  /ebo scale <n> - Set UI scale (0.5-2.0)")
        addon:Info("  /ebo link <token> - Link website account")
        addon:Info("  /ebo status   - Show current status")
    elseif cmd == "ui" or cmd == "toggle" then
        addon:ToggleUI()
    elseif cmd == "expand" then
        if addon.MetricsUI then
            addon.MetricsUI:SetExpanded(true)
            addon:Info("UI expanded")
        end
    elseif cmd == "collapse" then
        if addon.MetricsUI then
            addon.MetricsUI:SetExpanded(false)
            addon:Info("UI collapsed")
        end
    elseif cmd == "lock" then
        if addon.MetricsUI then
            addon.MetricsUI:Lock()
            addon:Info("UI position locked")
        end
    elseif cmd == "unlock" then
        if addon.MetricsUI then
            addon.MetricsUI:Unlock()
            addon:Info("UI unlocked - drag to reposition")
        end
    elseif cmd == "reset" then
        if addon.CombatTracker then
            addon.CombatTracker:ResetEncounter()
            addon:Info("Encounter reset")
        end
    elseif cmd == "resetui" then
        if addon.MetricsUI then
            addon.MetricsUI:ResetPosition()
            addon:Info("UI position reset to default")
        end
    elseif cmd == "link" then
        if param and param ~= "" then
            -- Store token for companion app to use
            if addon.savedVars then
                addon.savedVars.accountToken = param
                addon:Info("Account linked! Token saved for sync.")
            end
        else
            addon:Info("Usage: /ebo link <token>")
            addon:Info("Get your token from the website dashboard.")
        end
    elseif cmd == "advisor" then
        if addon.SkillAdvisor then
            local newState = not addon.SkillAdvisor:IsEnabled()
            addon.SkillAdvisor:SetEnabled(newState)
            addon:Info("Skill Advisor: %s", newState and "ON" or "OFF")
        end
    elseif cmd == "highlight" then
        if addon.SkillAdvisor then
            local newState = not addon.SkillAdvisor:IsHighlightEnabled()
            addon.SkillAdvisor:SetHighlightEnabled(newState)
            addon:Info("Skill Highlights: %s", newState and "ON" or "OFF")
        end
    elseif cmd == "auto" then
        if addon.MetricsUI then
            addon.MetricsUI:ToggleAutoDisplay()
            addon:Info("Auto-display: %s", addon.MetricsUI:IsAutoDisplayEnabled() and "ON" or "OFF")
        end
    elseif cmd == "scale" then
        local scale = tonumber(param)
        if scale and scale >= 0.5 and scale <= 2.0 then
            if addon.MetricsUI then
                addon.MetricsUI:SetScale(scale)
                addon:Info("UI scale: %.1f", scale)
            end
        else
            addon:Info("Usage: /ebo scale <0.5-2.0>")
        end
    elseif cmd == "debug" then
        addon.savedVars.settings.verboseLogging = not addon.savedVars.settings.verboseLogging
        addon:Info("Debug logging: %s", addon.savedVars.settings.verboseLogging and "ON" or "OFF")
    elseif cmd == "snapshot" then
        if addon.BuildSnapshot then
            addon.BuildSnapshot:CaptureFullSnapshot()
            addon:Info("Build snapshot captured")
        end
    elseif cmd == "status" then
        local status = "Unknown"
        if addon.CombatTracker then
            local inCombat = addon.CombatTracker:IsInEncounter()
            local runsCount = addon.savedVars and addon.savedVars.stats and addon.savedVars.stats.totalRunsRecorded or 0
            status = string.format("%s | %d runs recorded", inCombat and "In Combat" or "Idle", runsCount)
        end
        addon:Info("Status: %s", status)
        if addon.savedVars and addon.savedVars.accountToken then
            addon:Info("Account: Linked")
        else
            addon:Info("Account: Not linked (/ebo link <token>)")
        end
    else
        addon:Info("Unknown command: %s. Type /ebo help for commands.", cmd)
    end
end

---------------------------------------------------------------------------
-- Initialize
---------------------------------------------------------------------------

RegisterEvents()
