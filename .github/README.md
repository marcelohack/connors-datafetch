# GitHub Workflows

This directory contains GitHub Actions workflows for automated CI/CD.

## Workflows

### CI Pipeline (`ci.yml`)

Runs on every push to `main` and on pull requests.

**Jobs:**

1. **Lint and Type Check**
   - Black formatting check
   - isort import sorting check
   - Flake8 linting
   - Mypy static type checking

2. **Test Suite**
   - Runs pytest with coverage
   - Generates coverage reports (XML, HTML, terminal)
   - Uploads HTML coverage report as artifact

3. **Build Package**
   - Builds source distribution and wheel
   - Validates distribution with twine
   - Uploads distribution as artifact

### Release (`release.yml`)

Publishes the package to PyPI.

**Triggers:**
- Automatically when a GitHub release is published
- Manually via workflow_dispatch (publishes to Test PyPI)

**Prerequisites:**
- Set up repository secrets:
  - `PYPI_TOKEN` - PyPI API token for production releases
  - `TEST_PYPI_TOKEN` - Test PyPI API token for manual testing

## Configuration Files

- `.flake8` - Flake8 linting configuration
- `pyproject.toml` - Configuration for Black, isort, mypy, pytest, coverage

## Running Checks Locally

Before pushing, run these commands to catch issues early:

```bash
# Format code
black connors_downloader/ tests/
isort connors_downloader/ tests/

# Run linting
flake8 connors_downloader/ tests/

# Type checking
mypy connors_downloader/

# Run tests with coverage
pytest tests/ --cov=connors_downloader --cov-report=term-missing
```
