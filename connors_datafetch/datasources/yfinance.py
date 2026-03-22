from typing import cast

import pandas as pd
import yfinance as yf

from connors_datafetch.core.datasource import MarketDataSource
from connors_datafetch.core.registry import registry


@registry.register_datasource("yfinance")
class YfinanceDataSource:
    """yfinance - Yahoo Finance data source implementation"""

    # Max lookback days per interval (None = unlimited)
    SUPPORTED_INTERVALS = {
        "1m": 7,
        "2m": 60,
        "5m": 60,
        "15m": 60,
        "30m": 60,
        "90m": 60,
        "1h": 730,
        "1d": None,
        "1wk": None,
        "1mo": None,
    }

    def fetch(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
        extended_hours: bool = False,
    ) -> pd.DataFrame:
        """Fetch OHLCV data from Yahoo Finance

        Args:
            symbol: Ticker symbol
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 90m, 1h, 1d, 1wk, 1mo)
            extended_hours: Include pre-market and after-hours data (default: False)
        """
        if interval not in self.SUPPORTED_INTERVALS:
            supported = ", ".join(sorted(self.SUPPORTED_INTERVALS.keys()))
            raise ValueError(
                f"Interval '{interval}' not supported for yfinance datasource. "
                f"Supported intervals: {supported}"
            )

        # Validate date range against interval limits
        max_days = self.SUPPORTED_INTERVALS[interval]
        if max_days is not None:
            start_dt = pd.to_datetime(start)
            end_dt = pd.to_datetime(end)
            requested_days = (end_dt - start_dt).days
            if requested_days > max_days:
                raise ValueError(
                    f"Interval '{interval}' supports a maximum lookback of {max_days} days, "
                    f"but the requested range spans {requested_days} days. "
                    f"Please narrow your date range or use a larger interval."
                )

        df = cast(
            pd.DataFrame,
            yf.download(
                tickers=symbol,
                start=start,
                end=end,
                interval=interval,
                prepost=extended_hours,
                progress=False,
                multi_level_index=False,
            ),
        )

        # Convert column names to lowercase for consistency
        df.columns = df.columns.str.lower()
        if df.index.name:
            df.index.name = df.index.name.lower()

        return df
