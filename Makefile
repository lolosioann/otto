.PHONY: help install sync clean test coverage lint format type-check docs docs-serve docs-test spell-check pre-commit all

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Installation & Dependencies
install: ## Install dependencies and pre-commit hooks
	uv sync --all-extras
	pre-commit install
	@echo "✓ Installation complete"

sync: ## Sync dependencies from uv.lock
	uv sync --all-extras
	@echo "✓ Dependencies synced"

# Cleaning
clean: ## Remove build artifacts and caches
	rm -rf docs/_build/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -f .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned build artifacts"

# Testing
test: ## Run tests with pytest
	uv run pytest

coverage: ## Run tests with coverage report
	uv run pytest --cov=src --cov-report=term-missing --cov-report=html
	@echo "✓ Coverage report: htmlcov/index.html"

# Code Quality
lint: ## Run ruff linter
	uv run ruff check src/

lint-fix: ## Run ruff linter with auto-fix
	uv run ruff check src/ --fix
	@echo "✓ Linting complete"

format: ## Format code with ruff
	uv run ruff format src/
	@echo "✓ Code formatted"

type-check: ## Run mypy type checker
	uv run mypy src/
	@echo "✓ Type checking complete"

security: ## Run bandit security scanner
	uv run bandit -r src -c pyproject.toml
	@echo "✓ Security scan complete"

docstrings: ## Check docstring coverage
	uv run interrogate -c pyproject.toml src/
	@echo "✓ Docstring coverage check complete"

# Documentation
docs: ## Build HTML documentation
	uv run sphinx-build -b html docs docs/_build/html
	@echo "✓ Documentation built: docs/_build/html/index.html"

docs-strict: ## Build docs with warnings as errors
	uv run sphinx-build -W -b html docs docs/_build/html
	@echo "✓ Documentation built (strict mode)"

docs-serve: docs ## Build and open documentation in browser
	@command -v xdg-open >/dev/null 2>&1 && xdg-open docs/_build/html/index.html || \
	command -v open >/dev/null 2>&1 && open docs/_build/html/index.html || \
	echo "Please open docs/_build/html/index.html manually"

docs-test: ## Test code examples in documentation
	uv run sphinx-build -b doctest docs docs/_build/doctest
	@echo "✓ Documentation tests passed"

spell-check: ## Spell-check documentation
	uv run sphinx-build -b spelling docs docs/_build/spelling
	@echo "✓ Spell-check complete"

docs-coverage: ## Check documentation coverage
	uv run sphinx-build -b coverage docs docs/_build/coverage
	@cat docs/_build/coverage/python.txt
	@echo "✓ Documentation coverage report generated"

# Pre-commit
pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files
	@echo "✓ Pre-commit checks complete"

pre-commit-update: ## Update pre-commit hook versions
	pre-commit autoupdate
	@echo "✓ Pre-commit hooks updated"

# Comprehensive Checks
check: lint type-check docstrings docs-strict docs-test ## Run all code quality checks
	@echo "✓ All checks passed"

ci: pre-commit test coverage docs-strict docs-test spell-check ## Run all CI checks locally
	@echo "✓ All CI checks passed"

# Development
dev: install ## Set up development environment
	@echo "✓ Development environment ready"

all: clean install lint format type-check test docs ## Clean, install, check, test, and build docs
	@echo "✓ Full build complete"

# Git helpers
commit-check: ## Verify everything before commit
	@echo "Running pre-commit hooks..."
	@pre-commit run --all-files
	@echo "Running type checks..."
	@uv run mypy src/
	@echo "Building documentation..."
	@uv run sphinx-build -W -b html docs docs/_build/html >/dev/null 2>&1
	@uv run sphinx-build -W -b doctest docs docs/_build/doctest >/dev/null 2>&1
	@echo "✓ Ready to commit"

# Dependency management
lock: ## Generate/update uv.lock file
	uv lock
	@echo "✓ Lock file updated"

add: ## Add a dependency (usage: make add PKG=package-name)
	@if [ -z "$(PKG)" ]; then \
		echo "Error: PKG not specified. Usage: make add PKG=package-name"; \
		exit 1; \
	fi
	uv add $(PKG)
	@echo "✓ Added $(PKG)"

add-dev: ## Add a dev dependency (usage: make add-dev PKG=package-name)
	@if [ -z "$(PKG)" ]; then \
		echo "Error: PKG not specified. Usage: make add-dev PKG=package-name"; \
		exit 1; \
	fi
	uv add --dev $(PKG)
	@echo "✓ Added $(PKG) to dev dependencies"
