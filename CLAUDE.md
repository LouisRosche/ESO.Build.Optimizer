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
│                         CLOUD BACKEND                           │
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

### 2.1 Component Responsibilities

| Component | Tech Stack | Responsibility |
|-----------|------------|----------------|
| Lua Addon | Lua 5.1, ESO API | Combat logging, build tracking, in-game UI |
| Companion App | Python/Electron | Watch SavedVariables, sync to cloud |
| Web API | Python/FastAPI or Node | Auth, data ingestion, query interface |
| ML Pipeline | Python, scikit-learn/PyTorch | Percentile calc, contribution analysis, recommendations |
| Database | PostgreSQL + vector store | Run history, feature data, embeddings |
| Web Interface | React/Vue | User dashboard, build editor, analytics |

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
| UESP | uesp.net/wiki/Online:* | Skills, sets, mechanics | Very High |
| ESO-Hub | eso-hub.com | Sets, builds | High |
| ESO Logs | esologs.com | Combat rankings | High (for percentiles) |
| Alcast | alcasthq.com | Meta builds | Medium (opinion-based) |

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
- [x] Feature dataset structure (1,328 entries)
- [x] Excel generation pipeline
- [x] Research docs on addon gaps

### In Progress:
- [ ] Complete feature dataset (~2,000 target)
- [ ] Design contribution model
- [ ] Prototype Lua addon

### Not Started:
- [ ] Companion app
- [ ] Web API
- [ ] ML pipeline
- [ ] Web interface

---

## 11. Quick Reference Commands

```bash
# Generate Excel from JSON data
python scripts/generate_excel.py

# Count features
for f in data/raw/*.json; do echo "$f: $(python3 -c "import json; print(len(json.load(open('$f'))))")"; done

# Validate JSON
python -m json.tool data/raw/phase01_class_skills.json > /dev/null && echo "Valid"
```

---

## 12. Questions for Human Review

When uncertain, ask about:
1. **Balance priorities** - DPS meta vs. survivability vs. group utility
2. **Content scope** - Focus on dungeons first? Trials? PvP?
3. **UI preferences** - Minimal vs. detailed in-game display
4. **Privacy** - What player data is okay to aggregate?

---

*Last updated: January 2026 | ESO Update 48*
