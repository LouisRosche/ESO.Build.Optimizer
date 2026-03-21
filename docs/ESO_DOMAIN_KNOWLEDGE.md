# ESO Domain Knowledge

Reference material for Elder Scrolls Online game systems relevant to this project.

---

## Classes and Subclassing (Update 46+)

ESO has 7 base classes. Since Update 46, players can **subclass** - using skills from a secondary class.

| Class | Primary Resource | Signature Mechanic |
|-------|------------------|-------------------|
| Dragonknight | Magicka/Stamina | **Reworked in U49** - updated skill lines, new DoT/sustain mechanics |
| Nightblade | Magicka/Stamina | Stealth, execute damage |
| Sorcerer | Magicka | Pets, shields, burst |
| Templar | Magicka/Stamina | Jabs, purify, execute (Radiant Glory) |
| Warden | Magicka/Stamina | Bear, sustain (Bull Netch), Ice |
| Necromancer | Magicka/Stamina | Corpses, Blastbones |
| Arcanist | Magicka | Crux system, beams |

> **U49 Note (March 2026)**: Dragonknight received a significant class rework in Update 49. DK skill data in the feature database must be re-scraped and validated against the new skill values, morphs, and mechanics. The `patch_updated` field for all DK skills should be set to `U49`.

**Subclassing meta** (as of U49):
- Warden subclass: Bull Netch (sustain), Ice Fortress (buffs)
- Templar subclass: Radiant Glory (ranged execute)
- Arcanist subclass: Cephaliarch's Flail (execute with Crux)

---

## Role Contribution Model

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

---

## Gear Sets

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

---

## Combat Metrics We Track

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

---

## Update/Patch Cadence

ESO releases quarterly updates:
- **Q1**: Update XX (usually March)
- **Q2**: Chapter (major expansion, June)
- **Q3**: Update XX+1 (usually September)
- **Q4**: Update XX+2 (usually December)

**Data freshness requirement**: Feature data must track `patch_updated` field. Scraping should run post-patch to detect changes.

---

## ESO API Constraints

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

**Implication**: All sync happens via SavedVariables -> Companion App -> Cloud

---

## Market Context

### Complementary Tools

| Tool | What They Do | What We Add |
|------|-------------|-------------|
| **Combat Metrics** | Raw DPS/HPS numbers, buff uptimes, combat breakdowns | Cloud analytics, ML recommendations, cross-session tracking, percentile comparisons |
| **ESO Logs** | Trial percentile rankings and leaderboards | Per-encounter recs across all content types, ML-based build optimization |

**Key positioning**: No ML-based combat analytics tool exists for ESO. We are the first to apply machine learning to ESO combat data for personalized improvement recommendations.

### Console Compatibility (June 2025+)

Critical requirements for PlayStation/Xbox:
- **File extension**: Must use `.addon` (not just `.txt`)
- **Case sensitivity**: PlayStation uses case-sensitive filesystem
- **File limits**: Maximum 500 files per addon
- **No compatibility layer**: Deprecated functions will not work

---

*Last updated: March 2026 | ESO Update 49 (API 101049)*
