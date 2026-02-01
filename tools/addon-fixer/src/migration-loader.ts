/**
 * Migration database loader.
 *
 * Loads migrations from the shared JSON database, providing
 * a single source of truth for both analysis and transformation.
 */

import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

// ============================================================================
// Types (matching JSON structure)
// ============================================================================

export interface FunctionMigration {
  id: string;
  oldName: string;
  type: 'renamed' | 'removed' | 'replaced' | 'signature_changed' | 'return_changed';
  newName?: string;
  versionDeprecated?: number;
  versionRemoved?: number;
  category: string;
  confidence: number;
  autoFixable: boolean;
  notes: string;
  replacementCode?: string;
  oldSignature?: string;
  newSignature?: string;
}

export interface EventMigration {
  id: string;
  oldName: string;
  type: 'removed' | 'renamed';
  versionRemoved?: number;
  replacementEvent?: string;
  notes: string;
}

export interface LibraryMigration {
  id: string;
  name: string;
  globalVariable: string;
  patterns: string[];
  minVersion?: number;
  notes: string;
}

export interface PatternMigration {
  id: string;
  name: string;
  pattern: string;
  replacement: string;
  category: string;
  confidence: number;
  autoFixable: boolean;
  notes: string;
}

export interface AddonRecommendation {
  name: string;
  complexity: 'low' | 'medium' | 'high' | 'very_high';
  shouldAttemptFix: boolean;
  recommendations: string[];
}

export interface APIVersionInfo {
  version: number;
  update: string;
  releaseDate: string;
  changes: string[];
}

export interface MigrationDatabase {
  version: string;
  lastUpdated: string;
  currentLiveAPI: number;
  currentPTSAPI: number;
  apiVersionHistory: APIVersionInfo[];
  functionMigrations: FunctionMigration[];
  eventMigrations: EventMigration[];
  libraryMigrations: LibraryMigration[];
  patternMigrations: PatternMigration[];
  validCurrentFunctions: string[];
  addonRecommendations: AddonRecommendation[];
}

// ============================================================================
// Loader
// ============================================================================

let cachedDatabase: MigrationDatabase | null = null;

export async function loadMigrations(
  customPath?: string
): Promise<MigrationDatabase> {
  if (cachedDatabase && !customPath) {
    return cachedDatabase;
  }

  const __filename = fileURLToPath(import.meta.url);
  const __dirname = dirname(__filename);

  // Default path is relative to project root
  const defaultPath = join(
    __dirname,
    '..',
    '..',
    '..',
    'data',
    'migrations',
    'eso-api-migrations.json'
  );

  const filePath = customPath ?? defaultPath;

  try {
    const content = await readFile(filePath, 'utf-8');
    const database = JSON.parse(content) as MigrationDatabase;

    if (!customPath) {
      cachedDatabase = database;
    }

    return database;
  } catch (e) {
    // Fall back to embedded minimal database
    console.warn(`Failed to load migrations from ${filePath}, using embedded fallback`);
    return getEmbeddedMigrations();
  }
}

/**
 * Minimal embedded migrations for when JSON file is unavailable.
 */
function getEmbeddedMigrations(): MigrationDatabase {
  return {
    version: '1.0.0-embedded',
    lastUpdated: '2026-02-01',
    currentLiveAPI: 101048,
    currentPTSAPI: 101049,
    apiVersionHistory: [],
    functionMigrations: [
      {
        id: 'cp-001',
        oldName: 'GetUnitVeteranRank',
        type: 'renamed',
        newName: 'GetUnitChampionPoints',
        versionDeprecated: 100015,
        category: 'champion_points',
        confidence: 1.0,
        autoFixable: true,
        notes: 'Veteran Ranks replaced with Champion Points',
      },
    ],
    eventMigrations: [],
    libraryMigrations: [
      {
        id: 'lib-001',
        name: 'LibAddonMenu-2.0',
        globalVariable: 'LibAddonMenu2',
        patterns: ['LibStub("LibAddonMenu-2.0")'],
        notes: 'LibStub deprecated',
      },
    ],
    patternMigrations: [],
    validCurrentFunctions: ['GetPlayerStat', 'GetUnitPower', 'ZO_SavedVars'],
    addonRecommendations: [],
  };
}

// ============================================================================
// Query Functions
// ============================================================================

export function getFunctionMigration(
  db: MigrationDatabase,
  funcName: string
): FunctionMigration | undefined {
  return db.functionMigrations.find((m) => m.oldName === funcName);
}

export function getLibraryMigration(
  db: MigrationDatabase,
  libName: string
): LibraryMigration | undefined {
  return db.libraryMigrations.find((m) => m.name === libName);
}

export function getEventMigration(
  db: MigrationDatabase,
  eventName: string
): EventMigration | undefined {
  return db.eventMigrations.find((m) => m.oldName === eventName);
}

export function isValidCurrentFunction(
  db: MigrationDatabase,
  funcName: string
): boolean {
  return db.validCurrentFunctions.includes(funcName);
}

export function getAutoFixableMigrations(
  db: MigrationDatabase,
  minConfidence: number = 0.8
): FunctionMigration[] {
  return db.functionMigrations.filter(
    (m) => m.autoFixable && m.confidence >= minConfidence
  );
}

export function getMigrationsByCategory(
  db: MigrationDatabase,
  category: string
): FunctionMigration[] {
  return db.functionMigrations.filter((m) => m.category === category);
}

export function getAddonRecommendation(
  db: MigrationDatabase,
  addonName: string
): AddonRecommendation | undefined {
  return db.addonRecommendations.find((r) =>
    addonName.toLowerCase().includes(r.name.toLowerCase())
  );
}
