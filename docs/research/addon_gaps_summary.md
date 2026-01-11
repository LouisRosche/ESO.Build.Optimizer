# ESO Addon Gaps: What Players Need But Don't Have

Elder Scrolls Online's addon ecosystem has mature coverage for individual features but **significant gaps in unified account-wide tracking** represent the largest development opportunity. Research across ESOUI, Reddit, and official forums reveals consistent player frustration with fragmented multi-character management, abandoned essential addons, and missing feature-rich tools. The clearest evidence of demand comes from the discontinuation of Leo's Altholic—a comprehensive character dashboard with no successor—and the loss of per-character achievement tracking after Update 33, which generated 91+ pages of forum debate.

---

## The altoholic problem remains unsolved

The single most glaring gap in ESO's addon ecosystem is the lack of a comprehensive account-wide dashboard. **Leo's Altholic**, which provided unified tracking for dailies, riding training, research timers, currencies, skill points, and character stats, was discontinued and has no adequate replacement. Players with 10+ characters currently need to install 4-6 separate addons—Character Knowledge, Inventory Insight, Craft Store, Account Achievements, Character Zone Tracker—and manually log into each character to synchronize data.

The demand evidence is substantial. Character Zone Tracker's author silvereyes explicitly noted they "no longer play ESO" and the addon is "looking for a new maintainer." Account Achievements requires players to "manually update progress by clicking the button in the addon's settings" rather than tracking automatically. Craft Store and similar addons only populate data after logging into each character individually, creating tedious maintenance for altoholics.

What players repeatedly request across forums includes:
- Single dashboard showing all characters' daily/weekly completion status
- Research timers visible without character switching
- Currency totals across all characters in one view
- Cross-character crafting material tracking including housing storage
- Automatic data synchronization without manual relogging

---

## Update 33 created a tracking void that addons haven't filled

When ZOS implemented Account-Wide Achievements in March 2022, they inadvertently destroyed per-character progression tracking that completionists relied upon. Forum sentiment crystallized around one distinction: **"Account-wide achievements are good. Account-wide COMPLETION is bad."** New alts immediately show zone completion for delves, world bosses, and world events they've never visited.

ZOS explicitly rejected restoring per-character tracking, stating it would "nullify the database improvements that Account Wide Achievements bring." The Character Achievements addon only displays archived data from before Update 33—it cannot track new achievements earned per-character. This creates a genuine gap: players who want to complete content on specific characters have no way to track what that character has actually accomplished versus inherited account progress.

The evidence of sustained demand appears in forum threads with **38+ upvotes** on account-wide titles, the 91-page official Q&A thread, and repeated Reddit discussions asking how to restore per-character tracking. This represents a development opportunity for an addon that shadows character activity post-Update 33, building a local database of what each character has genuinely completed.

---

## In-game theorycrafting tools vanished entirely

The discontinuation of **Stoned** left a complete void in the ESO addon ecosystem. No current addon allows players to theoretically compare gear combinations, calculate optimal builds, or simulate DPS without actually equipping items and respeccing. Players must use external websites like ESO-Skillbook or spreadsheets for theorycrafting.

Related gaps in combat analysis persist. **CritDamage** doesn't properly include Khajiit passive or Shadow Mundus adjustments. **MitigationPercent** works inconsistently. Multiple forum requests exist for a "gear advisor" that suggests equipment based on build type during leveling—nothing adequate exists.

One forum user summarized: "I wouldn't think it would take that much data...just a simple map overlay with pin points" when requesting quest skill point visualization. Currently, no addon shows all quests that reward skill points on the map before accepting them, despite Urich's Skill Point Finder achieving **1.78 million downloads** for the simpler task of showing already-earned skill points.

---

## Abandoned addons represent immediate takeover opportunities

Several high-download addons sit abandoned with active user bases:

| Addon | Impact | Status |
|-------|--------|--------|
| Leo's Altholic | Comprehensive character dashboard | Discontinued, no successor |
| PersonalAssistant | Banking, junk, loot, repair automation | Discontinued |
| Character Zone Tracker | Per-character delve/boss completion | Seeking maintainer |
| Stoned | In-game theorycrafting/stat calculation | Discontinued, unique functionality lost |
| TraitBuddy 2.0 | Trait research tracking | Marked OBSOLETE, "do not ask for new features" |
| Settings Profiler | Settings profiles per character | Author departed 2019 |

The PersonalAssistant discontinuation particularly stands out. It automated banking decisions, junk identification, loot handling, and repair functionality in one package. Current alternatives require installing multiple separate addons (Dustman for junk, FCOItemSaver for protection, etc.) and configuring each independently.

---

## Guild trader filtering remains frustratingly heavy

A consistent veteran complaint involves finding unknown recipes, motifs, and style pages at guild traders. **Awesome Guild Store** provides filtering capability but carries significant performance overhead—players report it contributing to 2-10 minute loading times alongside Master Merchant. Multiple forum requests ask for a "lightweight addon showing only unknown recipes/styles without heavy overhead."

The specific use case: standing at a guild trader, instantly seeing which recipe scrolls, motif chapters, or style pages you don't yet know, without waiting for massive database loads. Current solutions either require the full trading suite overhead or manual checking against Character Knowledge data.

---

## Transmog and style tracking has gaps despite sticker book

While the Sticker Book replaced some Set Tracker functionality, **style page and outfit style tracking** remains fragmented. Style Tracker exists but uses a limited "master character" system. Forum requests for "Is there a known/unknown outfit style tracker?" went unanswered at ESOUI.

Specific missing functionality includes:
- Comprehensive view of all collected vs. missing motif chapters across all styles
- Outfit style page completion tracking per category (hats, costumes, personalities)
- Visual indication in guild stores which style pages are unknown
- Cross-referencing what styles can be obtained from which content

---

## Console launch creates a new market in June 2025

Update 46 brings addon support to PS5 and Xbox Series X|S in June 2025—the first time console players will access addons at all. Initially limited to UI-based addons through an in-game menu (not ESOUI/Minion), this represents an **entirely new user base** experiencing functionality PC players have had for years.

Console opportunity areas include performance-optimized versions of essential addons: map pins, buff tracking, inventory management, and daily quest tracking. The curated addon selection means less competition initially, but performance-conscious development is crucial given console hardware constraints. Old-generation consoles (PS4/Xbox One) will not receive addon support.

---

## Feature requests with strongest evidence of demand

Based on upvotes, thread length, and repeated requests across multiple sources:

**Account-wide with per-character toggle** remains the most-requested paradigm. Players want keybindings, camera settings, UI positions, and addon configurations to sync across characters while retaining the option to customize individually. Votan's Keybinder partially addresses keybindings, but forum users ask "No idea why this is not an option by default. This is 100% essential."

**Bulk operations** generate consistent requests: clean all fish button, combine duplicate surveys for same location, delete all mail, auto-bind uncollected gear for sticker book. These represent small but high-frequency annoyances for veteran players.

**Housing storage visibility** at crafting stations would show materials stored in housing chests alongside bank and craft bag contents—currently requires running between storage chests to check quantities.

---

## Concrete development suggestions ranked by evidence

**Tier 1: Clear market gap with strong evidence**
1. **Ultimate Altholic Dashboard** — Unified interface replacing Leo's Altholic combining character stats, dailies, research timers, currencies, and achievement tracking. Evidence: discontinued original had high usage, multiple requests for replacement
2. **Per-Character Achievement Shadow Tracker** — Records what achievements each character actually completes post-Update 33. Evidence: 91-page forum thread, ZOS rejection confirms unmet demand
3. **In-Game Build Theorycrafting Tool** — Replace abandoned Stoned with gear comparison, stat calculation, DPS simulation. Evidence: unique functionality with no current solution

**Tier 2: Underserved categories with repeated requests**
4. **Lightweight Unknown Item Filter** — Simple guild store overlay showing only uncollected recipes/motifs/styles without Master Merchant overhead. Evidence: repeated forum requests for lighter alternative
5. **Comprehensive Style Completion Tracker** — All motifs, outfit styles, and cosmetics in one interface showing collection progress. Evidence: forum requests, limited current options
6. **Skill Point Quest Map Overlay** — Shows all quests rewarding skill points on map before accepting. Evidence: explicit forum request, 1.78M downloads for related functionality

**Tier 3: Takeover opportunities**
7. **Character Zone Tracker Maintenance** — Take over actively-seeking-maintainer addon tracking delve/boss/event completion per character
8. **PersonalAssistant Successor** — Unified automation for banking, junk, loot, repair decisions in one addon

The ESO addon ecosystem rewards developers who consolidate fragmented functionality into comprehensive solutions. The pattern of Leo's Altholic, PersonalAssistant, and Stoned discontinuations shows that "do-everything" addons achieve high adoption—and their abandonment creates genuine community pain that replacement projects can address.