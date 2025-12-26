# Contributing to Otto

## Development Setup

### First-Time Setup

```bash
# Clone repository
git clone https://github.com/lolosioann/otto.git
cd otto

# Install dependencies (production only)
uv sync

# Install with dev dependencies
uv sync --extra dev

# Setup pre-commit hooks (recommended)
uv run pre-commit install
```

### Pre-Commit Hooks (Recommended)

This project uses pre-commit to automatically run code quality checks before each commit.

**Setup:**
```bash
# Install pre-commit hooks after installing dev dependencies
uv run pre-commit install
```

**What it does automatically:**
- Formats code with black
- Lints and fixes issues with ruff
- Type checks with mypy
- Trims trailing whitespace
- Fixes end-of-file
- Validates YAML/TOML files
- Checks for large files

**Manual run (all files):**
```bash
uv run pre-commit run --all-files
```

**Skip hooks (not recommended):**
```bash
git commit --no-verify
```

### Important: Dev Dependencies Installation

The dev dependencies are defined as **optional** in `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "black>=24.0.0",
    "ruff>=0.3.0",
    "mypy>=1.8.0",
    "pre-commit>=4.0.0",
]
```

**Key Point**: You MUST use `--extra dev` flag to install them:

```bash
# Wrong - only installs production dependencies
uv sync --dev

# Correct - installs dev dependencies
uv sync --extra dev
```

## Development Workflow

### Code Quality Tools

Run these before committing:

```bash
# Format code (auto-fixes)
uv run black src/

# Lint code
uv run ruff check src/

# Type check
uv run mypy src/

# Run tests (when implemented)
uv run pytest
```

### Pre-Commit Checklist

**If using pre-commit hooks (recommended):**
All formatting, linting, and type checking happens automatically on `git commit`.

**Manual checklist (if not using pre-commit):**
- [ ] Code formatted with black
- [ ] No ruff lint errors
- [ ] No mypy type errors
- [ ] Tests pass (when implemented)
- [ ] Docstrings updated
- [ ] Type hints on new functions

### Adding Dependencies

```bash
# Production dependency
uv add package-name

# Dev dependency
uv add --dev package-name
```

### Dependency Management with uv

**Always commit both files together:**
- `pyproject.toml` - Dependency specifications
- `uv.lock` - Locked versions

## Code Standards

### Type Hints
- Required on all function signatures
- Use PEP 585 style: `type[BaseException]` not `Type[BaseException]`
- Use `Optional[T]` for nullable types

### Docstrings
- Module-level docstrings required
- Class docstrings with description
- Method docstrings with Args/Returns/Raises sections

### Error Handling
- Catch specific exceptions (NotFound, APIError, DockerException)
- Translate to custom exceptions with context
- Include details dict for debugging

### Example Method Pattern
```python
def method_name(self, param: str) -> ReturnType:
    """Brief description.

    Args:
        param: Parameter description

    Returns:
        Return value description

    Raises:
        ContainerError: When operation fails
    """
    try:
        result = self.client.operation(param)
        return result
    except APIError as e:
        raise ContainerError(
            f"Operation failed: {e}",
            details={"param": param, "error": str(e)}
        )
```

## Project Structure

```
otto/
├── src/
│   ├── __init__.py              # Package root
│   └── docker_handler/
│       ├── __init__.py          # Public API exports
│       ├── client.py            # DockerClientWrapper
│       └── exceptions.py        # Custom exceptions
├── tests/                       # (to be implemented)
├── .gitignore                   # Python ignores
├── pyproject.toml              # Project config
├── README.md                    # User documentation
├── CLAUDE.md                    # AI assistant context
└── CONTRIBUTING.md             # This file
```
