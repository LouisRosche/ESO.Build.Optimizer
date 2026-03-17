--[[
    Furnish Profit Targeter - Market Copy Module

    Generates psychologically optimized zone chat advertising copy,
    manages portfolio home information, and provides Discord-ready
    marketing templates for all three product tiers.

    Author: ESO Build Optimizer Team
    Version: 1.0.0
]]--

---------------------------------------------------------------------------
-- Module Setup
---------------------------------------------------------------------------

local FPT = FurnishProfitTargeter
local MarketCopy = {}
FPT.MarketCopy = MarketCopy

---------------------------------------------------------------------------
-- Ad Template Library
---------------------------------------------------------------------------

-- Pre-built, psychologically optimized ad templates
local AD_TEMPLATES = {
    -- Tier 1: Bulk Structural
    bulk_update49 = {
        name = "Update 49 Bulk Structural",
        target = "General housing players",
        template = "[Update 49] Need to fill those new housing slots? Selling bulk %STYLE% structural walls and custom Room-in-a-Box bundles! Whisper for Discord portfolio link!",
        notes = "Peak conversion template. Use in major cities during prime hours.",
    },
    bulk_builder = {
        name = "Builder's Supply",
        target = "Active builders",
        template = "WTS Bulk Housing Structures: %STYLE% walls, platforms, stairs - stacks of 5/10 available. One-stop shop for your build project! Whisper for inventory.",
        notes = "Targets players actively building. Use in housing-heavy zones.",
    },
    bulk_restock = {
        name = "Restock Notification",
        target = "Repeat customers",
        template = "RESTOCKED: Fresh batch of %STYLE% structural pieces ready! Walls, floors, platforms in bulk. Whisper or COD your order!",
        notes = "Use when you've just crafted a new batch.",
    },

    -- Tier 2: Room-in-a-Box
    bundle_showcase = {
        name = "Bundle Showcase",
        target = "Aesthetic-focused players",
        template = "WTS Custom Room-in-a-Box bundles! Fully themed, pre-designed rooms with EHT auto-install. Currently offering: %BUNDLES%. Visit my portfolio home to preview! Whisper for details.",
        notes = "List 2-3 bundle names. Always include portfolio CTA.",
    },
    bundle_new = {
        name = "New Bundle Launch",
        target = "Housing enthusiasts",
        template = "NEW! '%BUNDLE_NAME%' Room-in-a-Box: %DESCRIPTION%. Includes all furniture + free EHT installation. Limited availability - whisper now!",
        notes = "Use when launching a new bundle design.",
    },

    -- Tier 3: Commission Services
    commission_general = {
        name = "Decorator Services",
        target = "Wealthy players",
        template = "Professional Housing Decorator: Full-service custom builds from cozy apartments to epic mansions. Free consultation + portfolio tour. Prices start at 2M gold. Whisper for booking!",
        notes = "Cast a wide net. Adjust starting price based on market.",
    },
    commission_premium = {
        name = "Premium Commissions",
        target = "Whale demographic",
        template = "Elite Decorator Available: Specializing in Notable Homes and complete estate builds. Portfolio includes 50+ completed projects. Budget consultations starting at 10M gold. Whisper for exclusive tour.",
        notes = "Only use in endgame hubs (Craglorn, trial zones). High-value targeting.",
    },

    -- Special/Seasonal
    seasonal_event = {
        name = "Event Tie-In",
        template = "Get your home event-ready! Selling themed furniture bundles and bulk decorations for %EVENT%. Custom builds available. Whisper for portfolio!",
        notes = "Replace %EVENT% with current ESO event name.",
    },
}

---------------------------------------------------------------------------
-- Initialization
---------------------------------------------------------------------------

function MarketCopy:Initialize()
    -- Load custom templates if any
    local marketing = FPT.savedVars.marketing
    if not marketing.customTemplates then marketing.customTemplates = {} end
    if not marketing.portfolioHome then marketing.portfolioHome = "" end
    if not marketing.adHistory then marketing.adHistory = {} end

    FPT:Debug("MarketCopy initialized with %d built-in + %d custom templates",
        self:CountTemplates(), #marketing.customTemplates)
end

---------------------------------------------------------------------------
-- Ad Generation
---------------------------------------------------------------------------

-- Generate the primary zone chat ad
function MarketCopy:GenerateAd(templateName)
    FPT:Info("%s===== ZONE CHAT AD COPY =====%s", FPT.COLORS.GOLD, FPT.COLORS.RESET)

    if templateName and AD_TEMPLATES[templateName] then
        self:ShowTemplate(templateName)
        return
    end

    -- Show all templates organized by tier
    FPT:Info("")
    FPT:Info("%s--- Tier 1: Bulk Structural ---%s", FPT.COLORS.CYAN, FPT.COLORS.RESET)
    self:ShowTemplate("bulk_update49")
    self:ShowTemplate("bulk_builder")
    self:ShowTemplate("bulk_restock")

    FPT:Info("")
    FPT:Info("%s--- Tier 2: Room-in-a-Box ---%s", FPT.COLORS.PURPLE, FPT.COLORS.RESET)
    self:ShowTemplate("bundle_showcase")
    self:ShowTemplate("bundle_new")

    FPT:Info("")
    FPT:Info("%s--- Tier 3: Commissions ---%s", FPT.COLORS.GOLD, FPT.COLORS.RESET)
    self:ShowTemplate("commission_general")
    self:ShowTemplate("commission_premium")

    FPT:Info("")
    FPT:Info("%s--- Seasonal ---%s", FPT.COLORS.ORANGE, FPT.COLORS.RESET)
    self:ShowTemplate("seasonal_event")

    -- Show custom templates
    local custom = FPT.savedVars.marketing.customTemplates
    if #custom > 0 then
        FPT:Info("")
        FPT:Info("%s--- Custom Templates ---%s", FPT.COLORS.GREEN, FPT.COLORS.RESET)
        for i, tmpl in ipairs(custom) do
            FPT:Info("  %d. %s%s%s", i, FPT.COLORS.WHITE, tmpl.name or "Unnamed", FPT.COLORS.RESET)
            FPT:Info("     %s", self:FillTemplate(tmpl.template))
        end
    end

    FPT:Info("")
    FPT:Info("%sReplace %%STYLE%%, %%BUNDLES%%, etc. with your current inventory.%s",
        FPT.COLORS.GRAY, FPT.COLORS.RESET)
    FPT:Info("%sBest times: Tuesday evening (post-flip) and Friday evening (weekend start).%s",
        FPT.COLORS.GRAY, FPT.COLORS.RESET)
end

function MarketCopy:ShowTemplate(templateName)
    local tmpl = AD_TEMPLATES[templateName]
    if not tmpl then return end

    local filledText = self:FillTemplate(tmpl.template)

    FPT:Info("  %s[%s]%s %s",
        FPT.COLORS.ORANGE, tmpl.name, FPT.COLORS.RESET,
        tmpl.target and ("(" .. tmpl.target .. ")") or "")
    FPT:Info("  %s%s%s", FPT.COLORS.WHITE, filledText, FPT.COLORS.RESET)
    if tmpl.notes then
        FPT:Info("  %s%s%s", FPT.COLORS.GRAY, tmpl.notes, FPT.COLORS.RESET)
    end
end

-- Fill template placeholders with current data
function MarketCopy:FillTemplate(template)
    if not template then return "" end

    local filled = template

    -- Helper: escape % in replacement strings for gsub safety
    -- In Lua, % is special in gsub replacements (%1 = capture).
    -- Unescaped % from item names would crash with "invalid use of '%'"
    local function safeReplace(str, pattern, replacement)
        -- Escape any % in the replacement to %%
        local safe = string.gsub(replacement, "%%", "%%%%")
        return string.gsub(str, pattern, safe)
    end

    -- Fill %STYLE% with a top-selling style from last scan
    local topStyle = self:GetTopStyle()
    filled = safeReplace(filled, "%%STYLE%%", topStyle or "Alinor")

    -- Fill %BUNDLES% with bundle names
    local bundleNames = self:GetBundleNameList()
    filled = safeReplace(filled, "%%BUNDLES%%", bundleNames or "themed bundles")

    -- Fill %BUNDLE_NAME% with first bundle
    local firstBundle = self:GetFirstBundleName()
    filled = safeReplace(filled, "%%BUNDLE_NAME%%", firstBundle or "Custom Theme")

    -- Fill %DESCRIPTION% with first bundle description
    local firstDesc = self:GetFirstBundleDescription()
    filled = safeReplace(filled, "%%DESCRIPTION%%", firstDesc or "curated themed furniture set")

    -- Fill %EVENT% with placeholder
    filled = safeReplace(filled, "%%EVENT%%", "[Current Event]")

    return filled
end

---------------------------------------------------------------------------
-- Data Helpers
---------------------------------------------------------------------------

function MarketCopy:GetTopStyle()
    local results = FPT.savedVars.lastScanResults
    if not results then return nil end

    -- Count styles in top results
    local styleCounts = {}
    for _, item in ipairs(results) do
        if item.styleName then
            styleCounts[item.styleName] = (styleCounts[item.styleName] or 0) + 1
        end
    end

    -- Find most common
    local topStyle, topCount = nil, 0
    for style, count in pairs(styleCounts) do
        if count > topCount then
            topStyle = style
            topCount = count
        end
    end

    return topStyle
end

function MarketCopy:GetBundleNameList()
    local bundles = FPT.savedVars.bundles
    if not bundles or #bundles == 0 then return nil end

    local names = {}
    for i = 1, math.min(3, #bundles) do
        table.insert(names, bundles[i].name)
    end

    return table.concat(names, ", ")
end

function MarketCopy:GetFirstBundleName()
    local bundles = FPT.savedVars.bundles
    if bundles and #bundles > 0 then
        return bundles[1].name
    end
    return nil
end

function MarketCopy:GetFirstBundleDescription()
    local bundles = FPT.savedVars.bundles
    if bundles and #bundles > 0 then
        return bundles[1].description
    end
    return nil
end

function MarketCopy:CountTemplates()
    local count = 0
    for _ in pairs(AD_TEMPLATES) do count = count + 1 end
    return count
end

---------------------------------------------------------------------------
-- Portfolio Home
---------------------------------------------------------------------------

function MarketCopy:ShowPortfolio()
    local marketing = FPT.savedVars.marketing

    FPT:Info("%s===== PORTFOLIO HOME =====%s", FPT.COLORS.GOLD, FPT.COLORS.RESET)

    if marketing.portfolioHome and marketing.portfolioHome ~= "" then
        FPT:Info("Portfolio Home: %s%s%s", FPT.COLORS.GREEN, marketing.portfolioHome, FPT.COLORS.RESET)
    else
        FPT:Info("No portfolio home set.")
        FPT:Info("Set with: /fpt portfolio set <house name>")
    end

    FPT:Info("")
    FPT:Info("%s--- Portfolio Best Practices ---%s", FPT.COLORS.GRAY, FPT.COLORS.RESET)
    FPT:Info("  1. Use a medium-large home divided into themed Showrooms")
    FPT:Info("  2. Each showroom = one Room-in-a-Box template")
    FPT:Info("  3. Keep lighting dramatic for screenshots")
    FPT:Info("  4. Place a guest book / message board near entrance")
    FPT:Info("  5. Update showrooms when adding new bundle designs")

    FPT:Info("")
    FPT:Info("%s--- Invite Script ---%s", FPT.COLORS.GRAY, FPT.COLORS.RESET)
    FPT:Info("  Visit my primary residence to see the catalogue!")
    FPT:Info("  %s@YourName's %s%s", FPT.COLORS.CYAN, marketing.portfolioHome or "<House Name>", FPT.COLORS.RESET)
end

-- Set portfolio home
function MarketCopy:SetPortfolio(houseName)
    FPT.savedVars.marketing.portfolioHome = houseName
    FPT:Info("Portfolio home set to: %s", houseName)
end

---------------------------------------------------------------------------
-- Discord Marketing Helpers
---------------------------------------------------------------------------

-- Generate a full Discord WTS post
function MarketCopy:GenerateDiscordPost()
    local bundles = FPT.savedVars.bundles
    local portfolio = FPT.savedVars.marketing.portfolioHome

    FPT:Info("%s===== DISCORD WTS POST =====%s", FPT.COLORS.GOLD, FPT.COLORS.RESET)

    local post = "**Housing Furnishings & Decorating Services**\n\n"
    post = post .. "**Tier 1 - Bulk Structural:**\n"
    post = post .. "Stacks of 5/10 available: walls, platforms, stairs, columns\n"
    post = post .. "Styles: Alinor, Elsweyr, Colovian, Solstice, and more\n\n"

    if bundles and #bundles > 0 then
        post = post .. "**Tier 2 - Room-in-a-Box Bundles:**\n"
        for _, bundle in ipairs(bundles) do
            post = post .. string.format("- %s (%s) - %s\n",
                bundle.name, bundle.tier, FPT:FormatGold(bundle.suggestedPrice))
        end
        post = post .. "All bundles include EHT template for instant installation!\n\n"
    end

    post = post .. "**Tier 3 - Custom Commissions:**\n"
    post = post .. "Full-service decoration from 2M gold. Notable homes welcome.\n\n"

    if portfolio and portfolio ~= "" then
        post = post .. "**Portfolio:** Visit my " .. portfolio .. " for showroom tours!\n"
    end

    post = post .. "\nWhisper in-game or DM here for pricing!"

    FPT:Info(post)
end
