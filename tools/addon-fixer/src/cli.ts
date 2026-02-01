#!/usr/bin/env node
/**
 * ESO Addon Fixer CLI
 *
 * Command-line interface for analyzing and fixing broken ESO addons.
 */

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { readFile, stat, readdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join, basename, extname } from 'node:path';
import { execSync } from 'node:child_process';

import { AddonFixer, analyzeAddon, fixAddon } from './fixer.js';
import {
  API_VERSION_HISTORY,
  FUNCTION_MIGRATIONS,
  LIBRARY_MIGRATIONS,
  ADDON_RECOMMENDATIONS,
  getMigrationsByCategory,
  getMigrationsByVersion,
} from './migrations.js';
import {
  LIBRARY_DATABASE,
  LIBRARY_RECOMMENDATIONS,
  checkLibraryHealth,
  getLibraryRecommendations,
} from './library-db.js';
import { CURRENT_LIVE_API, CURRENT_PTS_API } from './types.js';
import type { FixerConfig, IssueSeverity } from './types.js';

// ============================================================================
// CLI Setup
// ============================================================================

const program = new Command();

// Get version from package.json
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

program
  .name('eso-addon-fixer')
  .description('Automated fixer for broken Elder Scrolls Online addons')
  .version('1.0.0');

// ============================================================================
// Analyze Command
// ============================================================================

program
  .command('analyze <addon-path>')
  .description('Analyze an addon for issues without making changes')
  .option('-v, --verbose', 'Show detailed file-by-file analysis')
  .option('--json', 'Output results as JSON')
  .option('-c, --confidence <number>', 'Minimum confidence threshold (0.0-1.0)', '0.8')
  .action(async (addonPath: string, options: { verbose?: boolean; json?: boolean; confidence: string }) => {
    const spinner = ora('Analyzing addon...').start();

    try {
      const config: Partial<FixerConfig> = {
        confidenceThreshold: parseFloat(options.confidence),
      };

      const result = await analyzeAddon(addonPath, config);
      spinner.stop();

      if (options.json) {
        console.log(JSON.stringify(result, null, 2));
        return;
      }

      // Print header
      console.log(chalk.bold('\n' + '='.repeat(60)));
      console.log(chalk.bold(` Addon: ${result.addonName}`));
      console.log('='.repeat(60) + '\n');

      // Status
      const hasErrors = result.summary.issuesBySeverity.error > 0;
      const status = hasErrors ? chalk.red('ISSUES FOUND') : chalk.green('SUCCESS');
      console.log(`Status: ${status}`);
      console.log(`Path: ${result.addonPath}`);
      console.log(`Total issues: ${result.summary.totalIssues}`);
      console.log(`Auto-fixable: ${result.summary.autoFixableCount}`);
      console.log(`Estimated fix time: ${result.summary.estimatedFixTime}`);

      // Issue summary
      if (result.summary.totalIssues > 0) {
        console.log(chalk.bold('\n--- Issues by Severity ---\n'));
        if (result.summary.issuesBySeverity.error > 0) {
          console.log(chalk.red(`  Errors: ${result.summary.issuesBySeverity.error}`));
        }
        if (result.summary.issuesBySeverity.warning > 0) {
          console.log(chalk.yellow(`  Warnings: ${result.summary.issuesBySeverity.warning}`));
        }
        if (result.summary.issuesBySeverity.info > 0) {
          console.log(chalk.blue(`  Info: ${result.summary.issuesBySeverity.info}`));
        }
      }

      // Verbose output
      if (options.verbose) {
        console.log(chalk.bold('\n--- File Details ---\n'));

        for (const fileResult of result.fileResults) {
          const fileIssues = fileResult.issues.length;
          const filename = fileResult.filePath.split('/').pop() ?? fileResult.filePath;

          if (fileIssues > 0) {
            console.log(`  ${chalk.cyan(filename)}:`);
            for (const issue of fileResult.issues) {
              const severityColor = getSeverityColor(issue.severity);
              const prefix = issue.autoFixable ? '[FIX]' : '[MANUAL]';
              console.log(`  ${severityColor(prefix)} ${issue.message}`);
              if (issue.suggestedFix) {
                console.log(chalk.gray(`        → ${issue.suggestedFix}`));
              }
            }
            console.log();
          }
        }
      }

    } catch (error) {
      spinner.fail('Analysis failed');
      console.error(chalk.red(`Error: ${error}`));
      process.exit(1);
    }
  });

// ============================================================================
// Fix Command
// ============================================================================

program
  .command('fix <addon-path>')
  .description('Fix issues in an addon')
  .option('-o, --output <dir>', 'Output directory for packaged addon')
  .option('-v, --verbose', 'Show detailed changes')
  .option('--dry-run', 'Preview changes without modifying files')
  .option('--no-backup', 'Skip backup creation')
  .option('--no-version-update', 'Don\'t update API version')
  .option('--no-libstub-fix', 'Don\'t fix LibStub patterns')
  .option('--no-font-fix', 'Don\'t fix font paths')
  .option('-c, --confidence <number>', 'Minimum confidence threshold (0.0-1.0)', '0.8')
  .action(async (addonPath: string, options: {
    output?: string;
    verbose?: boolean;
    dryRun?: boolean;
    backup?: boolean;
    versionUpdate?: boolean;
    libstubFix?: boolean;
    fontFix?: boolean;
    confidence: string;
  }) => {
    const spinner = ora('Fixing addon...').start();

    try {
      const config: Partial<FixerConfig> = {
        dryRun: options.dryRun ?? false,
        createBackup: options.backup ?? true,
        updateApiVersion: options.versionUpdate ?? true,
        fixLibStub: options.libstubFix ?? true,
        fixFontPaths: options.fontFix ?? true,
        confidenceThreshold: parseFloat(options.confidence),
      };

      const result = await fixAddon(addonPath, options.output, config);
      spinner.stop();

      // Print header
      console.log(chalk.bold('\n' + '='.repeat(60)));
      console.log(chalk.bold(` Addon: ${result.addonName}`));
      console.log('='.repeat(60) + '\n');

      // Status
      const status = result.success ? chalk.green('SUCCESS') : chalk.red('FAILED');
      console.log(`Status: ${status}`);
      console.log(`Total changes: ${result.totalChanges}`);

      if (options.dryRun) {
        console.log(chalk.yellow('\n[DRY RUN] No files were modified.\n'));
      }

      if (result.backupPath) {
        console.log(`Backup: ${result.backupPath}`);
      }

      if (result.packagePath) {
        console.log(`Package: ${result.packagePath}`);
      }

      // Errors
      if (result.errors.length > 0) {
        console.log(chalk.red('\n--- Errors ---\n'));
        for (const error of result.errors) {
          console.log(chalk.red(`  ${error}`));
        }
      }

      // Warnings
      if (result.warnings.length > 0) {
        console.log(chalk.yellow('\n--- Warnings ---\n'));
        for (const warning of result.warnings) {
          console.log(chalk.yellow(`  ${warning}`));
        }
      }

      // Recommendations
      if (result.recommendations.length > 0) {
        console.log(chalk.cyan('\n--- Recommendations ---\n'));
        for (const rec of result.recommendations) {
          console.log(`  ${rec}`);
        }
      }

      // Verbose changes
      if (options.verbose && result.totalChanges > 0) {
        console.log(chalk.bold('\n--- Changes ---\n'));

        for (const fileResult of result.fileResults) {
          if (fileResult.changes.length > 0) {
            const filename = fileResult.filePath.split('/').pop() ?? fileResult.filePath;
            console.log(`  ${chalk.cyan(filename)}:`);
            for (const change of fileResult.changes) {
              console.log(chalk.gray(`    ${change.reason}`));
              console.log(`    ${chalk.red(`- ${change.oldCode}`)}`);
              console.log(`    ${chalk.green(`+ ${change.newCode}`)}`);
            }
            console.log();
          }
        }
      }

      process.exit(result.success ? 0 : 1);

    } catch (error) {
      spinner.fail('Fix failed');
      console.error(chalk.red(`Error: ${error}`));
      process.exit(1);
    }
  });

// ============================================================================
// Verify Command
// ============================================================================

program
  .command('verify <addon-path>')
  .description('Verify addon after fixing (syntax check, manifest validation)')
  .option('--json', 'Output results as JSON')
  .action(async (addonPath: string, options: { json?: boolean }) => {
    const spinner = ora('Verifying addon...').start();
    const results: {
      syntax: { status: 'pass' | 'fail' | 'skipped'; errors: string[] };
      manifest: { status: 'pass' | 'warn' | 'fail'; issues: string[] };
      caseCheck: { status: 'pass' | 'warn' | 'fail'; issues: string[] };
      remaining: { status: 'pass' | 'warn' | 'fail'; count: number; issues: string[] };
      overall: 'pass' | 'warn' | 'fail';
    } = {
      syntax: { status: 'skipped', errors: [] },
      manifest: { status: 'pass', issues: [] },
      caseCheck: { status: 'pass', issues: [] },
      remaining: { status: 'pass', count: 0, issues: [] },
      overall: 'pass',
    };

    try {
      const addonName = basename(addonPath);

      // 1. Syntax Check with luacheck
      spinner.text = 'Checking Lua syntax...';
      try {
        execSync('which luacheck', { stdio: 'pipe' });
        // luacheck is available
        try {
          const luaFiles = await findLuaFiles(addonPath);
          if (luaFiles.length > 0) {
            execSync(`luacheck ${luaFiles.map(f => `"${f}"`).join(' ')} --no-config --codes`, {
              stdio: 'pipe',
              encoding: 'utf-8',
            });
            results.syntax.status = 'pass';
          } else {
            results.syntax.status = 'skipped';
            results.syntax.errors.push('No Lua files found');
          }
        } catch (e: unknown) {
          results.syntax.status = 'fail';
          const error = e as { stdout?: string; stderr?: string };
          results.syntax.errors.push(error.stdout || error.stderr || 'Syntax check failed');
        }
      } catch {
        results.syntax.status = 'skipped';
        results.syntax.errors.push('luacheck not installed');
      }

      // 2. Manifest Check
      spinner.text = 'Checking manifest...';
      const addonManifest = join(addonPath, `${addonName}.addon`);
      const txtManifest = join(addonPath, `${addonName}.txt`);

      try {
        await stat(addonManifest);
      } catch {
        results.manifest.issues.push('Missing .addon file (required for console)');
        try {
          await stat(txtManifest);
          results.manifest.issues.push('Using deprecated .txt manifest');
        } catch {
          results.manifest.status = 'fail';
          results.manifest.issues.push('No manifest file found');
        }
      }

      // Check API version in manifest
      try {
        const manifestPath = await stat(addonManifest).then(() => addonManifest).catch(() => txtManifest);
        const manifestContent = await readFile(manifestPath, 'utf-8');
        const apiMatch = manifestContent.match(/##\s*APIVersion:\s*(\d+)/);
        if (apiMatch) {
          const apiVersion = parseInt(apiMatch[1], 10);
          if (apiVersion < CURRENT_LIVE_API) {
            results.manifest.issues.push(`API version ${apiVersion} is outdated (current: ${CURRENT_LIVE_API})`);
          }
        } else {
          results.manifest.issues.push('No APIVersion found in manifest');
        }
      } catch {
        // Already handled above
      }

      // Only fail if critical issues, warn for deprecation/outdated
      if (results.manifest.issues.length > 0 && results.manifest.status !== 'fail') {
        const hasCriticalIssue = results.manifest.issues.some(i =>
          i.includes('No manifest file found') || i.includes('No APIVersion found')
        );
        results.manifest.status = hasCriticalIssue ? 'fail' : 'warn';
      }

      // 3. Case Sensitivity Check
      spinner.text = 'Checking case sensitivity...';
      const analysisResult = await analyzeAddon(addonPath);
      const caseIssues = analysisResult.fileResults
        .flatMap(f => f.issues)
        .filter(i => i.message?.includes('Case mismatch') || i.message?.includes('Missing file'));

      if (caseIssues.length > 0) {
        results.caseCheck.status = caseIssues.some(i => i.severity === 'error') ? 'fail' : 'warn';
        results.caseCheck.issues = caseIssues.map(i => i.message ?? '');
      }

      // 4. Remaining Issues
      spinner.text = 'Checking for remaining issues...';
      const remainingIssues = analysisResult.fileResults
        .flatMap(f => f.issues)
        .filter(i => i.category !== 'dependency' && i.severity !== 'info');

      results.remaining.count = remainingIssues.length;
      if (remainingIssues.length > 0) {
        results.remaining.status = remainingIssues.some(i => i.severity === 'error') ? 'fail' : 'warn';
        results.remaining.issues = remainingIssues.slice(0, 10).map(i => `${i.category}: ${i.message}`);
        if (remainingIssues.length > 10) {
          results.remaining.issues.push(`... and ${remainingIssues.length - 10} more`);
        }
      }

      // Calculate overall status
      if (results.syntax.status === 'fail' || results.manifest.status === 'fail' ||
          results.caseCheck.status === 'fail' || results.remaining.status === 'fail') {
        results.overall = 'fail';
      } else if (results.manifest.status === 'warn' || results.caseCheck.status === 'warn' ||
                 results.remaining.status === 'warn') {
        results.overall = 'warn';
      }

      spinner.stop();

      if (options.json) {
        console.log(JSON.stringify(results, null, 2));
        return;
      }

      // Print results
      console.log(chalk.bold('\n' + '='.repeat(60)));
      console.log(chalk.bold(` Verification Report: ${addonName}`));
      console.log('='.repeat(60) + '\n');

      // Syntax
      const syntaxIcon = results.syntax.status === 'pass' ? chalk.green('✓') :
        results.syntax.status === 'fail' ? chalk.red('✗') : chalk.gray('○');
      console.log(`${syntaxIcon} Syntax Check: ${results.syntax.status.toUpperCase()}`);
      if (results.syntax.errors.length > 0) {
        for (const err of results.syntax.errors) {
          console.log(chalk.gray(`    ${err.split('\n')[0]}`));
        }
      }

      // Manifest
      const manifestIcon = results.manifest.status === 'pass' ? chalk.green('✓') :
        results.manifest.status === 'warn' ? chalk.yellow('!') : chalk.red('✗');
      console.log(`${manifestIcon} Manifest: ${results.manifest.status.toUpperCase()}`);
      for (const issue of results.manifest.issues) {
        console.log(chalk.gray(`    ${issue}`));
      }

      // Case
      const caseIcon = results.caseCheck.status === 'pass' ? chalk.green('✓') :
        results.caseCheck.status === 'warn' ? chalk.yellow('!') : chalk.red('✗');
      console.log(`${caseIcon} Case Sensitivity: ${results.caseCheck.status.toUpperCase()}`);
      for (const issue of results.caseCheck.issues) {
        console.log(chalk.gray(`    ${issue}`));
      }

      // Remaining
      const remainIcon = results.remaining.status === 'pass' ? chalk.green('✓') :
        results.remaining.status === 'warn' ? chalk.yellow('!') : chalk.red('✗');
      console.log(`${remainIcon} Remaining Issues: ${results.remaining.count}`);
      for (const issue of results.remaining.issues) {
        console.log(chalk.gray(`    ${issue}`));
      }

      // Overall
      console.log(chalk.bold('\n--- Overall ---'));
      const overallColor = results.overall === 'pass' ? chalk.green :
        results.overall === 'warn' ? chalk.yellow : chalk.red;
      console.log(overallColor(`\n  ${results.overall.toUpperCase()}\n`));

      process.exit(results.overall === 'fail' ? 1 : 0);

    } catch (error) {
      spinner.fail('Verification failed');
      console.error(chalk.red(`Error: ${error}`));
      process.exit(1);
    }
  });

// ============================================================================
// Migrations Command
// ============================================================================

program
  .command('migrations')
  .description('List known API migrations')
  .option('-c, --category <category>', 'Filter by category')
  .option('--version <number>', 'Filter by API version')
  .option('--json', 'Output as JSON')
  .action((options: { category?: string; version?: string; json?: boolean }) => {
    let migrations = [...FUNCTION_MIGRATIONS];

    if (options.category) {
      migrations = getMigrationsByCategory(options.category) as typeof migrations;
    }

    if (options.version) {
      const version = parseInt(options.version, 10);
      migrations = getMigrationsByVersion(version) as typeof migrations;
    }

    if (options.json) {
      console.log(JSON.stringify(migrations, null, 2));
      return;
    }

    console.log(chalk.bold('\n' + '='.repeat(60)));
    console.log(chalk.bold(' Known API Migrations'));
    console.log('='.repeat(60) + '\n');

    // Group by category
    const byCategory = new Map<string, typeof migrations>();
    for (const m of migrations) {
      const cat = m.category;
      if (!byCategory.has(cat)) {
        byCategory.set(cat, []);
      }
      byCategory.get(cat)!.push(m);
    }

    for (const [category, catMigrations] of byCategory) {
      console.log(chalk.bold(`\n${category.toUpperCase()}`));
      console.log('-'.repeat(40));

      for (const m of catMigrations) {
        const confidence = m.confidence >= 0.9 ? chalk.green('●') :
          m.confidence >= 0.7 ? chalk.yellow('●') : chalk.red('●');
        const autoFix = m.autoFixable ? chalk.green('[auto]') : chalk.gray('[manual]');

        console.log(`  ${confidence} ${m.oldName} → ${m.newName ?? m.replacementCode ?? 'removed'} ${autoFix}`);
        if (m.notes) {
          console.log(chalk.gray(`     ${m.notes}`));
        }
      }
    }

    console.log(chalk.bold('\n\nLibrary Migrations:'));
    console.log('-'.repeat(40));
    for (const lib of LIBRARY_MIGRATIONS) {
      console.log(`  ${lib.libraryName} → ${lib.globalVariable}`);
    }

    console.log(`\n\nTotal: ${FUNCTION_MIGRATIONS.length} function migrations, ${LIBRARY_MIGRATIONS.length} library migrations`);
  });

// ============================================================================
// Libraries Command
// ============================================================================

program
  .command('libraries')
  .alias('libs')
  .description('Show known ESO libraries and check addon dependencies')
  .option('-a, --addon <path>', 'Check library health for a specific addon')
  .option('--all', 'Show all libraries including deprecated')
  .option('--json', 'Output as JSON')
  .action(async (options: { addon?: string; all?: boolean; json?: boolean }) => {
    if (options.addon) {
      // Check library health for an addon
      const spinner = ora('Checking library health...').start();

      try {
        // Read manifest to find dependencies
        const manifestPath = join(options.addon, basename(options.addon) + '.txt');
        let manifestContent: string;
        try {
          manifestContent = await readFile(manifestPath, 'utf-8');
        } catch {
          const addonManifest = join(options.addon, basename(options.addon) + '.addon');
          manifestContent = await readFile(addonManifest, 'utf-8');
        }

        // Parse dependencies
        const depLines = manifestContent.split('\n')
          .filter(l => l.startsWith('## DependsOn:') || l.startsWith('## OptionalDependsOn:'));

        const dependencies: { name: string; version?: string }[] = [];
        for (const line of depLines) {
          const deps = line.split(':')[1]?.trim().split(/\s+/) || [];
          for (const dep of deps) {
            const match = dep.match(/^([^>=<]+)(?:>=(\d+))?/);
            if (match) {
              dependencies.push({
                name: match[1],
                version: match[2],
              });
            }
          }
        }

        // Also scan Lua files for library usage
        const luaFiles = await findLuaFiles(options.addon);
        let allCode = '';
        for (const file of luaFiles.slice(0, 20)) { // Limit for performance
          try {
            allCode += await readFile(file, 'utf-8') + '\n';
          } catch { /* skip */ }
        }

        // Get recommendations
        const recommendations = getLibraryRecommendations(allCode);

        spinner.stop();

        if (options.json) {
          const healthResults = dependencies.map(d => checkLibraryHealth(d.name, d.version));
          console.log(JSON.stringify({ dependencies, healthResults, recommendations }, null, 2));
          return;
        }

        // Print results
        console.log(chalk.bold('\n' + '='.repeat(60)));
        console.log(chalk.bold(` Library Health Check: ${basename(options.addon)}`));
        console.log('='.repeat(60) + '\n');

        if (dependencies.length === 0) {
          console.log(chalk.gray('No dependencies declared in manifest.\n'));
        } else {
          console.log(chalk.bold('Declared Dependencies:\n'));
          for (const dep of dependencies) {
            const health = checkLibraryHealth(dep.name, dep.version);
            if (!health) {
              console.log(`  ${chalk.yellow('?')} ${dep.name} - Unknown library`);
              continue;
            }

            if (health.isDeprecated) {
              console.log(`  ${chalk.red('✗')} ${dep.name} - ${chalk.red('DEPRECATED')}`);
              if (health.replacement) {
                console.log(chalk.gray(`      Replace with: ${health.replacement}`));
              }
            } else if (health.isOutdated) {
              console.log(`  ${chalk.yellow('!')} ${dep.name} ${dep.version || '?'} → ${chalk.green(health.latestVersion)}`);
              if (health.esouiUrl) {
                console.log(chalk.gray(`      Update: ${health.esouiUrl}`));
              }
            } else {
              console.log(`  ${chalk.green('✓')} ${dep.name} ${dep.version || ''} - Up to date`);
            }
          }
        }

        if (recommendations.length > 0) {
          console.log(chalk.bold('\n\nLibrary Recommendations:\n'));
          for (const rec of recommendations) {
            console.log(`  ${chalk.cyan('→')} ${rec.description}`);
            console.log(chalk.gray(`      Consider: ${rec.library}`));
            console.log(chalk.gray(`      Benefit: ${rec.benefit}\n`));
          }
        }

      } catch (err) {
        spinner.stop();
        console.error(chalk.red(`Error: ${err}`));
        process.exit(1);
      }
    } else {
      // Show all known libraries
      const libraries = options.all
        ? LIBRARY_DATABASE
        : LIBRARY_DATABASE.filter(l => l.maintained);

      if (options.json) {
        console.log(JSON.stringify(libraries, null, 2));
        return;
      }

      console.log(chalk.bold('\n' + '='.repeat(60)));
      console.log(chalk.bold(' ESO Addon Library Database'));
      console.log('='.repeat(60) + '\n');

      console.log(`Known libraries: ${chalk.green(libraries.length)}`);
      if (!options.all) {
        console.log(chalk.gray('(Use --all to include deprecated libraries)\n'));
      }

      // Group by category
      type LibInfo = typeof libraries[number];
      const categories = new Map<string, LibInfo[]>();
      for (const lib of libraries) {
        const cat = lib.purpose.includes('DEPRECATED') ? 'Deprecated' :
          lib.purpose.includes('UI') || lib.purpose.includes('menu') || lib.purpose.includes('Settings') ? 'UI & Settings' :
          lib.purpose.includes('Inventory') || lib.purpose.includes('Trading') || lib.purpose.includes('filter') ? 'Inventory & Trading' :
          lib.purpose.includes('Map') || lib.purpose.includes('coordinate') ? 'Map & Location' :
          lib.purpose.includes('Combat') || lib.purpose.includes('Group') ? 'Combat & Group' :
          'Utilities';

        if (!categories.has(cat)) {
          categories.set(cat, []);
        }
        categories.get(cat)!.push(lib);
      }

      for (const [category, libs] of categories) {
        console.log(chalk.bold(`\n${category}:`));
        console.log('-'.repeat(40));
        for (const lib of libs) {
          const status = lib.maintained ? chalk.green('✓') : chalk.red('✗');
          const version = chalk.gray(`v${lib.latestVersion}`);
          console.log(`  ${status} ${lib.name} ${version}`);
          console.log(chalk.gray(`      Global: ${lib.globalVariable} | ${lib.purpose}`));
          if (lib.esouiId) {
            console.log(chalk.gray(`      ESOUI: https://www.esoui.com/downloads/info${lib.esouiId}`));
          }
        }
      }

      console.log(chalk.bold('\n\nQuick Reference:'));
      console.log('-'.repeat(40));
      console.log('  Check addon: eso-addon-fixer libraries -a /path/to/addon');
      console.log('  Show all:    eso-addon-fixer libraries --all\n');
    }
  });

// ============================================================================
// Info Command
// ============================================================================

program
  .command('info')
  .description('Show ESO API version information')
  .action(() => {
    console.log(chalk.bold('\n' + '='.repeat(60)));
    console.log(chalk.bold(' ESO API Version Information'));
    console.log('='.repeat(60) + '\n');

    console.log(`Current Live API Version: ${chalk.green(CURRENT_LIVE_API)}`);
    console.log(`Current PTS API Version: ${chalk.yellow(CURRENT_PTS_API)}`);

    console.log(chalk.bold('\n--- Significant API Changes ---\n'));

    for (const info of API_VERSION_HISTORY) {
      const label = info.isLive ? chalk.green('[LIVE]') :
        info.isPTS ? chalk.yellow('[PTS]') : chalk.gray('[OLD]');

      console.log(`  ${chalk.cyan(info.version)} ${label} - ${info.update}`);
      for (const change of info.significantChanges) {
        console.log(chalk.gray(`    - ${change}`));
      }
      console.log();
    }
  });

// ============================================================================
// Export Command
// ============================================================================

program
  .command('export')
  .description('Export migration database to JSON')
  .option('-o, --output <file>', 'Output file path', 'migrations.json')
  .action(async (options: { output: string }) => {
    const data = {
      apiVersions: API_VERSION_HISTORY,
      functionMigrations: FUNCTION_MIGRATIONS,
      libraryMigrations: LIBRARY_MIGRATIONS,
      addonRecommendations: ADDON_RECOMMENDATIONS,
    };

    const { writeFile } = await import('node:fs/promises');
    await writeFile(options.output, JSON.stringify(data, null, 2));
    console.log(chalk.green(`Exported to ${options.output}`));
  });

// ============================================================================
// Helpers
// ============================================================================

function getSeverityColor(severity: IssueSeverity): (text: string) => string {
  switch (severity) {
    case 'error':
      return chalk.red;
    case 'warning':
      return chalk.yellow;
    case 'info':
      return chalk.blue;
    default:
      return chalk.white;
  }
}

async function findLuaFiles(dirPath: string): Promise<string[]> {
  const files: string[] = [];

  const processDir = async (dir: string): Promise<void> => {
    const entries = await readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = join(dir, entry.name);
      if (entry.isDirectory() && !entry.name.includes('_backup_')) {
        await processDir(fullPath);
      } else if (entry.isFile() && extname(entry.name).toLowerCase() === '.lua') {
        files.push(fullPath);
      }
    }
  };

  await processDir(dirPath);
  return files;
}

// ============================================================================
// Main
// ============================================================================

program.parse();
