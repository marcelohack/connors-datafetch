from typing import cast

import pandas as pd
import yfinance as yf

from connors_datafetch.core.datasource import MarketDataSource
from connors_datafetch.core.registry import registry


@registry.register_datasource("yfinance")
class YfinanceDataSource:
    """yfinance - Yahoo Finance data source implementation"""

    def fetch(
        self, symbol: str, start: str, end: str, interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch OHLCV data from Yahoo Finance"""
        df = cast(
            pd.DataFrame,
            yf.download(
                tickers=symbol,
                start=start,
                end=end,
                interval=interval,
                progress=False,
                multi_level_index=False,
            ),
        )

        # Convert column names to lowercase for consistency
        df.columns = df.columns.str.lower()
        if df.index.name:
            df.index.name = df.index.name.lower()

        return df
