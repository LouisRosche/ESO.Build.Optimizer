/**
 * Tests for ESOUI scraper and changelog analysis.
 */

import { describe, it, expect } from 'vitest';
import {
  analyzeChangelog,
  generateUpdateReport,
  type UpdateCheck,
} from '../esoui-scraper.js';

describe('analyzeChangelog', () => {
  it('detects API-related changes', () => {
    const changelog = 'Updated for API version 101048. Fixed compatibility issues.';
    const analysis = analyzeChangelog(changelog);

    expect(analysis.mentionsApiChange).toBe(true);
    expect(analysis.keywords).toContain('api');
    expect(analysis.keywords).toContain('compatibility');
  });

  it('detects bug fix mentions', () => {
    const changelog = 'Fixed a crash when opening inventory. Bug with tooltip resolved.';
    const analysis = analyzeChangelog(changelog);

    expect(analysis.mentionsBugFix).toBe(true);
    expect(analysis.keywords).toContain('fix');
    expect(analysis.keywords).toContain('bug');
  });

  it('detects new feature mentions', () => {
    const changelog = 'Added new minimap feature. Implemented support for controller.';
    const analysis = analyzeChangelog(changelog);

    expect(analysis.mentionsNewFeature).toBe(true);
    expect(analysis.keywords).toContain('add');
    expect(analysis.keywords).toContain('feature');
  });

  it('detects breaking change mentions', () => {
    const changelog = 'Breaking: Removed old API. Deprecated functions have been removed.';
    const analysis = analyzeChangelog(changelog);

    expect(analysis.mentionsBreakingChange).toBe(true);
    expect(analysis.keywords).toContain('breaking');
    expect(analysis.keywords).toContain('removed');
  });

  it('detects library mentions', () => {
    const changelog = 'Updated LibAddonMenu to latest version. LibFilters compatibility fix.';
    const analysis = analyzeChangelog(changelog);

    expect(analysis.mentionsLibrary.length).toBeGreaterThan(0);
    expect(analysis.mentionsLibrary).toContain('libaddonmenu');
  });

  it('handles empty changelog', () => {
    const analysis = analyzeChangelog('');

    expect(analysis.mentionsApiChange).toBe(false);
    expect(analysis.mentionsBugFix).toBe(false);
    expect(analysis.mentionsNewFeature).toBe(false);
    expect(analysis.mentionsBreakingChange).toBe(false);
    expect(analysis.mentionsLibrary).toHaveLength(0);
    expect(analysis.keywords).toHaveLength(0);
  });

  it('is case insensitive', () => {
    const changelog = 'FIXED BUG with API COMPATIBILITY';
    const analysis = analyzeChangelog(changelog);

    expect(analysis.mentionsBugFix).toBe(true);
    expect(analysis.mentionsApiChange).toBe(true);
  });

  it('returns unique keywords', () => {
    const changelog = 'fix fix fix bug bug bug';
    const analysis = analyzeChangelog(changelog);

    const uniqueKeywords = new Set(analysis.keywords);
    expect(uniqueKeywords.size).toBe(analysis.keywords.length);
  });
});

describe('generateUpdateReport', () => {
  it('generates report for updates', () => {
    const updates: UpdateCheck[] = [
      {
        esouiId: 1234,
        name: 'Test Addon',
        knownVersion: '1.0.0',
        currentVersion: '2.0.0',
        hasUpdate: true,
        changelog: 'Fixed bugs and added features.',
        changelogAnalysis: analyzeChangelog('Fixed bugs and added features.'),
      },
    ];

    const report = generateUpdateReport(updates);

    expect(report).toContain('Addon Update Report');
    expect(report).toContain('Test Addon');
    expect(report).toContain('1.0.0 → 2.0.0');
    expect(report).toContain('Updates available: 1');
  });

  it('handles no updates', () => {
    const updates: UpdateCheck[] = [
      {
        esouiId: 1234,
        name: 'Test Addon',
        knownVersion: '1.0.0',
        currentVersion: '1.0.0',
        hasUpdate: false,
      },
    ];

    const report = generateUpdateReport(updates);

    expect(report).toContain('Updates available: 0');
    expect(report).toContain('Up to date: 1');
  });

  it('handles failed checks', () => {
    const updates: UpdateCheck[] = [
      {
        esouiId: 1234,
        name: 'Test Addon',
        knownVersion: '1.0.0',
        currentVersion: 'unknown',
        hasUpdate: false,
      },
    ];

    const report = generateUpdateReport(updates);

    expect(report).toContain('Failed to check: 1');
  });

  it('highlights breaking changes', () => {
    const updates: UpdateCheck[] = [
      {
        esouiId: 1234,
        name: 'Test Addon',
        knownVersion: '1.0.0',
        currentVersion: '2.0.0',
        hasUpdate: true,
        changelog: 'Breaking change: Removed old API.',
        changelogAnalysis: analyzeChangelog('Breaking change: Removed old API.'),
      },
    ];

    const report = generateUpdateReport(updates);

    expect(report).toContain('Breaking changes');
  });

  it('includes ESOUI URL', () => {
    const updates: UpdateCheck[] = [
      {
        esouiId: 1234,
        name: 'Test Addon',
        knownVersion: '1.0.0',
        currentVersion: '2.0.0',
        hasUpdate: true,
      },
    ];

    const report = generateUpdateReport(updates);

    expect(report).toContain('esoui.com/downloads/info1234');
  });
});
