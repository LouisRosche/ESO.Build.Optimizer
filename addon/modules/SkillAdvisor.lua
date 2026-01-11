--[[
    ESO Build Optimizer - Skill Advisor Module

    Provides real-time skill recommendations based on:
    - Nearby enemy count (AoE suggestions)
    - Skill cooldowns
    - Combat situation awareness

    Author: ESO Build Optimizer Team
    Version: 0.1.0
]]--

---------------------------------------------------------------------------
-- Module Setup
---------------------------------------------------------------------------

local addon = ESOBuildOptimizer
local SkillAdvisor = {}
addon.SkillAdvisor = SkillAdvisor

---------------------------------------------------------------------------
-- Constants
---------------------------------------------------------------------------

local UPDATE_INTERVAL_MS = 200  -- Update every 200ms during combat
local AOE_ENEMY_THRESHOLD = 2   -- Suggest AoE when 2+ enemies nearby
local ENEMY_DETECTION_RANGE = 10 -- Range in meters for nearby enemy detection

-- Skill tags for categorization (ability IDs mapped to tags)
-- This would be expanded with actual ability ID mappings
local SKILL_TAGS = {
    -- Format: [abilityId] = { tags = {"aoe", "dot", "execute", etc}, minTargets = 1 }
    -- Example skills - these would be expanded based on data files
}

-- Known AoE skills by name pattern (fallback when ID not mapped)
local AOE_SKILL_PATTERNS = {
    "Wall of",
    "Unstable Wall",
    "Elemental Storm",
    "Flurry",
    "Whirlwind",
    "Steel Tornado",
    "Brawler",
    "Cleave",
    "Carve",
    "Puncturing Sweep",
    "Jabs",
    "Whirling Blades",
    "Blastbones",
    "Stalking Blastbones",
    "Unnerving Boneyard",
    "Pestilent Colossus",
    "Glacial Colossus",
    "Elemental Blockade",
    "Liquid Lightning",
    "Impale",
    "Killers Blade",
    "Radiant Glory",
    "Radiant Oppression",
    "Executioner",
    "Reverse Slash",
}

-- Execute skills (for low health targets)
local EXECUTE_SKILL_PATTERNS = {
    "Killer",
    "Executioner",
    "Reverse Slash",
    "Radiant Glory",
    "Radiant Oppression",
    "Impale",
    "Assassin's Will",
    "Merciless Resolve",
}

local COLORS = {
    highlight = { 1.0, 0.82, 0.0, 0.8 },  -- Gold highlight
    aoe = { 0.6, 0.2, 1.0, 0.8 },          -- Purple for AoE
    execute = { 1.0, 0.2, 0.2, 0.8 },       -- Red for execute
    normal = { 1.0, 1.0, 1.0, 0.6 },        -- White normal
}

---------------------------------------------------------------------------
-- State
---------------------------------------------------------------------------

local state = {
    initialized = false,
    enabled = true,
    highlightEnabled = true,

    -- Combat state
    inCombat = false,
    nearbyEnemyCount = 0,
    targetHealthPercent = 100,

    -- Skill analysis
    frontBarSkills = {},
    backBarSkills = {},
    currentBar = 1,  -- 1 = front, 2 = back

    -- Cooldown tracking
    cooldowns = {},  -- { [slotIndex] = { remaining = 0, duration = 0 } }

    -- Current recommendation
    currentRecommendation = nil,
    recommendationReason = "",

    -- UI elements for highlights
    highlights = {},

    -- Update handler
    updateName = "ESOBuildOptimizer_SkillAdvisor_Update",
}

---------------------------------------------------------------------------
-- Utility Functions
---------------------------------------------------------------------------

local function GetCurrentTime()
    return GetGameTimeMilliseconds() / 1000
end

local function IsSkillAoE(abilityId, abilityName)
    -- Check skill tags first
    local skillInfo = SKILL_TAGS[abilityId]
    if skillInfo and skillInfo.tags then
        for _, tag in ipairs(skillInfo.tags) do
            if tag == "aoe" then
                return true
            end
        end
    end

    -- Fallback to name pattern matching
    if abilityName then
        for _, pattern in ipairs(AOE_SKILL_PATTERNS) do
            if string.find(abilityName, pattern) then
                return true
            end
        end
    end

    return false
end

local function IsSkillExecute(abilityId, abilityName)
    -- Check skill tags first
    local skillInfo = SKILL_TAGS[abilityId]
    if skillInfo and skillInfo.tags then
        for _, tag in ipairs(skillInfo.tags) do
            if tag == "execute" then
                return true
            end
        end
    end

    -- Fallback to name pattern matching
    if abilityName then
        for _, pattern in ipairs(EXECUTE_SKILL_PATTERNS) do
            if string.find(abilityName, pattern) then
                return true
            end
        end
    end

    return false
end

local function CountNearbyEnemies()
    local count = 0

    -- Method 1: Check combat targets via reticle and nearby units
    -- ESO doesn't have a direct "GetNearbyEnemies" function, so we use
    -- a combination of approaches

    -- Check if we have a target
    if DoesUnitExist("reticleover") then
        local reaction = GetUnitReaction("reticleover")
        if reaction == UNIT_REACTION_HOSTILE then
            count = count + 1
        end
    end

    -- Check boss units
    for i = 1, MAX_BOSSES do
        local bossTag = "boss" .. i
        if DoesUnitExist(bossTag) and not IsUnitDead(bossTag) then
            count = count + 1
        end
    end

    -- Use combat event tracking from CombatTracker for additional accuracy
    -- This is a simplified approach - in practice, you'd track unit IDs
    -- from combat events to build a more accurate picture

    -- For now, use a heuristic based on recent combat events
    if addon.CombatTracker and addon.CombatTracker:IsInEncounter() then
        local encounter = addon.CombatTracker:GetCurrentEncounter()
        if encounter then
            -- Estimate based on damage pattern (multiple targets = more hits)
            -- This is an approximation
            local hitRate = encounter.damage.hits > 0 and
                (encounter.damage.hits / math.max(1, GetCurrentTime() - encounter.startTime)) or 0

            -- High hit rate suggests multiple targets (AoE hitting)
            if hitRate > 5 then
                count = math.max(count, 3)
            elseif hitRate > 3 then
                count = math.max(count, 2)
            end
        end
    end

    return count
end

local function GetTargetHealthPercent()
    if DoesUnitExist("reticleover") then
        local current, max = GetUnitPower("reticleover", POWERTYPE_HEALTH)
        if max > 0 then
            return (current / max) * 100
        end
    end

    -- Check boss health as alternative
    for i = 1, MAX_BOSSES do
        local bossTag = "boss" .. i
        if DoesUnitExist(bossTag) and not IsUnitDead(bossTag) then
            local current, max = GetUnitPower(bossTag, POWERTYPE_HEALTH)
            if max > 0 then
                return (current / max) * 100
            end
        end
    end

    return 100
end

---------------------------------------------------------------------------
-- Skill Bar Analysis
---------------------------------------------------------------------------

local function AnalyzeSkillBar(hotbarCategory)
    local skills = {}
    local slots = {3, 4, 5, 6, 7, 8}  -- Standard skill slots

    for _, slotIndex in ipairs(slots) do
        local abilityId = GetSlotBoundId(slotIndex, hotbarCategory)

        if abilityId and abilityId > 0 then
            local abilityName = GetAbilityName(abilityId)
            local isPassive = IsAbilityPassive(abilityId)

            if not isPassive then
                local isAoE = IsSkillAoE(abilityId, abilityName)
                local isExecute = IsSkillExecute(abilityId, abilityName)
                local cost, mechanic = GetAbilityCost(abilityId)
                local isUltimate = (slotIndex == 8)

                skills[slotIndex] = {
                    id = abilityId,
                    name = abilityName,
                    isAoE = isAoE,
                    isExecute = isExecute,
                    isUltimate = isUltimate,
                    cost = cost,
                    resource = mechanic,
                }
            end
        end
    end

    return skills
end

local function RefreshSkillBars()
    state.frontBarSkills = AnalyzeSkillBar(HOTBAR_CATEGORY_PRIMARY)
    state.backBarSkills = AnalyzeSkillBar(HOTBAR_CATEGORY_BACKUP)
    addon:Debug("SkillAdvisor: Skill bars refreshed")
end

---------------------------------------------------------------------------
-- Cooldown Tracking
---------------------------------------------------------------------------

local function UpdateCooldowns()
    local slots = {3, 4, 5, 6, 7, 8}

    for _, slotIndex in ipairs(slots) do
        local remaining, duration, global, globalSlotType = GetSlotCooldownInfo(slotIndex)

        state.cooldowns[slotIndex] = {
            remaining = remaining / 1000,  -- Convert to seconds
            duration = duration / 1000,
            isOnCooldown = remaining > 0,
            isGlobal = global,
        }
    end
end

local function IsSkillReady(slotIndex)
    local cooldownInfo = state.cooldowns[slotIndex]
    if cooldownInfo then
        return not cooldownInfo.isOnCooldown
    end
    return true
end

---------------------------------------------------------------------------
-- Recommendation Engine
---------------------------------------------------------------------------

local function GetCurrentBarSkills()
    local activeBar = GetActiveHotbarCategory()
    if activeBar == HOTBAR_CATEGORY_PRIMARY then
        state.currentBar = 1
        return state.frontBarSkills
    else
        state.currentBar = 2
        return state.backBarSkills
    end
end

local function GenerateRecommendation()
    if not state.enabled or not state.inCombat then
        state.currentRecommendation = nil
        state.recommendationReason = ""
        return nil
    end

    local skills = GetCurrentBarSkills()
    if not skills or not next(skills) then
        return nil
    end

    UpdateCooldowns()

    local recommendation = nil
    local reason = ""
    local priority = 0  -- Higher = more important

    -- Priority 1: Execute phase (target below 25% health)
    if state.targetHealthPercent <= 25 then
        for slotIndex, skill in pairs(skills) do
            if skill.isExecute and IsSkillReady(slotIndex) and not skill.isUltimate then
                if priority < 3 then
                    recommendation = slotIndex
                    reason = "Execute phase - target low health"
                    priority = 3
                end
            end
        end
    end

    -- Priority 2: AoE when multiple enemies
    if state.nearbyEnemyCount >= AOE_ENEMY_THRESHOLD then
        for slotIndex, skill in pairs(skills) do
            if skill.isAoE and IsSkillReady(slotIndex) and not skill.isUltimate then
                if priority < 2 then
                    recommendation = slotIndex
                    reason = string.format("AoE recommended - %d enemies nearby", state.nearbyEnemyCount)
                    priority = 2
                end
            end
        end
    end

    state.currentRecommendation = recommendation
    state.recommendationReason = reason

    return recommendation, reason
end

---------------------------------------------------------------------------
-- Visual Highlight System
---------------------------------------------------------------------------

local function CreateHighlightFrame(slotIndex)
    local name = "ESOBuildOptimizer_SkillHighlight_" .. slotIndex
    local highlight = WINDOW_MANAGER:CreateControl(name, GuiRoot, CT_TEXTURE)

    highlight:SetDimensions(52, 52)
    highlight:SetDrawLayer(DL_OVERLAY)
    highlight:SetDrawTier(DT_HIGH)
    highlight:SetTexture("EsoUI/Art/ActionBar/abilityHighlight.dds")
    highlight:SetColor(unpack(COLORS.highlight))
    highlight:SetHidden(true)

    -- Position will be updated when highlighting
    highlight.slotIndex = slotIndex

    return highlight
end

local function InitializeHighlights()
    local slots = {3, 4, 5, 6, 7, 8}

    for _, slotIndex in ipairs(slots) do
        if not state.highlights[slotIndex] then
            state.highlights[slotIndex] = CreateHighlightFrame(slotIndex)
        end
    end
end

local function UpdateHighlightPosition(highlight, slotIndex)
    -- Get the action button control for this slot
    local actionButton = ZO_ActionBar_GetButton(slotIndex)

    if actionButton then
        local buttonControl = actionButton.slot
        if buttonControl then
            highlight:ClearAnchors()
            highlight:SetAnchor(CENTER, buttonControl, CENTER, 0, 0)
            return true
        end
    end

    return false
end

local function ShowHighlight(slotIndex, color)
    if not state.highlightEnabled then return end

    local highlight = state.highlights[slotIndex]
    if highlight then
        if UpdateHighlightPosition(highlight, slotIndex) then
            highlight:SetColor(unpack(color or COLORS.highlight))
            highlight:SetHidden(false)

            -- Pulse animation
            if not highlight.animation then
                highlight.animation = ANIMATION_MANAGER:CreateTimeline()

                local pulse = highlight.animation:InsertAnimation(ANIMATION_ALPHA, highlight, 0)
                pulse:SetDuration(500)
                pulse:SetAlphaValues(0.4, 1.0)
                pulse:SetEasingFunction(ZO_EaseOutQuadratic)

                local pulseBack = highlight.animation:InsertAnimation(ANIMATION_ALPHA, highlight, 500)
                pulseBack:SetDuration(500)
                pulseBack:SetAlphaValues(1.0, 0.4)
                pulseBack:SetEasingFunction(ZO_EaseInQuadratic)

                highlight.animation:SetPlaybackType(ANIMATION_PLAYBACK_LOOP, LOOP_INDEFINITELY)
            end

            highlight.animation:PlayFromStart()
        end
    end
end

local function HideHighlight(slotIndex)
    local highlight = state.highlights[slotIndex]
    if highlight then
        highlight:SetHidden(true)
        if highlight.animation then
            highlight.animation:Stop()
        end
    end
end

local function HideAllHighlights()
    for slotIndex, highlight in pairs(state.highlights) do
        HideHighlight(slotIndex)
    end
end

local function UpdateHighlights()
    if not state.highlightEnabled or not state.inCombat then
        HideAllHighlights()
        return
    end

    local recommendation = state.currentRecommendation

    -- Hide all highlights first
    for slotIndex, _ in pairs(state.highlights) do
        if slotIndex ~= recommendation then
            HideHighlight(slotIndex)
        end
    end

    -- Show highlight for recommended skill
    if recommendation then
        local skills = GetCurrentBarSkills()
        local skill = skills and skills[recommendation]

        local color = COLORS.highlight
        if skill then
            if skill.isExecute then
                color = COLORS.execute
            elseif skill.isAoE then
                color = COLORS.aoe
            end
        end

        ShowHighlight(recommendation, color)
    end
end

---------------------------------------------------------------------------
-- Update Loop
---------------------------------------------------------------------------

local function OnUpdate()
    if not state.initialized or not state.enabled then return end
    if not state.inCombat then return end

    -- Update combat situation
    state.nearbyEnemyCount = CountNearbyEnemies()
    state.targetHealthPercent = GetTargetHealthPercent()

    -- Generate recommendation
    GenerateRecommendation()

    -- Update visual highlights
    UpdateHighlights()

    -- Notify MetricsUI of recommendation
    if addon.MetricsUI and addon.MetricsUI.UpdateSkillRecommendation then
        addon.MetricsUI:UpdateSkillRecommendation(
            state.currentRecommendation,
            state.recommendationReason
        )
    end
end

local function StartUpdateLoop()
    EVENT_MANAGER:RegisterForUpdate(state.updateName, UPDATE_INTERVAL_MS, OnUpdate)
end

local function StopUpdateLoop()
    EVENT_MANAGER:UnregisterForUpdate(state.updateName)
end

---------------------------------------------------------------------------
-- Event Handlers
---------------------------------------------------------------------------

function SkillAdvisor:OnCombatStateChanged(inCombat)
    state.inCombat = inCombat

    if inCombat then
        RefreshSkillBars()
        StartUpdateLoop()
    else
        StopUpdateLoop()
        HideAllHighlights()
        state.currentRecommendation = nil
        state.recommendationReason = ""
    end
end

function SkillAdvisor:OnActionBarChanged(slotIndex)
    if state.initialized then
        RefreshSkillBars()
    end
end

function SkillAdvisor:OnActiveWeaponPairChanged(activeWeaponPair, locked)
    -- Bar swap occurred
    if state.inCombat then
        -- Immediate update on bar swap
        OnUpdate()
    end
end

---------------------------------------------------------------------------
-- Public API
---------------------------------------------------------------------------

function SkillAdvisor:Initialize()
    if state.initialized then return end

    -- Load settings
    if addon.savedVars and addon.savedVars.settings then
        state.enabled = addon.savedVars.settings.showSkillAdvisor ~= false
        state.highlightEnabled = addon.savedVars.settings.skillHighlightEnabled ~= false
    end

    -- Initialize highlights
    InitializeHighlights()

    -- Initial skill bar analysis
    RefreshSkillBars()

    -- Register for weapon swap event
    EVENT_MANAGER:RegisterForEvent(
        addon.name .. "_SkillAdvisor",
        EVENT_ACTIVE_WEAPON_PAIR_CHANGED,
        function(eventCode, activeWeaponPair, locked)
            self:OnActiveWeaponPairChanged(activeWeaponPair, locked)
        end
    )

    state.initialized = true
    addon:Debug("SkillAdvisor initialized")
end

function SkillAdvisor:SetEnabled(enabled)
    state.enabled = enabled

    if addon.savedVars then
        addon.savedVars.settings.showSkillAdvisor = enabled
    end

    if not enabled then
        HideAllHighlights()
        state.currentRecommendation = nil
    end
end

function SkillAdvisor:SetHighlightEnabled(enabled)
    state.highlightEnabled = enabled

    if addon.savedVars then
        addon.savedVars.settings.skillHighlightEnabled = enabled
    end

    if not enabled then
        HideAllHighlights()
    end
end

function SkillAdvisor:IsEnabled()
    return state.enabled
end

function SkillAdvisor:IsHighlightEnabled()
    return state.highlightEnabled
end

function SkillAdvisor:GetCurrentRecommendation()
    return state.currentRecommendation, state.recommendationReason
end

function SkillAdvisor:GetNearbyEnemyCount()
    return state.nearbyEnemyCount
end

function SkillAdvisor:GetTargetHealthPercent()
    return state.targetHealthPercent
end

function SkillAdvisor:GetCooldownInfo(slotIndex)
    return state.cooldowns[slotIndex]
end

function SkillAdvisor:RefreshSkillBars()
    RefreshSkillBars()
end

-- Manual trigger for testing
function SkillAdvisor:ForceUpdate()
    RefreshSkillBars()
    UpdateCooldowns()
    state.nearbyEnemyCount = CountNearbyEnemies()
    state.targetHealthPercent = GetTargetHealthPercent()
    GenerateRecommendation()
    UpdateHighlights()
end
