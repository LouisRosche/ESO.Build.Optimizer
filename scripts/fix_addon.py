#!/usr/bin/env python3
"""
ESO Addon Fixer - Automated tool for fixing broken ESO addons.

This script provides a simple entry point to the addon fixer tool.

Usage:
    python scripts/fix_addon.py analyze /path/to/addon
    python scripts/fix_addon.py fix /path/to/addon
    python scripts/fix_addon.py fix /path/to/addon -o /output/dir
    python scripts/fix_addon.py migrations
    python scripts/fix_addon.py info

For full help:
    python scripts/fix_addon.py --help
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from addon_fixer.cli import main

if __name__ == "__main__":
    sys.exit(main())
