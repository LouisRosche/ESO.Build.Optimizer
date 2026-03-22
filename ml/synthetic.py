"""
Synthetic combat data generator for testing the ML pipeline.

Generates realistic combat runs with correlated metrics for use in
percentile calculation and recommendation engine testing.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from ml.percentile import (
    CombatRun,
    ContentInfo,
    ContentType,
    ContributionMetrics,
    Difficulty,
    RoleType,
)
from ml.recommendations import (
    BuildSnapshot,
    CombatMetrics as RecCombatMetrics,
    CombatRun as RecCombatRun,
    ContributionScores,
)

# Realistic ESO content
DUNGEON_NAMES = [
    "Lair of Maarselok", "Black Drake Villa", "Red Petal Bastion",
    "Coral Aerie", "Graven Deep", "Earthen Root Enclave",
    "Bal Sunnar", "Scrivener's Hall", "Oathsworn Pit",
]

TRIAL_NAMES = [
    "Rockgrove", "Dreadsail Reef", "Sanity's Edge",
    "Lucent Citadel", "Halls of Fabrication", "Cloudrest",
]

GEAR_SETS_BY_ROLE = {
    RoleType.DPS: [
        "Kinras's Wrath", "Bahsei's Mania", "Pillar of Nirn",
        "Relequen", "Whorl of the Depths", "Coral Riptide",
        "Tzogvin's Warband", "Ansuul's Torment",
    ],
    RoleType.HEALER: [
        "Spell Power Cure", "Roaring Opportunist", "Vestment of Olorime",
        "Hollowfang Thirst", "Stone-Talker's Oath",
    ],
    RoleType.TANK: [
        "Saxhleel Champion", "Pearlescent Ward", "Turning Tide",
        "Claw of Yolnahkriin", "Drake's Rush",
    ],
}

SKILLS_BY_CLASS = {
    "Dragonknight": {
        "front": ["Molten Whip", "Flames of Oblivion", "Burning Embers", "Engulfing Flames", "Standard of Might"],
        "back": ["Unstable Wall of Fire", "Cauterize", "Venomous Claw", "Noxious Breath", "Ferocious Leap"],
    },
    "Nightblade": {
        "front": ["Surprise Attack", "Killer's Blade", "Relentless Focus", "Concealed Weapon", "Incapacitating Strike"],
        "back": ["Twisting Path", "Sap Essence", "Unstable Wall of Elements", "Leeching Strikes", "Soul Harvest"],
    },
    "Sorcerer": {
        "front": ["Crystal Fragments", "Daedric Prey", "Haunting Curse", "Volatile Familiar", "Greater Storm Atronach"],
        "back": ["Unstable Wall of Elements", "Boundless Storm", "Critical Surge", "Twilight Tormentor", "Power Overload"],
    },
    "Templar": {
        "front": ["Puncturing Sweep", "Blazing Spear", "Purifying Light", "Solar Barrage", "Crescent Sweep"],
        "back": ["Unstable Wall of Elements", "Radiant Glory", "Reflective Light", "Channeled Focus", "Remembrance"],
    },
}

RACES = ["Dark Elf", "High Elf", "Khajiit", "Orc", "Nord", "Breton", "Argonian"]
CLASSES = list(SKILLS_BY_CLASS.keys())


def generate_percentile_population(
    count: int = 200,
    content_name: str = "Lair of Maarselok",
    content_type: ContentType = ContentType.DUNGEON,
    difficulty: Difficulty = Difficulty.VETERAN,
    role: RoleType = RoleType.DPS,
    skill_spread: float = 0.3,
) -> list[CombatRun]:
    """
    Generate a realistic population of CombatRuns for percentile testing.

    Metrics follow a roughly normal distribution around a mean, with
    correlated sub-metrics (e.g., high damage_dealt correlates with
    higher buff_uptime and mechanic_execution).

    Args:
        count: Number of runs to generate
        content_name: Dungeon/trial name
        content_type: Content category
        difficulty: Difficulty level
        role: Player role
        skill_spread: How much variance in player skill (0.0-1.0)
    """
    runs = []
    base_time = datetime.now(timezone.utc) - timedelta(days=30)

    for i in range(count):
        # Generate a "skill level" for this player (0.0 = bad, 1.0 = great)
        skill = random.gauss(0.5, skill_spread)
        skill = max(0.05, min(0.98, skill))

        # Metrics correlate with skill but have individual noise
        damage_dealt = _noisy(skill, 0.1)
        buff_uptime = _noisy(skill * 0.9 + 0.1, 0.08)
        mechanic_execution = _noisy(skill * 0.8 + 0.15, 0.1)
        resource_efficiency = _noisy(skill * 0.7 + 0.2, 0.12)
        debuff_uptime = _noisy(skill * 0.6 + 0.1, 0.15)
        healing_done = _noisy(0.05, 0.03) if role == RoleType.DPS else _noisy(skill * 0.8, 0.1)
        damage_taken = _noisy(0.3 - skill * 0.2, 0.08)

        run = CombatRun(
            run_id=f"syn-{i:04d}",
            player_id=f"player-{i % 80:03d}",
            character_name=f"Char{i % 80}",
            timestamp=base_time + timedelta(hours=i * 2, minutes=random.randint(0, 59)),
            content=ContentInfo(
                content_type=content_type,
                name=content_name,
                difficulty=difficulty,
            ),
            duration_sec=random.randint(240, 600),
            success=random.random() < (0.5 + skill * 0.4),
            group_size=4 if content_type == ContentType.DUNGEON else 12,
            cp_level=random.randint(1800, 2400),
            role=role,
            metrics=ContributionMetrics(
                damage_dealt=damage_dealt,
                damage_taken=damage_taken,
                healing_done=healing_done,
                buff_uptime=buff_uptime,
                debuff_uptime=debuff_uptime,
                mechanic_execution=mechanic_execution,
                resource_efficiency=resource_efficiency,
            ),
        )
        runs.append(run)

    return runs


def generate_recommendation_run(
    skill_level: float = 0.5,
    player_class: str = "Dragonknight",
    role: RoleType = RoleType.DPS,
    content_name: str = "Lair of Maarselok",
) -> RecCombatRun:
    """
    Generate a single CombatRun with full build snapshot for recommendation testing.

    Args:
        skill_level: 0.0 (beginner) to 1.0 (expert)
        player_class: ESO class name
        role: Player role
        content_name: Content name
    """
    class_skills = SKILLS_BY_CLASS.get(player_class, SKILLS_BY_CLASS["Dragonknight"])
    gear_pool = GEAR_SETS_BY_ROLE.get(role, GEAR_SETS_BY_ROLE[RoleType.DPS])

    # Better players use better gear combos
    num_sets = 2 if skill_level > 0.3 else 1
    sets = random.sample(gear_pool, min(num_sets, len(gear_pool)))

    # DPS scales with skill level (realistic ESO range: 20k-120k)
    base_dps = 20000 + skill_level * 100000
    dps = int(_noisy_val(base_dps, base_dps * 0.1))
    duration = random.randint(240, 600)

    # Buff uptimes correlate with skill
    buff_uptimes = {}
    for buff_name in ["Major Brutality", "Major Savagery", "Minor Force", "Major Berserk"]:
        buff_uptimes[buff_name] = round(_noisy(skill_level * 0.85 + 0.1, 0.08), 3)

    build = BuildSnapshot(
        player_class=player_class,
        subclass=None,
        race=random.choice(RACES),
        cp_level=random.randint(1800, 2400),
        sets=sets,
        skills_front=class_skills["front"][:5],
        skills_back=class_skills["back"][:5],
        champion_points={},
    )

    metrics = RecCombatMetrics(
        damage_done=dps * duration,
        dps=float(dps),
        crit_rate=round(_noisy(skill_level * 0.3 + 0.4, 0.05), 3),
        healing_done=int(duration * _noisy_val(200, 100)),
        hps=round(_noisy_val(200, 100), 1),
        overhealing=int(duration * _noisy_val(500, 200)) if skill_level < 0.5 else 0,
        damage_taken=int(duration * _noisy_val(3000 - skill_level * 1500, 500)),
        damage_blocked=int(duration * _noisy_val(500, 200)),
        damage_mitigated=int(duration * _noisy_val(1000, 300)),
        deaths=max(0, int(random.gauss(2 - skill_level * 2, 0.8))),
        interrupts=random.randint(0, 5),
        synergies_used=random.randint(3, 15),
        buff_uptime=buff_uptimes,
        debuff_uptime={},
    )

    contribution = ContributionScores(
        damage_dealt=_noisy(skill_level, 0.1),
        damage_taken=_noisy(0.3 - skill_level * 0.2, 0.08),
        healing_done=_noisy(0.05, 0.03),
        buff_uptime=_noisy(skill_level * 0.85 + 0.1, 0.08),
        debuff_uptime=_noisy(skill_level * 0.6 + 0.1, 0.1),
        mechanic_execution=_noisy(skill_level * 0.8 + 0.15, 0.1),
        resource_efficiency=_noisy(skill_level * 0.7 + 0.2, 0.1),
    )

    return RecCombatRun(
        run_id=f"rec-run-{random.randint(1000, 9999)}",
        player_id=f"player-{random.randint(1, 100):03d}",
        character_name=f"TestChar",
        timestamp=datetime.now(timezone.utc),
        content=RecCombatRun.__dataclass_fields__["content"].type(
            content_type="dungeon",
            name=content_name,
            difficulty="veteran",
        ) if hasattr(RecCombatRun, "__dataclass_fields__") else type("ContentInfo", (), {
            "content_type": "dungeon",
            "name": content_name,
            "difficulty": "veteran",
            "matches": lambda self, other: self.name == other.name,
        })(),
        duration_sec=duration,
        success=random.random() < (0.5 + skill_level * 0.4),
        group_size=4,
        build_snapshot=build,
        metrics=metrics,
        contribution_scores=contribution,
    )


def _noisy(base: float, noise: float) -> float:
    """Return base + Gaussian noise, clamped to [0, 1]."""
    return max(0.0, min(1.0, random.gauss(base, noise)))


def _noisy_val(base: float, noise: float) -> float:
    """Return base + Gaussian noise, clamped to >= 0."""
    return max(0.0, random.gauss(base, noise))
