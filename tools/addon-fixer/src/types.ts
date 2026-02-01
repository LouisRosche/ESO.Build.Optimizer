/**
 * Core type definitions for the ESO Addon Fixer.
 * Strict typing ensures precision in detection and fixes.
 */

// ============================================================================
// API Version Types
// ============================================================================

export interface APIVersionInfo {
  readonly version: number;
  readonly update: string;
  readonly releaseDate: string;
  readonly isLive: boolean;
  readonly isPTS: boolean;
  readonly significantChanges: readonly string[];
}

export const CURRENT_LIVE_API = 101048 as const;
export const CURRENT_PTS_API = 101049 as const;

// ============================================================================
// Migration Types
// ============================================================================

export type MigrationType =
  | 'renamed'           // Function renamed, same signature
  | 'signature_changed' // Parameters added/removed/reordered
  | 'return_changed'    // Return value(s) changed
  | 'removed'           // Function completely removed
  | 'deprecated'        // Still works but should be updated
  | 'replaced';         // Different function entirely

export type IssueSeverity = 'error' | 'warning' | 'info';

export type IssueCategory =
  | 'api_version'
  | 'libstub'
  | 'deprecated_function'
  | 'signature_change'
  | 'font_path'
  | 'texture_path'
  | 'encoding'
  | 'xml_control'
  | 'dependency'
  | 'event_constant'
  | 'potential_nil';

/**
 * Represents a single API migration with full context.
 * The `confidence` field indicates how certain we are about this migration.
 */
export interface FunctionMigration {
  readonly oldName: string;
  readonly migrationType: MigrationType;
  readonly newName?: string;
  readonly oldSignature?: string;
  readonly newSignature?: string;
  readonly versionDeprecated?: number;
  readonly versionRemoved?: number;
  readonly notes: string;
  readonly replacementCode?: string;
  readonly category: string;
  /** 0.0-1.0 confidence that this migration applies */
  readonly confidence: number;
  /** Whether this should trigger an auto-fix */
  readonly autoFixable: boolean;
  /** Conditions under which this migration does NOT apply */
  readonly exceptions?: readonly string[];
}

export interface LibraryMigration {
  readonly libraryName: string;
  readonly oldPatterns: readonly string[];
  readonly globalVariable: string;
  readonly minVersion?: number;
  readonly notes: string;
}

// ============================================================================
// Issue Types
// ============================================================================

export interface SourceLocation {
  readonly line: number;
  readonly column: number;
  readonly offset: number;
}

export interface SourceRange {
  readonly start: SourceLocation;
  readonly end: SourceLocation;
}

/**
 * An issue found during analysis.
 * Immutable to prevent accidental mutation during processing.
 */
export interface Issue {
  readonly id: string;
  readonly filePath: string;
  readonly location: SourceRange;
  readonly category: IssueCategory;
  readonly severity: IssueSeverity;
  readonly message: string;
  readonly details?: string;
  readonly oldCode: string;
  readonly suggestedFix?: string;
  readonly autoFixable: boolean;
  readonly confidence: number;
  readonly relatedMigration?: FunctionMigration;
}

// ============================================================================
// Analysis Result Types
// ============================================================================

export interface FileAnalysisResult {
  readonly filePath: string;
  readonly fileType: 'lua' | 'xml' | 'manifest' | 'unknown';
  readonly issues: readonly Issue[];
  readonly metrics: FileMetrics;
  readonly parseErrors: readonly ParseError[];
}

export interface FileMetrics {
  readonly lineCount: number;
  readonly functionCount: number;
  readonly eventRegistrations: number;
  readonly libStubUsages: number;
  readonly deprecatedCalls: number;
}

export interface ParseError {
  readonly message: string;
  readonly location?: SourceLocation;
  readonly recoverable: boolean;
}

export interface AddonAnalysisResult {
  readonly addonPath: string;
  readonly addonName: string;
  readonly manifestData?: ManifestData;
  readonly fileResults: readonly FileAnalysisResult[];
  readonly validationResult?: ValidationResult;
  readonly summary: AnalysisSummary;
}

export interface AnalysisSummary {
  readonly totalFiles: number;
  readonly totalIssues: number;
  readonly issuesBySeverity: Record<IssueSeverity, number>;
  readonly issuesByCategory: Partial<Record<IssueCategory, number>>;
  readonly autoFixableCount: number;
  readonly estimatedFixTime: string;
}

// ============================================================================
// Manifest Types
// ============================================================================

export interface ManifestData {
  readonly path: string;
  readonly title: string;
  readonly apiVersions: readonly number[];
  readonly addonVersion?: number;
  readonly version?: string;
  readonly author?: string;
  readonly description?: string;
  readonly dependsOn: readonly DependencyInfo[];
  readonly optionalDependsOn: readonly DependencyInfo[];
  readonly savedVariables: readonly string[];
  readonly isLibrary: boolean;
  readonly files: readonly string[];
  readonly rawContent: string;
  readonly encoding: 'utf-8' | 'utf-8-bom' | 'windows-1252' | 'unknown';
  readonly lineEnding: 'crlf' | 'lf' | 'mixed';
}

export interface DependencyInfo {
  readonly name: string;
  readonly minVersion?: number;
  readonly raw: string;
}

// ============================================================================
// Validation Types
// ============================================================================

export interface ValidationResult {
  readonly isValid: boolean;
  readonly dependencies: readonly DependencyValidation[];
  readonly errors: readonly string[];
  readonly warnings: readonly string[];
}

export interface DependencyValidation {
  readonly name: string;
  readonly required: boolean;
  readonly isAvailable: boolean;
  readonly currentVersion?: number;
  readonly requiredVersion?: number;
  readonly isDeprecated: boolean;
  readonly replacement?: string;
}

// ============================================================================
// Fix Types
// ============================================================================

export interface FixerConfig {
  readonly updateApiVersion: boolean;
  readonly fixLibStub: boolean;
  readonly fixDeprecatedFunctions: boolean;
  readonly fixFontPaths: boolean;
  readonly fixXmlIssues: boolean;
  readonly fixEncoding: boolean;
  readonly addNilGuards: boolean;
  readonly validateDependencies: boolean;
  readonly createBackup: boolean;
  readonly dryRun: boolean;
  /** Minimum confidence threshold for auto-fixes (0.0-1.0) */
  readonly confidenceThreshold: number;
}

export const DEFAULT_CONFIG: FixerConfig = {
  updateApiVersion: true,
  fixLibStub: true,
  fixDeprecatedFunctions: true,
  fixFontPaths: true,
  fixXmlIssues: true,
  fixEncoding: true,
  addNilGuards: false,
  validateDependencies: true,
  createBackup: true,
  dryRun: false,
  confidenceThreshold: 0.8,
};

export interface FileFixResult {
  readonly filePath: string;
  readonly fileType: 'lua' | 'xml' | 'manifest';
  readonly changes: readonly FixChange[];
  readonly errors: readonly string[];
  readonly wasModified: boolean;
}

export interface FixChange {
  readonly location: SourceRange;
  readonly oldCode: string;
  readonly newCode: string;
  readonly reason: string;
  readonly confidence: number;
}

export interface AddonFixResult {
  readonly addonPath: string;
  readonly addonName: string;
  readonly success: boolean;
  readonly fileResults: readonly FileFixResult[];
  readonly backupPath?: string;
  readonly packagePath?: string;
  readonly totalChanges: number;
  readonly errors: readonly string[];
  readonly warnings: readonly string[];
  readonly recommendations: readonly string[];
}

// ============================================================================
// Lua AST Types (subset of luaparse types for our use)
// ============================================================================

export interface LuaNode {
  readonly type: string;
  readonly loc?: {
    readonly start: { line: number; column: number };
    readonly end: { line: number; column: number };
  };
  readonly range?: readonly [number, number];
}

export interface LuaCallExpression extends LuaNode {
  readonly type: 'CallExpression';
  readonly base: LuaNode;
  readonly arguments: readonly LuaNode[];
}

export interface LuaIdentifier extends LuaNode {
  readonly type: 'Identifier';
  readonly name: string;
}

export interface LuaStringLiteral extends LuaNode {
  readonly type: 'StringLiteral';
  readonly value: string;
  readonly raw: string;
}

export interface LuaMemberExpression extends LuaNode {
  readonly type: 'MemberExpression';
  readonly base: LuaNode;
  readonly identifier: LuaIdentifier;
  readonly indexer: '.' | ':';
}
