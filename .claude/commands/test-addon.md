---
description: Run verification suite on an ESO addon after fixing
allowed-tools: Bash(node*), Bash(npm*), Bash(luacheck*), Read, Glob
---

# Context
- Tool location: tools/addon-fixer/
- Verification steps: syntax check, manifest validation, case sensitivity

# Task
Run comprehensive verification on the specified addon:

1. **Lua Syntax Check** (if luacheck available):
   ```bash
   luacheck $ARGUMENTS/*.lua --no-config --codes 2>/dev/null || echo "luacheck not installed"
   ```

2. **Manifest Validation**:
   - Check for .addon file (console compatibility)
   - Verify APIVersion is current (101048)
   - Check file references match actual files (case-sensitive)

3. **Analyze for remaining issues**:
   ```bash
   cd tools/addon-fixer && node dist/cli.js analyze $ARGUMENTS
   ```

4. **Report verification results**:
   - PASS: All checks passed
   - WARN: Minor issues found (list them)
   - FAIL: Critical issues remain (list them)

If verification fails, suggest specific fixes.
