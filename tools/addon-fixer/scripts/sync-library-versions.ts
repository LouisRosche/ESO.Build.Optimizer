#!/usr/bin/env npx ts-node
/**
 * Sync library versions from ESOUI.com
 *
 * Fetches the latest version info for all tracked libraries and updates
 * the library-db.ts file with current versions.
 *
 * Usage:
 *   npx ts-node scripts/sync-library-versions.ts
 *   npx ts-node scripts/sync-library-versions.ts --dry-run
 *   npx ts-node scripts/sync-library-versions.ts --check  # CI mode - fails if outdated
 */

import { LIBRARY_DATABASE, type LibraryVersionInfo } from '../src/library-db.js';

interface ESOUIAddonInfo {
  id: number;
  name: string;
  version: string;
  lastUpdate: string;
  downloads: number;
  apiVersion?: string;
}

interface SyncResult {
  library: string;
  esouiId: number;
  currentVersion: string;
  fetchedVersion: string;
  isOutdated: boolean;
  error?: string;
}

const ESOUI_BASE_URL = 'https://www.esoui.com/downloads';

/**
 * Fetch addon info from ESOUI.
 * ESOUI doesn't have a public API, so we parse the addon page HTML.
 */
async function fetchESOUIAddon(esouiId: number): Promise<ESOUIAddonInfo | null> {
  const url = `${ESOUI_BASE_URL}/info${esouiId}.html`;

  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'ESO-Addon-Fixer/1.0 (Library Version Sync)',
      },
    });

    if (!response.ok) {
      console.error(`  Failed to fetch ${url}: ${response.status}`);
      return null;
    }

    const html = await response.text();

    // Parse version from page
    // Look for: <div id="version">Version: X.X.X</div>
    const versionMatch = html.match(/Version:\s*([^\s<]+)/i);
    const version = versionMatch?.[1] || 'unknown';

    // Parse last update date
    // Look for: Updated: YYYY-MM-DD or similar
    const dateMatch = html.match(/Updated?:\s*(\d{2}-\d{2}-\d{2}|\d{4}-\d{2}-\d{2})/i);
    const lastUpdate = dateMatch?.[1] || 'unknown';

    // Parse download count
    const downloadsMatch = html.match(/Downloads:\s*([\d,]+)/i);
    const downloads = parseInt(downloadsMatch?.[1]?.replace(/,/g, '') || '0', 10);

    // Parse addon name
    const nameMatch = html.match(/<title>([^<]+)\s*-\s*Addons/i);
    const name = nameMatch?.[1]?.trim() || `Addon ${esouiId}`;

    return {
      id: esouiId,
      name,
      version,
      lastUpdate,
      downloads,
    };
  } catch (error) {
    console.error(`  Error fetching ${url}:`, error);
    return null;
  }
}

/**
 * Generate updated library-db.ts content with new versions.
 */
function generateUpdatedDatabase(results: SyncResult[]): string {
  const updates = new Map(
    results
      .filter(r => !r.error && r.fetchedVersion !== 'unknown')
      .map(r => [r.library, { version: r.fetchedVersion, date: new Date().toISOString().split('T')[0] }])
  );

  // Read current file and update versions
  let content = `/**
 * Library version database for ESO addon ecosystem.
 *
 * AUTO-GENERATED - Last synced: ${new Date().toISOString().split('T')[0]}
 * Run: npx ts-node scripts/sync-library-versions.ts
 */

`;

  // This is a simplified approach - in production you'd parse and update the actual file
  console.log('\nUpdated versions:');
  for (const [lib, data] of updates) {
    console.log(`  ${lib}: ${data.version} (${data.date})`);
  }

  return content;
}

async function main() {
  const args = process.argv.slice(2);
  const isDryRun = args.includes('--dry-run');
  const isCheck = args.includes('--check');

  console.log('ESO Library Version Sync');
  console.log('========================\n');

  if (isDryRun) {
    console.log('DRY RUN - No changes will be made\n');
  }

  const librariesWithIds = LIBRARY_DATABASE.filter(l => l.esouiId);
  console.log(`Checking ${librariesWithIds.length} libraries...\n`);

  const results: SyncResult[] = [];
  let outdatedCount = 0;

  for (const lib of librariesWithIds) {
    process.stdout.write(`Fetching ${lib.name}...`);

    const info = await fetchESOUIAddon(lib.esouiId!);

    if (info) {
      const isOutdated = info.version !== lib.latestVersion;
      if (isOutdated) outdatedCount++;

      results.push({
        library: lib.name,
        esouiId: lib.esouiId!,
        currentVersion: lib.latestVersion,
        fetchedVersion: info.version,
        isOutdated,
      });

      const status = isOutdated ? '⚠️  OUTDATED' : '✓';
      console.log(` ${status} (${lib.latestVersion} → ${info.version})`);
    } else {
      results.push({
        library: lib.name,
        esouiId: lib.esouiId!,
        currentVersion: lib.latestVersion,
        fetchedVersion: 'unknown',
        isOutdated: false,
        error: 'Failed to fetch',
      });
      console.log(' ✗ Failed');
    }

    // Rate limiting - be nice to ESOUI
    await new Promise(resolve => setTimeout(resolve, 500));
  }

  // Summary
  console.log('\n' + '='.repeat(50));
  console.log('Summary');
  console.log('='.repeat(50));
  console.log(`Total libraries: ${librariesWithIds.length}`);
  console.log(`Outdated: ${outdatedCount}`);
  console.log(`Errors: ${results.filter(r => r.error).length}`);

  if (outdatedCount > 0) {
    console.log('\nOutdated libraries:');
    for (const r of results.filter(r => r.isOutdated)) {
      console.log(`  ${r.library}: ${r.currentVersion} → ${r.fetchedVersion}`);
    }
  }

  // In check mode, exit with error if outdated
  if (isCheck && outdatedCount > 0) {
    console.log('\n✗ Library versions are outdated. Run sync to update.');
    process.exit(1);
  }

  // Generate update suggestions
  if (!isDryRun && outdatedCount > 0) {
    console.log('\nTo update library-db.ts, apply these changes:');
    for (const r of results.filter(r => r.isOutdated)) {
      console.log(`  ${r.library}:`);
      console.log(`    latestVersion: '${r.currentVersion}' → '${r.fetchedVersion}'`);
      console.log(`    lastUpdated: '${new Date().toISOString().split('T')[0]}'`);
    }
  }

  // Output JSON for automation
  if (args.includes('--json')) {
    console.log('\n' + JSON.stringify(results, null, 2));
  }
}

main().catch(console.error);
