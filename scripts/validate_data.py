#!/usr/bin/env python3
"""
Data validation script for ESO Build Optimizer.

Validates JSON data files against schemas and checks for common issues.
"""

import json
import sys
from pathlib import Path
from typing import Any

# Try to import jsonschema for schema validation
try:
    from jsonschema import Draft7Validator, ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    print("Warning: jsonschema not installed. Schema validation disabled.")
    print("Install with: pip install jsonschema")


def load_json_file(path: Path) -> tuple[Any, list[str]]:
    """Load a JSON file and return (data, errors)."""
    errors = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data, errors
    except json.JSONDecodeError as e:
        errors.append(f"JSON parse error: {e}")
        return None, errors
    except Exception as e:
        errors.append(f"Read error: {e}")
        return None, errors


def validate_feature_data(data: list[dict], filename: str) -> list[str]:
    """Validate feature data for common issues."""
    errors = []
    warnings = []

    if not isinstance(data, list):
        errors.append(f"{filename}: Expected array, got {type(data).__name__}")
        return errors

    seen_ids = set()
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            errors.append(f"{filename}[{i}]: Expected object, got {type(item).__name__}")
            continue

        # Check required fields
        if 'feature_id' not in item:
            errors.append(f"{filename}[{i}]: Missing required field 'feature_id'")
        else:
            fid = item['feature_id']
            if fid in seen_ids:
                errors.append(f"{filename}[{i}]: Duplicate feature_id '{fid}'")
            seen_ids.add(fid)

        if 'name' not in item:
            errors.append(f"{filename}[{i}]: Missing required field 'name'")
        elif not item['name'] or not item['name'].strip():
            errors.append(f"{filename}[{i}]: Empty 'name' field")

        if 'system' not in item:
            warnings.append(f"{filename}[{i}]: Missing 'system' field")

        if 'category' not in item:
            warnings.append(f"{filename}[{i}]: Missing 'category' field")

    return errors + warnings


def validate_against_schema(data: list[dict], schema: dict, filename: str) -> list[str]:
    """Validate data against JSON schema."""
    if not HAS_JSONSCHEMA:
        return []

    errors = []
    validator = Draft7Validator(schema)

    for i, item in enumerate(data):
        item_errors = list(validator.iter_errors(item))
        for error in item_errors:
            path = '.'.join(str(p) for p in error.path) if error.path else 'root'
            errors.append(f"{filename}[{i}].{path}: {error.message}")

    return errors


def main():
    """Main validation routine."""
    data_dir = Path(__file__).parent.parent / 'data' / 'raw'
    schema_dir = Path(__file__).parent.parent / 'data' / 'schemas'

    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        sys.exit(1)

    # Load schemas
    schemas = {}
    if schema_dir.exists():
        for schema_file in schema_dir.glob('*.schema.json'):
            schema_data, errs = load_json_file(schema_file)
            if schema_data:
                schema_name = schema_file.stem.replace('.schema', '')
                schemas[schema_name] = schema_data
                print(f"Loaded schema: {schema_name}")

    # Validate data files
    total_errors = 0
    total_warnings = 0
    total_entries = 0

    print("\n" + "="*60)
    print("Validating JSON data files...")
    print("="*60 + "\n")

    for json_file in sorted(data_dir.glob('*.json')):
        print(f"Checking {json_file.name}...")

        data, load_errors = load_json_file(json_file)
        if load_errors:
            for err in load_errors:
                print(f"  ✗ {err}")
            total_errors += len(load_errors)
            continue

        if isinstance(data, list):
            total_entries += len(data)
            print(f"  Entries: {len(data)}")

        # Run validation
        validation_errors = validate_feature_data(data, json_file.name)

        # Schema validation if available
        if 'feature' in schemas:
            schema_errors = validate_against_schema(data, schemas['feature'], json_file.name)
            validation_errors.extend(schema_errors)

        if validation_errors:
            errors = [e for e in validation_errors if not e.startswith("Warning")]
            warnings = [e for e in validation_errors if e.startswith("Warning")]

            total_errors += len(errors)
            total_warnings += len(warnings)

            for err in errors[:5]:  # Limit output
                print(f"  ✗ {err}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more errors")

            for warn in warnings[:3]:
                print(f"  ! {warn}")
        else:
            print(f"  ✓ Valid")

    # Summary
    print("\n" + "="*60)
    print("Validation Summary")
    print("="*60)
    print(f"Total entries: {total_entries}")
    print(f"Errors: {total_errors}")
    print(f"Warnings: {total_warnings}")

    if total_errors > 0:
        print("\n✗ Validation FAILED")
        sys.exit(1)
    else:
        print("\n✓ Validation PASSED")
        sys.exit(0)


if __name__ == '__main__':
    main()
