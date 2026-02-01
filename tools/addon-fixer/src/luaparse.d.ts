/**
 * Type declarations for luaparse
 */

declare module 'luaparse' {
  export interface ParseOptions {
    locations?: boolean;
    ranges?: boolean;
    comments?: boolean;
    luaVersion?: '5.1' | '5.2' | '5.3' | 'LuaJIT';
    onCreateNode?: (node: Node) => void;
    onCreateScope?: () => void;
    onDestroyScope?: () => void;
  }

  export interface Node {
    type: string;
    range?: [number, number];
    loc?: {
      start: { line: number; column: number };
      end: { line: number; column: number };
    };
    [key: string]: unknown;
  }

  export interface Chunk extends Node {
    type: 'Chunk';
    body: Statement[];
    comments?: Comment[];
  }

  export interface Statement extends Node {}
  export interface Expression extends Node {}

  export interface Comment extends Node {
    type: 'Comment';
    value: string;
    raw: string;
  }

  export interface Identifier extends Node {
    type: 'Identifier';
    name: string;
  }

  export interface CallExpression extends Node {
    type: 'CallExpression';
    base: Expression;
    arguments: Expression[];
  }

  export interface MemberExpression extends Node {
    type: 'MemberExpression';
    base: Expression;
    identifier: Identifier;
    indexer: '.' | ':';
  }

  export interface StringLiteral extends Node {
    type: 'StringLiteral';
    value: string;
    raw: string;
  }

  export function parse(code: string, options?: ParseOptions): Chunk;
}
