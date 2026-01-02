# Manual Setup Steps

After pulling these changes, complete these manual setup steps.

## 1. Install System Dependencies (Local Development)

### Spell-checking support (enchant)

For spell-checking to work locally, install enchant:

**Arch Linux:**
```bash
sudo pacman -S enchant
```

**Ubuntu/Debian:**
```bash
sudo apt-get install enchant-2
```

**macOS:**
```bash
brew install enchant
```

**Verify installation:**
```bash
python -c "import enchant; print('✓ enchant installed')"
```

## 2. Sync Dependencies

```bash
make install
# OR manually:
uv sync --all-extras
pre-commit install
```

## 3. Enable GitHub Pages (for docs deployment)

**Required for automatic docs deployment to work.**

1. Go to repository Settings → Pages
2. Under "Source", select:
   - **Source**: Deploy from a branch
   - **Branch**: `gh-pages` / `/ (root)`
3. Click **Save**

After the first deployment (on next push to `main`), docs will be at:
```
https://<your-username>.github.io/otto/
```

**Note:** The `gh-pages` branch will be created automatically by the CI/CD pipeline on the first `main` push.

## 4. Verify Local Setup

Run comprehensive checks:

```bash
make ci
```

This runs:
- Pre-commit hooks (ruff, bandit, interrogate, mypy)
- Tests (when implemented)
- Coverage checks
- Documentation build (strict mode)
- Documentation doctest
- Spell-check

Expected output: `✓ All CI checks passed`

## 5. Test Documentation Build

```bash
# Build HTML docs
make docs

# Open in browser
make docs-serve

# Test code examples
make docs-test

# Spell-check
make spell-check
```

All should pass without errors.

## 6. Commit Changes

After verifying everything works:

```bash
# Verify pre-commit
make commit-check

# Stage changes
git add .

# Commit
git commit -m "add comprehensive sphinx docs with testing and github pages"

# Push to develop (CI will run all checks)
git push origin ci-cd-setup
```

## Common Issues

### Issue: Spell-check fails with "Dictionary not found"

**Cause:** enchant not installed or dictionary missing

**Fix:**
```bash
# Install enchant (see step 1)
sudo pacman -S enchant  # Arch
sudo apt-get install enchant-2  # Ubuntu/Debian

# Verify
python -c "import enchant; enchant.Dict('en_US')"
```

### Issue: myst-parser import error

**Cause:** Dependencies not synced

**Fix:**
```bash
make sync
```

### Issue: GitHub Pages not deploying

**Cause:** Pages not enabled in repo settings (see step 3)

**Fix:**
1. Enable Pages in repo settings
2. Push to `main` branch (not develop)
3. Check Actions tab for deployment status

### Issue: Doctest failures

**Cause:** Docker daemon not running

**Fix:**
```bash
# Start Docker
sudo systemctl start docker

# Verify
docker ps
```

## Optional: Add Makefile Autocomplete

For better developer experience, you can add tab-completion:

**Bash:**
```bash
# Add to ~/.bashrc
complete -W "$(make -qp | awk -F':' '/^[a-zA-Z0-9][^$#\/\t=]*:([^=]|$)/ {split($1,A,/ /);for(i in A)print A[i]}' | sort -u)" make
```

**Zsh:**
```bash
# Add to ~/.zshrc
compdef _gnu_generic make
```

## Development Workflow

Daily workflow:

```bash
# Start new feature
git checkout -b feature-name

# Make changes...

# Run checks before committing
make commit-check

# Commit
git commit -m "description"

# Before pushing
make ci

# Push
git push origin feature-name
```

## Troubleshooting

If you encounter issues:

1. **Clean and rebuild:**
   ```bash
   make clean
   make install
   make docs
   ```

2. **Check Python environment:**
   ```bash
   uv run python --version  # Should be 3.10+
   ```

3. **Verify all tools:**
   ```bash
   make check
   ```

4. **Check CI logs:**
   - Go to Actions tab in GitHub
   - Click on failing workflow
   - Review logs for specific errors

## Next Steps

- Review the comprehensive docs: `make docs-serve`
- Read CONTRIBUTING.md for development guidelines
- Implement tests (see pyproject.toml coverage requirements)
- Write narrative documentation for new features

## Questions?

- Check project docs: `docs/`
- Review CONTRIBUTING.md
- Open an issue for bugs/questions
