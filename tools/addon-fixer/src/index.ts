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

// ESOUI Scraper
export {
  scrapeAddonInfo,
  scrapeMultipleAddons,
  checkForUpdates,
  analyzeChangelog,
  generateUpdateReport,
  type ScrapedAddonInfo,
  type AddonVersionHistory,
  type ChangelogAnalysis,
  type UpdateCheck,
} from './esoui-scraper.js';

// Addon Data APIs (for synergy analysis)
export {
  ADDON_DATA_APIS,
  findDataSynergies,
  getAddonsByDataType,
  getIntegrationSuggestions,
  getAddonDataAPI,
  findConsumers,
  getDataDependencyGraph,
  type AddonDataAPI,
  type ExposedDataPoint,
  type DataSynergyOpportunity,
  type DataAccessMethod,
} from './addon-data-apis.js';

// Addon Collaborator Framework
export {
  AddonCollaborator,
  LUA_REFERENCE,
  type DataSource,
  type CorrelatedInsight,
  type CollaboratorEvent,
} from './addon-collaborator.js';

// ESO Addon Development Guide
export {
  COMMON_BUGS,
  BEST_PRACTICES,
  OPTIMIZATION_PATTERNS,
  API_DEPRECATION_TIMELINE,
  getBugsByCategory,
  getBugsBySeverity,
  getPracticesByCategory,
  getApiChangesInRange,
  findPotentialBugs,
  getDocStats,
  type CommonBug,
  type BestPractice,
  type OptimizationPattern,
  type ApiChange,
} from './eso-addon-guide.js';
