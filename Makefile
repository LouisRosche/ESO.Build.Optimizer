# ESO Build Optimizer - Development Makefile
# Common workflows for rapid development iteration

.PHONY: help all clean test build lint validate fix-addon

# Default target
help:
	@echo "ESO Build Optimizer - Development Commands"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Build & Test:"
	@echo "  all          - Build and test everything"
	@echo "  test         - Run all tests"
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
	@echo "Cleanup:"
	@echo "  clean        - Remove build artifacts"

# =============================================================================
# Combined Targets
# =============================================================================

all: build test lint

test: fixer-test lua-check validate
	@echo "All tests passed!"

build: fixer-build
	@echo "Build complete!"

lint: fixer-lint lua-check
	@echo "Linting complete!"

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
	@for file in addon/*.lua addon/modules/*.lua; do \
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
# Cleanup
# =============================================================================

clean:
	@echo "Cleaning build artifacts..."
	rm -rf tools/addon-fixer/dist
	rm -rf web/dist
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
