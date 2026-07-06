# connors-datafetch

> Part of the [Connors Trading System](https://github.com/marcelohack/connors-playground)

## Overview

Financial data downloader with support for multiple data sources including stocks, forex, and cryptocurrency markets. Provides both a standalone CLI (`connors-datafetch`) and integration with the [connors-playground](https://github.com/marcelohack/connors-playground) Streamlit UI.

## Features

- **Multiple Data Sources**: yfinance, Polygon.io, Finnhub, FMP, and CCXT (100+ crypto exchanges)
- **Flexible Date Ranges**: Use predefined timespans (1Y, 6M, YTD) or custom date ranges
- **Multiple Markets**: Support for global markets (US, Australia, Brazil, Canada, UK, Germany, Japan, Hong Kong, India)
- **Multiple Formats**: Export to CSV or JSON
- **CLI Tool**: Command-line interface for easy data downloading
- **Programmatic API**: Use as a library in your Python code

## Installation

```bash
pip install connors-datafetch
```

### Local Development

**Prerequisites**: [uv](https://github.com/astral-sh/uv) (will install Python 3.13 if needed).
Sibling repo must be cloned alongside this one: `../core` (wired as an editable path source via `[tool.uv.sources]`).

```bash
uv sync --extra dev
```

uv reads `.python-version` to pick the interpreter and creates `.venv/` automatically. Run commands with `uv run <cmd>` (no activation needed), or `source .venv/bin/activate`.

### Optional Dependencies

For cryptocurrency data via CCXT:
```bash
pip install ccxt
```

For API-based datasources, you'll need API keys:
- Polygon.io: Set `POLYGON_API_KEY` environment variable
- Finnhub: Set `FINNHUB_API_KEY` environment variable
- FMP: Set `FMP_API_KEY` environment variable

## Quick Start

### Programmatic API

```python
from connors_datafetch.services.datafetch_service import DataFetchService

# Initialize service
service = DataFetchService()

# Download data
result = service.download_data(
    datasource="yfinance",
    ticker="AAPL",
    timeframe="1Y",
    interval="1d"
)

if result.success:
    df = result.data
    print(f"Downloaded {len(df)} records")
    print(f"Saved to: {result.file_path}")
```

### Standalone CLI

```bash
# Download 1 year of Apple stock data
connors-datafetch --datasource yfinance --ticker AAPL

# Download with specific timespan
connors-datafetch --datasource yfinance --ticker MSFT --timespan 6M

# Download with custom date range
connors-datafetch --datasource yfinance --ticker AAPL \
    --start 2023-01-01 --end 2023-12-31 --interval 1wk

# Australian stock with market suffix
connors-datafetch --datasource yfinance --ticker BHP \
    --market australia --timespan 2Y

# Cryptocurrency from Binance
connors-datafetch --datasource ccxt --exchange binance \
    --ticker BTC/USDT --interval 1h --timespan 1M

# Download year-to-date data
connors-datafetch --datasource yfinance --ticker MSFT --timespan YTD

# Different data sources
connors-datafetch --datasource polygon --ticker TSLA --start 2023-06-01 --end 2023-06-30
connors-datafetch --datasource fmp --ticker AAPL --timespan 3M

# List available options
connors-datafetch --list-datasources
connors-datafetch --list-markets
```

The `connors-datafetch` command is installed with the package (`connors_datafetch/cli.py`; also runnable as `python -m connors_datafetch.cli`).

## Available Data Sources

### Free Data Sources

- **yfinance**: Yahoo Finance (no API key required)
  - Supported intervals: 1m, 2m, 5m, 15m, 30m, 90m, 1h, 1d, 1wk, 1mo
  - Intraday limits: 1m (7 days), 5m/15m/30m (60 days), 1h (730 days)
  - Supports `extended_hours` for pre-market/after-hours data
  - Global coverage for stocks, ETFs, indices

- **ccxt**: Cryptocurrency data from 100+ exchanges (no API key required)
  - Supported intervals: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M
  - Exchanges: Binance, Kraken, Coinbase, Bybit, OKX, and 100+ more

### API-Based Data Sources (Require API Key)

- **polygon**: Polygon.io professional market data
  - Supported intervals: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1wk, 1mo
- **finnhub**: Finnhub real-time stock market data
  - Supported intervals: 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo
- **fmp**: Financial Modeling Prep data
  - Supported intervals: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1wk, 1mo

## Available Markets

| Market | Suffix | Example |
|--------|--------|---------|
| `america` | none | `AAPL` |
| `australia` | `.AX` | `BHP.AX` |
| `brazil` | `.SA` | `PETR4.SA` |
| `canada` | `.TO` | `RY.TO` |
| `uk` | `.L` | `BP.L` |
| `germany` | `.DE` | `SAP.DE` |
| `japan` | `.T` | `7203.T` |
| `hong_kong` | `.HK` | `0005.HK` |
| `india` | `.NS` | `RELIANCE.NS` |
| `crypto` | n/a | via CCXT |

## Predefined Timespans

`1D`, `5D`, `10D`, `1W`, `2W`, `1M`, `3M`, `6M`, `YTD`, `1Y`, `2Y`, `3Y`, `5Y`

## Output

Downloaded files are saved to `~/.connors/downloads/datasets/` (or `$CONNORS_HOME/downloads/datasets/` if set).

Filename format:
- Stocks: `{ticker}_{market}_{start}_{end}_{interval}.{csv|json}`
- Crypto: `{ticker}_{exchange}_{start}_{end}_{interval}.{csv|json}`

## Development

```bash
git clone https://github.com/marcelohack/connors-datafetch.git
cd connors-datafetch
uv sync --extra dev

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=connors_datafetch
```

## Related Packages

| Package | Description | Links |
|---------|-------------|-------|
| [connors-playground](https://github.com/marcelohack/connors-playground) | CLI + Streamlit UI (integration hub) | [README](https://github.com/marcelohack/connors-playground#readme) |
| [connors-core](https://github.com/marcelohack/connors-core) | Registry, config, indicators, metrics | [README](https://github.com/marcelohack/connors-core#readme) |
| [connors-backtest](https://github.com/marcelohack/connors-backtest) | Backtesting service + built-in strategies | [README](https://github.com/marcelohack/connors-backtest#readme) |
| [connors-strategies](https://github.com/marcelohack/connors-strategies) | Trading strategy collection (private) | — |
| [connors-screener](https://github.com/marcelohack/connors-screener) | Stock screening system | [README](https://github.com/marcelohack/connors-screener#readme) |
| [connors-sr](https://github.com/marcelohack/connors-sr) | Support & Resistance calculator | [README](https://github.com/marcelohack/connors-sr#readme) |
| [connors-regime](https://github.com/marcelohack/connors-regime) | Market regime detection | [README](https://github.com/marcelohack/connors-regime#readme) |
| [connors-bots](https://github.com/marcelohack/connors-bots) | Automated trading bots | [README](https://github.com/marcelohack/connors-bots#readme) |

## License

MIT
