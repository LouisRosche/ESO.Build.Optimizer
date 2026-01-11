--[[
    ESO Build Optimizer - Build Snapshot Module

    Captures current character build state:
    - Equipped gear sets
    - Slotted skills (front/back bar)
    - Champion points
    - Character stats

    Author: ESO Build Optimizer Team
    Version: 1.0.0
]]--

---------------------------------------------------------------------------
-- Module Setup
---------------------------------------------------------------------------

local addon = ESOBuildOptimizer
local BuildSnapshot = {}
addon.BuildSnapshot = BuildSnapshot

---------------------------------------------------------------------------
-- Constants
---------------------------------------------------------------------------

-- Equipment slot mappings
local EQUIPMENT_SLOTS = {
    EQUIP_SLOT_HEAD,
    EQUIP_SLOT_NECK,
    EQUIP_SLOT_CHEST,
    EQUIP_SLOT_SHOULDERS,
    EQUIP_SLOT_MAIN_HAND,
    EQUIP_SLOT_OFF_HAND,
    EQUIP_SLOT_WAIST,
    EQUIP_SLOT_LEGS,
    EQUIP_SLOT_FEET,
    EQUIP_SLOT_RING1,
    EQUIP_SLOT_RING2,
    EQUIP_SLOT_HAND,
    EQUIP_SLOT_BACKUP_MAIN,
    EQUIP_SLOT_BACKUP_OFF,
}

local SLOT_NAMES = {
    [EQUIP_SLOT_HEAD] = "Head",
    [EQUIP_SLOT_NECK] = "Neck",
    [EQUIP_SLOT_CHEST] = "Chest",
    [EQUIP_SLOT_SHOULDERS] = "Shoulders",
    [EQUIP_SLOT_MAIN_HAND] = "Main Hand",
    [EQUIP_SLOT_OFF_HAND] = "Off Hand",
    [EQUIP_SLOT_WAIST] = "Waist",
    [EQUIP_SLOT_LEGS] = "Legs",
    [EQUIP_SLOT_FEET] = "Feet",
    [EQUIP_SLOT_RING1] = "Ring 1",
    [EQUIP_SLOT_RING2] = "Ring 2",
    [EQUIP_SLOT_HAND] = "Hands",
    [EQUIP_SLOT_BACKUP_MAIN] = "Backup Main",
    [EQUIP_SLOT_BACKUP_OFF] = "Backup Off",
}

-- Class ID to name mapping
local CLASS_NAMES = {
    [1] = "Dragonknight",
    [2] = "Sorcerer",
    [3] = "Nightblade",
    [4] = "Warden",
    [5] = "Necromancer",
    [6] = "Templar",
    [117] = "Arcanist",
}

-- Race ID to name mapping
local RACE_NAMES = {
    [1] = "Breton",
    [2] = "Redguard",
    [3] = "Orc",
    [4] = "Dark Elf",
    [5] = "Nord",
    [6] = "Argonian",
    [7] = "High Elf",
    [8] = "Wood Elf",
    [9] = "Khajiit",
    [10] = "Imperial",
}

-- Action bar slots
local ACTION_BAR_SLOTS = {3, 4, 5, 6, 7, 8} -- Slots 3-7 are skills, 8 is ultimate

---------------------------------------------------------------------------
-- State
---------------------------------------------------------------------------

local state = {
    initialized = false,
    currentBuild = nil,
    lastSnapshotTime = 0,
    pendingUpdate = false,
}

---------------------------------------------------------------------------
-- Utility Functions
---------------------------------------------------------------------------

local function GetClassName(classId)
    return CLASS_NAMES[classId] or "Unknown"
end

local function GetRaceName(raceId)
    return RACE_NAMES[raceId] or "Unknown"
end

local function GetCurrentTime()
    return GetGameTimeMilliseconds() / 1000
end

---------------------------------------------------------------------------
-- Equipment Capture
---------------------------------------------------------------------------

local function CaptureEquippedGear()
    local gear = {}
    local sets = {}
    local setCount = {}

    for _, slot in ipairs(EQUIPMENT_SLOTS) do
        local itemLink = GetItemLink(BAG_WORN, slot)

        -- Validate item link format before processing
        if itemLink and itemLink ~= "" and string.match(itemLink, "^|H") then
            local hasSet, setName, numBonuses, numEquipped, maxEquipped = GetItemLinkSetInfo(itemLink)
            local itemName = GetItemName(BAG_WORN, slot)
            local quality = GetItemQuality(BAG_WORN, slot)
            local level = GetItemLevel(BAG_WORN, slot)
            local trait = GetItemTrait(BAG_WORN, slot)
            -- Validate trait before getting string representation
            local traitName = (trait and trait ~= ITEM_TRAIT_TYPE_NONE)
                and GetString("SI_ITEMTRAITTYPE", trait) or "None"

            gear[SLOT_NAMES[slot]] = {
                name = itemName,
                link = itemLink,
                quality = quality,
                level = level,
                trait = traitName,
                set = hasSet and setName or nil,
            }

            if hasSet then
                setCount[setName] = (setCount[setName] or 0) + 1
            end
        end
    end

    -- Build set list with piece counts
    for setName, count in pairs(setCount) do
        table.insert(sets, {
            name = setName,
            pieces = count,
        })
    end

    return gear, sets
end

---------------------------------------------------------------------------
-- Skills Capture
---------------------------------------------------------------------------

local function CaptureActionBar(hotbarCategory)
    local skills = {}

    for _, slotIndex in ipairs(ACTION_BAR_SLOTS) do
        local abilityId = GetSlotBoundId(slotIndex, hotbarCategory)

        if abilityId and abilityId > 0 then
            local abilityName = GetAbilityName(abilityId)
            local isUltimate = (slotIndex == 8)
            local cost, mechanic = GetAbilityCost(abilityId)

            skills[slotIndex] = {
                id = abilityId,
                name = abilityName,
                is_ultimate = isUltimate,
                cost = cost,
                resource = GetString("SI_COMBATMECHANICTYPE", mechanic),
            }
        end
    end

    return skills
end

local function CaptureAllSkills()
    return {
        front = CaptureActionBar(HOTBAR_CATEGORY_PRIMARY),
        back = CaptureActionBar(HOTBAR_CATEGORY_BACKUP),
    }
end

---------------------------------------------------------------------------
-- Champion Points Capture
---------------------------------------------------------------------------

local function CaptureChampionPoints()
    local cp = {
        total = GetPlayerChampionPointsEarned(),
        warfare = {},
        fitness = {},
        craft = {},
    }

    -- Note: Full CP capture requires iterating through discipline slots
    -- This is a simplified version showing totals

    -- Get slotted stars for each discipline
    -- Warfare (discipline 1) - slots 1-4 on champion bar
    for slot = 1, 4 do
        local starId = GetSlotBoundId(slot, HOTBAR_CATEGORY_CHAMPION)
        if starId and starId > 0 then
            local starName = GetChampionSkillName(starId)
            table.insert(cp.warfare, {
                slot = slot,
                id = starId,
                name = starName,
            })
        end
    end

    -- TODO: Fitness (discipline 2) - slots 5-8 on champion bar
    -- ESO uses different slot indices for each discipline
    -- The exact slot mapping needs verification with the ESO API
    for slot = 5, 8 do
        local starId = GetSlotBoundId(slot, HOTBAR_CATEGORY_CHAMPION)
        if starId and starId > 0 then
            local starName = GetChampionSkillName(starId)
            table.insert(cp.fitness, {
                slot = slot - 4,  -- Normalize to 1-4 for discipline-local slot
                id = starId,
                name = starName,
            })
        end
    end

    -- TODO: Craft (discipline 3) - slots 9-12 on champion bar
    -- Craft CP stars are passive and may not appear in hotbar slots
    -- Full implementation requires GetChampionDisciplineSpentPoints
    -- and iteration through GetNumChampionDisciplineSkills

    return cp
end

---------------------------------------------------------------------------
-- Character Stats Capture
---------------------------------------------------------------------------

local function CaptureCharacterStats()
    local stats = {}

    -- Power pools
    stats.max_health = GetPlayerStat(STAT_HEALTH_MAX)
    stats.max_magicka = GetPlayerStat(STAT_MAGICKA_MAX)
    stats.max_stamina = GetPlayerStat(STAT_STAMINA_MAX)

    -- Damage stats
    stats.weapon_damage = GetPlayerStat(STAT_WEAPON_POWER)
    stats.spell_damage = GetPlayerStat(STAT_SPELL_POWER)
    stats.weapon_critical = GetPlayerStat(STAT_CRITICAL_STRIKE)
    stats.spell_critical = GetPlayerStat(STAT_SPELL_CRITICAL)
    stats.critical_damage = GetPlayerStat(STAT_CRITICAL_BONUS)

    -- Penetration
    stats.physical_penetration = GetPlayerStat(STAT_PHYSICAL_PENETRATION)
    stats.spell_penetration = GetPlayerStat(STAT_SPELL_PENETRATION)

    -- Resistances
    stats.physical_resistance = GetPlayerStat(STAT_PHYSICAL_RESIST)
    stats.spell_resistance = GetPlayerStat(STAT_SPELL_RESIST)

    -- Recovery
    stats.health_recovery = GetPlayerStat(STAT_HEALTH_REGEN_COMBAT)
    stats.magicka_recovery = GetPlayerStat(STAT_MAGICKA_REGEN_COMBAT)
    stats.stamina_recovery = GetPlayerStat(STAT_STAMINA_REGEN_COMBAT)

    return stats
end

---------------------------------------------------------------------------
-- Full Snapshot
---------------------------------------------------------------------------

local function CreateBuildSnapshot()
    local gear, sets = CaptureEquippedGear()

    local snapshot = {
        timestamp = addon:GetTimestamp(),

        -- Character info
        character = {
            name = GetUnitName("player"),
            class = GetClassName(GetUnitClassId("player")),
            class_id = GetUnitClassId("player"),
            subclass = nil, -- TODO: Detect subclass from skill bars
            race = GetRaceName(GetUnitRaceId("player")),
            race_id = GetUnitRaceId("player"),
            level = GetUnitLevel("player"),
            cp_level = GetPlayerChampionPointsEarned(),
            alliance = GetString("SI_ALLIANCE", GetUnitAlliance("player")),
        },

        -- Equipment
        gear = gear,
        sets = sets,

        -- Skills
        skills = CaptureAllSkills(),

        -- Champion points
        champion_points = CaptureChampionPoints(),

        -- Stats
        stats = CaptureCharacterStats(),
    }

    return snapshot
end

---------------------------------------------------------------------------
-- Subclass Detection
---------------------------------------------------------------------------

local function DetectSubclass(skills)
    -- Analyze slotted skills to detect if player is using skills from another class
    -- This is a simplified implementation - full version would check skill line origins

    -- For now, return nil (no subclass detected)
    -- TODO: Implement full subclass detection based on skill ability IDs
    return nil
end

---------------------------------------------------------------------------
-- Event Handlers
---------------------------------------------------------------------------

function BuildSnapshot:OnEquipmentChanged(slotIndex)
    if not state.initialized then return end

    -- Debounce updates
    if not state.pendingUpdate then
        state.pendingUpdate = true
        zo_callLater(function()
            self:CaptureFullSnapshot()
            state.pendingUpdate = false
        end, 500)
    end

    -- Only format debug string when verbose logging is enabled
    if addon.savedVars and addon.savedVars.settings.verboseLogging then
        addon:Debug("Equipment changed: slot %d", slotIndex)
    end
end

function BuildSnapshot:OnSkillChanged()
    if not state.initialized then return end

    addon:Debug("Skill changed")
end

function BuildSnapshot:OnActionBarChanged(slotIndex)
    if not state.initialized then return end

    -- Debounce updates
    if not state.pendingUpdate then
        state.pendingUpdate = true
        zo_callLater(function()
            self:CaptureFullSnapshot()
            state.pendingUpdate = false
        end, 500)
    end

    -- Only format debug string when verbose logging is enabled
    if addon.savedVars and addon.savedVars.settings.verboseLogging then
        addon:Debug("Action bar changed: slot %d", slotIndex)
    end
end

---------------------------------------------------------------------------
-- Public API
---------------------------------------------------------------------------

function BuildSnapshot:Initialize()
    if state.initialized then return end

    state.initialized = true
    addon:Debug("BuildSnapshot initialized")
end

function BuildSnapshot:CaptureFullSnapshot()
    if not state.initialized then
        addon:Error("BuildSnapshot not initialized")
        return nil
    end

    state.currentBuild = CreateBuildSnapshot()
    state.lastSnapshotTime = GetCurrentTime()

    -- Store in saved variables
    if addon.savedVars then
        addon.savedVars.currentBuild = state.currentBuild

        -- Add to pending sync
        table.insert(addon.savedVars.pendingSync.builds, {
            timestamp = state.currentBuild.timestamp,
            build = state.currentBuild,
        })
    end

    addon:Debug("Build snapshot captured")
    return state.currentBuild
end

function BuildSnapshot:GetCurrentBuild()
    return state.currentBuild
end

function BuildSnapshot:GetEquippedSets()
    if state.currentBuild and state.currentBuild.sets then
        local setNames = {}
        for _, setInfo in ipairs(state.currentBuild.sets) do
            table.insert(setNames, setInfo.name)
        end
        return setNames
    end
    return {}
end

function BuildSnapshot:GetSlottedSkills()
    if state.currentBuild and state.currentBuild.skills then
        return state.currentBuild.skills
    end
    return {}
end

function BuildSnapshot:GetStats()
    if state.currentBuild and state.currentBuild.stats then
        return state.currentBuild.stats
    end
    return {}
end

function BuildSnapshot:PrintSummary()
    local build = state.currentBuild
    if not build then
        addon:Info("No build snapshot available")
        return
    end

    addon:Info("--- Build Summary ---")
    addon:Info("Character: %s (%s %s)",
        build.character.name,
        build.character.race,
        build.character.class)
    addon:Info("Level: %d | CP: %d",
        build.character.level,
        build.character.cp_level)

    if build.sets then
        local setList = {}
        for _, setInfo in ipairs(build.sets) do
            table.insert(setList, string.format("%s (%d)", setInfo.name, setInfo.pieces))
        end
        addon:Info("Sets: %s", table.concat(setList, ", "))
    end

    if build.stats then
        addon:Info("Stats: WD %d | SD %d | Max Health %d",
            build.stats.weapon_damage or 0,
            build.stats.spell_damage or 0,
            build.stats.max_health or 0)
    end
end
