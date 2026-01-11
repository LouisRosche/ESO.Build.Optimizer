#!/usr/bin/env python3
"""
Documentation Refresh Workflow

This script checks for updates to technical documentation sources and
alerts when manual review is needed. It maintains a version tracking file
to detect when documentation may be stale.

Usage:
    python scripts/refresh_docs.py          # Check all sources
    python scripts/refresh_docs.py --update # Update version tracking
    python scripts/refresh_docs.py --report # Generate staleness report
"""

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

# Optional: Install httpx for actual web fetching
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs" / "technical"
VERSION_FILE = PROJECT_ROOT / "docs" / ".doc_versions.json"


@dataclass
class DocSource:
    """A documentation source to track."""
    name: str
    url: str
    doc_file: str
    check_pattern: Optional[str] = None  # Regex to extract version/date
    refresh_trigger: str = "quarterly"  # quarterly, monthly, on_release


# Documentation sources we track
DOC_SOURCES = [
    # ESO Addon API
    DocSource(
        name="ESOUI API Version",
        url="https://wiki.esoui.com/APIVersion",
        doc_file="ESO_ADDON_API.md",
        check_pattern=r"API Version (\d+)",
        refresh_trigger="on_release",
    ),
    DocSource(
        name="UESP ESO Data",
        url="https://esoapi.uesp.net/",
        doc_file="ESO_ADDON_API.md",
        check_pattern=r"v(\d+)",
        refresh_trigger="on_release",
    ),

    # FastAPI
    DocSource(
        name="FastAPI Best Practices",
        url="https://github.com/zhanymkanov/fastapi-best-practices",
        doc_file="FASTAPI_BEST_PRACTICES.md",
        refresh_trigger="quarterly",
    ),
    DocSource(
        name="FastAPI Official Docs",
        url="https://fastapi.tiangolo.com/",
        doc_file="FASTAPI_BEST_PRACTICES.md",
        refresh_trigger="on_release",
    ),

    # Frontend
    DocSource(
        name="Vite Documentation",
        url="https://vite.dev/guide/",
        doc_file="REACT_VITE_BEST_PRACTICES.md",
        refresh_trigger="on_release",
    ),
    DocSource(
        name="React Documentation",
        url="https://react.dev/",
        doc_file="REACT_VITE_BEST_PRACTICES.md",
        refresh_trigger="on_release",
    ),

    # Deployment
    DocSource(
        name="Neon Pricing/Plans",
        url="https://neon.com/docs/introduction/plans",
        doc_file="DEPLOYMENT_FREE_TIER.md",
        refresh_trigger="monthly",
    ),
    DocSource(
        name="Render Free Tier",
        url="https://render.com/docs/free",
        doc_file="DEPLOYMENT_FREE_TIER.md",
        refresh_trigger="monthly",
    ),
    DocSource(
        name="Vercel Pricing",
        url="https://vercel.com/pricing",
        doc_file="DEPLOYMENT_FREE_TIER.md",
        refresh_trigger="monthly",
    ),

    # Packaging
    DocSource(
        name="PyInstaller Documentation",
        url="https://pyinstaller.org/",
        doc_file="PYINSTALLER_PACKAGING.md",
        check_pattern=r"PyInstaller ([\d.]+)",
        refresh_trigger="on_release",
    ),
]


def load_versions() -> dict:
    """Load the version tracking file."""
    if VERSION_FILE.exists():
        return json.loads(VERSION_FILE.read_text())
    return {"sources": {}, "last_check": None}


def save_versions(data: dict) -> None:
    """Save the version tracking file."""
    VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    VERSION_FILE.write_text(json.dumps(data, indent=2))


def get_doc_last_updated(doc_file: str) -> Optional[str]:
    """Extract the 'Last Updated' date from a doc file."""
    doc_path = DOCS_DIR / doc_file
    if not doc_path.exists():
        return None

    content = doc_path.read_text()
    match = re.search(r"Last Updated[:\s]*([A-Za-z]+ \d{4})", content)
    if match:
        return match.group(1)
    return None


def check_staleness(source: DocSource, versions: dict) -> dict:
    """Check if a documentation source may be stale."""
    result = {
        "name": source.name,
        "url": source.url,
        "doc_file": source.doc_file,
        "status": "unknown",
        "message": "",
    }

    # Get doc file last updated
    doc_updated = get_doc_last_updated(source.doc_file)
    result["doc_last_updated"] = doc_updated

    # Check tracked version
    tracked = versions.get("sources", {}).get(source.name, {})
    last_checked = tracked.get("last_checked")
    result["last_checked"] = last_checked

    # Determine staleness based on refresh trigger
    now = datetime.now()

    if not last_checked:
        result["status"] = "never_checked"
        result["message"] = "Never checked - manual review recommended"
        return result

    last_check_date = datetime.fromisoformat(last_checked)
    days_since_check = (now - last_check_date).days

    if source.refresh_trigger == "monthly" and days_since_check > 30:
        result["status"] = "stale"
        result["message"] = f"Last checked {days_since_check} days ago (monthly refresh recommended)"
    elif source.refresh_trigger == "quarterly" and days_since_check > 90:
        result["status"] = "stale"
        result["message"] = f"Last checked {days_since_check} days ago (quarterly refresh recommended)"
    elif source.refresh_trigger == "on_release":
        # For release-triggered docs, we just note when last checked
        result["status"] = "ok"
        result["message"] = f"Last checked {days_since_check} days ago (check after major releases)"
    else:
        result["status"] = "ok"
        result["message"] = f"Checked {days_since_check} days ago"

    return result


def generate_report(versions: dict) -> str:
    """Generate a staleness report for all documentation sources."""
    lines = [
        "# Documentation Freshness Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Source Status",
        "",
    ]

    stale_count = 0
    for source in DOC_SOURCES:
        result = check_staleness(source, versions)

        if result["status"] == "stale":
            status_icon = "🔴"
            stale_count += 1
        elif result["status"] == "never_checked":
            status_icon = "🟡"
            stale_count += 1
        else:
            status_icon = "🟢"

        lines.append(f"### {status_icon} {result['name']}")
        lines.append(f"- **URL**: {result['url']}")
        lines.append(f"- **Doc File**: `{result['doc_file']}`")
        lines.append(f"- **Status**: {result['message']}")
        if result.get("doc_last_updated"):
            lines.append(f"- **Doc Last Updated**: {result['doc_last_updated']}")
        lines.append("")

    # Summary
    lines.insert(4, f"**{stale_count}/{len(DOC_SOURCES)} sources may need review**")
    lines.insert(5, "")

    return "\n".join(lines)


def update_check_times(versions: dict) -> dict:
    """Mark all sources as checked now."""
    now = datetime.now().isoformat()

    if "sources" not in versions:
        versions["sources"] = {}

    for source in DOC_SOURCES:
        if source.name not in versions["sources"]:
            versions["sources"][source.name] = {}
        versions["sources"][source.name]["last_checked"] = now

    versions["last_check"] = now
    return versions


def fetch_and_compare(source: DocSource) -> Optional[str]:
    """Fetch a URL and compare content hash (requires httpx)."""
    if not HAS_HTTPX:
        return None

    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            response = client.get(source.url)
            response.raise_for_status()
            content_hash = hashlib.md5(response.content).hexdigest()
            return content_hash
    except Exception as e:
        print(f"  Warning: Could not fetch {source.url}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Check documentation freshness")
    parser.add_argument("--update", action="store_true",
                        help="Mark all sources as checked")
    parser.add_argument("--report", action="store_true",
                        help="Generate staleness report")
    parser.add_argument("--fetch", action="store_true",
                        help="Fetch URLs and compare hashes (requires httpx)")

    args = parser.parse_args()

    versions = load_versions()

    if args.report:
        report = generate_report(versions)
        print(report)

        # Also save report to file
        report_path = DOCS_DIR / "FRESHNESS_REPORT.md"
        report_path.write_text(report)
        print(f"\nReport saved to: {report_path}")

    elif args.update:
        versions = update_check_times(versions)
        save_versions(versions)
        print(f"Updated check times for {len(DOC_SOURCES)} sources")
        print(f"Version file: {VERSION_FILE}")

    elif args.fetch:
        if not HAS_HTTPX:
            print("Error: httpx not installed. Run: pip install httpx")
            sys.exit(1)

        print("Fetching documentation sources...")
        for source in DOC_SOURCES:
            print(f"  Checking {source.name}...")
            content_hash = fetch_and_compare(source)
            if content_hash:
                old_hash = versions.get("sources", {}).get(source.name, {}).get("content_hash")
                if old_hash and old_hash != content_hash:
                    print(f"    ⚠️  Content changed! Manual review recommended.")
                elif not old_hash:
                    print(f"    📝 First fetch recorded.")

                if source.name not in versions.get("sources", {}):
                    versions["sources"][source.name] = {}
                versions["sources"][source.name]["content_hash"] = content_hash
                versions["sources"][source.name]["last_checked"] = datetime.now().isoformat()

        save_versions(versions)
        print("\nVersion tracking updated.")

    else:
        # Default: show status
        print("Documentation Freshness Check")
        print("=" * 40)

        stale = []
        for source in DOC_SOURCES:
            result = check_staleness(source, versions)
            if result["status"] in ("stale", "never_checked"):
                stale.append(result)

        if stale:
            print(f"\n⚠️  {len(stale)} source(s) may need review:\n")
            for item in stale:
                print(f"  - {item['name']}")
                print(f"    {item['message']}")
                print(f"    URL: {item['url']}")
                print()
        else:
            print("\n✅ All documentation sources are up to date.")

        print("\nCommands:")
        print("  --report  Generate detailed report")
        print("  --update  Mark all as checked")
        print("  --fetch   Fetch URLs and detect changes (requires httpx)")


if __name__ == "__main__":
    main()
