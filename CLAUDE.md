# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Connors Downloader is a financial data downloader library that supports multiple data sources (stocks, forex, crypto) with a unified interface. It provides both a CLI tool and a programmatic Python API.

## Development Commands

### Installation
```bash
# Install in development mode with all dependencies
pip install -e ".[dev]"
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=connors_downloader

# Run specific test file
pytest tests/test_download_service.py

# Run specific test function
pytest tests/test_download_service.py::test_function_name
```

### Code Quality
```bash
# Format code with black
black connors_downloader tests

# Sort imports with isort
isort connors_downloader tests

# Type checking with mypy
mypy connors_downloader

# Linting with flake8
flake8 connors_downloader
```

### Running the CLI
```bash
# Basic usage (installed as editable package)
connors-download --datasource yfinance --ticker AAPL --timespan 1Y

# Run directly from source
python -m connors_downloader.cli.downloader --datasource yfinance --ticker AAPL
```

## Architecture

### Core Components

**Data Source Registry (`core/registry.py`)**
- Central registry for all data sources using decorator pattern
- Data sources register themselves via `@registry.register_datasource("name")`
- Provides factory method `create_datasource(name, **kwargs)` for instantiation

**Data Source Protocol (`core/datasource.py`)**
- Defines `MarketDataSource` protocol with `fetch()` method
- All data sources must implement: `fetch(symbol, start, end, interval) -> pd.DataFrame`
- Returns DataFrames with lowercase column names: `[open, high, low, close, volume]`
- DatetimeIndex named `'date'`

**Timespan Calculator (`core/timespan.py`)**
- Handles predefined timespans: 1D, 5D, 1W, 2W, 1M, 3M, 6M, YTD, 1Y, 2Y, 3Y, 5Y
- Converts timespans to date ranges
- Special handling for YTD (year-to-date)
- Fallback to custom date ranges when timespan not provided

**Download Service (`services/download_service.py`)**
- High-level interface for downloading financial data
- Orchestrates registry, config manager, and data sources
- Handles file naming, output formats (CSV/JSON), and storage
- Default storage location: `~/.connors/downloads/datasets/` (or `$CONNORS_HOME`)

**Config Manager (`config/manager.py`)**
- Manages market configurations for different regions
- Applies market-specific ticker suffixes (e.g., `.AX` for Australia, `.SA` for Brazil)
- Supports 10 markets: america, australia, brazil, canada, uk, germany, japan, hong_kong, india, crypto

### Data Sources

Each datasource is a separate module in `datasources/` that registers itself:

**yfinance** (`datasources/yfinance.py`)
- Free Yahoo Finance data, no API key required
- Supports: stocks, ETFs, indices globally
- Intervals: 1d, 1wk, 1mo

**ccxt** (`datasources/ccxt.py`)
- Cryptocurrency data from 100+ exchanges
- Requires `exchange` parameter (e.g., "binance", "kraken")
- Intervals: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M
- No API key needed for public OHLCV data
- Automatic pagination for large date ranges

**polygon, finnhub, fmp** (API-based, require keys)
- Set via environment variables: `POLYGON_API_KEY`, `FINNHUB_API_KEY`, `FMP_API_KEY`

### Data Flow

1. User provides: datasource, ticker, dates/timespan, interval, market (optional), exchange (optional for ccxt)
2. `DownloadService` validates parameters and calculates date range from timespan if needed
3. Config manager applies market suffix to ticker if applicable
4. Registry creates appropriate datasource instance
5. Datasource fetches data and returns DataFrame with standardized schema
6. Service saves to CSV/JSON with generated filename
7. Returns `DownloadResult` with data, file path, and metadata

### File Naming Convention

Default pattern (without `--include-datasource`):
- Stocks: `{ticker}_{market}_{timeframe|start_end}_{interval}.{csv|json}`
- Crypto: `{ticker}_{exchange}_{timeframe|start_end}_{interval}.{csv|json}`

With `--include-datasource`:
- Stocks: `{ticker}_{market}_{datasource}_{timeframe|start_end}_{interval}.{csv|json}`
- Crypto: `{ticker}_{exchange}_{datasource}_{timeframe|start_end}_{interval}.{csv|json}`

Examples:
- `AAPL_1year_1d.csv` (US stock, 1Y timespan)
- `BHP_australia_1year_1d.csv` (Australian stock)
- `BTC-USDT_binance_1month_1h.csv` (crypto with exchange)

## Important Patterns

### Adding a New Data Source

1. Create file in `connors_downloader/datasources/your_source.py`
2. Import registry: `from connors_downloader.core.registry import registry`
3. Decorate class with: `@registry.register_datasource("your_source")`
4. Implement `fetch(symbol, start, end, interval)` method
5. Return DataFrame with lowercase columns: `[open, high, low, close, volume]`
6. Set DatetimeIndex named `'date'`
7. Import in `services/download_service.py` to ensure registration

### Type Checking

- Project uses strict mypy configuration
- All functions must have type annotations
- Requires Python 3.13+
- Use `typing` module for complex types
- External libraries without stubs are ignored in `[[tool.mypy.overrides]]`

### Testing Strategy

- Tests are in `tests/` directory
- Use pytest fixtures and mocking (`pytest-mock`)
- Coverage target tracked via `pytest-cov`
- Filter warnings via `pyproject.toml` configuration

## Environment Variables

- `CONNORS_HOME`: Override default app directory (`~/.connors`)
- `DOWNLOAD_CONFIG`: Default market configuration (default: "america")
- `POLYGON_API_KEY`: Polygon.io API key
- `FINNHUB_API_KEY`: Finnhub API key
- `FMP_API_KEY`: Financial Modeling Prep API key
- `CCXT_API_KEY`: CCXT API key (optional, for private endpoints)
- `CCXT_SECRET`: CCXT secret (optional, for private endpoints)

## Python Version

This project requires Python 3.13+ as specified in `pyproject.toml`. Ensure compatibility when adding new dependencies or language features.

## GitHub Actions CI/CD

The project uses GitHub Actions for automated testing and deployment.

### Workflows

**CI Pipeline (`.github/workflows/ci.yml`)**
- Triggers on push to `main` and pull requests
- Three parallel jobs after dependency installation:
  1. **Lint and Type Check**: black, isort, flake8, mypy
  2. **Test Suite**: pytest with coverage reports
  3. **Build Package**: builds distribution and validates with twine

**Release (`.github/workflows/release.yml`)**
- Triggers on GitHub releases or manual dispatch
- Builds and publishes to PyPI (requires `PYPI_TOKEN` secret)
- Manual dispatch publishes to Test PyPI (requires `TEST_PYPI_TOKEN` secret)

### Pre-commit Checks

Run these locally before pushing to catch CI failures early:
```bash
# Format and lint
black connors_downloader/ tests/
isort connors_downloader/ tests/
flake8 connors_downloader/ tests/
mypy connors_downloader/

# Test
pytest tests/ --cov=connors_downloader
```
