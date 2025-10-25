"""
CCXT DataSource - Cryptocurrency data from multiple exchanges

Supports 100+ cryptocurrency exchanges via the CCXT unified API library.
Provides OHLCV (Open, High, Low, Close, Volume) data for crypto trading pairs.

Supported exchanges: Binance, Kraken, Coinbase, and many more.
"""

import os
from typing import Optional
import pandas as pd

try:
    import ccxt
except ImportError:
    raise ImportError(
        "ccxt library is required for crypto datasource. "
        "Install it with: pip install ccxt"
    )

from connors_downloader.core.registry import registry


@registry.register_datasource("ccxt")
class CCXTDataSource:
    """
    CCXT - Unified cryptocurrency exchange API

    Fetches historical OHLCV data from 100+ crypto exchanges using the CCXT library.

    Features:
    - Multi-exchange support (Binance, Kraken, Coinbase, etc.)
    - Crypto-specific intervals (1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M)
    - Automatic pagination for large date ranges
    - Standardized output format matching other datasources

    Example:
        >>> from connors.datasources.ccxt import CCXTDataSource
        >>> ds = CCXTDataSource(exchange="binance")
        >>> df = ds.fetch("BTC/USDT", "2024-01-01", "2024-01-31", "1h")
    """

    # Interval mapping: CLI format -> CCXT format
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

    def __init__(
        self,
        exchange: str = "binance",
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
    ):
        """
        Initialize CCXT datasource

        Args:
            exchange: Exchange ID (binance, kraken, coinbase, etc.)
                     Default: "binance"
            api_key: Optional API key for private endpoints
                    Can also be set via environment variable: CCXT_API_KEY
            secret: Optional secret for private endpoints
                   Can also be set via environment variable: CCXT_SECRET

        Raises:
            ValueError: If exchange is not supported by CCXT
        """
        self.exchange_id = exchange.lower()

        # Validate exchange exists in CCXT
        if self.exchange_id not in ccxt.exchanges:
            available_exchanges = ", ".join(sorted(ccxt.exchanges[:20]))
            raise ValueError(
                f"Exchange '{exchange}' not supported by CCXT. "
                f"Available exchanges (first 20): {available_exchanges}... "
                f"See https://github.com/ccxt/ccxt#supported-cryptocurrency-exchange-markets for full list."
            )

        # Get exchange class
        exchange_class = getattr(ccxt, self.exchange_id)

        # Initialize with credentials if provided (or from environment)
        config = {}

        # API key from parameter or environment
        if api_key:
            config["apiKey"] = api_key
        elif os.getenv("CCXT_API_KEY"):
            config["apiKey"] = os.getenv("CCXT_API_KEY")

        # Secret from parameter or environment
        if secret:
            config["secret"] = secret
        elif os.getenv("CCXT_SECRET"):
            config["secret"] = os.getenv("CCXT_SECRET")

        # Create exchange instance
        self.exchange = exchange_class(config)

        # Enable rate limiting to avoid API bans
        self.exchange.enableRateLimit = True

    def fetch(
        self, symbol: str, start: str, end: str, interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from crypto exchange

        Args:
            symbol: Trading pair in CCXT format (e.g., BTC/USDT, ETH/USD, BTC/EUR)
                   Format: BASE/QUOTE (e.g., BTC/USDT means Bitcoin priced in USDT)
            start: Start date in YYYY-MM-DD format
            end: End date in YYYY-MM-DD format
            interval: Timeframe interval
                     Supported: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M
                     Default: "1d" (daily)

        Returns:
            pandas.DataFrame with columns: [open, high, low, close, volume]
            Index: DatetimeIndex named 'date' (UTC timezone)

        Raises:
            ValueError: If interval not supported or symbol invalid
            RuntimeError: If no data found or API error

        Example:
            >>> ds = CCXTDataSource(exchange="binance")
            >>> df = ds.fetch("BTC/USDT", "2024-01-01", "2024-01-31", "1h")
            >>> print(df.head())
                                   open      high       low     close      volume
            date
            2024-01-01 00:00:00  42800.0  42850.0  42750.0  42820.0  125.450000
            2024-01-01 01:00:00  42820.0  42900.0  42800.0  42880.0  98.320000
        """
        # Validate and map interval
        timeframe = self.INTERVAL_MAP.get(interval)
        if not timeframe:
            supported = ", ".join(sorted(self.INTERVAL_MAP.keys()))
            raise ValueError(
                f"Interval '{interval}' not supported for CCXT datasource. "
                f"Supported intervals: {supported}"
            )

        # Check if exchange supports this timeframe
        if hasattr(self.exchange, "timeframes"):
            if timeframe not in self.exchange.timeframes:
                available_tf = ", ".join(sorted(self.exchange.timeframes.keys()))
                raise ValueError(
                    f"Timeframe '{timeframe}' not supported by {self.exchange_id}. "
                    f"Available timeframes: {available_tf}"
                )

        # Convert dates to milliseconds timestamp (CCXT uses milliseconds)
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)
        since = int(start_dt.timestamp() * 1000)
        until = int(end_dt.timestamp() * 1000)

        # Fetch all data with pagination (CCXT limits to ~1000 candles per request)
        all_ohlcv = []
        current_since = since

        # Safety limit to prevent infinite loops
        max_iterations = 1000
        iteration = 0

        while current_since < until and iteration < max_iterations:
            try:
                # Fetch OHLCV data
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=current_since,
                    limit=1000,  # Max candles per request
                )
            except ccxt.NetworkError as e:
                raise RuntimeError(
                    f"Network error fetching data from {self.exchange_id}: {str(e)}"
                )
            except ccxt.ExchangeError as e:
                raise RuntimeError(
                    f"Exchange error from {self.exchange_id}: {str(e)}. "
                    f"Check if symbol '{symbol}' is valid for this exchange."
                )
            except Exception as e:
                raise RuntimeError(
                    f"Unexpected error fetching data from {self.exchange_id}: {str(e)}"
                )

            # Break if no data returned
            if not ohlcv:
                break

            # Add to results
            all_ohlcv.extend(ohlcv)

            # Update timestamp for next batch (add 1ms to avoid duplicate)
            last_timestamp = ohlcv[-1][0]
            current_since = last_timestamp + 1

            # Stop if we've reached or passed the end date
            if current_since >= until:
                break

            iteration += 1

        # Check if we hit the safety limit
        if iteration >= max_iterations:
            raise RuntimeError(
                f"Exceeded maximum iterations ({max_iterations}) while fetching data. "
                f"This might indicate an issue with the date range or exchange response."
            )

        # Check if any data was retrieved
        if not all_ohlcv:
            raise RuntimeError(
                f"No data found for {symbol} on {self.exchange_id} "
                f"between {start} and {end}"
            )

        # Convert to DataFrame
        # CCXT returns: [timestamp, open, high, low, close, volume]
        df = pd.DataFrame(
            all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        # Convert timestamp (milliseconds) to datetime
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

        # Set timestamp as index
        df = df.set_index("timestamp")

        # Rename index to 'date' for consistency with other datasources
        df.index.name = "date"

        # Filter to exact date range (inclusive)
        # Convert to timezone-aware for comparison
        start_dt_utc = start_dt.tz_localize("UTC") if start_dt.tzinfo is None else start_dt
        end_dt_utc = end_dt.tz_localize("UTC") if end_dt.tzinfo is None else end_dt

        df = df[(df.index >= start_dt_utc) & (df.index <= end_dt_utc)]

        # Ensure columns are lowercase for consistency
        df.columns = df.columns.str.lower()

        # Sort by date (should already be sorted, but ensure it)
        df = df.sort_index()

        # Remove any duplicate timestamps (shouldn't happen, but be safe)
        df = df[~df.index.duplicated(keep="first")]

        return df

    def get_supported_symbols(self) -> list:
        """
        Get list of supported trading pairs for this exchange

        Returns:
            List of trading pair symbols (e.g., ['BTC/USDT', 'ETH/USD', ...])

        Example:
            >>> ds = CCXTDataSource(exchange="binance")
            >>> symbols = ds.get_supported_symbols()
            >>> 'BTC/USDT' in symbols
            True
        """
        try:
            self.exchange.load_markets()
            return list(self.exchange.markets.keys())
        except Exception as e:
            raise RuntimeError(
                f"Failed to load markets from {self.exchange_id}: {str(e)}"
            )

    def get_supported_timeframes(self) -> list:
        """
        Get list of supported timeframes for this exchange

        Returns:
            List of supported timeframe strings (e.g., ['1m', '5m', '1h', '1d'])

        Example:
            >>> ds = CCXTDataSource(exchange="binance")
            >>> timeframes = ds.get_supported_timeframes()
            >>> '1h' in timeframes
            True
        """
        if hasattr(self.exchange, "timeframes"):
            return list(self.exchange.timeframes.keys())
        else:
            # Return common timeframes if exchange doesn't specify
            return ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]
