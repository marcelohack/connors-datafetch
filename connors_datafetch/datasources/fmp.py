import os
from typing import Optional

import pandas as pd
import requests

from connors_datafetch.core.datasource import MarketDataSource
from connors_datafetch.core.registry import registry


@registry.register_datasource("fmp")
class FinancialModelingPrepDataSource:
    """FMP - FinancialModelingPrep data source implementation"""

    def __init__(self, api_key: Optional[str] = None):
        self.session = requests.Session()
        if api_key is None:
            api_key = os.getenv("FMP_API_KEY")
            if not api_key:
                raise ValueError(
                    "FinancialModelingPrep API key is required. Please set the FMP_API_KEY environment variable "
                    "or pass it as the api_key parameter."
                )
        self.api_key = api_key

    def fetch(
        self, symbol: str, start: str, end: str, interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch OHLCV data from FinancialModelingPrep"""

        # FMP v3 API supports daily data through historical-price-full endpoint
        # For weekly/monthly, we use the historical-chart endpoint
        if interval == "1d":
            # Use historical-price-full endpoint for daily data
            url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
            params = {
                "from": pd.to_datetime(start).strftime("%Y-%m-%d"),
                "to": pd.to_datetime(end).strftime("%Y-%m-%d"),
                "apikey": self.api_key,
            }
        elif interval in ["1wk", "1mo"]:
            # Use historical-chart endpoint for weekly/monthly data
            interval_map = {
                "1wk": "1week",
                "1mo": "1month",
            }
            timeseries = interval_map[interval]
            url = f"https://financialmodelingprep.com/api/v3/historical-chart/{timeseries}/{symbol}"
            params = {
                "from": pd.to_datetime(start).strftime("%Y-%m-%d"),
                "to": pd.to_datetime(end).strftime("%Y-%m-%d"),
                "apikey": self.api_key,
            }
        else:
            raise ValueError(
                f"Unsupported interval: {interval}. Use '1d', '1wk', or '1mo'."
            )

        response = self.session.get(url, params=params, timeout=20)
        if response.status_code != 200:
            raise RuntimeError(
                f"FMP HTTP {response.status_code}: {response.text[:200]}"
            )
        data = response.json()

        # Handle different response formats based on endpoint
        if interval == "1d":
            # Daily data comes wrapped in a 'historical' key from historical-price-full
            results = data.get("historical", [])
        else:
            # Weekly/monthly data from historical-chart comes as direct array
            results = data if isinstance(data, list) else []

        if not results:
            raise RuntimeError("FMP returned no results")

        # FMP uses consistent field names for all intervals
        df = pd.DataFrame(results)
        df = df[["open", "high", "low", "close", "volume"]]
        df.columns = ["open", "high", "low", "close", "volume"]

        # Set datetime index using date column
        df.index = pd.to_datetime([row["date"] for row in results])
        df.index.name = "date"

        # Sort by date (FMP returns newest first, we want oldest first)
        df = df.sort_index()

        return df
