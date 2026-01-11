--[[
    ESO Build Optimizer - Metrics UI Module

    Provides a simple in-game display for:
    - Real-time DPS/HPS (collapsed view)
    - Expanded view with crit, uptime, deaths, etc.
    - Skill recommendation display
    - Auto-display settings

    Author: ESO Build Optimizer Team
    Version: 0.1.0
]]--

---------------------------------------------------------------------------
-- Module Setup
---------------------------------------------------------------------------

local addon = ESOBuildOptimizer
local MetricsUI = {}
addon.MetricsUI = MetricsUI

---------------------------------------------------------------------------
-- Constants
---------------------------------------------------------------------------

local UI_NAMESPACE = "ESOBuildOptimizer_MetricsUI"

local DEFAULT_POSITION = {
    x = 100,
    y = 100,
}

-- Dimensions for collapsed and expanded states
local UI_DIMENSIONS = {
    collapsed = {
        width = 180,
        height = 60,
    },
    expanded = {
        width = 220,
        height = 200,
    },
}

local COLORS = {
    background = { 0.1, 0.1, 0.1, 0.8 },
    border = { 0.4, 0.4, 0.4, 1.0 },
    title = { 1.0, 0.82, 0.0, 1.0 },    -- Gold
    dps = { 1.0, 0.3, 0.3, 1.0 },       -- Red
    hps = { 0.3, 1.0, 0.3, 1.0 },       -- Green
    text = { 1.0, 1.0, 1.0, 1.0 },      -- White
    dim = { 0.6, 0.6, 0.6, 1.0 },       -- Gray
    button = { 0.3, 0.3, 0.3, 1.0 },    -- Button background
    buttonHover = { 0.5, 0.5, 0.5, 1.0 },
    recommendation = { 0.6, 0.2, 1.0, 1.0 },  -- Purple for skill recs
    warning = { 1.0, 0.6, 0.2, 1.0 },   -- Orange for warnings
}

---------------------------------------------------------------------------
-- State
---------------------------------------------------------------------------

local state = {
    initialized = false,
    visible = false,
    locked = false,
    expanded = false,      -- Collapsed by default
    autoDisplay = true,    -- Auto-show during combat (opt-in default)

    -- UI elements
    window = nil,
    background = nil,
    expandButton = nil,
    labels = {},
    expandedPanel = nil,

    -- Current metrics
    dps = 0,
    hps = 0,
    hits = 0,
    crits = 0,

    -- Extended metrics
    damageDone = 0,
    healingDone = 0,
    damageTaken = 0,
    deaths = 0,
    buffUptime = 0,

    -- Skill recommendation
    skillRecommendation = nil,
    skillRecommendationReason = "",

    -- Last encounter summary
    lastEncounter = nil,
}

---------------------------------------------------------------------------
-- UI Creation - Helper Functions
---------------------------------------------------------------------------

local function CreateLabel(parent, name, anchor, offsetX, offsetY, width, height, align)
    local label = WINDOW_MANAGER:CreateControl(name, parent, CT_LABEL)
    label:SetFont("ZoFontGameMedium")
    label:SetColor(unpack(COLORS.text))
    label:SetHorizontalAlignment(align or TEXT_ALIGN_LEFT)
    label:SetVerticalAlignment(TEXT_ALIGN_CENTER)
    label:SetDimensions(width, height)
    label:SetAnchor(anchor, parent, anchor, offsetX, offsetY)
    return label
end

local function CreateButton(parent, name, anchor, anchorTo, anchorToPoint, offsetX, offsetY, width, height, text)
    local button = WINDOW_MANAGER:CreateControl(name, parent, CT_BUTTON)
    button:SetDimensions(width, height)
    button:SetAnchor(anchor, anchorTo, anchorToPoint, offsetX, offsetY)
    button:SetFont("ZoFontGameBold")
    button:SetNormalFontColor(unpack(COLORS.text))
    button:SetMouseOverFontColor(unpack(COLORS.title))
    button:SetText(text)

    -- Button background
    local bg = WINDOW_MANAGER:CreateControl(name .. "_BG", button, CT_BACKDROP)
    bg:SetAnchorFill(button)
    bg:SetCenterColor(unpack(COLORS.button))
    bg:SetEdgeColor(unpack(COLORS.border))
    -- Note: SetEdgeTexture with empty string removed - can cause issues
    button.bg = bg

    -- Hover effect
    button:SetHandler("OnMouseEnter", function()
        bg:SetCenterColor(unpack(COLORS.buttonHover))
    end)
    button:SetHandler("OnMouseExit", function()
        bg:SetCenterColor(unpack(COLORS.button))
    end)

    return button
end

---------------------------------------------------------------------------
-- UI Creation - Main Window
---------------------------------------------------------------------------

local function CreateMainWindow()
    -- Check if window already exists to prevent duplicates
    if WINDOW_MANAGER:GetControlByName(UI_NAMESPACE) then
        return WINDOW_MANAGER:GetControlByName(UI_NAMESPACE)
    end

    local window = WINDOW_MANAGER:CreateTopLevelWindow(UI_NAMESPACE)

    local savedPos = addon.savedVars and addon.savedVars.settings.uiPosition or DEFAULT_POSITION
    local scale = addon.savedVars and addon.savedVars.settings.uiScale or 1.0
    local dims = state.expanded and UI_DIMENSIONS.expanded or UI_DIMENSIONS.collapsed

    window:SetDimensions(dims.width, dims.height)
    window:SetAnchor(TOPLEFT, GuiRoot, TOPLEFT, savedPos.x, savedPos.y)
    window:SetScale(scale)
    window:SetMouseEnabled(true)
    window:SetMovable(true)
    window:SetClampedToScreen(true)
    window:SetHidden(true)
    window:SetDrawLayer(DL_OVERLAY)
    window:SetDrawTier(DT_HIGH)

    -- Register for drag events to save position
    window:SetHandler("OnMoveStop", function()
        if addon.savedVars then
            local x, y = window:GetLeft(), window:GetTop()
            addon.savedVars.settings.uiPosition = { x = x, y = y }
        end
    end)

    return window
end

local function CreateBackground(parent)
    local bg = WINDOW_MANAGER:CreateControl(UI_NAMESPACE .. "_BG", parent, CT_BACKDROP)
    bg:SetAnchorFill(parent)
    bg:SetCenterColor(unpack(COLORS.background))
    bg:SetEdgeColor(unpack(COLORS.border))
    -- Note: SetEdgeTexture with empty string removed - can cause issues
    return bg
end

---------------------------------------------------------------------------
-- UI Creation - Collapsed View
---------------------------------------------------------------------------

local function CreateCollapsedView(window)
    -- Title bar with expand button
    local titleRow = WINDOW_MANAGER:CreateControl(UI_NAMESPACE .. "_TitleRow", window, CT_CONTROL)
    titleRow:SetDimensions(UI_DIMENSIONS.collapsed.width - 16, 20)
    titleRow:SetAnchor(TOPLEFT, window, TOPLEFT, 8, 5)

    -- Title label
    local title = CreateLabel(titleRow, UI_NAMESPACE .. "_Title",
        TOPLEFT, 0, 0, UI_DIMENSIONS.collapsed.width - 50, 20, TEXT_ALIGN_LEFT)
    title:SetFont("ZoFontGameBold")
    title:SetColor(unpack(COLORS.title))
    title:SetText("EBO")
    state.labels.title = title

    -- Expand/Collapse button (+/-)
    local expandBtn = CreateButton(titleRow, UI_NAMESPACE .. "_ExpandBtn",
        TOPRIGHT, titleRow, TOPRIGHT, 0, 0, 24, 18, "+")
    expandBtn:SetHandler("OnClicked", function()
        MetricsUI:ToggleExpanded()
    end)
    state.expandButton = expandBtn

    -- DPS Row
    local dpsRow = WINDOW_MANAGER:CreateControl(UI_NAMESPACE .. "_DPSRow", window, CT_CONTROL)
    dpsRow:SetDimensions(UI_DIMENSIONS.collapsed.width - 16, 18)
    dpsRow:SetAnchor(TOPLEFT, window, TOPLEFT, 8, 28)

    local dpsLabel = CreateLabel(dpsRow, UI_NAMESPACE .. "_DPSLabel",
        TOPLEFT, 0, 0, 35, 18)
    dpsLabel:SetColor(unpack(COLORS.dim))
    dpsLabel:SetText("DPS:")

    local dpsValue = CreateLabel(dpsRow, UI_NAMESPACE .. "_DPSValue",
        TOPLEFT, 38, 0, 60, 18)
    dpsValue:SetColor(unpack(COLORS.dps))
    dpsValue:SetText("0")
    state.labels.dps = dpsValue

    -- HPS next to DPS on collapsed view
    local hpsLabel = CreateLabel(dpsRow, UI_NAMESPACE .. "_HPSLabelCollapsed",
        TOPLEFT, 90, 0, 35, 18)
    hpsLabel:SetColor(unpack(COLORS.dim))
    hpsLabel:SetText("HPS:")

    local hpsValue = CreateLabel(dpsRow, UI_NAMESPACE .. "_HPSValueCollapsed",
        TOPLEFT, 125, 0, 50, 18)
    hpsValue:SetColor(unpack(COLORS.hps))
    hpsValue:SetText("0")
    state.labels.hpsCollapsed = hpsValue

    -- Status Row (skill recommendation or status)
    local statusRow = WINDOW_MANAGER:CreateControl(UI_NAMESPACE .. "_StatusRow", window, CT_CONTROL)
    statusRow:SetDimensions(UI_DIMENSIONS.collapsed.width - 16, 18)
    statusRow:SetAnchor(TOPLEFT, window, TOPLEFT, 8, 46)

    local statusLabel = CreateLabel(statusRow, UI_NAMESPACE .. "_StatusCollapsed",
        TOPLEFT, 0, 0, UI_DIMENSIONS.collapsed.width - 16, 18, TEXT_ALIGN_LEFT)
    statusLabel:SetFont("ZoFontGameSmall")
    statusLabel:SetColor(unpack(COLORS.dim))
    statusLabel:SetText("Ready")
    state.labels.statusCollapsed = statusLabel
end

---------------------------------------------------------------------------
-- UI Creation - Expanded View
---------------------------------------------------------------------------

local function CreateExpandedPanel(window)
    local panel = WINDOW_MANAGER:CreateControl(UI_NAMESPACE .. "_ExpandedPanel", window, CT_CONTROL)
    panel:SetDimensions(UI_DIMENSIONS.expanded.width - 16, UI_DIMENSIONS.expanded.height - 65)
    panel:SetAnchor(TOPLEFT, window, TOPLEFT, 8, 65)
    panel:SetHidden(true)
    state.expandedPanel = panel

    local yOffset = 0
    local lineHeight = 18
    local labelWidth = 100
    local valueWidth = 80

    -- Separator line
    local separator = WINDOW_MANAGER:CreateControl(UI_NAMESPACE .. "_Separator", panel, CT_TEXTURE)
    separator:SetDimensions(UI_DIMENSIONS.expanded.width - 20, 1)
    separator:SetAnchor(TOPLEFT, panel, TOPLEFT, 0, yOffset)
    separator:SetColor(unpack(COLORS.border))
    yOffset = yOffset + 5

    -- Crit Rate
    local critLabel = CreateLabel(panel, UI_NAMESPACE .. "_CritLabel",
        TOPLEFT, 0, yOffset, labelWidth, lineHeight)
    critLabel:SetColor(unpack(COLORS.dim))
    critLabel:SetText("Crit Rate:")

    local critValue = CreateLabel(panel, UI_NAMESPACE .. "_CritValue",
        TOPLEFT, labelWidth, yOffset, valueWidth, lineHeight)
    critValue:SetColor(unpack(COLORS.text))
    critValue:SetText("0%")
    state.labels.crit = critValue
    yOffset = yOffset + lineHeight

    -- Total Damage
    local dmgLabel = CreateLabel(panel, UI_NAMESPACE .. "_DmgLabel",
        TOPLEFT, 0, yOffset, labelWidth, lineHeight)
    dmgLabel:SetColor(unpack(COLORS.dim))
    dmgLabel:SetText("Total Damage:")

    local dmgValue = CreateLabel(panel, UI_NAMESPACE .. "_DmgValue",
        TOPLEFT, labelWidth, yOffset, valueWidth, lineHeight)
    dmgValue:SetColor(unpack(COLORS.dps))
    dmgValue:SetText("0")
    state.labels.totalDamage = dmgValue
    yOffset = yOffset + lineHeight

    -- Total Healing
    local healLabel = CreateLabel(panel, UI_NAMESPACE .. "_HealLabel",
        TOPLEFT, 0, yOffset, labelWidth, lineHeight)
    healLabel:SetColor(unpack(COLORS.dim))
    healLabel:SetText("Total Healing:")

    local healValue = CreateLabel(panel, UI_NAMESPACE .. "_HealValue",
        TOPLEFT, labelWidth, yOffset, valueWidth, lineHeight)
    healValue:SetColor(unpack(COLORS.hps))
    healValue:SetText("0")
    state.labels.totalHealing = healValue
    yOffset = yOffset + lineHeight

    -- Damage Taken
    local takenLabel = CreateLabel(panel, UI_NAMESPACE .. "_TakenLabel",
        TOPLEFT, 0, yOffset, labelWidth, lineHeight)
    takenLabel:SetColor(unpack(COLORS.dim))
    takenLabel:SetText("Damage Taken:")

    local takenValue = CreateLabel(panel, UI_NAMESPACE .. "_TakenValue",
        TOPLEFT, labelWidth, yOffset, valueWidth, lineHeight)
    takenValue:SetColor(unpack(COLORS.warning))
    takenValue:SetText("0")
    state.labels.damageTaken = takenValue
    yOffset = yOffset + lineHeight

    -- Deaths
    local deathLabel = CreateLabel(panel, UI_NAMESPACE .. "_DeathLabel",
        TOPLEFT, 0, yOffset, labelWidth, lineHeight)
    deathLabel:SetColor(unpack(COLORS.dim))
    deathLabel:SetText("Deaths:")

    local deathValue = CreateLabel(panel, UI_NAMESPACE .. "_DeathValue",
        TOPLEFT, labelWidth, yOffset, valueWidth, lineHeight)
    deathValue:SetColor(unpack(COLORS.text))
    deathValue:SetText("0")
    state.labels.deaths = deathValue
    yOffset = yOffset + lineHeight + 5

    -- Skill Advisor Section
    local advisorSeparator = WINDOW_MANAGER:CreateControl(UI_NAMESPACE .. "_AdvisorSep", panel, CT_TEXTURE)
    advisorSeparator:SetDimensions(UI_DIMENSIONS.expanded.width - 20, 1)
    advisorSeparator:SetAnchor(TOPLEFT, panel, TOPLEFT, 0, yOffset)
    advisorSeparator:SetColor(unpack(COLORS.border))
    yOffset = yOffset + 5

    local advisorHeader = CreateLabel(panel, UI_NAMESPACE .. "_AdvisorHeader",
        TOPLEFT, 0, yOffset, UI_DIMENSIONS.expanded.width - 20, lineHeight)
    advisorHeader:SetFont("ZoFontGameBold")
    advisorHeader:SetColor(unpack(COLORS.recommendation))
    advisorHeader:SetText("Skill Advisor")
    yOffset = yOffset + lineHeight

    local advisorRec = CreateLabel(panel, UI_NAMESPACE .. "_AdvisorRec",
        TOPLEFT, 0, yOffset, UI_DIMENSIONS.expanded.width - 20, lineHeight * 2)
    advisorRec:SetFont("ZoFontGameSmall")
    advisorRec:SetColor(unpack(COLORS.text))
    advisorRec:SetText("No recommendations")
    advisorRec:SetVerticalAlignment(TEXT_ALIGN_TOP)
    state.labels.skillRecommendation = advisorRec
end

---------------------------------------------------------------------------
-- UI Creation - Settings Panel (optional toggle)
---------------------------------------------------------------------------

local function CreateSettingsRow(window)
    -- Auto-display checkbox row (shown in expanded view only)
    local settingsRow = WINDOW_MANAGER:CreateControl(UI_NAMESPACE .. "_SettingsRow", window, CT_CONTROL)
    settingsRow:SetDimensions(UI_DIMENSIONS.expanded.width - 16, 20)
    settingsRow:SetAnchor(BOTTOMLEFT, window, BOTTOMLEFT, 8, -5)
    settingsRow:SetHidden(true)
    state.settingsRow = settingsRow

    -- Auto-display toggle text
    local autoDisplayLabel = CreateLabel(settingsRow, UI_NAMESPACE .. "_AutoDisplayLabel",
        TOPLEFT, 0, 0, 120, 20)
    autoDisplayLabel:SetFont("ZoFontGameSmall")
    autoDisplayLabel:SetColor(unpack(COLORS.dim))
    autoDisplayLabel:SetText("Auto-show in combat")

    -- Toggle button
    local toggleBtn = CreateButton(settingsRow, UI_NAMESPACE .. "_AutoDisplayToggle",
        TOPRIGHT, settingsRow, TOPRIGHT, 0, 0, 40, 18, "ON")
    toggleBtn:SetHandler("OnClicked", function()
        MetricsUI:ToggleAutoDisplay()
    end)
    state.autoDisplayToggle = toggleBtn
end

---------------------------------------------------------------------------
-- UI Creation - Main Entry Point
---------------------------------------------------------------------------

local function CreateUIElements()
    local window = CreateMainWindow()
    state.window = window

    -- Background
    state.background = CreateBackground(window)

    -- Collapsed view elements
    CreateCollapsedView(window)

    -- Expanded panel elements
    CreateExpandedPanel(window)

    -- Settings row
    CreateSettingsRow(window)

    addon:Debug("UI elements created")
end

---------------------------------------------------------------------------
-- UI Update Functions
---------------------------------------------------------------------------

local function FormatNumber(num)
    if num >= 1000000 then
        return string.format("%.2fM", num / 1000000)
    elseif num >= 1000 then
        return string.format("%.1fK", num / 1000)
    else
        return string.format("%d", num)
    end
end

local function UpdateWindowSize()
    if not state.window then return end

    local dims = state.expanded and UI_DIMENSIONS.expanded or UI_DIMENSIONS.collapsed
    state.window:SetDimensions(dims.width, dims.height)

    -- Update expand button text
    if state.expandButton then
        state.expandButton:SetText(state.expanded and "-" or "+")
    end

    -- Show/hide expanded panel
    if state.expandedPanel then
        state.expandedPanel:SetHidden(not state.expanded)
    end

    -- Show/hide settings row
    if state.settingsRow then
        state.settingsRow:SetHidden(not state.expanded)
    end
end

local function UpdateAutoDisplayButton()
    if state.autoDisplayToggle then
        state.autoDisplayToggle:SetText(state.autoDisplay and "ON" or "OFF")
        if state.autoDisplay then
            state.autoDisplayToggle:SetNormalFontColor(unpack(COLORS.hps))
        else
            state.autoDisplayToggle:SetNormalFontColor(unpack(COLORS.dim))
        end
    end
end

local function UpdateDisplay()
    if not state.visible or not state.window then return end

    -- Update DPS (both views)
    if state.labels.dps then
        state.labels.dps:SetText(FormatNumber(state.dps))
    end

    -- Update HPS (collapsed view)
    if state.labels.hpsCollapsed then
        state.labels.hpsCollapsed:SetText(FormatNumber(state.hps))
    end

    -- Update Crit Rate (expanded only)
    if state.labels.crit then
        local critRate = state.hits > 0 and (state.crits / state.hits * 100) or 0
        state.labels.crit:SetText(string.format("%.1f%%", critRate))
    end

    -- Update Total Damage (expanded only)
    if state.labels.totalDamage then
        state.labels.totalDamage:SetText(FormatNumber(state.damageDone))
    end

    -- Update Total Healing (expanded only)
    if state.labels.totalHealing then
        state.labels.totalHealing:SetText(FormatNumber(state.healingDone))
    end

    -- Update Damage Taken (expanded only)
    if state.labels.damageTaken then
        state.labels.damageTaken:SetText(FormatNumber(state.damageTaken))
    end

    -- Update Deaths (expanded only)
    if state.labels.deaths then
        state.labels.deaths:SetText(tostring(state.deaths))
    end

    -- Update Status (collapsed view)
    if state.labels.statusCollapsed then
        if state.skillRecommendation and state.skillRecommendationReason ~= "" then
            state.labels.statusCollapsed:SetText(state.skillRecommendationReason)
            state.labels.statusCollapsed:SetColor(unpack(COLORS.recommendation))
        elseif addon.CombatTracker and addon.CombatTracker:IsInEncounter() then
            state.labels.statusCollapsed:SetText("In Combat")
            state.labels.statusCollapsed:SetColor(unpack(COLORS.dps))
        else
            state.labels.statusCollapsed:SetText("Ready")
            state.labels.statusCollapsed:SetColor(unpack(COLORS.dim))
        end
    end

    -- Update Skill Recommendation (expanded view)
    if state.labels.skillRecommendation then
        if state.skillRecommendation and state.skillRecommendationReason ~= "" then
            -- Get skill name if available
            local skillName = ""
            if addon.SkillAdvisor then
                local rec, reason = addon.SkillAdvisor:GetCurrentRecommendation()
                if rec then
                    local abilityId = GetSlotBoundId(rec, GetActiveHotbarCategory())
                    if abilityId and abilityId > 0 then
                        skillName = GetAbilityName(abilityId) .. ": "
                    end
                end
            end
            state.labels.skillRecommendation:SetText(skillName .. state.skillRecommendationReason)
            state.labels.skillRecommendation:SetColor(unpack(COLORS.recommendation))
        else
            state.labels.skillRecommendation:SetText("No recommendations")
            state.labels.skillRecommendation:SetColor(unpack(COLORS.dim))
        end
    end
end

---------------------------------------------------------------------------
-- Event Handlers
---------------------------------------------------------------------------

function MetricsUI:UpdateMetrics(dps, hps, hits, crits)
    state.dps = dps or 0
    state.hps = hps or 0
    state.hits = hits or 0
    state.crits = crits or 0

    -- Get extended metrics from CombatTracker
    if addon.CombatTracker then
        local encounter = addon.CombatTracker:GetCurrentEncounter()
        if encounter then
            state.damageDone = encounter.damage.total or 0
            state.healingDone = encounter.healing.total or 0
            state.damageTaken = encounter.damageTaken.total or 0
            state.deaths = encounter.deaths or 0
        end
    end

    UpdateDisplay()
end

function MetricsUI:UpdateSkillRecommendation(slotIndex, reason)
    state.skillRecommendation = slotIndex
    state.skillRecommendationReason = reason or ""
    UpdateDisplay()
end

function MetricsUI:OnEncounterEnd(runData)
    state.lastEncounter = runData

    -- Reset real-time metrics
    state.dps = 0
    state.hps = 0
    state.hits = 0
    state.crits = 0
    state.damageDone = 0
    state.healingDone = 0
    state.damageTaken = 0
    state.deaths = 0
    state.skillRecommendation = nil
    state.skillRecommendationReason = ""

    -- Show summary briefly
    if runData and runData.metrics then
        local metrics = runData.metrics
        addon:Info("Encounter Complete: %d DPS | %d HPS | %.1f%% Crit | %d Deaths",
            metrics.dps or 0,
            metrics.hps or 0,
            (metrics.crit_rate or 0) * 100,
            metrics.deaths or 0
        )
    end

    UpdateDisplay()
end

function MetricsUI:OnCombatStateChanged(inCombat)
    -- Auto-show during combat if enabled
    if state.autoDisplay then
        if inCombat and not state.visible then
            self:Show()
        end
        -- Note: We don't auto-hide on combat end to let player review stats
    end
end

---------------------------------------------------------------------------
-- Public API
---------------------------------------------------------------------------

function MetricsUI:Initialize()
    if state.initialized then return end

    -- Load settings
    if addon.savedVars and addon.savedVars.settings then
        state.expanded = addon.savedVars.settings.expandedView or false
        state.autoDisplay = addon.savedVars.settings.autoDisplayMetrics ~= false  -- Default true
    end

    CreateUIElements()
    UpdateWindowSize()
    UpdateAutoDisplayButton()

    -- Show UI if setting is enabled
    if addon.savedVars and addon.savedVars.settings.showUI then
        self:Show()
    end

    state.initialized = true
    addon:Debug("MetricsUI initialized")
end

function MetricsUI:Show()
    if state.window then
        state.window:SetHidden(false)
        state.visible = true
        UpdateDisplay()
        addon:Debug("UI shown")
    end
end

function MetricsUI:Hide()
    if state.window then
        state.window:SetHidden(true)
        state.visible = false
        addon:Debug("UI hidden")
    end
end

function MetricsUI:Toggle()
    if state.visible then
        self:Hide()
    else
        self:Show()
    end

    -- Save preference
    if addon.savedVars then
        addon.savedVars.settings.showUI = state.visible
    end
end

function MetricsUI:ToggleExpanded()
    state.expanded = not state.expanded
    UpdateWindowSize()

    -- Save preference
    if addon.savedVars then
        addon.savedVars.settings.expandedView = state.expanded
    end

    addon:Debug("UI %s", state.expanded and "expanded" or "collapsed")
end

function MetricsUI:ToggleAutoDisplay()
    state.autoDisplay = not state.autoDisplay
    UpdateAutoDisplayButton()

    -- Save preference
    if addon.savedVars then
        addon.savedVars.settings.autoDisplayMetrics = state.autoDisplay
    end

    addon:Debug("Auto-display %s", state.autoDisplay and "enabled" or "disabled")
end

function MetricsUI:SetExpanded(expanded)
    state.expanded = expanded
    UpdateWindowSize()

    if addon.savedVars then
        addon.savedVars.settings.expandedView = expanded
    end
end

function MetricsUI:SetAutoDisplay(enabled)
    state.autoDisplay = enabled
    UpdateAutoDisplayButton()

    if addon.savedVars then
        addon.savedVars.settings.autoDisplayMetrics = enabled
    end
end

function MetricsUI:IsExpanded()
    return state.expanded
end

function MetricsUI:IsAutoDisplayEnabled()
    return state.autoDisplay
end

function MetricsUI:IsVisible()
    return state.visible
end

function MetricsUI:SetScale(scale)
    if state.window then
        state.window:SetScale(scale)
        if addon.savedVars then
            addon.savedVars.settings.uiScale = scale
        end
    end
end

function MetricsUI:Lock()
    if state.window then
        state.window:SetMovable(false)
        state.locked = true
        if addon.savedVars then
            addon.savedVars.settings.uiLocked = true
        end
    end
end

function MetricsUI:Unlock()
    if state.window then
        state.window:SetMovable(true)
        state.locked = false
        if addon.savedVars then
            addon.savedVars.settings.uiLocked = false
        end
    end
end

function MetricsUI:GetLastEncounter()
    return state.lastEncounter
end

function MetricsUI:Reset()
    state.dps = 0
    state.hps = 0
    state.hits = 0
    state.crits = 0
    state.damageDone = 0
    state.healingDone = 0
    state.damageTaken = 0
    state.deaths = 0
    state.skillRecommendation = nil
    state.skillRecommendationReason = ""
    state.lastEncounter = nil
    UpdateDisplay()
end
