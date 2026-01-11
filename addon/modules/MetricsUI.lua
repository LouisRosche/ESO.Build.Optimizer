--[[
    ESO Build Optimizer - Metrics UI Module

    Provides a simple in-game display for:
    - Real-time DPS/HPS
    - Buff uptimes
    - Encounter summary

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

local UI_DIMENSIONS = {
    width = 200,
    height = 120,
}

local COLORS = {
    background = { 0.1, 0.1, 0.1, 0.8 },
    border = { 0.4, 0.4, 0.4, 1.0 },
    title = { 1.0, 0.82, 0.0, 1.0 },    -- Gold
    dps = { 1.0, 0.3, 0.3, 1.0 },       -- Red
    hps = { 0.3, 1.0, 0.3, 1.0 },       -- Green
    text = { 1.0, 1.0, 1.0, 1.0 },      -- White
    dim = { 0.6, 0.6, 0.6, 1.0 },       -- Gray
}

---------------------------------------------------------------------------
-- State
---------------------------------------------------------------------------

local state = {
    initialized = false,
    visible = false,
    locked = false,

    -- UI elements
    window = nil,
    labels = {},

    -- Current metrics
    dps = 0,
    hps = 0,
    hits = 0,
    crits = 0,

    -- Last encounter summary
    lastEncounter = nil,
}

---------------------------------------------------------------------------
-- UI Creation
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

local function CreateMainWindow()
    local window = WINDOW_MANAGER:CreateTopLevelWindow(UI_NAMESPACE)

    local savedPos = addon.savedVars and addon.savedVars.settings.uiPosition or DEFAULT_POSITION
    local scale = addon.savedVars and addon.savedVars.settings.uiScale or 1.0

    window:SetDimensions(UI_DIMENSIONS.width, UI_DIMENSIONS.height)
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
            local x, y = window:GetScreenRect()
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
    bg:SetEdgeTexture("", 1, 1, 1)
    return bg
end

local function CreateUIElements()
    local window = CreateMainWindow()
    state.window = window

    -- Background
    CreateBackground(window)

    -- Title bar
    local title = CreateLabel(window, UI_NAMESPACE .. "_Title",
        TOPLEFT, 8, 8, UI_DIMENSIONS.width - 16, 20, TEXT_ALIGN_CENTER)
    title:SetFont("ZoFontGameBold")
    title:SetColor(unpack(COLORS.title))
    title:SetText("ESO Build Optimizer")
    state.labels.title = title

    -- DPS Label
    local dpsLabel = CreateLabel(window, UI_NAMESPACE .. "_DPSLabel",
        TOPLEFT, 8, 35, 40, 20)
    dpsLabel:SetColor(unpack(COLORS.dim))
    dpsLabel:SetText("DPS:")

    local dpsValue = CreateLabel(window, UI_NAMESPACE .. "_DPSValue",
        TOPLEFT, 50, 35, 100, 20)
    dpsValue:SetColor(unpack(COLORS.dps))
    dpsValue:SetText("0")
    state.labels.dps = dpsValue

    -- HPS Label
    local hpsLabel = CreateLabel(window, UI_NAMESPACE .. "_HPSLabel",
        TOPLEFT, 8, 55, 40, 20)
    hpsLabel:SetColor(unpack(COLORS.dim))
    hpsLabel:SetText("HPS:")

    local hpsValue = CreateLabel(window, UI_NAMESPACE .. "_HPSValue",
        TOPLEFT, 50, 55, 100, 20)
    hpsValue:SetColor(unpack(COLORS.hps))
    hpsValue:SetText("0")
    state.labels.hps = hpsValue

    -- Crit Rate Label
    local critLabel = CreateLabel(window, UI_NAMESPACE .. "_CritLabel",
        TOPLEFT, 8, 75, 40, 20)
    critLabel:SetColor(unpack(COLORS.dim))
    critLabel:SetText("Crit:")

    local critValue = CreateLabel(window, UI_NAMESPACE .. "_CritValue",
        TOPLEFT, 50, 75, 100, 20)
    critValue:SetColor(unpack(COLORS.text))
    critValue:SetText("0%")
    state.labels.crit = critValue

    -- Status Label
    local statusLabel = CreateLabel(window, UI_NAMESPACE .. "_Status",
        TOPLEFT, 8, 95, UI_DIMENSIONS.width - 16, 20, TEXT_ALIGN_CENTER)
    statusLabel:SetColor(unpack(COLORS.dim))
    statusLabel:SetText("Idle")
    state.labels.status = statusLabel

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

local function UpdateDisplay()
    if not state.visible or not state.window then return end

    -- Update DPS
    if state.labels.dps then
        state.labels.dps:SetText(FormatNumber(state.dps))
    end

    -- Update HPS
    if state.labels.hps then
        state.labels.hps:SetText(FormatNumber(state.hps))
    end

    -- Update Crit Rate
    if state.labels.crit then
        local critRate = state.hits > 0 and (state.crits / state.hits * 100) or 0
        state.labels.crit:SetText(string.format("%.1f%%", critRate))
    end

    -- Update Status
    if state.labels.status then
        if addon.CombatTracker and addon.CombatTracker:IsInEncounter() then
            state.labels.status:SetText("In Combat")
            state.labels.status:SetColor(unpack(COLORS.dps))
        else
            state.labels.status:SetText("Idle")
            state.labels.status:SetColor(unpack(COLORS.dim))
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

    UpdateDisplay()
end

function MetricsUI:OnEncounterEnd(runData)
    state.lastEncounter = runData

    -- Reset real-time metrics
    state.dps = 0
    state.hps = 0
    state.hits = 0
    state.crits = 0

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

---------------------------------------------------------------------------
-- Public API
---------------------------------------------------------------------------

function MetricsUI:Initialize()
    if state.initialized then return end

    CreateUIElements()

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
    state.lastEncounter = nil
    UpdateDisplay()
end
