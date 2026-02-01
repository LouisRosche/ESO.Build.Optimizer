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

    // Find manifest - prefer .addon over .txt (console requirement)
    const addonManifestPath = join(addonPath, `${addonName}.addon`);
    const txtManifestPath = join(addonPath, `${addonName}.txt`);
    let manifestPath: string | null = null;
    let manifestData;
    let usesDeprecatedTxt = false;

    try {
      await stat(addonManifestPath);
      manifestPath = addonManifestPath;
    } catch {
      try {
        await stat(txtManifestPath);
        manifestPath = txtManifestPath;
        usesDeprecatedTxt = true;
      } catch {
        warnings.push(`Missing manifest file: ${addonName}.addon or ${addonName}.txt`);
      }
    }

    if (manifestPath) {
      const manifestResult = await analyzeManifest(manifestPath);

      // Add deprecation warning for .txt extension
      if (usesDeprecatedTxt) {
        const txtIssue: Issue = {
          id: 'manifest-ext-001',
          filePath: manifestPath,
          category: 'api_version',
          severity: 'warning',
          message: '.txt manifest extension is deprecated (use .addon for console support)',
          details: 'Starting June 4, 2025, .txt files will be ignored on console. Create a .addon file.',
          location: { start: { line: 1, column: 0, offset: 0 }, end: { line: 1, column: 0, offset: 0 } },
          oldCode: `${addonName}.txt`,
          suggestedFix: `${addonName}.addon`,
          autoFixable: true,
          confidence: 1.0,
        };
        const enhancedManifestResult: FileAnalysisResult = {
          ...manifestResult,
          issues: [txtIssue, ...manifestResult.issues],
        };
        fileResults.push(enhancedManifestResult);
      } else {
        fileResults.push(manifestResult);
      }

      manifestData = await parseManifest(manifestPath);
    }

    // Find all Lua and XML files
    const files = await this.findFiles(addonPath);

    // Analyze Lua files
    for (const file of files.lua) {
      const result = await this.luaAnalyzer!.analyzeFile(file);
      // Add pattern migration issues
      const patternIssues = await this.checkPatternMigrations(file);
      if (patternIssues.length > 0) {
        const enhancedResult: FileAnalysisResult = {
          ...result,
          issues: [...result.issues, ...patternIssues],
        };
        fileResults.push(enhancedResult);
      } else {
        fileResults.push(result);
      }
    }

    // Analyze XML files
    for (const file of files.xml) {
      const result = await this.analyzeXmlFile(file);
      fileResults.push(result);
    }

    // Check case sensitivity (console compatibility)
    if (manifestData?.files && manifestData.files.length > 0) {
      const caseIssues = await this.checkCaseSensitivity(addonPath, manifestData.files as string[]);
      if (caseIssues.length > 0) {
        fileResults.push({
          filePath: addonPath,
          fileType: 'manifest',
          issues: caseIssues,
          metrics: { lineCount: 0, functionCount: 0, eventRegistrations: 0, libStubUsages: 0, deprecatedCalls: 0 },
          parseErrors: [],
        });
      }
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
      // Fix manifest - prefer .addon over .txt
      const addonManifestPath = join(addonPath, `${addonName}.addon`);
      const txtManifestPath = join(addonPath, `${addonName}.txt`);
      let manifestPath: string | null = null;
      let usesDeprecatedTxt = false;

      try {
        await stat(addonManifestPath);
        manifestPath = addonManifestPath;
      } catch {
        try {
          await stat(txtManifestPath);
          manifestPath = txtManifestPath;
          usesDeprecatedTxt = true;
        } catch {
          warnings.push('Manifest file not found');
        }
      }

      if (manifestPath) {
        const manifestResult = await fixManifest(manifestPath, this.config.dryRun);
        fileResults.push(manifestResult);
        totalChanges += manifestResult.changes.length;

        // Create .addon file from .txt if needed (for console compatibility)
        if (usesDeprecatedTxt && !this.config.dryRun) {
          try {
            const content = await fsReadFile(txtManifestPath, 'utf-8');
            await fsWriteFile(addonManifestPath, content, 'utf-8');
            const addonCopyResult: FileFixResult = {
              filePath: addonManifestPath,
              fileType: 'manifest',
              changes: [{
                location: { start: { line: 1, column: 0, offset: 0 }, end: { line: 1, column: 0, offset: 0 } },
                oldCode: '',
                newCode: `${addonName}.addon`,
                reason: 'Create .addon file for console compatibility (June 2025 requirement)',
                confidence: 1.0,
              }],
              errors: [],
              wasModified: true,
            };
            fileResults.push(addonCopyResult);
            totalChanges += 1;
          } catch (e) {
            warnings.push(`Failed to create .addon file: ${e}`);
          }
        }
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
  // Pattern Migration Check
  // ============================================================================

  private async checkPatternMigrations(filePath: string): Promise<Issue[]> {
    const issues: Issue[] = [];

    if (!this.migrations?.patternMigrations) {
      return issues;
    }

    let content: string;
    try {
      content = await fsReadFile(filePath, 'utf-8');
    } catch {
      return issues;
    }

    let issueId = 0;
    for (const pattern of this.migrations.patternMigrations) {
      try {
        // Check if pattern looks like a regex (contains unescaped regex metacharacters)
        // Parentheses in a literal like "WINDOW_MANAGER:CreateControl(" should use string search
        const regexMetaChars = /[|[\]+*?^${}]|\\[dDwWsSbB]/;
        const isRegexPattern = regexMetaChars.test(pattern.pattern);

        if (!isRegexPattern) {
          // Simple string search (literal matching)
          let pos = 0;
          while ((pos = content.indexOf(pattern.pattern, pos)) !== -1) {
            // Skip if in comment
            const lineStart = content.lastIndexOf('\n', pos) + 1;
            const lineContent = content.substring(lineStart, pos);
            if (lineContent.includes('--')) {
              pos++;
              continue;
            }

            const lineNum = content.substring(0, pos).split('\n').length;
            issues.push({
              id: `pattern-${++issueId}`,
              filePath,
              category: 'deprecated_function',
              severity: 'warning',
              message: pattern.notes,
              location: {
                start: { line: lineNum, column: 0, offset: pos },
                end: { line: lineNum, column: pattern.pattern.length, offset: pos + pattern.pattern.length },
              },
              oldCode: pattern.pattern,
              suggestedFix: pattern.replacement,
              autoFixable: pattern.autoFixable,
              confidence: pattern.confidence,
            });
            pos++;
          }
        } else {
          // Regex-based search
          const regex = new RegExp(pattern.pattern, 'g');
          let match;
          while ((match = regex.exec(content)) !== null) {
            // Skip if in comment
            const lineStart = content.lastIndexOf('\n', match.index) + 1;
            const lineContent = content.substring(lineStart, match.index);
            if (lineContent.includes('--')) {
              continue;
            }

            const lineNum = content.substring(0, match.index).split('\n').length;
            issues.push({
              id: `pattern-${++issueId}`,
              filePath,
              category: 'deprecated_function',
              severity: 'warning',
              message: pattern.notes,
              location: {
                start: { line: lineNum, column: 0, offset: match.index },
                end: { line: lineNum, column: match[0].length, offset: match.index + match[0].length },
              },
              oldCode: match[0],
              suggestedFix: pattern.replacement,
              autoFixable: pattern.autoFixable,
              confidence: pattern.confidence,
            });
          }
        }
      } catch (e) {
          // Report invalid patterns instead of silent skip
          issues.push({
            id: `pattern-error-${++issueId}`,
            filePath,
            category: 'deprecated_function',
            severity: 'info',
            message: `Invalid pattern migration "${pattern.name}": ${e instanceof Error ? e.message : 'unknown error'}`,
            location: { start: { line: 0, column: 0, offset: 0 }, end: { line: 0, column: 0, offset: 0 } },
            oldCode: pattern.pattern,
            suggestedFix: undefined,
            autoFixable: false,
            confidence: 0,
          });
        }
      }

    return issues;
  }

  // ============================================================================
  // Case Sensitivity Check (Console Compatibility)
  // ============================================================================

  private async checkCaseSensitivity(addonPath: string, manifestFiles: string[]): Promise<Issue[]> {
    const issues: Issue[] = [];
    let issueId = 0;

    // Get actual files on disk
    const actualFiles = new Map<string, string>(); // lowercase -> actual path
    const collectFiles = async (dir: string, prefix: string = ''): Promise<void> => {
      try {
        const entries = await readdir(dir, { withFileTypes: true });
        for (const entry of entries) {
          const relativePath = prefix ? `${prefix}/${entry.name}` : entry.name;
          if (entry.isDirectory() && !entry.name.includes('_backup_')) {
            await collectFiles(join(dir, entry.name), relativePath);
          } else if (entry.isFile()) {
            actualFiles.set(relativePath.toLowerCase(), relativePath);
          }
        }
      } catch {
        // Skip unreadable directories
      }
    };
    await collectFiles(addonPath);

    // Check each manifest file reference
    for (const manifestFile of manifestFiles) {
      const lowerPath = manifestFile.toLowerCase();
      const actualPath = actualFiles.get(lowerPath);

      if (actualPath && actualPath !== manifestFile) {
        issues.push({
          id: `case-${++issueId}`,
          filePath: addonPath,
          category: 'dependency',
          severity: 'warning',
          message: `Case mismatch: manifest references "${manifestFile}" but file is "${actualPath}"`,
          details: 'PlayStation uses case-sensitive filesystem. This will fail on console.',
          location: { start: { line: 0, column: 0, offset: 0 }, end: { line: 0, column: 0, offset: 0 } },
          oldCode: manifestFile,
          suggestedFix: actualPath,
          autoFixable: true,
          confidence: 1.0,
        });
      } else if (!actualPath && !actualFiles.has(lowerPath)) {
        issues.push({
          id: `missing-${++issueId}`,
          filePath: addonPath,
          category: 'dependency',
          severity: 'error',
          message: `Missing file: manifest references "${manifestFile}" but file not found`,
          location: { start: { line: 0, column: 0, offset: 0 }, end: { line: 0, column: 0, offset: 0 } },
          oldCode: manifestFile,
          autoFixable: false,
          confidence: 1.0,
        });
      }
    }

    return issues;
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
