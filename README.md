# Otto

**Otto** is a Python CLI tool for monitoring and orchestrating Docker containers with enhanced error handling and type safety.

[![CI/CD Pipeline](https://github.com/lolosioann/otto/actions/workflows/ci.yml/badge.svg)](https://github.com/lolosioann/otto/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://lolosioann.github.io/otto/)

## Features

- **Type-safe Docker SDK wrapper** with full mypy coverage
- **Custom exception hierarchy** with detailed error context
- **Context manager support** for safe resource cleanup
- **NumPy-style docstrings** throughout
- **Comprehensive documentation** with tested code examples
- **Pre-commit hooks** for code quality (ruff, bandit, mypy, interrogate)
- **CI/CD pipeline** with documentation testing and GitHub Pages deployment

## Quick Start

### Prerequisites

- Python 3.10+
- Docker daemon (local or remote)
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Clone repository
git clone <repo-url>
cd otto

# Install dependencies and set up dev environment
make install

# Or manually
uv sync --all-extras
pre-commit install
```

### Usage

```python
from docker_handler import DockerClientWrapper

# Connect to Docker daemon
with DockerClientWrapper() as client:
    # Check connection
    if client.ping():
        print("✓ Connected to Docker")

    # List running containers
    containers = client.list_containers()
    for container in containers:
        print(f"{container.name}: {container.status}")
```

See the [full documentation](https://lolosioann.github.io/otto/) for more examples.

## Development

### Quick Commands (Makefile)

```bash
make help              # Show all available commands
make install           # Install deps and pre-commit hooks
make test              # Run tests
make coverage          # Run tests with coverage report
make lint              # Run ruff linter
make format            # Format code with ruff
make type-check        # Run mypy type checking
make docs              # Build HTML documentation
make docs-serve        # Build and open docs in browser
make docs-test         # Test code examples in docs
make spell-check       # Spell-check documentation
make pre-commit        # Run all pre-commit hooks
make ci                # Run all CI checks locally
make commit-check      # Verify everything before commit
make clean             # Remove build artifacts
```

### Manual Commands

```bash
# Code quality
uv run ruff format src/
uv run ruff check src/ --fix
uv run mypy src/
uv run bandit -r src -c pyproject.toml

# Testing
uv run pytest --cov=src --cov-report=term-missing

# Documentation
uv run sphinx-build -b html docs docs/_build/html
uv run sphinx-build -b doctest docs docs/_build/doctest
uv run sphinx-build -b spelling docs docs/_build/spelling
```

### Pre-commit Hooks

Automatically run on every commit:
- **ruff** - Linting and formatting
- **bandit** - Security scanning
- **interrogate** - Docstring coverage (≥80%)
- **mypy** - Type checking (strict mode)
- Standard checks (trailing whitespace, YAML/TOML validation, etc.)

Run manually: `make pre-commit` or `pre-commit run --all-files`

## Project Structure

```
otto/
├── src/
│   ├── __init__.py
│   └── docker_handler/           # Docker SDK wrapper
│       ├── __init__.py
│       ├── client.py             # Main client class
│       └── exceptions.py         # Custom exceptions
├── docs/                         # Sphinx documentation
│   ├── index.rst                 # Main page
│   ├── quickstart.rst            # Getting started
│   ├── guides/                   # User guides
│   └── api/                      # API reference
├── tests/                        # Test suite (to be implemented)
├── Makefile                      # Common dev commands
├── pyproject.toml                # Project config
├── uv.lock                       # Locked dependencies
├── CONTRIBUTING.md               # Development guidelines
└── SETUP.md                      # Manual setup steps
```

## Documentation

Documentation is built with Sphinx and includes:
- **Narrative guides** (error handling, context managers, etc.)
- **API reference** with auto-generated docstrings
- **Tested code examples** (doctest ensures examples work)
- **Cross-references** to Python stdlib and Docker SDK
- **Spell-checking** for quality assurance

Build locally: `make docs-serve`

View online: [https://lolosioann.github.io/otto/](https://lolosioann.github.io/otto/)

## CI/CD Pipeline

Automated checks on every push to `develop`/`main`:

1. **Pre-commit hooks** (ruff, bandit, interrogate, mypy)
2. **Unit tests** with coverage (Python 3.11 & 3.12)
3. **Type checking** (mypy strict mode)
4. **Documentation build** (fails on warnings)
5. **Documentation spell-check**
6. **Documentation doctest** (tests code examples)

On push to `main`:
- **Automatic deployment** to GitHub Pages

## Code Quality Standards

- **Type hints**: Mandatory on all functions and class attributes
- **Docstrings**: NumPy-style, ≥80% coverage (enforced by interrogate)
- **Test coverage**: ≥85% (when tests implemented)
- **Code style**: PEP 8 via ruff (100 char line length)
- **Security**: Bandit scanning in CI
- **Documentation**: More than just docstrings - guides, tutorials, examples

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

Key points:
- Use `make commit-check` before committing
- Write more than docstrings - include guides for new features
- Test all code examples with doctest
- NumPy-style docstrings required
- Type hints mandatory

## Manual Setup

See [SETUP.md](SETUP.md) for manual setup steps including:
- Installing system dependencies (enchant for spell-checking)
- Enabling GitHub Pages
- Verifying local setup

## License

MIT License - see [LICENSE](LICENSE) file.

## Architecture

Otto uses a layered architecture:

- **docker_handler**: Docker SDK wrapper with enhanced error handling
  - Custom exception hierarchy with detailed context
  - Type-safe API with full mypy coverage
  - Context manager protocol for safe cleanup

Future modules (planned):
- **CLI interface**: Command-line tool for container management
- **Edge agent**: Lightweight monitoring agent
- **Orchestrator**: Container coordination and scheduling

## Current Status

**Version**: 0.1.0 (early development)

Implemented:
- ✅ Docker client wrapper with error handling
- ✅ Custom exception hierarchy
- ✅ Context manager support
- ✅ Type-safe API
- ✅ Comprehensive documentation
- ✅ CI/CD pipeline
- ✅ Pre-commit hooks

To be implemented:
- ⏳ Test suite (structure ready, 85% coverage requirement set)
- ⏳ CLI interface
- ⏳ Container lifecycle operations (start, stop, restart)
- ⏳ Container monitoring and stats
- ⏳ Multi-container orchestration

## Questions?

- Check the [documentation](https://lolosioann.github.io/otto/)
- Read [CONTRIBUTING.md](CONTRIBUTING.md)
- Open an [issue](https://github.com/lolosioann/otto/issues)
