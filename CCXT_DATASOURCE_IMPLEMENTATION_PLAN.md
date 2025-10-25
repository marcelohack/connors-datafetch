# CCXT Crypto DataSource Implementation Plan

**Date:** 2025-10-18
**Status:** PLANNING
**Branch:** `ccxt_crypto_datasource`

---

## 📋 Executive Summary

Implement a crypto-specific datasource using the [CCXT library](https://github.com/ccxt/ccxt) to download cryptocurrency OHLCV data from multiple exchanges (Binance, Kraken, Coinbase, etc.). The implementation will reuse existing DataSource architecture with minimal disruption while supporting crypto-specific requirements.

**Key Goals:**
1. ✅ Reuse existing `MarketDataSource` Protocol
2. ✅ Support multiple exchanges via `--exchange` parameter
3. ✅ Support crypto-specific intervals (1m, 5m, 15m, 1h, 4h, 12h, 1d, 1w)
4. ✅ Handle timestamp index (crypto standard) vs date index (stocks)
5. ✅ Minimal changes to existing CLI and services

---

## 🏗️ Architecture Analysis

### Existing DataSource Pattern

All datasources follow this pattern:

```python
@registry.register_datasource("datasource_name")
class DataSourceClass:
    """Description"""

    def __init__(self, api_key: Optional[str] = None):
        # Optional: Initialize API clients, sessions, etc.
        pass

    def fetch(
        self, symbol: str, start: str, end: str, interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch OHLCV data"""
        # 1. Map interval to datasource format
        # 2. Fetch data from API
        # 3. Convert to DataFrame with columns: [open, high, low, close, volume]
        # 4. Set index to datetime with name='date'
        # 5. Return normalized DataFrame
```

### Current DataSource Interface

```python
class MarketDataSource(Protocol):
    def fetch(
        self,
        symbol: str,
        start: Union[str, date, datetime],
        end: Union[str, date, datetime],
        interval: str = "1d",
    ) -> pd.DataFrame: ...
```

**Key observations:**
- ✅ Protocol is flexible - no strict base class
- ✅ `__init__` can accept custom parameters
- ✅ Registry passes `**kwargs` to datasource constructor
- ⚠️ Currently no mechanism to pass exchange to `fetch()` method

---

## 🚧 Implementation Challenges

### Challenge 1: Exchange Parameter

**Problem:** Exchange is needed at fetch time, but current interface doesn't support it.

**Solutions:**

#### Option A: Pass exchange in constructor (RECOMMENDED)
```python
@registry.register_datasource("ccxt")
class CCXTDataSource:
    def __init__(self, exchange: str = "binance"):
        self.exchange_id = exchange
        self.exchange = getattr(ccxt, exchange)()

    def fetch(self, symbol: str, start: str, end: str, interval: str = "1d"):
        # Use self.exchange
```

**CLI:**
```bash
python -m connors.cli.downloader \
  --datasource ccxt \
  --datasource-params "exchange:binance" \
  --ticker BTC/USDT \
  --start 2024-01-01 --end 2024-12-31
```

#### Option B: Encode exchange in datasource name
```python
@registry.register_datasource("ccxt_binance")
class CCXTBinanceDataSource:
    ...

@registry.register_datasource("ccxt_kraken")
class CCXTKrakenDataSource:
    ...
```

**CLI:**
```bash
python -m connors.cli.downloader \
  --datasource ccxt_binance \
  --ticker BTC/USDT
```

⚠️ **Downside:** Need to register each exchange separately

#### Option C: Add --exchange CLI parameter (MOST USER-FRIENDLY)
```bash
python -m connors.cli.downloader \
  --datasource ccxt \
  --exchange binance \
  --ticker BTC/USDT
```

**Requires:**
- Add `--exchange` argument to CLI
- Pass exchange via registry kwargs
- Update download_service

**Recommendation:** **Option C** - Best UX, clean separation

---

### Challenge 2: Crypto Intervals

**Problem:** Crypto supports more granular intervals than stocks

**Current intervals:** `1d, 1wk, 1mo`
**Crypto intervals:** `1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M`

**Solution:**
- Add crypto intervals to supported list
- Map to CCXT timeframe format
- Make interval choices dynamic or extended

```python
CCXT_INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "12h": "12h",
    "1d": "1d",
    "1w": "1w",
    "1M": "1M",
}
```

---

### Challenge 3: Timestamp vs Date Index

**Problem:** Crypto data uses `timestamp` column, stocks use `Date` or `date` index

**Current behavior:**
- Polygon: Returns timestamp, converts to `date` index
- YFinance: Returns with datetime index named `Date`

**Solution:**
```python
# In CCXT datasource fetch():
df.index = pd.to_datetime(df['timestamp'], unit='ms')
df.index.name = 'date'  # Standardize to 'date' for consistency
df = df.drop(columns=['timestamp'])
```

**Alternative:** Keep as `timestamp` but requires changes downstream

**Recommendation:** Use `date` for consistency with existing system

---

## 📝 Implementation Plan

### Phase 1: Core CCXT DataSource ✅

**File:** `connors/datasources/ccxt.py`

```python
"""
CCXT DataSource - Cryptocurrency data from multiple exchanges

Supports: Binance, Kraken, Coinbase, and 100+ other exchanges via CCXT library
"""

import os
from typing import Optional
import pandas as pd
import ccxt
from connors.core.registry import registry


@registry.register_datasource("ccxt")
class CCXTDataSource:
    """CCXT - Unified cryptocurrency exchange API"""

    INTERVAL_MAP = {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "2h": "2h",
        "4h": "4h",
        "6h": "6h",
        "12h": "12h",
        "1d": "1d",
        "1w": "1w",
        "1M": "1M",
    }

    def __init__(self, exchange: str = "binance", api_key: Optional[str] = None, secret: Optional[str] = None):
        """
        Initialize CCXT datasource

        Args:
            exchange: Exchange ID (binance, kraken, coinbase, etc.)
            api_key: Optional API key for private endpoints
            secret: Optional secret for private endpoints
        """
        self.exchange_id = exchange

        # Validate exchange exists
        if exchange not in ccxt.exchanges:
            raise ValueError(
                f"Exchange '{exchange}' not supported. "
                f"Available: {', '.join(ccxt.exchanges[:10])}..."
            )

        # Create exchange instance
        exchange_class = getattr(ccxt, exchange)

        # Initialize with credentials if provided
        config = {}
        if api_key:
            config['apiKey'] = api_key
        if secret:
            config['secret'] = secret

        self.exchange = exchange_class(config)

    def fetch(
        self, symbol: str, start: str, end: str, interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from crypto exchange

        Args:
            symbol: Trading pair (e.g., BTC/USDT, ETH/USD)
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            interval: Timeframe (1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M)

        Returns:
            DataFrame with columns: [open, high, low, close, volume] and datetime index
        """
        # Map interval
        timeframe = self.INTERVAL_MAP.get(interval)
        if not timeframe:
            raise ValueError(
                f"Interval '{interval}' not supported. "
                f"Available: {list(self.INTERVAL_MAP.keys())}"
            )

        # Convert dates to milliseconds timestamp
        since = int(pd.to_datetime(start).timestamp() * 1000)
        until = int(pd.to_datetime(end).timestamp() * 1000)

        # Fetch all data (may require pagination)
        all_ohlcv = []
        current_since = since

        while current_since < until:
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=current_since,
                limit=1000  # Max per request
            )

            if not ohlcv:
                break

            all_ohlcv.extend(ohlcv)

            # Update since to last timestamp
            current_since = ohlcv[-1][0] + 1

            # Stop if we've reached the end
            if current_since >= until:
                break

        if not all_ohlcv:
            raise RuntimeError(f"No data found for {symbol} on {self.exchange_id}")

        # Convert to DataFrame
        df = pd.DataFrame(
            all_ohlcv,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )

        # Convert timestamp to datetime index
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        df.index.name = 'date'  # Standardize name

        # Filter to exact date range
        df = df[(df.index >= start) & (df.index <= end)]

        # Ensure lowercase columns
        df.columns = df.columns.str.lower()

        return df
```

**Dependencies:**
```bash
pip install ccxt
```

**Tests:**
```python
# tests/test_ccxt_datasource.py
def test_ccxt_binance():
    ds = CCXTDataSource(exchange="binance")
    df = ds.fetch("BTC/USDT", "2024-01-01", "2024-01-02", "1h")
    assert len(df) == 24
    assert list(df.columns) == ['open', 'high', 'low', 'close', 'volume']
    assert df.index.name == 'date'
```

---

### Phase 2: CLI Updates ✅

**File:** `connors/cli/downloader.py`

**Changes:**

1. **Add --exchange argument:**
```python
parser.add_argument(
    "--exchange",
    help="Cryptocurrency exchange for ccxt datasource (e.g., binance, kraken, coinbase)"
)
```

2. **Update interval choices (make dynamic):**
```python
# Current (static):
parser.add_argument(
    "--interval",
    default="1d",
    choices=["1d", "1wk", "1mo"],
    help="Data interval"
)

# New (extended for crypto):
parser.add_argument(
    "--interval",
    default="1d",
    choices=["1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1wk", "1mo", "1M"],
    help="Data interval (crypto supports more granular intervals)"
)
```

3. **Pass exchange to datasource:**
```python
# After: datasource_instance = self.registry.create_datasource(datasource)

# New:
kwargs = {}
if args.exchange:
    kwargs['exchange'] = args.exchange

datasource_instance = self.registry.create_datasource(datasource, **kwargs)
```

**Usage examples:**
```bash
# Binance BTC/USDT hourly data
python -m connors.cli.downloader \
  --datasource ccxt \
  --exchange binance \
  --ticker BTC/USDT \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --interval 1h

# Kraken ETH/USD daily data
python -m connors.cli.downloader \
  --datasource ccxt \
  --exchange kraken \
  --ticker ETH/USD \
  --interval 1d \
  --timespan 1Y

# Coinbase BTC/USD 15-minute data
python -m connors.cli.downloader \
  --datasource ccxt \
  --exchange coinbase \
  --ticker BTC/USD \
  --interval 15m \
  --start 2024-06-01 \
  --end 2024-06-30
```

---

### Phase 3: Download Service Updates ✅

**File:** `connors/services/download_service.py`

**Changes:**

1. **Import ccxt datasource:**
```python
import connors.datasources.ccxt  # noqa: F401
```

2. **Update datasource info:**
```python
def get_datasource_info(self) -> Dict[str, Dict[str, Any]]:
    datasources_info = {
        # ... existing ...
        "ccxt": {
            "name": "ccxt",
            "description": "Cryptocurrency data from 100+ exchanges via CCXT",
            "requires_api_key": False,
            "supported_intervals": "1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M",
            "requires_exchange": True,
            "global_coverage": True,
        },
    }
```

3. **Update supported intervals:**
```python
def get_supported_intervals(self) -> List[str]:
    """Get list of supported data intervals"""
    return ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1wk", "1mo", "1M"]
```

4. **Accept exchange parameter in download method:**
```python
def download(
    self,
    datasource: str,
    ticker: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    interval: str = "1d",
    market: Optional[str] = None,
    output_file: Optional[str] = None,
    output_format: str = "csv",
    progress_callback: Optional[Callable[[str], None]] = None,
    exchange: Optional[str] = None,  # NEW
) -> DownloadResult:
    # ...

    # Create datasource instance with exchange if provided
    kwargs = {}
    if exchange:
        kwargs['exchange'] = exchange

    datasource_instance = self.registry.create_datasource(datasource, **kwargs)
```

---

### Phase 4: Documentation ✅

**File:** `connors/datasources/CCXT_README.md`

Create comprehensive documentation covering:
- Supported exchanges
- Symbol format (BTC/USDT vs BTCUSDT)
- Interval mappings
- Rate limits
- API key setup (optional)
- Examples for major exchanges

---

## 🔄 Alternative Crypto DataSources

### Future Implementations

#### 1. CoinGecko (Free, No API Key)
```python
@registry.register_datasource("coingecko")
class CoinGeckoDataSource:
    """Free crypto data from CoinGecko API"""
    # Limited to daily data only
    # Good for historical price data
```

#### 2. CryptoCompare
```python
@registry.register_datasource("cryptocompare")
class CryptoCompareDataSource:
    """CryptoCompare - Crypto data API"""
    # Requires API key
    # Good for historical data
```

#### 3. Messari
```python
@registry.register_datasource("messari")
class MessariDataSource:
    """Messari - Crypto research data"""
    # Requires API key
    # Good for fundamental data
```

---

## 📦 Testing Strategy

### Unit Tests
```bash
tests/test_ccxt_datasource.py
```

**Test cases:**
- ✅ Fetch BTC/USDT from Binance
- ✅ Fetch ETH/USD from Kraken
- ✅ Different intervals (1m, 1h, 1d)
- ✅ Date range filtering
- ✅ Invalid exchange error
- ✅ Invalid symbol error
- ✅ Column normalization
- ✅ Index naming

### Integration Tests
```bash
tests/test_ccxt_integration.py
```

**Test cases:**
- ✅ CLI download with --exchange
- ✅ Download service with exchange parameter
- ✅ CSV/JSON output format
- ✅ Multiple timeframes

### Manual Testing
```bash
# Test download with different exchanges
bash scripts/test_ccxt_downloads.sh
```

---

## 🚀 Deployment Steps

### Step 1: Install Dependencies
```bash
pip install ccxt
```

### Step 2: Create CCXT DataSource
```bash
git checkout -b ccxt_crypto_datasource
touch connors/datasources/ccxt.py
# Implement CCXTDataSource class
```

### Step 3: Update CLI
```bash
# Edit connors/cli/downloader.py
# Add --exchange argument
# Extend interval choices
```

### Step 4: Update Download Service
```bash
# Edit connors/services/download_service.py
# Add exchange parameter support
# Update datasource info
```

### Step 5: Write Tests
```bash
# Create tests/test_ccxt_datasource.py
pytest tests/test_ccxt_datasource.py -v
```

### Step 6: Documentation
```bash
# Create connors/datasources/CCXT_README.md
# Update main README.md
# Update CLAUDE.md with CCXT examples
```

### Step 7: Test End-to-End
```bash
# Test various exchanges
python -m connors.cli.downloader --datasource ccxt --exchange binance --ticker BTC/USDT --timespan 1M
python -m connors.cli.downloader --datasource ccxt --exchange kraken --ticker ETH/USD --timespan 1M
python -m connors.cli.downloader --datasource ccxt --exchange coinbase --ticker BTC/USD --timespan 1M
```

### Step 8: Commit and Push
```bash
git add .
git commit -m "Add CCXT crypto datasource with multi-exchange support"
git push origin ccxt_crypto_datasource
```

---

## ⚠️ Considerations & Limitations

### Rate Limits
- Each exchange has different rate limits
- CCXT handles rate limiting automatically
- May need to add delays for large date ranges

### Symbol Format
- Different exchanges use different formats:
  - Binance: `BTC/USDT`
  - Kraken: `BTC/USD` or `XBT/USD`
  - Coinbase: `BTC/USD`
- CCXT normalizes to unified format (/)

### Data Availability
- Not all exchanges support all intervals
- Historical data may be limited on some exchanges
- Some exchanges require API keys for historical data

### Pagination
- Large date ranges may require multiple API calls
- Implemented with pagination in fetch() method

### Timezone
- All timestamps are UTC
- No timezone conversion needed for crypto (24/7 market)

---

## 📊 Example Usage

### Download BTC/USDT from Binance (1 year, hourly)
```bash
python -m connors.cli.downloader \
  --datasource ccxt \
  --exchange binance \
  --ticker BTC/USDT \
  --interval 1h \
  --timespan 1Y \
  --output btc_binance_1h.csv
```

### Download ETH/USD from Kraken (custom range, daily)
```bash
python -m connors.cli.downloader \
  --datasource ccxt \
  --exchange kraken \
  --ticker ETH/USD \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --interval 1d \
  --format json
```

### Backtest with CCXT Data
```bash
# Download data
python -m connors.cli.downloader \
  --datasource ccxt \
  --exchange binance \
  --ticker BTC/USDT \
  --interval 1h \
  --timespan 1Y \
  --output ~/Downloads/BTC_USDT_1h.csv

# Run backtest
python -m connors.cli.backtest \
  --tickers BTC-USDT \
  --strategy RSI_Crypto \
  --config america \
  --interval 1h \
  --dataset-file ~/Downloads/BTC_USDT_1h.csv
```

---

## ✅ Success Criteria

1. ✅ CCXT datasource successfully downloads from Binance
2. ✅ CCXT datasource successfully downloads from Kraken
3. ✅ CCXT datasource successfully downloads from Coinbase
4. ✅ All crypto intervals (1m-1M) work correctly
5. ✅ DataFrame output matches existing format (lowercase columns, date index)
6. ✅ CLI --exchange parameter works
7. ✅ Integration with download_service works
8. ✅ All tests pass
9. ✅ Documentation complete
10. ✅ No breaking changes to existing datasources

---

## 🎯 Future Enhancements

### Phase 5: Advanced Features
- [ ] Support for multiple symbols in single request
- [ ] Real-time WebSocket data streaming
- [ ] Order book data
- [ ] Trade data (tick-by-tick)
- [ ] Funding rates (for futures)

### Phase 6: Exchange-Specific Optimizations
- [ ] Binance: Use batch download for multiple symbols
- [ ] Kraken: Handle XBT vs BTC naming
- [ ] Coinbase: Pro API integration

### Phase 7: Caching
- [ ] Cache exchange metadata (symbols, intervals)
- [ ] Cache downloaded data for faster re-runs
- [ ] Smart incremental updates

---

## 📚 References

- [CCXT Documentation](https://docs.ccxt.com/)
- [CCXT GitHub](https://github.com/ccxt/ccxt)
- [CCXT Manual](https://docs.ccxt.com/en/latest/manual.html)
- [CCXT Supported Exchanges](https://github.com/ccxt/ccxt/wiki/Exchange-Markets)
- [Binance API](https://binance-docs.github.io/apidocs/spot/en/)
- [Kraken API](https://docs.kraken.com/rest/)
- [Coinbase API](https://docs.cloud.coinbase.com/exchange/reference/)

---

**Status:** Ready for implementation
**Estimated Effort:** 4-6 hours
**Risk:** Low (minimal changes to existing code)
**Priority:** High (enables crypto backtesting with RSI_Crypto strategy)
