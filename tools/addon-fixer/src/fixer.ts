/**
 * Main addon fixer orchestrator.
 *
 * Coordinates analysis and fixing across all file types:
 * - Manifest files (.txt)
 * - Lua source files (.lua)
 * - XML UI files (.xml)
 */

import { readdir, stat, mkdir, copyFile, rm, writeFile as fsWriteFile, readFile as fsReadFile } from 'node:fs/promises';
import { join, basename, dirname, extname } from 'node:path';
import { createWriteStream } from 'node:fs';
import * as archiver from 'archiver';

import type {
  FixerConfig,
  AddonAnalysisResult,
  AddonFixResult,
  FileAnalysisResult,
  FileFixResult,
  AnalysisSummary,
  IssueSeverity,
  IssueCategory,
  Issue,
  FixChange,
} from './types.js';
import { DEFAULT_CONFIG } from './types.js';
import { LuaAnalyzer } from './lua-analyzer.js';
import { LuaTransformer } from './lua-transformer.js';
import { parseManifest, analyzeManifest, fixManifest } from './manifest-parser.js';
import { loadMigrations, getAddonRecommendation, type MigrationDatabase } from './migration-loader.js';

// ============================================================================
// Addon Fixer
// ============================================================================

export class AddonFixer {
  private readonly config: FixerConfig;
  private luaAnalyzer: LuaAnalyzer | null = null;
  private luaTransformer: LuaTransformer | null = null;
  private migrations: MigrationDatabase | null = null;

  constructor(config: Partial<FixerConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  private async initialize(): Promise<void> {
    if (!this.migrations) {
      this.migrations = await loadMigrations();
    }
    if (!this.luaAnalyzer) {
      this.luaAnalyzer = new LuaAnalyzer(this.config.confidenceThreshold);
    }
    if (!this.luaTransformer) {
      this.luaTransformer = new LuaTransformer();
      await this.luaTransformer.initialize();
    }
  }

  // ============================================================================
  // Analysis
  // ============================================================================

  async analyze(addonPath: string): Promise<AddonAnalysisResult> {
    await this.initialize();

    const addonName = basename(addonPath);
    const fileResults: FileAnalysisResult[] = [];
    const warnings: string[] = [];

    // Check for replacement recommendations
    const recommendation = getAddonRecommendation(this.migrations!, addonName);
    if (recommendation) {
      warnings.push(...recommendation.recommendations);
      if (!recommendation.shouldAttemptFix) {
        warnings.push(`This addon (${addonName}) is not recommended for automated repair.`);
      }
    }

    // Find manifest
    const manifestPath = join(addonPath, `${addonName}.txt`);
    let manifestData;

    try {
      await stat(manifestPath);
      const manifestResult = await analyzeManifest(manifestPath);
      fileResults.push(manifestResult);
      manifestData = await parseManifest(manifestPath);
    } catch {
      warnings.push(`Missing manifest file: ${addonName}.txt`);
    }

    // Find all Lua and XML files
    const files = await this.findFiles(addonPath);

    // Analyze Lua files
    for (const file of files.lua) {
      const result = await this.luaAnalyzer!.analyzeFile(file);
      fileResults.push(result);
    }

    // Analyze XML files
    for (const file of files.xml) {
      const result = await this.analyzeXmlFile(file);
      fileResults.push(result);
    }

    // Calculate summary
    const summary = this.calculateSummary(fileResults);

    return {
      addonPath,
      addonName,
      manifestData,
      fileResults,
      summary,
    };
  }

  // ============================================================================
  // Fixing
  // ============================================================================

  async fix(addonPath: string, outputPath?: string): Promise<AddonFixResult> {
    await this.initialize();

    const addonName = basename(addonPath);
    const fileResults: FileFixResult[] = [];
    const errors: string[] = [];
    const warnings: string[] = [];
    const recommendations: string[] = [];
    let backupPath: string | undefined;
    let packagePath: string | undefined;
    let totalChanges = 0;

    // Check for replacement recommendations
    const recommendation = getAddonRecommendation(this.migrations!, addonName);
    if (recommendation) {
      recommendations.push(...recommendation.recommendations);
    }

    // Create backup if enabled
    if (this.config.createBackup && !this.config.dryRun) {
      try {
        backupPath = await this.createBackup(addonPath);
      } catch (e) {
        warnings.push(`Failed to create backup: ${e}`);
      }
    }

    try {
      // Fix manifest
      const manifestPath = join(addonPath, `${addonName}.txt`);
      try {
        await stat(manifestPath);
        const manifestResult = await fixManifest(manifestPath, this.config.dryRun);
        fileResults.push(manifestResult);
        totalChanges += manifestResult.changes.length;
      } catch {
        warnings.push('Manifest file not found');
      }

      // Find all files
      const files = await this.findFiles(addonPath);

      // Fix Lua files
      for (const file of files.lua) {
        const result = await this.luaTransformer!.transformFile(
          file,
          {
            fixLibStub: this.config.fixLibStub,
            fixDeprecatedFunctions: this.config.fixDeprecatedFunctions,
            fixFontPaths: this.config.fixFontPaths,
            fixPatterns: true,
            confidenceThreshold: this.config.confidenceThreshold,
          },
          this.config.dryRun
        );
        fileResults.push(result);
        totalChanges += result.changes.length;
        errors.push(...result.errors);
      }

      // Fix XML files
      if (this.config.fixXmlIssues) {
        for (const file of files.xml) {
          const result = await this.fixXmlFile(file);
          fileResults.push(result);
          totalChanges += result.changes.length;
          errors.push(...result.errors);
        }
      }

      // Package if output path specified
      if (outputPath && !this.config.dryRun) {
        try {
          packagePath = await this.packageAddon(addonPath, outputPath);
        } catch (e) {
          errors.push(`Failed to package addon: ${e}`);
        }
      }
    } catch (e) {
      errors.push(`Error during fixing: ${e}`);

      // Restore from backup on failure
      if (backupPath && !this.config.dryRun) {
        try {
          await this.restoreBackup(backupPath, addonPath);
          warnings.push('Restored from backup due to errors');
        } catch (restoreError) {
          errors.push(`Failed to restore backup: ${restoreError}`);
        }
      }
    }

    return {
      addonPath,
      addonName,
      success: errors.length === 0,
      fileResults,
      backupPath,
      packagePath,
      totalChanges,
      errors,
      warnings,
      recommendations,
    };
  }

  // ============================================================================
  // File Discovery
  // ============================================================================

  private async findFiles(dirPath: string): Promise<{ lua: string[]; xml: string[] }> {
    const lua: string[] = [];
    const xml: string[] = [];

    const processDir = async (dir: string): Promise<void> => {
      const entries = await readdir(dir, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = join(dir, entry.name);

        if (entry.isDirectory()) {
          // Skip backup directories
          if (entry.name.includes('_backup_')) continue;
          await processDir(fullPath);
        } else if (entry.isFile()) {
          const ext = extname(entry.name).toLowerCase();
          if (ext === '.lua') {
            lua.push(fullPath);
          } else if (ext === '.xml') {
            xml.push(fullPath);
          }
        }
      }
    };

    await processDir(dirPath);
    return { lua, xml };
  }

  // ============================================================================
  // XML File Analysis/Fixing
  // ============================================================================

  private async analyzeXmlFile(filePath: string): Promise<FileAnalysisResult> {
    let content: string;

    try {
      content = await fsReadFile(filePath, 'utf-8');
    } catch {
      return {
        filePath,
        fileType: 'xml',
        issues: [],
        metrics: { lineCount: 0, functionCount: 0, eventRegistrations: 0, libStubUsages: 0, deprecatedCalls: 0 },
        parseErrors: [{ message: 'Failed to read file', recoverable: false }],
      };
    }

    const issues: Issue[] = [];
    let issueId = 0;

    // Check for font paths
    const fontPattern = /font\s*=\s*["']([^"']+)\.(ttf|otf)(\|[^"']*)?["']/gi;
    let match;

    while ((match = fontPattern.exec(content)) !== null) {
      const lineNum = content.substring(0, match.index).split('\n').length;

      issues.push({
        id: `xml-${++issueId}`,
        filePath,
        category: 'font_path',
        severity: 'warning',
        message: 'Font path uses old TTF/OTF format',
        location: {
          start: { line: lineNum, column: 0, offset: match.index },
          end: { line: lineNum, column: match[0]?.length ?? 0, offset: match.index + (match[0]?.length ?? 0) },
        },
        oldCode: match[0] ?? '',
        suggestedFix: match[0]?.replace(/\.(ttf|otf)/gi, '.slug'),
        autoFixable: true,
        confidence: 0.95,
      });
    }

    // Check for deprecated event handlers
    for (const evt of this.migrations?.eventMigrations ?? []) {
      const eventPattern = new RegExp(`On${evt.oldName.replace('EVENT_', '')}`, 'gi');
      let evtMatch;

      while ((evtMatch = eventPattern.exec(content)) !== null) {
        const lineNum = content.substring(0, evtMatch.index).split('\n').length;

        issues.push({
          id: `xml-${++issueId}`,
          filePath,
          category: 'event_constant',
          severity: 'warning',
          message: `Deprecated event handler: ${evtMatch[0]}`,
          location: {
            start: { line: lineNum, column: 0, offset: evtMatch.index },
            end: { line: lineNum, column: evtMatch[0].length, offset: evtMatch.index + evtMatch[0].length },
          },
          oldCode: evtMatch[0],
          suggestedFix: evt.replacementEvent ? `On${evt.replacementEvent.replace('EVENT_', '')}` : undefined,
          autoFixable: !!evt.replacementEvent,
          confidence: 0.8,
        });
      }
    }

    return {
      filePath,
      fileType: 'xml',
      issues,
      metrics: {
        lineCount: content.split('\n').length,
        functionCount: 0,
        eventRegistrations: 0,
        libStubUsages: 0,
        deprecatedCalls: 0,
      },
      parseErrors: [],
    };
  }

  private async fixXmlFile(filePath: string): Promise<FileFixResult> {
    const changes: FixChange[] = [];
    const errors: string[] = [];

    let content: string;
    try {
      content = await fsReadFile(filePath, 'utf-8');
    } catch (e) {
      return {
        filePath,
        fileType: 'xml',
        changes: [],
        errors: [`Failed to read file: ${e}`],
        wasModified: false,
      };
    }

    let modified = false;
    let newContent = content;

    // Fix font paths
    if (this.config.fixFontPaths) {
      const fontPattern = /(font\s*=\s*["'])([^"']+)\.(ttf|otf)(\|[^"']*)?((["']))/gi;
      newContent = newContent.replace(fontPattern, (match, prefix, path, ext, options, quote) => {
        const newPath = `${prefix}${path}.slug${options ?? ''}${quote}`;
        if (match !== newPath) {
          changes.push({
            location: { start: { line: 0, column: 0, offset: 0 }, end: { line: 0, column: 0, offset: 0 } },
            oldCode: match,
            newCode: newPath,
            reason: 'Convert font path to Slug format',
            confidence: 0.95,
          });
          modified = true;
        }
        return newPath;
      });
    }

    // Write if modified and not dry run
    if (modified && !this.config.dryRun) {
      try {
        await fsWriteFile(filePath, newContent, 'utf-8');
      } catch (e) {
        errors.push(`Failed to write file: ${e}`);
      }
    }

    return {
      filePath,
      fileType: 'xml',
      changes,
      errors,
      wasModified: modified && !this.config.dryRun,
    };
  }

  // ============================================================================
  // Backup and Packaging
  // ============================================================================

  private async createBackup(addonPath: string): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const addonName = basename(addonPath);
    const backupPath = join(dirname(addonPath), `${addonName}_backup_${timestamp}`);

    await this.copyDirectory(addonPath, backupPath);
    return backupPath;
  }

  private async restoreBackup(backupPath: string, originalPath: string): Promise<void> {
    await rm(originalPath, { recursive: true, force: true });
    await this.copyDirectory(backupPath, originalPath);
  }

  private async copyDirectory(src: string, dest: string): Promise<void> {
    await mkdir(dest, { recursive: true });
    const entries = await readdir(src, { withFileTypes: true });

    for (const entry of entries) {
      const srcPath = join(src, entry.name);
      const destPath = join(dest, entry.name);

      if (entry.isDirectory()) {
        await this.copyDirectory(srcPath, destPath);
      } else {
        await copyFile(srcPath, destPath);
      }
    }
  }

  private async packageAddon(addonPath: string, outputPath: string): Promise<string> {
    const addonName = basename(addonPath);
    const zipPath = join(outputPath, `${addonName}.zip`);

    await mkdir(outputPath, { recursive: true });

    return new Promise((resolve, reject) => {
      const output = createWriteStream(zipPath);
      // @ts-ignore - archiver types issue
      const archive = archiver.default('zip', { zlib: { level: 9 } });

      output.on('close', () => resolve(zipPath));
      archive.on('error', reject);

      archive.pipe(output);

      // Add files with correct structure (AddonName/file.lua)
      archive.directory(addonPath, addonName);

      archive.finalize();
    });
  }

  // ============================================================================
  // Summary Calculation
  // ============================================================================

  private calculateSummary(fileResults: readonly FileAnalysisResult[]): AnalysisSummary {
    const issuesBySeverity: Record<IssueSeverity, number> = {
      error: 0,
      warning: 0,
      info: 0,
    };

    const issuesByCategory: Partial<Record<IssueCategory, number>> = {};
    let autoFixableCount = 0;

    for (const result of fileResults) {
      for (const issue of result.issues) {
        issuesBySeverity[issue.severity]++;
        issuesByCategory[issue.category] = (issuesByCategory[issue.category] ?? 0) + 1;
        if (issue.autoFixable) {
          autoFixableCount++;
        }
      }
    }

    const totalIssues = issuesBySeverity.error + issuesBySeverity.warning + issuesBySeverity.info;

    // Estimate fix time based on complexity
    let estimatedMinutes = autoFixableCount * 0.1;
    estimatedMinutes += (totalIssues - autoFixableCount) * 2;

    const estimatedFixTime =
      estimatedMinutes < 1
        ? '< 1 minute'
        : estimatedMinutes < 60
          ? `~${Math.ceil(estimatedMinutes)} minutes`
          : `~${Math.ceil(estimatedMinutes / 60)} hours`;

    return {
      totalFiles: fileResults.length,
      totalIssues,
      issuesBySeverity,
      issuesByCategory,
      autoFixableCount,
      estimatedFixTime,
    };
  }
}

// ============================================================================
// Convenience Functions
// ============================================================================

export async function analyzeAddon(
  addonPath: string,
  config?: Partial<FixerConfig>
): Promise<AddonAnalysisResult> {
  const fixer = new AddonFixer(config);
  return fixer.analyze(addonPath);
}

export async function fixAddon(
  addonPath: string,
  outputPath?: string,
  config?: Partial<FixerConfig>
): Promise<AddonFixResult> {
  const fixer = new AddonFixer(config);
  return fixer.fix(addonPath, outputPath);
}
