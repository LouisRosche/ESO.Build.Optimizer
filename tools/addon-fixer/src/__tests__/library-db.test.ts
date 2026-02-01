/**
 * Tests for library database and health check functionality.
 */

import { describe, it, expect } from 'vitest';
import {
  LIBRARY_DATABASE,
  LIBRARY_RECOMMENDATIONS,
  parseVersion,
  checkLibraryHealth,
  getLibraryInfo,
  getLibraryRecommendations,
} from '../library-db.js';

describe('Library Database', () => {
  it('contains core libraries', () => {
    const names = LIBRARY_DATABASE.map(l => l.name);
    expect(names).toContain('LibAddonMenu-2.0');
    expect(names).toContain('LibFilters-3.0');
    expect(names).toContain('LibAsync');
    expect(names).toContain('LibGPS3');
  });

  it('all libraries have required fields', () => {
    for (const lib of LIBRARY_DATABASE) {
      expect(lib.name).toBeTruthy();
      expect(lib.globalVariable).toBeTruthy();
      expect(lib.latestVersion).toBeTruthy();
      expect(lib.purpose).toBeTruthy();
      expect(typeof lib.maintained).toBe('boolean');
    }
  });

  it('deprecated libraries have replacements noted', () => {
    const deprecated = LIBRARY_DATABASE.filter(l => !l.maintained);
    expect(deprecated.length).toBeGreaterThan(0);

    for (const lib of deprecated) {
      expect(lib.replacedBy || lib.purpose.includes('DEPRECATED')).toBeTruthy();
    }
  });

  it('has valid ESOUI IDs', () => {
    const withIds = LIBRARY_DATABASE.filter(l => l.esouiId);
    expect(withIds.length).toBeGreaterThan(10);

    for (const lib of withIds) {
      expect(lib.esouiId).toBeGreaterThan(0);
    }
  });
});

describe('parseVersion', () => {
  it('parses standard semver', () => {
    expect(parseVersion('2.0.35')).toBe(20035);
    expect(parseVersion('1.0.0')).toBe(10000);
    expect(parseVersion('3.5.2')).toBe(30502);
  });

  it('parses major.minor only', () => {
    expect(parseVersion('2.0')).toBe(20000);
    expect(parseVersion('1.5')).toBe(10500);
  });

  it('parses single number', () => {
    expect(parseVersion('35')).toBe(350000);
    expect(parseVersion('7')).toBe(70000);
  });

  it('handles v prefix', () => {
    expect(parseVersion('v2.0.35')).toBe(20035);
    expect(parseVersion('V1.0.0')).toBe(10000);
  });

  it('orders versions correctly', () => {
    expect(parseVersion('2.0.35')).toBeGreaterThan(parseVersion('2.0.30'));
    expect(parseVersion('3.0.0')).toBeGreaterThan(parseVersion('2.9.99'));
    expect(parseVersion('1.5.0')).toBeGreaterThan(parseVersion('1.4.99'));
  });
});

describe('checkLibraryHealth', () => {
  it('returns null for unknown library', () => {
    expect(checkLibraryHealth('UnknownLib-1.0')).toBeNull();
  });

  it('finds library by name', () => {
    const result = checkLibraryHealth('LibAddonMenu-2.0');
    expect(result).not.toBeNull();
    expect(result!.name).toBe('LibAddonMenu-2.0');
  });

  it('finds library by global variable', () => {
    const result = checkLibraryHealth('LibAddonMenu2');
    expect(result).not.toBeNull();
    expect(result!.name).toBe('LibAddonMenu-2.0');
  });

  it('detects outdated version', () => {
    const result = checkLibraryHealth('LibAddonMenu-2.0', '2.0.20');
    expect(result).not.toBeNull();
    expect(result!.isOutdated).toBe(true);
  });

  it('detects up-to-date version', () => {
    const result = checkLibraryHealth('LibAddonMenu-2.0', '2.0.35');
    expect(result).not.toBeNull();
    expect(result!.isOutdated).toBe(false);
  });

  it('detects deprecated libraries', () => {
    const result = checkLibraryHealth('LibStub');
    expect(result).not.toBeNull();
    expect(result!.isDeprecated).toBe(true);
    expect(result!.replacement).toBeTruthy();
  });

  it('provides ESOUI URL', () => {
    const result = checkLibraryHealth('LibAddonMenu-2.0');
    expect(result!.esouiUrl).toContain('esoui.com/downloads/info');
  });
});

describe('getLibraryInfo', () => {
  it('returns info by name', () => {
    const info = getLibraryInfo('LibAddonMenu-2.0');
    expect(info).toBeDefined();
    expect(info!.globalVariable).toBe('LibAddonMenu2');
  });

  it('returns info by global variable', () => {
    const info = getLibraryInfo('LibFilters3');
    expect(info).toBeDefined();
    expect(info!.name).toBe('LibFilters-3.0');
  });

  it('returns undefined for unknown', () => {
    expect(getLibraryInfo('FakeLib')).toBeUndefined();
  });
});

describe('Library Recommendations', () => {
  it('has recommendations defined', () => {
    expect(LIBRARY_RECOMMENDATIONS.length).toBeGreaterThan(0);
  });

  it('all recommendations have required fields', () => {
    for (const rec of LIBRARY_RECOMMENDATIONS) {
      expect(rec.pattern).toBeInstanceOf(RegExp);
      expect(rec.description).toBeTruthy();
      expect(rec.library).toBeTruthy();
      expect(rec.benefit).toBeTruthy();
    }
  });
});

describe('getLibraryRecommendations', () => {
  it('recommends LibGPS for map coordinates', () => {
    const code = `
      local x, y = GetMapPlayerPosition("player")
    `;
    const recs = getLibraryRecommendations(code);
    expect(recs.some(r => r.library === 'LibGPS3')).toBe(true);
  });

  it('recommends LibDebugLogger for debug output', () => {
    const code = `
      d(tostring(someValue))
    `;
    const recs = getLibraryRecommendations(code);
    expect(recs.some(r => r.library === 'LibDebugLogger')).toBe(true);
  });

  it('recommends LibCustomMenu for menu usage', () => {
    const code = `
      ZO_Menu_AddMenuItem("Test Item")
    `;
    const recs = getLibraryRecommendations(code);
    expect(recs.some(r => r.library === 'LibCustomMenu')).toBe(true);
  });

  it('returns empty for clean code', () => {
    const code = `
      local function add(a, b)
        return a + b
      end
    `;
    const recs = getLibraryRecommendations(code);
    expect(recs.length).toBe(0);
  });
});
