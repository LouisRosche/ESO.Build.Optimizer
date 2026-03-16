--[[
    Furnish Profit Targeter - Velocity Calculator Module

    Core algorithm: VelocityScore = ProfitMargin × SalesVelocity

    Applies the velocity multiplier to shift valuation from static profit
    to expected yield over time, prioritizing liquidity and inventory turnover.

    Author: ESO Build Optimizer Team
    Version: 1.0.0
]]--

---------------------------------------------------------------------------
-- Module Setup
---------------------------------------------------------------------------

local FPT = FurnishProfitTargeter
local VelocityCalculator = {}
FPT.VelocityCalculator = VelocityCalculator

---------------------------------------------------------------------------
-- Initialization
---------------------------------------------------------------------------

function VelocityCalculator:Initialize()
    FPT:Debug("VelocityCalculator initialized")
end

---------------------------------------------------------------------------
-- Sales Velocity Measurement
---------------------------------------------------------------------------

-- Get sales velocity (transaction count) for an item within the configured window
function VelocityCalculator:GetSalesVelocity(plan)
    local windowDays = FPT.savedVars.settings.velocityWindowDays
    local salesCount = 0

    -- Primary: Master Merchant confirmed sales
    if FPT.PriceEngine and FPT:HasMasterMerchant() then
        salesCount = FPT.PriceEngine:GetMMSalesCount(
            plan.itemLink or plan.resultItemId,
            windowDays
        )
    end

    -- Fallback: TTC listing count as demand proxy (less reliable)
    if salesCount == 0 and FPT.PriceEngine and FPT:HasTTC() then
        local listingCount = FPT.PriceEngine:GetTTCListingCount(
            plan.itemLink or plan.resultItemId
        )
        -- TTC listings are NOT sales; apply a conversion factor
        -- Typical sell-through rate is ~30-40% for furnishings
        salesCount = math.floor(listingCount * 0.35)
    end

    return salesCount
end

---------------------------------------------------------------------------
-- Core Velocity Score Calculation
---------------------------------------------------------------------------

--[[
    The velocity score formula:

    VelocityScore = ProfitMargin × SalesCount

    Where:
    - ProfitMargin = RetailPrice - MaterialCOGS (already calculated by PriceEngine)
    - SalesCount = Number of confirmed sales in the trailing velocity window

    This metric answers: "How much total profit can I expect from this item
    across multiple sales in the given time period?"

    A 5,000g margin item selling 50x/week = 250,000 velocity score
    A 100,000g margin item selling 1x/quarter ≈ 1,538 velocity score

    The velocity score clearly favors the high-turnover item.
]]--

function VelocityCalculator:CalculateScore(plan)
    local settings = FPT.savedVars.settings

    -- Get sales velocity
    local salesCount = self:GetSalesVelocity(plan)
    plan.salesCount = salesCount

    -- Apply minimum thresholds
    if plan.profitMargin < settings.minProfitMargin then
        plan.velocityScore = 0
        plan.excludeReason = "below_min_margin"
        return 0
    end

    if salesCount < settings.minSalesCount then
        plan.velocityScore = 0
        plan.excludeReason = "below_min_sales"
        return 0
    end

    -- Core formula: Margin × Velocity
    local velocityScore = plan.profitMargin * salesCount

    -- Apply style bonus: high-demand styles get a 20% boost
    if plan.isHighDemandStyle then
        velocityScore = velocityScore * 1.20
    end

    -- Apply structural bonus: Tier 1 bulk items get a 10% boost
    -- (they tend to sell in stacks, so actual volume is higher)
    if plan.isStructural then
        velocityScore = velocityScore * 1.10
    end

    plan.velocityScore = velocityScore
    plan.excludeReason = nil

    return velocityScore
end

---------------------------------------------------------------------------
-- Batch Scoring
---------------------------------------------------------------------------

-- Score all plans and return only those that meet thresholds
function VelocityCalculator:ScoreAll(plans, structuralOnly)
    local scored = {}

    for _, plan in ipairs(plans) do
        -- Skip if filtering structural only
        if structuralOnly and not plan.isStructural then
            -- skip non-structural
        else
            local score = self:CalculateScore(plan)
            if score > 0 then
                table.insert(scored, plan)
            end
        end
    end

    FPT:Debug("VelocityCalculator: %d of %d plans scored above threshold",
        #scored, #plans)

    return scored
end

---------------------------------------------------------------------------
-- Analytics Helpers
---------------------------------------------------------------------------

-- Get estimated daily profit for a plan
function VelocityCalculator:GetDailyProfit(plan)
    local windowDays = FPT.savedVars.settings.velocityWindowDays
    if plan.salesCount and plan.salesCount > 0 and plan.profitMargin then
        return (plan.profitMargin * plan.salesCount) / windowDays
    end
    return 0
end

-- Get estimated weekly profit for a plan
function VelocityCalculator:GetWeeklyProfit(plan)
    return self:GetDailyProfit(plan) * 7
end

-- Categorize a plan's velocity tier
function VelocityCalculator:GetVelocityTier(plan)
    local windowDays = FPT.savedVars.settings.velocityWindowDays
    local dailySales = (plan.salesCount or 0) / windowDays

    if dailySales >= 5 then
        return "ULTRA-HIGH", FPT.COLORS.GOLD
    elseif dailySales >= 2 then
        return "HIGH", FPT.COLORS.GREEN
    elseif dailySales >= 0.5 then
        return "MEDIUM", FPT.COLORS.CYAN
    elseif dailySales > 0 then
        return "LOW", FPT.COLORS.ORANGE
    else
        return "DEAD", FPT.COLORS.RED
    end
end

-- Generate velocity summary statistics for a set of scored plans
function VelocityCalculator:GetSummaryStats(scoredPlans)
    if #scoredPlans == 0 then
        return { count = 0, totalScore = 0, avgMargin = 0, avgVelocity = 0 }
    end

    local totalScore = 0
    local totalMargin = 0
    local totalSales = 0

    for _, plan in ipairs(scoredPlans) do
        totalScore = totalScore + (plan.velocityScore or 0)
        totalMargin = totalMargin + (plan.profitMargin or 0)
        totalSales = totalSales + (plan.salesCount or 0)
    end

    return {
        count = #scoredPlans,
        totalScore = totalScore,
        avgMargin = totalMargin / #scoredPlans,
        avgVelocity = totalSales / #scoredPlans,
        totalEstWeeklyProfit = (totalScore / FPT.savedVars.settings.velocityWindowDays) * 7,
    }
end
