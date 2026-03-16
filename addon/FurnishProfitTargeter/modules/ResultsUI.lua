--[[
    Furnish Profit Targeter - Results UI Module

    Provides a scrollable in-game window displaying the Top N
    velocity-scored furnishing items. Supports sorting, filtering,
    and detailed item tooltips.

    Author: ESO Build Optimizer Team
    Version: 1.0.0
]]--

---------------------------------------------------------------------------
-- Module Setup
---------------------------------------------------------------------------

local FPT = FurnishProfitTargeter
local ResultsUI = {}
FPT.ResultsUI = ResultsUI

---------------------------------------------------------------------------
-- Constants
---------------------------------------------------------------------------

local WINDOW_WIDTH = 520
local WINDOW_HEIGHT = 480
local ROW_HEIGHT = 52
local HEADER_HEIGHT = 40
local PADDING = 8
local MAX_VISIBLE_ROWS = 8

---------------------------------------------------------------------------
-- Local State
---------------------------------------------------------------------------

local window = nil
local rowPool = {}
local currentResults = {}
local isVisible = false
local isDragging = false

---------------------------------------------------------------------------
-- Initialization
---------------------------------------------------------------------------

function ResultsUI:Initialize()
    self:CreateWindow()
    FPT:Debug("ResultsUI initialized")
end

---------------------------------------------------------------------------
-- Window Creation
---------------------------------------------------------------------------

function ResultsUI:CreateWindow()
    -- Main window
    local tlw = WINDOW_MANAGER:CreateTopLevelWindow("FPT_ResultsWindow")
    tlw:SetDimensions(WINDOW_WIDTH, WINDOW_HEIGHT)

    local pos = FPT.savedVars.settings.uiPosition
    tlw:SetAnchor(TOPLEFT, GuiRoot, TOPLEFT, pos.x, pos.y)
    tlw:SetDrawLayer(DL_OVERLAY)
    tlw:SetDrawTier(DT_HIGH)
    tlw:SetMouseEnabled(true)
    tlw:SetMovable(not FPT.savedVars.settings.uiLocked)
    tlw:SetClampedToScreen(true)
    tlw:SetHidden(true)
    tlw:SetHandler("OnMoveStop", function(control)
        local _, _, _, _, offsetX, offsetY = control:GetAnchor(0)
        FPT.savedVars.settings.uiPosition.x = offsetX
        FPT.savedVars.settings.uiPosition.y = offsetY
    end)

    -- Background
    local bg = WINDOW_MANAGER:CreateControl("FPT_ResultsBG", tlw, CT_BACKDROP)
    bg:SetAnchorFill(tlw)
    bg:SetCenterColor(0, 0, 0, 0.85)
    bg:SetEdgeColor(0.6, 0.5, 0.2, 0.9)
    bg:SetEdgeTexture("", 1, 1, 1, 0)

    -- Title bar
    local titleBar = WINDOW_MANAGER:CreateControl("FPT_TitleBar", tlw, CT_LABEL)
    titleBar:SetAnchor(TOPLEFT, tlw, TOPLEFT, PADDING, PADDING)
    titleBar:SetDimensions(WINDOW_WIDTH - 80, 24)
    titleBar:SetFont("ZoFontWinH3")
    titleBar:SetColor(1, 0.84, 0, 1)
    titleBar:SetText("Furnish Profit Targeter")

    -- Close button
    local closeBtn = WINDOW_MANAGER:CreateControl("FPT_CloseBtn", tlw, CT_BUTTON)
    closeBtn:SetAnchor(TOPRIGHT, tlw, TOPRIGHT, -PADDING, PADDING)
    closeBtn:SetDimensions(20, 20)
    closeBtn:SetFont("ZoFontWinH3")
    closeBtn:SetNormalFontColor(1, 0.3, 0.3, 1)
    closeBtn:SetMouseOverFontColor(1, 0.5, 0.5, 1)
    closeBtn:SetText("X")
    closeBtn:SetHandler("OnClicked", function()
        self:Hide()
    end)

    -- Column headers
    local headerY = PADDING + 28

    local headers = {
        { text = "#",        x = PADDING,      width = 24 },
        { text = "Item",     x = PADDING + 28, width = 200 },
        { text = "Margin",   x = 240,          width = 70 },
        { text = "Sales",    x = 314,          width = 50 },
        { text = "V-Score",  x = 368,          width = 80 },
        { text = "ROI",      x = 452,          width = 55 },
    }

    for i, header in ipairs(headers) do
        local label = WINDOW_MANAGER:CreateControl("FPT_Header" .. i, tlw, CT_LABEL)
        label:SetAnchor(TOPLEFT, tlw, TOPLEFT, header.x, headerY)
        label:SetDimensions(header.width, 20)
        label:SetFont("ZoFontWinT1")
        label:SetColor(0.7, 0.7, 0.7, 1)
        label:SetText(header.text)
    end

    -- Divider line
    local divider = WINDOW_MANAGER:CreateControl("FPT_Divider", tlw, CT_BACKDROP)
    divider:SetAnchor(TOPLEFT, tlw, TOPLEFT, PADDING, headerY + 20)
    divider:SetDimensions(WINDOW_WIDTH - PADDING * 2, 1)
    divider:SetCenterColor(0.5, 0.4, 0.1, 0.8)
    divider:SetEdgeColor(0, 0, 0, 0)

    -- Scroll area for results
    local scrollContainer = WINDOW_MANAGER:CreateControl("FPT_ScrollArea", tlw, CT_CONTROL)
    scrollContainer:SetAnchor(TOPLEFT, tlw, TOPLEFT, 0, headerY + 24)
    scrollContainer:SetAnchor(BOTTOMRIGHT, tlw, BOTTOMRIGHT, 0, -36)

    -- Status bar at bottom
    local statusBar = WINDOW_MANAGER:CreateControl("FPT_StatusBar", tlw, CT_LABEL)
    statusBar:SetAnchor(BOTTOMLEFT, tlw, BOTTOMLEFT, PADDING, -PADDING)
    statusBar:SetDimensions(WINDOW_WIDTH - PADDING * 2, 20)
    statusBar:SetFont("ZoFontWinT2")
    statusBar:SetColor(0.6, 0.6, 0.6, 1)
    statusBar:SetText("")

    window = tlw
    self.window = tlw
    self.scrollContainer = scrollContainer
    self.statusBar = statusBar
    self.titleBar = titleBar
end

---------------------------------------------------------------------------
-- Row Management
---------------------------------------------------------------------------

function ResultsUI:CreateRow(index)
    local parent = self.scrollContainer
    local rowName = "FPT_Row" .. index
    local yOffset = (index - 1) * ROW_HEIGHT

    local row = WINDOW_MANAGER:CreateControl(rowName, parent, CT_CONTROL)
    row:SetAnchor(TOPLEFT, parent, TOPLEFT, PADDING, yOffset)
    row:SetDimensions(WINDOW_WIDTH - PADDING * 2, ROW_HEIGHT)
    row:SetMouseEnabled(true)

    -- Hover highlight
    local highlight = WINDOW_MANAGER:CreateControl(rowName .. "_HL", row, CT_BACKDROP)
    highlight:SetAnchorFill(row)
    highlight:SetCenterColor(0.3, 0.3, 0.1, 0)
    highlight:SetEdgeColor(0, 0, 0, 0)

    row:SetHandler("OnMouseEnter", function()
        highlight:SetCenterColor(0.3, 0.3, 0.1, 0.3)
    end)
    row:SetHandler("OnMouseExit", function()
        highlight:SetCenterColor(0.3, 0.3, 0.1, 0)
    end)

    -- Rank number
    local rankLabel = WINDOW_MANAGER:CreateControl(rowName .. "_Rank", row, CT_LABEL)
    rankLabel:SetAnchor(TOPLEFT, row, TOPLEFT, 0, 4)
    rankLabel:SetDimensions(24, 20)
    rankLabel:SetFont("ZoFontWinH4")
    rankLabel:SetColor(1, 0.84, 0, 1)

    -- Item name (with link)
    local nameLabel = WINDOW_MANAGER:CreateControl(rowName .. "_Name", row, CT_LABEL)
    nameLabel:SetAnchor(TOPLEFT, row, TOPLEFT, 28, 2)
    nameLabel:SetDimensions(200, 20)
    nameLabel:SetFont("ZoFontWinT1")
    nameLabel:SetColor(1, 1, 1, 1)

    -- Tags line (Tier/Style)
    local tagLabel = WINDOW_MANAGER:CreateControl(rowName .. "_Tag", row, CT_LABEL)
    tagLabel:SetAnchor(TOPLEFT, row, TOPLEFT, 28, 20)
    tagLabel:SetDimensions(200, 16)
    tagLabel:SetFont("ZoFontWinT2")
    tagLabel:SetColor(0.6, 0.6, 0.6, 1)

    -- Margin
    local marginLabel = WINDOW_MANAGER:CreateControl(rowName .. "_Margin", row, CT_LABEL)
    marginLabel:SetAnchor(TOPLEFT, row, TOPLEFT, 232, 4)
    marginLabel:SetDimensions(75, 20)
    marginLabel:SetFont("ZoFontWinT1")
    marginLabel:SetColor(0, 1, 0, 1)

    -- Sub-margin (COGS line)
    local cogsLabel = WINDOW_MANAGER:CreateControl(rowName .. "_COGS", row, CT_LABEL)
    cogsLabel:SetAnchor(TOPLEFT, row, TOPLEFT, 232, 22)
    cogsLabel:SetDimensions(75, 14)
    cogsLabel:SetFont("ZoFontWinT2")
    cogsLabel:SetColor(0.5, 0.5, 0.5, 1)

    -- Sales count
    local salesLabel = WINDOW_MANAGER:CreateControl(rowName .. "_Sales", row, CT_LABEL)
    salesLabel:SetAnchor(TOPLEFT, row, TOPLEFT, 306, 4)
    salesLabel:SetDimensions(55, 20)
    salesLabel:SetFont("ZoFontWinT1")
    salesLabel:SetColor(0, 0.9, 0.9, 1)

    -- Velocity Score
    local scoreLabel = WINDOW_MANAGER:CreateControl(rowName .. "_Score", row, CT_LABEL)
    scoreLabel:SetAnchor(TOPLEFT, row, TOPLEFT, 360, 4)
    scoreLabel:SetDimensions(85, 20)
    scoreLabel:SetFont("ZoFontWinH4")
    scoreLabel:SetColor(1, 0.84, 0, 1)

    -- ROI
    local roiLabel = WINDOW_MANAGER:CreateControl(rowName .. "_ROI", row, CT_LABEL)
    roiLabel:SetAnchor(TOPLEFT, row, TOPLEFT, 444, 4)
    roiLabel:SetDimensions(55, 20)
    roiLabel:SetFont("ZoFontWinT1")

    -- Click handler for detail view
    row:SetHandler("OnMouseUp", function(control, button)
        if button == MOUSE_BUTTON_INDEX_LEFT then
            FPT:ShowItemDetail(index)
        end
    end)

    -- Row divider
    local rowDiv = WINDOW_MANAGER:CreateControl(rowName .. "_Div", row, CT_BACKDROP)
    rowDiv:SetAnchor(BOTTOMLEFT, row, BOTTOMLEFT, 0, 0)
    rowDiv:SetDimensions(WINDOW_WIDTH - PADDING * 2, 1)
    rowDiv:SetCenterColor(0.3, 0.3, 0.3, 0.3)
    rowDiv:SetEdgeColor(0, 0, 0, 0)

    return {
        control = row,
        rank = rankLabel,
        name = nameLabel,
        tag = tagLabel,
        margin = marginLabel,
        cogs = cogsLabel,
        sales = salesLabel,
        score = scoreLabel,
        roi = roiLabel,
    }
end

function ResultsUI:UpdateRow(row, index, item)
    row.rank:SetText(tostring(index))

    -- Item name (truncate if needed)
    local displayName = item.name or "Unknown"
    if #displayName > 28 then
        displayName = string.sub(displayName, 1, 26) .. ".."
    end
    row.name:SetText(displayName)

    -- Tags
    local tags = {}
    if item.isStructural then table.insert(tags, "|c00FFFF[T1]|r") end
    if item.isHighDemandStyle then table.insert(tags, "|cFF8C00[" .. (item.styleName or "HOT") .. "]|r") end
    if item.craftTypeName then table.insert(tags, item.craftTypeName) end
    row.tag:SetText(table.concat(tags, " "))

    -- Margin
    row.margin:SetText(FPT:FormatGold(item.profitMargin))
    if item.profitMargin > 10000 then
        row.margin:SetColor(0, 1, 0, 1)
    elseif item.profitMargin > 5000 then
        row.margin:SetColor(0.5, 1, 0, 1)
    else
        row.margin:SetColor(0.7, 0.9, 0.3, 1)
    end

    -- COGS
    row.cogs:SetText("COGS: " .. FPT:FormatGold(item.materialCost))

    -- Sales
    row.sales:SetText(tostring(item.salesCount or 0))

    -- Velocity Score
    row.score:SetText(FPT:FormatGold(item.velocityScore))

    -- ROI
    local roiPct = (item.roi or 0) * 100
    row.roi:SetText(string.format("%.0f%%", roiPct))
    if roiPct > 100 then
        row.roi:SetColor(0, 1, 0, 1)
    elseif roiPct > 50 then
        row.roi:SetColor(0.5, 1, 0, 1)
    elseif roiPct > 0 then
        row.roi:SetColor(1, 1, 0, 1)
    else
        row.roi:SetColor(1, 0.3, 0.3, 1)
    end

    row.control:SetHidden(false)
end

---------------------------------------------------------------------------
-- Public API
---------------------------------------------------------------------------

function ResultsUI:ShowResults(results)
    currentResults = results or {}

    -- Create/update rows
    for i = 1, math.max(#currentResults, #rowPool) do
        if i <= #currentResults then
            if not rowPool[i] then
                rowPool[i] = self:CreateRow(i)
            end
            self:UpdateRow(rowPool[i], i, currentResults[i])
        elseif rowPool[i] then
            rowPool[i].control:SetHidden(true)
        end
    end

    -- Update status bar
    if self.statusBar and #currentResults > 0 then
        local stats = FPT.VelocityCalculator and FPT.VelocityCalculator:GetSummaryStats(currentResults) or {}
        self.statusBar:SetText(string.format(
            "%d items | Est. weekly: %s | Click row for details",
            #currentResults,
            FPT:FormatGold(stats.totalEstWeeklyProfit or 0)
        ))
    end

    self:Show()
end

function ResultsUI:Show()
    if window then
        window:SetHidden(false)
        isVisible = true
    end
end

function ResultsUI:Hide()
    if window then
        window:SetHidden(true)
        isVisible = false
    end
end

function ResultsUI:Toggle()
    if isVisible then
        self:Hide()
    else
        if #currentResults > 0 then
            self:Show()
        else
            FPT:Info("No results to display. Run /fpt first.")
        end
    end
end

function ResultsUI:IsVisible()
    return isVisible
end
