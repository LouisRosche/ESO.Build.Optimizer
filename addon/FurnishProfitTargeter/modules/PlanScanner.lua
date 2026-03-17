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

-- Scan all known furnishing plans across all recipe lists (single pass)
function PlanScanner:ScanAllPlans()
    local plans = {}
    local seen = {} -- deduplicate by result item link

    local numRecipeLists = GetNumRecipeLists()

    for listIndex = 1, numRecipeLists do
        local listName, numRecipesInList = GetRecipeListInfo(listIndex)

        for recipeIndex = 1, numRecipesInList do
            -- GetRecipeInfo returns: known, recipeName, numIngredients,
            --   provisionerLevelReq, qualityReq, specialIngredientType
            -- NOTE: resultItemId is NOT returned here
            local known, recipeName, numIngredients = GetRecipeInfo(listIndex, recipeIndex)

            if known then
                -- Get the result item link to check if it's a furnishing
                local resultLink = GetRecipeResultItemLink(listIndex, recipeIndex, LINK_STYLE_BRACKETS)

                if resultLink and resultLink ~= "" and self:IsFurnishing(resultLink) then
                    -- Deduplicate by result link
                    if not seen[resultLink] then
                        seen[resultLink] = true

                        local resultItemId = GetItemLinkItemId(resultLink)

                        local plan = self:BuildPlanData(
                            listIndex, recipeIndex, recipeName,
                            numIngredients, resultItemId, resultLink
                        )
                        if plan then
                            table.insert(plans, plan)
                        end
                    end
                end
            end
        end
    end

    FPT:Debug("PlanScanner: found %d unique known furnishing plans", #plans)
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
    numIngredients, resultItemId, resultLink)

    -- Get material requirements
    local materials = {}
    local totalMaterialCount = 0

    for ingredientIndex = 1, numIngredients do
        -- ESO API: GetRecipeIngredientItemInfo (not GetRecipeIngredientInfo)
        local ingredientName, _, ingredientQuantity =
            GetRecipeIngredientItemInfo(listIndex, recipeIndex, ingredientIndex)
        local ingredientLink =
            GetRecipeIngredientItemLink(listIndex, recipeIndex, ingredientIndex, LINK_STYLE_BRACKETS)

        local ingredientItemId = nil
        if ingredientLink and ingredientLink ~= "" then
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

    -- Determine the furnishing's specialized type
    -- GetItemLinkSpecializedItemType is the correct ESO API function
    local _, specializedType = GetItemLinkItemType(resultLink)

    -- Detect which crafting type this recipe belongs to
    -- We infer from ingredient types since GetRecipeInfo doesn't return craft type
    local craftType = self:InferCraftType(materials)

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
-- Craft Type Inference
---------------------------------------------------------------------------

-- Infer crafting type from ingredient materials
-- Housing materials map to specific crafting stations
function PlanScanner:InferCraftType(materials)
    for _, mat in ipairs(materials) do
        local id = mat.itemId
        if id then
            -- Heartwood → Woodworking
            if id == 114889 then return CRAFTING_TYPE_WOODWORKING end
            -- Regulus → Blacksmithing
            if id == 114890 then return CRAFTING_TYPE_BLACKSMITHING end
            -- Bast → Clothier
            if id == 114891 then return CRAFTING_TYPE_CLOTHIER end
            -- Mundane Rune → Enchanting
            if id == 114892 then return CRAFTING_TYPE_ENCHANTING end
            -- Clean Pelts → Clothier
            if id == 114893 then return CRAFTING_TYPE_CLOTHIER end
            -- Decorative Wax → Provisioning
            if id == 114894 then return CRAFTING_TYPE_PROVISIONING end
            -- Ochre → Alchemy
            if id == 114895 then return CRAFTING_TYPE_ALCHEMY end
        end
    end
    return nil
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
        if string.find(lowerName, string.lower(tag), 1, true) then
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
        if string.find(lowerName, pattern, 1, true) then
            return true
        end
    end

    return false
end

-- Detect if item belongs to a high-demand architectural style
function PlanScanner:DetectHighDemandStyle(itemName)
    if not itemName then return false, nil end

    for _, style in ipairs(FPT.HIGH_DEMAND_STYLES) do
        if string.find(itemName, style, 1, true) then
            return true, style
        end
    end

    return false, nil
end

-- Get a summary of known plans by crafting type
function PlanScanner:GetPlanSummary()
    local plans = self:ScanAllPlans()
    local summary = {}

    for _, plan in ipairs(plans) do
        local craftName = plan.craftTypeName or "Unknown"
        summary[craftName] = (summary[craftName] or 0) + 1
    end

    return summary
end
