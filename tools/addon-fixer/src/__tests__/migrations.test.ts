/**
 * Tests for the migration database.
 */

import { describe, it, expect } from 'vitest';
import {
  FUNCTION_MIGRATIONS,
  LIBRARY_MIGRATIONS,
  VALID_CURRENT_FUNCTIONS,
  getMigrationByName,
  getLibraryMigration,
  getMigrationsByCategory,
  getMigrationsByVersion,
  getAutoFixableMigrations,
  isValidCurrentFunction,
} from '../migrations.js';

describe('Migration Database', () => {
  describe('FUNCTION_MIGRATIONS', () => {
    it('should have migrations defined', () => {
      expect(FUNCTION_MIGRATIONS.length).toBeGreaterThan(0);
    });

    it('should have valid confidence values (0-1)', () => {
      for (const m of FUNCTION_MIGRATIONS) {
        expect(m.confidence).toBeGreaterThanOrEqual(0);
        expect(m.confidence).toBeLessThanOrEqual(1);
      }
    });

    it('should have categories for all migrations', () => {
      for (const m of FUNCTION_MIGRATIONS) {
        expect(m.category).toBeTruthy();
      }
    });
  });

  describe('LIBRARY_MIGRATIONS', () => {
    it('should have library migrations defined', () => {
      expect(LIBRARY_MIGRATIONS.length).toBeGreaterThan(0);
    });

    it('should have LibAddonMenu migration', () => {
      const lam = LIBRARY_MIGRATIONS.find(m => m.libraryName === 'LibAddonMenu-2.0');
      expect(lam).toBeDefined();
      expect(lam?.globalVariable).toBe('LibAddonMenu2');
    });
  });

  describe('getMigrationByName', () => {
    it('should find GetUnitVeteranRank migration', () => {
      const migration = getMigrationByName('GetUnitVeteranRank');
      expect(migration).toBeDefined();
      expect(migration?.newName).toBe('GetUnitChampionPoints');
      expect(migration?.confidence).toBe(1.0);
    });

    it('should return undefined for unknown function', () => {
      const migration = getMigrationByName('NonExistentFunction');
      expect(migration).toBeUndefined();
    });
  });

  describe('getLibraryMigration', () => {
    it('should find LibFilters migration', () => {
      const migration = getLibraryMigration('LibFilters-3.0');
      expect(migration).toBeDefined();
      expect(migration?.globalVariable).toBe('LibFilters3');
    });
  });

  describe('getMigrationsByCategory', () => {
    it('should return champion_points migrations', () => {
      const migrations = getMigrationsByCategory('champion_points');
      expect(migrations.length).toBeGreaterThan(0);
      expect(migrations.every(m => m.category === 'champion_points')).toBe(true);
    });
  });

  describe('getMigrationsByVersion', () => {
    it('should return migrations for API 100015', () => {
      const migrations = getMigrationsByVersion(100015);
      expect(migrations.length).toBeGreaterThan(0);
      expect(migrations.some(m => m.oldName === 'GetUnitVeteranRank')).toBe(true);
    });
  });

  describe('getAutoFixableMigrations', () => {
    it('should return only high-confidence auto-fixable migrations', () => {
      const migrations = getAutoFixableMigrations(0.9);
      for (const m of migrations) {
        expect(m.autoFixable).toBe(true);
        expect(m.confidence).toBeGreaterThanOrEqual(0.9);
      }
    });
  });

  describe('isValidCurrentFunction', () => {
    it('should return true for GetPlayerStat', () => {
      expect(isValidCurrentFunction('GetPlayerStat')).toBe(true);
    });

    it('should return true for ZO_SavedVars', () => {
      expect(isValidCurrentFunction('ZO_SavedVars')).toBe(true);
    });

    it('should return false for GetUnitVeteranRank', () => {
      expect(isValidCurrentFunction('GetUnitVeteranRank')).toBe(false);
    });
  });

  describe('False Positive Prevention', () => {
    it('should NOT flag GetPlayerStat as deprecated', () => {
      const migration = getMigrationByName('GetPlayerStat');
      expect(migration).toBeUndefined();
    });

    it('should NOT flag GetUnitPower as deprecated', () => {
      const migration = getMigrationByName('GetUnitPower');
      expect(migration).toBeUndefined();
    });

    it('should NOT flag GetSlotBoundId as deprecated', () => {
      const migration = getMigrationByName('GetSlotBoundId');
      expect(migration).toBeUndefined();
    });

    it('should have GetPlayerStat in VALID_CURRENT_FUNCTIONS', () => {
      expect(VALID_CURRENT_FUNCTIONS.has('GetPlayerStat')).toBe(true);
    });
  });
});
