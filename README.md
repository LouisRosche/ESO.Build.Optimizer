# ESO Build Optimizer - Feature Documentation

A comprehensive dataset documenting ALL player-facing features in Elder Scrolls Online, organized into a normalized Excel dataset with ~2,000+ rows.

## Project Structure

```
ESO.Build.Optimizer/
├── data/
│   ├── raw/                    # Raw JSON data per phase
│   │   ├── phase01_class_skills.json
│   │   ├── phase02_weapon_skills.json
│   │   ├── phase03_armor_skills.json
│   │   ├── phase04_guild_skills.json
│   │   ├── phase05_world_skills.json
│   │   ├── phase06_alliance_war.json
│   │   ├── phase07_racial_passives.json
│   │   ├── phase08_crafting_skills.json
│   │   ├── phase09_scribing_system.json
│   │   ├── phase10_champion_points.json
│   │   └── phase11_companion_skills.json
│   └── compiled/
│       └── eso_features_complete.xlsx
├── scripts/
│   └── generate_excel.py       # Excel generation script
├── requirements.txt
└── README.md
```

## Data Schema

| Column | Type | Description |
|--------|------|-------------|
| feature_id | TEXT | Unique ID: {SYSTEM}_{CATEGORY}_{LINE}_{###} |
| system | TEXT | PLAYER, COMPANION, CHAMPION, SCRIBING |
| category | TEXT | Class, Weapon, Armor, Guild, World, Racial, Alliance, Craft, Constellation, Grimoire, Script |
| subcategory | TEXT | Skill line or sub-constellation name |
| feature_type | TEXT | ACTIVE, PASSIVE, ULTIMATE, MORPH_A, MORPH_B, SLOTTABLE, GRIMOIRE, FOCUS_SCRIPT, SIGNATURE_SCRIPT, AFFIX_SCRIPT, STAR |
| name | TEXT | Official feature name |
| parent_feature | TEXT | Morph parent or NULL |
| class_restriction | TEXT | Class name or ANY or companion name |
| unlock_method | TEXT | How obtained (level, quest, purchase, etc.) |
| resource_type | TEXT | Magicka, Stamina, Ultimate, None, Variable |
| resource_cost | INT | Base cost (NULL for passives) |
| cast_time | TEXT | Instant, Channel X sec, etc. |
| target_type | TEXT | Self, Enemy, Area, Cone, Ground, Ally |
| range_m | INT | Range in meters |
| radius_m | INT | AoE radius (NULL if N/A) |
| duration_sec | DECIMAL | Effect duration |
| cooldown_sec | DECIMAL | Cooldown if applicable |
| base_effect | TEXT | Core mechanic (≤250 chars) |
| scaling_stat | TEXT | Max Magicka, Weapon Damage, etc. |
| max_ranks | INT | Number of ranks (passives) |
| rank_progression | TEXT | JSON: {"1": "effect", "2": "effect"} |
| stages | INT | Champion Point stages |
| points_per_stage | INT | CP cost per stage |
| compatible_grimoires | TEXT | Pipe-delimited grimoire names (scripts only) |
| buff_debuff_granted | TEXT | Major/Minor buffs/debuffs applied |
| synergy | TEXT | Synergy name if generates one |
| tags | TEXT | Pipe-delimited: damage|fire|dot|aoe|execute |
| dlc_required | TEXT | Base Game, Blackwood, Gold Road, etc. |
| patch_updated | TEXT | Last update version |
| source_url | TEXT | UESP/ESO-Hub verification link |

## Expected Row Counts

| Phase | Content | Est. Rows |
|-------|---------|-----------|
| 1 | Player Class Skills | ~500 |
| 2 | Weapon Skills | ~150 |
| 3 | Armor Skills | ~45 |
| 4 | Guild Skills | ~180 |
| 5 | World Skills | ~120 |
| 6 | Alliance War | ~50 |
| 7 | Racial Passives | ~40 |
| 8 | Crafting Skills | ~100 |
| 9 | Scribing System | ~200 |
| 10 | Champion Points | ~99 |
| 11 | Companion Skills | ~300 |
| **TOTAL** | | **~1,800-2,000** |

## Data Sources

- Primary: https://en.uesp.net/wiki/Online:Skills
- Secondary: https://eso-hub.com/en/skills
- Tertiary: https://alcasthq.com

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Generate Excel file from JSON data
python scripts/generate_excel.py
```

## License

Data compiled from publicly available ESO game information for educational and optimization purposes.
