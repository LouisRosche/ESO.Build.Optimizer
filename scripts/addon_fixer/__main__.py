"""
Allow running the addon fixer as a module.

Usage:
    python -m addon_fixer analyze /path/to/addon
    python -m addon_fixer fix /path/to/addon
"""

from .cli import main

if __name__ == "__main__":
    main()
