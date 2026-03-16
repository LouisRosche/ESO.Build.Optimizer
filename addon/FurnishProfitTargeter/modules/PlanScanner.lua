--[[
    Furnish Profit Targeter - Plan Scanner Module

    Iterates through every known furnishing plan the character has learned.
    Extracts item IDs, material requirements, crafting station types,
    and categorizes items (structural, decorative, lighting, etc.)

    Author: ESO Build Optimizer Team
    Version: 1.0.0
]]--

---------------------------------------------------------------------------
-- Module Setup
---------------------------------------------------------------------------

local FPT = FurnishProfitTargeter
local PlanScanner = {}
FPT.PlanScanner = PlanScanner

---------------------------------------------------------------------------
-- Constants
---------------------------------------------------------------------------

-- Furnishing category IDs from ESO API
local CATEGORY_NAMES = {
    [SPECIALIZED_ITEMTYPE_FURNISHING_CRAFTING_STATION]    = "Crafting Station",
    [SPECIALIZED_ITEMTYPE_FURNISHING_LIGHT]               = "Lighting",
    [SPECIALIZED_ITEMTYPE_FURNISHING_ORNAMENTAL]          = "Ornamental",
    [SPECIALIZED_ITEMTYPE_FURNISHING_SEATING]             = "Seating",
    [SPECIALIZED_ITEMTYPE_FURNISHING_TARGET_DUMMY]        = "Target Dummy",
}

-- Crafting type display names
local CRAFT_TYPE_NAMES = {
    [CRAFTING_TYPE_BLACKSMITHING]  = "Blacksmithing",
    [CRAFTING_TYPE_CLOTHIER]       = "Clothier",
    [CRAFTING_TYPE_WOODWORKING]    = "Woodworking",
    [CRAFTING_TYPE_ENCHANTING]     = "Enchanting",
    [CRAFTING_TYPE_ALCHEMY]        = "Alchemy",
    [CRAFTING_TYPE_PROVISIONING]   = "Provisioning",
    [CRAFTING_TYPE_JEWELRYCRAFTING] = "Jewelry Crafting",
}

---------------------------------------------------------------------------
-- Initialization
---------------------------------------------------------------------------

function PlanScanner:Initialize()
    FPT:Debug("PlanScanner initialized")
end

---------------------------------------------------------------------------
-- Core Scanning
---------------------------------------------------------------------------

-- Scan all known furnishing plans across all crafting types
function PlanScanner:ScanAllPlans()
    local plans = {}

    -- Iterate through each crafting type that can produce furnishings
    for craftType = 1, 7 do
        local craftPlans = self:ScanCraftType(craftType)
        for _, plan in ipairs(craftPlans) do
            table.insert(plans, plan)
        end
    end

    FPT:Debug("PlanScanner: found %d total known plans", #plans)
    return plans
end

-- Scan furnishing plans for a specific crafting type
function PlanScanner:ScanCraftType(craftType)
    local plans = {}

    -- Get the number of known furnishing recipes for this craft type
    local numRecipes = GetNumRecipeLists()

    for listIndex = 1, numRecipes do
        local listName, numRecipesInList = GetRecipeListInfo(listIndex)

        for recipeIndex = 1, numRecipesInList do
            local known, recipeName, numIngredients, _, _, _, resultItemId =
                GetRecipeInfo(listIndex, recipeIndex)

            if known and resultItemId and resultItemId > 0 then
                -- Check if this recipe produces a furnishing
                local resultLink = GetRecipeResultItemLink(listIndex, recipeIndex, LINK_STYLE_BRACKETS)

                if resultLink and self:IsFurnishing(resultLink) then
                    local plan = self:BuildPlanData(
                        listIndex, recipeIndex, recipeName,
                        numIngredients, resultItemId, resultLink, craftType
                    )
                    if plan then
                        table.insert(plans, plan)
                    end
                end
            end
        end
    end

    return plans
end

-- Check if an item link is a furnishing
function PlanScanner:IsFurnishing(itemLink)
    if not itemLink then return false end
    local itemType = GetItemLinkItemType(itemLink)
    return itemType == ITEMTYPE_FURNISHING
end

-- Build comprehensive plan data for a single recipe
function PlanScanner:BuildPlanData(listIndex, recipeIndex, recipeName,
    numIngredients, resultItemId, resultLink, craftType)

    -- Get material requirements
    local materials = {}
    local totalMaterialCount = 0

    for ingredientIndex = 1, numIngredients do
        local ingredientName, _, ingredientQuantity =
            GetRecipeIngredientInfo(listIndex, recipeIndex, ingredientIndex)
        local ingredientLink =
            GetRecipeIngredientItemLink(listIndex, recipeIndex, ingredientIndex, LINK_STYLE_BRACKETS)

        local ingredientItemId = nil
        if ingredientLink then
            ingredientItemId = GetItemLinkItemId(ingredientLink)
        end

        table.insert(materials, {
            name = ingredientName,
            itemId = ingredientItemId,
            itemLink = ingredientLink,
            quantity = ingredientQuantity or 1,
            -- Prices filled in by PriceEngine
            unitPrice = 0,
            totalPrice = 0,
        })

        totalMaterialCount = totalMaterialCount + (ingredientQuantity or 1)
    end

    -- Get item quality and other info
    local quality = GetItemLinkDisplayQuality(resultLink)
    local itemName = GetItemLinkName(resultLink)

    -- Determine specialized type (lighting, seating, etc.)
    local specializedType = GetItemLinkFurnishingLimitType(resultLink)

    -- Detect if structural
    local isStructural = self:IsStructuralItem(itemName, resultLink)

    -- Detect high-demand style
    local isHighDemandStyle, styleName = self:DetectHighDemandStyle(itemName)

    return {
        -- Identity
        listIndex = listIndex,
        recipeIndex = recipeIndex,
        resultItemId = resultItemId,
        itemLink = resultLink,
        name = itemName or recipeName,

        -- Crafting info
        craftType = craftType,
        craftTypeName = CRAFT_TYPE_NAMES[craftType] or "Unknown",

        -- Materials
        materials = materials,
        totalMaterialCount = totalMaterialCount,

        -- Classification
        quality = quality,
        specializedType = specializedType,
        specializedTypeName = CATEGORY_NAMES[specializedType] or "General",
        isStructural = isStructural,
        isHighDemandStyle = isHighDemandStyle,
        styleName = styleName,

        -- Pricing (filled by PriceEngine)
        materialCost = 0,
        retailPrice = 0,
        mmPrice = 0,
        ttcPrice = 0,
        profitMargin = 0,
        roi = 0,

        -- Velocity (filled by VelocityCalculator)
        salesCount = 0,
        velocityScore = 0,
    }
end

---------------------------------------------------------------------------
-- Item Classification
---------------------------------------------------------------------------

-- Check if item name matches structural building component patterns
function PlanScanner:IsStructuralItem(itemName, itemLink)
    if not itemName then return false end

    local lowerName = string.lower(itemName)

    -- Check against structural tags
    for _, tag in ipairs(FPT.STRUCTURAL_TAGS) do
        if string.find(lowerName, string.lower(tag)) then
            return true
        end
    end

    -- Additional structural patterns
    local structuralPatterns = {
        "divider", "partition", "screen", "doorway", "door frame",
        "awning", "canopy", "roof", "tile", "brick", "stone block",
        "shelf", "counter", "table, grand", "table, long",
    }

    for _, pattern in ipairs(structuralPatterns) do
        if string.find(lowerName, pattern) then
            return true
        end
    end

    return false
end

-- Detect if item belongs to a high-demand architectural style
function PlanScanner:DetectHighDemandStyle(itemName)
    if not itemName then return false, nil end

    for _, style in ipairs(FPT.HIGH_DEMAND_STYLES) do
        if string.find(itemName, style) then
            return true, style
        end
    end

    return false, nil
end

-- Get a summary of known plans by crafting type
function PlanScanner:GetPlanSummary()
    local summary = {}

    for craftType = 1, 7 do
        local plans = self:ScanCraftType(craftType)
        local craftName = CRAFT_TYPE_NAMES[craftType] or "Unknown"
        summary[craftName] = #plans
    end

    return summary
end
