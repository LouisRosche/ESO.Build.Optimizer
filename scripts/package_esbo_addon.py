#!/usr/bin/env python3
"""
Package ESOBuildOptimizer addon for ESOUI distribution.

Creates a properly structured ZIP file ready for upload to esoui.com
or manual installation via Minion.

Usage:
    python scripts/package_esbo_addon.py                # Build ZIP
    python scripts/package_esbo_addon.py --check        # Dry-run validation only
    python scripts/package_esbo_addon.py --output dist/  # Custom output directory
"""

import argparse
import hashlib
import re
import sys
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
ADDON_DIR = REPO_ROOT / "addon" / "ESOBuildOptimizer"
ADDON_NAME = "ESOBuildOptimizer"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "dist"

REQUIRED_FILES = [
    "ESOBuildOptimizer.txt",
    "ESOBuildOptimizer.addon",
    "ESOBuildOptimizer.lua",
    "modules/CombatTracker.lua",
    "modules/BuildSnapshot.lua",
    "modules/MetricsUI.lua",
    "modules/SkillAdvisor.lua",
]

EXCLUDE_PATTERNS = [
    "*.bak", "*.orig", "*.test.lua", "*_spec.lua",
    "__pycache__", ".git", ".DS_Store", "Thumbs.db",
]


def validate_manifest(addon_dir: Path) -> list[str]:
    """Validate manifest file structure and content."""
    errors = []
    manifest = addon_dir / f"{ADDON_NAME}.txt"

    if not manifest.exists():
        errors.append(f"Manifest not found: {manifest}")
        return errors

    content = manifest.read_bytes()
    if b"\r\n" not in content:
        errors.append("Manifest must use CRLF line endings (found LF)")

    text = content.decode("utf-8", errors="replace")
    lines = text.replace("\r\n", "\n").split("\n")

    has_title = has_api = has_version = has_saved_vars = False
    listed_files = []

    for line in lines:
        line = line.strip()
        if line.startswith("## Title:"):
            has_title = True
        elif line.startswith("## APIVersion:"):
            has_api = True
            versions = line.split(":")[1].strip().split()
            for v in versions:
                if not v.isdigit():
                    errors.append(f"Invalid APIVersion: '{v}'")
                elif int(v) < 101047:
                    errors.append(f"APIVersion {v} is too old (minimum 101047)")
        elif line.startswith("## AddOnVersion:"):
            has_version = True
            ver = line.split(":")[1].strip()
            if not ver.isdigit():
                errors.append(f"AddOnVersion must be integer, got '{ver}'")
        elif line.startswith("## SavedVariables:"):
            has_saved_vars = True
        elif not line.startswith("##") and not line.startswith("#") and line:
            listed_files.append(line)

    if not has_title:
        errors.append("Missing ## Title: in manifest")
    if not has_api:
        errors.append("Missing ## APIVersion: in manifest")
    if not has_version:
        errors.append("Missing ## AddOnVersion: in manifest")
    if not has_saved_vars:
        errors.append("Missing ## SavedVariables: in manifest")

    for f in listed_files:
        if not (addon_dir / f).exists():
            errors.append(f"Manifest lists '{f}' but file does not exist")

    return errors


def validate_console_manifest(addon_dir: Path) -> list[str]:
    """Validate .addon console manifest matches .txt."""
    errors = []
    txt = addon_dir / f"{ADDON_NAME}.txt"
    addon = addon_dir / f"{ADDON_NAME}.addon"

    if not addon.exists():
        errors.append(f"Console manifest missing: {ADDON_NAME}.addon")
        return errors

    txt_content = txt.read_bytes().replace(b"\r\n", b"\n")
    addon_content = addon.read_bytes().replace(b"\r\n", b"\n")

    if txt_content != addon_content:
        errors.append(".txt and .addon manifests have different content")

    return errors


def validate_lua_syntax(addon_dir: Path) -> list[str]:
    """Basic Lua syntax validation."""
    errors = []
    for lua_file in addon_dir.rglob("*.lua"):
        content = lua_file.read_text(encoding="utf-8", errors="replace")
        rel = lua_file.relative_to(addon_dir)

        if content.startswith("\ufeff"):
            errors.append(f"{rel}: File has UTF-8 BOM")

    return errors


def validate_file_sizes(addon_dir: Path) -> list[str]:
    """Check file sizes are reasonable."""
    errors = []
    total_size = 0
    for f in addon_dir.rglob("*"):
        if f.is_file():
            size = f.stat().st_size
            total_size += size
            if size > 500_000:
                rel = f.relative_to(addon_dir)
                errors.append(f"{rel}: {size/1024:.0f}KB (unusually large)")
    if total_size > 5_000_000:
        errors.append(f"Total size {total_size/1024/1024:.1f}MB (consider optimizing)")
    return errors


def validate_no_secrets(addon_dir: Path) -> list[str]:
    """Check for secrets or credentials."""
    errors = []
    secret_patterns = [
        r"api[_-]?key\s*=\s*['\"][^'\"]{10,}",
        r"password\s*=\s*['\"][^'\"]+",
        r"secret\s*=\s*['\"][^'\"]+",
        r"token\s*=\s*['\"][a-zA-Z0-9]{20,}",
    ]
    for f in addon_dir.rglob("*"):
        if not f.is_file() or f.suffix not in (".lua", ".xml", ".txt"):
            continue
        content = f.read_text(encoding="utf-8", errors="replace")
        rel = f.relative_to(addon_dir)
        for pattern in secret_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                errors.append(f"{rel}: Possible secret found")
    return errors


def build_file_list(addon_dir: Path) -> list[Path]:
    """Get files to include in the package."""
    files = []
    for f in addon_dir.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(addon_dir)
        excluded = any(rel.match(p) for p in EXCLUDE_PATTERNS)
        if not excluded:
            files.append(f)
    return sorted(files)


def create_package(addon_dir: Path, output_dir: Path, dry_run: bool = False) -> Path | None:
    """Create the distribution ZIP file."""
    print("=" * 60)
    print(f"  Packaging {ADDON_NAME}")
    print("=" * 60)
    print()

    all_errors = []

    for name, validator in [
        ("manifest", lambda: validate_manifest(addon_dir)),
        ("console manifest", lambda: validate_console_manifest(addon_dir)),
        ("Lua files", lambda: validate_lua_syntax(addon_dir)),
        ("file sizes", lambda: validate_file_sizes(addon_dir)),
        ("secrets scan", lambda: validate_no_secrets(addon_dir)),
    ]:
        print(f"Validating {name}...")
        errors = validator()
        all_errors.extend(errors)
        for e in errors:
            print(f"  ERROR: {e}")
        if not errors:
            print("  OK")

    print("Checking required files...")
    missing = [r for r in REQUIRED_FILES if not (addon_dir / r).exists()]
    all_errors.extend(f"Required file missing: {m}" for m in missing)
    for m in missing:
        print(f"  MISSING: {m}")
    if not missing:
        print(f"  OK ({len(REQUIRED_FILES)} files)")

    print()

    if all_errors:
        print(f"FAILED: {len(all_errors)} error(s) found")
        for e in all_errors:
            print(f"  - {e}")
        return None

    files = build_file_list(addon_dir)

    print(f"Files to package: {len(files)}")
    total_size = 0
    for f in files:
        rel = f.relative_to(addon_dir)
        size = f.stat().st_size
        total_size += size
        print(f"  {rel} ({size/1024:.1f}KB)")

    print(f"\nTotal size: {total_size/1024:.1f}KB")

    if dry_run:
        print("\n[DRY RUN] Would create ZIP but --check flag set")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_text = (addon_dir / f"{ADDON_NAME}.txt").read_text(encoding="utf-8", errors="replace")
    version_match = re.search(r"## AddOnVersion:\s*(\d+)", manifest_text)
    addon_version = version_match.group(1) if version_match else "0"

    zip_name = f"{ADDON_NAME}-v{addon_version}.zip"
    zip_path = output_dir / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            rel = f.relative_to(addon_dir)
            arcname = f"{ADDON_NAME}/{rel}"
            zf.write(f, arcname)

    sha256 = hashlib.sha256(zip_path.read_bytes()).hexdigest()

    print(f"\nPackage created: {zip_path}")
    print(f"  Size: {zip_path.stat().st_size/1024:.1f}KB")
    print(f"  SHA256: {sha256}")
    print(f"\nReady to upload to esoui.com!")

    return zip_path


def main():
    parser = argparse.ArgumentParser(description="Package ESBO addon for ESOUI distribution")
    parser.add_argument("--check", action="store_true", help="Dry-run validation only")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    if not ADDON_DIR.exists():
        print(f"ERROR: Addon directory not found: {ADDON_DIR}")
        sys.exit(1)

    result = create_package(ADDON_DIR, Path(args.output), dry_run=args.check)
    if result is None and not args.check:
        sys.exit(1)


if __name__ == "__main__":
    main()
