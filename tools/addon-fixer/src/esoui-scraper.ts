/**
 * ESOUI.com Addon Scraper
 *
 * Automatically fetches addon information, changelogs, and version history
 * from ESOUI.com to keep our compatibility database current.
 */

export interface AddonVersionHistory {
  readonly version: string;
  readonly date: string;
  readonly changelog: string[];
  readonly apiVersion?: number;
}

export interface ScrapedAddonInfo {
  readonly esouiId: number;
  readonly name: string;
  readonly author: string;
  readonly currentVersion: string;
  readonly lastUpdated: string;
  readonly downloads: number;
  readonly favorites: number;
  readonly apiVersion?: number;
  readonly description: string;
  readonly dependencies: string[];
  readonly optionalDeps: string[];
  readonly changelog: string;
  readonly versionHistory: AddonVersionHistory[];
  readonly categories: string[];
  readonly scrapedAt: string;
}

export interface ChangelogAnalysis {
  readonly mentionsApiChange: boolean;
  readonly mentionsLibrary: string[];
  readonly mentionsBugFix: boolean;
  readonly mentionsNewFeature: boolean;
  readonly mentionsBreakingChange: boolean;
  readonly keywords: string[];
}

const ESOUI_BASE = 'https://www.esoui.com/downloads';
const USER_AGENT = 'ESO-Addon-Fixer/1.0 (Addon Compatibility Tracker)';

/**
 * Fetch and parse addon info from ESOUI
 */
export async function scrapeAddonInfo(esouiId: number): Promise<ScrapedAddonInfo | null> {
  const url = `${ESOUI_BASE}/info${esouiId}.html`;

  try {
    const response = await fetch(url, {
      headers: { 'User-Agent': USER_AGENT },
    });

    if (!response.ok) {
      return null;
    }

    const html = await response.text();
    return parseAddonPage(esouiId, html);
  } catch (error) {
    console.error(`Failed to scrape addon ${esouiId}:`, error);
    return null;
  }
}

/**
 * Parse addon page HTML
 */
function parseAddonPage(esouiId: number, html: string): ScrapedAddonInfo {
  // Extract basic info
  const nameMatch = html.match(/<div class="title"[^>]*>([^<]+)</i) ||
                    html.match(/<title>([^-<]+)/i);
  const name = nameMatch?.[1]?.trim() || `Addon ${esouiId}`;

  const authorMatch = html.match(/Author:\s*<[^>]+>([^<]+)</i) ||
                      html.match(/by\s+<a[^>]+>([^<]+)</i);
  const author = authorMatch?.[1]?.trim() || 'Unknown';

  const versionMatch = html.match(/Version:\s*([^\s<]+)/i);
  const currentVersion = versionMatch?.[1] || 'unknown';

  const dateMatch = html.match(/Updated?:\s*(\d{2}-\d{2}-\d{2}|\d{4}-\d{2}-\d{2})/i);
  const lastUpdated = dateMatch?.[1] || 'unknown';

  const downloadsMatch = html.match(/Downloads:\s*([\d,]+)/i);
  const downloads = parseInt(downloadsMatch?.[1]?.replace(/,/g, '') || '0', 10);

  const favoritesMatch = html.match(/Favorites:\s*([\d,]+)/i);
  const favorites = parseInt(favoritesMatch?.[1]?.replace(/,/g, '') || '0', 10);

  const apiMatch = html.match(/API\s*Version:\s*(\d+)/i) ||
                   html.match(/APIVersion:\s*(\d+)/i);
  const apiVersion = apiMatch ? parseInt(apiMatch[1], 10) : undefined;

  // Extract description
  const descMatch = html.match(/<div class="description"[^>]*>([\s\S]*?)<\/div>/i);
  const description = descMatch?.[1]?.replace(/<[^>]+>/g, ' ').trim() || '';

  // Extract dependencies
  const dependencies = extractDependencies(html, 'DependsOn') ||
                       extractDependencies(html, 'Dependencies');
  const optionalDeps = extractDependencies(html, 'OptionalDependsOn') ||
                       extractDependencies(html, 'Optional');

  // Extract changelog
  const changelogMatch = html.match(/<div class="changelog"[^>]*>([\s\S]*?)<\/div>/i) ||
                         html.match(/Changelog:?([\s\S]*?)(?:<\/div>|<div class)/i);
  const changelog = changelogMatch?.[1]?.replace(/<[^>]+>/g, '\n').trim() || '';

  // Extract version history
  const versionHistory = extractVersionHistory(html);

  // Extract categories
  const categories = extractCategories(html);

  return {
    esouiId,
    name,
    author,
    currentVersion,
    lastUpdated,
    downloads,
    favorites,
    apiVersion,
    description: description.slice(0, 500),
    dependencies,
    optionalDeps,
    changelog,
    versionHistory,
    categories,
    scrapedAt: new Date().toISOString(),
  };
}

function extractDependencies(html: string, keyword: string): string[] {
  const pattern = new RegExp(`${keyword}[:\\s]*([^<\\n]+)`, 'i');
  const match = html.match(pattern);
  if (!match) return [];

  return match[1]
    .split(/[,\s]+/)
    .map(d => d.trim())
    .filter(d => d && !d.startsWith('##'));
}

function extractVersionHistory(html: string): AddonVersionHistory[] {
  const history: AddonVersionHistory[] = [];

  // Look for version history section
  const historyMatch = html.match(/Version History:?([\s\S]*?)(?:<\/div>|<div class)/i);
  if (!historyMatch) return history;

  // Parse individual versions
  const versionPattern = /v?(\d+[\d.]*)\s*[-–]\s*(\d{2,4}[-/]\d{2}[-/]\d{2,4})[:\s]*([\s\S]*?)(?=v?\d+[\d.]*\s*[-–]|$)/gi;
  let match;

  while ((match = versionPattern.exec(historyMatch[1])) !== null) {
    const changelog = match[3]
      .replace(/<[^>]+>/g, '\n')
      .split('\n')
      .map(l => l.trim())
      .filter(l => l);

    history.push({
      version: match[1],
      date: match[2],
      changelog,
    });
  }

  return history.slice(0, 10); // Limit to last 10 versions
}

function extractCategories(html: string): string[] {
  const categories: string[] = [];

  // Look for category links
  const catPattern = /category=(\w+)/gi;
  let match;
  while ((match = catPattern.exec(html)) !== null) {
    if (!categories.includes(match[1])) {
      categories.push(match[1]);
    }
  }

  return categories;
}

/**
 * Analyze changelog for important information
 */
export function analyzeChangelog(changelog: string): ChangelogAnalysis {
  const lower = changelog.toLowerCase();

  const apiKeywords = ['api', 'apiversion', 'update', 'patch', 'compatibility'];
  const libraryKeywords = ['libaddonmenu', 'libstub', 'libfilters', 'libasync', 'libgps', 'lib'];
  const bugKeywords = ['fix', 'bug', 'issue', 'crash', 'error', 'broken'];
  const featureKeywords = ['add', 'new', 'feature', 'support', 'implement'];
  const breakingKeywords = ['breaking', 'removed', 'deprecated', 'incompatible', 'require'];

  const mentionedLibraries = libraryKeywords.filter(lib =>
    lower.includes(lib.toLowerCase())
  );

  const foundKeywords = [
    ...apiKeywords.filter(k => lower.includes(k)),
    ...bugKeywords.filter(k => lower.includes(k)),
    ...featureKeywords.filter(k => lower.includes(k)),
    ...breakingKeywords.filter(k => lower.includes(k)),
  ];

  return {
    mentionsApiChange: apiKeywords.some(k => lower.includes(k)),
    mentionsLibrary: mentionedLibraries,
    mentionsBugFix: bugKeywords.some(k => lower.includes(k)),
    mentionsNewFeature: featureKeywords.some(k => lower.includes(k)),
    mentionsBreakingChange: breakingKeywords.some(k => lower.includes(k)),
    keywords: [...new Set(foundKeywords)],
  };
}

/**
 * Scrape multiple addons with rate limiting
 */
export async function scrapeMultipleAddons(
  esouiIds: number[],
  delayMs: number = 500,
  onProgress?: (current: number, total: number, addon: ScrapedAddonInfo | null) => void
): Promise<Map<number, ScrapedAddonInfo>> {
  const results = new Map<number, ScrapedAddonInfo>();

  for (let i = 0; i < esouiIds.length; i++) {
    const id = esouiIds[i];
    const info = await scrapeAddonInfo(id);

    if (info) {
      results.set(id, info);
    }

    onProgress?.(i + 1, esouiIds.length, info);

    // Rate limiting
    if (i < esouiIds.length - 1) {
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
  }

  return results;
}

/**
 * Check for updates compared to known versions
 */
export interface UpdateCheck {
  readonly esouiId: number;
  readonly name: string;
  readonly knownVersion: string;
  readonly currentVersion: string;
  readonly hasUpdate: boolean;
  readonly changelog?: string;
  readonly changelogAnalysis?: ChangelogAnalysis;
}

export async function checkForUpdates(
  addons: Array<{ esouiId: number; name: string; knownVersion: string }>,
  delayMs: number = 500
): Promise<UpdateCheck[]> {
  const results: UpdateCheck[] = [];

  for (let i = 0; i < addons.length; i++) {
    const addon = addons[i];
    const info = await scrapeAddonInfo(addon.esouiId);

    if (info) {
      const hasUpdate = info.currentVersion !== addon.knownVersion;
      results.push({
        esouiId: addon.esouiId,
        name: addon.name,
        knownVersion: addon.knownVersion,
        currentVersion: info.currentVersion,
        hasUpdate,
        changelog: hasUpdate ? info.changelog : undefined,
        changelogAnalysis: hasUpdate ? analyzeChangelog(info.changelog) : undefined,
      });
    } else {
      results.push({
        esouiId: addon.esouiId,
        name: addon.name,
        knownVersion: addon.knownVersion,
        currentVersion: 'unknown',
        hasUpdate: false,
      });
    }

    // Rate limiting
    if (i < addons.length - 1) {
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
  }

  return results;
}

/**
 * Generate update report
 */
export function generateUpdateReport(updates: UpdateCheck[]): string {
  const lines: string[] = [
    '# Addon Update Report',
    `Generated: ${new Date().toISOString()}`,
    '',
  ];

  const withUpdates = updates.filter(u => u.hasUpdate);
  const noUpdates = updates.filter(u => !u.hasUpdate && u.currentVersion !== 'unknown');
  const failed = updates.filter(u => u.currentVersion === 'unknown');

  lines.push(`## Summary`);
  lines.push(`- Total checked: ${updates.length}`);
  lines.push(`- Updates available: ${withUpdates.length}`);
  lines.push(`- Up to date: ${noUpdates.length}`);
  lines.push(`- Failed to check: ${failed.length}`);
  lines.push('');

  if (withUpdates.length > 0) {
    lines.push('## Updates Available');
    lines.push('');

    for (const update of withUpdates) {
      lines.push(`### ${update.name}`);
      lines.push(`- ESOUI: https://www.esoui.com/downloads/info${update.esouiId}`);
      lines.push(`- Version: ${update.knownVersion} → ${update.currentVersion}`);

      if (update.changelogAnalysis) {
        const analysis = update.changelogAnalysis;
        if (analysis.mentionsBreakingChange) {
          lines.push(`- ⚠️ **Breaking changes mentioned**`);
        }
        if (analysis.mentionsApiChange) {
          lines.push(`- 🔄 API-related changes`);
        }
        if (analysis.mentionsLibrary.length > 0) {
          lines.push(`- 📚 Libraries: ${analysis.mentionsLibrary.join(', ')}`);
        }
      }

      lines.push('');
    }
  }

  return lines.join('\n');
}
