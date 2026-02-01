#!/usr/bin/env node
/**
 * ESO Addon Fixer CLI
 *
 * Command-line interface for analyzing and fixing broken ESO addons.
 */

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { AddonFixer, analyzeAddon, fixAddon } from './fixer.js';
import {
  API_VERSION_HISTORY,
  FUNCTION_MIGRATIONS,
  LIBRARY_MIGRATIONS,
  ADDON_RECOMMENDATIONS,
  getMigrationsByCategory,
  getMigrationsByVersion,
} from './migrations.js';
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

// ============================================================================
// Main
// ============================================================================

program.parse();
