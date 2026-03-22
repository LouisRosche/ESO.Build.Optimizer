--[[
    Furnish Profit Targeter (FPT)
    Main Addon File

    Algorithmic furnishing profit calculator using sales velocity.
    Integrates with Master Merchant and Tamriel Trade Centre to identify
    the highest velocity-adjusted profit furnishing plans.

    Core metric: VelocityScore = ProfitMargin × SalesVelocity
    Run /fpt every Tuesday and Friday to recalibrate manufacturing queue.

    Author: ESO Build Optimizer Team
    Version: 1.0.0
    APIVersion: 101047 101048 101049
]]--

---------------------------------------------------------------------------
-- Addon Namespace
---------------------------------------------------------------------------

FurnishProfitTargeter = FurnishProfitTargeter or {}
local FPT = FurnishProfitTargeter

FPT.name = "FurnishProfitTargeter"
FPT.displayName = "Furnish Profit Targeter"
FPT.version = "1.0.0"
FPT.author = "ESO Build Optimizer Team"

-- Module references (populated when modules load)
FPT.PlanScanner = nil
FPT.PriceEngine = nil
FPT.VelocityCalculator = nil
FPT.ResultsUI = nil
FPT.BundleManager = nil
FPT.SupplyTracker = nil
FPT.MarketCopy = nil

---------------------------------------------------------------------------
-- Default SavedVariables
---------------------------------------------------------------------------

local defaultSavedVars = {
    settings = {
        enabled = true,
        verboseLogging = false,
        topNResults = 10,

        -- Velocity window: how many days of sales history to consider
        velocityWindowDays = 14,

        -- Minimum profit margin (gold) to consider an item worth listing
        minProfitMargin = 500,

        -- Minimum sales count in velocity window to consider an item liquid
        minSalesCount = 3,

        -- Price source priority: "mm" (Master Merchant) or "ttc" (TTC)
        primaryPriceSource = "mm",

        -- COD discount target (percentage below TTC average for starter zone buys)
        codDiscountPct = 15,

        -- Guild trader listing fee percentage (ESO default is ~7% for guild stores)
        guildTraderFeePct = 7,

        -- TTC listing-to-sales conversion factor (sell-through rate estimate)
        -- Used when MM data unavailable; 0.35 = ~35% of TTC listings result in sales
        ttcSellThroughRate = 0.35,

        -- Material price overrides (manually set floor prices)
        materialOverrides = {},

        -- Show notifications on Tuesday/Friday reminder
        showScheduleReminder = true,

        -- UI settings
        uiLocked = false,
        uiPosition = { x = 400, y = 200 },
        uiScale = 1.0,
        showResultsOnScan = true,
    },

    -- Cached scan results
    lastScanResults = {},
    lastScanTimestamp = 0,

    -- Bundle definitions (Room-in-a-Box)
    bundles = {},

    -- Supply chain tracking
    supplyChain = {
        codPurchases = {},
        materialInventory = {},
        dailyLog = {},
        totalSaved = 0,
        totalSpent = 0,
        totalUnits = 0,
    },

    -- Marketing templates
    marketing = {
        customTemplates = {},
        portfolioHome = "",
        adHistory = {},
    },

    -- Historical profit tracking
    profitHistory = {},

    -- Statistics
    stats = {
        totalScansRun = 0,
        totalItemsCrafted = 0,
        totalGoldEarned = 0,
        totalGoldSavedOnMaterials = 0,
    },
}

---------------------------------------------------------------------------
-- Constants
---------------------------------------------------------------------------

-- Key housing material item IDs
FPT.MATERIALS = {
    HEARTWOOD       = 114889,
    MUNDANE_RUNE    = 114892,
    DECORATIVE_WAX  = 114894,
    REGULUS          = 114890,
    BAST            = 114891,
    CLEAN_PELTS     = 114893,
    OCHRE           = 114895,
}

-- Material names for display
FPT.MATERIAL_NAMES = {
    [114889] = "Heartwood",
    [114892] = "Mundane Rune",
    [114894] = "Decorative Wax",
    [114890] = "Regulus",
    [114891] = "Bast",
    [114893] = "Clean Pelts",
    [114895] = "Ochre",
}

-- Furnishing crafting station types
FPT.CRAFT_TYPES = {
    BLACKSMITHING = CRAFTING_TYPE_BLACKSMITHING,
    CLOTHIER      = CRAFTING_TYPE_CLOTHIER,
    WOODWORKING   = CRAFTING_TYPE_WOODWORKING,
    ENCHANTING    = CRAFTING_TYPE_ENCHANTING,
    ALCHEMY       = CRAFTING_TYPE_ALCHEMY,
    PROVISIONING  = CRAFTING_TYPE_PROVISIONING,
    JEWELRYCRAFTING = CRAFTING_TYPE_JEWELRYCRAFTING,
}

-- Structural item category tags for Tier 1 bulk identification
FPT.STRUCTURAL_TAGS = {
    "wall", "floor", "platform", "stairs", "stairway",
    "column", "pillar", "arch", "ceiling", "foundation",
    "fence", "railing", "beam", "support", "plank",
}

-- Architectural styles in high demand post-Update 49
FPT.HIGH_DEMAND_STYLES = {
    "Alinor", "Elsweyr", "Solitude", "Colovian", "West Weald",
    "Solstice", "Necrom", "Apocrypha", "Telvanni", "Dwarven",
}

-- Starter zones for supply chain operations
FPT.STARTER_ZONES = {
    "Khenarthi's Roost", "Stros M'Kai", "Betnikh",
    "Bleakrock Isle", "Bal Foyen", "Vulkhel Guard",
}

-- Schedule days using (days + 4) % 7 formula:
-- Thu=4, Fri=5, Sat=6, Sun=0, Mon=1, Tue=2, Wed=3
FPT.SCHEDULE_DAYS = {
    TUESDAY = 2,
    FRIDAY  = 5,
}

-- Colors
FPT.COLORS = {
    GOLD     = "|cFFD700",
    GREEN    = "|c00FF00",
    RED      = "|cFF4444",
    CYAN     = "|c00FFFF",
    WHITE    = "|cFFFFFF",
    ORANGE   = "|cFF8C00",
    PURPLE   = "|cAA55FF",
    GRAY     = "|c999999",
    RESET    = "|r",
}

---------------------------------------------------------------------------
-- Local State
---------------------------------------------------------------------------

local isInitialized = false
local isPlayerActivated = false
local CreateSettingsPanel  -- forward declaration (defined after slash commands)

---------------------------------------------------------------------------
-- Utility Functions
---------------------------------------------------------------------------

local function DeepCopy(orig, seen)
    local origType = type(orig)
    local copy
    if origType == "table" then
        if seen and seen[orig] then return seen[orig] end
        copy = {}
        seen = seen or {}
        seen[orig] = copy
        for origKey, origValue in pairs(orig) do
            copy[DeepCopy(origKey, seen)] = DeepCopy(origValue, seen)
        end
    else
        copy = orig
    end
    return copy
end

-- Log ring buffer for post-crash debugging (persisted to SavedVars)
local LOG_RING_MAX = 200
local logRing = {}

local SV_MAX_STRING_LEN = 1900  -- ESO SavedVars crash on strings > 1999 bytes

local function AppendLog(level, msg)
    -- Truncate to prevent SavedVars nil-string crash
    if msg and #msg > SV_MAX_STRING_LEN then
        msg = string.sub(msg, 1, SV_MAX_STRING_LEN) .. "...[truncated]"
    end
    table.insert(logRing, {
        t = GetTimeStamp and GetTimeStamp() or 0,
        l = level,
        m = msg,
    })
    -- Prune oldest entries
    while #logRing > LOG_RING_MAX do
        table.remove(logRing, 1)
    end
end

function FPT:Debug(message, ...)
    local ok, formatted = pcall(string.format, message, ...)
    if not ok then formatted = message end

    AppendLog("D", formatted)

    if self.savedVars and self.savedVars.settings.verboseLogging then
        d(string.format("[FPT] %s", formatted))
    end
end

function FPT:Info(message, ...)
    local ok, formatted = pcall(string.format, message, ...)
    if not ok then formatted = message end

    AppendLog("I", formatted)
    d(string.format("%s[FPT]%s %s", self.COLORS.GOLD, self.COLORS.RESET, formatted))
end

function FPT:Error(message, ...)
    local ok, formatted = pcall(string.format, message, ...)
    if not ok then formatted = message end

    AppendLog("E", formatted)
    d(string.format("%s[FPT] ERROR:%s %s", self.COLORS.RED, self.COLORS.RESET, formatted))
end

-- Dump recent logs to chat (for bug reports)
function FPT:DumpLogs(count)
    count = count or 50
    local start = math.max(1, #logRing - count + 1)

    self:Info("%s===== FPT DEBUG LOG (last %d entries) =====%s",
        self.COLORS.GRAY, math.min(count, #logRing), self.COLORS.RESET)

    for i = start, #logRing do
        local entry = logRing[i]
        local levelColor = entry.l == "E" and self.COLORS.RED
            or entry.l == "D" and self.COLORS.GRAY
            or self.COLORS.RESET
        d(string.format("%s[%s]%s %s", levelColor, entry.l, self.COLORS.RESET, entry.m))
    end

    self:Info("Log buffer: %d/%d entries. Use /fpt exportlog to save to SavedVars.", #logRing, LOG_RING_MAX)
end

-- Export log ring to SavedVars for external retrieval
function FPT:ExportLogs()
    if self.savedVars then
        self.savedVars._debugLog = logRing
        self:Info("Exported %d log entries to SavedVariables.", #logRing)
        self:Info("Find them in: FurnishProfitTargeterSV._debugLog")
    end
end

-- Format gold amount with commas
function FPT:FormatGold(amount)
    if not amount then return "0g" end
    local formatted = tostring(math.floor(amount))
    local k
    while true do
        formatted, k = string.gsub(formatted, "^(-?%d+)(%d%d%d)", "%1,%2")
        if k == 0 then break end
    end
    return formatted .. "g"
end

-- Format dimensionless score with commas (not currency)
function FPT:FormatScore(score)
    if not score then return "0" end
    local formatted = tostring(math.floor(score))
    local k
    while true do
        formatted, k = string.gsub(formatted, "^(-?%d+)(%d%d%d)", "%1,%2")
        if k == 0 then break end
    end
    return formatted
end

-- Format percentage
function FPT:FormatPct(value)
    if not value then return "0%" end
    return string.format("%.1f%%", value * 100)
end

-- Get item link from item ID
function FPT:GetItemLinkFromId(itemId)
    if not itemId then return nil end
    return string.format("|H1:item:%d:0:0:0:0:0:0:0:0:0:0:0:0:0:0:0:0:0:0:0:0|h|h", itemId)
end

-- Check for Master Merchant availability
function FPT:HasMasterMerchant()
    return MasterMerchant ~= nil
end

-- Check for TTC availability
function FPT:HasTTC()
    return TamrielTradeCentrePrice ~= nil
end

-- Get current day of week (0=Sunday through 6=Saturday)
function FPT:GetDayOfWeek()
    local ts = GetTimeStamp()
    -- ESO epoch + Unix epoch offset, calculate day of week
    local days = math.floor(ts / 86400)
    return (days + 4) % 7  -- Jan 1 1970 was Thursday (4)
end

-- Check if today is a recommended scan day
function FPT:IsScanDay()
    local day = self:GetDayOfWeek()
    return day == self.SCHEDULE_DAYS.TUESDAY or day == self.SCHEDULE_DAYS.FRIDAY
end

---------------------------------------------------------------------------
-- Dependency Detection
---------------------------------------------------------------------------

local function CheckDependencies()
    local hasMM = FPT:HasMasterMerchant()
    local hasTTC = FPT:HasTTC()

    if not hasMM and not hasTTC then
        FPT:Error("No price data source detected!")
        FPT:Error("Install Master Merchant and/or Tamriel Trade Centre for price data.")
        return false
    end

    FPT:Debug("Price sources - MM: %s, TTC: %s",
        hasMM and "YES" or "NO",
        hasTTC and "YES" or "NO")

    return true
end

---------------------------------------------------------------------------
-- SavedVariables Management
---------------------------------------------------------------------------

-- Current SavedVariables schema version (increment on breaking changes)
local SAVEDVARS_VERSION = 1

-- Validate that a saved value has the expected type; reset to default if corrupt
local function ValidateField(sv, key, default)
    if sv[key] == nil then
        sv[key] = DeepCopy(default)
        return
    end

    local expectedType = type(default)
    local actualType = type(sv[key])

    -- Type mismatch = corruption; reset to default
    if expectedType ~= actualType then
        FPT:Debug("SavedVars: resetting corrupted field '%s' (expected %s, got %s)",
            tostring(key), expectedType, actualType)
        sv[key] = DeepCopy(default)
    end
end

-- Deep-merge nested tables: add missing keys from defaults, validate types
local function MergeDefaults(sv, defaults)
    if type(sv) ~= "table" or type(defaults) ~= "table" then return end

    for key, defaultValue in pairs(defaults) do
        if sv[key] == nil then
            sv[key] = DeepCopy(defaultValue)
        elseif type(defaultValue) == "table" and type(sv[key]) == "table" then
            -- Recurse for nested tables (but not arrays like codPurchases)
            -- Only merge if default has string keys (is a struct, not an array)
            local isStruct = false
            for k, _ in pairs(defaultValue) do
                if type(k) == "string" then
                    isStruct = true
                    break
                end
            end
            if isStruct then
                MergeDefaults(sv[key], defaultValue)
            end
        elseif type(defaultValue) ~= type(sv[key]) then
            -- Type mismatch on leaf value = corruption
            FPT:Debug("SavedVars: resetting corrupted '%s' (expected %s, got %s)",
                tostring(key), type(defaultValue), type(sv[key]))
            sv[key] = DeepCopy(defaultValue)
        end
    end
end

local function InitializeSavedVariables()
    -- Handle completely missing or corrupted root
    if type(FurnishProfitTargeterSV) ~= "table" then
        FPT:Debug("SavedVars: root was %s, resetting to defaults",
            type(FurnishProfitTargeterSV))
        FurnishProfitTargeterSV = DeepCopy(defaultSavedVars)
    end

    local sv = FurnishProfitTargeterSV

    -- Version migration: check if SavedVars need upgrading
    local savedVersion = sv._schemaVersion or 0
    if savedVersion < SAVEDVARS_VERSION then
        FPT:Debug("SavedVars: migrating from v%d to v%d", savedVersion, SAVEDVARS_VERSION)
        -- Future migrations go here:
        -- if savedVersion < 2 then MigrateV1toV2(sv) end
    end
    sv._schemaVersion = SAVEDVARS_VERSION

    -- Deep-merge all defaults (handles new fields, type corruption, nested structs)
    MergeDefaults(sv, defaultSavedVars)

    -- Validate critical numeric settings are within sane bounds
    local s = sv.settings
    if type(s.velocityWindowDays) ~= "number" or s.velocityWindowDays < 3 or s.velocityWindowDays > 30 then
        s.velocityWindowDays = defaultSavedVars.settings.velocityWindowDays
    end
    if type(s.topNResults) ~= "number" or s.topNResults < 5 or s.topNResults > 50 then
        s.topNResults = defaultSavedVars.settings.topNResults
    end
    if type(s.codDiscountPct) ~= "number" or s.codDiscountPct < 5 or s.codDiscountPct > 30 then
        s.codDiscountPct = defaultSavedVars.settings.codDiscountPct
    end
    if type(s.minProfitMargin) ~= "number" or s.minProfitMargin < 0 then
        s.minProfitMargin = defaultSavedVars.settings.minProfitMargin
    end
    if type(s.minSalesCount) ~= "number" or s.minSalesCount < 0 then
        s.minSalesCount = defaultSavedVars.settings.minSalesCount
    end
    if type(s.guildTraderFeePct) ~= "number" or s.guildTraderFeePct < 0 or s.guildTraderFeePct > 20 then
        s.guildTraderFeePct = defaultSavedVars.settings.guildTraderFeePct
    end
    if type(s.ttcSellThroughRate) ~= "number" or s.ttcSellThroughRate < 0.05 or s.ttcSellThroughRate > 1.0 then
        s.ttcSellThroughRate = defaultSavedVars.settings.ttcSellThroughRate
    end

    FPT.savedVars = sv
    FPT:Debug("SavedVariables initialized (schema v%d)", SAVEDVARS_VERSION)
end

---------------------------------------------------------------------------
-- Event Handlers
---------------------------------------------------------------------------

local function OnAddonLoaded(eventCode, addonName)
    if addonName ~= FPT.name then return end

    EVENT_MANAGER:UnregisterForEvent(FPT.name, EVENT_ADD_ON_LOADED)

    math.randomseed(GetGameTimeMilliseconds())

    InitializeSavedVariables()

    isInitialized = true
    FPT:Debug("Addon loaded")
end

local function OnPlayerActivated(eventCode, initial)
    if not isInitialized then return end
    if isPlayerActivated then return end

    isPlayerActivated = true
    EVENT_MANAGER:UnregisterForEvent(FPT.name, EVENT_PLAYER_ACTIVATED)

    -- Check dependencies
    local hasPriceData = CheckDependencies()

    -- Initialize modules
    if FPT.PlanScanner then
        FPT.PlanScanner:Initialize()
    end

    if FPT.PriceEngine then
        FPT.PriceEngine:Initialize()
    end

    if FPT.VelocityCalculator then
        FPT.VelocityCalculator:Initialize()
    end

    if FPT.ResultsUI then
        FPT.ResultsUI:Initialize()
    end

    if FPT.BundleManager then
        FPT.BundleManager:Initialize()
    end

    if FPT.SupplyTracker then
        FPT.SupplyTracker:Initialize()
    end

    if FPT.MarketCopy then
        FPT.MarketCopy:Initialize()
    end

    -- Show startup info
    FPT:Info("%sFurnish Profit Targeter%s v%s loaded", FPT.COLORS.GOLD, FPT.COLORS.RESET, FPT.version)

    if hasPriceData then
        FPT:Info("Price sources: %s%s%s",
            FPT:HasMasterMerchant() and (FPT.COLORS.GREEN .. "MM " .. FPT.COLORS.RESET) or "",
            (FPT:HasMasterMerchant() and FPT:HasTTC()) and "+ " or "",
            FPT:HasTTC() and (FPT.COLORS.GREEN .. "TTC" .. FPT.COLORS.RESET) or "")
    end

    -- Tuesday/Friday reminder
    if FPT.savedVars.settings.showScheduleReminder and FPT:IsScanDay() then
        FPT:Info("%s>>> SCAN DAY! Run /fpt to recalibrate your manufacturing queue <<<", FPT.COLORS.CYAN)
    end

    -- Create LAM settings panel (after modules are initialized)
    CreateSettingsPanel()
end

---------------------------------------------------------------------------
-- Slash Commands
---------------------------------------------------------------------------

SLASH_COMMANDS["/fpt"] = function(args)
    local cmd, param = string.match(args or "", "^(%S*)%s*(.*)$")
    cmd = string.lower(cmd or "")

    if cmd == "" or cmd == "scan" then
        -- Primary function: run the velocity profit scan
        FPT:RunScan()

    elseif cmd == "help" then
        FPT:Info("%sFurnish Profit Targeter%s v%s", FPT.COLORS.GOLD, FPT.COLORS.RESET, FPT.version)
        FPT:Info("Commands:")
        FPT:Info("  /fpt              - Run velocity profit scan (Top 10)")
        FPT:Info("  /fpt scan         - Same as above")
        FPT:Info("  /fpt top <N>      - Show top N results (default 10)")
        FPT:Info("  /fpt last         - Show last scan results")
        FPT:Info("  /fpt detail <N>   - Show detailed breakdown for item #N")
        FPT:Info("  /fpt materials    - Show current material spot prices")
        FPT:Info("  /fpt bundles      - List Room-in-a-Box bundles")
        FPT:Info("  /fpt bundle <name>- Show bundle details / create new")
        FPT:Info("  /fpt supply       - Show supply chain dashboard")
        FPT:Info("  /fpt cod          - Show COD purchase summary")
        FPT:Info("  /fpt ad           - Generate zone chat ad copy")
        FPT:Info("  /fpt portfolio    - Show portfolio home info")
        FPT:Info("  /fpt tier1        - Filter results: structural bulk only")
        FPT:Info("  /fpt stats        - Show lifetime profit statistics")
        FPT:Info("  /fpt settings     - Open settings panel")
        FPT:Info("  /fpt window       - Toggle results window")
        FPT:Info("  /fpt debug        - Toggle debug logging")
        FPT:Info("  /fpt log [N]      - Show last N log entries (default 50)")
        FPT:Info("  /fpt exportlog    - Save log buffer to SavedVars for bug reports")
        FPT:Info("  /fpt selftest     - Run internal pipeline diagnostics")
        FPT:Info("  /fpt health       - Show price source health status")
        FPT:Info("  /fpt help         - Show this help")

    elseif cmd == "top" then
        local n = tonumber(param) or 10
        FPT:RunScan(n)

    elseif cmd == "last" then
        FPT:ShowLastResults()

    elseif cmd == "detail" then
        local index = tonumber(param)
        if index then
            FPT:ShowItemDetail(index)
        else
            FPT:Info("Usage: /fpt detail <number>")
        end

    elseif cmd == "materials" or cmd == "mats" then
        FPT:ShowMaterialPrices()

    elseif cmd == "bundles" then
        if FPT.BundleManager then
            FPT.BundleManager:ListBundles()
        end

    elseif cmd == "bundle" then
        if FPT.BundleManager then
            if param and param ~= "" then
                FPT.BundleManager:ShowBundle(param)
            else
                FPT.BundleManager:ListBundles()
            end
        end

    elseif cmd == "supply" then
        if FPT.SupplyTracker then
            FPT.SupplyTracker:ShowDashboard()
        end

    elseif cmd == "cod" then
        if FPT.SupplyTracker then
            FPT.SupplyTracker:ShowCODSummary()
        end

    elseif cmd == "ad" or cmd == "adcopy" then
        if FPT.MarketCopy then
            FPT.MarketCopy:GenerateAd()
        end

    elseif cmd == "portfolio" then
        if FPT.MarketCopy then
            FPT.MarketCopy:ShowPortfolio()
        end

    elseif cmd == "tier1" or cmd == "structural" then
        FPT:RunScan(nil, true)

    elseif cmd == "stats" then
        FPT:ShowStats()

    elseif cmd == "settings" then
        FPT:OpenSettings()

    elseif cmd == "window" or cmd == "ui" then
        if FPT.ResultsUI then
            FPT.ResultsUI:Toggle()
        end

    elseif cmd == "debug" then
        FPT.savedVars.settings.verboseLogging = not FPT.savedVars.settings.verboseLogging
        FPT:Info("Debug logging: %s", FPT.savedVars.settings.verboseLogging and "ON" or "OFF")

    elseif cmd == "log" or cmd == "logs" then
        local count = tonumber(param) or 50
        FPT:DumpLogs(count)

    elseif cmd == "exportlog" then
        FPT:ExportLogs()

    elseif cmd == "selftest" or cmd == "test" then
        FPT:RunSelfTest()

    elseif cmd == "health" then
        FPT:ShowPriceHealth()

    else
        FPT:Info("Unknown command: %s. Type /fpt help for commands.", cmd)
    end
end

---------------------------------------------------------------------------
-- Core Scan Orchestrator
---------------------------------------------------------------------------

function FPT:RunScan(topN, structuralOnly)
    topN = topN or self.savedVars.settings.topNResults

    if not self:HasMasterMerchant() and not self:HasTTC() then
        self:Error("Cannot scan: no price data source available.")
        self:Error("Install Master Merchant or Tamriel Trade Centre.")
        return
    end

    self:Info("Scanning known furnishing plans...")

    -- Evict stale price cache entries before scanning to bound memory usage
    if self.PriceEngine and self.PriceEngine.EvictStaleEntries then
        self.PriceEngine:EvictStaleEntries()
    end

    -- Step 1: Iterate all known plans
    local plans = {}
    if self.PlanScanner then
        plans = self.PlanScanner:ScanAllPlans()
        self:Debug("Found %d known furnishing plans", #plans)
    else
        self:Error("PlanScanner module not loaded")
        return
    end

    if #plans == 0 then
        self:Info("No known furnishing plans found on this character.")
        return
    end

    -- Step 2: Calculate COGS and retail for each plan
    if not self.PriceEngine then
        self:Error("PriceEngine module not loaded")
        return
    end

    local priceErrors = 0
    for _, plan in ipairs(plans) do
        local ok, err = pcall(function()
            self.PriceEngine:CalculatePrices(plan)
        end)
        if not ok then
            priceErrors = priceErrors + 1
            self:Debug("Price error on '%s': %s", plan.name or "unknown", tostring(err))
            plan.materialCost = 0
            plan.retailPrice = 0
            plan.profitMargin = 0
            plan.roi = 0
            plan.netRevenue = 0
            plan.adjustedMargin = 0
            plan.adjustedROI = 0
            plan.profitPerMaterialUnit = 0
        end
    end

    if priceErrors > 0 then
        self:Debug("Pricing: %d/%d plans had errors (continuing with %d good plans)",
            priceErrors, #plans, #plans - priceErrors)
    end

    -- Step 3: Calculate velocity scores
    if not self.VelocityCalculator then
        self:Error("VelocityCalculator module not loaded")
        return
    end

    local scored = {}
    local ok, err = pcall(function()
        scored = self.VelocityCalculator:ScoreAll(plans, structuralOnly)
    end)

    if not ok then
        self:Error("Velocity scoring failed: %s", tostring(err))
        return
    end

    -- Step 4: Sort by velocity score descending, take top N
    table.sort(scored, function(a, b) return a.velocityScore > b.velocityScore end)

    local results = {}
    for i = 1, math.min(topN, #scored) do
        results[i] = scored[i]
    end

    -- Save results
    self.savedVars.lastScanResults = results
    self.savedVars.lastScanTimestamp = GetTimeStamp()
    self.savedVars.stats.totalScansRun = self.savedVars.stats.totalScansRun + 1

    -- Validate result integrity (logs issues without blocking)
    self:ValidateScanResults(results)

    -- Display results
    self:DisplayScanResults(results, structuralOnly)

    -- Show in UI window if enabled
    if self.ResultsUI and self.savedVars.settings.showResultsOnScan then
        self.ResultsUI:ShowResults(results)
    end
end

function FPT:DisplayScanResults(results, structuralOnly)
    if #results == 0 then
        self:Info("No profitable items found matching criteria.")
        return
    end

    local header = structuralOnly and "STRUCTURAL BULK" or "VELOCITY PROFIT"
    self:Info("%s========== %s TOP %d ==========%s",
        self.COLORS.GOLD, header, #results, self.COLORS.RESET)

    for i, item in ipairs(results) do
        local tierTag = ""
        if item.isStructural then
            tierTag = self.COLORS.CYAN .. "[T1-BULK] " .. self.COLORS.RESET
        end

        local styleTag = ""
        if item.isHighDemandStyle then
            styleTag = self.COLORS.ORANGE .. "[HOT] " .. self.COLORS.RESET
        end

        self:Info("%s#%d%s %s%s%s",
            self.COLORS.GOLD, i, self.COLORS.RESET,
            tierTag, styleTag,
            item.itemLink or item.name or "Unknown")

        self:Info("   Margin: %s%s%s | Velocity: %s%d sales/%dd%s | Score: %s%s%s",
            self.COLORS.GREEN, self:FormatGold(item.profitMargin), self.COLORS.RESET,
            self.COLORS.CYAN, item.salesCount or 0, self.savedVars.settings.velocityWindowDays, self.COLORS.RESET,
            self.COLORS.GOLD, self:FormatScore(item.velocityScore), self.COLORS.RESET)

        self:Info("   COGS: %s | Retail: %s | ROI: %s",
            self:FormatGold(item.materialCost),
            self:FormatGold(item.retailPrice),
            self:FormatPct(item.roi))
    end

    -- Aggregated portfolio summary
    if self.VelocityCalculator then
        local stats = self.VelocityCalculator:GetSummaryStats(results)
        local feePct = self.savedVars.settings.guildTraderFeePct or 7
        local windowDays = self.savedVars.settings.velocityWindowDays or 14

        self:Info("")
        self:Info("%s--- Portfolio Summary ---%s", self.COLORS.GRAY, self.COLORS.RESET)
        self:Info("  Avg Margin: %s%s%s (after %d%% fee: %s%s%s)",
            self.COLORS.GREEN, self:FormatGold(stats.avgMargin), self.COLORS.RESET,
            feePct,
            self.COLORS.GREEN, self:FormatGold(stats.avgMargin * (1 - feePct / 100)), self.COLORS.RESET)
        self:Info("  Avg Velocity: %s%.1f sales/%dd%s",
            self.COLORS.CYAN, stats.avgVelocity, windowDays, self.COLORS.RESET)
        self:Info("  Est. Weekly Gross: %s%s%s",
            self.COLORS.GOLD, self:FormatGold(stats.totalEstWeeklyProfit), self.COLORS.RESET)

        local weeklyNet = stats.totalEstWeeklyProfit * (1 - feePct / 100)
        self:Info("  Est. Weekly Net (-%d%% fee): %s%s%s",
            feePct,
            self.COLORS.GREEN, self:FormatGold(weeklyNet), self.COLORS.RESET)
    end

    self:Info("%s===========================================%s", self.COLORS.GOLD, self.COLORS.RESET)
    self:Info("Scanned %d plans. Use /fpt detail <N> for breakdown.", #results)
end

function FPT:ShowLastResults()
    local results = self.savedVars.lastScanResults
    if not results or #results == 0 then
        self:Info("No previous scan results. Run /fpt to scan.")
        return
    end

    local ts = self.savedVars.lastScanTimestamp
    local age = GetTimeStamp() - ts
    local ageStr
    if age < 3600 then
        ageStr = string.format("%d minutes ago", math.floor(age / 60))
    elseif age < 86400 then
        ageStr = string.format("%.1f hours ago", age / 3600)
    else
        ageStr = string.format("%.1f days ago", age / 86400)
    end

    self:Info("Last scan: %s (%d results)", ageStr, #results)
    self:DisplayScanResults(results)
end

function FPT:ShowItemDetail(index)
    local results = self.savedVars.lastScanResults
    if not results or #results == 0 then
        self:Info("No scan results. Run /fpt first.")
        return
    end

    local item = results[index]
    if not item then
        self:Info("Invalid item number. Range: 1-%d", #results)
        return
    end

    self:Info("%s===== ITEM DETAIL: #%d =====%s", self.COLORS.GOLD, index, self.COLORS.RESET)
    self:Info("Item: %s", item.itemLink or item.name or "Unknown")
    self:Info("Craft Type: %s", item.craftTypeName or "Unknown")

    if item.isStructural then
        self:Info("Category: %sTier 1 - Structural Bulk%s", self.COLORS.CYAN, self.COLORS.RESET)
    end
    if item.isHighDemandStyle then
        self:Info("Style: %s%s (High Demand)%s", self.COLORS.ORANGE, item.styleName or "Unknown", self.COLORS.RESET)
    end

    self:Info("")
    self:Info("%s--- Cost Breakdown (COGS) ---%s", self.COLORS.GRAY, self.COLORS.RESET)
    if item.materials then
        for _, mat in ipairs(item.materials) do
            local name = FPT.MATERIAL_NAMES[mat.itemId] or mat.name or "Unknown"
            self:Info("  %s x%d @ %s = %s",
                name, mat.quantity, self:FormatGold(mat.unitPrice), self:FormatGold(mat.totalPrice))
        end
    end
    self:Info("  %sTotal COGS: %s%s", self.COLORS.RED, self:FormatGold(item.materialCost), self.COLORS.RESET)

    self:Info("")
    self:Info("%s--- Revenue ---%s", self.COLORS.GRAY, self.COLORS.RESET)
    self:Info("  Retail Price (MM): %s", self:FormatGold(item.mmPrice))
    self:Info("  Retail Price (TTC): %s", self:FormatGold(item.ttcPrice))
    self:Info("  %sUsed Price: %s%s", self.COLORS.GREEN, self:FormatGold(item.retailPrice), self.COLORS.RESET)

    self:Info("")
    self:Info("%s--- Velocity Analysis ---%s", self.COLORS.GRAY, self.COLORS.RESET)
    self:Info("  Profit Margin: %s%s%s", self.COLORS.GREEN, self:FormatGold(item.profitMargin), self.COLORS.RESET)
    self:Info("  Sales Count (%dd): %s%d%s",
        self.savedVars.settings.velocityWindowDays,
        self.COLORS.CYAN, item.salesCount or 0, self.COLORS.RESET)
    self:Info("  %sVelocity Score: %s%s",
        self.COLORS.GOLD, self:FormatScore(item.velocityScore), self.COLORS.RESET)
    self:Info("  ROI: %s", self:FormatPct(item.roi))

    -- Fee-adjusted analysis
    local feePct = self.savedVars.settings.guildTraderFeePct or 7
    local feeMultiplier = 1 - (feePct / 100)
    local netRevenue = (item.retailPrice or 0) * feeMultiplier
    local adjustedMargin = netRevenue - (item.materialCost or 0)

    self:Info("")
    self:Info("%s--- Fee-Adjusted Analysis (-%d%% guild fee) ---%s", self.COLORS.GRAY, feePct, self.COLORS.RESET)
    self:Info("  Net Revenue: %s", self:FormatGold(netRevenue))
    self:Info("  Adjusted Margin: %s%s%s", self.COLORS.GREEN, self:FormatGold(adjustedMargin), self.COLORS.RESET)
    if item.materialCost and item.materialCost > 0 then
        local adjustedROI = adjustedMargin / item.materialCost
        self:Info("  Adjusted ROI: %s", self:FormatPct(adjustedROI))
    end

    -- Material efficiency
    if item.totalMaterialCount and item.totalMaterialCount > 0 and adjustedMargin > 0 then
        local profitPerUnit = adjustedMargin / item.totalMaterialCount
        self:Info("  Profit/Material Unit: %s%s%s", self.COLORS.CYAN, self:FormatGold(profitPerUnit), self.COLORS.RESET)
    end

    if item.salesCount and item.salesCount > 0 and adjustedMargin > 0 then
        local windowDays = self.savedVars.settings.velocityWindowDays or 14
        if windowDays > 0 then
            local dailyProfit = (adjustedMargin * item.salesCount) / windowDays
            local weeklyProfit = dailyProfit * 7
            self:Info("  Est. Daily Net Profit: %s%s%s", self.COLORS.GREEN, self:FormatGold(dailyProfit), self.COLORS.RESET)
            self:Info("  Est. Weekly Net Profit: %s%s%s", self.COLORS.GREEN, self:FormatGold(weeklyProfit), self.COLORS.RESET)
        end
    end
end

function FPT:ShowMaterialPrices()
    self:Info("%s===== MATERIAL SPOT PRICES =====%s", self.COLORS.GOLD, self.COLORS.RESET)

    if not self.PriceEngine then
        self:Error("PriceEngine module not loaded")
        return
    end

    for itemId, name in pairs(self.MATERIAL_NAMES) do
        local mmPrice = self.PriceEngine:GetMMPrice(itemId)
        local ttcPrice = self.PriceEngine:GetTTCPrice(itemId)
        local override = self.savedVars.settings.materialOverrides[itemId]

        local priceStr = ""
        if mmPrice then
            priceStr = priceStr .. string.format("MM: %s%s%s", self.COLORS.GREEN, self:FormatGold(mmPrice), self.COLORS.RESET)
        end
        if ttcPrice then
            if priceStr ~= "" then priceStr = priceStr .. " | " end
            priceStr = priceStr .. string.format("TTC: %s%s%s", self.COLORS.CYAN, self:FormatGold(ttcPrice), self.COLORS.RESET)
        end
        if override then
            priceStr = priceStr .. string.format(" | Override: %s%s%s", self.COLORS.ORANGE, self:FormatGold(override), self.COLORS.RESET)
        end

        if priceStr == "" then
            priceStr = self.COLORS.RED .. "No data" .. self.COLORS.RESET
        end

        self:Info("  %s: %s", name, priceStr)
    end

    -- Show COD discount target
    local discountPct = self.savedVars.settings.codDiscountPct
    self:Info("")
    self:Info("COD Target Discount: %s%d%%%s below market", self.COLORS.ORANGE, discountPct, self.COLORS.RESET)
end

function FPT:ShowStats()
    local stats = self.savedVars.stats
    self:Info("%s===== LIFETIME STATISTICS =====%s", self.COLORS.GOLD, self.COLORS.RESET)
    self:Info("  Total Scans: %d", stats.totalScansRun)
    self:Info("  Items Crafted: %d", stats.totalItemsCrafted)
    self:Info("  Gold Earned: %s%s%s", self.COLORS.GREEN, self:FormatGold(stats.totalGoldEarned), self.COLORS.RESET)
    self:Info("  Gold Saved (COD): %s%s%s", self.COLORS.GREEN, self:FormatGold(stats.totalGoldSavedOnMaterials), self.COLORS.RESET)
end

function FPT:OpenSettings()
    -- If LibAddonMenu is available, open settings panel
    local LAM = LibAddonMenu2
    if LAM then
        LAM:OpenToPanel(FPT.settingsPanel)
    else
        self:Info("Settings via commands:")
        self:Info("  Top N results: %d (change with /fpt top <N>)", self.savedVars.settings.topNResults)
        self:Info("  Velocity window: %d days", self.savedVars.settings.velocityWindowDays)
        self:Info("  Min profit margin: %s", self:FormatGold(self.savedVars.settings.minProfitMargin))
        self:Info("  Min sales count: %d", self.savedVars.settings.minSalesCount)
        self:Info("  Price source: %s", self.savedVars.settings.primaryPriceSource)
        self:Info("  Guild trader fee: %d%%", self.savedVars.settings.guildTraderFeePct)
        self:Info("  TTC sell-through rate: %.0f%%", self.savedVars.settings.ttcSellThroughRate * 100)
        self:Info("  COD discount: %d%%", self.savedVars.settings.codDiscountPct)
    end
end

---------------------------------------------------------------------------
-- Internal Diagnostics
---------------------------------------------------------------------------

function FPT:RunSelfTest()
    self:Info("%s===== FPT SELF-TEST =====%s", self.COLORS.GOLD, self.COLORS.RESET)

    local passed = 0
    local failed = 0
    local warnings = 0

    local function check(name, ok, detail)
        if ok then
            passed = passed + 1
            self:Debug("  PASS: %s", name)
        else
            failed = failed + 1
            self:Info("  %sFAIL:%s %s - %s", self.COLORS.RED, self.COLORS.RESET, name, detail or "")
        end
    end

    local function warn(name, detail)
        warnings = warnings + 1
        self:Info("  %sWARN:%s %s - %s", self.COLORS.ORANGE, self.COLORS.RESET, name, detail or "")
    end

    -- T1: Module availability
    check("PlanScanner loaded", self.PlanScanner ~= nil, "Module not registered")
    check("PriceEngine loaded", self.PriceEngine ~= nil, "Module not registered")
    check("VelocityCalculator loaded", self.VelocityCalculator ~= nil, "Module not registered")
    check("ResultsUI loaded", self.ResultsUI ~= nil, "Module not registered")
    check("BundleManager loaded", self.BundleManager ~= nil, "Module not registered")
    check("SupplyTracker loaded", self.SupplyTracker ~= nil, "Module not registered")
    check("MarketCopy loaded", self.MarketCopy ~= nil, "Module not registered")

    -- T2: Price source availability
    local hasMM = self:HasMasterMerchant()
    local hasTTC = self:HasTTC()
    check("At least one price source", hasMM or hasTTC, "No MM or TTC detected")
    if not hasMM then warn("Master Merchant", "Not loaded (TTC-only mode)") end
    if not hasTTC then warn("TTC", "Not loaded (MM-only mode)") end

    -- T3: SavedVars integrity
    check("SavedVars initialized", self.savedVars ~= nil, "savedVars is nil")
    if self.savedVars then
        check("Settings table exists", type(self.savedVars.settings) == "table", "settings corrupted")
        check("Stats table exists", type(self.savedVars.stats) == "table", "stats corrupted")
        check("SupplyChain table exists", type(self.savedVars.supplyChain) == "table", "supplyChain corrupted")

        -- T4: Settings bounds validation
        local s = self.savedVars.settings
        check("velocityWindowDays in range", s.velocityWindowDays >= 3 and s.velocityWindowDays <= 30,
            string.format("value=%s", tostring(s.velocityWindowDays)))
        check("guildTraderFeePct in range", s.guildTraderFeePct >= 0 and s.guildTraderFeePct <= 20,
            string.format("value=%s", tostring(s.guildTraderFeePct)))
        check("ttcSellThroughRate in range", s.ttcSellThroughRate >= 0.05 and s.ttcSellThroughRate <= 1.0,
            string.format("value=%s", tostring(s.ttcSellThroughRate)))
        check("codDiscountPct in range", s.codDiscountPct >= 5 and s.codDiscountPct <= 30,
            string.format("value=%s", tostring(s.codDiscountPct)))
    end

    -- T5: Price engine smoke test (try pricing a known material)
    if self.PriceEngine then
        local testItemId = self.MATERIALS.HEARTWOOD  -- 114889
        local price, source = self.PriceEngine:GetBestPrice(testItemId)
        check("Can query material price", price ~= nil,
            string.format("Heartwood returned nil from %s", source or "no source"))
        if price then
            check("Material price is positive", price > 0,
                string.format("Heartwood price=%s", tostring(price)))
            if price > 10000 then
                warn("Material price suspiciously high",
                    string.format("Heartwood=%s (expected < 10,000)", self:FormatGold(price)))
            end
        end
    end

    -- T6: Plan scanner smoke test
    if self.PlanScanner then
        local plans = self.PlanScanner:ScanAllPlans()
        check("PlanScanner returns table", type(plans) == "table", "ScanAllPlans returned " .. type(plans))
        if #plans > 0 then
            local sample = plans[1]
            check("Plan has name", sample.name ~= nil, "First plan missing name")
            check("Plan has materials", sample.materials ~= nil and #sample.materials > 0,
                "First plan missing materials")
            check("Plan has itemLink", sample.itemLink ~= nil, "First plan missing itemLink")
        else
            warn("No known plans", "Character may not know any furnishing recipes")
        end
    end

    -- T7: Formula invariant checks
    -- Verify that fee multiplier is < 1 (fee reduces revenue, never increases it)
    local feePct = self.savedVars and self.savedVars.settings.guildTraderFeePct or 7
    local feeMultiplier = 1 - (feePct / 100)
    check("Fee multiplier < 1", feeMultiplier < 1 and feeMultiplier > 0,
        string.format("feeMultiplier=%s (expected 0 < x < 1)", tostring(feeMultiplier)))

    -- T8: Last scan results integrity
    if self.savedVars and self.savedVars.lastScanResults then
        local results = self.savedVars.lastScanResults
        if #results > 0 then
            local hasNegativeScore = false
            local hasNilMargin = false
            local hasSortError = false
            for i, item in ipairs(results) do
                if (item.velocityScore or 0) < 0 then hasNegativeScore = true end
                if item.profitMargin == nil then hasNilMargin = true end
                if i > 1 and (item.velocityScore or 0) > (results[i-1].velocityScore or 0) then
                    hasSortError = true
                end
            end
            check("No negative velocity scores", not hasNegativeScore, "Found item with negative velocityScore")
            check("No nil profit margins", not hasNilMargin, "Found item with nil profitMargin")
            check("Results sorted descending", not hasSortError, "Results not properly sorted by velocityScore")
        end
    end

    -- Summary
    self:Info("")
    local total = passed + failed
    if failed == 0 then
        self:Info("%sSELF-TEST PASSED:%s %d/%d checks OK, %d warnings",
            self.COLORS.GREEN, self.COLORS.RESET, passed, total, warnings)
    else
        self:Info("%sSELF-TEST FAILED:%s %d/%d checks OK, %d failed, %d warnings",
            self.COLORS.RED, self.COLORS.RESET, passed, total, failed, warnings)
    end

    self:Info("Log buffer: %d/%d entries. Use /fpt exportlog to save for bug reports.", #logRing, LOG_RING_MAX)
end

function FPT:ShowPriceHealth()
    self:Info("%s===== PRICE SOURCE HEALTH =====%s", self.COLORS.GOLD, self.COLORS.RESET)

    if not self.PriceEngine then
        self:Error("PriceEngine module not loaded")
        return
    end

    local hasMM = self:HasMasterMerchant()
    local hasTTC = self:HasTTC()

    self:Info("  Master Merchant: %s",
        hasMM and (self.COLORS.GREEN .. "AVAILABLE" .. self.COLORS.RESET)
        or (self.COLORS.RED .. "NOT LOADED" .. self.COLORS.RESET))
    self:Info("  Tamriel Trade Centre: %s",
        hasTTC and (self.COLORS.GREEN .. "AVAILABLE" .. self.COLORS.RESET)
        or (self.COLORS.RED .. "NOT LOADED" .. self.COLORS.RESET))
    self:Info("  Primary source: %s", self.savedVars.settings.primaryPriceSource)

    -- Test each material for price availability
    self:Info("")
    self:Info("%s--- Material Price Coverage ---%s", self.COLORS.GRAY, self.COLORS.RESET)

    local totalMats = 0
    local coveredMM = 0
    local coveredTTC = 0
    local coveredAny = 0

    for itemId, name in pairs(self.MATERIAL_NAMES) do
        totalMats = totalMats + 1
        local mmPrice = self.PriceEngine:GetMMPrice(itemId)
        local ttcPrice = self.PriceEngine:GetTTCPrice(itemId)
        local hasAny = mmPrice or ttcPrice

        if mmPrice then coveredMM = coveredMM + 1 end
        if ttcPrice then coveredTTC = coveredTTC + 1 end
        if hasAny then coveredAny = coveredAny + 1 end

        local status = ""
        if mmPrice and ttcPrice then
            local diff = math.abs(mmPrice - ttcPrice)
            local avg = (mmPrice + ttcPrice) / 2
            local divergence = avg > 0 and (diff / avg * 100) or 0
            if divergence > 30 then
                status = string.format("%s DIVERGENT (%.0f%%)%s", self.COLORS.RED, divergence, self.COLORS.RESET)
            else
                status = string.format("%s OK%s", self.COLORS.GREEN, self.COLORS.RESET)
            end
            self:Info("  %s: MM=%s TTC=%s %s", name,
                self:FormatGold(mmPrice), self:FormatGold(ttcPrice), status)
        elseif mmPrice then
            self:Info("  %s: MM=%s %sTTC=N/A%s", name,
                self:FormatGold(mmPrice), self.COLORS.ORANGE, self.COLORS.RESET)
        elseif ttcPrice then
            self:Info("  %s: %sMM=N/A%s TTC=%s", name,
                self.COLORS.ORANGE, self.COLORS.RESET, self:FormatGold(ttcPrice))
        else
            self:Info("  %s: %sNO DATA%s", name, self.COLORS.RED, self.COLORS.RESET)
        end
    end

    -- Coverage summary
    self:Info("")
    self:Info("%s--- Coverage Summary ---%s", self.COLORS.GRAY, self.COLORS.RESET)
    self:Info("  MM coverage: %d/%d materials (%.0f%%)", coveredMM, totalMats, totalMats > 0 and (coveredMM / totalMats * 100) or 0)
    self:Info("  TTC coverage: %d/%d materials (%.0f%%)", coveredTTC, totalMats, totalMats > 0 and (coveredTTC / totalMats * 100) or 0)
    self:Info("  Any source: %d/%d materials (%.0f%%)", coveredAny, totalMats, totalMats > 0 and (coveredAny / totalMats * 100) or 0)

    -- Cache info
    if self.PriceEngine.GetCacheSize then
        local cacheSize = self.PriceEngine:GetCacheSize()
        self:Info("  Price cache: %d entries", cacheSize)
    end

    if coveredAny < totalMats then
        self:Info("")
        self:Info("%sWarning: Some materials have no price data. Scan results may be incomplete.%s",
            self.COLORS.ORANGE, self.COLORS.RESET)
    end
end

---------------------------------------------------------------------------
-- Scan Result Validation
---------------------------------------------------------------------------

-- Validate scan results for data integrity issues
-- Called automatically after each scan; logs issues without blocking results
function FPT:ValidateScanResults(results)
    if not results or #results == 0 then return end

    local issues = 0

    for i, item in ipairs(results) do
        -- Detect impossible margins (retail < COGS shouldn't score > 0)
        if (item.profitMargin or 0) < 0 and (item.velocityScore or 0) > 0 then
            issues = issues + 1
            self:Debug("Integrity: item #%d '%s' has negative margin (%s) but positive velocity score",
                i, item.name or "unknown", self:FormatGold(item.profitMargin))
        end

        -- Detect suspiciously high ROI (possible data error)
        if (item.roi or 0) > 100 then
            self:Debug("Integrity: item #%d '%s' has ROI of %.0f%% (>10,000%% - possible pricing error)",
                i, item.name or "unknown", (item.roi or 0) * 100)
        end

        -- Detect zero COGS with non-zero retail (materials have no price data)
        if (item.materialCost or 0) == 0 and (item.retailPrice or 0) > 0 then
            issues = issues + 1
            self:Debug("Integrity: item #%d '%s' has 0 COGS but %s retail (missing material prices?)",
                i, item.name or "unknown", self:FormatGold(item.retailPrice))
        end

        -- Detect stale velocity data (salesCount > 0 but both prices nil)
        if (item.salesCount or 0) > 0 and (item.mmPrice or 0) == 0 and (item.ttcPrice or 0) == 0 then
            self:Debug("Integrity: item #%d '%s' has %d sales but no retail price data",
                i, item.name or "unknown", item.salesCount)
        end
    end

    if issues > 0 then
        self:Debug("Scan validation: %d potential data integrity issues (see debug log)", issues)
    end
end

---------------------------------------------------------------------------
-- LAM Settings Panel
---------------------------------------------------------------------------

CreateSettingsPanel = function()
    local LAM = LibAddonMenu2
    if not LAM then return end

    local panelData = {
        type = "panel",
        name = FPT.displayName,
        displayName = FPT.COLORS.GOLD .. FPT.displayName .. FPT.COLORS.RESET,
        author = FPT.author,
        version = FPT.version,
        registerForRefresh = true,
    }

    FPT.settingsPanel = LAM:RegisterAddonPanel(FPT.name .. "Options", panelData)

    local optionsTable = {
        {
            type = "header",
            name = "Scan Settings",
        },
        {
            type = "slider",
            name = "Top N Results",
            tooltip = "Number of items to show in scan results",
            min = 5, max = 50, step = 1,
            getFunc = function() return FPT.savedVars.settings.topNResults end,
            setFunc = function(value) FPT.savedVars.settings.topNResults = value end,
        },
        {
            type = "slider",
            name = "Velocity Window (Days)",
            tooltip = "How many days of sales history to analyze",
            min = 3, max = 30, step = 1,
            getFunc = function() return FPT.savedVars.settings.velocityWindowDays end,
            setFunc = function(value) FPT.savedVars.settings.velocityWindowDays = value end,
        },
        {
            type = "editbox",
            name = "Minimum Profit Margin (Gold)",
            tooltip = "Items below this margin are excluded from results",
            getFunc = function() return tostring(FPT.savedVars.settings.minProfitMargin) end,
            setFunc = function(value) FPT.savedVars.settings.minProfitMargin = tonumber(value) or 500 end,
        },
        {
            type = "slider",
            name = "Minimum Sales Count",
            tooltip = "Minimum sales in velocity window to consider an item liquid",
            min = 1, max = 20, step = 1,
            getFunc = function() return FPT.savedVars.settings.minSalesCount end,
            setFunc = function(value) FPT.savedVars.settings.minSalesCount = value end,
        },
        {
            type = "header",
            name = "Price Sources",
        },
        {
            type = "dropdown",
            name = "Primary Price Source",
            tooltip = "Which addon to prefer for retail pricing",
            choices = { "Master Merchant", "Tamriel Trade Centre" },
            choicesValues = { "mm", "ttc" },
            getFunc = function() return FPT.savedVars.settings.primaryPriceSource end,
            setFunc = function(value) FPT.savedVars.settings.primaryPriceSource = value end,
        },
        {
            type = "header",
            name = "Financial Model",
        },
        {
            type = "slider",
            name = "Guild Trader Fee (%)",
            tooltip = "Guild store listing fee percentage deducted from revenue (ESO default ~7%)",
            min = 0, max = 20, step = 1,
            getFunc = function() return FPT.savedVars.settings.guildTraderFeePct end,
            setFunc = function(value) FPT.savedVars.settings.guildTraderFeePct = value end,
        },
        {
            type = "slider",
            name = "TTC Sell-Through Rate (%)",
            tooltip = "Estimated percentage of TTC listings that result in actual sales (used as fallback when MM data unavailable)",
            min = 5, max = 100, step = 5,
            getFunc = function() return math.floor(FPT.savedVars.settings.ttcSellThroughRate * 100) end,
            setFunc = function(value) FPT.savedVars.settings.ttcSellThroughRate = value / 100 end,
        },
        {
            type = "header",
            name = "Supply Chain",
        },
        {
            type = "slider",
            name = "COD Discount Target (%)",
            tooltip = "Target discount percentage below TTC average for starter zone purchases",
            min = 5, max = 30, step = 1,
            getFunc = function() return FPT.savedVars.settings.codDiscountPct end,
            setFunc = function(value) FPT.savedVars.settings.codDiscountPct = value end,
        },
        {
            type = "header",
            name = "Display",
        },
        {
            type = "checkbox",
            name = "Show Results Window on Scan",
            tooltip = "Automatically show the results UI window when running a scan",
            getFunc = function() return FPT.savedVars.settings.showResultsOnScan end,
            setFunc = function(value) FPT.savedVars.settings.showResultsOnScan = value end,
        },
        {
            type = "checkbox",
            name = "Tuesday/Friday Reminder",
            tooltip = "Show reminder on scan days",
            getFunc = function() return FPT.savedVars.settings.showScheduleReminder end,
            setFunc = function(value) FPT.savedVars.settings.showScheduleReminder = value end,
        },
    }

    LAM:RegisterOptionControls(FPT.name .. "Options", optionsTable)
end

---------------------------------------------------------------------------
-- Event Registration & Init
---------------------------------------------------------------------------

local function RegisterEvents()
    EVENT_MANAGER:RegisterForEvent(FPT.name, EVENT_ADD_ON_LOADED, OnAddonLoaded)
    EVENT_MANAGER:RegisterForEvent(FPT.name, EVENT_PLAYER_ACTIVATED, OnPlayerActivated)
end

RegisterEvents()
