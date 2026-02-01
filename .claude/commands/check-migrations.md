---
description: Show available ESO API migrations and their details
allowed-tools: Bash(node*), Read
---

# Context
- Migration database: data/migrations/eso-api-migrations.json
- Tool location: tools/addon-fixer/

# Task
Display information about available API migrations:

1. **List all migrations**:
   ```bash
   cd tools/addon-fixer && node dist/cli.js migrations
   ```

2. **Show migration details** by category if requested:
   - Function migrations (deprecated API calls)
   - Library migrations (LibStub replacements)
   - Event migrations (renamed events)
   - Pattern migrations (code patterns to update)

3. **Filter by version** if specified:
   - Show only migrations for a specific API version
   - Example: "migrations for 101041" shows font path changes

4. **Console compatibility info**:
   ```bash
   cd tools/addon-fixer && node dist/cli.js info
   ```

Use $ARGUMENTS to filter (e.g., "libstub", "fonts", "101041", "console").
