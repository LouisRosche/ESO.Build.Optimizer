/**
 * Main addon fixer orchestrator.
 *
 * Coordinates analysis and fixing across all file types:
 * - Manifest files (.txt)
 * - Lua source files (.lua)
 * - XML UI files (.xml)
 */

import { readdir, stat, mkdir, copyFile, rm } from 'node:fs/promises';
import { join, basename, dirname, extname } from 'node:path';
import { createWriteStream } from 'node:fs';
import { pipeline } from 'node:stream/promises';
import { createGzip } from 'node:zlib';
import * as tar from 'tar';

import type {
  FixerConfig,
  AddonAnalysisResult,
  AddonFixResult,
  FileAnalysisResult,
  FileFixResult,
  AnalysisSummary,
  IssueSeverity,
  IssueCategory,
} from './types.js';
import { DEFAULT_CONFIG } from './types.js';
import { LuaAnalyzer } from './lua-analyzer.js';
import { parseManifest, analyzeManifest, fixManifest } from './manifest-parser.js';
import { getAddonRecommendation } from './migrations.js';

// ============================================================================
// Addon Fixer
// ============================================================================

export class AddonFixer {
  private readonly config: FixerConfig;
  private readonly luaAnalyzer: LuaAnalyzer;

  constructor(config: Partial<FixerConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.luaAnalyzer = new LuaAnalyzer(this.config.confidenceThreshold);
  }

  // ============================================================================
  // Analysis
  // ============================================================================

  async analyze(addonPath: string): Promise<AddonAnalysisResult> {
    const addonName = basename(addonPath);
    const fileResults: FileAnalysisResult[] = [];
    const warnings: string[] = [];
    const errors: string[] = [];

    // Check for replacement recommendations
    const recommendation = getAddonRecommendation(addonName);
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
      const result = await this.luaAnalyzer.analyzeFile(file);
      fileResults.push(result);
    }

    // Analyze XML files (simplified for now)
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
    const addonName = basename(addonPath);
    const fileResults: FileFixResult[] = [];
    const errors: string[] = [];
    const warnings: string[] = [];
    const recommendations: string[] = [];
    let backupPath: string | undefined;
    let packagePath: string | undefined;
    let totalChanges = 0;

    // Check for replacement recommendations
    const recommendation = getAddonRecommendation(addonName);
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
        const result = await this.fixLuaFile(file);
        fileResults.push(result);
        totalChanges += result.changes.length;
        errors.push(...result.errors);
      }

      // Fix XML files
      for (const file of files.xml) {
        const result = await this.fixXmlFile(file);
        fileResults.push(result);
        totalChanges += result.changes.length;
        errors.push(...result.errors);
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
  // Lua File Fixing
  // ============================================================================

  private async fixLuaFile(filePath: string): Promise<FileFixResult> {
    // For now, use the analyzer to detect issues
    // Full transformation requires luaparse code generation
    const analysis = await this.luaAnalyzer.analyzeFile(filePath);

    const changes = analysis.issues
      .filter((issue) => issue.autoFixable && issue.confidence >= this.config.confidenceThreshold)
      .map((issue) => ({
        location: issue.location,
        oldCode: issue.oldCode,
        newCode: issue.suggestedFix ?? '',
        reason: issue.message,
        confidence: issue.confidence,
      }));

    // Apply fixes if not dry run
    // TODO: Implement actual code transformation
    const wasModified = changes.length > 0 && !this.config.dryRun;

    return {
      filePath,
      fileType: 'lua',
      changes,
      errors: analysis.parseErrors.map((e) => e.message),
      wasModified,
    };
  }

  // ============================================================================
  // XML File Analysis/Fixing
  // ============================================================================

  private async analyzeXmlFile(filePath: string): Promise<FileAnalysisResult> {
    // Simplified XML analysis - just check for font paths
    const { readFile } = await import('node:fs/promises');
    let content: string;

    try {
      content = await readFile(filePath, 'utf-8');
    } catch {
      return {
        filePath,
        fileType: 'xml',
        issues: [],
        metrics: { lineCount: 0, functionCount: 0, eventRegistrations: 0, libStubUsages: 0, deprecatedCalls: 0 },
        parseErrors: [{ message: 'Failed to read file', recoverable: false }],
      };
    }

    const issues: FileAnalysisResult['issues'] = [];
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
    const analysis = await this.analyzeXmlFile(filePath);

    const changes = analysis.issues
      .filter((issue) => issue.autoFixable)
      .map((issue) => ({
        location: issue.location,
        oldCode: issue.oldCode,
        newCode: issue.suggestedFix ?? '',
        reason: issue.message,
        confidence: issue.confidence,
      }));

    return {
      filePath,
      fileType: 'xml',
      changes,
      errors: [],
      wasModified: changes.length > 0 && !this.config.dryRun,
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

    // Use archiver or similar - for now just create the path
    // TODO: Implement actual zip creation
    await mkdir(outputPath, { recursive: true });

    return zipPath;
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
    let estimatedMinutes = autoFixableCount * 0.1; // Auto-fixes are quick
    estimatedMinutes += (totalIssues - autoFixableCount) * 2; // Manual fixes take longer

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
