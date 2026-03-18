--[[
    Furnish Profit Targeter - Bundle Manager Module

    Manages "Room-in-a-Box" bundle definitions for Tier 2 sales.
    Tracks curated sets of furniture items organized by theme,
    calculates total COGS, suggested pricing, and generates
    bundle descriptions for Discord/Zone Chat marketing.

    Author: ESO Build Optimizer Team
    Version: 1.0.0
]]--

---------------------------------------------------------------------------
-- Module Setup
---------------------------------------------------------------------------

local FPT = FurnishProfitTargeter
local BundleManager = {}
FPT.BundleManager = BundleManager

---------------------------------------------------------------------------
-- Preset Bundle Templates
---------------------------------------------------------------------------

-- Pre-configured Room-in-a-Box templates inspired by popular housing themes
local PRESET_BUNDLES = {
    {
        id = "necrom_library",
        name = "The Complete Necrom Scholar's Library",
        description = "Hermaeus Mora bookcases, Apocrypha lighting, scattered tomes, and Telvanni reading furniture.",
        theme = "Necrom / Apocrypha",
        tier = "Premium",
        tags = { "library", "necrom", "apocrypha", "scholarly", "telvanni" },
        -- Items defined by name pattern (matched against known plans)
        itemPatterns = {
            "Apocrypha.*Bookcase",
            "Apocrypha.*Sconce",
            "Apocrypha.*Lantern",
            "Apocrypha.*Candle",
            "Telvanni.*Desk",
            "Telvanni.*Chair",
            "Telvanni.*Shelf",
            "Necrom.*Book",
            "Necrom.*Scroll",
            "Necrom.*Tome",
        },
        suggestedMarkupPct = 40,
    },
    {
        id = "colovian_tavern",
        name = "The Cozy Colovian Tavern",
        description = "West Weald bar counters, Colovian wine kegs, rustic seating, and warm fireplace ambiance.",
        theme = "West Weald / Colovian",
        tier = "Standard",
        tags = { "tavern", "colovian", "west weald", "rustic", "food" },
        itemPatterns = {
            "West Weald.*Counter",
            "West Weald.*Bar",
            "Colovian.*Keg",
            "Colovian.*Barrel",
            "Colovian.*Chair",
            "Colovian.*Table",
            "Colovian.*Bench",
            "Solitude.*Fireplace",
            "Colovian.*Candle",
            "Colovian.*Mug",
            "Colovian.*Bottle",
        },
        suggestedMarkupPct = 35,
    },
    {
        id = "alinor_throne_room",
        name = "Alinor Royal Throne Room",
        description = "Majestic Alinor columns, walls, throne, elegant lighting, and Summerset banners.",
        theme = "Alinor / Summerset",
        tier = "Luxury",
        tags = { "alinor", "summerset", "royal", "throne", "elegant" },
        itemPatterns = {
            "Alinor.*Column",
            "Alinor.*Wall",
            "Alinor.*Throne",
            "Alinor.*Banner",
            "Alinor.*Chandelier",
            "Alinor.*Sconce",
            "Alinor.*Carpet",
            "Alinor.*Curtain",
            "Alinor.*Pedestal",
        },
        suggestedMarkupPct = 50,
    },
    {
        id = "elsweyr_garden",
        name = "Elsweyr Moonlit Garden",
        description = "Khajiiti planters, moon sugar palms, Elsweyr platforms, exotic lanterns, and water features.",
        theme = "Elsweyr / Khajiiti",
        tier = "Premium",
        tags = { "elsweyr", "garden", "khajiit", "outdoor", "moonlit" },
        itemPatterns = {
            "Elsweyr.*Planter",
            "Elsweyr.*Platform",
            "Elsweyr.*Lantern",
            "Elsweyr.*Fountain",
            "Elsweyr.*Tree",
            "Elsweyr.*Palm",
            "Elsweyr.*Fence",
            "Elsweyr.*Bench",
            "Elsweyr.*Rug",
        },
        suggestedMarkupPct = 40,
    },
    {
        id = "dwarven_workshop",
        name = "Dwarven Engineer's Workshop",
        description = "Dwemer machinery, gears, pipes, workbenches, and clockwork lighting.",
        theme = "Dwarven / Clockwork",
        tier = "Premium",
        tags = { "dwarven", "dwemer", "clockwork", "workshop", "machinery" },
        itemPatterns = {
            "Dwarven.*Gear",
            "Dwarven.*Pipe",
            "Dwarven.*Table",
            "Dwarven.*Bench",
            "Dwarven.*Lamp",
            "Dwarven.*Sconce",
            "Clockwork.*",
            "Dwarven.*Column",
            "Dwarven.*Shelf",
        },
        suggestedMarkupPct = 45,
    },
    {
        id = "solstice_bedroom",
        name = "Solstice Winter Bedroom",
        description = "Warm furs, cozy fireplace, Solstice candles, wooden bed frame, and snowy window accents.",
        theme = "Solstice / Nordic",
        tier = "Standard",
        tags = { "solstice", "winter", "bedroom", "cozy", "nordic" },
        itemPatterns = {
            "Solstice.*Bed",
            "Solstice.*Candle",
            "Solstice.*Fur",
            "Solstice.*Rug",
            "Solstice.*Fireplace",
            "Nord.*Chest",
            "Nord.*Nightstand",
            "Nord.*Curtain",
            "Solstice.*Wreath",
        },
        suggestedMarkupPct = 30,
    },
}

---------------------------------------------------------------------------
-- Initialization
---------------------------------------------------------------------------

function BundleManager:Initialize()
    -- Load preset bundles into saved vars if not already present
    local sv = FPT.savedVars.bundles
    if not sv or #sv == 0 then
        FPT.savedVars.bundles = {}
        for _, preset in ipairs(PRESET_BUNDLES) do
            table.insert(FPT.savedVars.bundles, {
                id = preset.id,
                name = preset.name,
                description = preset.description,
                theme = preset.theme,
                tier = preset.tier,
                tags = preset.tags,
                itemPatterns = preset.itemPatterns,
                suggestedMarkupPct = preset.suggestedMarkupPct,
                -- Actual matched items (populated on demand)
                matchedItems = {},
                -- Financial tracking
                totalCOGS = 0,
                suggestedPrice = 0,
                timesSold = 0,
                totalRevenue = 0,
            })
        end
    end

    FPT:Debug("BundleManager initialized with %d bundles", #FPT.savedVars.bundles)
end

---------------------------------------------------------------------------
-- Bundle Operations
---------------------------------------------------------------------------

-- List all bundles
function BundleManager:ListBundles()
    local bundles = FPT.savedVars.bundles
    if not bundles or #bundles == 0 then
        FPT:Info("No bundles defined. Use /fpt bundle <name> to create one.")
        return
    end

    FPT:Info("%s===== ROOM-IN-A-BOX BUNDLES =====%s", FPT.COLORS.GOLD, FPT.COLORS.RESET)

    for i, bundle in ipairs(bundles) do
        local tierColor = FPT.COLORS.WHITE
        if bundle.tier == "Luxury" then tierColor = FPT.COLORS.GOLD
        elseif bundle.tier == "Premium" then tierColor = FPT.COLORS.PURPLE
        elseif bundle.tier == "Standard" then tierColor = FPT.COLORS.CYAN
        end

        FPT:Info("%s%d.%s %s%s%s %s[%s]%s",
            FPT.COLORS.GOLD, i, FPT.COLORS.RESET,
            FPT.COLORS.WHITE, bundle.name, FPT.COLORS.RESET,
            tierColor, bundle.tier or "Standard", FPT.COLORS.RESET)

        FPT:Info("   %s%s%s | Sold: %d | Revenue: %s",
            FPT.COLORS.GRAY, bundle.theme or "No theme", FPT.COLORS.RESET,
            bundle.timesSold or 0,
            FPT:FormatGold(bundle.totalRevenue or 0))
    end

    FPT:Info("")
    FPT:Info("Use /fpt bundle <name> for details. /fpt bundle add <name> to create.")
end

-- Show detailed bundle info
function BundleManager:ShowBundle(nameOrIndex)
    local bundle = self:FindBundle(nameOrIndex)
    if not bundle then
        -- Try to create a new bundle
        if nameOrIndex and string.sub(nameOrIndex, 1, 4) == "add " then
            local newName = string.sub(nameOrIndex, 5)
            self:CreateBundle(newName)
        else
            FPT:Info("Bundle not found: '%s'. Use /fpt bundle add <name> to create.", nameOrIndex)
        end
        return
    end

    FPT:Info("%s===== BUNDLE: %s =====%s", FPT.COLORS.GOLD, bundle.name, FPT.COLORS.RESET)
    FPT:Info("Theme: %s", bundle.theme or "Custom")
    FPT:Info("Tier: %s", bundle.tier or "Standard")
    FPT:Info("Description: %s", bundle.description or "No description")

    -- Calculate current costs
    self:CalculateBundleCosts(bundle)

    FPT:Info("")
    FPT:Info("%s--- Pricing ---%s", FPT.COLORS.GRAY, FPT.COLORS.RESET)
    FPT:Info("  Total COGS: %s%s%s", FPT.COLORS.RED, FPT:FormatGold(bundle.totalCOGS), FPT.COLORS.RESET)
    FPT:Info("  Suggested Price (+%d%%): %s%s%s",
        bundle.suggestedMarkupPct or 35,
        FPT.COLORS.GREEN, FPT:FormatGold(bundle.suggestedPrice), FPT.COLORS.RESET)

    -- Fee-adjusted profit per sale
    local feePct = FPT.savedVars.settings.guildTraderFeePct or 7
    local grossProfit = bundle.suggestedPrice - bundle.totalCOGS
    local netRevenue = bundle.suggestedPrice * (1 - feePct / 100)
    local netProfit = netRevenue - bundle.totalCOGS
    FPT:Info("  Gross Profit: %s%s%s",
        FPT.COLORS.GREEN, FPT:FormatGold(grossProfit), FPT.COLORS.RESET)
    FPT:Info("  Net Profit (-%d%% fee): %s%s%s",
        feePct,
        FPT.COLORS.GREEN, FPT:FormatGold(netProfit), FPT.COLORS.RESET)

    FPT:Info("")
    FPT:Info("%s--- Lifetime ---%s", FPT.COLORS.GRAY, FPT.COLORS.RESET)
    FPT:Info("  Times Sold: %d", bundle.timesSold or 0)
    FPT:Info("  Total Revenue: %s", FPT:FormatGold(bundle.totalRevenue or 0))

    -- List item patterns
    if bundle.itemPatterns and #bundle.itemPatterns > 0 then
        FPT:Info("")
        FPT:Info("%s--- Item Patterns (%d) ---%s", FPT.COLORS.GRAY, #bundle.itemPatterns, FPT.COLORS.RESET)
        for _, pattern in ipairs(bundle.itemPatterns) do
            FPT:Info("  - %s", pattern)
        end
    end

    -- Generate Discord ad copy for this bundle
    FPT:Info("")
    FPT:Info("%s--- Discord Ad Copy ---%s", FPT.COLORS.GRAY, FPT.COLORS.RESET)
    local adCopy = self:GenerateBundleAdCopy(bundle)
    FPT:Info("  %s", adCopy)
end

-- Find a bundle by name or index
function BundleManager:FindBundle(nameOrIndex)
    local bundles = FPT.savedVars.bundles
    if not bundles then return nil end

    -- Try as index first
    local index = tonumber(nameOrIndex)
    if index and bundles[index] then
        return bundles[index]
    end

    -- Search by name (case-insensitive partial match)
    local lowerSearch = string.lower(nameOrIndex)
    for _, bundle in ipairs(bundles) do
        if bundle.name and string.find(string.lower(bundle.name), lowerSearch) then
            return bundle
        end
        if bundle.id and string.find(string.lower(bundle.id), lowerSearch) then
            return bundle
        end
    end

    return nil
end

local MAX_BUNDLES = 100

-- Create a new custom bundle
function BundleManager:CreateBundle(name)
    if not name or name == "" then
        FPT:Info("Usage: /fpt bundle add <bundle name>")
        return
    end

    if #FPT.savedVars.bundles >= MAX_BUNDLES then
        FPT:Info("Bundle limit reached (%d). Remove a bundle before adding more.", MAX_BUNDLES)
        return
    end

    local bundle = {
        id = string.lower(string.gsub(name, "%s+", "_")),
        name = name,
        description = "",
        theme = "Custom",
        tier = "Standard",
        tags = {},
        itemPatterns = {},
        suggestedMarkupPct = 35,
        matchedItems = {},
        totalCOGS = 0,
        suggestedPrice = 0,
        timesSold = 0,
        totalRevenue = 0,
    }

    table.insert(FPT.savedVars.bundles, bundle)
    FPT:Info("Bundle created: '%s'", name)
    FPT:Info("Add items with: /fpt bundle additem <bundle> <item pattern>")
end

-- Calculate total COGS for a bundle based on matched items
function BundleManager:CalculateBundleCosts(bundle)
    if not bundle then return end

    local totalCOGS = 0

    -- Match item patterns against last scan results (deduplicate by name)
    local results = FPT.savedVars.lastScanResults or {}
    local matched = {}
    local seen = {}

    for _, pattern in ipairs(bundle.itemPatterns or {}) do
        for _, item in ipairs(results) do
            if item.name and not seen[item.name] and string.find(item.name, pattern) then
                seen[item.name] = true
                table.insert(matched, item)
                totalCOGS = totalCOGS + (item.materialCost or 0)
            end
        end
    end

    bundle.matchedItems = matched
    bundle.totalCOGS = totalCOGS
    bundle.suggestedPrice = math.floor(totalCOGS * (1 + (bundle.suggestedMarkupPct or 35) / 100))
end

-- Record a bundle sale
function BundleManager:RecordSale(nameOrIndex, salePrice)
    local bundle = self:FindBundle(nameOrIndex)
    if not bundle then
        FPT:Info("Bundle not found: '%s'", nameOrIndex)
        return
    end

    salePrice = salePrice or bundle.suggestedPrice

    bundle.timesSold = (bundle.timesSold or 0) + 1
    bundle.totalRevenue = (bundle.totalRevenue or 0) + salePrice

    -- Update global stats
    FPT.savedVars.stats.totalGoldEarned = FPT.savedVars.stats.totalGoldEarned + salePrice

    FPT:Info("Sale recorded: '%s' for %s. Total sales: %d",
        bundle.name, FPT:FormatGold(salePrice), bundle.timesSold)
end

-- Generate Discord-ready ad copy for a bundle
function BundleManager:GenerateBundleAdCopy(bundle)
    return string.format(
        "**WTS: %s** | %s | %d curated pieces, professionally arranged. " ..
        "Includes EHT template for instant installation. Price: %s | " ..
        "Whisper for portfolio tour!",
        bundle.name,
        bundle.description or bundle.theme or "",
        #(bundle.itemPatterns or {}),
        FPT:FormatGold(bundle.suggestedPrice)
    )
end
