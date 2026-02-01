/**
 * Snapshot tests for Lua transformations
 *
 * These tests ensure transformation outputs remain consistent across changes.
 * If a snapshot changes unexpectedly, it indicates a regression.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { LuaTransformer } from '../lua-transformer.js';

let transformer: LuaTransformer;

beforeAll(async () => {
  transformer = new LuaTransformer();
  await transformer.initialize();
});

describe('Lua Transformations - Snapshots', () => {
  describe('LibStub Patterns', () => {
    it('transforms basic LibStub call', () => {
      const input = `local LAM = LibStub("LibAddonMenu-2.0")`;
      const result = transformer.transformCode(input, 'test.lua');
      expect(result.code).toMatchInlineSnapshot(`"local LAM = LibAddonMenu2"`);
      expect(result.changes).toHaveLength(1);
    });

    it('transforms LibStub:GetLibrary pattern', () => {
      // Note: LibStub:GetLibrary pattern uses member expression - handled by regex fallback
      const input = `local LAM = LibStub:GetLibrary("LibAddonMenu-2.0", true)`;
      const result = transformer.transformCode(input, 'test.lua');
      // Current implementation handles this via regex pattern matching
      expect(result.code).toMatchInlineSnapshot(`"local LAM = LibAddonMenu2"`);
    });

    it('transforms multiple LibStub calls', () => {
      const input = `local LAM = LibStub("LibAddonMenu-2.0")
local LF = LibStub("LibFilters-3.0")
local LCM = LibStub("LibCustomMenu")`;
      const result = transformer.transformCode(input, 'test.lua');
      expect(result.code).toMatchInlineSnapshot(`
        "local LAM = LibAddonMenu2
        local LF = LibFilters3
        local LCM = LibCustomMenu"
      `);
      expect(result.changes).toHaveLength(3);
    });

    it('preserves non-LibStub code', () => {
      const input = `local function DoSomething()
    local x = 42
    return x * 2
end`;
      const result = transformer.transformCode(input, 'test.lua');
      expect(result.code).toBe(input);
      expect(result.changes).toHaveLength(0);
    });
  });

  describe('Font Path Patterns', () => {
    it('transforms .ttf to .slug', () => {
      const input = `label:SetFont("MyAddon/fonts/custom.ttf|16|soft-shadow-thin")`;
      const result = transformer.transformCode(input, 'test.lua');
      expect(result.code).toMatchInlineSnapshot(
        `"label:SetFont("MyAddon/fonts/custom.slug|16|soft-shadow-thin")"`
      );
    });

    it('transforms .otf to .slug', () => {
      const input = `label:SetFont("MyAddon/fonts/custom.otf|16")`;
      const result = transformer.transformCode(input, 'test.lua');
      expect(result.code).toMatchInlineSnapshot(
        `"label:SetFont("MyAddon/fonts/custom.slug|16")"`
      );
    });

    it('preserves ESO font constants', () => {
      const input = `label:SetFont("$(MEDIUM_FONT)|$(KB_18)|soft-shadow-thin")`;
      const result = transformer.transformCode(input, 'test.lua');
      // Font constants should remain unchanged
      expect(result.code).toBe(input);
    });

    it('transforms multiple font paths', () => {
      const input = `local FONTS = {
    header = "MyAddon/fonts/header.ttf|24",
    body = "MyAddon/fonts/body.ttf|16",
}`;
      const result = transformer.transformCode(input, 'test.lua');
      expect(result.code).toMatchInlineSnapshot(`
        "local FONTS = {
            header = "MyAddon/fonts/header.slug|24",
            body = "MyAddon/fonts/body.slug|16",
        }"
      `);
    });
  });

  describe('Deprecated Function Patterns', () => {
    it('transforms GetUnitVeteranRank', () => {
      const input = `local vr = GetUnitVeteranRank("player")`;
      const result = transformer.transformCode(input, 'test.lua');
      expect(result.code).toMatchInlineSnapshot(
        `"local vr = GetUnitChampionPoints("player")"`
      );
    });
  });

  describe('Complex Real-World Examples', () => {
    it('transforms typical addon initialization', () => {
      const input = `-- MyAddon initialization
local addon = {}
addon.name = "MyAddon"

local LAM = LibStub("LibAddonMenu-2.0")

function addon:Initialize()
    self.label:SetFont("MyAddon/fonts/main.ttf|18")
end`;
      const result = transformer.transformCode(input, 'test.lua');
      expect(result.code).toMatchInlineSnapshot(`
        "-- MyAddon initialization
        local addon = {}
        addon.name = "MyAddon"

        local LAM = LibAddonMenu2

        function addon:Initialize()
            self.label:SetFont("MyAddon/fonts/main.slug|18")
        end"
      `);
      expect(result.changes.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('Edge Cases', () => {
    it('handles empty input', () => {
      const result = transformer.transformCode('', 'test.lua');
      expect(result.code).toBe('');
      expect(result.changes).toHaveLength(0);
    });

    it('handles code with only comments', () => {
      const input = `-- This is a comment
-- Another comment`;
      const result = transformer.transformCode(input, 'test.lua');
      expect(result.code).toBe(input);
      expect(result.changes).toHaveLength(0);
    });

    it('preserves already-migrated code', () => {
      const input = `local LAM = LibAddonMenu2 -- Already using global`;
      const result = transformer.transformCode(input, 'test.lua');
      expect(result.code).toBe(input);
      expect(result.changes).toHaveLength(0);
    });
  });
});

describe('Transformation Metrics', () => {
  it('counts changes correctly', () => {
    const input = `local LAM = LibStub("LibAddonMenu-2.0")
local LF = LibStub("LibFilters-3.0")
label:SetFont("path/font.ttf|16")`;
    const result = transformer.transformCode(input, 'test.lua');
    expect(result.changes.length).toBeGreaterThanOrEqual(3);

    const reasons = result.changes.map(c => c.reason);
    expect(reasons.some(r => r.includes('LibStub'))).toBe(true);
  });

  it('provides location info for changes', () => {
    const input = `local LAM = LibStub("LibAddonMenu-2.0")`;
    const result = transformer.transformCode(input, 'test.lua');
    expect(result.changes[0].location).toBeDefined();
  });
});
