# ESO Addon Fixer (TypeScript)

Automated tool for fixing broken Elder Scrolls Online addons. Uses AST-based Lua parsing for precision detection and fixing.

## Features

- **AST-Based Analysis**: Uses `luaparse` for accurate Lua code analysis
- **Confidence Scoring**: Each detection has a confidence level (0.0-1.0)
- **False Positive Prevention**: Maintains a whitelist of valid current functions
- **TypeScript**: Fully typed for safety and IDE support
- **Modern CLI**: Beautiful output with colors and spinners

## Installation

```bash
cd tools/addon-fixer
npm install
npm run build
```

## Usage

```bash
# Analyze an addon
npx eso-addon-fixer analyze /path/to/MyAddon

# Fix an addon (creates backup)
npx eso-addon-fixer fix /path/to/MyAddon

# Fix and package for distribution
npx eso-addon-fixer fix /path/to/MyAddon -o /output/dir

# Dry run (preview changes)
npx eso-addon-fixer fix /path/to/MyAddon --dry-run

# List known API migrations
npx eso-addon-fixer migrations

# Show API version info
npx eso-addon-fixer info
```

## Key Improvements Over Python Version

### 1. AST-Based Lua Analysis

Instead of regex, uses `luaparse` to build an Abstract Syntax Tree:

```typescript
// Can distinguish function calls from definitions
CallExpression: { base: Identifier('GetUnitVeteranRank'), arguments: [...] }

// Properly handles string literals and comments
StringLiteral: { value: 'GetUnitVeteranRank', ... } // Won't be flagged
```

### 2. Confidence Scoring

Each migration has a confidence level:

```typescript
{
  oldName: 'GetUnitVeteranRank',
  newName: 'GetUnitChampionPoints',
  confidence: 1.0,  // Definite, always safe to fix
  autoFixable: true,
}
```

Only migrations meeting the threshold (default 0.8) are auto-fixed.

### 3. False Positive Prevention

Functions that work fine in current API are whitelisted:

```typescript
const VALID_CURRENT_FUNCTIONS = new Set([
  'GetPlayerStat',   // Signature changed but still works
  'GetUnitPower',    // Return value changed but backward compatible
  'GetSlotBoundId',  // Works fine
  // ...
]);
```

### 4. Strict Typing

All types are strictly defined:

```typescript
interface FunctionMigration {
  readonly oldName: string;
  readonly migrationType: MigrationType;
  readonly newName?: string;
  readonly confidence: number;
  readonly autoFixable: boolean;
  // ...
}
```

## Architecture

```
src/
├── types.ts           # Type definitions
├── migrations.ts      # Migration database with confidence
├── lua-analyzer.ts    # AST-based Lua analysis
├── manifest-parser.ts # Manifest parsing and fixing
├── fixer.ts           # Main orchestrator
├── cli.ts             # Command-line interface
└── __tests__/         # Test files
```

## Migration Database

### Function Migrations

| Function | Replacement | Confidence | Auto-Fix |
|----------|-------------|------------|----------|
| `GetUnitVeteranRank` | `GetUnitChampionPoints` | 1.0 | Yes |
| `GetUnitVeteranPoints` | (removed) | 1.0 | No |
| `IsUnitVeteran` | `GetUnitChampionPoints() > 0` | 0.9 | No |
| `SearchTradingHouse` | `ExecuteTradingHouseSearch` | 0.9 | Yes |

### Library Migrations

| Library | Global Variable |
|---------|-----------------|
| LibAddonMenu-2.0 | `LibAddonMenu2` |
| LibFilters-3.0 | `LibFilters3` |
| LibCustomMenu | `LibCustomMenu` |
| LibGPS3 | `LibGPS3` |

## Testing

```bash
npm test                 # Run tests
npm run test:watch       # Watch mode
npm run test:coverage    # With coverage
```

## Development

```bash
npm run dev      # Watch mode compilation
npm run build    # Production build
npm run lint     # ESLint
npm run typecheck # TypeScript check
```

## Comparison: Python vs TypeScript

| Feature | Python Version | TypeScript Version |
|---------|----------------|-------------------|
| Lua Parsing | Regex-based | AST-based (luaparse) |
| Confidence | None | Per-migration (0.0-1.0) |
| False Positives | Common | Prevented via whitelist |
| Type Safety | Runtime only | Compile-time |
| Performance | Good | Better (V8) |
| CLI UX | Basic | Rich (chalk, ora) |

## License

MIT
