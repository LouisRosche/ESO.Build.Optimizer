#!/usr/bin/env python3
"""
Neon PostgreSQL Database Setup Script

This script initializes the database schema and seeds initial data
from the JSON files in /data/raw/.

Usage:
    # Set environment variable first
    export DATABASE_URL="postgresql+asyncpg://user:pass@host/db?sslmode=require"

    # Run the script
    python scripts/setup_neon.py

    # Or with arguments
    python scripts/setup_neon.py --seed-only     # Only seed data (tables exist)
    python scripts/setup_neon.py --drop-all      # Drop and recreate tables
    python scripts/setup_neon.py --dry-run       # Show what would be done
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data" / "raw"


def get_database_url() -> str:
    """Get database URL from environment."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL environment variable is required.\n"
            "For Neon, use: postgresql+asyncpg://user:pass@host/db?sslmode=require"
        )

    # Convert postgres:// to postgresql+asyncpg:// if needed
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Ensure SSL for Neon
    if "neon" in url and "sslmode" not in url:
        separator = "&" if "?" in url else "?"
        url += f"{separator}sslmode=require"

    return url


async def create_tables(engine, drop_existing: bool = False):
    """Create database tables from SQLAlchemy models."""
    from api.models.database import Base, User, CombatRun, Recommendation, Feature, GearSet, RateLimit

    async with engine.begin() as conn:
        if drop_existing:
            logger.warning("Dropping all existing tables...")
            await conn.run_sync(Base.metadata.drop_all)

        logger.info("Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Tables created successfully!")

    # List created tables
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        ))
        tables = [row[0] for row in result]
        logger.info(f"Tables in database: {', '.join(tables)}")


async def seed_features(session: AsyncSession, dry_run: bool = False):
    """Seed features from JSON files."""
    from api.models.database import Feature

    feature_files = list(DATA_DIR.glob("phase*.json"))
    total_count = 0

    for file_path in sorted(feature_files):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                features = json.load(f)

            if not isinstance(features, list):
                logger.warning(f"Skipping {file_path.name}: not a list")
                continue

            count = 0
            for feature_data in features:
                if "feature_id" not in feature_data:
                    continue

                # Map JSON fields to database columns
                feature = Feature(
                    feature_id=feature_data.get("feature_id"),
                    system=feature_data.get("system", "PLAYER"),
                    category=feature_data.get("category", "Unknown"),
                    subcategory=feature_data.get("subcategory"),
                    feature_type=feature_data.get("feature_type", "ACTIVE"),
                    name=feature_data.get("name", "Unknown"),
                    parent_feature=feature_data.get("parent_feature"),
                    class_restriction=feature_data.get("class_restriction"),
                    unlock_method=feature_data.get("unlock_method"),
                    resource_type=feature_data.get("resource_type"),
                    resource_cost=feature_data.get("resource_cost"),
                    cast_time=feature_data.get("cast_time"),
                    target_type=feature_data.get("target_type"),
                    range_m=feature_data.get("range_m"),
                    radius_m=feature_data.get("radius_m"),
                    duration_sec=feature_data.get("duration_sec"),
                    cooldown_sec=feature_data.get("cooldown_sec"),
                    base_effect=feature_data.get("base_effect"),
                    scaling_stat=feature_data.get("scaling_stat"),
                    max_ranks=feature_data.get("max_ranks"),
                    rank_progression=json.dumps(feature_data.get("rank_progression")) if feature_data.get("rank_progression") else None,
                    buff_debuff_granted=feature_data.get("buff_debuff_granted"),
                    synergy=feature_data.get("synergy"),
                    tags=feature_data.get("tags"),
                    dlc_required=feature_data.get("dlc_required"),
                    patch_updated=feature_data.get("patch_updated", "U48"),
                    source_url=feature_data.get("source_url"),
                )

                if not dry_run:
                    session.add(feature)
                count += 1

            if not dry_run:
                await session.commit()

            logger.info(f"  {file_path.name}: {count} features")
            total_count += count

        except json.JSONDecodeError as e:
            logger.error(f"JSON error in {file_path.name}: {e}")
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            if not dry_run:
                await session.rollback()

    return total_count


async def seed_gear_sets(session: AsyncSession, dry_run: bool = False):
    """Seed gear sets from JSON files."""
    from api.models.database import GearSet

    set_files = list(DATA_DIR.glob("sets_*.json"))
    total_count = 0

    for file_path in sorted(set_files):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                sets = json.load(f)

            if not isinstance(sets, list):
                logger.warning(f"Skipping {file_path.name}: not a list")
                continue

            count = 0
            for set_data in sets:
                if "set_id" not in set_data:
                    continue

                # Map JSON fields to database columns
                gear_set = GearSet(
                    set_id=set_data.get("set_id"),
                    name=set_data.get("name", "Unknown"),
                    set_type=set_data.get("set_type", "Unknown"),
                    weight=set_data.get("weight", "Light"),
                    bind_type=set_data.get("bind_type", "Bind on Pickup"),
                    tradeable=set_data.get("tradeable", False),
                    location=set_data.get("location", "Unknown"),
                    dlc_required=set_data.get("dlc_required"),
                    bonuses=set_data.get("bonuses", {}),
                    pve_tier=set_data.get("pve_tier"),
                    role_affinity=set_data.get("role_affinity"),
                    tags=set_data.get("tags"),
                    patch_updated=set_data.get("patch_updated", "U48"),
                    source_url=set_data.get("source_url"),
                )

                if not dry_run:
                    session.add(gear_set)
                count += 1

            if not dry_run:
                await session.commit()

            logger.info(f"  {file_path.name}: {count} gear sets")
            total_count += count

        except json.JSONDecodeError as e:
            logger.error(f"JSON error in {file_path.name}: {e}")
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            if not dry_run:
                await session.rollback()

    return total_count


async def verify_data(session: AsyncSession):
    """Verify seeded data counts."""
    from sqlalchemy import func, select
    from api.models.database import Feature, GearSet, User, CombatRun

    logger.info("\nData verification:")

    # Count features
    result = await session.execute(select(func.count()).select_from(Feature))
    feature_count = result.scalar()
    logger.info(f"  Features: {feature_count}")

    # Count gear sets
    result = await session.execute(select(func.count()).select_from(GearSet))
    set_count = result.scalar()
    logger.info(f"  Gear Sets: {set_count}")

    # Count users
    result = await session.execute(select(func.count()).select_from(User))
    user_count = result.scalar()
    logger.info(f"  Users: {user_count}")

    # Count combat runs
    result = await session.execute(select(func.count()).select_from(CombatRun))
    run_count = result.scalar()
    logger.info(f"  Combat Runs: {run_count}")


async def main(args):
    """Main setup function."""
    database_url = get_database_url()

    # Mask password in logs
    safe_url = database_url
    if "@" in safe_url:
        parts = safe_url.split("@")
        user_pass = parts[0].split("://")[1] if "://" in parts[0] else parts[0]
        if ":" in user_pass:
            user = user_pass.split(":")[0]
            safe_url = safe_url.replace(user_pass, f"{user}:****")

    logger.info(f"Connecting to database: {safe_url}")

    if args.dry_run:
        logger.info("DRY RUN - No changes will be made")

    # Create engine
    engine = create_async_engine(
        database_url,
        echo=args.verbose,
        pool_pre_ping=True,
    )

    # Create session factory
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        # Test connection
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"Connected to: {version}")

        # Create tables
        if not args.seed_only:
            if not args.dry_run:
                await create_tables(engine, drop_existing=args.drop_all)
            else:
                logger.info("Would create tables (dry run)")

        # Seed data
        async with async_session() as session:
            logger.info("\nSeeding features...")
            feature_count = await seed_features(session, dry_run=args.dry_run)

            logger.info("\nSeeding gear sets...")
            set_count = await seed_gear_sets(session, dry_run=args.dry_run)

            if not args.dry_run:
                logger.info("\nVerifying data...")
                await verify_data(session)

            logger.info(f"\nTotal: {feature_count} features, {set_count} gear sets")

        logger.info("\nSetup completed successfully!")

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Setup Neon PostgreSQL database for ESO Build Optimizer"
    )
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Only seed data (assume tables exist)"
    )
    parser.add_argument(
        "--drop-all",
        action="store_true",
        help="Drop and recreate all tables (WARNING: data loss)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose SQL output"
    )

    args = parser.parse_args()

    asyncio.run(main(args))
