/**
 * ESO Addon Fixer - Main exports
 *
 * Automated tool for fixing broken Elder Scrolls Online addons.
 * Uses AST-based Lua analysis for precision detection and fixing.
 */

// Types
export type {
  APIVersionInfo,
  MigrationType,
  IssueSeverity,
  IssueCategory,
  FunctionMigration,
  LibraryMigration,
  SourceLocation,
  SourceRange,
  Issue,
  FileAnalysisResult,
  FileMetrics,
  ParseError,
  AddonAnalysisResult,
  AnalysisSummary,
  ManifestData,
  DependencyInfo,
  ValidationResult,
  DependencyValidation,
  FixerConfig,
  FileFixResult,
  FixChange,
  AddonFixResult,
} from './types.js';

export {
  CURRENT_LIVE_API,
  CURRENT_PTS_API,
  DEFAULT_CONFIG,
} from './types.js';

// Migration Database
export {
  loadMigrations,
  getFunctionMigration,
  getLibraryMigration,
  getEventMigration,
  isValidCurrentFunction,
  getAutoFixableMigrations,
  getMigrationsByCategory,
  getAddonRecommendation,
  type MigrationDatabase,
} from './migration-loader.js';

// Analyzers
export { LuaAnalyzer, analyzeLuaFile } from './lua-analyzer.js';
export { LuaTransformer, transformLuaFile, transformLuaCode } from './lua-transformer.js';
export { parseManifest, analyzeManifest, fixManifest } from './manifest-parser.js';

// Library Database
export {
  LIBRARY_DATABASE,
  LIBRARY_RECOMMENDATIONS,
  checkLibraryHealth,
  getLibraryInfo,
  getLibraryRecommendations,
  parseVersion,
  type LibraryVersionInfo,
  type LibraryHealthResult,
  type LibraryRecommendation,
} from './library-db.js';

// Addon Compatibility Database
export {
  ADDON_COMPATIBILITY_DB,
  getAddonsByCategory,
  getAddonsByStatus,
  getAddonSuite,
  getAddonInfo,
  getAddonsNeedingFixes,
  getAlternatives,
  getCategories,
  getCompatibilityStats,
  type AddonCompatibility,
  type AddonStatus,
  type FixComplexity,
} from './addon-compat-db.js';

// Main Fixer
export { AddonFixer, analyzeAddon, fixAddon } from './fixer.js';
