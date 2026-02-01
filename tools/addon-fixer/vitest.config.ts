import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['src/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.ts'],
      exclude: ['src/**/*.test.ts', 'src/cli.ts'],
      // Coverage thresholds - enforce minimum coverage
      thresholds: {
        // Global thresholds
        statements: 60,
        branches: 50,
        functions: 60,
        lines: 60,
        // Per-file thresholds can be more lenient
        perFile: true,
      },
    },
    // Snapshot settings
    snapshotFormat: {
      escapeString: false,
      printBasicPrototype: false,
    },
  },
});
