"""
Seed the features and gear_sets database tables from data/raw/ JSON files.

Usage:
    python scripts/seed_features.py                    # Seed local database
    python scripts/seed_features.py --database-url URL # Seed specific database
    python scripts/seed_features.py --dry-run          # Count entries without writing
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"

# Columns that exist in the features table
FEATURE_COLUMNS = {
    "feature_id", "system", "category", "subcategory", "feature_type",
    "name", "parent_feature", "class_restriction", "unlock_method",
    "resource_type", "resource_cost", "cast_time", "target_type",
    "range_m", "radius_m", "duration_sec", "cooldown_sec",
    "base_effect", "scaling_stat", "max_ranks", "rank_progression",
    "buff_debuff_granted", "synergy", "tags",
    "dlc_required", "patch_updated", "source_url",
}

# Columns that exist in the gear_sets table
GEAR_SET_COLUMNS = {
    "set_id", "name", "set_type", "weight", "bind_type", "tradeable",
    "location", "dlc_required", "bonuses", "pve_tier", "role_affinity",
    "tags", "patch_updated", "source_url",
}


def load_features() -> list[dict]:
    """Load all skill/feature entries from phase*.json files."""
    features = []
    for json_file in sorted(DATA_DIR.glob("phase*.json")):
        try:
            with open(json_file) as f:
                data = json.load(f)
            if isinstance(data, list):
                for entry in data:
                    # Filter to known columns
                    filtered = {k: v for k, v in entry.items() if k in FEATURE_COLUMNS}
                    if "feature_id" in filtered:
                        features.append(filtered)
            logger.info(f"  Loaded {len(data)} entries from {json_file.name}")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"  Skipping {json_file.name}: {e}")
    return features


def load_gear_sets() -> list[dict]:
    """Load all gear set entries from sets_*.json files."""
    gear_sets = []
    for json_file in sorted(DATA_DIR.glob("sets_*.json")):
        try:
            with open(json_file) as f:
                data = json.load(f)
            if isinstance(data, list):
                for entry in data:
                    filtered = {k: v for k, v in entry.items() if k in GEAR_SET_COLUMNS}
                    # Ensure JSON fields are dicts, not strings
                    for json_field in ("bonuses", "role_affinity"):
                        if json_field in filtered and isinstance(filtered[json_field], str):
                            try:
                                filtered[json_field] = json.loads(filtered[json_field])
                            except json.JSONDecodeError:
                                filtered[json_field] = None
                    if "set_id" in filtered:
                        gear_sets.append(filtered)
            logger.info(f"  Loaded {len(data)} entries from {json_file.name}")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"  Skipping {json_file.name}: {e}")
    return gear_sets


async def seed_database(database_url: str, dry_run: bool = False) -> None:
    """Seed features and gear sets into the database."""
    logger.info("Loading feature data from data/raw/...")
    features = load_features()
    gear_sets = load_gear_sets()

    logger.info(f"\nLoaded {len(features)} features and {len(gear_sets)} gear sets")

    if dry_run:
        logger.info("Dry run — no database changes made.")
        return

    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # Upsert features
        logger.info("\nSeeding features table...")
        inserted = 0
        for feature in features:
            cols = ", ".join(feature.keys())
            placeholders = ", ".join(f":{k}" for k in feature.keys())
            stmt = text(
                f"INSERT INTO features ({cols}) VALUES ({placeholders}) "
                f"ON CONFLICT (feature_id) DO UPDATE SET "
                + ", ".join(f"{k} = EXCLUDED.{k}" for k in feature.keys() if k != "feature_id")
            )
            await session.execute(stmt, feature)
            inserted += 1

        logger.info(f"  Upserted {inserted} features")

        # Upsert gear sets
        logger.info("Seeding gear_sets table...")
        inserted = 0
        for gear_set in gear_sets:
            # Convert dict fields to JSON strings for raw SQL
            params = {}
            for k, v in gear_set.items():
                if isinstance(v, (dict, list)):
                    params[k] = json.dumps(v)
                else:
                    params[k] = v

            cols = ", ".join(params.keys())
            placeholders = ", ".join(f":{k}" for k in params.keys())
            stmt = text(
                f"INSERT INTO gear_sets ({cols}) VALUES ({placeholders}) "
                f"ON CONFLICT (set_id) DO UPDATE SET "
                + ", ".join(f"{k} = EXCLUDED.{k}" for k in params.keys() if k != "set_id")
            )
            await session.execute(stmt, params)
            inserted += 1

        logger.info(f"  Upserted {inserted} gear sets")

        await session.commit()
        logger.info("\nSeeding complete!")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed features and gear sets into the database")
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL (default: from api.core.config)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count entries without writing to database",
    )
    args = parser.parse_args()

    if args.database_url:
        db_url = args.database_url
    else:
        from api.core.config import settings
        db_url = settings.database_url

    asyncio.run(seed_database(db_url, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
