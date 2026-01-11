#!/usr/bin/env python3
"""
Build script for ESO Build Optimizer Companion App
Creates platform-specific executables using PyInstaller.

Usage:
    python build.py              # Build for current platform
    python build.py --all        # Build instructions for all platforms
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_platform_info():
    """Get current platform information."""
    system = platform.system().lower()
    if system == 'darwin':
        return 'macos', '.app', 'icon.icns'
    elif system == 'windows':
        return 'windows', '.exe', 'icon.ico'
    else:
        return 'linux', '', 'icon.png'


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("Error: PyInstaller not installed. Run: pip install pyinstaller")
        return False

    try:
        import watchdog
        import httpx
        print("Core dependencies: OK")
    except ImportError as e:
        print(f"Error: Missing dependency: {e}")
        return False

    return True


def build_executable(output_dir: Path = None):
    """Build the executable for the current platform."""
    platform_name, ext, icon = get_platform_info()

    print(f"\nBuilding for {platform_name}...")

    # Ensure we're in the companion directory
    companion_dir = Path(__file__).parent
    os.chdir(companion_dir)

    # Output directory
    if output_dir is None:
        output_dir = companion_dir / 'dist'

    # Clean previous builds
    for dir_name in ['build', 'dist']:
        dir_path = companion_dir / dir_name
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                print(f"Cleaned {dir_name}/")
            except OSError as e:
                print(f"Warning: Could not clean {dir_name}/: {e}")

    # Run PyInstaller
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        'build.spec'
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        print("Build failed!")
        return False

    # Show output
    dist_dir = companion_dir / 'dist'
    if dist_dir.exists():
        print(f"\nBuild complete! Output in: {dist_dir}")
        for item in dist_dir.iterdir():
            size_mb = item.stat().st_size / (1024 * 1024) if item.is_file() else 0
            print(f"  - {item.name}" + (f" ({size_mb:.1f} MB)" if size_mb else ""))

    return True


def print_all_platforms_instructions():
    """Print instructions for building on all platforms."""
    print("""
ESO Build Optimizer Companion App - Cross-Platform Build Instructions
======================================================================

The companion app can be built for Windows, macOS, and Linux.
Each platform must be built on its native OS.

PREREQUISITES (all platforms):
  pip install -r requirements.txt

WINDOWS:
  1. Open Command Prompt or PowerShell
  2. cd companion
  3. python build.py
  4. Output: dist/ESOBuildOptimizer.exe

macOS:
  1. Open Terminal
  2. cd companion
  3. python build.py
  4. Output: dist/ESOBuildOptimizer.app

LINUX:
  1. Open Terminal
  2. cd companion
  3. python build.py
  4. Output: dist/ESOBuildOptimizer

GITHUB ACTIONS (automated):
  The project includes a GitHub Actions workflow that builds
  for all platforms automatically on each release.
  See: .github/workflows/build-companion.yml

NOTES:
  - Windows builds work on Windows 10/11
  - macOS builds work on 10.15+ (Catalina and later)
  - Linux builds work on most modern distributions
  - The app runs as a system tray icon by default
  - Use --headless flag for server/script usage
""")


def main():
    parser = argparse.ArgumentParser(
        description='Build ESO Build Optimizer Companion App'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Show instructions for building on all platforms'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Output directory for built executable'
    )

    args = parser.parse_args()

    if args.all:
        print_all_platforms_instructions()
        return

    print("ESO Build Optimizer Companion App - Build Script")
    print("=" * 50)

    if not check_dependencies():
        sys.exit(1)

    if not build_executable(args.output):
        sys.exit(1)

    print("\nBuild successful!")


if __name__ == '__main__':
    main()
