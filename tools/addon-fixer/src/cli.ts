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
import {
  ADDON_COMPATIBILITY_DB,
  getAddonsByCategory,
  getAddonsByStatus,
  getAddonSuite,
  getAddonInfo,
  getCategories,
  getCompatibilityStats,
  type AddonStatus,
} from './addon-compat-db.js';
import {
  scrapeAddonInfo,
  scrapeMultipleAddons,
  checkForUpdates,
  analyzeChangelog,
  generateUpdateReport,
  type ScrapedAddonInfo,
} from './esoui-scraper.js';
import {
  ADDON_DATA_APIS,
  findDataSynergies,
  getAddonsByDataType,
  getIntegrationSuggestions,
  getAddonDataAPI,
  getDataDependencyGraph,
} from './addon-data-apis.js';
import {
  COMMON_BUGS,
  BEST_PRACTICES,
  OPTIMIZATION_PATTERNS,
  API_DEPRECATION_TIMELINE,
  getBugsByCategory,
  getBugsBySeverity,
  getPracticesByCategory,
  getDocStats,
} from './eso-addon-guide.js';
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
// Addons Command (Compatibility Database)
// ============================================================================

program
  .command('addons')
  .description('Browse addon compatibility database')
  .option('-c, --category <category>', 'Filter by category (combat, ui, inventory, trading, maps, etc.)')
  .option('-s, --status <status>', 'Filter by status (working, needs_update, broken, deprecated)')
  .option('--suite <name>', 'Show all addons in a suite (e.g., "Personal Assistant")')
  .option('-n, --name <name>', 'Get info for a specific addon')
  .option('--stats', 'Show compatibility statistics')
  .option('--json', 'Output as JSON')
  .action((options: {
    category?: string;
    status?: string;
    suite?: string;
    name?: string;
    stats?: boolean;
    json?: boolean;
  }) => {
    // Get specific addon info
    if (options.name) {
      const addon = getAddonInfo(options.name);
      if (!addon) {
        console.log(chalk.red(`Addon not found: ${options.name}`));
        console.log(chalk.gray('Use "eso-addon-fixer addons" to see all tracked addons'));
        process.exit(1);
      }

      if (options.json) {
        console.log(JSON.stringify(addon, null, 2));
        return;
      }

      console.log(chalk.bold('\n' + '='.repeat(60)));
      console.log(chalk.bold(` ${addon.name}`));
      console.log('='.repeat(60) + '\n');

      const statusColor = addon.status === 'working' ? chalk.green :
        addon.status === 'needs_update' ? chalk.yellow :
        addon.status === 'broken' ? chalk.red :
        addon.status === 'deprecated' ? chalk.gray : chalk.white;

      console.log(`Status: ${statusColor(addon.status.toUpperCase())}`);
      console.log(`Category: ${addon.category}`);
      console.log(`Author: ${addon.author}`);
      console.log(`Description: ${addon.description}`);
      if (addon.esouiId) {
        console.log(`ESOUI: https://www.esoui.com/downloads/info${addon.esouiId}`);
      }
      if (addon.suite) {
        console.log(`Suite: ${addon.suite}`);
      }
      if (addon.dependencies?.length) {
        console.log(`Dependencies: ${addon.dependencies.join(', ')}`);
      }
      if (addon.issues?.length) {
        console.log(chalk.yellow('\nKnown Issues:'));
        for (const issue of addon.issues) {
          console.log(chalk.yellow(`  - ${issue}`));
        }
      }
      if (addon.fixInstructions?.length) {
        console.log(chalk.cyan('\nFix Instructions:'));
        for (const instruction of addon.fixInstructions) {
          console.log(chalk.cyan(`  - ${instruction}`));
        }
      }
      if (addon.alternative) {
        console.log(chalk.green(`\nAlternative: ${addon.alternative}`));
      }
      if (addon.notes) {
        console.log(chalk.gray(`\nNotes: ${addon.notes}`));
      }
      console.log(chalk.gray(`\nLast verified: ${addon.lastVerified}`));
      return;
    }

    // Show statistics
    if (options.stats) {
      const stats = getCompatibilityStats();

      if (options.json) {
        console.log(JSON.stringify(stats, null, 2));
        return;
      }

      console.log(chalk.bold('\n' + '='.repeat(60)));
      console.log(chalk.bold(' Addon Compatibility Statistics'));
      console.log('='.repeat(60) + '\n');

      console.log(`Total tracked: ${chalk.bold(stats.total)}`);
      console.log(`${chalk.green('✓')} Working: ${stats.working} (${Math.round(stats.working / stats.total * 100)}%)`);
      console.log(`${chalk.yellow('!')} Needs Update: ${stats.needsUpdate}`);
      console.log(`${chalk.red('✗')} Broken: ${stats.broken}`);
      console.log(`${chalk.gray('○')} Deprecated: ${stats.deprecated}`);

      console.log(chalk.bold('\n\nCategories:\n'));
      for (const cat of getCategories()) {
        const count = getAddonsByCategory(cat).length;
        console.log(`  ${cat}: ${count} addons`);
      }
      return;
    }

    // Filter addons
    let addons = [...ADDON_COMPATIBILITY_DB];

    if (options.category) {
      addons = getAddonsByCategory(options.category);
      if (addons.length === 0) {
        console.log(chalk.yellow(`No addons found in category: ${options.category}`));
        console.log(chalk.gray(`Available categories: ${getCategories().join(', ')}`));
        return;
      }
    }

    if (options.status) {
      addons = getAddonsByStatus(options.status as AddonStatus);
      if (addons.length === 0) {
        console.log(chalk.yellow(`No addons found with status: ${options.status}`));
        return;
      }
    }

    if (options.suite) {
      addons = getAddonSuite(options.suite);
      if (addons.length === 0) {
        console.log(chalk.yellow(`No addons found in suite: ${options.suite}`));
        return;
      }
    }

    if (options.json) {
      console.log(JSON.stringify(addons, null, 2));
      return;
    }

    // Display addons
    console.log(chalk.bold('\n' + '='.repeat(60)));
    console.log(chalk.bold(' ESO Addon Compatibility Database'));
    console.log('='.repeat(60) + '\n');

    const stats = getCompatibilityStats();
    console.log(`Tracked: ${stats.total} addons | ` +
      `${chalk.green(stats.working + ' working')} | ` +
      `${chalk.yellow(stats.needsUpdate + ' need update')} | ` +
      `${chalk.gray(stats.deprecated + ' deprecated')}\n`);

    // Group by category
    const byCategory = new Map<string, typeof addons>();
    for (const addon of addons) {
      if (!byCategory.has(addon.category)) {
        byCategory.set(addon.category, []);
      }
      byCategory.get(addon.category)!.push(addon);
    }

    for (const [category, categoryAddons] of byCategory) {
      console.log(chalk.bold(`\n${category}:`));
      console.log('-'.repeat(40));

      for (const addon of categoryAddons) {
        const statusIcon = addon.status === 'working' ? chalk.green('✓') :
          addon.status === 'needs_update' ? chalk.yellow('!') :
          addon.status === 'broken' ? chalk.red('✗') :
          addon.status === 'deprecated' ? chalk.gray('○') : chalk.gray('?');

        const suiteTag = addon.suite ? chalk.cyan(` [${addon.suite}]`) : '';

        console.log(`  ${statusIcon} ${addon.name}${suiteTag}`);
        console.log(chalk.gray(`      ${addon.description}`));
        if (addon.status === 'deprecated' && addon.alternative) {
          console.log(chalk.gray(`      Alternative: ${addon.alternative}`));
        }
      }
    }

    console.log(chalk.bold('\n\nQuick Reference:'));
    console.log('-'.repeat(40));
    console.log('  Get addon info:    eso-addon-fixer addons -n "Combat Metrics"');
    console.log('  Filter by status:  eso-addon-fixer addons -s needs_update');
    console.log('  Filter by category: eso-addon-fixer addons -c trading');
    console.log('  Show suite:        eso-addon-fixer addons --suite "Personal Assistant"');
    console.log('  Show stats:        eso-addon-fixer addons --stats\n');
  });

// ============================================================================
// Sync Command
// ============================================================================

program
  .command('sync')
  .description('Sync library versions from ESOUI.com')
  .option('--dry-run', 'Show what would be updated without making changes')
  .option('--check', 'Check if versions are outdated (for CI)')
  .option('--json', 'Output results as JSON')
  .action(async (options: { dryRun?: boolean; check?: boolean; json?: boolean }) => {
    const spinner = ora('Fetching library versions from ESOUI...').start();

    const librariesWithIds = LIBRARY_DATABASE.filter(l => l.esouiId);
    const results: Array<{
      library: string;
      current: string;
      fetched: string;
      isOutdated: boolean;
      error?: string;
    }> = [];

    spinner.text = `Checking ${librariesWithIds.length} libraries...`;

    for (const lib of librariesWithIds) {
      spinner.text = `Fetching ${lib.name}...`;

      try {
        const response = await fetch(
          `https://www.esoui.com/downloads/info${lib.esouiId}.html`,
          { headers: { 'User-Agent': 'ESO-Addon-Fixer/1.0' } }
        );

        if (response.ok) {
          const html = await response.text();
          const versionMatch = html.match(/Version:\s*([^\s<]+)/i);
          const fetched = versionMatch?.[1] || 'unknown';

          results.push({
            library: lib.name,
            current: lib.latestVersion,
            fetched,
            isOutdated: fetched !== 'unknown' && fetched !== lib.latestVersion,
          });
        } else {
          results.push({
            library: lib.name,
            current: lib.latestVersion,
            fetched: 'unknown',
            isOutdated: false,
            error: `HTTP ${response.status}`,
          });
        }
      } catch (err) {
        results.push({
          library: lib.name,
          current: lib.latestVersion,
          fetched: 'unknown',
          isOutdated: false,
          error: String(err),
        });
      }

      // Rate limiting
      await new Promise(resolve => setTimeout(resolve, 300));
    }

    spinner.stop();

    if (options.json) {
      console.log(JSON.stringify(results, null, 2));
      return;
    }

    const outdated = results.filter(r => r.isOutdated);
    const errors = results.filter(r => r.error);

    console.log(chalk.bold('\n' + '='.repeat(60)));
    console.log(chalk.bold(' Library Version Sync'));
    console.log('='.repeat(60) + '\n');

    console.log(`Checked: ${results.length} libraries`);
    console.log(`Outdated: ${outdated.length}`);
    console.log(`Errors: ${errors.length}\n`);

    if (outdated.length > 0) {
      console.log(chalk.bold('Outdated Libraries:\n'));
      for (const r of outdated) {
        console.log(`  ${chalk.yellow('!')} ${r.library}`);
        console.log(chalk.gray(`      ${r.current} → ${chalk.green(r.fetched)}`));
      }

      if (!options.dryRun) {
        console.log(chalk.bold('\n\nUpdate library-db.ts with:\n'));
        for (const r of outdated) {
          console.log(`  ${r.library}:`);
          console.log(chalk.gray(`    latestVersion: '${r.fetched}'`));
          console.log(chalk.gray(`    lastUpdated: '${new Date().toISOString().split('T')[0]}'`));
        }
      }
    } else {
      console.log(chalk.green('✓ All library versions are up to date!'));
    }

    if (errors.length > 0) {
      console.log(chalk.bold('\n\nFetch Errors:\n'));
      for (const r of errors) {
        console.log(`  ${chalk.red('✗')} ${r.library}: ${r.error}`);
      }
    }

    if (options.check && outdated.length > 0) {
      process.exit(1);
    }
  });

// ============================================================================
// Scrape Command
// ============================================================================

program
  .command('scrape')
  .description('Scrape addon info and changelogs from ESOUI.com')
  .option('-i, --id <id>', 'Scrape a single addon by ESOUI ID')
  .option('--check-updates', 'Check tracked addons for updates')
  .option('--report', 'Generate an update report')
  .option('--category <category>', 'Check addons in a specific category')
  .option('--json', 'Output as JSON')
  .action(async (options: {
    id?: string;
    checkUpdates?: boolean;
    report?: boolean;
    category?: string;
    json?: boolean;
  }) => {
    const spinner = ora('Scraping ESOUI...').start();

    try {
      // Scrape single addon
      if (options.id) {
        const esouiId = parseInt(options.id, 10);
        spinner.text = `Fetching addon ${esouiId}...`;
        const info = await scrapeAddonInfo(esouiId);

        spinner.stop();

        if (!info) {
          console.log(chalk.red(`Failed to fetch addon ${esouiId}`));
          process.exit(1);
        }

        if (options.json) {
          console.log(JSON.stringify(info, null, 2));
          return;
        }

        console.log(chalk.bold('\n' + '='.repeat(60)));
        console.log(chalk.bold(` ${info.name}`));
        console.log('='.repeat(60) + '\n');

        console.log(`ESOUI ID: ${info.esouiId}`);
        console.log(`Author: ${info.author}`);
        console.log(`Version: ${chalk.green(info.currentVersion)}`);
        console.log(`Last Updated: ${info.lastUpdated}`);
        console.log(`Downloads: ${info.downloads.toLocaleString()}`);
        console.log(`Favorites: ${info.favorites.toLocaleString()}`);
        if (info.apiVersion) {
          console.log(`API Version: ${info.apiVersion}`);
        }
        if (info.categories.length > 0) {
          console.log(`Categories: ${info.categories.join(', ')}`);
        }
        if (info.dependencies.length > 0) {
          console.log(`Dependencies: ${info.dependencies.join(', ')}`);
        }
        if (info.optionalDeps.length > 0) {
          console.log(`Optional: ${info.optionalDeps.join(', ')}`);
        }

        if (info.description) {
          console.log(chalk.bold('\nDescription:'));
          console.log(chalk.gray(info.description));
        }

        if (info.changelog) {
          console.log(chalk.bold('\nChangelog Analysis:'));
          const analysis = analyzeChangelog(info.changelog);
          if (analysis.mentionsBreakingChange) {
            console.log(chalk.red('  ⚠️  Breaking changes mentioned'));
          }
          if (analysis.mentionsApiChange) {
            console.log(chalk.yellow('  🔄 API-related changes'));
          }
          if (analysis.mentionsBugFix) {
            console.log(chalk.green('  🐛 Bug fixes'));
          }
          if (analysis.mentionsNewFeature) {
            console.log(chalk.cyan('  ✨ New features'));
          }
          if (analysis.mentionsLibrary.length > 0) {
            console.log(chalk.blue(`  📚 Libraries: ${analysis.mentionsLibrary.join(', ')}`));
          }
          if (analysis.keywords.length > 0) {
            console.log(chalk.gray(`  Keywords: ${analysis.keywords.join(', ')}`));
          }
        }

        if (info.versionHistory.length > 0) {
          console.log(chalk.bold('\nRecent Version History:'));
          for (const v of info.versionHistory.slice(0, 5)) {
            console.log(`  ${chalk.cyan(v.version)} (${v.date})`);
            for (const line of v.changelog.slice(0, 3)) {
              console.log(chalk.gray(`    - ${line}`));
            }
            if (v.changelog.length > 3) {
              console.log(chalk.gray(`    ... and ${v.changelog.length - 3} more`));
            }
          }
        }

        return;
      }

      // Check tracked addons for updates
      if (options.checkUpdates || options.report) {
        let addonsToCheck = ADDON_COMPATIBILITY_DB.filter(a => a.esouiId);

        if (options.category) {
          addonsToCheck = addonsToCheck.filter(a =>
            a.category.toLowerCase() === options.category!.toLowerCase()
          );
        }

        spinner.text = `Checking ${addonsToCheck.length} addons for updates...`;

        const checksToPerform = addonsToCheck.map(a => ({
          esouiId: a.esouiId,
          name: a.name,
          knownVersion: 'unknown', // We don't track versions yet
        }));

        const results: ScrapedAddonInfo[] = [];
        let checked = 0;

        for (const addon of addonsToCheck) {
          spinner.text = `Checking ${addon.name} (${++checked}/${addonsToCheck.length})...`;
          const info = await scrapeAddonInfo(addon.esouiId);
          if (info) {
            results.push(info);
          }
          // Rate limiting
          await new Promise(resolve => setTimeout(resolve, 500));
        }

        spinner.stop();

        if (options.json) {
          console.log(JSON.stringify(results, null, 2));
          return;
        }

        if (options.report) {
          // Generate markdown report
          console.log(chalk.bold('# ESO Addon Status Report'));
          console.log(`Generated: ${new Date().toISOString()}\n`);
          console.log(`Total scraped: ${results.length} addons\n`);

          // Group by update recency
          const now = new Date();
          const recentlyUpdated = results.filter(r => {
            const date = new Date(r.lastUpdated);
            return (now.getTime() - date.getTime()) < 30 * 24 * 60 * 60 * 1000;
          });
          const notRecentlyUpdated = results.filter(r => {
            const date = new Date(r.lastUpdated);
            return (now.getTime() - date.getTime()) >= 30 * 24 * 60 * 60 * 1000;
          });

          console.log(chalk.bold('## Recently Updated (last 30 days):\n'));
          for (const r of recentlyUpdated) {
            const analysis = analyzeChangelog(r.changelog);
            console.log(`### ${r.name}`);
            console.log(`- Version: ${r.currentVersion}`);
            console.log(`- Updated: ${r.lastUpdated}`);
            if (analysis.mentionsBreakingChange) {
              console.log(chalk.red('- ⚠️ Breaking changes!'));
            }
            console.log();
          }

          if (notRecentlyUpdated.length > 0) {
            console.log(chalk.bold('\n## Not Updated Recently:\n'));
            for (const r of notRecentlyUpdated.slice(0, 20)) {
              console.log(`- ${r.name}: ${r.currentVersion} (${r.lastUpdated})`);
            }
          }
          return;
        }

        // Normal output
        console.log(chalk.bold('\n' + '='.repeat(60)));
        console.log(chalk.bold(' ESOUI Addon Status'));
        console.log('='.repeat(60) + '\n');

        console.log(`Scraped: ${results.length} addons\n`);

        // Sort by last updated
        results.sort((a, b) => {
          const dateA = new Date(a.lastUpdated).getTime() || 0;
          const dateB = new Date(b.lastUpdated).getTime() || 0;
          return dateB - dateA;
        });

        for (const info of results.slice(0, 20)) {
          const analysis = analyzeChangelog(info.changelog);
          const flags: string[] = [];

          if (analysis.mentionsBreakingChange) flags.push(chalk.red('⚠️'));
          if (analysis.mentionsApiChange) flags.push(chalk.yellow('🔄'));

          console.log(`${chalk.cyan(info.name)} v${info.currentVersion} ${flags.join(' ')}`);
          console.log(chalk.gray(`  Updated: ${info.lastUpdated} | Downloads: ${info.downloads.toLocaleString()}`));
        }

        if (results.length > 20) {
          console.log(chalk.gray(`\n... and ${results.length - 20} more`));
        }

        return;
      }

      // Default: show help
      spinner.stop();
      console.log(chalk.bold('\nESO Addon Scraper'));
      console.log('-'.repeat(40));
      console.log('  Scrape single addon:  eso-addon-fixer scrape -i 1245');
      console.log('  Check for updates:    eso-addon-fixer scrape --check-updates');
      console.log('  Generate report:      eso-addon-fixer scrape --report');
      console.log('  Filter by category:   eso-addon-fixer scrape --check-updates --category combat');

    } catch (error) {
      spinner.fail('Scraping failed');
      console.error(chalk.red(`Error: ${error}`));
      process.exit(1);
    }
  });

// ============================================================================
// Synergy Command (Addon Collaborator)
// ============================================================================

program
  .command('synergy')
  .description('Explore addon data sharing and synergy opportunities')
  .option('-a, --addon <name>', 'Show data API for a specific addon')
  .option('-t, --type <type>', 'Show addons by data type (combat, price, inventory, location, crafting, ui)')
  .option('--synergies', 'Show all identified synergy opportunities')
  .option('--graph', 'Show data dependency graph')
  .option('--json', 'Output as JSON')
  .action((options: {
    addon?: string;
    type?: string;
    synergies?: boolean;
    graph?: boolean;
    json?: boolean;
  }) => {
    // Show specific addon's data API
    if (options.addon) {
      const api = getAddonDataAPI(options.addon);
      if (!api) {
        console.log(chalk.red(`Addon not found: ${options.addon}`));
        console.log(chalk.gray('Use "eso-addon-fixer synergy" to see all tracked addons'));
        process.exit(1);
      }

      if (options.json) {
        console.log(JSON.stringify(api, null, 2));
        return;
      }

      console.log(chalk.bold('\n' + '='.repeat(60)));
      console.log(chalk.bold(` ${api.name} - Data API`));
      console.log('='.repeat(60) + '\n');

      console.log(`Primary Function: ${api.primaryFunction}`);
      console.log(`ESOUI: https://www.esoui.com/downloads/info${api.esouiId}`);
      if (api.globalNamespace) {
        console.log(`Global Namespace: ${chalk.cyan(api.globalNamespace)}`);
      }

      console.log(chalk.bold('\nExposed Data:'));
      for (const data of api.exposedData) {
        console.log(`\n  ${chalk.green(data.name)}`);
        console.log(chalk.gray(`    Access: ${data.accessMethod} via ${data.accessPath}`));
        console.log(chalk.gray(`    Type: ${data.dataType}`));
        console.log(chalk.gray(`    ${data.description}`));
        if (data.exampleCode) {
          console.log(chalk.cyan(`    Example: ${data.exampleCode}`));
        }
        console.log(chalk.gray(`    Realtime: ${data.realtime} | Update: ${data.updateFrequency || 'n/a'}`));
      }

      console.log(chalk.bold('\nConsumes From:'));
      console.log(`  ${api.consumesFrom.join(', ') || 'None'}`);

      console.log(chalk.bold('\nKnown Integrations:'));
      console.log(`  ${api.knownIntegrations.join(', ') || 'None'}`);

      if (api.notes) {
        console.log(chalk.bold('\nNotes:'));
        console.log(chalk.gray(`  ${api.notes}`));
      }

      // Show synergy suggestions
      const synergies = getIntegrationSuggestions(api.name);
      if (synergies.length > 0) {
        console.log(chalk.bold('\nSynergy Opportunities:'));
        for (const s of synergies) {
          const partner = s.sourceAddon === api.name ? s.targetAddon : s.sourceAddon;
          console.log(`  ${chalk.yellow('→')} ${partner} (${s.synergyType})`);
          console.log(chalk.gray(`    ${s.description}`));
        }
      }

      return;
    }

    // Show addons by data type
    if (options.type) {
      const validTypes = ['combat', 'price', 'inventory', 'location', 'crafting', 'ui'];
      if (!validTypes.includes(options.type)) {
        console.log(chalk.red(`Invalid type: ${options.type}`));
        console.log(chalk.gray(`Valid types: ${validTypes.join(', ')}`));
        process.exit(1);
      }

      const addons = getAddonsByDataType(options.type as 'combat' | 'price' | 'inventory' | 'location' | 'crafting' | 'ui');

      if (options.json) {
        console.log(JSON.stringify(addons, null, 2));
        return;
      }

      console.log(chalk.bold(`\nAddons providing ${options.type} data:\n`));
      for (const addon of addons) {
        console.log(`  ${chalk.cyan(addon.name)}`);
        console.log(chalk.gray(`    ${addon.primaryFunction}`));
        console.log(chalk.gray(`    Data points: ${addon.exposedData.length}`));
      }
      return;
    }

    // Show all synergies
    if (options.synergies) {
      const synergies = findDataSynergies();

      if (options.json) {
        console.log(JSON.stringify(synergies, null, 2));
        return;
      }

      console.log(chalk.bold('\n' + '='.repeat(60)));
      console.log(chalk.bold(' Addon Data Synergy Opportunities'));
      console.log('='.repeat(60) + '\n');

      // Group by synergy type
      const byType = new Map<string, typeof synergies>();
      for (const s of synergies) {
        if (!byType.has(s.synergyType)) {
          byType.set(s.synergyType, []);
        }
        byType.get(s.synergyType)!.push(s);
      }

      for (const [type, typeSynergies] of byType) {
        const typeLabel = type === 'correlation' ? '📊 Correlation' :
          type === 'enhancement' ? '✨ Enhancement' :
          type === 'automation' ? '⚙️  Automation' :
          type === 'aggregation' ? '📦 Aggregation' : type;

        console.log(chalk.bold(`\n${typeLabel}:`));
        console.log('-'.repeat(40));

        for (const s of typeSynergies) {
          const complexity = s.implementationComplexity === 'low' ? chalk.green('●') :
            s.implementationComplexity === 'medium' ? chalk.yellow('●') :
            chalk.red('●');

          console.log(`  ${complexity} ${s.sourceAddon} + ${s.targetAddon}`);
          console.log(chalk.gray(`    ${s.description}`));
          console.log(chalk.gray(`    Data: ${s.dataPoint}`));
        }
      }

      console.log(chalk.bold('\n\nComplexity Legend:'));
      console.log(`  ${chalk.green('●')} Low | ${chalk.yellow('●')} Medium | ${chalk.red('●')} High`);
      return;
    }

    // Show dependency graph
    if (options.graph) {
      const graph = getDataDependencyGraph();

      if (options.json) {
        const obj: Record<string, string[]> = {};
        for (const [key, value] of graph) {
          obj[key] = Array.from(value);
        }
        console.log(JSON.stringify(obj, null, 2));
        return;
      }

      console.log(chalk.bold('\n' + '='.repeat(60)));
      console.log(chalk.bold(' Addon Data Dependency Graph'));
      console.log('='.repeat(60) + '\n');

      for (const [addon, deps] of graph) {
        if (deps.size > 0) {
          console.log(`${chalk.cyan(addon)}`);
          for (const dep of deps) {
            console.log(chalk.gray(`  └─ ${dep}`));
          }
        }
      }
      return;
    }

    // Default: show all tracked addons
    if (options.json) {
      console.log(JSON.stringify(ADDON_DATA_APIS, null, 2));
      return;
    }

    console.log(chalk.bold('\n' + '='.repeat(60)));
    console.log(chalk.bold(' Addon Data API Registry'));
    console.log('='.repeat(60) + '\n');

    console.log(`Tracked addons: ${chalk.green(ADDON_DATA_APIS.length)}`);
    console.log(`Total data points: ${chalk.green(ADDON_DATA_APIS.reduce((sum, a) => sum + a.exposedData.length, 0))}`);
    console.log(`Synergy opportunities: ${chalk.green(findDataSynergies().length)}\n`);

    // Group by category
    const categories: Record<string, typeof ADDON_DATA_APIS[number][]> = {
      'Combat & DPS': [],
      'Inventory & Trading': [],
      'Map & Location': [],
      'Crafting': [],
      'Group & Raiding': [],
      'UI & Quality of Life': [],
      'Builds & Sets': [],
    };

    for (const addon of ADDON_DATA_APIS) {
      const cat =
        addon.name.includes('Combat') || addon.name.includes('FTC') || addon.name.includes('Notifier') || addon.name.includes('Hodor') ? 'Combat & DPS' :
        addon.name.includes('Merchant') || addon.name.includes('Trade') || addon.name.includes('Inventory') || addon.name.includes('Arkadius') ? 'Inventory & Trading' :
        addon.name.includes('Harvest') || addon.name.includes('Destination') ? 'Map & Location' :
        addon.name.includes('Writ') || addon.name.includes('Potion') ? 'Crafting' :
        addon.name.includes('Raid') || addon.name.includes('Hodor') ? 'Group & Raiding' :
        addon.name.includes('Dressing') || addon.name.includes('IIfA') ? 'Builds & Sets' :
        'UI & Quality of Life';

      if (!categories[cat]) categories[cat] = [];
      categories[cat].push(addon);
    }

    for (const [category, addons] of Object.entries(categories)) {
      if (addons.length === 0) continue;
      console.log(chalk.bold(`\n${category}:`));
      console.log('-'.repeat(40));
      for (const addon of addons) {
        const dataCount = addon.exposedData.length;
        console.log(`  ${chalk.cyan(addon.name)} (${dataCount} data points)`);
        console.log(chalk.gray(`    ${addon.primaryFunction}`));
      }
    }

    console.log(chalk.bold('\n\nQuick Reference:'));
    console.log('-'.repeat(40));
    console.log('  View addon API:       eso-addon-fixer synergy -a "Combat Metrics"');
    console.log('  Find by data type:    eso-addon-fixer synergy -t combat');
    console.log('  Show all synergies:   eso-addon-fixer synergy --synergies');
    console.log('  Show dependency graph: eso-addon-fixer synergy --graph\n');
  });

// ============================================================================
// Guide Command (ESO Addon Development Guide)
// ============================================================================

program
  .command('guide')
  .description('ESO addon development guide - bugs, best practices, optimizations')
  .option('-b, --bugs [category]', 'Show common bugs (memory, events, api, ui, savedvars, threading)')
  .option('-p, --practices [category]', 'Show best practices (performance, maintainability, compatibility, ux, security)')
  .option('-o, --optimizations', 'Show performance optimization patterns')
  .option('-a, --api', 'Show API deprecation timeline')
  .option('-s, --severity <level>', 'Filter bugs by severity (critical, major, minor)')
  .option('--stats', 'Show documentation statistics')
  .option('--json', 'Output as JSON')
  .action((options: {
    bugs?: boolean | string;
    practices?: boolean | string;
    optimizations?: boolean;
    api?: boolean;
    severity?: string;
    stats?: boolean;
    json?: boolean;
  }) => {
    // Show stats
    if (options.stats) {
      const stats = getDocStats();

      if (options.json) {
        console.log(JSON.stringify(stats, null, 2));
        return;
      }

      console.log(chalk.bold('\n' + '='.repeat(60)));
      console.log(chalk.bold(' ESO Addon Development Guide - Statistics'));
      console.log('='.repeat(60) + '\n');

      console.log(`Total documented bugs: ${chalk.red(stats.totalBugs)} (${chalk.red(stats.criticalBugs)} critical)`);
      console.log(`Best practices: ${chalk.green(stats.totalPractices)}`);
      console.log(`Optimization patterns: ${chalk.cyan(stats.totalOptimizations)}`);
      console.log(`API changes documented: ${chalk.yellow(stats.apiChanges)}`);
      return;
    }

    // Show bugs
    if (options.bugs !== undefined) {
      let bugs = [...COMMON_BUGS];

      if (typeof options.bugs === 'string') {
        bugs = getBugsByCategory(options.bugs as 'memory' | 'events' | 'api' | 'ui' | 'savedvars' | 'threading');
        if (bugs.length === 0) {
          console.log(chalk.red(`Unknown category: ${options.bugs}`));
          console.log(chalk.gray('Valid categories: memory, events, api, ui, savedvars, threading'));
          return;
        }
      }

      if (options.severity) {
        bugs = getBugsBySeverity(options.severity as 'critical' | 'major' | 'minor');
      }

      if (options.json) {
        console.log(JSON.stringify(bugs, null, 2));
        return;
      }

      console.log(chalk.bold('\n' + '='.repeat(60)));
      console.log(chalk.bold(' Common ESO Addon Bugs'));
      console.log('='.repeat(60) + '\n');

      for (const bug of bugs) {
        const severityColor = bug.severity === 'critical' ? chalk.red :
          bug.severity === 'major' ? chalk.yellow : chalk.blue;

        console.log(`${severityColor(`[${bug.severity.toUpperCase()}]`)} ${chalk.bold(bug.id)}: ${bug.title}`);
        console.log(chalk.gray(`  Category: ${bug.category}`));
        console.log(`  ${bug.description}\n`);
        console.log(chalk.yellow('  Symptoms:'));
        for (const symptom of bug.symptoms) {
          console.log(`    - ${symptom}`);
        }
        console.log(chalk.red(`\n  Cause: ${bug.cause}`));
        console.log(chalk.green(`  Fix: ${bug.fix}`));

        if (bug.codeExample) {
          console.log(chalk.bold('\n  Example:'));
          console.log(chalk.red('  // Bad:'));
          for (const line of bug.codeExample.bad.split('\n').slice(0, 5)) {
            console.log(chalk.gray(`    ${line}`));
          }
          console.log(chalk.green('\n  // Good:'));
          for (const line of bug.codeExample.good.split('\n').slice(0, 5)) {
            console.log(chalk.gray(`    ${line}`));
          }
        }
        console.log('\n' + '-'.repeat(60) + '\n');
      }
      return;
    }

    // Show best practices
    if (options.practices !== undefined) {
      let practices = [...BEST_PRACTICES];

      if (typeof options.practices === 'string') {
        practices = getPracticesByCategory(options.practices as 'performance' | 'maintainability' | 'compatibility' | 'ux' | 'security');
        if (practices.length === 0) {
          console.log(chalk.red(`Unknown category: ${options.practices}`));
          console.log(chalk.gray('Valid categories: performance, maintainability, compatibility, ux, security'));
          return;
        }
      }

      if (options.json) {
        console.log(JSON.stringify(practices, null, 2));
        return;
      }

      console.log(chalk.bold('\n' + '='.repeat(60)));
      console.log(chalk.bold(' ESO Addon Best Practices'));
      console.log('='.repeat(60) + '\n');

      // Group by category
      const byCategory = new Map<string, typeof practices>();
      for (const p of practices) {
        if (!byCategory.has(p.category)) {
          byCategory.set(p.category, []);
        }
        byCategory.get(p.category)!.push(p);
      }

      for (const [category, catPractices] of byCategory) {
        console.log(chalk.bold(`\n${category.toUpperCase()}:`));
        console.log('-'.repeat(40));

        for (const p of catPractices) {
          console.log(`\n  ${chalk.cyan(p.id)}: ${chalk.bold(p.title)}`);
          console.log(`  ${p.description}`);
          console.log(chalk.gray(`  Why: ${p.rationale}`));
          if (p.codeExample) {
            console.log(chalk.green('\n  Example:'));
            for (const line of p.codeExample.split('\n').slice(0, 6)) {
              console.log(chalk.gray(`    ${line}`));
            }
          }
        }
      }
      return;
    }

    // Show optimizations
    if (options.optimizations) {
      if (options.json) {
        console.log(JSON.stringify(OPTIMIZATION_PATTERNS, null, 2));
        return;
      }

      console.log(chalk.bold('\n' + '='.repeat(60)));
      console.log(chalk.bold(' Performance Optimization Patterns'));
      console.log('='.repeat(60) + '\n');

      for (const opt of OPTIMIZATION_PATTERNS) {
        const impactColor = opt.impact === 'high' ? chalk.red :
          opt.impact === 'medium' ? chalk.yellow : chalk.blue;

        console.log(`${impactColor(`[${opt.impact.toUpperCase()} IMPACT]`)} ${chalk.bold(opt.id)}: ${opt.title}`);
        console.log(`  ${opt.description}\n`);

        console.log(chalk.red('  Before:'));
        for (const line of opt.before.split('\n').slice(0, 4)) {
          console.log(chalk.gray(`    ${line}`));
        }

        console.log(chalk.green('\n  After:'));
        for (const line of opt.after.split('\n').slice(0, 6)) {
          console.log(chalk.gray(`    ${line}`));
        }

        console.log(chalk.cyan(`\n  Explanation: ${opt.explanation}`));
        console.log('\n' + '-'.repeat(60) + '\n');
      }
      return;
    }

    // Show API timeline
    if (options.api) {
      if (options.json) {
        console.log(JSON.stringify(API_DEPRECATION_TIMELINE, null, 2));
        return;
      }

      console.log(chalk.bold('\n' + '='.repeat(60)));
      console.log(chalk.bold(' API Deprecation Timeline'));
      console.log('='.repeat(60) + '\n');

      for (const version of API_DEPRECATION_TIMELINE) {
        console.log(chalk.bold(`\nAPI ${version.apiVersion} - ${version.update} (${version.date})`));
        console.log('-'.repeat(50));

        for (const change of version.changes) {
          const typeColor = change.type === 'removed' ? chalk.red :
            change.type === 'deprecated' ? chalk.yellow :
            change.type === 'renamed' ? chalk.cyan : chalk.blue;

          console.log(`  ${typeColor(`[${change.type.toUpperCase()}]`)} ${change.item}`);
          if (change.replacement) {
            console.log(chalk.green(`    → ${change.replacement}`));
          }
          if (change.notes) {
            console.log(chalk.gray(`    Note: ${change.notes}`));
          }
        }
      }
      return;
    }

    // Default: show overview
    const stats = getDocStats();

    console.log(chalk.bold('\n' + '='.repeat(60)));
    console.log(chalk.bold(' ESO Addon Development Guide'));
    console.log('='.repeat(60) + '\n');

    console.log('A comprehensive guide to ESO addon development best practices,');
    console.log('common bugs and their solutions, and performance optimizations.\n');

    console.log(`Documented: ${chalk.red(stats.totalBugs + ' bugs')} | ` +
      `${chalk.green(stats.totalPractices + ' practices')} | ` +
      `${chalk.cyan(stats.totalOptimizations + ' optimizations')} | ` +
      `${chalk.yellow(stats.apiChanges + ' API changes')}\n`);

    console.log(chalk.bold('Quick Reference:'));
    console.log('-'.repeat(40));
    console.log('  Show all bugs:        eso-addon-fixer guide --bugs');
    console.log('  Memory bugs only:     eso-addon-fixer guide --bugs memory');
    console.log('  Critical bugs:        eso-addon-fixer guide --bugs --severity critical');
    console.log('  Best practices:       eso-addon-fixer guide --practices');
    console.log('  Performance tips:     eso-addon-fixer guide --practices performance');
    console.log('  Optimizations:        eso-addon-fixer guide --optimizations');
    console.log('  API timeline:         eso-addon-fixer guide --api');
    console.log('  Statistics:           eso-addon-fixer guide --stats\n');

    console.log(chalk.bold('Bug Categories:'));
    console.log(`  ${chalk.red('memory')}     - Memory leaks, unbounded growth, GC issues`);
    console.log(`  ${chalk.yellow('events')}    - Event handling, filtering, registration`);
    console.log(`  ${chalk.blue('api')}        - Deprecated functions, API changes`);
    console.log(`  ${chalk.cyan('ui')}         - UI creation, handlers, fonts`);
    console.log(`  ${chalk.green('savedvars')} - SavedVariables persistence issues`);
    console.log(`  ${chalk.magenta('threading')} - Async operations, blocking\n`);
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
