# Makefile for SMS.py testing and development

.PHONY: help test test-basic test-advanced test-full test-integration test-coverage clean install-deps lint format check-syntax quick dev pre-commit coverage-summary

# Default target
help:
	@echo "SMS.py Development Makefile"
	@echo "=========================="
	@echo ""
	@echo "Available targets:"
	@echo "  help           - Show this help message"
	@echo "  test           - Run basic tests (fastest, default)"
	@echo "  test-basic     - Run basic tests only (~36 tests)"
	@echo "  test-advanced  - Run basic + advanced tests (~40 tests)"
	@echo "  test-full      - Run full test suite (~40 tests, no integration)"
	@echo "  test-integration - Run integration tests only (~8 tests)"
	@echo "  test-coverage  - Run tests with coverage report"
	@echo "  test-sms       - Test SMS.py with auto-enabled debug + strict mode"
	@echo "  quick          - Quick validation with basic tests"
	@echo "  quick-sms      - Quick SMS.py test with auto-enabled features"
	@echo "  install-deps   - Install test dependencies"
	@echo "  check-syntax   - Check Python syntax"
	@echo "  lint           - Run code linting (if available)"
	@echo "  format         - Format code (if black available)"
	@echo "  clean          - Clean up test artifacts"
	@echo "  dev            - Complete development workflow"
	@echo "  pre-commit     - Pre-commit validation"
	@echo ""

# Default test target (basic tests)
test: check-syntax
	@echo "🧪 Running basic tests (default)..."
	@python3 test_sms_unified.py --basic --limit 100

# Test using SMS.py with proper test mode (auto-enables debug + strict mode)
test-sms: check-syntax
	@echo "🧪 Running SMS.py test mode (auto-enables debug + strict mode)..."
	@python3 sms.py --test-mode --test-limit 10 --output-format html

# Run basic tests only (fastest)
test-basic: check-syntax
	@echo "⚡ Running basic tests only (~36 tests)..."
	@python3 test_sms_unified.py --basic --limit 100

# Run advanced tests (basic + advanced)
test-advanced: check-syntax
	@echo "🚀 Running advanced tests (~40 tests)..."
	@python3 test_sms_unified.py --advanced --limit 100

# Run full test suite (no integration)
test-full: check-syntax
	@echo "🎯 Running full test suite (~40 tests)..."
	@python3 test_sms_unified.py --full --limit 100

# Run integration tests only
test-integration: check-syntax
	@echo "🔗 Running integration tests (~8 tests)..."
	@python3 test_sms_unified.py --integration --limit 100

# Run tests with coverage
test-coverage: install-deps check-syntax
	@echo "📊 Running tests with coverage..."
	@python3 -m pytest test_sms_unified.py --cov=sms --cov-report=html --cov-report=term-missing -v

# Quick validation with basic tests
quick: check-syntax
	@echo "⚡ Running quick validation (basic tests, limit 25)..."
	@python3 test_sms_unified.py --basic --limit 25

# Quick SMS.py test (auto-enables debug + strict mode)
quick-sms: check-syntax
	@echo "⚡ Running quick SMS.py test (auto-enables debug + strict mode)..."
	@python3 sms.py --test-mode --test-limit 5 --output-format html

# Development testing with basic tests
dev-test: check-syntax
	@echo "🧪 Running development tests (basic, limit 50)..."
	@python3 test_sms_unified.py --basic --limit 50

# Production testing with full suite
prod-test: check-syntax
	@echo "🏭 Running production tests (full suite, limit 200)..."
	@python3 test_sms_unified.py --full --limit 200

# Install test dependencies
install-deps:
	@echo "📦 Installing test dependencies..."
	@python3 -m pip install -r test_requirements.txt

# Check Python syntax
check-syntax:
	@echo "🔍 Checking Python syntax..."
	@python3 -m py_compile sms.py
	@echo "✅ Syntax check passed"

# Run code linting (if available)
lint:
	@echo "🔍 Running code linting..."
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 sms.py --max-line-length=100 --ignore=E501,W503; \
		echo "✅ Linting passed"; \
	else \
		echo "⚠️  flake8 not found. Install with: pip install flake8"; \
		exit 1; \
	fi

# Format code (if black available)
format:
	@echo "🎨 Formatting code..."
	@if command -v black >/dev/null 2>&1; then \
		black sms.py; \
		echo "✅ Code formatted"; \
	else \
		echo "⚠️  black not found. Install with: pip install black"; \
		exit 1; \
	fi

# Clean up test artifacts
clean:
	@echo "🧹 Cleaning up test artifacts..."
	@rm -rf __pycache__/
	@rm -rf .pytest_cache/
	@rm -rf htmlcov/
	@rm -f .coverage
	@rm -f *.pyc
	@rm -f *.pyo
	@echo "✅ Cleanup complete"

# Development workflow
dev: format lint dev-test
	@echo "🎉 Development checks completed successfully!"

# SMS.py development workflow (with auto-enabled features)
dev-sms: format lint quick-sms
	@echo "🎉 SMS.py development checks completed successfully!"

# Pre-commit checks
pre-commit: check-syntax test-basic
	@echo "✅ Pre-commit checks passed"

# Show test coverage summary
coverage-summary: test-coverage
	@echo "📊 Coverage summary:"
	@if [ -f .coverage ]; then \
		coverage report; \
	else \
		echo "No coverage data found. Run 'make test-coverage' first."; \
	fi

# Legacy compatibility targets
legacy-test: check-syntax
	@echo "⚠️  Running legacy test compatibility..."
	@echo "Note: This runs the deprecated test files for backward compatibility"
	@python3 test_sms_basic.py

legacy-test-full: check-syntax
	@echo "⚠️  Running legacy full test compatibility..."
	@echo "Note: This runs the deprecated test files for backward compatibility"
	@python3 test_sms_unified.py --basic

# Performance testing targets
test-fast: check-syntax
	@echo "⚡ Running fast tests (basic, limit 25)..."
	@python3 test_sms_unified.py --basic --limit 25

test-medium: check-syntax
	@echo "🚀 Running medium tests (advanced, limit 75)..."
	@python3 test_sms_unified.py --advanced --limit 75

test-thorough: check-syntax
	@echo "🎯 Running thorough tests (full + integration, limit 200)..."
	@python3 test_sms_unified.py --full --limit 200
	@python3 test_sms_unified.py --integration --limit 200

# Show test information
test-info:
	@echo "📊 Test Suite Information:"
	@echo "=========================="
	@echo "Basic tests: ~36 tests (fastest)"
	@echo "Advanced tests: ~40 tests (fast)"
	@echo "Full suite: ~40 tests (fast, no integration)"
	@echo "Integration tests: ~8 tests (slow)"
	@echo ""
	@echo "Performance options:"
	@echo "  --limit 25   : Very fast (development)"
	@echo "  --limit 50   : Fast (daily testing)"
	@echo "  --limit 100  : Balanced (default)"
	@echo "  --limit 200  : Thorough (release testing)"
	@echo "  --limit 500+ : Comprehensive (production)"
	@echo ""
	@echo "Examples:"
	@echo "  make test-fast      # Basic tests, limit 25"
	@echo "  make test-medium    # Advanced tests, limit 75"
	@echo "  make test-thorough  # Full suite + integration, limit 200"
	@echo ""
	@echo "SMS.py Test Mode (auto-enables debug + strict mode):"
	@echo "  make test-sms       # Test SMS.py with 10 entries"
	@echo "  make quick-sms      # Test SMS.py with 5 entries"
	@echo "  make dev-sms        # Format + lint + quick SMS.py test"
