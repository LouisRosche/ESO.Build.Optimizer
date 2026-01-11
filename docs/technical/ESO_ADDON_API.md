# ESO Addon API Reference

> **Last Updated**: January 2026
> **API Version**: 101047 (ESO 11.0.0 "Seasons of the Worm Cult Part 1")
> **Source**: [ESOUI Wiki](https://wiki.esoui.com/Main_Page), [UESP ESO Data](https://esoapi.uesp.net/)

---

## Overview

ESO uses **Lua 5.1** (Havok Script variant). Addons cannot make network requests - all sync must happen via SavedVariables files read by external applications.

## Key Documentation Sources

| Resource | URL | Description |
|----------|-----|-------------|
| ESOUI Wiki | https://wiki.esoui.com/Main_Page | Community-maintained API docs |
| ESOUI API | https://wiki.esoui.com/API | Function reference by category |
| APIVersion History | https://wiki.esoui.com/APIVersion | API version changelog |
| ESOUI GitHub | https://github.com/esoui/esoui | Official UI source code |
| UESP ESO Data | https://esoapi.uesp.net/ | Extracted game data |
| ZOS API Updates | https://www.esoui.com/forums/forumdisplay.php?f=166 | Official patch notes |

## Combat Events (Critical for our addon)

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
ACTION_RESULT_DAMAGE = 1
ACTION_RESULT_CRITICAL_DAMAGE = 2
ACTION_RESULT_DOT_TICK = 3
ACTION_RESULT_DOT_TICK_CRITICAL = 4
ACTION_RESULT_HEAL = 16
ACTION_RESULT_CRITICAL_HEAL = 17
ACTION_RESULT_HOT_TICK = 18
ACTION_RESULT_HOT_TICK_CRITICAL = 19
ACTION_RESULT_BLOCKED_DAMAGE = 35
ACTION_RESULT_DAMAGE_SHIELDED = 116
ACTION_RESULT_INTERRUPT = 81
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
```

## Unit Information Functions

```lua
-- Player info
GetUnitName("player")
GetUnitLevel("player")
GetUnitEffectiveChampionPoints("player")
GetUnitClass("player")
GetUnitRace("player")
GetUnitPower("player", POWERTYPE_HEALTH)
GetUnitPower("player", POWERTYPE_MAGICKA)
GetUnitPower("player", POWERTYPE_STAMINA)
GetUnitPower("player", POWERTYPE_ULTIMATE)

-- Boss detection
MAX_BOSSES = 12
DoesUnitExist("boss1")
IsUnitDead("boss1")
GetUnitName("boss1")

-- Combat state
IsUnitInCombat("player")
```

## Equipment/Build Functions

```lua
-- Equipped items
GetItemLink(BAG_WORN, slotIndex, LINK_STYLE_DEFAULT)
GetItemInfo(BAG_WORN, slotIndex)

-- Slot indices (BAG_WORN):
EQUIP_SLOT_HEAD = 0
EQUIP_SLOT_CHEST = 2
EQUIP_SLOT_SHOULDERS = 3
EQUIP_SLOT_WAIST = 6
EQUIP_SLOT_LEGS = 8
EQUIP_SLOT_FEET = 9
EQUIP_SLOT_HAND = 16
EQUIP_SLOT_MAIN_HAND = 4
EQUIP_SLOT_OFF_HAND = 5
EQUIP_SLOT_BACKUP_MAIN = 20
EQUIP_SLOT_BACKUP_OFF = 21
EQUIP_SLOT_NECK = 1
EQUIP_SLOT_RING1 = 11
EQUIP_SLOT_RING2 = 12

-- Active abilities
GetSlotBoundId(slotIndex, hotbarCategory)
GetSlotName(slotIndex, hotbarCategory)
-- HOTBAR_CATEGORY_PRIMARY = 0, HOTBAR_CATEGORY_BACKUP = 1
```

## SavedVariables

```lua
-- Addon manifest (.txt file)
## SavedVariables: MyAddonSavedVars

-- In Lua code
MyAddonSavedVars = MyAddonSavedVars or {}
MyAddonSavedVars.runs = MyAddonSavedVars.runs or {}

-- Data persists on:
-- 1. /reloadui
-- 2. Zone change
-- 3. Logout
-- NOT during loading screens
```

## UI Creation

```lua
-- Create control
local window = WINDOW_MANAGER:CreateTopLevelWindow("MyAddonWindow")
window:SetDimensions(300, 200)
window:SetAnchor(CENTER, GuiRoot, CENTER, 0, 0)
window:SetHidden(false)

-- Create label
local label = WINDOW_MANAGER:CreateControl("MyAddonLabel", window, CT_LABEL)
label:SetFont("ZoFontWinH2")
label:SetText("Hello World")
label:SetAnchor(CENTER, window, CENTER, 0, 0)

-- Register fragment for scene management
SCENE_MANAGER:RegisterTopLevelWindow(window)
```

## Event Registration Best Practices

```lua
-- GOOD: Namespace events
local ADDON_NAME = "ESOBuildOptimizer"
EVENT_MANAGER:RegisterForEvent(ADDON_NAME, EVENT_COMBAT_EVENT, OnCombatEvent)

-- Unregister when not needed
EVENT_MANAGER:UnregisterForEvent(ADDON_NAME, EVENT_COMBAT_EVENT)

-- Use filters to reduce callback frequency
EVENT_MANAGER:AddFilterForEvent(ADDON_NAME, EVENT_COMBAT_EVENT,
    REGISTER_FILTER_SOURCE_COMBAT_UNIT_TYPE, COMBAT_UNIT_TYPE_PLAYER)
```

## Performance Guidelines

1. **Minimize global lookups** - Cache frequently accessed globals in locals
2. **Use event filters** - Reduce callback frequency
3. **Batch UI updates** - Don't update every frame
4. **Avoid string concatenation in loops** - Use table.concat
5. **Profile with /script** - Test performance in-game

## API Update Protocol

When ESO patches:
1. Check https://wiki.esoui.com/APIVersion for version bump
2. Review ESOUI forum "Tutorials & Other Helpful Info" for patch notes
3. Test addon functionality
4. Update API version in addon manifest if required

---

*This document should be refreshed after each ESO quarterly update.*
