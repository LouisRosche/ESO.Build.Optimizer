"""
ESO Build Optimizer - Combat Metrics (CMX) Data Parser

Parses Combat Metrics addon SavedVariables and translates fight data
into our CombatRun schema format for upload via the existing sync pipeline.

Combat Metrics stores data in SavedVariables/CombatMetrics.lua as a Lua table
with the top-level variable `CMX`. Key structures:

    CMX = {
        ["lastfight"] = { ... },        -- Most recent fight summary
        ["log"] = { ... },              -- Combat log entries
        ["data"] = {                    -- Per-account fight history
            ["@AccountName"] = {
                ["CharacterName"] = {
                    [1] = { fight record },
                    [2] = { fight record },
                    ...
                },
            },
        },
    }

Each fight record typically contains:
    - starttime / endtime (or duration)
    - dps, hps
    - damageOut / damageOutTotal
    - healingOut / healingOutTotal
    - damageIn / damageInTotal
    - bossfight (boolean or boss name)
    - bossname
    - units (table of unit data)
    - log (combat log entries with abilities)

Since CMX does not track gear or build info, runs imported from CMX are
marked as partial data (build_snapshot = None) and flagged with
source="combat_metrics".

Usage:
    from cmx_parser import CMXParser

    parser = CMXParser(saved_variables_path)
    runs = parser.parse()
    for run in runs:
        sync_client.upload_run(run)
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from watcher import CombatRun, LuaTableParser

# Configure module logger
logger = logging.getLogger(__name__)

# Combat Metrics SavedVariables filename
CMX_FILENAME = "CombatMetrics.lua"

# Minimum fight duration (seconds) to consider a fight worth importing
MIN_FIGHT_DURATION = 5.0


class CMXParser:
    """
    Parser for Combat Metrics SavedVariables data.

    Reads CombatMetrics.lua, extracts fight records, and converts them
    to CombatRun objects compatible with our sync pipeline.

    Attributes:
        saved_variables_path: Path to the ESO SavedVariables directory.
        uploaded_fight_hashes: Set of hashes for fights already uploaded,
                               used for deduplication.
    """

    def __init__(
        self,
        saved_variables_path: Path,
        uploaded_fight_hashes: Optional[set[str]] = None,
    ):
        """
        Initialize the CMX parser.

        Args:
            saved_variables_path: Path to the SavedVariables directory.
            uploaded_fight_hashes: Optional set of previously uploaded fight
                                   hashes for deduplication. If not provided,
                                   an empty set is used (no dedup).
        """
        self.saved_variables_path = Path(saved_variables_path)
        self.uploaded_fight_hashes = uploaded_fight_hashes or set()
        self._lua_parser = LuaTableParser()

    @property
    def cmx_file_path(self) -> Path:
        """Full path to the CombatMetrics.lua file."""
        return self.saved_variables_path / CMX_FILENAME

    def file_exists(self) -> bool:
        """Check whether the CombatMetrics.lua file exists."""
        return self.cmx_file_path.exists()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def parse(self) -> list[dict[str, Any]]:
        """
        Parse all fight records from CombatMetrics.lua.

        Returns:
            List of fight dicts in CombatRunCreate-compatible format,
            excluding fights that have already been uploaded (dedup).
        """
        if not self.file_exists():
            logger.debug("CombatMetrics.lua not found at %s", self.cmx_file_path)
            return []

        try:
            content = self.cmx_file_path.read_text(encoding="utf-8")
        except (OSError, IOError) as exc:
            logger.error("Failed to read CombatMetrics.lua: %s", exc)
            return []

        try:
            data = self._lua_parser.parse(content)
        except Exception as exc:
            logger.error("Failed to parse CombatMetrics.lua: %s", exc)
            return []

        return self._extract_fights(data)

    def parse_new_fights(self) -> list[dict[str, Any]]:
        """
        Parse only fights not yet uploaded (convenience wrapper).

        Identical to parse() since dedup is built-in, but makes intent
        explicit for callers.
        """
        return self.parse()

    def mark_uploaded(self, fight_hash: str) -> None:
        """Mark a fight hash as uploaded so it will be skipped next parse."""
        self.uploaded_fight_hashes.add(fight_hash)

    # -------------------------------------------------------------------------
    # Fight Extraction
    # -------------------------------------------------------------------------

    def _extract_fights(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Extract fight records from parsed CMX data.

        Handles multiple data layouts that CMX has used across versions:
        1. CMX.data.@Account.CharName.[n] = fight  (structured)
        2. CMX.lastfight = fight                     (single latest fight)
        """
        results: list[dict[str, Any]] = []

        # Find the CMX table - it may be stored as "CMX" or
        # "CombatMetrics_SavedVariables" depending on CMX version
        cmx_data = data.get("CMX", {})
        if not cmx_data:
            cmx_data = data.get("CombatMetrics_SavedVariables", {})
        if not cmx_data:
            # Try any top-level key containing "CombatMetric"
            for key in data:
                if "CombatMetric" in key or "CMX" in key:
                    cmx_data = data[key]
                    break

        if not cmx_data:
            logger.debug("No CMX data found in CombatMetrics.lua")
            return results

        # Extract from structured data (per-account, per-character)
        account_data = cmx_data.get("data", {})
        if isinstance(account_data, dict):
            for account_name, characters in account_data.items():
                if not isinstance(characters, dict):
                    continue
                for char_name, fights in characters.items():
                    fight_list = self._normalize_fight_list(fights)
                    for fight in fight_list:
                        run = self._convert_fight(fight, char_name, account_name)
                        if run is not None:
                            results.append(run)

        # Also extract lastfight if present and not already captured
        lastfight = cmx_data.get("lastfight", {})
        if isinstance(lastfight, dict) and lastfight:
            run = self._convert_fight(lastfight)
            if run is not None:
                results.append(run)

        logger.info(
            "Extracted %d new CMX fight(s) from CombatMetrics.lua", len(results)
        )
        return results

    def _normalize_fight_list(self, fights: Any) -> list[dict[str, Any]]:
        """Normalize fights to a list of dicts regardless of storage format."""
        if isinstance(fights, list):
            return [f for f in fights if isinstance(f, dict)]
        if isinstance(fights, dict):
            # Could be integer-keyed (Lua array converted to dict)
            return [v for v in fights.values() if isinstance(v, dict)]
        return []

    # -------------------------------------------------------------------------
    # Fight Conversion
    # -------------------------------------------------------------------------

    def _convert_fight(
        self,
        fight: dict[str, Any],
        character_name: Optional[str] = None,
        account_name: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Convert a single CMX fight record to our CombatRunCreate-compatible dict.

        Returns None if the fight should be skipped (too short, duplicate, etc.).
        """
        # Calculate fight hash for deduplication
        fight_hash = self._compute_fight_hash(fight)
        if fight_hash in self.uploaded_fight_hashes:
            return None

        # Extract duration
        duration = self._extract_duration(fight)
        if duration < MIN_FIGHT_DURATION:
            return None

        # Extract character name from fight data or parameter
        char_name = (
            fight.get("charname")
            or fight.get("characterName")
            or fight.get("charName")
            or character_name
            or "Unknown"
        )

        # Extract timestamp
        timestamp = self._extract_timestamp(fight)

        # Extract damage metrics
        damage_done = self._to_int(
            fight.get("damageOutTotal")
            or fight.get("damageOut")
            or fight.get("damage")
            or 0
        )

        # DPS - either stored directly or calculated
        dps = self._to_float(fight.get("dps") or 0.0)
        if dps == 0.0 and duration > 0 and damage_done > 0:
            dps = damage_done / duration

        # Healing metrics
        healing_done = self._to_int(
            fight.get("healingOutTotal")
            or fight.get("healingOut")
            or fight.get("healing")
            or 0
        )
        hps = self._to_float(fight.get("hps") or 0.0)
        if hps == 0.0 and duration > 0 and healing_done > 0:
            hps = healing_done / duration

        # Damage taken
        damage_taken = self._to_int(
            fight.get("damageInTotal")
            or fight.get("damageIn")
            or fight.get("damageTaken")
            or 0
        )

        # Boss / content info
        boss_name = fight.get("bossname") or fight.get("bossName") or ""
        is_boss_fight = bool(
            fight.get("bossfight")
            or fight.get("bossFight")
            or boss_name
        )
        content_name = boss_name if boss_name else "Unknown Encounter"
        content_type = "dungeon" if is_boss_fight else "overworld"

        # Group size - CMX sometimes stores this
        group_size = self._to_int(fight.get("groupSize") or fight.get("group_size") or 1)
        if group_size < 1:
            group_size = 1

        # Build the CombatRunCreate-compatible dict
        # Note: build_snapshot is None because CMX does not track gear/skills.
        # The API schema requires build_snapshot, so we provide a minimal
        # placeholder that the server can recognize as partial/CMX data.
        run_data = {
            "character_name": char_name,
            "content": {
                "type": content_type,
                "name": content_name,
                "difficulty": "normal",  # CMX does not reliably distinguish difficulty
            },
            "duration_sec": int(duration),
            "success": bool(fight.get("success", fight.get("completed", True))),
            "group_size": group_size,
            "build_snapshot": None,  # CMX does not track builds
            "metrics": {
                "damage_done": damage_done,
                "dps": round(dps, 1),
                "crit_rate": 0.0,  # Populated below if available
                "healing_done": healing_done,
                "hps": round(hps, 1),
                "overhealing": 0,
                "damage_taken": damage_taken,
                "damage_blocked": 0,
                "damage_mitigated": 0,
                "deaths": self._to_int(fight.get("deaths") or 0),
                "interrupts": self._to_int(fight.get("interrupts") or 0),
                "synergies_used": 0,
                "synergies_provided": 0,
                "time_dead": 0.0,
                "magicka_spent": 0,
                "stamina_spent": 0,
                "ultimate_spent": 0,
                "potion_uses": 0,
                "buff_uptime": [],
                "debuff_uptime": [],
                "dot_uptime": [],
            },
            # Metadata for our pipeline
            "_source": "combat_metrics",
            "_cmx_fight_hash": fight_hash,
            "_account_name": account_name,
            "_timestamp": timestamp.isoformat(),
            "_partial_data": True,
        }

        # Try to extract crit rate if CMX provides it
        crit_rate = fight.get("critRate") or fight.get("crit_rate")
        if crit_rate is not None:
            run_data["metrics"]["crit_rate"] = min(
                1.0, self._to_float(crit_rate)
            )

        # Extract buff/debuff uptimes if CMX provides them
        self._extract_buff_uptimes(fight, run_data["metrics"])

        # Mark as uploaded for dedup
        self.uploaded_fight_hashes.add(fight_hash)

        return run_data

    # -------------------------------------------------------------------------
    # Field Extraction Helpers
    # -------------------------------------------------------------------------

    def _extract_duration(self, fight: dict[str, Any]) -> float:
        """Extract fight duration in seconds from various CMX field names."""
        # Direct duration field
        duration = fight.get("duration") or fight.get("combattime") or fight.get("combatTime")
        if duration is not None:
            return self._to_float(duration)

        # Calculate from start/end times
        start = fight.get("starttime") or fight.get("startTime")
        end = fight.get("endtime") or fight.get("endTime")
        if start is not None and end is not None:
            return max(0.0, self._to_float(end) - self._to_float(start))

        return 0.0

    def _extract_timestamp(self, fight: dict[str, Any]) -> datetime:
        """Extract fight timestamp, falling back to now() if unavailable."""
        for key in ("starttime", "startTime", "timestamp", "time"):
            raw = fight.get(key)
            if raw is None:
                continue
            if isinstance(raw, (int, float)) and raw > 1_000_000_000:
                # Unix timestamp (seconds)
                try:
                    return datetime.fromtimestamp(raw, tz=timezone.utc)
                except (OSError, ValueError):
                    continue
            if isinstance(raw, str):
                try:
                    return datetime.fromisoformat(raw)
                except ValueError:
                    continue

        return datetime.now(tz=timezone.utc)

    def _extract_buff_uptimes(
        self, fight: dict[str, Any], metrics: dict[str, Any]
    ) -> None:
        """Extract buff/debuff uptime data if CMX provides it."""
        # CMX may store buff data in various formats
        buffs = fight.get("buffs") or fight.get("buffUptime") or {}
        if isinstance(buffs, dict):
            buff_list = []
            for name, value in buffs.items():
                uptime = self._to_float(value) if not isinstance(value, dict) else 0.0
                if isinstance(value, dict):
                    uptime = self._to_float(
                        value.get("uptime") or value.get("percentage") or 0.0
                    )
                # Normalize to 0-1 range (CMX sometimes uses 0-100)
                if uptime > 1.0:
                    uptime = uptime / 100.0
                uptime = max(0.0, min(1.0, uptime))
                if uptime > 0:
                    buff_list.append({"name": str(name), "uptime": uptime})
            metrics["buff_uptime"] = buff_list

        debuffs = fight.get("debuffs") or fight.get("debuffUptime") or {}
        if isinstance(debuffs, dict):
            debuff_list = []
            for name, value in debuffs.items():
                uptime = self._to_float(value) if not isinstance(value, dict) else 0.0
                if isinstance(value, dict):
                    uptime = self._to_float(
                        value.get("uptime") or value.get("percentage") or 0.0
                    )
                if uptime > 1.0:
                    uptime = uptime / 100.0
                uptime = max(0.0, min(1.0, uptime))
                if uptime > 0:
                    debuff_list.append({"name": str(name), "uptime": uptime})
            metrics["debuff_uptime"] = debuff_list

    def _compute_fight_hash(self, fight: dict[str, Any]) -> str:
        """
        Compute a stable hash for a fight record for deduplication.

        Uses a combination of timestamp, duration, and damage to create
        a fingerprint that's stable across re-parses but unique per fight.
        """
        # Build a fingerprint from the most stable fields
        parts = [
            str(fight.get("starttime") or fight.get("startTime") or ""),
            str(fight.get("duration") or fight.get("combattime") or ""),
            str(fight.get("damageOutTotal") or fight.get("damageOut") or fight.get("damage") or ""),
            str(fight.get("healingOutTotal") or fight.get("healingOut") or ""),
            str(fight.get("charname") or fight.get("characterName") or ""),
            str(fight.get("bossname") or fight.get("bossName") or ""),
        ]
        fingerprint = "|".join(parts)
        return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]

    # -------------------------------------------------------------------------
    # Type Coercion Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _to_float(value: Any) -> float:
        """Safely convert a value to float."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 0.0
        return 0.0

    @staticmethod
    def _to_int(value: Any) -> int:
        """Safely convert a value to int."""
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value))
            except ValueError:
                return 0
        return 0
