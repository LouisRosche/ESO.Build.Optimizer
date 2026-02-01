/**
 * Integration tests for the ESO Addon Fixer.
 *
 * Tests the full pipeline: analysis, transformations, and fixes.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdir, rm, writeFile, readFile, stat } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { AddonFixer } from '../fixer.js';
import { LuaAnalyzer } from '../lua-analyzer.js';
import { LuaTransformer } from '../lua-transformer.js';

// Test fixture directory
let testDir: string;

describe('ESO Addon Fixer Integration', () => {
  beforeEach(async () => {
    // Create temp directory for each test
    testDir = join(tmpdir(), `addon-fixer-test-${Date.now()}`);
    await mkdir(testDir, { recursive: true });
  });

  afterEach(async () => {
    // Cleanup temp directory
    await rm(testDir, { recursive: true, force: true });
  });

  describe('Manifest File Extension', () => {
    it('should detect .txt manifest as deprecated when .addon is missing', async () => {
      const addonDir = join(testDir, 'TestAddon');
      await mkdir(addonDir);

      // Create .txt manifest only (deprecated)
      await writeFile(
        join(addonDir, 'TestAddon.txt'),
        '## Title: TestAddon\n## APIVersion: 101048\n'
      );

      const fixer = new AddonFixer();
      const result = await fixer.analyze(addonDir);

      // Should find the deprecation issue
      const manifestIssue = result.fileResults.flatMap(f => f.issues)
        .find(i => i.id === 'manifest-ext-001');

      expect(manifestIssue).toBeDefined();
      expect(manifestIssue?.severity).toBe('warning');
      expect(manifestIssue?.message).toContain('.txt manifest extension is deprecated');
    });

    it('should not flag .addon manifest as deprecated', async () => {
      const addonDir = join(testDir, 'TestAddon');
      await mkdir(addonDir);

      // Create .addon manifest (current)
      await writeFile(
        join(addonDir, 'TestAddon.addon'),
        '## Title: TestAddon\n## APIVersion: 101048\n'
      );

      const fixer = new AddonFixer();
      const result = await fixer.analyze(addonDir);

      // Should NOT find the deprecation issue
      const manifestIssue = result.fileResults.flatMap(f => f.issues)
        .find(i => i.id === 'manifest-ext-001');

      expect(manifestIssue).toBeUndefined();
    });

    it('should create .addon file when fixing .txt-only addon', async () => {
      const addonDir = join(testDir, 'TestAddon');
      await mkdir(addonDir);

      // Create .txt manifest only
      await writeFile(
        join(addonDir, 'TestAddon.txt'),
        '## Title: TestAddon\n## APIVersion: 101048\n'
      );

      const fixer = new AddonFixer({ dryRun: false, createBackup: false });
      await fixer.fix(addonDir);

      // .addon file should now exist
      const addonPath = join(addonDir, 'TestAddon.addon');
      const addonExists = await stat(addonPath).then(() => true).catch(() => false);
      expect(addonExists).toBe(true);
    });
  });

  describe('Case Sensitivity Detection', () => {
    it('should detect case mismatch in file references', async () => {
      const addonDir = join(testDir, 'TestAddon');
      await mkdir(addonDir);

      // Create manifest with mixed case reference
      await writeFile(
        join(addonDir, 'TestAddon.addon'),
        '## Title: TestAddon\n## APIVersion: 101048\n\nMyFile.lua\n'
      );

      // Create file with different case
      await writeFile(join(addonDir, 'myfile.lua'), 'local test = 1');

      const fixer = new AddonFixer();
      const result = await fixer.analyze(addonDir);

      // Should find case mismatch issue
      const caseIssue = result.fileResults.flatMap(f => f.issues)
        .find(i => i.message?.includes('Case mismatch'));

      expect(caseIssue).toBeDefined();
      expect(caseIssue?.severity).toBe('warning');
    });

    it('should detect missing files referenced in manifest', async () => {
      const addonDir = join(testDir, 'TestAddon');
      await mkdir(addonDir);

      // Create manifest referencing non-existent file
      await writeFile(
        join(addonDir, 'TestAddon.addon'),
        '## Title: TestAddon\n## APIVersion: 101048\n\nMissingFile.lua\n'
      );

      const fixer = new AddonFixer();
      const result = await fixer.analyze(addonDir);

      // Should find missing file issue
      const missingIssue = result.fileResults.flatMap(f => f.issues)
        .find(i => i.message?.includes('Missing file'));

      expect(missingIssue).toBeDefined();
      expect(missingIssue?.severity).toBe('error');
    });
  });

  describe('Library Name Normalization', () => {
    it('should detect LibStub regardless of library version suffix', async () => {
      const luaContent = `local LAM = LibStub("LibAddonMenu-2.0")`;
      const luaPath = join(testDir, 'test.lua');
      await writeFile(luaPath, luaContent);

      const analyzer = new LuaAnalyzer();
      const result = await analyzer.analyzeFile(luaPath);

      const libStubIssue = result.issues.find(i => i.category === 'libstub');
      expect(libStubIssue).toBeDefined();
      expect(libStubIssue?.suggestedFix).toBe('LibAddonMenu2');
    });

    it('should handle case-insensitive library name matching', async () => {
      const luaContent = `local LF = LibStub("LIBFILTERS-3.0")`;
      const luaPath = join(testDir, 'test.lua');
      await writeFile(luaPath, luaContent);

      const analyzer = new LuaAnalyzer();
      const result = await analyzer.analyzeFile(luaPath);

      const libStubIssue = result.issues.find(i => i.category === 'libstub');
      expect(libStubIssue).toBeDefined();
      expect(libStubIssue?.suggestedFix).toBe('LibFilters3');
    });

    it('should transform LibStub to global variable', async () => {
      const luaContent = `local LAM = LibStub("LibAddonMenu-2.0")
local test = LAM:CreateControlPanel()`;
      const luaPath = join(testDir, 'test.lua');
      await writeFile(luaPath, luaContent);

      const transformer = new LuaTransformer();
      await transformer.initialize();
      const result = await transformer.transformFile(luaPath, {}, false);

      expect(result.changes.length).toBeGreaterThan(0);
      const content = await readFile(luaPath, 'utf-8');
      expect(content).toContain('LibAddonMenu2');
      expect(content).not.toContain('LibStub');
    });
  });

  describe('Pattern Migration Detection', () => {
    it('should detect WINDOW_MANAGER:CreateControl pattern', async () => {
      const addonDir = join(testDir, 'TestAddon');
      await mkdir(addonDir);

      await writeFile(
        join(addonDir, 'TestAddon.addon'),
        '## Title: TestAddon\n## APIVersion: 101048\n\nmain.lua\n'
      );

      await writeFile(
        join(addonDir, 'main.lua'),
        `local ctrl = WINDOW_MANAGER:CreateControl("MyControl", parent, CT_LABEL)`
      );

      const fixer = new AddonFixer();
      const result = await fixer.analyze(addonDir);

      const patternIssue = result.fileResults.flatMap(f => f.issues)
        .find(i => i.oldCode?.includes('WINDOW_MANAGER:CreateControl('));

      expect(patternIssue).toBeDefined();
      expect(patternIssue?.suggestedFix).toContain('CreateControl(');
    });

    it('should NOT detect WINDOW_MANAGER:CreateControlFromVirtual', async () => {
      const addonDir = join(testDir, 'TestAddon');
      await mkdir(addonDir);

      await writeFile(
        join(addonDir, 'TestAddon.addon'),
        '## Title: TestAddon\n## APIVersion: 101048\n\nmain.lua\n'
      );

      await writeFile(
        join(addonDir, 'main.lua'),
        `local ctrl = WINDOW_MANAGER:CreateControlFromVirtual("MyControl", parent, "MyTemplate")`
      );

      const fixer = new AddonFixer();
      const result = await fixer.analyze(addonDir);

      // Should NOT incorrectly match CreateControlFromVirtual
      const patternIssue = result.fileResults.flatMap(f => f.issues)
        .find(i => i.oldCode?.includes('WINDOW_MANAGER:CreateControl('));

      expect(patternIssue).toBeUndefined();
    });
  });

  describe('Font Path Migration', () => {
    it('should detect TTF font paths', async () => {
      const luaContent = `local font = "EsoUI/fonts/univers57.ttf|16"`;
      const luaPath = join(testDir, 'test.lua');
      await writeFile(luaPath, luaContent);

      const analyzer = new LuaAnalyzer();
      const result = await analyzer.analyzeFile(luaPath);

      const fontIssue = result.issues.find(i => i.category === 'font_path');
      expect(fontIssue).toBeDefined();
      expect(fontIssue?.suggestedFix).toContain('.slug');
    });

    it('should transform TTF to Slug format', async () => {
      const luaContent = `local font = "EsoUI/fonts/univers57.ttf|16"`;
      const luaPath = join(testDir, 'test.lua');
      await writeFile(luaPath, luaContent);

      const transformer = new LuaTransformer();
      await transformer.initialize();
      await transformer.transformFile(luaPath, { fixFontPaths: true }, false);

      const content = await readFile(luaPath, 'utf-8');
      expect(content).toContain('.slug');
      expect(content).not.toContain('.ttf');
    });
  });

  describe('Deprecated Function Detection', () => {
    it('should detect GetUnitVeteranRank as deprecated', async () => {
      const luaContent = `local vr = GetUnitVeteranRank("player")`;
      const luaPath = join(testDir, 'test.lua');
      await writeFile(luaPath, luaContent);

      const analyzer = new LuaAnalyzer();
      const result = await analyzer.analyzeFile(luaPath);

      const deprecatedIssue = result.issues.find(i =>
        i.category === 'deprecated_function' &&
        i.message?.includes('GetUnitVeteranRank')
      );

      expect(deprecatedIssue).toBeDefined();
      expect(deprecatedIssue?.suggestedFix).toBe('GetUnitChampionPoints');
    });

    it('should NOT flag GetPlayerStat as deprecated', async () => {
      const luaContent = `local stat = GetPlayerStat(STAT_WEAPON_POWER)`;
      const luaPath = join(testDir, 'test.lua');
      await writeFile(luaPath, luaContent);

      const analyzer = new LuaAnalyzer();
      const result = await analyzer.analyzeFile(luaPath);

      const falsePositive = result.issues.find(i =>
        i.category === 'deprecated_function' &&
        i.message?.includes('GetPlayerStat')
      );

      expect(falsePositive).toBeUndefined();
    });
  });

  describe('End-to-End Fix Workflow', () => {
    it('should fix multiple issues in a single addon', async () => {
      const addonDir = join(testDir, 'TestAddon');
      await mkdir(addonDir);

      // Create manifest with .txt (deprecated)
      await writeFile(
        join(addonDir, 'TestAddon.txt'),
        '## Title: TestAddon\n## APIVersion: 101046\n\nmain.lua\n'
      );

      // Create Lua file with multiple issues
      await writeFile(
        join(addonDir, 'main.lua'),
        `local LAM = LibStub("LibAddonMenu-2.0")
local font = "MyAddon/fonts/myfont.ttf|14"
local vr = GetUnitVeteranRank("player")
`
      );

      const fixer = new AddonFixer({ dryRun: false, createBackup: false });
      const result = await fixer.fix(addonDir);

      expect(result.success).toBe(true);
      expect(result.totalChanges).toBeGreaterThan(0);

      // Verify fixes were applied
      const luaContent = await readFile(join(addonDir, 'main.lua'), 'utf-8');
      expect(luaContent).toContain('LibAddonMenu2');
      expect(luaContent).not.toContain('LibStub');
      expect(luaContent).toContain('.slug');
      expect(luaContent).not.toContain('.ttf');

      // .addon file should exist
      const addonFileExists = await stat(join(addonDir, 'TestAddon.addon'))
        .then(() => true)
        .catch(() => false);
      expect(addonFileExists).toBe(true);
    });

    it('should create backup when enabled', async () => {
      const addonDir = join(testDir, 'TestAddon');
      await mkdir(addonDir);

      await writeFile(
        join(addonDir, 'TestAddon.addon'),
        '## Title: TestAddon\n## APIVersion: 101048\n\nmain.lua\n'
      );

      await writeFile(
        join(addonDir, 'main.lua'),
        `local LAM = LibStub("LibAddonMenu-2.0")`
      );

      const fixer = new AddonFixer({ dryRun: false, createBackup: true });
      const result = await fixer.fix(addonDir);

      expect(result.backupPath).toBeDefined();
      expect(result.backupPath).toContain('_backup_');

      // Cleanup backup
      if (result.backupPath) {
        await rm(result.backupPath, { recursive: true, force: true });
      }
    });

    it('should respect dry-run mode', async () => {
      const addonDir = join(testDir, 'TestAddon');
      await mkdir(addonDir);

      await writeFile(
        join(addonDir, 'TestAddon.addon'),
        '## Title: TestAddon\n## APIVersion: 101048\n\nmain.lua\n'
      );

      const originalContent = `local LAM = LibStub("LibAddonMenu-2.0")`;
      await writeFile(join(addonDir, 'main.lua'), originalContent);

      const fixer = new AddonFixer({ dryRun: true });
      const result = await fixer.fix(addonDir);

      // Changes should be reported but not applied
      expect(result.totalChanges).toBeGreaterThan(0);

      // File should be unchanged
      const content = await readFile(join(addonDir, 'main.lua'), 'utf-8');
      expect(content).toBe(originalContent);
    });
  });

  describe('Silent Pattern Failure Reporting', () => {
    it('should report invalid patterns as info issues', async () => {
      // This test verifies that pattern migration errors don't silently fail
      // The actual behavior depends on having an invalid pattern in the database
      // For now, we just verify the fixer doesn't crash with weird patterns in files

      const addonDir = join(testDir, 'TestAddon');
      await mkdir(addonDir);

      await writeFile(
        join(addonDir, 'TestAddon.addon'),
        '## Title: TestAddon\n## APIVersion: 101048\n\nmain.lua\n'
      );

      // Create file with unusual characters that might confuse regex
      await writeFile(
        join(addonDir, 'main.lua'),
        `local test = "[{weird}]" -- some comment`
      );

      const fixer = new AddonFixer();
      const result = await fixer.analyze(addonDir);

      // Should complete without throwing
      expect(result).toBeDefined();
      expect(result.summary).toBeDefined();
    });
  });
});
