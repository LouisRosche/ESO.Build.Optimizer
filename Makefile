# ESO Build Optimizer - Development Makefile
# Common workflows for rapid development iteration

.PHONY: help all clean test build lint validate fix-addon fpt-test fpt-validate fpt-package

# Default target
help:
	@echo "ESO Build Optimizer - Development Commands"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Build & Test:"
	@echo "  all          - Build and test everything"
	@echo "  test         - Run all tests"
	@echo "  pytest       - Run Python unit tests only"
	@echo "  build        - Build all components"
	@echo "  lint         - Run all linters"
	@echo ""
	@echo "Addon Fixer:"
	@echo "  fixer-build  - Build addon fixer"
	@echo "  fixer-test   - Run addon fixer tests"
	@echo "  fixer-watch  - Watch mode for development"
	@echo ""
	@echo "Data:"
	@echo "  validate     - Validate JSON data files"
	@echo "  excel        - Generate Excel compilation"
	@echo ""
	@echo "Lua Addon:"
	@echo "  lua-check    - Lint Lua addon code"
	@echo ""
	@echo "FurnishProfitTargeter:"
	@echo "  fpt-test     - Run FPT pre-publish test suite"
	@echo "  fpt-validate - Run FPT static validator"
	@echo "  fpt-package  - Build FPT ESOUI distribution ZIP"
	@echo ""
	@echo "ESOBuildOptimizer:"
	@echo "  esbo-test    - Run ESBO pre-publish test suite"
	@echo "  esbo-package - Build ESBO ESOUI distribution ZIP"
	@echo ""
	@echo "Database:"
	@echo "  seed         - Seed features/gear into database"
	@echo "  seed-dry     - Count features (no DB write)"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean        - Remove build artifacts"

# =============================================================================
# Combined Targets
# =============================================================================

all: build test lint

test: pytest fixer-test lua-check validate fpt-validate
	@echo "All tests passed!"

build: fixer-build
	@echo "Build complete!"

lint: fixer-lint lua-check
	@echo "Linting complete!"

# =============================================================================
# Python Tests
# =============================================================================

pytest:
	@echo "Running Python tests..."
	pytest tests/ -v --tb=short

# =============================================================================
# Addon Fixer
# =============================================================================

fixer-build:
	@echo "Building addon fixer..."
	cd tools/addon-fixer && npm run build

fixer-test:
	@echo "Testing addon fixer..."
	cd tools/addon-fixer && npm test

fixer-lint:
	@echo "Linting addon fixer..."
	cd tools/addon-fixer && npm run lint

fixer-watch:
	@echo "Starting watch mode..."
	cd tools/addon-fixer && npm run dev

fixer-coverage:
	@echo "Running tests with coverage..."
	cd tools/addon-fixer && npm run test:coverage

# =============================================================================
# Data Validation
# =============================================================================

validate:
	@echo "Validating JSON data files..."
	python scripts/validate_data.py

excel:
	@echo "Generating Excel compilation..."
	python scripts/generate_excel.py

# =============================================================================
# Lua Addon
# =============================================================================

lua-check:
	@echo "Checking Lua syntax..."
	@for file in $$(find addon -name '*.lua' -type f); do \
		echo "  Checking $$file..."; \
		luac -p "$$file" 2>/dev/null || echo "    Warning: $$file has issues"; \
	done
	@echo "Lua check complete!"

lua-lint:
	@echo "Running luacheck..."
	luacheck addon/ --no-unused-args --no-max-line-length 2>/dev/null || true

# =============================================================================
# Fix Addon (CLI wrapper)
# =============================================================================

# Usage: make fix-addon ADDON=/path/to/addon
fix-addon:
ifndef ADDON
	@echo "Usage: make fix-addon ADDON=/path/to/addon"
	@exit 1
endif
	@echo "Analyzing addon: $(ADDON)"
	cd tools/addon-fixer && node dist/cli.js analyze "$(ADDON)"

# =============================================================================
# Library Sync
# =============================================================================

lib-sync:
	@echo "Syncing library versions from ESOUI..."
	cd tools/addon-fixer && npx ts-node scripts/sync-library-versions.ts

lib-check:
	@echo "Checking library versions..."
	cd tools/addon-fixer && npx ts-node scripts/sync-library-versions.ts --check

# =============================================================================
# FurnishProfitTargeter
# =============================================================================

fpt-test:
	@echo "Running FPT pre-publish test suite..."
	python scripts/test_fpt_prepublish.py

fpt-validate:
	@echo "Running FPT static validator..."
	python scripts/validate_fpt_addon.py

fpt-package:
	@echo "Packaging FPT addon for ESOUI..."
	python scripts/package_fpt_addon.py

fpt-package-check:
	@echo "Validating FPT package (dry run)..."
	python scripts/package_fpt_addon.py --check

# =============================================================================
# ESOBuildOptimizer
# =============================================================================

esbo-test:
	@echo "Running ESBO pre-publish test suite..."
	python scripts/test_esbo_prepublish.py

esbo-package:
	@echo "Packaging ESBO addon for ESOUI..."
	python scripts/package_esbo_addon.py

esbo-package-check:
	@echo "Validating ESBO package (dry run)..."
	python scripts/package_esbo_addon.py --check

# =============================================================================
# Database
# =============================================================================

seed:
	@echo "Seeding features and gear sets..."
	python scripts/seed_features.py

seed-dry:
	@echo "Counting features (dry run)..."
	python scripts/seed_features.py --dry-run

# =============================================================================
# Cleanup
# =============================================================================

clean:
	@echo "Cleaning build artifacts..."
	rm -rf tools/addon-fixer/dist
	rm -rf web/dist
	rm -rf dist/
	rm -rf data/compiled/*.xlsx
	@echo "Clean complete!"

# =============================================================================
# Quick Development Shortcuts
# =============================================================================

# Quick build and test cycle
dev: fixer-build fixer-test
	@echo "Development cycle complete!"

# Full CI simulation
ci: clean all
	@echo "CI simulation complete!"
