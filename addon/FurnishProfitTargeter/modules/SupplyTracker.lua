--[[
    Furnish Profit Targeter - Supply Tracker Module

    Tracks COD (Cash-on-Delivery) purchases from starter zones,
    monitors material inventory levels, calculates savings vs
    market price, and provides supply chain analytics.

    Core principle: Buy materials at 15% below TTC average from
    starter zones to maximize manufacturing margins.

    Author: ESO Build Optimizer Team
    Version: 1.0.0
]]--

---------------------------------------------------------------------------
-- Module Setup
---------------------------------------------------------------------------

local FPT = FurnishProfitTargeter
local SupplyTracker = {}
FPT.SupplyTracker = SupplyTracker

---------------------------------------------------------------------------
-- Constants
---------------------------------------------------------------------------

-- COD mail processing event
local COD_CHECK_INTERVAL_MS = 5000  -- Check pending COD every 5 seconds

-- Material item IDs for tracking
local TRACKED_MATERIALS = {
    [114889] = "Heartwood",
    [114890] = "Regulus",
    [114891] = "Bast",
    [114892] = "Mundane Rune",
    [114893] = "Clean Pelts",
    [114894] = "Decorative Wax",
    [114895] = "Ochre",
}

---------------------------------------------------------------------------
-- Initialization
---------------------------------------------------------------------------

function SupplyTracker:Initialize()
    -- Ensure supply chain data structure exists
    local sc = FPT.savedVars.supplyChain
    if not sc.codPurchases then sc.codPurchases = {} end
    if not sc.materialInventory then sc.materialInventory = {} end
    if not sc.dailyLog then sc.dailyLog = {} end
    if not sc.totalSaved then sc.totalSaved = 0 end
    if not sc.totalSpent then sc.totalSpent = 0 end
    if not sc.totalUnits then sc.totalUnits = 0 end

    -- Register for mail events to track COD purchases
    self:RegisterMailEvents()

    FPT:Debug("SupplyTracker initialized")
end

---------------------------------------------------------------------------
-- Mail Event Tracking
---------------------------------------------------------------------------

function SupplyTracker:RegisterMailEvents()
    -- Hook into mail receive events to detect COD material purchases
    EVENT_MANAGER:RegisterForEvent(
        FPT.name .. "_mail",
        EVENT_MAIL_READABLE,
        function(eventCode, mailId)
            self:OnMailReadable(mailId)
        end
    )
end

-- Called when a mail becomes readable - check if it's a COD material delivery
function SupplyTracker:OnMailReadable(mailId)
    local senderDisplayName, senderCharacterName, subject, _, _, fromSystem, fromCS, _, codAmount =
        GetMailItemInfo(mailId)

    -- Skip system and CS mails
    if fromSystem or fromCS then return end

    -- Check if this is a COD mail (has a payment amount)
    if codAmount and codAmount > 0 then
        -- Check attachments for tracked materials
        local numAttachments = GetMailAttachmentInfo(mailId)
        for attachIndex = 1, numAttachments do
            local itemLink = GetAttachedItemLink(mailId, attachIndex, LINK_STYLE_BRACKETS)
            if itemLink then
                local itemId = GetItemLinkItemId(itemLink)
                if TRACKED_MATERIALS[itemId] then
                    local _, stackCount = GetAttachedItemInfo(mailId, attachIndex)
                    self:RecordCODPurchase(itemId, stackCount or 1, codAmount, senderDisplayName)
                end
            end
        end
    end
end

---------------------------------------------------------------------------
-- COD Purchase Recording
---------------------------------------------------------------------------

function SupplyTracker:RecordCODPurchase(itemId, quantity, totalPaid, sender)
    local sc = FPT.savedVars.supplyChain
    local materialName = TRACKED_MATERIALS[itemId] or "Unknown"
    local unitPaid = totalPaid / quantity

    -- Get current market price for savings calculation
    local marketPrice = 0
    if FPT.PriceEngine then
        marketPrice = FPT.PriceEngine:GetTTCPrice(itemId) or FPT.PriceEngine:GetMMPrice(itemId) or 0
    end

    local savings = (marketPrice - unitPaid) * quantity

    -- Record the purchase
    local purchase = {
        itemId = itemId,
        materialName = materialName,
        quantity = quantity,
        unitPaid = unitPaid,
        totalPaid = totalPaid,
        marketPrice = marketPrice,
        savings = math.max(0, savings),
        sender = sender or "Unknown",
        timestamp = GetTimeStamp(),
    }

    table.insert(sc.codPurchases, purchase)

    -- Keep last 500 purchases
    while #sc.codPurchases > 500 do
        table.remove(sc.codPurchases, 1)
    end

    -- Update inventory tracking
    sc.materialInventory[itemId] = (sc.materialInventory[itemId] or 0) + quantity

    -- Update totals
    sc.totalSaved = sc.totalSaved + math.max(0, savings)
    sc.totalSpent = sc.totalSpent + totalPaid
    sc.totalUnits = sc.totalUnits + quantity

    -- Update global stats
    FPT.savedVars.stats.totalGoldSavedOnMaterials = sc.totalSaved

    if savings > 0 then
        FPT:Debug("COD: %s x%d @ %s/ea (saved %s vs market %s)",
            materialName, quantity,
            FPT:FormatGold(unitPaid),
            FPT:FormatGold(savings),
            FPT:FormatGold(marketPrice))
    end
end

---------------------------------------------------------------------------
-- Dashboard Display
---------------------------------------------------------------------------

function SupplyTracker:ShowDashboard()
    local sc = FPT.savedVars.supplyChain

    FPT:Info("%s===== SUPPLY CHAIN DASHBOARD =====%s", FPT.COLORS.GOLD, FPT.COLORS.RESET)

    -- Material inventory
    FPT:Info("%s--- Material Inventory ---%s", FPT.COLORS.GRAY, FPT.COLORS.RESET)
    local hasInventory = false
    for itemId, name in pairs(TRACKED_MATERIALS) do
        local qty = sc.materialInventory[itemId] or 0
        if qty > 0 then
            hasInventory = true
            local marketPrice = 0
            if FPT.PriceEngine then
                marketPrice = FPT.PriceEngine:GetTTCPrice(itemId) or FPT.PriceEngine:GetMMPrice(itemId) or 0
            end
            local marketValue = marketPrice * qty

            FPT:Info("  %s: %s%d%s units (market value: %s)",
                name,
                FPT.COLORS.CYAN, qty, FPT.COLORS.RESET,
                FPT:FormatGold(marketValue))
        end
    end
    if not hasInventory then
        FPT:Info("  %sNo materials tracked yet%s", FPT.COLORS.GRAY, FPT.COLORS.RESET)
    end

    -- COD Pricing targets
    FPT:Info("")
    FPT:Info("%s--- COD Target Prices (%d%% discount) ---%s",
        FPT.COLORS.GRAY, FPT.savedVars.settings.codDiscountPct, FPT.COLORS.RESET)

    if FPT.PriceEngine then
        local targets = FPT.PriceEngine:GetAllCODTargets()
        for itemId, data in pairs(targets) do
            if data.marketPrice and data.codTarget then
                FPT:Info("  %s: Market %s -> COD Target %s%s%s (save %s/unit)",
                    data.name,
                    FPT:FormatGold(data.marketPrice),
                    FPT.COLORS.GREEN, FPT:FormatGold(data.codTarget), FPT.COLORS.RESET,
                    FPT:FormatGold(data.savings))
            end
        end
    end

    -- Totals
    FPT:Info("")
    FPT:Info("%s--- Lifetime Totals ---%s", FPT.COLORS.GRAY, FPT.COLORS.RESET)
    FPT:Info("  Total COD Purchases: %d", #sc.codPurchases)
    FPT:Info("  Total Units Acquired: %s%d%s", FPT.COLORS.CYAN, sc.totalUnits or 0, FPT.COLORS.RESET)
    FPT:Info("  Total Spent: %s", FPT:FormatGold(sc.totalSpent or 0))
    FPT:Info("  Total Saved vs Market: %s%s%s", FPT.COLORS.GREEN, FPT:FormatGold(sc.totalSaved or 0), FPT.COLORS.RESET)

    if (sc.totalSpent or 0) > 0 then
        local avgDiscount = (sc.totalSaved / (sc.totalSpent + sc.totalSaved)) * 100
        FPT:Info("  Average Discount: %s%.1f%%%s", FPT.COLORS.GREEN, avgDiscount, FPT.COLORS.RESET)
    end

    -- Starter zone WTB command
    FPT:Info("")
    FPT:Info("%s--- Starter Zone Buy Template ---%s", FPT.COLORS.GRAY, FPT.COLORS.RESET)
    self:GenerateWTBMessage()
end

function SupplyTracker:ShowCODSummary()
    local sc = FPT.savedVars.supplyChain
    local purchases = sc.codPurchases

    if not purchases or #purchases == 0 then
        FPT:Info("No COD purchases recorded yet.")
        return
    end

    FPT:Info("%s===== RECENT COD PURCHASES =====%s", FPT.COLORS.GOLD, FPT.COLORS.RESET)

    -- Show last 10 purchases
    local startIdx = math.max(1, #purchases - 9)
    for i = #purchases, startIdx, -1 do
        local p = purchases[i]
        local savingsStr = ""
        if p.savings and p.savings > 0 then
            savingsStr = string.format(" %s(saved %s)%s", FPT.COLORS.GREEN, FPT:FormatGold(p.savings), FPT.COLORS.RESET)
        end

        FPT:Info("  %s x%d @ %s/ea from %s%s",
            p.materialName or "Unknown",
            p.quantity or 0,
            FPT:FormatGold(p.unitPaid or 0),
            p.sender or "Unknown",
            savingsStr)
    end

    -- Per-material summary
    FPT:Info("")
    FPT:Info("%s--- Per-Material Summary ---%s", FPT.COLORS.GRAY, FPT.COLORS.RESET)

    local matSummary = {}
    for _, p in ipairs(purchases) do
        local id = p.itemId
        if not matSummary[id] then
            matSummary[id] = { name = p.materialName, qty = 0, spent = 0, saved = 0 }
        end
        matSummary[id].qty = matSummary[id].qty + (p.quantity or 0)
        matSummary[id].spent = matSummary[id].spent + (p.totalPaid or 0)
        matSummary[id].saved = matSummary[id].saved + (p.savings or 0)
    end

    for _, summary in pairs(matSummary) do
        local avgUnit = summary.qty > 0 and (summary.spent / summary.qty) or 0
        FPT:Info("  %s: %d units, avg %s/ea, saved %s%s%s total",
            summary.name, summary.qty,
            FPT:FormatGold(avgUnit),
            FPT.COLORS.GREEN, FPT:FormatGold(summary.saved), FPT.COLORS.RESET)
    end
end

---------------------------------------------------------------------------
-- WTB Message Generation
---------------------------------------------------------------------------

function SupplyTracker:GenerateWTBMessage()
    -- Build WTB message with current COD target prices
    local parts = {}

    if FPT.PriceEngine then
        local targets = FPT.PriceEngine:GetAllCODTargets()
        -- Focus on the 3 most important materials
        local keyMats = { 114889, 114892, 114894 }  -- Heartwood, Mundane Rune, Decorative Wax

        for _, itemId in ipairs(keyMats) do
            local data = targets[itemId]
            if data and data.codTarget then
                table.insert(parts, string.format("%s @ %s/ea",
                    data.name, FPT:FormatGold(data.codTarget)))
            end
        end
    end

    local priceList = #parts > 0 and table.concat(parts, ", ") or "competitive prices"

    local wtbMsg = string.format(
        "WTB your unused Heartwood, Mundane Runes, and Decorative Wax! COD me any amount - %s. Instant gold, no listing fees!",
        priceList
    )

    FPT:Info("  %s%s%s", FPT.COLORS.CYAN, wtbMsg, FPT.COLORS.RESET)
    FPT:Info("  %s(Copy and paste into starter zone chat)%s", FPT.COLORS.GRAY, FPT.COLORS.RESET)
end

-- Manually deduct materials when crafting
function SupplyTracker:DeductMaterial(itemId, quantity)
    local sc = FPT.savedVars.supplyChain
    local current = sc.materialInventory[itemId] or 0
    sc.materialInventory[itemId] = math.max(0, current - quantity)
end

-- Reset inventory tracking (e.g., after physical inventory count)
function SupplyTracker:ResetInventory()
    FPT.savedVars.supplyChain.materialInventory = {}
    FPT:Info("Material inventory reset.")
end
