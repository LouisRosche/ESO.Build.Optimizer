"""
ESO Build Optimizer - SavedVariables File Watcher

This module watches the ESO SavedVariables directory for changes and parses
the addon's data file. It extracts combat run data, build snapshots, and
metrics, emitting events when new data is detected.

ESO writes SavedVariables data only on logout or zone change, so this watcher
monitors file modifications and parses the Lua table format used by ESO.

Usage:
    from watcher import SavedVariablesWatcher

    def on_combat_run(run_data):
        print(f"New combat run: {run_data['run_id']}")

    def on_build_change(build_data):
        print(f"Build updated: {build_data['character_name']}")

    watcher = SavedVariablesWatcher()
    watcher.on_combat_run = on_combat_run
    watcher.on_build_change = on_build_change
    watcher.start()
"""

from __future__ import annotations

import hashlib
import logging
import os
import platform
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

try:
    from watchdog.events import FileModifiedEvent, FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    raise ImportError(
        "The 'watchdog' library is required. Install with: pip install watchdog"
    )


# Configure module logger
logger = logging.getLogger(__name__)

# Maximum cached combat runs to prevent unbounded memory growth
MAX_CACHED_RUNS = 10000


# =============================================================================
# Platform-Specific Path Detection
# =============================================================================


def get_default_saved_variables_path() -> Path:
    """
    Get the default SavedVariables directory path based on the current platform.

    Returns:
        Path to the SavedVariables directory.

    Raises:
        OSError: If the platform is not supported or path cannot be determined.
    """
    system = platform.system()

    if system == "Windows":
        # Windows: Documents/Elder Scrolls Online/live/SavedVariables/
        userprofile = os.environ.get("USERPROFILE")
        if not userprofile:
            userprofile = os.path.expanduser("~")
        documents = Path(userprofile) / "Documents"
        return documents / "Elder Scrolls Online" / "live" / "SavedVariables"

    elif system == "Darwin":
        # macOS: ~/Documents/Elder Scrolls Online/live/SavedVariables/
        return (
            Path.home()
            / "Documents"
            / "Elder Scrolls Online"
            / "live"
            / "SavedVariables"
        )

    elif system == "Linux":
        # Linux (Steam/Proton): ~/.steam/steam/steamapps/compatdata/306130/...
        steam_path = (
            Path.home()
            / ".steam"
            / "steam"
            / "steamapps"
            / "compatdata"
            / "306130"
            / "pfx"
            / "drive_c"
            / "users"
            / "steamuser"
            / "Documents"
            / "Elder Scrolls Online"
            / "live"
            / "SavedVariables"
        )

        # Alternative Flatpak Steam path
        flatpak_path = (
            Path.home()
            / ".var"
            / "app"
            / "com.valvesoftware.Steam"
            / ".steam"
            / "steam"
            / "steamapps"
            / "compatdata"
            / "306130"
            / "pfx"
            / "drive_c"
            / "users"
            / "steamuser"
            / "Documents"
            / "Elder Scrolls Online"
            / "live"
            / "SavedVariables"
        )

        # Check which path exists
        if steam_path.exists():
            return steam_path
        elif flatpak_path.exists():
            return flatpak_path
        else:
            # Return the standard path even if it doesn't exist yet
            return steam_path

    else:
        raise OSError(f"Unsupported platform: {system}")


def find_saved_variables_paths() -> list[Path]:
    """
    Find all possible SavedVariables directories on the system.

    This searches common installation locations for ESO.

    Returns:
        List of existing SavedVariables directory paths.
    """
    paths = []
    system = platform.system()

    if system == "Windows":
        # Check multiple possible locations
        for base in [
            Path(os.environ.get("USERPROFILE", "")) / "Documents",
            Path(os.environ.get("ONEDRIVE", "")) / "Documents" if os.environ.get("ONEDRIVE") else None,
        ]:
            if base is None:
                continue
            for variant in ["live", "pts", "liveeu"]:
                path = base / "Elder Scrolls Online" / variant / "SavedVariables"
                if path.exists():
                    paths.append(path)

    elif system == "Darwin":
        for variant in ["live", "pts", "liveeu"]:
            path = (
                Path.home()
                / "Documents"
                / "Elder Scrolls Online"
                / variant
                / "SavedVariables"
            )
            if path.exists():
                paths.append(path)

    elif system == "Linux":
        # Steam paths
        steam_bases = [
            Path.home() / ".steam" / "steam",
            Path.home() / ".local" / "share" / "Steam",
            Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".steam" / "steam",
        ]

        for steam_base in steam_bases:
            for variant in ["live", "pts", "liveeu"]:
                path = (
                    steam_base
                    / "steamapps"
                    / "compatdata"
                    / "306130"
                    / "pfx"
                    / "drive_c"
                    / "users"
                    / "steamuser"
                    / "Documents"
                    / "Elder Scrolls Online"
                    / variant
                    / "SavedVariables"
                )
                if path.exists():
                    paths.append(path)

    return paths


# =============================================================================
# Lua Table Parser
# =============================================================================


class LuaParseError(Exception):
    """Exception raised when Lua parsing fails."""

    pass


class LuaTableParser:
    """
    Parser for ESO SavedVariables Lua table format.

    ESO SavedVariables files contain Lua table definitions like:
        ESOBuildOptimizer_SavedVariables = {
            ["key"] = "value",
            ["nested"] = {
                [1] = "array element",
            },
        }

    This parser converts these to Python dictionaries.
    """

    # Token patterns
    TOKEN_PATTERNS = [
        ("WHITESPACE", r"\s+"),
        ("COMMENT", r"--[^\n]*"),
        ("MULTILINE_COMMENT", r"--\[\[.*?\]\]"),
        ("STRING_DOUBLE", r'"(?:[^"\\]|\\.)*"'),
        ("STRING_SINGLE", r"'(?:[^'\\]|\\.)*'"),
        ("STRING_LONG", r"\[\[.*?\]\]"),
        ("NUMBER", r"-?(?:0x[0-9a-fA-F]+|\d+\.?\d*(?:[eE][+-]?\d+)?)"),
        ("BOOLEAN", r"\b(?:true|false)\b"),
        ("NIL", r"\bnil\b"),
        ("IDENTIFIER", r"[a-zA-Z_][a-zA-Z0-9_]*"),
        ("EQUALS", r"="),
        ("LBRACE", r"\{"),
        ("RBRACE", r"\}"),
        ("LBRACKET", r"\["),
        ("RBRACKET", r"\]"),
        ("COMMA", r","),
        ("SEMICOLON", r";"),
    ]

    def __init__(self):
        """Initialize the parser with compiled regex patterns."""
        pattern = "|".join(
            f"(?P<{name}>{regex})" for name, regex in self.TOKEN_PATTERNS
        )
        self._tokenizer = re.compile(pattern, re.DOTALL)

    def parse(self, lua_content: str) -> dict[str, Any]:
        """
        Parse a Lua SavedVariables file content.

        Args:
            lua_content: The raw Lua file content.

        Returns:
            Dictionary containing all SavedVariables tables.

        Raises:
            LuaParseError: If parsing fails.
        """
        result = {}

        # Find all top-level variable assignments
        # Pattern: IDENTIFIER = { ... }
        assignment_pattern = re.compile(
            r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(\{)", re.DOTALL
        )

        pos = 0
        while pos < len(lua_content):
            match = assignment_pattern.search(lua_content, pos)
            if not match:
                break

            var_name = match.group(1)
            table_start = match.start(2)

            try:
                table_value, end_pos = self._parse_table(lua_content, table_start)
                result[var_name] = table_value
                pos = end_pos
            except LuaParseError as e:
                logger.warning(f"Failed to parse table {var_name}: {e}")
                # Try to skip to next assignment
                pos = match.end()

        return result

    def parse_table_string(self, table_string: str) -> Any:
        """
        Parse a single Lua table string.

        Args:
            table_string: A string containing a Lua table like "{ ... }".

        Returns:
            Parsed Python object (dict or list).
        """
        table_string = table_string.strip()
        if not table_string.startswith("{"):
            raise LuaParseError("Table string must start with '{'")

        value, _ = self._parse_table(table_string, 0)
        return value

    def _parse_table(self, content: str, start: int) -> tuple[Any, int]:
        """
        Parse a Lua table starting at the given position.

        Returns:
            Tuple of (parsed value, end position).
        """
        if content[start] != "{":
            raise LuaParseError(f"Expected '{{' at position {start}")

        pos = start + 1
        result: dict[Any, Any] = {}
        array_index = 1
        is_array = True

        while pos < len(content):
            # Skip whitespace and comments
            pos = self._skip_whitespace(content, pos)

            if pos >= len(content):
                raise LuaParseError("Unexpected end of content in table")

            # Check for table end
            if content[pos] == "}":
                break

            # Parse key-value pair or array element
            key: Any
            value: Any

            if content[pos] == "[":
                # Bracketed key: [key] = value
                pos += 1
                pos = self._skip_whitespace(content, pos)

                key, pos = self._parse_value(content, pos)
                pos = self._skip_whitespace(content, pos)

                if pos >= len(content) or content[pos] != "]":
                    raise LuaParseError(f"Expected ']' at position {pos}")
                pos += 1

                pos = self._skip_whitespace(content, pos)

                if pos >= len(content) or content[pos] != "=":
                    raise LuaParseError(f"Expected '=' at position {pos}")
                pos += 1

                pos = self._skip_whitespace(content, pos)
                value, pos = self._parse_value(content, pos)

                # Check if this breaks array pattern
                if key != array_index:
                    is_array = False
                else:
                    array_index += 1

            elif self._is_identifier_start(content, pos):
                # Check for identifier = value pattern
                ident_match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=", content[pos:])
                if ident_match:
                    key = ident_match.group(1)
                    pos += ident_match.end()
                    pos = self._skip_whitespace(content, pos)
                    value, pos = self._parse_value(content, pos)
                    is_array = False
                else:
                    # Array element (bare value)
                    value, pos = self._parse_value(content, pos)
                    key = array_index
                    array_index += 1
            else:
                # Array element (bare value)
                value, pos = self._parse_value(content, pos)
                key = array_index
                array_index += 1

            result[key] = value

            # Skip separator
            pos = self._skip_whitespace(content, pos)
            if pos < len(content) and content[pos] in ",;":
                pos += 1

        if pos >= len(content) or content[pos] != "}":
            raise LuaParseError(f"Expected '}}' at position {pos}")

        pos += 1

        # Convert to list if it's an array
        if is_array and result and all(isinstance(k, int) for k in result.keys()):
            max_key = max(result.keys())
            if max_key == len(result):
                return [result[i] for i in range(1, max_key + 1)], pos

        return result, pos

    def _parse_value(self, content: str, pos: int) -> tuple[Any, int]:
        """Parse a single Lua value at the given position."""
        pos = self._skip_whitespace(content, pos)

        if pos >= len(content):
            raise LuaParseError("Unexpected end of content")

        char = content[pos]

        # Table
        if char == "{":
            return self._parse_table(content, pos)

        # String (double-quoted)
        if char == '"':
            return self._parse_string(content, pos, '"')

        # String (single-quoted)
        if char == "'":
            return self._parse_string(content, pos, "'")

        # Long string [[...]]
        if content[pos : pos + 2] == "[[":
            return self._parse_long_string(content, pos)

        # Number, boolean, nil, or identifier
        token_match = re.match(
            r"(-?(?:0x[0-9a-fA-F]+|\d+\.?\d*(?:[eE][+-]?\d+)?)|true|false|nil|[a-zA-Z_][a-zA-Z0-9_]*)",
            content[pos:],
        )

        if token_match:
            token = token_match.group(1)
            new_pos = pos + len(token)

            if token == "true":
                return True, new_pos
            elif token == "false":
                return False, new_pos
            elif token == "nil":
                return None, new_pos
            elif re.match(r"-?(?:0x[0-9a-fA-F]+|\d+\.?\d*(?:[eE][+-]?\d+)?)", token):
                # Number
                if "." in token or "e" in token.lower():
                    return float(token), new_pos
                elif token.startswith("0x") or token.startswith("-0x"):
                    return int(token, 16), new_pos
                else:
                    return int(token), new_pos
            else:
                # Identifier (treat as string)
                return token, new_pos

        raise LuaParseError(f"Cannot parse value at position {pos}: {content[pos:pos+20]}")

    def _parse_string(self, content: str, pos: int, quote: str) -> tuple[str, int]:
        """Parse a quoted string."""
        if content[pos] != quote:
            raise LuaParseError(f"Expected {quote} at position {pos}")

        pos += 1
        result = []

        while pos < len(content):
            char = content[pos]

            if char == quote:
                return "".join(result), pos + 1

            if char == "\\":
                if pos + 1 >= len(content):
                    raise LuaParseError("Unexpected end of string")
                next_char = content[pos + 1]
                if next_char == "n":
                    result.append("\n")
                elif next_char == "t":
                    result.append("\t")
                elif next_char == "r":
                    result.append("\r")
                elif next_char == "\\":
                    result.append("\\")
                elif next_char == quote:
                    result.append(quote)
                else:
                    result.append(next_char)
                pos += 2
            else:
                result.append(char)
                pos += 1

        raise LuaParseError("Unterminated string")

    def _parse_long_string(self, content: str, pos: int) -> tuple[str, int]:
        """Parse a long string [[...]]."""
        if content[pos : pos + 2] != "[[":
            raise LuaParseError(f"Expected '[[' at position {pos}")

        end = content.find("]]", pos + 2)
        if end == -1:
            raise LuaParseError("Unterminated long string")

        return content[pos + 2 : end], end + 2

    def _skip_whitespace(self, content: str, pos: int) -> int:
        """Skip whitespace and comments."""
        while pos < len(content):
            # Skip whitespace
            if content[pos].isspace():
                pos += 1
                continue

            # Skip single-line comment
            if content[pos : pos + 2] == "--":
                if content[pos : pos + 4] == "--[[":
                    # Multi-line comment
                    end = content.find("]]", pos + 4)
                    if end == -1:
                        return len(content)
                    pos = end + 2
                else:
                    # Single-line comment
                    end = content.find("\n", pos)
                    if end == -1:
                        return len(content)
                    pos = end + 1
                continue

            break

        return pos

    def _is_identifier_start(self, content: str, pos: int) -> bool:
        """Check if position starts an identifier."""
        if pos >= len(content):
            return False
        char = content[pos]
        return char.isalpha() or char == "_"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class CombatRun:
    """Represents a single combat encounter run."""

    run_id: str
    character_name: str
    timestamp: datetime
    content_type: str  # dungeon, trial, arena, overworld
    content_name: str
    difficulty: str  # normal, veteran, hardmode
    duration_sec: float
    success: bool
    group_size: int
    build_snapshot: dict[str, Any]
    metrics: dict[str, Any]
    contribution_scores: dict[str, float] = field(default_factory=dict)
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class BuildSnapshot:
    """Represents a character's build state."""

    character_name: str
    timestamp: datetime
    class_name: str
    subclass: Optional[str]
    race: str
    cp_level: int
    sets: list[str]
    skills_front: list[str]
    skills_back: list[str]
    champion_points: dict[str, Any]
    raw_data: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# SavedVariables Watcher
# =============================================================================


class SavedVariablesEventHandler(FileSystemEventHandler):
    """Handle file system events for SavedVariables files."""

    def __init__(self, watcher: "SavedVariablesWatcher"):
        super().__init__()
        self.watcher = watcher

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.name == self.watcher.addon_filename:
            logger.debug(f"Detected modification to {path}")
            self.watcher._handle_file_change(path)


class SavedVariablesWatcher:
    """
    Watch ESO SavedVariables directory for addon data changes.

    This class monitors the SavedVariables file for the ESO Build Optimizer
    addon and emits events when new combat runs or build changes are detected.

    Attributes:
        saved_variables_path: Path to the SavedVariables directory.
        addon_name: Name of the addon to monitor.
        on_combat_run: Callback for new combat run data.
        on_build_change: Callback for build changes.
        on_error: Callback for errors.
    """

    def __init__(
        self,
        saved_variables_path: Optional[Path] = None,
        addon_name: str = "ESOBuildOptimizer",
        poll_interval: float = 1.0,
    ):
        """
        Initialize the SavedVariables watcher.

        Args:
            saved_variables_path: Path to SavedVariables directory.
                                  Auto-detected if not provided.
            addon_name: Name of the addon to monitor.
            poll_interval: How often to check for changes (seconds).
        """
        self.addon_name = addon_name
        self.addon_filename = f"{addon_name}.lua"
        self.poll_interval = poll_interval

        # Set or detect SavedVariables path
        if saved_variables_path:
            self.saved_variables_path = Path(saved_variables_path)
        else:
            self.saved_variables_path = get_default_saved_variables_path()

        # Parser instance
        self._parser = LuaTableParser()

        # State tracking
        self._last_file_hash: Optional[str] = None
        self._last_combat_runs: set[str] = set()
        self._last_build_hash: Optional[str] = None
        self._observer: Optional[Observer] = None
        self._running = False
        self._lock = threading.Lock()

        # Callbacks
        self.on_combat_run: Optional[Callable[[CombatRun], None]] = None
        self.on_build_change: Optional[Callable[[BuildSnapshot], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_file_change: Optional[Callable[[dict[str, Any]], None]] = None

        logger.info(f"Initialized watcher for {self.saved_variables_path}")

    @property
    def addon_file_path(self) -> Path:
        """Get the full path to the addon's SavedVariables file."""
        return self.saved_variables_path / self.addon_filename

    def start(self, blocking: bool = False) -> None:
        """
        Start watching for SavedVariables changes.

        Args:
            blocking: If True, block until stop() is called.
        """
        if self._running:
            logger.warning("Watcher is already running")
            return

        # Validate path exists
        if not self.saved_variables_path.exists():
            logger.warning(
                f"SavedVariables path does not exist: {self.saved_variables_path}. "
                "Will start watching when it becomes available."
            )

        self._running = True

        # Create and start the observer
        self._observer = Observer()
        event_handler = SavedVariablesEventHandler(self)

        # Watch the parent directory
        if self.saved_variables_path.exists():
            self._observer.schedule(
                event_handler, str(self.saved_variables_path), recursive=False
            )
            logger.info(f"Watching {self.saved_variables_path}")
        else:
            # Watch a parent that exists and check periodically
            watch_path = self.saved_variables_path
            while not watch_path.exists() and watch_path.parent != watch_path:
                watch_path = watch_path.parent

            if watch_path.exists():
                self._observer.schedule(
                    event_handler, str(watch_path), recursive=True
                )
                logger.info(f"Watching {watch_path} (waiting for SavedVariables)")

        self._observer.start()

        # Do initial parse if file exists
        if self.addon_file_path.exists():
            self._handle_file_change(self.addon_file_path)

        if blocking:
            try:
                while self._running:
                    time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                self.stop()

    def stop(self) -> None:
        """Stop watching for changes."""
        self._running = False

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5.0)
            self._observer = None
            logger.info("Watcher stopped")

    def parse_current_file(self) -> Optional[dict[str, Any]]:
        """
        Parse the current SavedVariables file.

        Returns:
            Parsed data dictionary or None if file doesn't exist.
        """
        if not self.addon_file_path.exists():
            logger.debug(f"Addon file not found: {self.addon_file_path}")
            return None

        try:
            content = self.addon_file_path.read_text(encoding="utf-8")
            return self._parser.parse(content)
        except Exception as e:
            logger.error(f"Failed to parse {self.addon_file_path}: {e}")
            if self.on_error:
                self.on_error(e)
            return None

    def _handle_file_change(self, path: Path) -> None:
        """Handle a detected file change with retry logic for race conditions."""
        with self._lock:
            content = None
            # Retry logic to handle race conditions during file writes
            for attempt in range(3):
                try:
                    if not path.exists():
                        return
                    content = path.read_text(encoding="utf-8")
                    break
                except (PermissionError, IOError) as e:
                    if attempt < 2:
                        time.sleep(0.5)
                    else:
                        logger.warning(f"Could not read file after retries: {e}")
                        return

            if content is None:
                return

            try:
                current_hash = hashlib.sha256(content.encode()).hexdigest()

                if current_hash == self._last_file_hash:
                    return

                self._last_file_hash = current_hash
                logger.info(f"Processing file change: {path}")

                # Parse the file
                data = self._parser.parse(content)

                # Emit raw file change event
                if self.on_file_change:
                    self.on_file_change(data)

                # Process structured data
                self._process_data(data)

            except Exception as e:
                logger.error(f"Error handling file change: {e}")
                if self.on_error:
                    self.on_error(e)

    def _process_data(self, data: dict[str, Any]) -> None:
        """Process parsed SavedVariables data."""
        # Look for the main SavedVariables table
        # ESO creates tables like: ESOBuildOptimizer_SavedVariables
        sv_key = f"{self.addon_name}_SavedVariables"
        sv_data = data.get(sv_key, {})

        if not sv_data:
            # Try alternate naming patterns
            for key in data:
                if self.addon_name in key:
                    sv_data = data[key]
                    break

        if not sv_data:
            logger.debug("No SavedVariables data found for addon")
            return

        # Process combat runs
        self._process_combat_runs(sv_data)

        # Process build snapshots
        self._process_builds(sv_data)

    def _process_combat_runs(self, sv_data: dict[str, Any]) -> None:
        """Process combat run data from SavedVariables."""
        combat_runs = sv_data.get("combatRuns", sv_data.get("combat_runs", []))

        if not isinstance(combat_runs, (list, dict)):
            return

        # Handle both list and dict formats
        if isinstance(combat_runs, dict):
            combat_runs = list(combat_runs.values())

        for run_data in combat_runs:
            if not isinstance(run_data, dict):
                continue

            run_id = run_data.get("run_id", run_data.get("runId", ""))
            if not run_id or run_id in self._last_combat_runs:
                continue

            self._last_combat_runs.add(run_id)

            # Prevent unbounded memory growth by limiting cache size
            if len(self._last_combat_runs) > MAX_CACHED_RUNS:
                # Convert to list, sort would require timestamps - just keep arbitrary subset
                # Since run_ids are UUIDs/timestamps, we keep the set but trim it
                excess = len(self._last_combat_runs) - MAX_CACHED_RUNS
                runs_list = list(self._last_combat_runs)
                self._last_combat_runs = set(runs_list[excess:])

            try:
                combat_run = self._create_combat_run(run_data)
                if self.on_combat_run:
                    self.on_combat_run(combat_run)
                logger.info(f"New combat run detected: {run_id}")
            except Exception as e:
                logger.error(f"Failed to process combat run {run_id}: {e}")

    def _process_builds(self, sv_data: dict[str, Any]) -> None:
        """Process build snapshot data from SavedVariables."""
        builds = sv_data.get("builds", sv_data.get("buildSnapshots", {}))

        if not isinstance(builds, dict):
            return

        # Get current build (most recent or active character)
        current_build = sv_data.get("currentBuild", sv_data.get("activeBuild", {}))

        if not current_build and builds:
            # Use first build if no current specified
            current_build = next(iter(builds.values()), {})

        if not current_build:
            return

        # Check if build changed
        build_hash = hashlib.sha256(str(current_build).encode()).hexdigest()
        if build_hash == self._last_build_hash:
            return

        self._last_build_hash = build_hash

        try:
            build_snapshot = self._create_build_snapshot(current_build)
            if self.on_build_change:
                self.on_build_change(build_snapshot)
            logger.info(f"Build change detected: {build_snapshot.character_name}")
        except Exception as e:
            logger.error(f"Failed to process build snapshot: {e}")

    def _create_combat_run(self, run_data: dict[str, Any]) -> CombatRun:
        """Create a CombatRun from raw data."""
        # Parse timestamp
        timestamp_raw = run_data.get("timestamp", run_data.get("time", ""))
        if isinstance(timestamp_raw, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp_raw)
        elif isinstance(timestamp_raw, str):
            try:
                timestamp = datetime.fromisoformat(timestamp_raw)
            except ValueError:
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()

        # Get content info
        content = run_data.get("content", {})
        if isinstance(content, str):
            content = {"name": content, "type": "unknown", "difficulty": "normal"}

        # Get build snapshot
        build_snapshot = run_data.get(
            "build_snapshot", run_data.get("buildSnapshot", {})
        )

        return CombatRun(
            run_id=run_data.get("run_id", run_data.get("runId", "")),
            character_name=run_data.get(
                "character_name", run_data.get("characterName", "Unknown")
            ),
            timestamp=timestamp,
            content_type=content.get("type", "unknown"),
            content_name=content.get("name", "Unknown"),
            difficulty=content.get("difficulty", "normal"),
            duration_sec=float(run_data.get("duration_sec", run_data.get("duration", 0))),
            success=bool(run_data.get("success", True)),
            group_size=int(run_data.get("group_size", run_data.get("groupSize", 1))),
            build_snapshot=build_snapshot,
            metrics=run_data.get("metrics", {}),
            contribution_scores=run_data.get(
                "contribution_scores", run_data.get("contributionScores", {})
            ),
            raw_data=run_data,
        )

    def _create_build_snapshot(self, build_data: dict[str, Any]) -> BuildSnapshot:
        """Create a BuildSnapshot from raw data."""
        # Parse timestamp
        timestamp_raw = build_data.get("timestamp", "")
        if isinstance(timestamp_raw, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp_raw)
        elif isinstance(timestamp_raw, str) and timestamp_raw:
            try:
                timestamp = datetime.fromisoformat(timestamp_raw)
            except ValueError:
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()

        return BuildSnapshot(
            character_name=build_data.get(
                "character_name", build_data.get("characterName", "Unknown")
            ),
            timestamp=timestamp,
            class_name=build_data.get("class", build_data.get("className", "Unknown")),
            subclass=build_data.get("subclass"),
            race=build_data.get("race", "Unknown"),
            cp_level=int(build_data.get("cp_level", build_data.get("cpLevel", 0))),
            sets=build_data.get("sets", []),
            skills_front=build_data.get(
                "skills_front", build_data.get("skillsFront", [])
            ),
            skills_back=build_data.get(
                "skills_back", build_data.get("skillsBack", [])
            ),
            champion_points=build_data.get(
                "champion_points", build_data.get("championPoints", {})
            ),
            raw_data=build_data,
        )

    def get_known_run_ids(self) -> set[str]:
        """Get the set of known combat run IDs."""
        return self._last_combat_runs.copy()

    def clear_run_cache(self) -> None:
        """Clear the cache of known run IDs."""
        with self._lock:
            self._last_combat_runs.clear()
            logger.info("Run cache cleared")


# =============================================================================
# Utility Functions
# =============================================================================


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
) -> None:
    """
    Set up logging for the watcher module.

    Args:
        level: Logging level.
        log_file: Optional path to log file.
    """
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


# =============================================================================
# CLI Entry Point
# =============================================================================


def main() -> None:
    """Command-line entry point for the watcher."""
    import argparse

    parser = argparse.ArgumentParser(
        description="ESO Build Optimizer SavedVariables Watcher"
    )
    parser.add_argument(
        "--path",
        type=Path,
        help="Path to SavedVariables directory (auto-detected if not provided)",
    )
    parser.add_argument(
        "--addon",
        default="ESOBuildOptimizer",
        help="Addon name to monitor (default: ESOBuildOptimizer)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--list-paths",
        action="store_true",
        help="List all detected SavedVariables paths and exit",
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)

    # List paths mode
    if args.list_paths:
        print("Detected SavedVariables paths:")
        paths = find_saved_variables_paths()
        if paths:
            for p in paths:
                print(f"  {p}")
        else:
            print("  No paths found")
            print(f"\nDefault path: {get_default_saved_variables_path()}")
        return

    # Define callbacks
    def on_combat_run(run: CombatRun) -> None:
        print(f"\n{'='*60}")
        print(f"NEW COMBAT RUN: {run.run_id}")
        print(f"  Character: {run.character_name}")
        print(f"  Content: {run.content_name} ({run.difficulty})")
        print(f"  Duration: {run.duration_sec:.1f}s")
        print(f"  Success: {run.success}")
        if run.metrics:
            print(f"  DPS: {run.metrics.get('dps', 'N/A')}")
        print(f"{'='*60}\n")

    def on_build_change(build: BuildSnapshot) -> None:
        print(f"\n{'='*60}")
        print(f"BUILD CHANGE: {build.character_name}")
        print(f"  Class: {build.class_name}")
        if build.subclass:
            print(f"  Subclass: {build.subclass}")
        print(f"  CP Level: {build.cp_level}")
        print(f"  Sets: {', '.join(build.sets) if build.sets else 'None'}")
        print(f"{'='*60}\n")

    def on_error(error: Exception) -> None:
        print(f"\nERROR: {error}\n", file=sys.stderr)

    # Create and start watcher
    watcher = SavedVariablesWatcher(
        saved_variables_path=args.path,
        addon_name=args.addon,
    )
    watcher.on_combat_run = on_combat_run
    watcher.on_build_change = on_build_change
    watcher.on_error = on_error

    print(f"Watching: {watcher.addon_file_path}")
    print("Press Ctrl+C to stop\n")

    try:
        watcher.start(blocking=True)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        watcher.stop()


if __name__ == "__main__":
    main()
