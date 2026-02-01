---
description: Analyze and fix an ESO addon for API compatibility
allowed-tools: Bash(node*), Bash(npm*), Read, Glob
---

# Context
- Current API Version: 101048 (Update 48)
- Tool location: tools/addon-fixer/

# Pre-computed info
- Available test addons: !`ls -1 test-addons/ 2>/dev/null || echo "No test-addons directory"`

# Task
Analyze the specified addon path for compatibility issues and apply fixes.

1. First, run analysis to understand the scope:
   ```bash
   cd tools/addon-fixer && node dist/cli.js analyze $ARGUMENTS
   ```

2. If issues are found, ask user to confirm before fixing

3. Apply fixes with backup:
   ```bash
   cd tools/addon-fixer && node dist/cli.js fix $ARGUMENTS
   ```

4. Report summary of changes made

If no path is provided, list available test addons and ask which to fix.
