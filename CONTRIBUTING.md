# Contributing to Otto

## Development Setup

### Prerequisites
- Python 3.10+
- uv package manager
- Docker (for runtime)
- Git

### Initial Setup
```bash
# Clone repository
git clone <repo-url>
cd otto

# Install dependencies with uv
uv sync --all-extras

# Install pre-commit hooks
pre-commit install
```

## Code Standards

### Python Style
- PEP 8 compliance (enforced by ruff)
- Type hints mandatory on all functions/class attributes
- Docstrings required (Google/NumPy style with Args/Returns/Raises)
- Black-compatible formatting (100 char line length)

### Code Quality Requirements
- All pre-commit hooks must pass
- Type checking with mypy (strict mode)
- Security scanning with bandit
- Docstring coverage ≥80% (interrogate)
- Test coverage ≥85% (when tests exist)

### Architecture Patterns
- Interface/Protocol classes for abstractions
- Dataclasses for data structures
- Context managers for resources
- Exception-based error handling (not return codes)

## Development Workflow

### Git Branching
- Main branches: `develop` (CI checks) → `main` (deployments)
- Feature branches: `feature-name` (lowercase, hyphen-separated)
- Create PRs from feature → develop
- Atomic commits: one logical change per commit
- Rebase over merge for clean history

### Commit Messages
- Terse, direct style
- Focus on "why" over "what"
- Format: `<action> <subject>` (e.g., "fix auth validation", "add container stats endpoint")

### Pre-commit Hooks
Run automatically on `git commit`:
- ruff (linting + formatting)
- bandit (security)
- interrogate (docstrings)
- mypy (type checking)
- Standard checks (trailing whitespace, YAML/TOML validation, etc.)

Manual run:
```bash
pre-commit run --all-files
```

## Development Commands

### Dependency Management
```bash
# Add dependency
uv add package-name

# Add dev dependency
uv add --dev package-name

# Sync after pulling changes
uv sync --all-extras

# Lock file must be committed
git add uv.lock
```

### Code Quality Checks
```bash
# Format code
uv run ruff format src/

# Lint code
uv run ruff check src/ --fix

# Type check
uv run mypy src/

# Security scan
uv run bandit -r src -c pyproject.toml

# Docstring coverage
uv run interrogate -c pyproject.toml src/
```

### Testing
```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=term-missing

# Coverage must be ≥85%
```

### Documentation
```bash
# Build docs locally (HTML)
uv run sphinx-build -b html docs docs/_build/html

# Test code examples in docs
uv run sphinx-build -b doctest docs docs/_build/doctest

# Spell-check documentation
uv run sphinx-build -b spelling docs docs/_build/spelling

# View docs
open docs/_build/html/index.html
```

**Documentation Requirements:**
- Write more than just docstrings - include guides, tutorials, architecture docs
- Use reStructuredText for rich cross-references and directives
- Include working code examples with `.. doctest::` directive
- Test all code examples (doctest runs in CI)
- Spell-check passes (add technical terms to `docs/spelling_wordlist.txt`)
- Cross-reference APIs: `:py:class:`, `:py:func:`, `:py:exc:`
- Link to external docs: Python stdlib, Docker SDK (via intersphinx)

## Before Committing

**Checklist:**
- [ ] Code formatted: `uv run ruff format src/`
- [ ] No lint errors: `uv run ruff check src/`
- [ ] Type checks pass: `uv run mypy src/`
- [ ] Tests pass: `uv run pytest` (when implemented)
- [ ] Pre-commit hooks pass: `pre-commit run --all-files`
- [ ] Documentation builds: `uv run sphinx-build -W -b html docs docs/_build/html`
- [ ] Doctest passes: `uv run sphinx-build -W -b doctest docs docs/_build/doctest`
- [ ] Spell-check passes: `uv run sphinx-build -W -b spelling docs docs/_build/spelling`
- [ ] No debug code (console.log, print statements, commented code)
- [ ] NumPy-style docstrings for new public APIs
- [ ] Type hints on all new functions
- [ ] Guides/tutorials for new features (not just API docs)

## Pull Request Guidelines

### PR Checklist
- [ ] Branch up-to-date with develop
- [ ] All CI checks pass
- [ ] Description explains what/why
- [ ] Breaking changes documented
- [ ] Tests added/updated (when implemented)

### Review Process
- All PRs require review
- Address review feedback via new commits
- Squash/rebase before merge if requested
- Delete feature branch after merge

## CI/CD Pipeline

### Automated Checks (on push to develop/main)
1. **Pre-commit hooks** - ruff, bandit, interrogate, mypy
2. **Tests** - pytest with coverage (Python 3.11 & 3.12)
3. **Type checking** - mypy strict mode
4. **Documentation build** - Sphinx HTML build (fails on warnings)
5. **Documentation spell-check** - sphinxcontrib-spelling
6. **Documentation doctest** - Tests all code examples in docs

### Continuous Deployment
- **GitHub Pages**: Docs auto-deployed to `gh-pages` branch on main push
- View at: `https://<username>.github.io/otto/`

### Pipeline must pass before merge

## Project Structure

```
otto/
├── src/
│   ├── __init__.py
│   └── docker_handler/      # Docker SDK wrapper
│       ├── __init__.py
│       ├── client.py
│       └── exceptions.py
├── docs/                    # Sphinx documentation
├── tests/                   # Pytest test suite (to be implemented)
├── pyproject.toml          # Project config & tool settings
├── uv.lock                 # Locked dependencies
└── .pre-commit-config.yaml # Pre-commit hooks
```

## Error Handling Pattern

```python
def new_method(self, param: str) -> ReturnType:
    """Method description.

    Args:
        param: Parameter description

    Returns:
        Return value description

    Raises:
        ContainerError: When operation fails
    """
    try:
        result = self.client.some_operation(param)
        return result
    except NotFound:
        raise ContainerNotFoundError(
            f"Resource not found: {param}",
            details={"param": param}
        )
    except APIError as e:
        raise ContainerError(
            f"API error: {e}",
            details={"param": param, "error": str(e)}
        )
```

## Questions?

- Check project docs: `docs/`
- Review existing code for patterns
- Ask in PR/issue discussion
