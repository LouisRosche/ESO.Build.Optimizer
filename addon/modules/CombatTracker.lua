--[[
    ESO Build Optimizer - Combat Tracker Module

    Tracks combat metrics including:
    - Damage done/taken
    - Healing done
    - Buff/debuff uptime
    - Deaths, interrupts, synergies
    - Encounter start/end detection

    Author: ESO Build Optimizer Team
    Version: 1.0.0
]]--

---------------------------------------------------------------------------
-- Module Setup
---------------------------------------------------------------------------

local addon = ESOBuildOptimizer
local CombatTracker = {}
addon.CombatTracker = CombatTracker

---------------------------------------------------------------------------
-- Constants
---------------------------------------------------------------------------

-- Combat result types we track
local TRACKED_RESULTS = {
    [ACTION_RESULT_DAMAGE] = "damage",
    [ACTION_RESULT_CRITICAL_DAMAGE] = "damage_crit",
    [ACTION_RESULT_DOT_TICK] = "dot",
    [ACTION_RESULT_DOT_TICK_CRITICAL] = "dot_crit",
    [ACTION_RESULT_HEAL] = "heal",
    [ACTION_RESULT_CRITICAL_HEAL] = "heal_crit",
    [ACTION_RESULT_HOT_TICK] = "hot",
    [ACTION_RESULT_HOT_TICK_CRITICAL] = "hot_crit",
    [ACTION_RESULT_BLOCKED_DAMAGE] = "blocked",
    [ACTION_RESULT_DAMAGE_SHIELDED] = "shielded",
    [ACTION_RESULT_INTERRUPT] = "interrupt",
    [ACTION_RESULT_ABSORBED] = "absorbed",
    [ACTION_RESULT_FALL_DAMAGE] = "fall_damage",
    [ACTION_RESULT_KILLING_BLOW] = "killing_blow",
}

-- Buff categories for uptime tracking
local MAJOR_BUFFS = {
    "Major Brutality", "Major Sorcery", "Major Prophecy", "Major Savagery",
    "Major Berserk", "Major Force", "Major Slayer", "Major Courage",
    "Major Resolve", "Major Heroism", "Major Expedition",
}

local MINOR_BUFFS = {
    "Minor Brutality", "Minor Sorcery", "Minor Prophecy", "Minor Savagery",
    "Minor Berserk", "Minor Force", "Minor Slayer", "Minor Courage",
}

local MAJOR_DEBUFFS = {
    "Major Breach", "Major Fracture", "Major Maim", "Major Vulnerability",
    "Major Cowardice", "Major Defile",
}

local MINOR_DEBUFFS = {
    "Minor Breach", "Minor Fracture", "Minor Maim", "Minor Vulnerability",
    "Minor Brittle", "Minor Magickasteal", "Minor Lifesteal",
}

-- Combat timeout (seconds without combat event = encounter end)
local COMBAT_TIMEOUT = 8

-- Pre-computed boss unit tags for fast lookup
local BOSS_UNIT_TAGS = {}
local BOSS_UNIT_TAGS_SET = {}
for i = 1, MAX_BOSSES do
    local tag = "boss" .. i
    BOSS_UNIT_TAGS[i] = tag
    BOSS_UNIT_TAGS_SET[tag] = true
end

---------------------------------------------------------------------------
-- State
---------------------------------------------------------------------------

local state = {
    initialized = false,
    inCombat = false,
    inEncounter = false,
    encounterCounter = 0,  -- Counter to track encounter instance for race condition prevention

    -- Current encounter data
    encounter = {
        startTime = 0,
        lastEventTime = 0,
        bossName = nil,
        bossMaxHealth = 0,

        -- Metrics
        damage = {
            total = 0,
            direct = 0,
            dot = 0,
            critical = 0,
            hits = 0,
            crits = 0,
        },

        damageTaken = {
            total = 0,
            blocked = 0,
            shielded = 0,
        },

        healing = {
            total = 0,
            direct = 0,
            hot = 0,
            critical = 0,
            overhealing = 0,
        },

        -- Buff/debuff tracking
        buffs = {},      -- { buffName = { startTime, totalUptime, active } }
        debuffs = {},    -- { debuffName = { startTime, totalUptime, active } }

        -- Execution metrics
        deaths = 0,
        interrupts = 0,
        synergiesUsed = 0,
        synergiesProvided = 0,

        -- Resource tracking
        ultimateSpent = 0,
    },
}

-- Buff/debuff lookup tables for fast checking
local buffLookup = {}
local debuffLookup = {}

---------------------------------------------------------------------------
-- Utility Functions
---------------------------------------------------------------------------

local function GetCurrentTime()
    return GetGameTimeMilliseconds() / 1000
end

local function InitBuffLookups()
    for _, buff in ipairs(MAJOR_BUFFS) do
        buffLookup[buff] = true
    end
    for _, buff in ipairs(MINOR_BUFFS) do
        buffLookup[buff] = true
    end
    for _, debuff in ipairs(MAJOR_DEBUFFS) do
        debuffLookup[debuff] = true
    end
    for _, debuff in ipairs(MINOR_DEBUFFS) do
        debuffLookup[debuff] = true
    end
end

local function ResetEncounter()
    state.encounter = {
        startTime = 0,
        lastEventTime = 0,
        bossName = nil,
        bossMaxHealth = 0,

        damage = {
            total = 0,
            direct = 0,
            dot = 0,
            critical = 0,
            hits = 0,
            crits = 0,
        },

        damageTaken = {
            total = 0,
            blocked = 0,
            shielded = 0,
        },

        healing = {
            total = 0,
            direct = 0,
            hot = 0,
            critical = 0,
            overhealing = 0,
        },

        buffs = {},
        debuffs = {},

        deaths = 0,
        interrupts = 0,
        synergiesUsed = 0,
        synergiesProvided = 0,

        ultimateSpent = 0,
    }
end

local function CalculateBuffUptimes(encounter, duration)
    local uptimes = {}
    local currentTime = GetCurrentTime()

    for buffName, buffData in pairs(encounter.buffs) do
        local totalUptime = buffData.totalUptime

        -- Add current active duration if still active
        if buffData.active and buffData.startTime > 0 then
            totalUptime = totalUptime + (currentTime - buffData.startTime)
        end

        uptimes[buffName] = duration > 0 and (totalUptime / duration) or 0
    end

    return uptimes
end

local function CalculateDebuffUptimes(encounter, duration)
    local uptimes = {}
    local currentTime = GetCurrentTime()

    for debuffName, debuffData in pairs(encounter.debuffs) do
        local totalUptime = debuffData.totalUptime

        if debuffData.active and debuffData.startTime > 0 then
            totalUptime = totalUptime + (currentTime - debuffData.startTime)
        end

        uptimes[debuffName] = duration > 0 and (totalUptime / duration) or 0
    end

    return uptimes
end

---------------------------------------------------------------------------
-- Encounter Management
---------------------------------------------------------------------------

local function StartEncounter()
    if state.inEncounter then return end

    state.inEncounter = true
    state.encounterCounter = state.encounterCounter + 1
    ResetEncounter()

    state.encounter.startTime = GetCurrentTime()
    state.encounter.lastEventTime = state.encounter.startTime

    -- Check for boss using pre-computed tags
    local bossName = nil
    for i = 1, #BOSS_UNIT_TAGS do
        local bossUnitTag = BOSS_UNIT_TAGS[i]
        if DoesUnitExist(bossUnitTag) then
            bossName = GetUnitName(bossUnitTag)
            state.encounter.bossMaxHealth = GetUnitPower(bossUnitTag, POWERTYPE_HEALTH)
            break
        end
    end

    state.encounter.bossName = bossName

    addon:Debug("Encounter started: %s", bossName or "Unknown")

    -- Capture build snapshot at encounter start
    if addon.BuildSnapshot then
        addon.BuildSnapshot:CaptureFullSnapshot()
    end
end

local function EndEncounter(success)
    if not state.inEncounter then return end

    local encounter = state.encounter
    local duration = GetCurrentTime() - encounter.startTime

    -- Skip very short encounters (< 5 seconds)
    if duration < 5 then
        addon:Debug("Encounter too short, skipping: %.1fs", duration)
        state.inEncounter = false
        ResetEncounter()
        return
    end

    -- Calculate final metrics
    local dps = duration > 0 and (encounter.damage.total / duration) or 0
    local hps = duration > 0 and (encounter.healing.total / duration) or 0
    local critRate = encounter.damage.hits > 0 and
        (encounter.damage.crits / encounter.damage.hits) or 0

    -- Build run data for saving
    local runData = {
        run_id = addon:GenerateRunId(),
        timestamp = addon:GetTimestamp(),
        duration_sec = duration,
        success = success,

        content = {
            type = encounter.bossName and "dungeon" or "overworld",
            name = encounter.bossName or "Unknown",
            difficulty = "unknown", -- TODO: Detect difficulty
        },

        build_snapshot = addon:GetCurrentBuild(),

        metrics = {
            damage_done = encounter.damage.total,
            dps = math.floor(dps),
            crit_rate = critRate,

            healing_done = encounter.healing.total,
            hps = math.floor(hps),
            overhealing = encounter.healing.overhealing,

            damage_taken = encounter.damageTaken.total,
            damage_blocked = encounter.damageTaken.blocked,
            damage_shielded = encounter.damageTaken.shielded,

            deaths = encounter.deaths,
            interrupts = encounter.interrupts,
            synergies_used = encounter.synergiesUsed,

            buff_uptime = CalculateBuffUptimes(encounter, duration),
            debuff_uptime = CalculateDebuffUptimes(encounter, duration),
        },
    }

    -- Save the run
    addon:SaveRun(runData)

    addon:Debug("Encounter ended: %.1fs, DPS: %d, Success: %s",
        duration, math.floor(dps), tostring(success))

    -- Update UI
    if addon.MetricsUI then
        addon.MetricsUI:OnEncounterEnd(runData)
    end

    state.inEncounter = false
    ResetEncounter()
end

---------------------------------------------------------------------------
-- Combat Event Processing
---------------------------------------------------------------------------

function CombatTracker:OnCombatEvent(eventCode, result, isError, abilityName,
    abilityGraphic, abilityActionSlotType, sourceName, sourceType,
    targetName, targetType, hitValue, powerType, damageType, log,
    sourceUnitId, targetUnitId, abilityId, overflow)

    if not state.initialized then return end

    local resultType = TRACKED_RESULTS[result]
    if not resultType then return end

    -- Start encounter on first combat event
    if not state.inEncounter and hitValue > 0 then
        StartEncounter()
    end

    if not state.inEncounter then return end

    local encounter = state.encounter
    encounter.lastEventTime = GetCurrentTime()

    local totalHit = hitValue + (overflow or 0)

    -- Process by result type
    if resultType == "damage" or resultType == "damage_crit" then
        encounter.damage.total = encounter.damage.total + totalHit
        encounter.damage.direct = encounter.damage.direct + totalHit
        encounter.damage.hits = encounter.damage.hits + 1
        if resultType == "damage_crit" then
            encounter.damage.crits = encounter.damage.crits + 1
            encounter.damage.critical = encounter.damage.critical + totalHit
        end

    elseif resultType == "dot" or resultType == "dot_crit" then
        encounter.damage.total = encounter.damage.total + totalHit
        encounter.damage.dot = encounter.damage.dot + totalHit
        encounter.damage.hits = encounter.damage.hits + 1
        if resultType == "dot_crit" then
            encounter.damage.crits = encounter.damage.crits + 1
            encounter.damage.critical = encounter.damage.critical + totalHit
        end

    elseif resultType == "heal" or resultType == "heal_crit" then
        encounter.healing.total = encounter.healing.total + totalHit
        encounter.healing.direct = encounter.healing.direct + totalHit
        if resultType == "heal_crit" then
            encounter.healing.critical = encounter.healing.critical + totalHit
        end

    elseif resultType == "hot" or resultType == "hot_crit" then
        encounter.healing.total = encounter.healing.total + totalHit
        encounter.healing.hot = encounter.healing.hot + totalHit
        if resultType == "hot_crit" then
            encounter.healing.critical = encounter.healing.critical + totalHit
        end

    elseif resultType == "blocked" then
        encounter.damageTaken.blocked = encounter.damageTaken.blocked + totalHit

    elseif resultType == "shielded" then
        encounter.damageTaken.shielded = encounter.damageTaken.shielded + totalHit

    elseif resultType == "interrupt" then
        encounter.interrupts = encounter.interrupts + 1
    end

    -- Update UI with real-time metrics
    if addon.MetricsUI then
        local duration = GetCurrentTime() - encounter.startTime
        local dps = duration > 0 and (encounter.damage.total / duration) or 0
        local hps = duration > 0 and (encounter.healing.total / duration) or 0
        addon.MetricsUI:UpdateMetrics(dps, hps, encounter.damage.hits, encounter.damage.crits)
    end
end

function CombatTracker:OnUnitDeathStateChanged(unitTag, isDead)
    if not state.inEncounter then return end

    if unitTag == "player" and isDead then
        state.encounter.deaths = state.encounter.deaths + 1
        addon:Debug("Player died")
    end

    -- Check if boss died (success) using pre-computed lookup
    if isDead and BOSS_UNIT_TAGS_SET[unitTag] then
        EndEncounter(true)
    end
end

function CombatTracker:OnCombatStateChanged(inCombat)
    state.inCombat = inCombat

    if not inCombat and state.inEncounter then
        -- Store encounter ID to validate in callback (race condition prevention)
        local encounterId = state.encounterCounter

        -- Combat ended, give a short delay for final events
        zo_callLater(function()
            -- Validate this callback is still for the same encounter
            if encounterId ~= state.encounterCounter then return end
            if not state.inCombat and state.inEncounter then
                -- Determine success based on boss state using pre-computed tags
                local bossAlive = false
                for i = 1, #BOSS_UNIT_TAGS do
                    local bossTag = BOSS_UNIT_TAGS[i]
                    if DoesUnitExist(bossTag) and not IsUnitDead(bossTag) then
                        bossAlive = true
                        break
                    end
                end
                EndEncounter(not bossAlive)
            end
        end, 2000)
    end
end

function CombatTracker:OnBossesChanged()
    if state.inCombat and not state.inEncounter then
        -- Boss appeared while in combat, start encounter using pre-computed tags
        for i = 1, #BOSS_UNIT_TAGS do
            if DoesUnitExist(BOSS_UNIT_TAGS[i]) then
                StartEncounter()
                break
            end
        end
    end
end

function CombatTracker:OnEffectChanged(changeType, effectSlot, effectName,
    unitTag, beginTime, endTime, stackCount, iconName, buffType, effectType,
    abilityType, statusEffectType, unitName, unitId, abilityId, sourceType)

    if not state.inEncounter then return end

    local currentTime = GetCurrentTime()

    -- Track buffs on player
    if unitTag == "player" and buffLookup[effectName] then
        if changeType == EFFECT_RESULT_GAINED or changeType == EFFECT_RESULT_UPDATED then
            if not state.encounter.buffs[effectName] then
                state.encounter.buffs[effectName] = {
                    startTime = currentTime,
                    totalUptime = 0,
                    active = true,
                }
            else
                if not state.encounter.buffs[effectName].active then
                    state.encounter.buffs[effectName].startTime = currentTime
                    state.encounter.buffs[effectName].active = true
                end
            end
        elseif changeType == EFFECT_RESULT_FADED then
            local buffData = state.encounter.buffs[effectName]
            if buffData and buffData.active then
                buffData.totalUptime = buffData.totalUptime + (currentTime - buffData.startTime)
                buffData.active = false
            end
        end
    end

    -- Track debuffs on boss targets using pre-computed lookup
    local isBoss = BOSS_UNIT_TAGS_SET[unitTag]

    if isBoss and debuffLookup[effectName] then
        if changeType == EFFECT_RESULT_GAINED or changeType == EFFECT_RESULT_UPDATED then
            if not state.encounter.debuffs[effectName] then
                state.encounter.debuffs[effectName] = {
                    startTime = currentTime,
                    totalUptime = 0,
                    active = true,
                }
            else
                if not state.encounter.debuffs[effectName].active then
                    state.encounter.debuffs[effectName].startTime = currentTime
                    state.encounter.debuffs[effectName].active = true
                end
            end
        elseif changeType == EFFECT_RESULT_FADED then
            local debuffData = state.encounter.debuffs[effectName]
            if debuffData and debuffData.active then
                debuffData.totalUptime = debuffData.totalUptime + (currentTime - debuffData.startTime)
                debuffData.active = false
            end
        end
    end
end

---------------------------------------------------------------------------
-- Public API
---------------------------------------------------------------------------

function CombatTracker:Initialize()
    if state.initialized then return end

    InitBuffLookups()
    ResetEncounter()

    state.initialized = true
    addon:Debug("CombatTracker initialized")
end

function CombatTracker:GetStatus()
    if state.inEncounter then
        local duration = GetCurrentTime() - state.encounter.startTime
        local dps = duration > 0 and (state.encounter.damage.total / duration) or 0
        return string.format("In Combat - %.1fs - %d DPS", duration, math.floor(dps))
    else
        return "Idle"
    end
end

function CombatTracker:GetCurrentEncounter()
    if state.inEncounter then
        return state.encounter
    end
    return nil
end

function CombatTracker:IsInEncounter()
    return state.inEncounter
end

function CombatTracker:ForceEndEncounter(success)
    if state.inEncounter then
        EndEncounter(success or false)
    end
end
