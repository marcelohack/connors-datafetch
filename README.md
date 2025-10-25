# Connors Downloader

Financial data downloader with support for multiple data sources including stocks, forex, and cryptocurrency markets.

## Features

- **Multiple Data Sources**: yfinance, Polygon.io, Finnhub, FMP, and CCXT (100+ crypto exchanges)
- **Flexible Date Ranges**: Use predefined timespans (1Y, 6M, YTD) or custom date ranges
- **Multiple Markets**: Support for global markets (US, Australia, Brazil, Canada, UK, Germany, Japan, Hong Kong, India)
- **Multiple Formats**: Export to CSV or JSON
- **CLI Tool**: Command-line interface for easy data downloading
- **Programmatic API**: Use as a library in your Python code

## Installation

```bash
pip install connors-downloader
```

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

### CLI Usage

Download stock data:
```bash
# Download 1 year of Apple stock data (default)
connors-download --datasource yfinance --ticker AAPL

# Download with specific timespan
connors-download --datasource yfinance --ticker MSFT --timespan 6M

# Download year-to-date data
connors-download --datasource yfinance --ticker TSLA --timespan YTD

# Download with custom date range
connors-download --datasource yfinance --ticker AAPL \
    --start 2023-01-01 --end 2023-12-31 --interval 1wk

# Download Australian stock with market suffix
connors-download --datasource yfinance --ticker BHP \
    --market australia --timespan 2Y

# Export as JSON
connors-download --datasource yfinance --ticker AAPL \
    --timespan 3M --format json
```

Download cryptocurrency data:
```bash
# Download BTC/USDT from Binance (1 month, 1-hour candles)
connors-download --datasource ccxt --exchange binance \
    --ticker BTC/USDT --interval 1h --timespan 1M

# Download ETH/USD from Kraken (daily candles)
connors-download --datasource ccxt --exchange kraken \
    --ticker ETH/USD --interval 1d \
    --start 2024-01-01 --end 2024-12-31
```

### Programmatic Usage

```python
from connors_downloader.services.download_service import DownloadService

# Initialize service
service = DownloadService()

# Download data
result = service.download_data(
    datasource="yfinance",
    ticker="AAPL",
    timeframe="1Y",  # Use predefined timeframe
    interval="1d"
)

# Access the data
if result.success:
    df = result.data
    print(f"Downloaded {len(df)} records")
    print(f"Saved to: {result.file_path}")
else:
    print(f"Error: {result.error}")

# Or use custom dates
result = service.download_data(
    datasource="yfinance",
    ticker="MSFT",
    start="2023-01-01",
    end="2023-12-31",
    interval="1wk",
    output_format="csv"
)
```

## Available Data Sources

### Free Data Sources

- **yfinance**: Yahoo Finance (no API key required)
  - Supported intervals: 1d, 1wk, 1mo
  - Global coverage for stocks, ETFs, indices

- **ccxt**: Cryptocurrency data from 100+ exchanges (no API key required)
  - Supported intervals: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M
  - Exchanges: Binance, Kraken, Coinbase, Bybit, OKX, and 100+ more

### API-Based Data Sources (Require API Key)

- **polygon**: Polygon.io professional market data
- **finnhub**: Finnhub real-time stock market data
- **fmp**: Financial Modeling Prep data

## Available Markets

- **america**: US stocks (no suffix)
- **australia**: Australian stocks (.AX suffix)
- **brazil**: Brazilian stocks (.SA suffix)
- **canada**: Canadian stocks (.TO suffix)
- **uk**: UK stocks (.L suffix)
- **germany**: German stocks (.DE suffix)
- **japan**: Japanese stocks (.T suffix)
- **hong_kong**: Hong Kong stocks (.HK suffix)
- **india**: Indian stocks (.NS suffix)
- **crypto**: Cryptocurrency markets (via CCXT)

## Predefined Timespans

- `1D`, `5D`, `10D`: Days
- `1W`, `2W`: Weeks
- `1M`, `3M`, `6M`: Months
- `1Y`, `2Y`, `3Y`, `5Y`: Years
- `YTD`: Year to date

## Output

Downloaded files are saved to `~/.connors/downloads/datasets/` (or `$CONNORS_HOME/downloads/datasets/` if set).

Filename format:
- Stocks: `{ticker}_{market}_{start}_{end}_{interval}.{csv|json}`
- Crypto: `{ticker}_{exchange}_{start}_{end}_{interval}.{csv|json}`
- With timeframe: `{ticker}_{market}_{timeframe}_{interval}.{csv|json}`

## CLI Options

```bash
connors-download --help

Options:
  --datasource {yfinance,polygon,finnhub,fmp,ccxt}
                        Data source to use
  --ticker TICKER       Stock ticker symbol or crypto pair (e.g., AAPL, BTC/USDT)
  --exchange EXCHANGE   Exchange for crypto (required with ccxt datasource)
  --market {america,australia,brazil,...}
                        Market configuration for ticker suffix
  --start YYYY-MM-DD    Start date
  --end YYYY-MM-DD      End date
  --timespan {1D,1W,1M,3M,6M,1Y,YTD,...}
                        Predefined timespan
  --interval {1m,5m,15m,1h,1d,1wk,1mo}
                        Data interval (default: 1d)
  --format {csv,json}   Output format (default: csv)
  --output PATH         Custom output file path
  --include-datasource  Include datasource name in filename
  --list-datasources    List available datasources
  --list-markets        List available markets
  -v, --verbose         Verbose output
```

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/connors-downloader.git
cd downloader

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=connors_downloader
```

## License

MIT License

## Related Projects

- **connors-trading**: Full trading strategy backtesting and analysis platform that uses this downloader
