# ESO Addon UI/UX Best Practices

> Guidelines for creating ESO addons that are consistent, accessible, and harmonize with other addons.

---

## 1. Color Design

### DarkUI Compatibility
Most ESO players use DarkUI or similar theming addons. Design for dark backgrounds.

```lua
-- BAD: Pure whites and bright colors
local COLORS = {
    text = { 1.0, 1.0, 1.0, 1.0 },     -- Too bright
    dps = { 1.0, 0.0, 0.0, 1.0 },      -- Neon red
}

-- GOOD: Softer, muted colors
local COLORS = {
    text = { 0.9, 0.9, 0.9, 1.0 },     -- Off-white
    dps = { 0.9, 0.35, 0.35, 1.0 },    -- Softer red
}
```

### Standard Color Palette
| Purpose | RGB Values | Notes |
|---------|-----------|-------|
| Background | 0.05, 0.05, 0.05, 0.85 | Dark, slightly transparent |
| Border | 0.35, 0.35, 0.35, 1.0 | Subtle, not prominent |
| Title/Gold | 0.85, 0.70, 0.0, 1.0 | ESO gold, muted |
| Text | 0.9, 0.9, 0.9, 1.0 | Off-white, easy to read |
| Dim/Label | 0.55, 0.55, 0.55, 1.0 | Secondary information |
| Damage/Red | 0.9, 0.35, 0.35, 1.0 | Combat damage |
| Healing/Green | 0.35, 0.85, 0.35, 1.0 | Healing output |
| Special/Purple | 0.55, 0.3, 0.85, 1.0 | Recommendations, buffs |
| Warning/Orange | 0.9, 0.55, 0.2, 1.0 | Warnings, damage taken |

---

## 2. Window Management

### Standard Behaviors
```lua
-- Make windows movable but clampable
window:SetMouseEnabled(true)
window:SetMovable(true)
window:SetClampedToScreen(true)

-- Save position on move
window:SetHandler("OnMoveStop", function()
    savedVars.uiPosition = { x = window:GetLeft(), y = window:GetTop() }
end)
```

### Lock/Unlock Pattern
Provide `/addon lock` and `/addon unlock` slash commands:
```lua
function UI:Lock()
    window:SetMovable(false)
    savedVars.uiLocked = true
end

function UI:Unlock()
    window:SetMovable(true)
    savedVars.uiLocked = false
end
```

### Reset Position
Always provide a way to reset UI position:
```lua
function UI:ResetPosition()
    window:ClearAnchors()
    window:SetAnchor(TOPLEFT, GuiRoot, TOPLEFT, DEFAULT_X, DEFAULT_Y)
    savedVars.uiPosition = { x = DEFAULT_X, y = DEFAULT_Y }
end
```

---

## 3. Collapsed/Expanded Views

### Default Collapsed
Start minimal to avoid screen clutter:
```lua
local state = {
    expanded = false,  -- Default collapsed
}

-- Allow expansion via button or slash command
function UI:ToggleExpanded()
    state.expanded = not state.expanded
    UpdateWindowSize()
end
```

### Expand Button Pattern
Use `+` / `-` indicators:
```lua
expandButton:SetText(state.expanded and "-" or "+")
expandButton:SetHandler("OnClicked", function()
    UI:ToggleExpanded()
end)
```

---

## 4. Slash Commands (Console Accessibility)

### Required Commands
Every addon should support these commands for gamepad/console users:

| Command | Purpose |
|---------|---------|
| `/addon toggle` | Show/hide UI |
| `/addon expand` | Expand to detailed view |
| `/addon collapse` | Collapse to minimal view |
| `/addon lock` | Lock position |
| `/addon unlock` | Unlock for repositioning |
| `/addon reset` | Reset to defaults |
| `/addon help` | Show available commands |

### Implementation Pattern
```lua
SLASH_COMMANDS["/myaddon"] = function(args)
    local cmd = string.lower(args or "")

    if cmd == "toggle" then
        MyAddon.UI:Toggle()
    elseif cmd == "expand" then
        MyAddon.UI:SetExpanded(true)
    elseif cmd == "collapse" then
        MyAddon.UI:SetExpanded(false)
    elseif cmd == "lock" then
        MyAddon.UI:Lock()
    elseif cmd == "unlock" then
        MyAddon.UI:Unlock()
    elseif cmd == "reset" then
        MyAddon.UI:ResetPosition()
    elseif cmd == "help" or cmd == "" then
        d("Usage: /myaddon <command>")
        d("  toggle, expand, collapse, lock, unlock, reset")
    end
end
```

---

## 5. SavedVariables Structure

### Account-Wide vs Per-Character
```lua
-- Account-wide settings (theme, preferences)
local accountDefaults = {
    theme = "dark",
    uiScale = 1.0,
}

-- Per-character settings (position, visibility)
local charDefaults = {
    uiPosition = { x = 100, y = 100 },
    showUI = true,
    expandedView = false,
}

-- Initialize with ZO_SavedVars
function Initialize()
    -- Use NewCharacterIdSettings (NOT New - breaks on rename)
    addon.charVars = ZO_SavedVars:NewCharacterIdSettings(
        "MyAddonSV", 1, nil, charDefaults
    )
    addon.accountVars = ZO_SavedVars:NewAccountWide(
        "MyAddonSV", 1, nil, accountDefaults
    )
end
```

### What Goes Where?
| Setting Type | Storage | Example |
|--------------|---------|---------|
| Position | Per-character | Window location |
| Visibility | Per-character | Show/hide state |
| Theme/Colors | Account-wide | Dark/light mode |
| Scale | Account-wide | UI scaling |
| Features | Account-wide | Enable/disable features |

---

## 6. LibAddonMenu Settings Panel

### Basic Setup
```lua
-- Access via global (NOT LibStub)
local LAM = LibAddonMenu2

function CreateSettingsPanel()
    local panelData = {
        type = "panel",
        name = "My Addon",
        author = "@YourName",
        version = "1.0.0",
        registerForRefresh = true,
    }

    LAM:RegisterAddonPanel("MyAddonPanel", panelData)
    LAM:RegisterOptionControls("MyAddonPanel", optionsData)
end
```

### Recommended Controls
```lua
local optionsData = {
    -- Header
    { type = "header", name = "Display Settings" },

    -- Checkbox
    {
        type = "checkbox",
        name = "Show UI",
        getFunc = function() return savedVars.showUI end,
        setFunc = function(v) savedVars.showUI = v; UpdateUI() end,
    },

    -- Slider
    {
        type = "slider",
        name = "UI Scale",
        min = 0.5, max = 2.0, step = 0.1,
        getFunc = function() return savedVars.uiScale end,
        setFunc = function(v) savedVars.uiScale = v; UpdateUI() end,
    },

    -- Dropdown
    {
        type = "dropdown",
        name = "Theme",
        choices = {"Dark", "Light", "Gold"},
        getFunc = function() return savedVars.theme end,
        setFunc = function(v) savedVars.theme = v; ApplyTheme() end,
    },

    -- Color picker
    {
        type = "colorpicker",
        name = "Title Color",
        getFunc = function() return unpack(savedVars.titleColor) end,
        setFunc = function(r,g,b,a) savedVars.titleColor = {r,g,b,a}; UpdateUI() end,
    },
}
```

---

## 7. Font Usage

### Standard ESO Fonts
Use built-in fonts for consistency:

| Font | Use Case |
|------|----------|
| `ZoFontGameSmall` | Secondary info, tooltips |
| `ZoFontGameMedium` | Main content |
| `ZoFontGameBold` | Headers, important values |
| `ZoFontGameLarge` | Primary metrics |
| `ZoFontWinH1` | Window titles |

```lua
label:SetFont("ZoFontGameMedium")  -- Primary text
header:SetFont("ZoFontGameBold")   -- Headers
```

### Avoid Custom Fonts
Custom fonts cause compatibility issues and require font file management.

---

## 8. Performance Guidelines

### Avoid OnUpdate
Never use `OnUpdate` for metrics - use events instead:
```lua
-- BAD: Runs every frame
window:SetHandler("OnUpdate", UpdateMetrics)

-- GOOD: Event-driven updates
EVENT_MANAGER:RegisterForUpdate(name, 500, UpdateMetrics)  -- Every 500ms
```

### Minimize Combat Event Work
```lua
-- Filter events at registration
EVENT_MANAGER:RegisterForEvent(name, EVENT_COMBAT_EVENT, OnCombat)
EVENT_MANAGER:AddFilterForEvent(name, EVENT_COMBAT_EVENT,
    REGISTER_FILTER_SOURCE_COMBAT_UNIT_TYPE, COMBAT_UNIT_TYPE_PLAYER)
```

### Batch Updates
```lua
-- Accumulate changes, update once per interval
local pendingUpdate = false

function QueueUpdate()
    if not pendingUpdate then
        pendingUpdate = true
        zo_callLater(function()
            DoActualUpdate()
            pendingUpdate = false
        end, 100)
    end
end
```

---

## 9. Console Compatibility (June 2025+)

### Critical Requirements
- **File extension**: Use `.addon` (not just `.txt`)
- **Case sensitivity**: PlayStation uses case-sensitive filesystem
- **No mouse dependence**: All features accessible via slash commands
- **File limit**: Maximum 500 files per addon

### Testing Checklist
- [ ] All features work via slash commands
- [ ] Manifest uses `.addon` extension
- [ ] File references match exact case
- [ ] No more than 500 files

---

## 10. Accessibility

### Text-Based Design
Use text labels, not just icons:
```lua
-- BAD: Icon only
button:SetTexture("icon.dds")

-- GOOD: Text + optional icon
button:SetText("Expand")
```

### Color Contrast
Ensure sufficient contrast between text and background:
- Minimum contrast ratio: 4.5:1 for normal text
- Off-white (0.9, 0.9, 0.9) on dark (0.1, 0.1, 0.1) = good

### Scalable UI
```lua
function UI:SetScale(scale)
    window:SetScale(math.max(0.5, math.min(2.0, scale)))
    savedVars.uiScale = scale
end
```

---

## 11. Testing with Other Addons

### DarkUI Test
1. Install DarkUI
2. Enable all theme options
3. Verify your addon looks good
4. Check text readability

### Bandit's UI Test
1. Install Bandit's UI
2. Verify no conflicts
3. Check window layering

### Common Conflicts
- Window z-ordering (use `DT_HIGH` draw tier)
- Namespace collisions (prefix all controls uniquely)
- Event name conflicts (use addon name prefix)

---

## Quick Reference

### Control Naming
```lua
-- Always prefix with addon name
local control = WINDOW_MANAGER:CreateControl("MyAddon_MainWindow", parent, CT_TOPLEVELCONTROL)
local label = WINDOW_MANAGER:CreateControl("MyAddon_DPSLabel", parent, CT_LABEL)
```

### Draw Layers
```lua
window:SetDrawLayer(DL_OVERLAY)  -- Above game elements
window:SetDrawTier(DT_HIGH)      -- Above most UI
```

### Fragment Integration
```lua
-- Respect HUD fade
local fragment = ZO_HUDFadeSceneFragment:New(window)
HUD_SCENE:AddFragment(fragment)
HUD_UI_SCENE:AddFragment(fragment)
```

---

*Last updated: February 2026 | ESO Update 48*
