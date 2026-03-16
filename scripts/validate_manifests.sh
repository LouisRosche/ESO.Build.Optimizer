#!/usr/bin/env bash
# Validate ESO addon manifests (.txt for PC, .addon for console) are in sync
# and that all referenced files exist with correct casing.
set -euo pipefail

ADDON_DIR="addon"
TXT_MANIFEST="$ADDON_DIR/ESOBuildOptimizer.txt"
ADDON_MANIFEST="$ADDON_DIR/ESOBuildOptimizer.addon"

errors=0

# --- 1. Check both manifests exist ---
for f in "$TXT_MANIFEST" "$ADDON_MANIFEST"; do
    if [ ! -f "$f" ]; then
        echo "ERROR: Manifest not found: $f"
        errors=$((errors + 1))
    fi
done

if [ "$errors" -gt 0 ]; then
    echo "FAIL: Missing manifest file(s). Cannot continue."
    exit 1
fi

# --- 2. Compare content (normalize line endings) ---
# Convert both to LF for comparison
txt_normalized=$(sed 's/\r$//' "$TXT_MANIFEST")
addon_normalized=$(sed 's/\r$//' "$ADDON_MANIFEST")

if [ "$txt_normalized" != "$addon_normalized" ]; then
    echo "ERROR: Manifests have different content (ignoring line endings)."
    echo ""
    echo "--- Diff (.txt vs .addon, line endings normalized) ---"
    tmp_txt=$(mktemp)
    tmp_addon=$(mktemp)
    sed 's/\r$//' "$TXT_MANIFEST" > "$tmp_txt"
    sed 's/\r$//' "$ADDON_MANIFEST" > "$tmp_addon"
    diff --unified --label ".txt" --label ".addon" "$tmp_txt" "$tmp_addon" || true
    rm -f "$tmp_txt" "$tmp_addon"
    echo "---"
    echo ""
    echo "The .txt (PC) and .addon (console) manifests must have identical content."
    echo "Update both files to match, then re-run CI."
    errors=$((errors + 1))
else
    echo "OK: .txt and .addon manifest content matches."
fi

# --- 3. Extract file references and verify they exist ---
# File references are lines that don't start with "##" and are not blank.
file_list=$(sed 's/\r$//' "$TXT_MANIFEST" | grep -v '^##' | grep -v '^[[:space:]]*$' || true)

if [ -z "$file_list" ]; then
    echo "WARNING: No file references found in manifest."
else
    echo ""
    echo "Checking file references from manifest..."
    while IFS= read -r ref; do
        # Trim whitespace
        ref=$(echo "$ref" | xargs)
        [ -z "$ref" ] && continue

        expected_path="$ADDON_DIR/$ref"

        # Check file exists
        if [ ! -f "$expected_path" ]; then
            echo "ERROR: File listed in manifest does not exist: $expected_path"
            errors=$((errors + 1))
            continue
        fi

        # --- 4. Case-sensitive path check (PlayStation requirement) ---
        # Resolve the actual path on disk and compare to what the manifest says.
        # Use find to get the exact casing from the filesystem.
        dir_part=$(dirname "$ref")
        base_part=$(basename "$ref")

        if [ "$dir_part" = "." ]; then
            search_dir="$ADDON_DIR"
        else
            search_dir="$ADDON_DIR/$dir_part"
        fi

        # Find the actual file in that directory with exact name match
        actual=$(find "$search_dir" -maxdepth 1 -name "$base_part" -print 2>/dev/null | head -1)

        if [ -z "$actual" ]; then
            echo "ERROR: Case mismatch - file not found with exact casing: $expected_path"
            errors=$((errors + 1))
        else
            # Compare the full relative path (from addon/) to detect directory casing issues too
            actual_rel="${actual#$ADDON_DIR/}"
            if [ "$actual_rel" != "$ref" ]; then
                echo "ERROR: Case mismatch for '$ref' - actual path on disk is '$actual_rel'"
                errors=$((errors + 1))
            else
                echo "  OK: $ref"
            fi
        fi
    done <<< "$file_list"
fi

echo ""
if [ "$errors" -gt 0 ]; then
    echo "FAIL: Manifest validation found $errors error(s)."
    exit 1
else
    echo "PASS: All manifest checks passed."
fi
