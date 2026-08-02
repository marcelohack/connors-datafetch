# connors-datafetch

> Part of the [Connors Trading System](https://github.com/marcelohack/connors-playground)

## Overview

Financial data downloader with support for multiple data sources including stocks, forex, and cryptocurrency markets. Provides a standalone CLI (`connors-datafetch`) and a programmatic API used across the Connors packages.

## Features

- **Multiple Data Sources**: yfinance, Polygon.io, Finnhub, FMP, EODHD, Alpaca (US equities incl. intraday), and CCXT (100+ crypto exchanges)
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
- EODHD: Set `EODHD_API_KEY` environment variable
- Alpaca: Set `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` (`ALPACA_API_SECRET` also accepted).
  Optionally `ALPACA_DATA_FEED` (`sip` default, or `iex` for free accounts — see below)

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

A datasource can also be used directly when you need its own options — here Alpaca's
feed and adjustment, which the generic service call doesn't expose:

```python
from connors_datafetch.datasources.alpaca import AlpacaDataSource

# Regular-trading-hours 5m bars for a session strategy
ds = AlpacaDataSource(feed="sip", adjustment="all")
df = ds.fetch("SPY", "2025-08-01", "2026-07-31", "5m")

rth = df.tz_convert("America/New_York").between_time("09:30", "15:55")
print(f"{len(rth):,} RTH bars over {rth.index.normalize().nunique()} sessions")
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
connors-datafetch --datasource eodhd --ticker AAPL --timespan 1Y

# Intraday US equities via Alpaca (a year of 5-minute SPY bars)
connors-datafetch --datasource alpaca --ticker SPY --interval 5m \
    --start 2025-08-01 --end 2026-07-31

# Same, on the free single-venue IEX feed instead of the consolidated tape
ALPACA_DATA_FEED=iex connors-datafetch --datasource alpaca --ticker SPY \
    --interval 5m --timespan 1M

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
  - Indices accept Yahoo's caret prefix (`^GSPC`, `^VIX`) or EODHD-style symbols (`GSPC.INDX`, `VIX.INDX` — converted to the caret form internally); output filenames always use the EODHD-style symbol (`GSPC.INDX_...`) so index files match across datasources

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
- **alpaca**: Alpaca Market Data — **US equities only** (use `ccxt` for crypto)
  - Supported intervals: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1wk, 1mo
  - History back to **2016**, sourced from the CTA and UTP consolidated tapes
  - Credentials: `ALPACA_API_KEY` + `ALPACA_SECRET_KEY` (`ALPACA_API_SECRET` accepted as an alias)
  - **This is the project's intraday equities source.** The alternatives don't work for
    session-based strategies: EODHD rejects intraday on the free plan
    (`403 Only EOD data allowed for free users`), and yfinance caps 5m at roughly 1–2
    months *and* returns exchange-local timestamps labelled UTC. Alpaca returns true
    UTC — `13:30:00Z` is the 09:30 New York open during EDT.
  - **Feed choice changes what the data means.** `sip` (default) is the full
    consolidated tape; `iex` is a single venue carrying roughly 3% of consolidated
    volume. For SPY's 09:30 bar that is ~1.9M shares versus ~50k. Opening ranges,
    session highs/lows and volume filters computed from IEX are *not* what the market
    saw. On a `sip` entitlement failure the datasource **raises rather than falling
    back**, so a plan lapse can't silently swap the tape for a fraction of it. Free
    accounts opt in deliberately with `ALPACA_DATA_FEED=iex` or `feed="iex"`.
    `sip` with unrestricted history requires Alpaca's paid data plan.
  - **Intraday returns extended-hours bars** (04:00–20:00 NY), not just the regular
    session. Consumers wanting regular trading hours only must filter — expect exactly
    78 five-minute bars per RTH session (390 minutes ÷ 5).
  - `adjustment` defaults to `all`; anything less than split adjustment turns historical
    splits into fake price gaps.
  - Pagination is automatic (10,000 bars per request).

- **eodhd**: EODHD end-of-day and intraday market data
  - Supported intervals: 1m, 5m, 1h, 1d, 1wk, 1mo
  - Symbols use EODHD exchange suffixes (e.g. `AAPL.US`, `BHP.AU`); bare tickers default to `.US`
  - Intraday range limits: 1m (120 days), 5m (600 days), 1h (7200 days)
  - **Intraday requires a paid plan** — free keys get `403 Only EOD data allowed for free users`
  - Indices are available via the `INDX` virtual exchange (Yahoo-style codes without the caret):

    | Index | EODHD symbol |
    |-------|--------------|
    | S&P 500 | `GSPC.INDX` |
    | Dow Jones Industrial | `DJI.INDX` |
    | NASDAQ Composite | `IXIC.INDX` |
    | NASDAQ 100 | `NDX.INDX` |
    | CBOE VIX | `VIX.INDX` |
    | S&P/ASX 200 | `AXJO.INDX` |
    | ASX All Ordinaries | `AORD.INDX` |
    | Bovespa (IBOVESPA) | `BVSP.INDX` |
    | FTSE 100 | `FTSE.INDX` |
    | DAX | `GDAXI.INDX` |
    | Nikkei 225 | `N225.INDX` |

    Example: `connors-datafetch --datasource eodhd --ticker GSPC.INDX --timespan 1Y`

    List all available indices: `curl "https://eodhd.com/api/exchange-symbol-list/INDX?api_token=$EODHD_API_KEY&fmt=json"`.
    Note: EOD index data is broadly included in paid plans, but intraday coverage for indices is more limited than for stocks.

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

The filename records the ticker, range and interval but **not the datasource or feed**
unless you pass `--include-datasource`. Two files of the same symbol and interval from
different sources — or from Alpaca's `sip` versus `iex` feed — are indistinguishable by
name and will overwrite each other. Use `--include-datasource` when keeping both.

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
| [connors-playground](https://github.com/marcelohack/connors-playground) | Workspace hub + API token manager | [README](https://github.com/marcelohack/connors-playground#readme) |
| [connors-core](https://github.com/marcelohack/connors-core) | Registry, config, indicators, metrics | [README](https://github.com/marcelohack/connors-core#readme) |
| [connors-backtest](https://github.com/marcelohack/connors-backtest) | Backtesting service + built-in strategies | [README](https://github.com/marcelohack/connors-backtest#readme) |
| [connors-strategies](https://github.com/marcelohack/connors-strategies) | Trading strategy collection (private) | — |
| [connors-screener](https://github.com/marcelohack/connors-screener) | Stock screening system | [README](https://github.com/marcelohack/connors-screener#readme) |
| [connors-sr](https://github.com/marcelohack/connors-sr) | Support & Resistance calculator | [README](https://github.com/marcelohack/connors-sr#readme) |
| [connors-regime](https://github.com/marcelohack/connors-regime) | Market regime detection | [README](https://github.com/marcelohack/connors-regime#readme) |
| [connors-bots](https://github.com/marcelohack/connors-bots) | Automated trading bots | [README](https://github.com/marcelohack/connors-bots#readme) |

## License

MIT
