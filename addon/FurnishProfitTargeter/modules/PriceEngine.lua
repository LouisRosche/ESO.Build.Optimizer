--[[
    Furnish Profit Targeter - Price Engine Module

    Integrates with Master Merchant (MM) and Tamriel Trade Centre (TTC)
    to provide real-time pricing for:
    - Raw material COGS (Cost of Goods Sold)
    - Finished furnishing retail values

    Supports price source priority, manual overrides,
    and COD discount calculations for supply chain optimization.

    Author: ESO Build Optimizer Team
    Version: 1.0.0
]]--

---------------------------------------------------------------------------
-- Module Setup
---------------------------------------------------------------------------

local FPT = FurnishProfitTargeter
local PriceEngine = {}
FPT.PriceEngine = PriceEngine

---------------------------------------------------------------------------
-- Local State
---------------------------------------------------------------------------

local priceCache = {}
local CACHE_TTL_MS = 300000  -- 5 minute cache

---------------------------------------------------------------------------
-- Initialization
---------------------------------------------------------------------------

function PriceEngine:Initialize()
    priceCache = {}
    FPT:Debug("PriceEngine initialized (MM: %s, TTC: %s)",
        FPT:HasMasterMerchant() and "YES" or "NO",
        FPT:HasTTC() and "YES" or "NO")
end

---------------------------------------------------------------------------
-- Master Merchant Integration
---------------------------------------------------------------------------

-- Get average price from Master Merchant for an item
function PriceEngine:GetMMPrice(itemIdOrLink)
    if not FPT:HasMasterMerchant() then return nil end

    local itemLink = itemIdOrLink
    if type(itemIdOrLink) == "number" then
        itemLink = FPT:GetItemLinkFromId(itemIdOrLink)
    end

    if not itemLink then return nil end

    -- Check cache
    local cacheKey = "mm_" .. tostring(itemLink)
    local cached = priceCache[cacheKey]
    if cached and (GetGameTimeMilliseconds() - cached.time) < CACHE_TTL_MS then
        return cached.price
    end

    local price = nil

    -- Try MasterMerchant:ItemPriceByItemLink
    local success, result = pcall(function()
        return MasterMerchant:ItemPriceByItemLink(itemLink)
    end)

    if success and result then
        if type(result) == "table" then
            price = result.avgPrice or result.average or result.avg
        elseif type(result) == "number" then
            price = result
        end
    end

    -- Cache result
    priceCache[cacheKey] = { price = price, time = GetGameTimeMilliseconds() }

    return price
end

-- Get sales count from Master Merchant in a given time window
function PriceEngine:GetMMSalesCount(itemIdOrLink, windowDays)
    if not FPT:HasMasterMerchant() then return 0 end

    local itemLink = itemIdOrLink
    if type(itemIdOrLink) == "number" then
        itemLink = FPT:GetItemLinkFromId(itemIdOrLink)
    end

    if not itemLink then return 0 end

    local count = 0

    -- Try to get sales data from MM
    local success, result = pcall(function()
        return MasterMerchant:GetSalesData(GetItemLinkItemId(itemLink))
    end)

    if success and result then
        local cutoffTime = GetTimeStamp() - (windowDays * 86400)

        if type(result) == "table" then
            for _, sale in pairs(result) do
                if type(sale) == "table" then
                    -- Iterate through guild sales records
                    for _, record in pairs(sale) do
                        if type(record) == "table" and record.timestamp then
                            if record.timestamp >= cutoffTime then
                                count = count + (record.quant or record.quantity or 1)
                            end
                        end
                    end
                end
            end
        end
    end

    return count
end

---------------------------------------------------------------------------
-- Tamriel Trade Centre Integration
---------------------------------------------------------------------------

-- Get price info from TTC for an item
function PriceEngine:GetTTCPrice(itemIdOrLink)
    if not FPT:HasTTC() then return nil end

    local itemLink = itemIdOrLink
    if type(itemIdOrLink) == "number" then
        itemLink = FPT:GetItemLinkFromId(itemIdOrLink)
    end

    if not itemLink then return nil end

    -- Check cache
    local cacheKey = "ttc_" .. tostring(itemLink)
    local cached = priceCache[cacheKey]
    if cached and (GetGameTimeMilliseconds() - cached.time) < CACHE_TTL_MS then
        return cached.price
    end

    local price = nil

    -- Try TamrielTradeCentrePrice:GetPriceInfo
    local success, result = pcall(function()
        return TamrielTradeCentrePrice:GetPriceInfo(itemLink)
    end)

    if success and result and type(result) == "table" then
        -- TTC returns { Avg, Min, Max, EntryCount, AmountCount, SuggestedPrice,
        --               SaleAvg, SaleEntryCount, SaleAmountCount }
        -- Prefer SaleAvg (actual sales) over Avg (listing averages) when available
        price = result.SaleAvg or result.SuggestedPrice or result.Avg
    end

    -- Cache result
    priceCache[cacheKey] = { price = price, time = GetGameTimeMilliseconds() }

    return price
end

-- Get TTC listing count as a proxy for demand
function PriceEngine:GetTTCListingCount(itemIdOrLink)
    if not FPT:HasTTC() then return 0 end

    local itemLink = itemIdOrLink
    if type(itemIdOrLink) == "number" then
        itemLink = FPT:GetItemLinkFromId(itemIdOrLink)
    end

    if not itemLink then return 0 end

    local count = 0

    local success, result = pcall(function()
        return TamrielTradeCentrePrice:GetPriceInfo(itemLink)
    end)

    if success and result and type(result) == "table" then
        count = result.AmountCount or 0
    end

    return count
end

---------------------------------------------------------------------------
-- Unified Price Resolution
---------------------------------------------------------------------------

-- Get the best available price for an item, respecting priority settings
function PriceEngine:GetBestPrice(itemIdOrLink)
    local settings = FPT.savedVars.settings
    local mmPrice = self:GetMMPrice(itemIdOrLink)
    local ttcPrice = self:GetTTCPrice(itemIdOrLink)

    -- Check for manual override (materials only)
    if type(itemIdOrLink) == "number" then
        local override = settings.materialOverrides[itemIdOrLink]
        if override then return override, "override" end
    end

    -- Priority-based resolution
    if settings.primaryPriceSource == "mm" then
        if mmPrice then return mmPrice, "mm" end
        if ttcPrice then return ttcPrice, "ttc" end
    else
        if ttcPrice then return ttcPrice, "ttc" end
        if mmPrice then return mmPrice, "mm" end
    end

    return nil, "none"
end

-- Get the retail selling price for a finished furnishing
function PriceEngine:GetRetailPrice(itemIdOrLink)
    local mmPrice = self:GetMMPrice(itemIdOrLink)
    local ttcPrice = self:GetTTCPrice(itemIdOrLink)

    -- For retail, prefer MM (actual confirmed sales) over TTC (listing averages)
    -- unless user has set TTC as primary
    local settings = FPT.savedVars.settings
    if settings.primaryPriceSource == "mm" then
        return mmPrice or ttcPrice, mmPrice, ttcPrice
    else
        return ttcPrice or mmPrice, mmPrice, ttcPrice
    end
end

---------------------------------------------------------------------------
-- COGS Calculation
---------------------------------------------------------------------------

-- Calculate total material cost (COGS) for a plan
function PriceEngine:CalculatePrices(plan)
    if not plan or not plan.materials then return end

    local totalCost = 0

    for _, mat in ipairs(plan.materials) do
        local unitPrice, source = self:GetBestPrice(mat.itemId or mat.itemLink)
        unitPrice = unitPrice or 0

        mat.unitPrice = unitPrice
        mat.totalPrice = unitPrice * mat.quantity
        mat.priceSource = source

        totalCost = totalCost + mat.totalPrice
    end

    plan.materialCost = totalCost

    -- Get retail price
    local retailPrice, mmPrice, ttcPrice = self:GetRetailPrice(plan.itemLink or plan.resultItemId)
    plan.retailPrice = retailPrice or 0
    plan.mmPrice = mmPrice or 0
    plan.ttcPrice = ttcPrice or 0

    -- Calculate margin and ROI
    plan.profitMargin = plan.retailPrice - plan.materialCost
    if plan.materialCost > 0 then
        plan.roi = plan.profitMargin / plan.materialCost
    else
        plan.roi = 0
    end
end

---------------------------------------------------------------------------
-- COD Discount Calculator
---------------------------------------------------------------------------

-- Calculate the target COD price for a material (for starter zone buying)
function PriceEngine:GetCODTargetPrice(itemId)
    local marketPrice = self:GetTTCPrice(itemId) or self:GetMMPrice(itemId)
    if not marketPrice then return nil end

    local discountPct = FPT.savedVars.settings.codDiscountPct / 100
    return math.floor(marketPrice * (1 - discountPct))
end

-- Get all material target COD prices
function PriceEngine:GetAllCODTargets()
    local targets = {}

    for itemId, name in pairs(FPT.MATERIAL_NAMES) do
        local marketPrice = self:GetTTCPrice(itemId) or self:GetMMPrice(itemId)
        local codTarget = self:GetCODTargetPrice(itemId)

        targets[itemId] = {
            name = name,
            marketPrice = marketPrice,
            codTarget = codTarget,
            savings = marketPrice and codTarget and (marketPrice - codTarget) or 0,
        }
    end

    return targets
end

---------------------------------------------------------------------------
-- Cache Management
---------------------------------------------------------------------------

function PriceEngine:ClearCache()
    priceCache = {}
    FPT:Debug("Price cache cleared")
end

-- Evict stale entries to prevent unbounded memory growth over long sessions
function PriceEngine:EvictStaleEntries()
    local now = GetGameTimeMilliseconds()
    local evicted = 0
    for key, entry in pairs(priceCache) do
        if (now - entry.time) >= CACHE_TTL_MS then
            priceCache[key] = nil
            evicted = evicted + 1
        end
    end
    if evicted > 0 then
        FPT:Debug("PriceEngine: evicted %d stale cache entries", evicted)
    end
end

-- Hard cap: if cache exceeds this size, clear it entirely
local CACHE_MAX_ENTRIES = 2000

function PriceEngine:GetCacheSize()
    local count = 0
    for _ in pairs(priceCache) do count = count + 1 end

    -- Auto-evict if cache is getting large
    if count > CACHE_MAX_ENTRIES then
        self:EvictStaleEntries()
        -- Recount after eviction
        count = 0
        for _ in pairs(priceCache) do count = count + 1 end
        -- If still over limit after eviction, hard clear
        if count > CACHE_MAX_ENTRIES then
            self:ClearCache()
            count = 0
        end
    end

    return count
end
