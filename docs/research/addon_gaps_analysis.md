# ESO Addon Gaps: Comprehensive Development Analysis

## Executive Summary

After deep research across ESOUI, Reddit, official forums, and community databases, the ESO addon ecosystem reveals **three tiers of opportunity**: genuinely unserved needs, poorly-served needs with high friction solutions, and emerging markets (console launch June 2025). The most impactful development targets combine fragmented functionality into unified dashboards, replace abandoned high-value addons, or solve performance problems with existing tools.

---

## Tier 1: True Gaps — No Adequate Solution Exists

### 1. Unified Account Dashboard (Leo's Altholic Successor)
**Evidence strength: Very High**

Leo's Altholic was discontinued with no replacement. Players must now use 4-7 separate addons:
- Character Knowledge (motifs, recipes)
- Inventory Insight (cross-character inventory)
- WPamA (pledges, companion rapport)
- Craft Store (research timers)
- Pollox's Daily Quest Tracker (daily completion)
- Endeavor Tracker (endeavors)

**The gap**: No single interface shows "all my characters at a glance" with dailies done, research timers, currencies, skill points, and riding training status.

**Forum evidence**: Repeated requests for "Altholic replacement," explicit statements that existing solutions require logging into each character to sync data.

**Development scope**: Large — would need to aggregate data from multiple API sources, store per-character state, display in unified UI.

---

### 2. Per-Character Achievement Shadow Tracker
**Evidence strength: Very High (91-page forum thread)**

Update 33 (March 2022) made achievements account-wide, which **destroyed per-character completion tracking**. ZOS explicitly rejected restoring this functionality. The Character Achievements addon only shows archived pre-Update 33 data.

**The actual request**: "I want to know which delves THIS character has completed, not which ones my account has completed."

**Technical approach**: Shadow-track character activity post-U33, building local database of what each character genuinely accomplishes. Would need to hook into discovery events, quest completions, boss kills, etc.

**Quote from forums**: "Account-wide achievements are good. Account-wide COMPLETION is bad."

---

### 3. In-Game Build Theorycrafting Tool
**Evidence strength: High**

**Stoned** was discontinued — the only addon that allowed comparing gear combinations, calculating stats, and simulating builds without respeccing. No replacement exists.

Current alternatives are all external:
- ESO-Skillbook website
- Spreadsheets
- Manual testing on target dummies

**The gap**: Players cannot answer "what would my stats be if I equipped X set instead of Y" without actually owning and equipping the gear.

**Technical complexity**: High — requires calculating set bonuses, CP effects, buff interactions. But most data is available via API.

---

### 4. Lightweight Guild Store Unknown Item Filter
**Evidence strength: High**

Repeated complaints about Master Merchant causing 2-10 minute loading times. Arkadius' Trade Tools is lighter but still has issues (30-day history limit, no material cost tracking).

**The specific unmet need**: "I just want to stand at a guild trader and see which recipes/motifs/styles I don't know, without loading a massive trading database."

Players want a **simple overlay** that cross-references Character Knowledge data with guild store listings — not a full price history system.

**Technical scope**: Medium — hook guild store UI, compare against learned recipe/motif/style data, add visual indicators.

---

## Tier 2: Poorly Served — High Friction Solutions Exist

### 5. Companion Management Dashboard
**Current state**: Fragmented across 4+ addons
- CompanionInfo (active companion only)
- Companion Stuff Tracker (gear tracking)
- Improved Companion Rapport Information
- WPamA (includes rapport across characters)

**The gap**: No single view of "all my companions across all characters" showing gear, rapport, XP, and skills. Must summon each companion individually to see their status.

**Opportunity**: Unified companion manager that caches data across sessions.

---

### 6. Housing Storage Visibility at Crafting Stations
**Current state**: Players must physically check housing storage chests

**Request**: When at a crafting station, show materials in housing storage alongside bank and craft bag totals.

**Technical limitation**: API may not expose housing storage contents without being in the house. Needs investigation.

---

### 7. Motif/Style Completion Tracker
**Current state**: Style Tracker exists but uses limited "master character" system. No comprehensive view of:
- All motif chapters collected vs. missing
- Outfit styles by category
- Where to obtain missing styles

**Opportunity**: Visual completion tracker with acquisition locations, similar to what Destinations does for map completion.

---

## Tier 3: Takeover Opportunities — Abandoned Addons

| Addon | Last Update | Downloads | Gap |
|-------|-------------|-----------|-----|
| Leo's Altholic | Discontinued | High | Full character dashboard |
| PersonalAssistant | Discontinued | High | Unified automation (banking, junk, loot, repair) |
| Character Zone Tracker | Seeking maintainer | ~50K | Per-character delve/boss tracking |
| TraitBuddy 2.0 | Marked OBSOLETE | ~200K | Trait research tracking (author says "do not ask for features") |
| Settings Profiler | Author left 2019 | Medium | Per-character settings sync |

**Note**: Taking over abandoned addons is often faster than building new ones — existing user base, established functionality, known API patterns.

---

## Critical Technical Constraints (API Limitations)

Before developing, understand what ESO's addon API **cannot** do:

1. **No real-time file I/O** — Data only writes to disk on zone change, /reloadui, or logout. Cannot stream data externally.

2. **No network requests** — Cannot phone home, sync to cloud, or integrate with external services directly from the addon.

3. **Combat-restricted functions** — Many UI modification functions disabled during combat.

4. **No cross-account data sharing** — Each account's SavedVariables are isolated.

5. **Memory overhead matters** — Large data structures (like Master Merchant's sales history) cause loading time issues. Design for lazy loading.

**Implication**: Account-wide dashboards must sync via SavedVariables on character logout, meaning data is only as fresh as the last time you logged that character.

---

## Console Market Opportunity (June 2025)

Update 46 brings addon support to PS5/Xbox Series X|S. This is an **entirely new market** of players who have never had addon access.

**Constraints**:
- UI-based addons only (initially)
- Curated selection via ZOS uploader tool
- Performance-critical due to console hardware
- Case-sensitive file paths on PlayStation

**High-value console ports**:
1. Votan's Minimap (essential, high demand from console wishlist threads)
2. Lazy Writ Crafter (most-requested based on forum threads)
3. Destinations (map markers)
4. Combat Metrics (raiders need DPS meters)
5. Buff tracking (S'rendarr equivalent)

**First-mover advantage**: Whoever ports popular addons first to console will capture that user base.

---

## Recommended Development Priorities

### Immediate High-Value Targets

| Project | Effort | Demand Evidence | Competition |
|---------|--------|-----------------|-------------|
| Ultimate Account Dashboard | Large | Discontinued Altholic, 4-7 addon fragmentation | None adequate |
| Lightweight Unknown Filter | Medium | Master Merchant complaints, repeated forum requests | None (MM is overkill) |
| Console Minimap Port | Medium | #1 wishlist item in console addon threads | First-mover wins |
| Character Zone Tracker Takeover | Small | Author seeking maintainer | Maintenance only |

### Strategic Longer-Term

| Project | Effort | Demand Evidence | Notes |
|---------|--------|-----------------|-------|
| Per-Character Achievement Shadow | Large | 91-page forum thread, ZOS rejected fix | Technically complex |
| In-Game Theorycrafting | Large | Stoned discontinuation | High complexity, high value |
| Companion Dashboard | Medium | Fragmented solutions | Aggregation play |

---

## Evidence Quality Assessment

| Claim | Evidence Type | Confidence |
|-------|---------------|------------|
| Altholic replacement needed | Explicit discontinuation + forum requests | Very High |
| Per-character tracking demand | 91-page official thread + ZOS rejection | Very High |
| Master Merchant performance issues | Multiple forum threads, workarounds documented | Very High |
| Console addon demand | Official June 2025 launch + wishlist threads | Very High |
| Theorycrafting gap | Stoned discontinuation + external tool reliance | High |
| Housing storage visibility | Forum requests | Medium |
| Style tracker gaps | Forum requests | Medium |

---

## What This Research Cannot Tell You

1. **Actual addon download/usage statistics** — ESOUI doesn't expose detailed analytics
2. **Revenue potential** — ESO addons are free; monetization is through donations only
3. **API stability** — ZOS can break addons with any patch
4. **Development time estimates** — Depends heavily on your Lua/ESO API familiarity
5. **Console-specific API differences** — Documentation still emerging

---

## Recommended Next Steps

1. **Validate demand**: Post on ESOUI forums asking "Would you use X?" before building
2. **Check API feasibility**: Review wiki.esoui.com for required functions
3. **Prototype small**: Build minimum viable feature, release, iterate based on feedback
4. **Consider takeovers**: Contacting authors of abandoned addons may be faster than rebuilding
5. **Monitor console launch**: June 2025 is a hard deadline for first-mover advantage