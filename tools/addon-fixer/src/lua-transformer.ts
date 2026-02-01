/**
 * Lua code transformer for ESO addon fixer.
 *
 * Uses luaparse for parsing and string manipulation for transformation.
 * Luaparse doesn't have a code generator, so we use source ranges
 * to perform precise string replacements.
 */

import * as luaparse from 'luaparse';
import { readFile, writeFile } from 'node:fs/promises';
import type {
  FixChange,
  FileFixResult,
  SourceRange,
  FunctionMigration,
  LibraryMigration,
} from './types.js';
import { loadMigrations, type MigrationDatabase } from './migration-loader.js';

// ============================================================================
// Types
// ============================================================================

interface PendingChange {
  start: number;
  end: number;
  oldCode: string;
  newCode: string;
  reason: string;
  confidence: number;
}

interface TransformContext {
  content: string;
  changes: FixChange[];
  pendingChanges: PendingChange[]; // Collect changes before applying
  filePath: string;
  config: TransformConfig;
  migrations: MigrationDatabase;
}

interface TransformConfig {
  fixLibStub: boolean;
  fixDeprecatedFunctions: boolean;
  fixFontPaths: boolean;
  fixPatterns: boolean;
  confidenceThreshold: number;
}

// ============================================================================
// Main Transformer
// ============================================================================

export class LuaTransformer {
  private migrations: MigrationDatabase | null = null;

  async initialize(): Promise<void> {
    this.migrations = await loadMigrations();
  }

  async transformFile(
    filePath: string,
    config: Partial<TransformConfig> = {},
    dryRun: boolean = false
  ): Promise<FileFixResult> {
    if (!this.migrations) {
      await this.initialize();
    }

    const fullConfig: TransformConfig = {
      fixLibStub: true,
      fixDeprecatedFunctions: true,
      fixFontPaths: true,
      fixPatterns: true,
      confidenceThreshold: 0.8,
      ...config,
    };

    let content: string;
    try {
      content = await readFile(filePath, 'utf-8');
    } catch {
      try {
        content = await readFile(filePath, 'latin1');
      } catch (e) {
        return {
          filePath,
          fileType: 'lua',
          changes: [],
          errors: [`Failed to read file: ${e}`],
          wasModified: false,
        };
      }
    }

    const ctx: TransformContext = {
      content,
      changes: [],
      pendingChanges: [],
      filePath,
      config: fullConfig,
      migrations: this.migrations!,
    };

    const errors: string[] = [];

    // Try AST-based transformation first
    try {
      const ast = luaparse.parse(content, {
        locations: true,
        ranges: true,
        comments: true,
        luaVersion: '5.1',
      });

      this.transformAST(ctx, ast);
      // Apply collected changes in reverse order (from end to start)
      this.applyPendingChanges(ctx);
    } catch (e) {
      // Fall back to regex-based transformation
      errors.push(`AST parsing failed, using regex fallback: ${e}`);
      this.transformWithRegex(ctx);
    }

    // Apply pattern-based transformations (font paths, etc.)
    if (fullConfig.fixFontPaths) {
      this.transformFontPaths(ctx);
    }

    if (fullConfig.fixPatterns) {
      this.transformPatterns(ctx);
    }

    // Write if not dry run and changes were made
    const wasModified = ctx.changes.length > 0 && !dryRun;
    if (wasModified) {
      try {
        await writeFile(filePath, ctx.content, 'utf-8');
      } catch (e) {
        errors.push(`Failed to write file: ${e}`);
      }
    }

    return {
      filePath,
      fileType: 'lua',
      changes: ctx.changes,
      errors,
      wasModified,
    };
  }

  // ============================================================================
  // AST-Based Transformation
  // ============================================================================

  private transformAST(ctx: TransformContext, node: luaparse.Node): void {
    if (!node || typeof node !== 'object') return;

    switch (node.type) {
      case 'CallExpression':
        this.transformCallExpression(ctx, node);
        break;
    }

    // Recursively visit child nodes
    for (const key of Object.keys(node)) {
      const value = (node as Record<string, unknown>)[key];
      if (Array.isArray(value)) {
        for (const child of value) {
          if (child && typeof child === 'object' && 'type' in child) {
            this.transformAST(ctx, child as luaparse.Node);
          }
        }
      } else if (value && typeof value === 'object' && 'type' in value) {
        this.transformAST(ctx, value as luaparse.Node);
      }
    }
  }

  private transformCallExpression(ctx: TransformContext, node: luaparse.Node): void {
    const callNode = node as unknown as {
      base: { type: string; name?: string; identifier?: { name: string }; range?: [number, number] };
      arguments: Array<{ type: string; value?: string; raw?: string }>;
      range?: [number, number];
    };

    // Check for LibStub calls
    if (ctx.config.fixLibStub) {
      const baseName = this.getNodeName(callNode.base);
      if (baseName === 'LibStub' && callNode.arguments.length > 0) {
        const firstArg = callNode.arguments[0];
        if (firstArg?.type === 'StringLiteral') {
          // luaparse may return null for value, so extract from raw (which includes quotes)
          const libName = firstArg.value ?? firstArg.raw?.slice(1, -1);
          if (!libName) return;
          // Normalize library name: case-insensitive, strip version suffix (e.g., "-2.0")
          const normalizedLibName = libName.toLowerCase().replace(/-\d+(\.\d+)?$/, '');
          const libMigration = ctx.migrations.libraryMigrations.find(
            (m) => m.name.toLowerCase().replace(/-\d+(\.\d+)?$/, '') === normalizedLibName ||
                   m.name.toLowerCase() === libName.toLowerCase()
          );

          // Use migration global variable, or generate one from library name
          const globalVar = libMigration?.globalVariable ?? libName.replace(/-[\d.]+$/, '').replace(/-/g, '');
          if (callNode.range) {
            this.collectChange(ctx, {
              start: callNode.range[0],
              end: callNode.range[1],
              oldCode: ctx.content.substring(callNode.range[0], callNode.range[1]),
              newCode: globalVar,
              reason: `Replace LibStub("${libName}") with ${globalVar}`,
              confidence: libMigration ? 0.95 : 0.85,
            });
          }
        }
      }
    }

    // Check for deprecated function calls
    if (ctx.config.fixDeprecatedFunctions) {
      const funcName = this.getNodeName(callNode.base);
      if (funcName) {
        const migration = ctx.migrations.functionMigrations.find(
          (m) => m.oldName === funcName
        );

        if (
          migration &&
          migration.autoFixable &&
          migration.confidence >= ctx.config.confidenceThreshold &&
          migration.type === 'renamed' &&
          migration.newName
        ) {
          // Get the range of just the function name, not the whole call
          const baseNode = callNode.base as { range?: [number, number] };
          if (baseNode.range) {
            this.collectChange(ctx, {
              start: baseNode.range[0],
              end: baseNode.range[1],
              oldCode: ctx.content.substring(baseNode.range[0], baseNode.range[1]),
              newCode: migration.newName,
              reason: `Rename ${funcName} to ${migration.newName}`,
              confidence: migration.confidence,
            });
          }
        }
      }
    }
  }

  private getNodeName(node: { type: string; name?: string; identifier?: { name: string } }): string | null {
    if (node.type === 'Identifier' && node.name) {
      return node.name;
    }
    if (node.type === 'MemberExpression' && node.identifier?.name) {
      return node.identifier.name;
    }
    return null;
  }

  // ============================================================================
  // Regex-Based Transformation (Fallback)
  // ============================================================================

  private transformWithRegex(ctx: TransformContext): void {
    // LibStub patterns
    if (ctx.config.fixLibStub) {
      const libStubPattern = /LibStub\s*\(\s*["']([^"']+)["']\s*(?:,\s*\w+)?\s*\)/g;
      let match;

      while ((match = libStubPattern.exec(ctx.content)) !== null) {
        const libName = match[1];
        const libMigration = ctx.migrations.libraryMigrations.find(
          (m) => m.name === libName
        );

        if (libMigration) {
          this.collectChange(ctx, {
            start: match.index,
            end: match.index + match[0].length,
            oldCode: match[0],
            newCode: libMigration.globalVariable,
            reason: `Replace LibStub("${libName}") with ${libMigration.globalVariable}`,
            confidence: 0.9,
          });
        }
      }
    }

    // Deprecated function renames
    if (ctx.config.fixDeprecatedFunctions) {
      for (const migration of ctx.migrations.functionMigrations) {
        if (
          migration.autoFixable &&
          migration.type === 'renamed' &&
          migration.newName &&
          migration.confidence >= ctx.config.confidenceThreshold
        ) {
          const pattern = new RegExp(`\\b${this.escapeRegex(migration.oldName)}\\b`, 'g');
          let match;

          while ((match = pattern.exec(ctx.content)) !== null) {
            // Skip if inside string literal or comment
            if (this.isInStringOrComment(ctx.content, match.index)) {
              continue;
            }

            this.collectChange(ctx, {
              start: match.index,
              end: match.index + match[0].length,
              oldCode: migration.oldName,
              newCode: migration.newName,
              reason: `Rename ${migration.oldName} to ${migration.newName}`,
              confidence: migration.confidence * 0.9, // Lower confidence for regex
            });
          }
        }
      }
    }

    // Apply all collected changes
    this.applyPendingChanges(ctx);
  }

  // ============================================================================
  // Pattern Transformations
  // ============================================================================

  private transformFontPaths(ctx: TransformContext): void {
    ctx.pendingChanges = []; // Clear for this phase
    const fontPattern = /(["'])([^"']+)\.(ttf|otf)(\|[^"']*)?(\1)/gi;
    let match;

    while ((match = fontPattern.exec(ctx.content)) !== null) {
      const oldPath = match[0];
      const newPath = oldPath.replace(/\.(ttf|otf)/gi, '.slug');

      if (oldPath !== newPath) {
        this.collectChange(ctx, {
          start: match.index,
          end: match.index + match[0].length,
          oldCode: oldPath,
          newCode: newPath,
          reason: 'Convert font path from TTF/OTF to Slug format',
          confidence: 0.95,
        });
      }
    }

    this.applyPendingChanges(ctx);
  }

  private transformPatterns(ctx: TransformContext): void {
    ctx.pendingChanges = []; // Clear for this phase
    for (const pattern of ctx.migrations.patternMigrations) {
      if (
        pattern.autoFixable &&
        pattern.confidence >= ctx.config.confidenceThreshold
      ) {
        try {
          // Check if pattern looks like a regex (contains unescaped regex metacharacters)
          const regexMetaChars = /[|[\]+*?^${}]|\\[dDwWsSbB]/;
          const isRegexPattern = regexMetaChars.test(pattern.pattern);

          if (!isRegexPattern) {
            // Simple string replacement
            let pos = 0;
            while ((pos = ctx.content.indexOf(pattern.pattern, pos)) !== -1) {
              // Skip if in comment
              const lineStart = ctx.content.lastIndexOf('\n', pos) + 1;
              const lineContent = ctx.content.substring(lineStart, pos);
              if (lineContent.includes('--')) {
                pos++;
                continue;
              }

              this.collectChange(ctx, {
                start: pos,
                end: pos + pattern.pattern.length,
                oldCode: pattern.pattern,
                newCode: pattern.replacement,
                reason: pattern.notes,
                confidence: pattern.confidence,
              });
              pos++;
            }
          } else {
            // Regex-based replacement
            const regex = new RegExp(pattern.pattern, 'g');
            let match;

            while ((match = regex.exec(ctx.content)) !== null) {
              // Skip if in comment
              const lineStart = ctx.content.lastIndexOf('\n', match.index) + 1;
              const lineContent = ctx.content.substring(lineStart, match.index);
              if (lineContent.includes('--')) {
                continue;
              }

              const newCode = match[0].replace(
                new RegExp(pattern.pattern),
                pattern.replacement
              );

              if (match[0] !== newCode) {
                this.collectChange(ctx, {
                  start: match.index,
                  end: match.index + match[0].length,
                  oldCode: match[0],
                  newCode,
                  reason: pattern.notes,
                  confidence: pattern.confidence,
                });
              }
            }
          }
        } catch {
          // Invalid regex pattern, skip
        }
      }
    }

    this.applyPendingChanges(ctx);
  }

  // ============================================================================
  // Change Collection and Application
  // ============================================================================

  /**
   * Collect a change for later application (used with AST traversal)
   */
  private collectChange(ctx: TransformContext, change: PendingChange): void {
    ctx.pendingChanges.push(change);
  }

  /**
   * Apply all pending changes in reverse order (from end to start).
   * This avoids offset tracking issues.
   */
  private applyPendingChanges(ctx: TransformContext): void {
    // Sort by start position descending (apply from end to start)
    const sorted = [...ctx.pendingChanges].sort((a, b) => b.start - a.start);

    for (const change of sorted) {
      // Apply the change directly (no offset needed since we go from end to start)
      ctx.content =
        ctx.content.substring(0, change.start) +
        change.newCode +
        ctx.content.substring(change.end);

      // Record the change
      ctx.changes.push({
        location: {
          start: { line: 0, column: 0, offset: change.start },
          end: { line: 0, column: 0, offset: change.end },
        },
        oldCode: change.oldCode,
        newCode: change.newCode,
        reason: change.reason,
        confidence: change.confidence,
      });
    }
  }

  /**
   * Apply a single change immediately (used with regex fallback).
   * Uses offset tracking for sequential application.
   */
  private applyChangeImmediate(
    ctx: TransformContext,
    change: PendingChange,
    offset: number
  ): number {
    const adjustedStart = change.start + offset;
    const adjustedEnd = change.end + offset;

    ctx.content =
      ctx.content.substring(0, adjustedStart) +
      change.newCode +
      ctx.content.substring(adjustedEnd);

    ctx.changes.push({
      location: {
        start: { line: 0, column: 0, offset: change.start },
        end: { line: 0, column: 0, offset: change.end },
      },
      oldCode: change.oldCode,
      newCode: change.newCode,
      reason: change.reason,
      confidence: change.confidence,
    });

    return offset + change.newCode.length - (change.end - change.start);
  }

  // ============================================================================
  // Helpers
  // ============================================================================

  private isInStringOrComment(content: string, position: number): boolean {
    const before = content.substring(Math.max(0, position - 500), position);

    // Check for line comment
    const lastNewline = before.lastIndexOf('\n');
    const lineContent = lastNewline >= 0 ? before.substring(lastNewline) : before;
    const dashDashPos = lineContent.indexOf('--');
    if (dashDashPos >= 0 && !lineContent.substring(dashDashPos).startsWith('--[[')) {
      return true;
    }

    // Check for block comment
    const blockStart = before.lastIndexOf('--[[');
    const blockEnd = before.lastIndexOf(']]');
    if (blockStart > blockEnd) {
      return true;
    }

    // Check for string literals
    let inString = false;
    let stringChar = '';
    for (let i = 0; i < before.length; i++) {
      const char = before[i];
      const prevChar = before[i - 1];

      if (!inString && (char === '"' || char === "'")) {
        inString = true;
        stringChar = char;
      } else if (inString && char === stringChar && prevChar !== '\\') {
        inString = false;
      }
    }

    return inString;
  }

  private escapeRegex(str: string): string {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
}

// ============================================================================
// Convenience Function
// ============================================================================

export async function transformLuaFile(
  filePath: string,
  config?: Partial<TransformConfig>,
  dryRun?: boolean
): Promise<FileFixResult> {
  const transformer = new LuaTransformer();
  await transformer.initialize();
  return transformer.transformFile(filePath, config, dryRun);
}
