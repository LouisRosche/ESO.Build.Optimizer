# ESO Build Optimizer - AI Agent Documentation

> **Purpose**: This document provides everything an AI agent needs to understand, develop, and maintain the ESO Build Optimizer ecosystem.

---

## 1. Project Vision

**What we're building**: An intelligent ESO performance analytics system that:
1. Tracks combat metrics in-game via Lua addon
2. Syncs data to a web interface via companion app
3. Applies ML to compare performance against similar runs
4. Generates actionable recommendations (gear, skills, execution)

**The gap we're filling**: Combat Metrics gives raw data. We give *actionable intelligence*.

**Unique value proposition**: "You performed at X percentile. To improve your contribution, do Y."

---

## 2. System Architecture

### 2.0 Distribution Model

**For End Users (hundreds of players):**
```
1. Install addon via Minion (one-click from ESOUI.com)
2. Create account at website (email + password)
3. Play the game - addon tracks automatically
4. View analytics on website - that's it!
```

**No technical interaction required from end users.**

### 2.1 System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER'S MACHINE                           │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │   ESO Client    │    │  Companion App  │                     │
│  │  (Lua Addon)    │───▶│  (reads SVars)  │                     │
│  │                 │    │                 │                     │
│  │ - Combat logs   │    │ - Watches file  │                     │
│  │ - Build state   │    │ - Uploads data  │                     │
│  │ - Metrics UI    │    │ - Pulls updates │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                              │
│           ▼                      │                              │
│  SavedVariables/*.lua            │                              │
└──────────────────────────────────┼──────────────────────────────┘
                                   │ HTTPS
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CLOUD BACKEND (Owner Managed)                │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │
│  │   Web API       │    │   ML Pipeline   │    │  Database   │  │
│  │                 │◀──▶│                 │◀──▶│             │  │
│  │ - Auth          │    │ - Percentile    │    │ - Runs      │  │
│  │ - Sync endpoint │    │   calculation   │    │ - Builds    │  │
│  │ - Query API     │    │ - Contribution  │    │ - Players   │  │
│  │                 │    │   classification│    │ - Features  │  │
│  └────────┬────────┘    │ - Recs engine   │    │             │  │
│           │             └─────────────────┘    └─────────────┘  │
│           ▼                                                     │
│  ┌─────────────────┐                                            │
│  │  Web Interface  │                                            │
│  │                 │                                            │
│  │ - Dashboard     │                                            │
│  │ - Build editor  │                                            │
│  │ - Analytics     │                                            │
│  │ - Rec generator │                                            │
│  └─────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

| Component | Tech Stack | Distribution | Responsibility |
|-----------|------------|--------------|----------------|
| Lua Addon | Lua 5.1, ESO API | **ESOUI.com / Minion** | Combat logging, build tracking, in-game UI |
| Companion App | Python/Electron | **Bundled download** | Watch SavedVariables, sync to cloud |
| Web API | Python/FastAPI | **Owner deployed (Render)** | Auth, data ingestion, query interface |
| ML Pipeline | Python, scikit-learn | **Owner deployed** | Percentile calc, recommendations |
| Database | PostgreSQL | **Owner deployed (Neon)** | Run history, feature data |
| Web Interface | React/Vite | **Owner deployed (Vercel)** | User dashboard, analytics |

### 2.3 User Journey

```
┌─────────────────────────────────────────────────────────────────┐
│  END USER EXPERIENCE (Zero Technical Knowledge Required)        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. DISCOVER                                                    │
│     └─ Find addon on ESOUI.com or via Minion search            │
│                                                                 │
│  2. INSTALL (One Click)                                         │
│     └─ Click "Install" in Minion → addon auto-downloads        │
│     └─ OR download ZIP from ESOUI → extract to AddOns folder   │
│                                                                 │
│  3. CREATE ACCOUNT                                              │
│     └─ Visit website → Register with email/password            │
│     └─ Link account via in-game command: /ebo link <token>     │
│                                                                 │
│  4. PLAY NORMALLY                                               │
│     └─ Addon runs automatically in background                  │
│     └─ Small UI shows real-time DPS/HPS (optional)             │
│     └─ Data syncs when companion app running                   │
│                                                                 │
│  5. VIEW ANALYTICS                                              │
│     └─ Log into website → see dashboard                        │
│     └─ View percentile rankings, recommendations               │
│     └─ Compare builds across characters                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. ESO Domain Knowledge

### 3.1 Classes and Subclassing (Update 46+)

ESO has 7 base classes. Since Update 46, players can **subclass** - using skills from a secondary class.

| Class | Primary Resource | Signature Mechanic |
|-------|------------------|-------------------|
| Dragonknight | Magicka/Stamina | Burning DoTs, self-healing |
| Nightblade | Magicka/Stamina | Stealth, execute damage |
| Sorcerer | Magicka | Pets, shields, burst |
| Templar | Magicka/Stamina | Jabs, purify, execute (Radiant Glory) |
| Warden | Magicka/Stamina | Bear, sustain (Bull Netch), Ice |
| Necromancer | Magicka/Stamina | Corpses, Blastbones |
| Arcanist | Magicka | Crux system, beams |

**Subclassing meta** (as of U48):
- Warden subclass: Bull Netch (sustain), Ice Fortress (buffs)
- Templar subclass: Radiant Glory (ranged execute)
- Arcanist subclass: Cephaliarch's Flail (execute with Crux)

### 3.2 Role Contribution Model

Traditional MMOs use trinary roles: Tank, Healer, DPS. ESO is more fluid.

**Our contribution model uses continuous categories:**

```
contribution = {
    "damage_dealt": 0.0-1.0,      # Raw DPS output
    "damage_taken": 0.0-1.0,      # Tanking (inverted - less = better for non-tanks)
    "healing_done": 0.0-1.0,      # HPS output
    "buff_uptime": 0.0-1.0,       # Group buff contribution
    "debuff_uptime": 0.0-1.0,     # Boss debuff contribution
    "mechanic_execution": 0.0-1.0, # Interrupt, synergy, positioning
    "resource_efficiency": 0.0-1.0 # Sustain, no overhealing/overkill
}
```

**Example profiles:**
- Pure DPS: `{damage: 0.9, buff: 0.1, ...}`
- Support DPS: `{damage: 0.6, buff: 0.3, debuff: 0.1, ...}`
- Off-tank: `{damage: 0.3, taken: 0.5, buff: 0.2, ...}`

### 3.3 Gear Sets

ESO gear provides **set bonuses** at 2/3/4/5 pieces worn.

| Set Type | Source | Example |
|----------|--------|---------|
| Overland | Zone drops | Spriggan's Thorns, Briarheart |
| Dungeon | Dungeon drops | Kinras's Wrath, Pillar of Nirn |
| Trial | 12-player raids | Relequen, Bahsei's Mania |
| Monster | Vet dungeon final boss | Balorgh, Valkyn Skoria |
| Craftable | Crafting stations | Rallying Cry, Mechanical Acuity |
| Mythic | Antiquities (1 piece) | Markyn Ring, Oakensoul |
| PvP | Cyrodiil/BGs | Plaguebreak, Daedric Trickery |

**Standard gear layout:**
- 2 Monster pieces (head + shoulders)
- 5-piece set #1 (body or weapons+jewelry)
- 5-piece set #2 (body or weapons+jewelry)
- OR: 1 Mythic + 5-piece + 5-piece (drop one monster)

### 3.4 Combat Metrics We Track

```lua
-- Per-encounter metrics
metrics = {
    -- Damage
    damage_done = 0,           -- Total damage dealt
    dps = 0,                   -- Damage per second
    crit_rate = 0,             -- Critical hit percentage
    dot_uptime = {},           -- Per-DoT uptime tracking

    -- Healing
    healing_done = 0,
    hps = 0,
    overhealing = 0,           -- Wasted healing

    -- Tanking
    damage_taken = 0,
    damage_blocked = 0,
    damage_mitigated = 0,

    -- Buffs/Debuffs
    buff_uptime = {},          -- Per-buff tracking
    debuff_uptime = {},        -- On boss

    -- Mechanics
    interrupts = 0,
    synergies_used = 0,
    synergies_provided = 0,
    deaths = 0,
    time_dead = 0,

    -- Resources
    magicka_spent = 0,
    stamina_spent = 0,
    ultimate_spent = 0,
    potion_uses = 0,
}
```

### 3.5 Update/Patch Cadence

ESO releases quarterly updates:
- **Q1**: Update XX (usually March)
- **Q2**: Chapter (major expansion, June)
- **Q3**: Update XX+1 (usually September)
- **Q4**: Update XX+2 (usually December)

**Data freshness requirement**: Feature data must track `patch_updated` field. Scraping should run post-patch to detect changes.

---

## 4. Data Models

### 4.1 Feature Schema (Skills, Sets, etc.)

```json
{
    "feature_id": "PLAYER_CLASS_DK_ARDENTFLAME_001",
    "system": "PLAYER|COMPANION|CHAMPION",
    "category": "Class|Weapon|Armor|Guild|World|AllianceWar|Racial|Crafting|Scribing|Set",
    "subcategory": "Skill line or set type",
    "feature_type": "ULTIMATE|ACTIVE|PASSIVE|MORPH_A|MORPH_B|SET_BONUS",
    "name": "Human-readable name",
    "parent_feature": "For morphs, the base skill ID",
    "class_restriction": "Dragonknight|null",
    "unlock_method": "How to obtain",
    "resource_type": "Magicka|Stamina|Ultimate|Health|None",
    "resource_cost": 2700,
    "cast_time": "Instant|0.8s|Channeled",
    "target_type": "Self|Enemy|Ally|Area|Ground",
    "range_m": 28,
    "radius_m": 8,
    "duration_sec": 10.0,
    "cooldown_sec": null,
    "base_effect": "Description of what it does",
    "scaling_stat": "Spell Damage|Weapon Damage|Max Health|etc",
    "max_ranks": 4,
    "rank_progression": "How it scales per rank",
    "buff_debuff_granted": "Major Brutality|Minor Maim|etc",
    "synergy": "Synergy name if applicable",
    "tags": "damage|heal|shield|dot|execute|aoe|single-target",
    "dlc_required": "Base Game|Necrom Chapter|etc",
    "patch_updated": "U48",
    "source_url": "https://uesp.net/..."
}
```

### 4.2 Combat Run Schema

```json
{
    "run_id": "uuid",
    "player_id": "uuid",
    "character_name": "string",
    "timestamp": "ISO8601",
    "content": {
        "type": "dungeon|trial|arena|overworld|pvp",
        "name": "Veteran Lair of Maarselok",
        "difficulty": "normal|veteran|hardmode"
    },
    "duration_sec": 1847,
    "success": true,
    "group_size": 4,
    "build_snapshot": {
        "class": "Dragonknight",
        "subclass": "Warden",
        "race": "Dark Elf",
        "cp_level": 2100,
        "sets": ["Bahsei's Mania", "Kinras's Wrath", "Kjalnar's Nightmare"],
        "skills_front": ["Molten Whip", "Flames of Oblivion", ...],
        "skills_back": ["Unstable Wall", "Cauterize", ...],
        "champion_points": {...}
    },
    "metrics": {
        "damage_done": 45000000,
        "dps": 24350,
        "healing_done": 2500000,
        "damage_taken": 8500000,
        "deaths": 1,
        "buff_uptime": {"Major Brutality": 0.94, ...},
        ...
    },
    "contribution_scores": {
        "damage_dealt": 0.72,
        "healing_done": 0.08,
        "buff_uptime": 0.15,
        ...
    }
}
```

### 4.3 Recommendation Schema

```json
{
    "recommendation_id": "uuid",
    "run_id": "uuid",
    "category": "gear|skill|execution|build",
    "priority": 1,
    "current_state": "Using Spriggan's Thorns",
    "recommended_change": "Switch to Pillar of Nirn",
    "expected_improvement": "+8% DPS based on similar players",
    "reasoning": "Your penetration is already capped from group debuffs",
    "confidence": 0.85
}
```

### 4.4 Gear Set Schema

```json
{
    "set_id": "SET_DUNGEON_KINRAS_WRATH",
    "name": "Kinras's Wrath",
    "set_type": "Dungeon|Trial|Overland|Monster|Craftable|Mythic|Arena",
    "weight": "Light|Medium|Heavy|Jewelry|Weapon",
    "bind_type": "Bind on Pickup|Bind on Equip|Craftable",
    "tradeable": false,
    "location": "Black Drake Villa",
    "dlc_required": "Flames of Ambition",
    "bonuses": {
        "2": {"stat": "Weapon and Spell Damage", "value": 129},
        "3": {"stat": "Minor Force", "uptime": "always"},
        "4": {"stat": "Weapon and Spell Damage", "value": 129},
        "5": {
            "effect": "Dealing direct damage grants Kinras's Wrath stack. At 5 stacks, gain Major Berserk for 5 seconds.",
            "proc_condition": "direct_damage",
            "buff_granted": "Major Berserk",
            "duration_sec": 5,
            "cooldown_sec": 0
        }
    },
    "pve_tier": "S|A|B|C|F",
    "role_affinity": {
        "damage_dealt": 0.95,
        "buff_uptime": 0.7,
        "healing_done": 0.0
    },
    "tags": "damage|crit|berserk|stacking|trial-meta",
    "patch_updated": "U48",
    "source_url": "https://eso-hub.com/en/sets/kinrass-wrath"
}
```

**Set Categories to Document:**
- Monster Sets (~80 sets)
- Dungeon Sets (~150 sets)
- Trial Sets (~50 sets)
- Overland Sets (~100 sets)
- Craftable Sets (~80 sets)
- Mythic Items (~30 items)
- Arena Weapons (~20 sets)

---

## 5. Development Workflows

### 5.1 For AI Agents: Task Types

When given a task, identify which type:

| Task Type | Approach |
|-----------|----------|
| **Data expansion** | Add rows to JSON files in `data/raw/`, run `scripts/generate_excel.py` |
| **Lua addon code** | Write to `addon/` directory, follow ESO API patterns |
| **Web scraping** | Create scripts in `scripts/scrapers/`, output to `data/scraped/` |
| **ML pipeline** | Work in `ml/` directory, document model decisions |
| **Web interface** | Work in `web/` directory |
| **Documentation** | Update this file or create specific docs |

### 5.2 Data Refresh Protocol

When ESO patches:

1. Check patch notes for skill/set changes
2. Run scrapers against UESP, ESO-Hub
3. Diff against existing data
4. Update `patch_updated` field on changed features
5. Regenerate Excel compilation
6. Version tag the dataset

### 5.3 Web Scraping Sources

| Source | URL | Data Type | Reliability |
|--------|-----|-----------|-------------|
| UESP | uesp.net/wiki/Online:* | Skills, sets, mechanics, quests | Very High |
| ESO-Hub | eso-hub.com | Sets, builds, item database | High |
| ESO Logs | esologs.com | Combat rankings, percentiles | High |
| ESO Sets | eso-sets.com | Set bonuses, acquisition | High |

**Excluded Sources:**
- Alcast (opinion-based meta builds, not objective data)

### 5.4 Coding Standards

**Lua (Addon):**
```lua
-- Use local variables
local MyAddon = {}

-- Namespace events
function MyAddon:OnCombatEvent(eventCode, ...)
end

-- Register with event manager
EVENT_MANAGER:RegisterForEvent("MyAddon", EVENT_COMBAT_EVENT, function(...) MyAddon:OnCombatEvent(...) end)
```

**Python (Backend/ML):**
```python
# Type hints required
def calculate_percentile(run: CombatRun, population: list[CombatRun]) -> float:
    ...

# Docstrings for complex functions
# Use dataclasses or Pydantic for schemas
```

**JSON Data:**
- Use snake_case for keys
- Include `null` for missing optional fields
- Keep arrays flat where possible

---

## 6. ESO API Constraints

**What the addon API CAN do:**
- Read combat events in real-time
- Access equipped gear, skills, attributes
- Read/write SavedVariables (persisted Lua tables)
- Display custom UI elements
- Hook into most game events

**What the addon API CANNOT do:**
- Make network requests (no HTTP/sockets)
- Access filesystem outside SavedVariables
- Modify game files
- Run during loading screens
- Persist data without zone change/logout

**Implication**: All sync happens via SavedVariables → Companion App → Cloud

---

## 7. Percentile Calculation Logic

```python
def calculate_percentile(
    run: CombatRun,
    comparison_pool: list[CombatRun]
) -> dict[str, float]:
    """
    Compare a run against similar runs.

    Similarity criteria:
    - Same content (dungeon name + difficulty)
    - Similar group size
    - Within CP range (±200)

    Note: Group composition varies - this is expected.
    The model must be robust to comp differences.
    """

    # Filter to similar runs
    similar = [r for r in comparison_pool
               if r.content == run.content
               and abs(r.cp_level - run.cp_level) <= 200]

    if len(similar) < 30:
        return {"confidence": "low", "sample_size": len(similar)}

    percentiles = {}
    for metric in CONTRIBUTION_METRICS:
        values = sorted([r.metrics[metric] for r in similar])
        player_value = run.metrics[metric]
        percentiles[metric] = bisect.bisect_left(values, player_value) / len(values)

    return percentiles
```

---

## 8. Recommendation Engine Logic

```python
def generate_recommendations(
    run: CombatRun,
    percentiles: dict[str, float],
    feature_db: FeatureDatabase
) -> list[Recommendation]:
    """
    Generate actionable recommendations based on:
    1. Weakest contribution categories
    2. Build comparison to high performers
    3. Execution gaps (buff uptime, etc.)
    """

    recs = []

    # Find weakest areas
    weakest = sorted(percentiles.items(), key=lambda x: x[1])[:3]

    for metric, pct in weakest:
        if pct < 0.5:  # Below median
            # Query similar high performers
            top_performers = get_top_performers(run.content, metric)

            # Diff builds
            gear_diff = diff_gear(run.build, top_performers)
            skill_diff = diff_skills(run.build, top_performers)

            if gear_diff:
                recs.append(Recommendation(
                    category="gear",
                    change=gear_diff[0],
                    reasoning=f"Top {metric} performers use this"
                ))

            if skill_diff:
                recs.append(Recommendation(
                    category="skill",
                    change=skill_diff[0],
                    reasoning=f"Higher uptime correlation with {metric}"
                ))

    return recs
```

---

## 9. File Structure

```
ESO.Build.Optimizer/
├── CLAUDE.md                 # This file - AI agent documentation
├── README.md                 # User-facing documentation
├── requirements.txt          # Python dependencies
│
├── data/
│   ├── raw/                  # Phase JSON files (skills, sets, etc.)
│   ├── compiled/             # Generated Excel files
│   ├── scraped/              # Raw scraper output
│   └── models/               # Trained ML models
│
├── scripts/
│   ├── generate_excel.py     # Compile JSON → Excel
│   ├── fix_addon.py          # ESO addon fixer CLI
│   ├── addon_fixer/          # Addon fixer package
│   │   ├── fixer.py          # Main orchestrator
│   │   ├── manifest.py       # Manifest parser/fixer
│   │   ├── lua_analyzer.py   # Lua code analysis
│   │   ├── xml_fixer.py      # XML virtual control fixes
│   │   ├── migrations.py     # API migration database
│   │   └── validator.py      # Dependency validation
│   └── scrapers/             # Web scraping scripts
│
├── addon/                    # Lua addon source
│   ├── ESOBuildOptimizer.txt # Addon manifest
│   ├── ESOBuildOptimizer.lua # Main addon file
│   ├── libs/                 # Library dependencies
│   └── ui/                   # UI XML/Lua files
│
├── companion/                # Desktop companion app
│   ├── watcher.py            # SavedVariables file watcher
│   └── sync.py               # Cloud sync logic
│
├── api/                      # Web API backend
│   ├── main.py               # FastAPI app
│   ├── models/               # Pydantic schemas
│   └── routes/               # API endpoints
│
├── ml/                       # Machine learning
│   ├── train.py              # Model training
│   ├── percentile.py         # Percentile calculation
│   └── recommendations.py    # Rec engine
│
└── web/                      # Web frontend
    ├── src/
    └── public/
```

---

## 10. Current State & Next Steps

### Completed:
- [x] Feature dataset (1,981 entries - skills, sets, champion points, companions)
- [x] Excel generation pipeline with field normalization
- [x] Research docs on addon gaps
- [x] Lua addon with combat tracking, build snapshots, metrics UI
- [x] Lua addon SkillAdvisor module (real-time recommendations, skill highlights)
- [x] Lua addon ESO best practices compliance (APIVersion 101046/101047, event filtering, manifest format)
- [x] Companion app (watcher.py + sync.py) with cross-platform support
- [x] FastAPI backend with auth, runs, recommendations endpoints
- [x] ML pipeline (percentile.py + recommendations.py)
- [x] React web frontend (dashboard, builds, analytics, recommendations)
- [x] Deployment configs (Vercel, Render, Neon)
- [x] Technical documentation system (5 comprehensive guides)
- [x] CI/CD pipeline (GitHub Actions with 6 parallel jobs)
- [x] Comprehensive test suite (pytest + vitest)
- [x] 122-issue codebase audit completed and fixed
- [x] ESO Addon Fixer tool (API migrations, LibStub removal, font paths, packaging)

### Ready for Release:
- [ ] ESOUI.com addon submission (see Section 10.1)
- [ ] Production deployment (owner managed)
- [ ] Companion app installer packaging

### Future Enhancements:
- [ ] Console addon support (PS5/Xbox - Update 46+)
- [ ] Additional content percentiles (more dungeons/trials)
- [ ] Guild leaderboards
- [ ] Build sharing/import

### 10.1 ESOUI.com Submission Checklist

The addon is ready for ESOUI.com distribution via Minion:

**Package Structure** (ZIP file for upload):
```
ESOBuildOptimizer/
├── ESOBuildOptimizer.txt          # Manifest (CRLF line endings)
├── ESOBuildOptimizer.lua          # Main addon
├── modules/
│   ├── CombatTracker.lua
│   ├── BuildSnapshot.lua
│   ├── MetricsUI.lua
│   └── SkillAdvisor.lua
└── LICENSE.txt                     # Optional
```

**ESOUI Submission Form:**
- **Title**: ESO Build Optimizer
- **Category**: Combat Mods
- **Version**: 1.0.0
- **Game Version**: 101046 / 101047 (Update 46-48)
- **Description**: Combat metrics with ML-powered recommendations. Track DPS/HPS, compare against similar players, get actionable improvement suggestions.
- **Changelog**: Initial release

**Manifest Compliance** (already done):
- [x] `## AddOnVersion: 1` (integer)
- [x] `## APIVersion: 101046 101047` (dual support)
- [x] `## SavedVariables:` declared
- [x] UTF-8 without BOM, CRLF line endings
- [x] `## OptionalDependsOn:` with versions
- [x] `## IsLibrary: false`

---

## 11. Quick Reference Commands

```bash
# Generate Excel from JSON data
python scripts/generate_excel.py

# Count features
for f in data/raw/*.json; do echo "$f: $(python3 -c "import json; print(len(json.load(open('$f'))))")"; done

# Validate JSON
python -m json.tool data/raw/phase01_class_skills.json > /dev/null && echo "Valid"

# ESO Addon Fixer commands (TypeScript CLI)
cd tools/addon-fixer
node dist/cli.js analyze /path/to/addon    # Analyze addon for issues
node dist/cli.js fix /path/to/addon        # Fix addon (creates backup)
node dist/cli.js verify /path/to/addon     # Verify addon is fixed
node dist/cli.js libraries                 # Browse known ESO libraries
node dist/cli.js libraries -a /path/addon  # Check addon library health
node dist/cli.js sync                      # Sync library versions from ESOUI
node dist/cli.js sync --check              # CI mode: fail if outdated
node dist/cli.js migrations                # List known API migrations
node dist/cli.js info                      # Show ESO API version info
```

---

## 11.1 ESO Addon Fixer

The addon fixer is an automated tool for repairing broken ESO addons. It updates addons to work with **APIVersion 101048** (Update 48).

### What It Fixes

| Category | Fixes Applied |
|----------|---------------|
| **Manifest** | Updates APIVersion, removes LibStub dependency, fixes encoding |
| **Lua Code** | Replaces LibStub patterns, renames deprecated functions, updates font paths |
| **XML Files** | Updates font paths, fixes virtual control inheritance |
| **Dependencies** | Validates library versions, suggests updates |

### Key Migrations

**LibStub Replacement** (deprecated since Summerset):
```lua
-- Old (deprecated):
local LAM = LibStub("LibAddonMenu-2.0")

-- New (modern):
local LAM = LibAddonMenu2
```

**Champion Points Migration** (API 100015):
```lua
-- Old: GetUnitVeteranRank(unitTag)
-- New: GetUnitChampionPoints(unitTag)
```

**Font Path Migration** (API 101041):
```lua
-- Old: "MyAddon/fonts/myfont.ttf|16"
-- New: "MyAddon/fonts/myfont.slug|16"
```

### Library Global Variables

| Library | Global Variable |
|---------|-----------------|
| LibAddonMenu-2.0 | `LibAddonMenu2` |
| LibFilters-3.0 | `LibFilters3` |
| LibCustomMenu | `LibCustomMenu` |
| LibGPS3 | `LibGPS3` |
| LibAsync | `LibAsync` |

### Addon Complexity Guide

| Complexity | Examples | Notes |
|------------|----------|-------|
| Low | Dustman, Set Tracker | Simple fixes, usually work immediately |
| Medium | FTC, PersonalAssistant | May need manual review |
| High | AwesomeGuildStore | Complex dependency chains |
| Very High | Wykkyd Framework | Recommend replacement addons |

### Programmatic Usage

```python
from addon_fixer import AddonFixer, FixerConfig

config = FixerConfig(
    update_api_version=True,
    fix_libstub=True,
    fix_font_paths=True,
    create_backup=True,
)

fixer = AddonFixer(config)
result = fixer.fix("/path/to/addon")

print(f"Changes: {result.total_changes}")
```

---

## 12. Market Context & Competitive Landscape

### 12.1 Discontinued Addons We Replace

| Addon | Gap Created | Our Solution |
|-------|-------------|--------------|
| **Combat Metrics** | Raw data only, no analysis | ML-powered recommendations |
| **Stoned** | No in-game theorycrafting | Build comparison via feature database |
| **Leo's Altholic** | No account-wide dashboard | Web interface with cross-character tracking |

### 12.2 Key Market Insights (from research)

1. **Update 33 (March 2022)** broke per-character achievement tracking. 91-page forum debate, ZOS rejected fix. Our addon can shadow-track per-character completion.

2. **Console addon support** launching June 2025 (Update 46) for PS5/Xbox Series X|S. First-mover opportunity for performance-optimized addons.

3. **"Do-everything" addons** achieve highest adoption. Fragmented solutions frustrate players. Our unified approach (addon + companion + web) addresses this.

4. **Lightweight alternatives** consistently requested. Master Merchant causes 2-10 min load times. Our approach: compute-heavy work happens server-side.

### 12.3 Differentiation

What we do that **nothing else does**:
- Continuous role contribution model (not Tank/Healer/DPS trinary)
- Percentile comparison against similar runs (same content, difficulty, CP range)
- Actionable recommendations with expected improvement estimates
- Historical trend analysis across runs

---

## 13. Technical Documentation System

> **CRITICAL FOR AI AGENTS**: Before implementing any component, read the relevant technical documentation in `docs/technical/` to ensure best practices are followed.

### 13.1 Documentation Files

| Document | Path | Covers |
|----------|------|--------|
| ESO Addon API | `docs/technical/ESO_ADDON_API.md` | Lua API, combat events, SavedVariables |
| FastAPI Best Practices | `docs/technical/FASTAPI_BEST_PRACTICES.md` | Project structure, async, Pydantic, security |
| React/Vite Guide | `docs/technical/REACT_VITE_BEST_PRACTICES.md` | Component patterns, hooks, TypeScript |
| Deployment Guide | `docs/technical/DEPLOYMENT_FREE_TIER.md` | Vercel, Render, Neon limits and configs |
| PyInstaller Packaging | `docs/technical/PYINSTALLER_PACKAGING.md` | Cross-platform builds, CI/CD |

### 13.2 Documentation Refresh Workflow

```bash
# Check documentation freshness
python scripts/refresh_docs.py

# Generate detailed report
python scripts/refresh_docs.py --report

# Mark all as reviewed (after manual check)
python scripts/refresh_docs.py --update

# Fetch and detect changes (requires httpx)
python scripts/refresh_docs.py --fetch
```

**Refresh triggers:**
- ESO quarterly updates → Check ESO Addon API docs
- Major library releases → Check relevant framework docs
- Monthly → Check deployment platform limits

### 13.3 Key Best Practices Quick Reference

**Lua Addon:**
- Use local variables, namespace events
- Register with `EVENT_MANAGER:RegisterForEvent(ADDON_NAME, ...)`
- Filter events to reduce callback frequency
- Data persists on zone change/logout, NOT during loading screens

**FastAPI:**
- Structure by domain/module, not file type
- Use `async def` for I/O, offload CPU work to background
- Leverage Pydantic for all validation
- Dependencies are cached per request

**React/Vite:**
- Use React Query for server state, Context for UI state
- Code-split with `lazy()` and `Suspense`
- Memoize only after profiling shows need
- TypeScript strict mode enabled

**Deployment:**
- Neon: 100 CU-hours/month, auto-suspend saves compute
- Render: Sleeps after 15min, use keep-alive endpoint
- Vercel: 10s function timeout, use for static/ISR

### 13.4 Online Documentation Sources

| Source | URL | Reliability |
|--------|-----|-------------|
| ESOUI Wiki | https://wiki.esoui.com/Main_Page | Very High |
| ESOUI API | https://wiki.esoui.com/API | Very High |
| UESP ESO Data | https://esoapi.uesp.net/ | Very High |
| FastAPI Docs | https://fastapi.tiangolo.com/ | Official |
| Vite Guide | https://vite.dev/guide/ | Official |
| Neon Docs | https://neon.com/docs/ | Official |
| Render Docs | https://render.com/docs/ | Official |

---

## 14. Project Decisions (Resolved)

| Decision | Resolution |
|----------|------------|
| **Privacy** | Anonymous by default. Opt-in for richer data sharing. |
| **Content scope** | PvE only, all-inclusive: dungeons, trials, arenas. No PvP. |
| **Historical data** | Starting fresh - addon replaces Combat Metrics entirely. |
| **Gear sets** | Include full set database (see section 4.4). |
| **Data sources** | UESP, ESO-Hub, ESO-Log, ESO-Sets. Exclude Alcast. |
| **In-game UI** | Minimal default with opt-in checkbox; "+" expander for full details |
| **Real-time recs** | Only actionable items (e.g., "use AoE when 2+ enemies nearby") |
| **Skill highlight** | Glow effect on recommended abilities during combat |
| **Rec style** | Data-backed nudge with confidence interval: "Switching X to Y would improve DPS by ~8% (85% confidence)" |
| **Companion platforms** | Windows primary; Mac/Linux supported via cross-platform Python |
| **Hosting** | Free tier: Vercel (frontend) + Render (backend) + Neon (database) |

---

## 15. Questions for Human Review

When uncertain, ask about:
1. **Balance priorities** - DPS meta vs. survivability vs. group utility
2. **Content priorities** - Which dungeons/trials to prioritize for percentile data
3. **Feature requests** - New functionality beyond current scope

---

## 16. Lessons Learned & Development Patterns

### 16.1 Lua Parser Quirks (luaparse)

When using `luaparse` for AST analysis:

```typescript
// WRONG: luaparse often returns null for StringLiteral.value
const value = stringNode.value; // null!

// CORRECT: Fall back to extracting from raw (which includes quotes)
const value = stringNode.value ?? stringNode.raw?.slice(1, -1);
```

This affects:
- LibStub detection (library name extraction)
- Font path analysis (path extraction)
- Any string literal processing

### 16.2 Pattern Matching Precision

When matching API patterns like `WINDOW_MANAGER:CreateControl`:

```typescript
// WRONG: Will match CreateControlFromVirtual too
pattern.includes("WINDOW_MANAGER:CreateControl")

// CORRECT: Include the opening paren for exact match
pattern === "WINDOW_MANAGER:CreateControl("
```

### 16.3 Console Compatibility (June 2025+)

Critical requirements for PlayStation/Xbox:
- **File extension**: Must use `.addon` (not just `.txt`)
- **Case sensitivity**: PlayStation uses case-sensitive filesystem
- **File limits**: Maximum 500 files per addon
- **No compatibility layer**: Deprecated functions will not work

### 16.4 Development Workflow Commands

```bash
# ESO Addon Fixer commands
cd tools/addon-fixer
node dist/cli.js analyze /path/to/addon    # Analyze for issues
node dist/cli.js fix /path/to/addon        # Fix issues (creates backup)
node dist/cli.js verify /path/to/addon     # Verify after fixing
node dist/cli.js migrations                 # List known migrations
node dist/cli.js info                       # Show API version info
```

### 16.5 Custom Slash Commands

Available in `.claude/commands/`:
- `/fix-addon <path>` - Analyze and fix an addon
- `/test-addon <path>` - Run verification suite
- `/check-migrations` - Show migration details

### 16.6 Specialized Agents

Available in `.claude/agents/`:
- `addon-analyzer` - Deep addon complexity analysis
- `fix-verifier` - Post-fix verification
- `migration-researcher` - Research new API changes

---

*Last updated: February 2026 | ESO Update 48*
