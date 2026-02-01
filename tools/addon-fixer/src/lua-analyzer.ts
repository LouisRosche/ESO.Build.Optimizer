/**
 * AST-based Lua code analyzer for ESO addon fixer.
 *
 * Uses luaparse for proper Lua parsing, avoiding regex-based
 * false positives and providing accurate source locations.
 *
 * Key improvements over regex:
 * - Distinguishes function calls from definitions
 * - Properly handles string literals and comments
 * - Tracks variable scopes
 * - Provides precise source locations
 */

import * as luaparse from 'luaparse';
import { readFile } from 'node:fs/promises';
import type {
  Issue,
  IssueCategory,
  IssueSeverity,
  FileAnalysisResult,
  FileMetrics,
  ParseError,
  SourceRange,
  LuaNode,
  LuaCallExpression,
  LuaIdentifier,
  LuaStringLiteral,
  LuaMemberExpression,
} from './types.js';
import {
  FUNCTION_MIGRATIONS,
  LIBRARY_MIGRATIONS,
  getMigrationByName,
  getLibraryByPattern,
  isValidCurrentFunction,
} from './migrations.js';

// ============================================================================
// Analyzer State
// ============================================================================

interface AnalyzerState {
  filePath: string;
  content: string;
  issues: Issue[];
  metrics: FileMetrics;
  parseErrors: ParseError[];
  issueIdCounter: number;
  localVariables: Set<string>;
}

function createInitialState(filePath: string, content: string): AnalyzerState {
  return {
    filePath,
    content,
    issues: [],
    metrics: {
      lineCount: content.split('\n').length,
      functionCount: 0,
      eventRegistrations: 0,
      libStubUsages: 0,
      deprecatedCalls: 0,
    },
    parseErrors: [],
    issueIdCounter: 0,
    localVariables: new Set(),
  };
}

// ============================================================================
// Main Analyzer
// ============================================================================

export class LuaAnalyzer {
  private readonly minConfidence: number;

  constructor(minConfidence: number = 0.8) {
    this.minConfidence = minConfidence;
  }

  async analyzeFile(filePath: string): Promise<FileAnalysisResult> {
    let content: string;
    let encoding: 'utf-8' | 'windows-1252' = 'utf-8';

    try {
      content = await readFile(filePath, 'utf-8');
    } catch {
      try {
        content = await readFile(filePath, 'latin1');
        encoding = 'windows-1252';
      } catch (e) {
        return {
          filePath,
          fileType: 'lua',
          issues: [],
          metrics: {
            lineCount: 0,
            functionCount: 0,
            eventRegistrations: 0,
            libStubUsages: 0,
            deprecatedCalls: 0,
          },
          parseErrors: [{
            message: `Failed to read file: ${e}`,
            recoverable: false,
          }],
        };
      }
    }

    const state = createInitialState(filePath, content);

    // Add encoding issue if needed
    if (encoding === 'windows-1252') {
      state.issues.push(this.createIssue(state, {
        category: 'encoding',
        severity: 'warning',
        message: 'File uses Windows-1252 encoding, should be UTF-8',
        location: { start: { line: 1, column: 0, offset: 0 }, end: { line: 1, column: 0, offset: 0 } },
        oldCode: '',
        suggestedFix: 'Convert to UTF-8 encoding',
        autoFixable: true,
        confidence: 1.0,
      }));
    }

    // Parse Lua AST
    let ast: luaparse.Chunk | null = null;
    try {
      ast = luaparse.parse(content, {
        locations: true,
        ranges: true,
        comments: true,
        luaVersion: '5.1',
      });
    } catch (e) {
      const parseError = e as { message?: string; line?: number; column?: number };
      state.parseErrors.push({
        message: parseError.message ?? 'Unknown parse error',
        location: parseError.line !== undefined ? {
          line: parseError.line,
          column: parseError.column ?? 0,
          offset: 0,
        } : undefined,
        recoverable: false,
      });

      // Fall back to regex-based analysis for unparseable files
      this.analyzeWithRegex(state);
    }

    if (ast) {
      this.analyzeAST(state, ast);
    }

    return {
      filePath,
      fileType: 'lua',
      issues: state.issues,
      metrics: state.metrics,
      parseErrors: state.parseErrors,
    };
  }

  // ============================================================================
  // AST Analysis
  // ============================================================================

  private analyzeAST(state: AnalyzerState, ast: luaparse.Chunk): void {
    this.visitNode(state, ast);
  }

  private visitNode(state: AnalyzerState, node: luaparse.Node): void {
    if (!node || typeof node !== 'object') return;

    switch (node.type) {
      case 'CallExpression':
        this.analyzeCallExpression(state, node as unknown as LuaCallExpression);
        break;

      case 'FunctionDeclaration':
        state.metrics = { ...state.metrics, functionCount: state.metrics.functionCount + 1 };
        break;

      case 'LocalStatement':
        // Track local variable declarations
        this.trackLocalVariables(state, node);
        break;

      case 'StringLiteral':
        this.analyzeStringLiteral(state, node as unknown as LuaStringLiteral);
        break;
    }

    // Recursively visit child nodes
    for (const key of Object.keys(node)) {
      const value = (node as Record<string, unknown>)[key];
      if (Array.isArray(value)) {
        for (const child of value) {
          if (child && typeof child === 'object' && 'type' in child) {
            this.visitNode(state, child as luaparse.Node);
          }
        }
      } else if (value && typeof value === 'object' && 'type' in value) {
        this.visitNode(state, value as luaparse.Node);
      }
    }
  }

  private trackLocalVariables(state: AnalyzerState, node: luaparse.Node): void {
    const localNode = node as { variables?: Array<{ name: string }> };
    if (localNode.variables) {
      for (const v of localNode.variables) {
        state.localVariables.add(v.name);
      }
    }
  }

  // ============================================================================
  // Call Expression Analysis
  // ============================================================================

  private analyzeCallExpression(state: AnalyzerState, node: LuaCallExpression): void {
    const funcName = this.extractFunctionName(node);
    if (!funcName) return;

    // Check for LibStub usage
    if (funcName === 'LibStub' || funcName.endsWith(':LibStub')) {
      this.analyzeLibStubCall(state, node);
      return;
    }

    // Check for EVENT_MANAGER registrations
    if (funcName.includes('RegisterForEvent')) {
      state.metrics = { ...state.metrics, eventRegistrations: state.metrics.eventRegistrations + 1 };
    }

    // Check for deprecated function calls
    // Skip if it's a valid current function (prevents false positives)
    if (isValidCurrentFunction(funcName)) {
      return;
    }

    const migration = getMigrationByName(funcName);
    if (migration && migration.confidence >= this.minConfidence) {
      state.metrics = { ...state.metrics, deprecatedCalls: state.metrics.deprecatedCalls + 1 };

      const location = this.nodeToSourceRange(node);
      const oldCode = this.extractSourceCode(state.content, location);

      state.issues.push(this.createIssue(state, {
        category: 'deprecated_function',
        severity: migration.migrationType === 'removed' ? 'error' : 'warning',
        message: `Deprecated function: ${funcName}`,
        details: migration.notes,
        location,
        oldCode,
        suggestedFix: migration.newName ?? migration.replacementCode,
        autoFixable: migration.autoFixable && migration.newName !== undefined,
        confidence: migration.confidence,
        relatedMigration: migration,
      }));
    }
  }

  private analyzeLibStubCall(state: AnalyzerState, node: LuaCallExpression): void {
    state.metrics = { ...state.metrics, libStubUsages: state.metrics.libStubUsages + 1 };

    // Extract library name from arguments
    const args = node.arguments;
    if (args.length === 0) return;

    const firstArg = args[0] as LuaNode;
    if (firstArg?.type !== 'StringLiteral') return;

    const libName = (firstArg as LuaStringLiteral).value;
    if (!libName) return; // Skip if library name is null/empty

    const libMigration = LIBRARY_MIGRATIONS.find((m) => m.libraryName === libName);

    const location = this.nodeToSourceRange(node);
    const oldCode = this.extractSourceCode(state.content, location);

    const suggestedGlobal = libMigration?.globalVariable ?? libName.replace(/-/g, '');
    state.issues.push(this.createIssue(state, {
      category: 'libstub',
      severity: 'warning',
      message: `LibStub is deprecated, use global variable instead`,
      details: `Replace with ${suggestedGlobal}`,
      location,
      oldCode,
      suggestedFix: suggestedGlobal,
      autoFixable: true,
      confidence: 0.95,
    }));
  }

  // ============================================================================
  // String Literal Analysis (Font Paths)
  // ============================================================================

  private analyzeStringLiteral(state: AnalyzerState, node: LuaStringLiteral): void {
    const value = node.value;
    if (!value) return; // Skip null/empty string literals

    // Check for old font paths
    if (/\.(ttf|otf)(\||"|$)/i.test(value)) {
      const location = this.nodeToSourceRange(node as unknown as LuaNode);
      const oldCode = node.raw;
      const suggestedFix = oldCode.replace(/\.(ttf|otf)/gi, '.slug');

      state.issues.push(this.createIssue(state, {
        category: 'font_path',
        severity: 'warning',
        message: 'Font path uses old TTF/OTF format, should use .slug (Update 41+)',
        location,
        oldCode,
        suggestedFix,
        autoFixable: true,
        confidence: 0.95,
      }));
    }

    // Check for texture paths that may have changed
    if (value.includes('EsoUI/Art/') && value.endsWith('.dds')) {
      // Only flag specific known-changed paths, not all texture references
      // This prevents false positives
    }
  }

  // ============================================================================
  // Fallback Regex Analysis
  // ============================================================================

  private analyzeWithRegex(state: AnalyzerState): void {
    const content = state.content;
    const lines = content.split('\n');

    // LibStub pattern (outside strings/comments)
    const libStubPattern = /LibStub\s*\(\s*["']([^"']+)["']\s*(?:,\s*\w+)?\s*\)/g;
    let match;

    while ((match = libStubPattern.exec(content)) !== null) {
      if (this.isInStringOrComment(content, match.index)) continue;

      const lineNum = content.substring(0, match.index).split('\n').length;
      const libName = match[1];
      const libMigration = LIBRARY_MIGRATIONS.find((m) => m.libraryName === libName);

      state.issues.push(this.createIssue(state, {
        category: 'libstub',
        severity: 'warning',
        message: 'LibStub is deprecated',
        location: {
          start: { line: lineNum, column: 0, offset: match.index },
          end: { line: lineNum, column: match[0]?.length ?? 0, offset: match.index + (match[0]?.length ?? 0) },
        },
        oldCode: match[0] ?? '',
        suggestedFix: libMigration?.globalVariable ?? libName?.replace(/-/g, ''),
        autoFixable: true,
        confidence: 0.9,
      }));
    }

    // Font path pattern
    const fontPattern = /["']([^"']+)\.(ttf|otf)(\|[^"']*)?["']/gi;
    while ((match = fontPattern.exec(content)) !== null) {
      const lineNum = content.substring(0, match.index).split('\n').length;

      state.issues.push(this.createIssue(state, {
        category: 'font_path',
        severity: 'warning',
        message: 'Font path uses old format',
        location: {
          start: { line: lineNum, column: 0, offset: match.index },
          end: { line: lineNum, column: match[0]?.length ?? 0, offset: match.index + (match[0]?.length ?? 0) },
        },
        oldCode: match[0] ?? '',
        suggestedFix: match[0]?.replace(/\.(ttf|otf)/gi, '.slug'),
        autoFixable: true,
        confidence: 0.95,
      }));
    }
  }

  private isInStringOrComment(content: string, position: number): boolean {
    // Simple check - look backwards for string/comment start
    const before = content.substring(Math.max(0, position - 200), position);

    // Check for line comment
    const lastNewline = before.lastIndexOf('\n');
    const lineContent = lastNewline >= 0 ? before.substring(lastNewline) : before;
    if (lineContent.includes('--') && !lineContent.includes(']]')) {
      return true;
    }

    // Check for block comment (simple check)
    const blockStart = before.lastIndexOf('--[[');
    const blockEnd = before.lastIndexOf(']]');
    if (blockStart > blockEnd) {
      return true;
    }

    // Check for string literals (basic check)
    let inString = false;
    let stringChar = '';
    for (let i = 0; i < before.length; i++) {
      const char = before[i];
      if (!inString && (char === '"' || char === "'")) {
        inString = true;
        stringChar = char ?? '';
      } else if (inString && char === stringChar && before[i - 1] !== '\\') {
        inString = false;
      }
    }

    return inString;
  }

  // ============================================================================
  // Helper Functions
  // ============================================================================

  private extractFunctionName(node: LuaCallExpression): string | null {
    const base = node.base;

    if (base.type === 'Identifier') {
      return (base as LuaIdentifier).name;
    }

    if (base.type === 'MemberExpression') {
      const member = base as LuaMemberExpression;
      const baseName = this.extractFunctionName({ ...node, base: member.base } as LuaCallExpression);
      if (baseName) {
        return `${baseName}${member.indexer}${member.identifier.name}`;
      }
      return member.identifier.name;
    }

    return null;
  }

  private nodeToSourceRange(node: LuaNode): SourceRange {
    const loc = node.loc;
    const range = node.range;

    return {
      start: {
        line: loc?.start.line ?? 1,
        column: loc?.start.column ?? 0,
        offset: range?.[0] ?? 0,
      },
      end: {
        line: loc?.end.line ?? 1,
        column: loc?.end.column ?? 0,
        offset: range?.[1] ?? 0,
      },
    };
  }

  private extractSourceCode(content: string, range: SourceRange): string {
    return content.substring(range.start.offset, range.end.offset);
  }

  private createIssue(
    state: AnalyzerState,
    params: Omit<Issue, 'id' | 'filePath'>
  ): Issue {
    return {
      id: `issue-${++state.issueIdCounter}`,
      filePath: state.filePath,
      ...params,
    };
  }
}

// ============================================================================
// Convenience Functions
// ============================================================================

export async function analyzeLuaFile(filePath: string): Promise<FileAnalysisResult> {
  const analyzer = new LuaAnalyzer();
  return analyzer.analyzeFile(filePath);
}
