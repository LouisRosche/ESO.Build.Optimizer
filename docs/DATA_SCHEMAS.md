# Data Schemas

JSON schemas for the ESO Build Optimizer data pipeline.

---

## Feature Schema (Skills, Sets, etc.)

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

---

## Combat Run Schema

```json
{
    "run_id": "uuid",
    "player_id": "uuid",
    "character_name": "string",
    "timestamp": "ISO8601",
    "content": {
        "type": "dungeon|trial|arena|overworld",
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
        "skills_front": ["Molten Whip", "Flames of Oblivion"],
        "skills_back": ["Unstable Wall", "Cauterize"],
        "champion_points": {}
    },
    "metrics": {
        "damage_done": 45000000,
        "dps": 24350,
        "healing_done": 2500000,
        "damage_taken": 8500000,
        "deaths": 1,
        "buff_uptime": {"Major Brutality": 0.94}
    },
    "contribution_scores": {
        "damage_dealt": 0.72,
        "healing_done": 0.08,
        "buff_uptime": 0.15
    }
}
```

---

## Recommendation Schema

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

## Gear Set Schema

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
            "effect": "Dealing direct damage grants Kinras's Wrath stack...",
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

---

*See also: `data/schemas/feature.schema.json` for the formal JSON Schema definition.*
