/**
 * ESO addon manifest (.txt) file parser and fixer.
 *
 * Handles parsing of manifest directives, dependency resolution,
 * and generation of fixed manifest content.
 */

import { readFile, writeFile } from 'node:fs/promises';
import type {
  ManifestData,
  DependencyInfo,
  Issue,
  SourceRange,
  FileAnalysisResult,
  FileFixResult,
  FixChange,
} from './types.js';
import { CURRENT_LIVE_API, CURRENT_PTS_API } from './types.js';
import { LIBRARY_MIGRATIONS } from './migrations.js';

// ============================================================================
// Constants
// ============================================================================

const DIRECTIVE_PATTERN = /^##\s*(\w+):\s*(.*)$/;
const FILE_PATTERN = /^([^#\s].*\.(lua|xml))$/i;
const DEPENDENCY_PATTERN = /(\w[\w-]*(?:>=\d+)?)/g;
const MAX_LINE_LENGTH = 301; // ESO limit in bytes

// ============================================================================
// Manifest Parser
// ============================================================================

export async function parseManifest(manifestPath: string): Promise<ManifestData> {
  let content: string;
  let encoding: 'utf-8' | 'utf-8-bom' | 'windows-1252' | 'unknown' = 'utf-8';

  try {
    const buffer = await readFile(manifestPath);

    // Check for UTF-8 BOM
    if (buffer[0] === 0xEF && buffer[1] === 0xBB && buffer[2] === 0xBF) {
      encoding = 'utf-8-bom';
      content = buffer.toString('utf-8').substring(1); // Skip BOM
    } else {
      content = buffer.toString('utf-8');
    }
  } catch {
    try {
      content = await readFile(manifestPath, 'latin1');
      encoding = 'windows-1252';
    } catch (e) {
      throw new Error(`Failed to read manifest: ${e}`);
    }
  }

  // Detect line endings
  const hasCRLF = content.includes('\r\n');
  const hasLF = content.includes('\n') && !hasCRLF;
  const lineEnding: 'crlf' | 'lf' | 'mixed' =
    hasCRLF && hasLF ? 'mixed' : hasCRLF ? 'crlf' : 'lf';

  // Normalize line endings for parsing
  const normalizedContent = content.replace(/\r\n/g, '\n');
  const lines = normalizedContent.split('\n');

  const data: ManifestData = {
    path: manifestPath,
    title: '',
    apiVersions: [],
    dependsOn: [],
    optionalDependsOn: [],
    savedVariables: [],
    isLibrary: false,
    files: [],
    rawContent: content,
    encoding,
    lineEnding,
  };

  const apiVersions: number[] = [];
  const dependsOn: DependencyInfo[] = [];
  const optionalDependsOn: DependencyInfo[] = [];
  const savedVariables: string[] = [];
  const files: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();

    // Skip empty lines and pure comments
    if (!trimmed || trimmed === '#' || trimmed.startsWith('# ')) {
      continue;
    }

    // Parse directive
    const directiveMatch = DIRECTIVE_PATTERN.exec(trimmed);
    if (directiveMatch) {
      const [, key, value] = directiveMatch;
      const keyLower = key?.toLowerCase() ?? '';
      const trimmedValue = value?.trim() ?? '';

      switch (keyLower) {
        case 'title':
          (data as { title: string }).title = trimmedValue;
          break;

        case 'apiversion':
          for (const v of trimmedValue.split(/\s+/)) {
            const parsed = parseInt(v, 10);
            if (!isNaN(parsed)) {
              apiVersions.push(parsed);
            }
          }
          break;

        case 'addonversion':
          const addonVersion = parseInt(trimmedValue, 10);
          if (!isNaN(addonVersion)) {
            (data as { addonVersion: number }).addonVersion = addonVersion;
          }
          break;

        case 'version':
          (data as { version: string }).version = trimmedValue;
          break;

        case 'author':
          (data as { author: string }).author = trimmedValue;
          break;

        case 'description':
          (data as { description: string }).description = trimmedValue;
          break;

        case 'dependson':
          dependsOn.push(...parseDependencies(trimmedValue));
          break;

        case 'optionaldependson':
          optionalDependsOn.push(...parseDependencies(trimmedValue));
          break;

        case 'savedvariables':
          savedVariables.push(...trimmedValue.split(/\s+/).filter(Boolean));
          break;

        case 'islibrary':
          (data as { isLibrary: boolean }).isLibrary = trimmedValue.toLowerCase() === 'true';
          break;
      }
      continue;
    }

    // Parse file reference
    const fileMatch = FILE_PATTERN.exec(trimmed);
    if (fileMatch) {
      files.push(fileMatch[1] ?? '');
    }
  }

  return {
    ...data,
    apiVersions,
    dependsOn,
    optionalDependsOn,
    savedVariables,
    files,
  };
}

function parseDependencies(value: string): DependencyInfo[] {
  const deps: DependencyInfo[] = [];
  const matches = value.match(DEPENDENCY_PATTERN);

  if (matches) {
    for (const match of matches) {
      const versionMatch = /^(.+?)>=(\d+)$/.exec(match);
      if (versionMatch) {
        deps.push({
          name: versionMatch[1] ?? '',
          minVersion: parseInt(versionMatch[2] ?? '0', 10),
          raw: match,
        });
      } else {
        deps.push({ name: match, raw: match });
      }
    }
  }

  return deps;
}

// ============================================================================
// Manifest Analyzer
// ============================================================================

export async function analyzeManifest(manifestPath: string): Promise<FileAnalysisResult> {
  const data = await parseManifest(manifestPath);
  const issues: Issue[] = [];
  let issueId = 0;

  const createIssue = (params: Omit<Issue, 'id' | 'filePath'>): Issue => ({
    id: `manifest-${++issueId}`,
    filePath: manifestPath,
    ...params,
  });

  // Check encoding
  if (data.encoding === 'utf-8-bom') {
    issues.push(createIssue({
      category: 'encoding',
      severity: 'warning',
      message: 'File has UTF-8 BOM (should be UTF-8 without BOM)',
      location: { start: { line: 1, column: 0, offset: 0 }, end: { line: 1, column: 0, offset: 0 } },
      oldCode: '',
      suggestedFix: 'Remove BOM',
      autoFixable: true,
      confidence: 1.0,
    }));
  } else if (data.encoding === 'windows-1252') {
    issues.push(createIssue({
      category: 'encoding',
      severity: 'warning',
      message: 'File uses Windows-1252 encoding (should be UTF-8)',
      location: { start: { line: 1, column: 0, offset: 0 }, end: { line: 1, column: 0, offset: 0 } },
      oldCode: '',
      suggestedFix: 'Convert to UTF-8',
      autoFixable: true,
      confidence: 1.0,
    }));
  }

  // Check line endings
  if (data.lineEnding !== 'crlf') {
    issues.push(createIssue({
      category: 'encoding',
      severity: 'info',
      message: `Line endings are ${data.lineEnding.toUpperCase()} (ESO prefers CRLF)`,
      location: { start: { line: 1, column: 0, offset: 0 }, end: { line: 1, column: 0, offset: 0 } },
      oldCode: '',
      suggestedFix: 'Convert to CRLF',
      autoFixable: true,
      confidence: 0.8,
    }));
  }

  // Check required directives
  if (!data.title) {
    issues.push(createIssue({
      category: 'api_version',
      severity: 'error',
      message: 'Missing required directive: ## Title:',
      location: { start: { line: 1, column: 0, offset: 0 }, end: { line: 1, column: 0, offset: 0 } },
      oldCode: '',
      autoFixable: false,
      confidence: 1.0,
    }));
  }

  if (data.apiVersions.length === 0) {
    issues.push(createIssue({
      category: 'api_version',
      severity: 'error',
      message: 'Missing required directive: ## APIVersion:',
      location: { start: { line: 1, column: 0, offset: 0 }, end: { line: 1, column: 0, offset: 0 } },
      oldCode: '',
      autoFixable: false,
      confidence: 1.0,
    }));
  }

  // Check API version
  const maxApiVersion = Math.max(...data.apiVersions, 0);
  if (maxApiVersion > 0 && maxApiVersion < CURRENT_LIVE_API) {
    issues.push(createIssue({
      category: 'api_version',
      severity: 'warning',
      message: `Outdated API version: ${maxApiVersion} (current: ${CURRENT_LIVE_API})`,
      location: { start: { line: 1, column: 0, offset: 0 }, end: { line: 1, column: 0, offset: 0 } },
      oldCode: `## APIVersion: ${data.apiVersions.join(' ')}`,
      suggestedFix: `## APIVersion: ${CURRENT_LIVE_API - 1} ${CURRENT_LIVE_API}`,
      autoFixable: true,
      confidence: 1.0,
    }));
  }

  // Check for LibStub dependency
  const hasLibStub = data.dependsOn.some((d) => d.name === 'LibStub');
  if (hasLibStub) {
    issues.push(createIssue({
      category: 'libstub',
      severity: 'warning',
      message: 'LibStub is deprecated and should be removed from dependencies',
      location: { start: { line: 1, column: 0, offset: 0 }, end: { line: 1, column: 0, offset: 0 } },
      oldCode: 'LibStub',
      suggestedFix: 'Remove LibStub from DependsOn',
      autoFixable: true,
      confidence: 1.0,
    }));
  }

  return {
    filePath: manifestPath,
    fileType: 'manifest',
    issues,
    metrics: {
      lineCount: data.rawContent.split('\n').length,
      functionCount: 0,
      eventRegistrations: 0,
      libStubUsages: hasLibStub ? 1 : 0,
      deprecatedCalls: 0,
    },
    parseErrors: [],
  };
}

// ============================================================================
// Manifest Fixer
// ============================================================================

export async function fixManifest(
  manifestPath: string,
  dryRun: boolean = false
): Promise<FileFixResult> {
  const data = await parseManifest(manifestPath);
  const changes: FixChange[] = [];
  const errors: string[] = [];

  let content = data.rawContent;
  let modified = false;

  // Fix API version
  const maxApiVersion = Math.max(...data.apiVersions, 0);
  if (maxApiVersion > 0 && maxApiVersion < CURRENT_LIVE_API) {
    const oldPattern = new RegExp(`^(##\\s*APIVersion:\\s*)${data.apiVersions.join('\\s+')}`, 'm');
    const newValue = `$1${CURRENT_LIVE_API - 1} ${CURRENT_LIVE_API}`;

    if (oldPattern.test(content)) {
      content = content.replace(oldPattern, newValue);
      changes.push({
        location: { start: { line: 0, column: 0, offset: 0 }, end: { line: 0, column: 0, offset: 0 } },
        oldCode: `## APIVersion: ${data.apiVersions.join(' ')}`,
        newCode: `## APIVersion: ${CURRENT_LIVE_API - 1} ${CURRENT_LIVE_API}`,
        reason: 'Update to current API version',
        confidence: 1.0,
      });
      modified = true;
    }
  }

  // Remove LibStub from dependencies
  const libStubPattern = /^(##\s*DependsOn:\s*)(.*)LibStub\s*/m;
  if (libStubPattern.test(content)) {
    content = content.replace(libStubPattern, (match, prefix, before) => {
      const cleaned = `${prefix}${before}`.replace(/\s+/g, ' ').trim();
      return cleaned;
    });
    changes.push({
      location: { start: { line: 0, column: 0, offset: 0 }, end: { line: 0, column: 0, offset: 0 } },
      oldCode: 'LibStub',
      newCode: '',
      reason: 'Remove deprecated LibStub dependency',
      confidence: 1.0,
    });
    modified = true;
  }

  // Fix encoding (remove BOM, ensure UTF-8)
  if (data.encoding === 'utf-8-bom') {
    content = content.replace(/^\uFEFF/, '');
    changes.push({
      location: { start: { line: 1, column: 0, offset: 0 }, end: { line: 1, column: 0, offset: 0 } },
      oldCode: 'UTF-8 BOM',
      newCode: '',
      reason: 'Remove UTF-8 BOM',
      confidence: 1.0,
    });
    modified = true;
  }

  // Ensure CRLF line endings
  if (!content.includes('\r\n') && content.includes('\n')) {
    content = content.replace(/\n/g, '\r\n');
    changes.push({
      location: { start: { line: 0, column: 0, offset: 0 }, end: { line: 0, column: 0, offset: 0 } },
      oldCode: 'LF',
      newCode: 'CRLF',
      reason: 'Convert to CRLF line endings',
      confidence: 0.9,
    });
    modified = true;
  }

  // Write file if not dry run
  if (!dryRun && modified) {
    try {
      await writeFile(manifestPath, content, 'utf-8');
    } catch (e) {
      errors.push(`Failed to write manifest: ${e}`);
    }
  }

  return {
    filePath: manifestPath,
    fileType: 'manifest',
    changes,
    errors,
    wasModified: modified && !dryRun,
  };
}
