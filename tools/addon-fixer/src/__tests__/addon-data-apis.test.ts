/**
 * Tests for addon data APIs and synergy analysis.
 */

import { describe, it, expect } from 'vitest';
import {
  ADDON_DATA_APIS,
  findDataSynergies,
  getAddonsByDataType,
  getIntegrationSuggestions,
  getAddonDataAPI,
  findConsumers,
  getDataDependencyGraph,
} from '../addon-data-apis.js';

describe('ADDON_DATA_APIS', () => {
  it('contains expected addons', () => {
    const names = ADDON_DATA_APIS.map(a => a.name);

    expect(names).toContain('Combat Metrics');
    expect(names).toContain('Master Merchant');
    expect(names).toContain('Inventory Insight');
    expect(names).toContain('Dressing Room');
  });

  it('all addons have required fields', () => {
    for (const addon of ADDON_DATA_APIS) {
      expect(addon.name).toBeTruthy();
      expect(addon.esouiId).toBeGreaterThan(0);
      expect(addon.primaryFunction).toBeTruthy();
      expect(Array.isArray(addon.exposedData)).toBe(true);
      expect(Array.isArray(addon.consumesFrom)).toBe(true);
      expect(Array.isArray(addon.knownIntegrations)).toBe(true);
    }
  });

  it('all exposed data points have required fields', () => {
    for (const addon of ADDON_DATA_APIS) {
      for (const data of addon.exposedData) {
        expect(data.name).toBeTruthy();
        expect(data.accessMethod).toBeTruthy();
        expect(data.accessPath).toBeTruthy();
        expect(data.dataType).toBeTruthy();
        expect(data.description).toBeTruthy();
        expect(typeof data.realtime).toBe('boolean');
      }
    }
  });

  it('has data points for combat tracking', () => {
    const cmx = ADDON_DATA_APIS.find(a => a.name === 'Combat Metrics');
    expect(cmx).toBeDefined();
    expect(cmx!.exposedData.length).toBeGreaterThan(0);

    const hasDps = cmx!.exposedData.some(d =>
      d.name.toLowerCase().includes('fight') || d.name.toLowerCase().includes('dps')
    );
    expect(hasDps).toBe(true);
  });

  it('has data points for price tracking', () => {
    const mm = ADDON_DATA_APIS.find(a => a.name === 'Master Merchant');
    expect(mm).toBeDefined();
    expect(mm!.exposedData.length).toBeGreaterThan(0);

    const hasPrice = mm!.exposedData.some(d =>
      d.name.toLowerCase().includes('price')
    );
    expect(hasPrice).toBe(true);
  });
});

describe('getAddonDataAPI', () => {
  it('finds addon by exact name', () => {
    const api = getAddonDataAPI('Combat Metrics');
    expect(api).toBeDefined();
    expect(api!.name).toBe('Combat Metrics');
  });

  it('finds addon case-insensitively', () => {
    const api = getAddonDataAPI('combat metrics');
    expect(api).toBeDefined();
    expect(api!.name).toBe('Combat Metrics');
  });

  it('returns undefined for unknown addon', () => {
    const api = getAddonDataAPI('NonexistentAddon');
    expect(api).toBeUndefined();
  });
});

describe('getAddonsByDataType', () => {
  it('finds combat addons', () => {
    const addons = getAddonsByDataType('combat');
    expect(addons.length).toBeGreaterThan(0);

    const names = addons.map(a => a.name);
    expect(names).toContain('Combat Metrics');
  });

  it('finds price addons', () => {
    const addons = getAddonsByDataType('price');
    expect(addons.length).toBeGreaterThan(0);

    const names = addons.map(a => a.name);
    expect(names).toContain('Master Merchant');
  });

  it('finds inventory addons', () => {
    const addons = getAddonsByDataType('inventory');
    expect(addons.length).toBeGreaterThan(0);

    const names = addons.map(a => a.name);
    expect(names).toContain('Inventory Insight');
  });

  it('returns empty array for unknown type', () => {
    const addons = getAddonsByDataType('nonexistent' as 'combat');
    expect(addons).toHaveLength(0);
  });
});

describe('findDataSynergies', () => {
  it('finds synergy opportunities', () => {
    const synergies = findDataSynergies();
    expect(synergies.length).toBeGreaterThan(0);
  });

  it('all synergies have required fields', () => {
    const synergies = findDataSynergies();

    for (const synergy of synergies) {
      expect(synergy.sourceAddon).toBeTruthy();
      expect(synergy.targetAddon).toBeTruthy();
      expect(synergy.dataPoint).toBeTruthy();
      expect(synergy.synergyType).toBeTruthy();
      expect(synergy.description).toBeTruthy();
      expect(synergy.implementationComplexity).toBeTruthy();
    }
  });

  it('includes build-performance correlation', () => {
    const synergies = findDataSynergies();
    const buildPerf = synergies.find(s =>
      s.sourceAddon === 'Combat Metrics' && s.targetAddon === 'Dressing Room'
    );

    expect(buildPerf).toBeDefined();
    expect(buildPerf!.synergyType).toBe('correlation');
  });

  it('includes set value aggregation', () => {
    const synergies = findDataSynergies();
    const valueAgg = synergies.find(s =>
      s.sourceAddon === 'IIfA' && s.targetAddon === 'Master Merchant'
    );

    expect(valueAgg).toBeDefined();
    expect(valueAgg!.synergyType).toBe('aggregation');
  });

  it('excludes synergies that are already native to addons', () => {
    const synergies = findDataSynergies();

    // MM + TTC already integrate natively - should not be listed
    const mmTtc = synergies.find(s =>
      s.sourceAddon === 'Master Merchant' && s.targetAddon === 'Tamriel Trade Centre'
    );
    expect(mmTtc).toBeUndefined();

    // FTC buff uptime is already tracked by Combat Metrics natively
    const ftcCmx = synergies.find(s =>
      s.sourceAddon === 'FTC' && s.targetAddon === 'Combat Metrics' &&
      s.dataPoint.includes('buff')
    );
    expect(ftcCmx).toBeUndefined();
  });

  it('has various synergy types', () => {
    const synergies = findDataSynergies();
    const types = new Set(synergies.map(s => s.synergyType));

    expect(types.has('correlation')).toBe(true);
    expect(types.has('enhancement')).toBe(true);
    expect(types.has('automation')).toBe(true);
    expect(types.has('aggregation')).toBe(true);
  });
});

describe('getIntegrationSuggestions', () => {
  it('finds suggestions for Combat Metrics', () => {
    const suggestions = getIntegrationSuggestions('Combat Metrics');
    expect(suggestions.length).toBeGreaterThan(0);

    const partners = suggestions.map(s =>
      s.sourceAddon === 'Combat Metrics' ? s.targetAddon : s.sourceAddon
    );
    expect(partners).toContain('Dressing Room');
  });

  it('finds suggestions for Master Merchant', () => {
    const suggestions = getIntegrationSuggestions('Master Merchant');
    expect(suggestions.length).toBeGreaterThan(0);
  });

  it('returns empty for addon with no synergies', () => {
    const suggestions = getIntegrationSuggestions('Unknown Addon');
    expect(suggestions).toHaveLength(0);
  });
});

describe('findConsumers', () => {
  it('finds addons that consume from LibAddonMenu', () => {
    const consumers = findConsumers('LibAddonMenu-2.0');
    expect(consumers.length).toBeGreaterThan(0);

    // Most addons should depend on LAM
    const names = consumers.map(c => c.name);
    expect(names).toContain('Combat Metrics');
  });

  it('finds addons that consume from LibGPS', () => {
    const consumers = findConsumers('LibGPS3');
    expect(consumers.length).toBeGreaterThan(0);

    const names = consumers.map(c => c.name);
    expect(names).toContain('Harvest Map');
  });
});

describe('getDataDependencyGraph', () => {
  it('returns a map', () => {
    const graph = getDataDependencyGraph();
    expect(graph instanceof Map).toBe(true);
  });

  it('includes known addons', () => {
    const graph = getDataDependencyGraph();
    expect(graph.has('Combat Metrics')).toBe(true);
    expect(graph.has('Master Merchant')).toBe(true);
  });

  it('shows LibAddonMenu as common dependency', () => {
    const graph = getDataDependencyGraph();
    let lamDependencyCount = 0;

    for (const deps of graph.values()) {
      if (deps.has('LibAddonMenu-2.0')) {
        lamDependencyCount++;
      }
    }

    expect(lamDependencyCount).toBeGreaterThan(5);
  });
});
