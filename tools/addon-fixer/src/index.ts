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

// Migrations
export {
  API_VERSION_HISTORY,
  FUNCTION_MIGRATIONS,
  LIBRARY_MIGRATIONS,
  EVENT_MIGRATIONS,
  VALID_CURRENT_FUNCTIONS,
  ADDON_RECOMMENDATIONS,
  getMigrationByName,
  getLibraryMigration,
  getLibraryByPattern,
  getMigrationsByCategory,
  getMigrationsByVersion,
  getAutoFixableMigrations,
  isValidCurrentFunction,
  getAddonRecommendation,
} from './migrations.js';

// Analyzers
export { LuaAnalyzer, analyzeLuaFile } from './lua-analyzer.js';
export { parseManifest, analyzeManifest, fixManifest } from './manifest-parser.js';

// Main Fixer
export { AddonFixer, analyzeAddon, fixAddon } from './fixer.js';
